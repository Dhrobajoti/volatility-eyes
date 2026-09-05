from celery import Celery

from ..config import get_settings

settings = get_settings()

celery_app = Celery(
    "vol_gui",
    broker=settings.redis_url,
    backend=settings.redis_url,
)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_track_started=True,
    # celery only imports the module passed to `-A`; tasks.py registers the
    # `run_plugin_job` task via decorator, so it must be imported explicitly
    # rather than relying on celery_app.py importing it (which would be
    # circular, since tasks.py imports celery_app from this module).
    imports=["app.worker.tasks", "app.worker.insight_tasks", "app.worker.legacy_tasks"],
)
