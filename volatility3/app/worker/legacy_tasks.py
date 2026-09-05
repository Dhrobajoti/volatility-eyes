"""Executes a legacy (volatility2) job. Deliberately a completely separate
function/task from execute_job (tasks.py) - a bug or outage here must never
be able to affect volatility3 job execution, which is the default/primary
path. See volatility2/README.md for the full isolation rationale.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from .. import legacy
from ..db import SessionLocal
from ..models.image import Image
from ..models.job import Job, JobStatus
from ..progress_bus import publish
from ..storage.images import absolute_path_for
from ..storage.results import write_legacy_result
from .celery_app import celery_app


def execute_legacy_job(job_id: uuid.UUID) -> None:
    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        if job is None:
            return

        image = db.get(Image, job.image_id)
        if image is None:
            job.status = JobStatus.failed
            job.error = {"type": "internal", "message": "Referenced image no longer exists"}
            job.finished_at = datetime.now(timezone.utc)
            db.commit()
            publish(job_id, 100.0, "failed", terminal=True)
            return

        profile = job.params.get("profile")
        if not profile:
            job.status = JobStatus.failed
            job.error = {"type": "missing_params", "message": "A volatility2 profile is required"}
            job.finished_at = datetime.now(timezone.utc)
            db.commit()
            publish(job_id, 100.0, "failed", terminal=True)
            return

        job.status = JobStatus.running
        job.started_at = datetime.now(timezone.utc)
        db.commit()
        publish(job_id, 10.0, f"Running {job.plugin_name} (volatility2)...")

        try:
            result = legacy.run_plugin(
                image_path=absolute_path_for(image.storage_path),
                profile=profile,
                plugin_name=job.plugin_name,
                extra_args=job.params.get("extra_args") or [],
            )
        except legacy.LegacyServiceError as exc:
            job.status = JobStatus.failed
            job.error = {"type": "internal", "message": f"Legacy service unavailable: {exc}"}
        else:
            job.result_path = write_legacy_result(job_id, result["output"])
            job.row_count = len(result["output"].splitlines())
            job.status = JobStatus.completed

        job.finished_at = datetime.now(timezone.utc)
        db.commit()
        publish(job_id, 100.0, job.status.value, terminal=True)
    finally:
        db.close()


@celery_app.task(name="run_legacy_plugin_job")
def run_legacy_plugin_job(job_id: str) -> None:
    execute_legacy_job(uuid.UUID(job_id))
