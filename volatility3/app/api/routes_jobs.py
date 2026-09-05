import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import legacy, vol_service
from ..db import get_db
from ..models.image import Image
from ..models.job import Job, JobStatus
from ..schemas.job import JobCreate, JobOut, JobResultOut
from ..storage.results import (
    job_file_path,
    list_job_files,
    read_legacy_result,
    read_result,
)
from ..worker.legacy_tasks import run_legacy_plugin_job
from ..worker.tasks import run_plugin_job
from .deps import get_current_user

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


def _create_v3_job(body: JobCreate, db: Session, user: str | None) -> Job:
    try:
        schema = vol_service.get_plugin_schema(body.plugin_name)
    except vol_service.PluginNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    missing = [
        {"name": f.name, "description": f.description}
        for f in schema.fields
        if f.required and body.params.get(f.name) in (None, "")
    ]
    if missing:
        raise HTTPException(status_code=422, detail={"type": "missing_params", "fields": missing})

    job = Job(
        image_id=body.image_id,
        plugin_name=body.plugin_name,
        params=body.params,
        engine="v3",
        status=JobStatus.queued,
        created_by=user,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    async_result = run_plugin_job.delay(str(job.id))
    job.celery_task_id = async_result.id
    db.commit()
    db.refresh(job)
    return job


def _create_legacy_job(body: JobCreate, image: Image, db: Session, user: str | None) -> Job:
    try:
        plugin_names = {p["name"] for p in legacy.list_plugins()}
    except legacy.LegacyServiceError as exc:
        raise HTTPException(status_code=503, detail=f"Legacy service unavailable: {exc}") from exc
    if body.plugin_name not in plugin_names:
        raise HTTPException(status_code=404, detail=f"Unknown legacy plugin: {body.plugin_name}")

    profile = body.params.get("profile") or image.legacy_profile
    if not profile:
        raise HTTPException(
            status_code=422,
            detail={
                "type": "missing_params",
                "fields": [{"name": "profile", "description": "Run 'Identify legacy profile' on this image first"}],
            },
        )

    job = Job(
        image_id=body.image_id,
        plugin_name=body.plugin_name,
        params={**body.params, "profile": profile},
        engine="v2",
        status=JobStatus.queued,
        created_by=user,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    async_result = run_legacy_plugin_job.delay(str(job.id))
    job.celery_task_id = async_result.id
    db.commit()
    db.refresh(job)
    return job


@router.post("", response_model=JobOut, status_code=201)
def create_job(
    body: JobCreate,
    db: Session = Depends(get_db),
    user: str | None = Depends(get_current_user),
) -> Job:
    image = db.get(Image, body.image_id)
    if image is None:
        raise HTTPException(status_code=404, detail="Image not found")

    if body.engine == "v2":
        return _create_legacy_job(body, image, db, user)
    return _create_v3_job(body, db, user)


@router.get("", response_model=list[JobOut])
def list_jobs(
    image_id: uuid.UUID | None = None,
    status: JobStatus | None = None,
    db: Session = Depends(get_db),
) -> list[Job]:
    stmt = select(Job).order_by(Job.created_at.desc())
    if image_id is not None:
        stmt = stmt.where(Job.image_id == image_id)
    if status is not None:
        stmt = stmt.where(Job.status == status)
    return list(db.scalars(stmt))


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: uuid.UUID, db: Session = Depends(get_db)) -> Job:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/{job_id}/result", response_model=JobResultOut)
def get_job_result(job_id: uuid.UUID, db: Session = Depends(get_db)) -> JobResultOut:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != JobStatus.completed or job.result_path is None:
        raise HTTPException(status_code=409, detail=f"Job is not completed (status={job.status.value})")
    if job.engine == "v2":
        return JobResultOut(raw_text=read_legacy_result(job.result_path))
    return JobResultOut(data=read_result(job.result_path))


@router.get("/{job_id}/files", response_model=list[str])
def list_job_result_files(job_id: uuid.UUID, db: Session = Depends(get_db)) -> list[str]:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return list_job_files(job_id)


@router.get("/{job_id}/files/{filename}")
def download_job_result_file(
    job_id: uuid.UUID, filename: str, db: Session = Depends(get_db)
) -> FileResponse:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if filename not in list_job_files(job_id):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(job_file_path(job_id, filename), filename=filename)
