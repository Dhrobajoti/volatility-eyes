"""Job execution: the piece where DB state, progress publishing, and
vol_service's exceptions all converge.

`execute_job` is a plain function (not a Celery task itself) so it can be
called two ways with identical behaviour:
- synchronously, inline, from the API request handler (used until the Celery
  queue is wired in)
- from `run_plugin_job`, the actual Celery task below, once a broker is
  available

Keeping them as one function avoids ever having two different codepaths for
"how a job actually runs".
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from .. import vol_service
from ..config import get_settings
from ..db import SessionLocal
from ..models.image import Image, ImageStatus
from ..models.job import Job, JobStatus
from ..progress_bus import publish
from ..storage.images import absolute_path_for
from ..storage.results import job_files_dir, write_result
from .celery_app import celery_app


def execute_job(job_id: uuid.UUID, celery_task=None) -> None:
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

        job.status = JobStatus.running
        job.started_at = datetime.now(timezone.utc)
        db.commit()

        def progress_cb(pct: float, description: str) -> None:
            job.progress_pct = pct
            job.progress_description = description
            db.commit()
            publish(job_id, pct, description)
            if celery_task is not None:
                celery_task.update_state(
                    state="PROGRESS", meta={"pct": pct, "description": description}
                )

        try:
            result = vol_service.run_plugin(
                image_path=absolute_path_for(image.storage_path),
                plugin_name=job.plugin_name,
                params=job.params,
                output_dir=job_files_dir(job_id),
                progress_cb=progress_cb,
            )
        except vol_service.MissingParametersError as exc:
            job.status = JobStatus.failed
            job.error = {"type": "missing_params", "fields": exc.field_errors}
        except vol_service.PluginNotFoundError as exc:
            job.status = JobStatus.failed
            job.error = {"type": "invalid_plugin", "message": str(exc)}
        except Exception as exc:  # noqa: BLE001 - convert any plugin/runtime failure to a job error
            job.status = JobStatus.failed
            job.error = {"type": "internal", "message": str(exc)}
        else:
            job.result_path = write_result(job_id, result.data)
            job.row_count = len(result.data)
            job.status = JobStatus.completed

        job.finished_at = datetime.now(timezone.utc)
        db.commit()
        publish(job_id, 100.0, job.status.value, terminal=True)
    finally:
        db.close()


@celery_app.task(bind=True, name="run_plugin_job")
def run_plugin_job(self, job_id: str) -> None:
    execute_job(uuid.UUID(job_id), celery_task=self)


def identify_image(image_id: uuid.UUID) -> None:
    db = SessionLocal()
    try:
        image = db.get(Image, image_id)
        if image is None:
            return
        image_path = absolute_path_for(image.storage_path)

        try:
            os_hint = vol_service.identify_os(image_path)
        except Exception:  # noqa: BLE001 - identification failing shouldn't block using the image
            os_hint = None
        image.os_hint = os_hint
        db.commit()  # OS category first, so the UI shows it without waiting on version info below

        if os_hint == "windows":
            try:
                image.os_version = vol_service.get_windows_version(image_path)
            except Exception:  # noqa: BLE001 - same reasoning as above
                image.os_version = None

        image.status = ImageStatus.ready
        db.commit()
    finally:
        db.close()


@celery_app.task(name="identify_image_task")
def identify_image_task(image_id: str) -> None:
    identify_image(uuid.UUID(image_id))
