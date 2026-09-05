"""Celery task that produces an Insight session's initial "first look"
summary: ensure the baseline plugin bundle has run, gather the results,
hand them to the (optional) insights service, and store the reply.

Reuses `execute_job` directly (the plain function, not the Celery task) for
each baseline plugin, called inline within this task rather than dispatched
as separate Celery tasks - avoids a worker with limited concurrency
deadlocking on a task that's waiting on other tasks in the same pool.

If the insights/ollama services aren't running (the Compose "insights"
profile wasn't started), this task fails cleanly with a stored error on the
session - it never raises out to affect the Celery worker's ability to keep
processing ordinary plugin jobs.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select

from .. import insights
from ..db import SessionLocal
from ..models.image import Image
from ..models.insight import InsightMessage, InsightRole, InsightSession, InsightSessionStatus
from ..models.job import Job, JobStatus
from ..storage.results import read_legacy_result, read_result
from .celery_app import celery_app
from .legacy_tasks import execute_legacy_job
from .tasks import execute_job


def _find_or_create_baseline_job(db, image_id: uuid.UUID, plugin_name: str, session_id: uuid.UUID) -> Job:
    existing = db.scalar(
        select(Job)
        .where(
            Job.image_id == image_id,
            Job.plugin_name == plugin_name,
            Job.status == JobStatus.completed,
        )
        .order_by(Job.created_at.desc())
    )
    if existing is not None:
        return existing

    job = Job(
        image_id=image_id,
        plugin_name=plugin_name,
        params={},
        status=JobStatus.queued,
        triggered_by=f"insight_session:{session_id}",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    execute_job(job.id)
    db.refresh(job)
    return job


def _find_or_create_legacy_baseline_job(
    db, image: Image, plugin_name: str, session_id: uuid.UUID
) -> Job:
    existing = db.scalar(
        select(Job)
        .where(
            Job.image_id == image.id,
            Job.plugin_name == plugin_name,
            Job.engine == "v2",
            Job.status == JobStatus.completed,
        )
        .order_by(Job.created_at.desc())
    )
    if existing is not None:
        return existing

    job = Job(
        image_id=image.id,
        plugin_name=plugin_name,
        engine="v2",
        params={"profile": image.legacy_profile},
        status=JobStatus.queued,
        triggered_by=f"insight_session:{session_id}",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    execute_legacy_job(job.id)
    db.refresh(job)
    return job


def generate_baseline_summary(session_id: uuid.UUID) -> None:
    db = SessionLocal()
    try:
        session = db.get(InsightSession, session_id)
        if session is None:
            return
        image = db.get(Image, session.image_id)
        if image is None:
            session.status = InsightSessionStatus.failed
            session.error = {"message": "Referenced image no longer exists"}
            db.commit()
            return

        # os_version is only ever populated when v3's windows.info.Info
        # plugin actually succeeds against this image - the same symbol
        # resolution that plugin needs is what every other v3 plugin needs
        # too, so it's a reliable proxy for "v3 actually works here",
        # unlike legacy_profile (just user-initiated detection, proves
        # nothing about whether v3 fails). Falls back to the v2 bundle when
        # v3 doesn't work and a legacy profile has been detected - the exact
        # gap that produced an "everything failed" summary before this fix.
        use_legacy = image.os_version is None and image.legacy_profile is not None

        if use_legacy:
            plugins = insights.LEGACY_BASELINE_PLUGINS
        else:
            plugins = insights.get_baseline_plugins(image.os_hint)
        if not plugins:
            session.status = InsightSessionStatus.failed
            session.error = {
                "message": (
                    f"No baseline plugin bundle for OS '{image.os_hint or 'unknown'}'. "
                    "Identify the image's OS (or detect its legacy profile) first."
                )
            }
            db.commit()
            return

        referenced_job_ids: list[str] = []
        plugin_results = []
        for plugin_name in plugins:
            if use_legacy:
                job = _find_or_create_legacy_baseline_job(db, image, plugin_name, session_id)
            else:
                job = _find_or_create_baseline_job(db, image.id, plugin_name, session_id)
            referenced_job_ids.append(str(job.id))
            if job.status != JobStatus.completed or not job.result_path:
                plugin_results.append(
                    {
                        "plugin_name": plugin_name,
                        "error": (job.error or {}).get("message", "plugin run failed"),
                    }
                )
                continue
            if use_legacy:
                text = read_legacy_result(job.result_path)
                trimmed = insights.trim_text_for_context(text)
            else:
                data = read_result(job.result_path)
                trimmed = insights.trim_for_context(data)
            plugin_results.append({"plugin_name": plugin_name, **trimmed})

        session.status = InsightSessionStatus.summarizing
        db.commit()

        image_info = {
            "filename": image.filename,
            "os_hint": image.os_hint,
            "os_version": image.os_version,
            "engine": "v2" if use_legacy else "v3",
            "legacy_profile": image.legacy_profile if use_legacy else None,
        }
        try:
            result = insights.summarize(image_info, plugin_results)
        except insights.InsightsUnavailableError as exc:
            session.status = InsightSessionStatus.failed
            session.error = {"message": f"Insights service unavailable: {exc}"}
            db.commit()
            return

        message = InsightMessage(
            session_id=session.id,
            role=InsightRole.assistant,
            content=result.get("summary", ""),
            referenced_job_ids=referenced_job_ids,
        )
        db.add(message)
        session.model_used = result.get("model_used")
        session.status = InsightSessionStatus.ready
        db.commit()
    finally:
        db.close()


def generate_job_insight(session_id: uuid.UUID) -> None:
    """Per-job "Insights" analysis - the button beside "Export as Text" on a
    single completed job's result page. Unlike generate_baseline_summary,
    this never runs any plugin itself: the job it analyzes must already be
    completed (enforced by routes_insights.py before the session/task is
    even created), so this only ever reads a result that already exists.
    """
    db = SessionLocal()
    try:
        session = db.get(InsightSession, session_id)
        if session is None:
            return
        image = db.get(Image, session.image_id)
        job = db.get(Job, session.source_job_id) if session.source_job_id else None
        if image is None or job is None:
            session.status = InsightSessionStatus.failed
            session.error = {"message": "Referenced image or job no longer exists"}
            db.commit()
            return
        if job.status != JobStatus.completed or not job.result_path:
            session.status = InsightSessionStatus.failed
            session.error = {"message": "Job has not completed successfully"}
            db.commit()
            return

        if job.engine == "v2":
            text = read_legacy_result(job.result_path)
            trimmed = insights.trim_text_for_context(text)
        else:
            data = read_result(job.result_path)
            trimmed = insights.trim_for_context(data)
        plugin_results = [{"plugin_name": job.plugin_name, **trimmed}]

        session.status = InsightSessionStatus.summarizing
        db.commit()

        image_info = {
            "filename": image.filename,
            "os_hint": image.os_hint,
            "os_version": image.os_version,
            "engine": job.engine,
            "legacy_profile": image.legacy_profile if job.engine == "v2" else None,
        }
        try:
            result = insights.summarize(image_info, plugin_results, mode="single_job")
        except insights.InsightsUnavailableError as exc:
            session.status = InsightSessionStatus.failed
            session.error = {"message": f"Insights service unavailable: {exc}"}
            db.commit()
            return

        message = InsightMessage(
            session_id=session.id,
            role=InsightRole.assistant,
            content=result.get("summary", ""),
            referenced_job_ids=[str(job.id)],
        )
        db.add(message)
        session.model_used = result.get("model_used")
        session.status = InsightSessionStatus.ready
        db.commit()
    finally:
        db.close()


@celery_app.task(name="generate_insight_baseline")
def generate_insight_baseline_task(session_id: str) -> None:
    generate_baseline_summary(uuid.UUID(session_id))


@celery_app.task(name="generate_job_insight")
def generate_job_insight_task(session_id: str) -> None:
    generate_job_insight(uuid.UUID(session_id))
