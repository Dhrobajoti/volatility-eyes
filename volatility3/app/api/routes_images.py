import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models.image import Image, ImageStatus
from ..models.job import Job, JobStatus
from ..schemas.image import ImageOut
from ..storage.images import delete_image_files, save_uploaded_image
from ..storage.results import delete_job_files
from ..worker.tasks import identify_image_task
from .deps import get_current_user

router = APIRouter(prefix="/api/images", tags=["images"])


@router.post("", response_model=ImageOut, status_code=201)
async def upload_image(
    file: UploadFile,
    db: Session = Depends(get_db),
    user: str | None = Depends(get_current_user),
) -> Image:
    saved = await save_uploaded_image(file)
    image = Image(
        id=saved.image_id,
        filename=file.filename or "image.raw",
        storage_path=saved.storage_path,
        size_bytes=saved.size_bytes,
        sha256=saved.sha256,
        status=ImageStatus.identifying,
        created_by=user,
    )
    db.add(image)
    db.commit()
    db.refresh(image)

    identify_image_task.delay(str(image.id))
    return image


@router.get("", response_model=list[ImageOut])
def list_images(db: Session = Depends(get_db)) -> list[Image]:
    return list(db.scalars(select(Image).order_by(Image.created_at.desc())))


@router.get("/{image_id}", response_model=ImageOut)
def get_image(image_id: uuid.UUID, db: Session = Depends(get_db)) -> Image:
    image = db.get(Image, image_id)
    if image is None:
        raise HTTPException(status_code=404, detail="Image not found")
    return image


@router.post("/{image_id}/identify", response_model=ImageOut)
def reidentify_image(image_id: uuid.UUID, db: Session = Depends(get_db)) -> Image:
    """Re-runs OS identification - mainly useful for images uploaded before
    this feature existed, or if a previous identification attempt failed."""
    image = db.get(Image, image_id)
    if image is None:
        raise HTTPException(status_code=404, detail="Image not found")
    image.status = ImageStatus.identifying
    db.commit()
    db.refresh(image)
    identify_image_task.delay(str(image.id))
    return image


@router.delete("/{image_id}", status_code=204)
def delete_image(image_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    image = db.get(Image, image_id)
    if image is None:
        raise HTTPException(status_code=404, detail="Image not found")

    active_job = db.scalar(
        select(Job).where(
            Job.image_id == image_id,
            Job.status.in_([JobStatus.queued, JobStatus.running]),
        )
    )
    if active_job is not None:
        raise HTTPException(
            status_code=409, detail="Image is referenced by a running or queued job"
        )

    # Deleting the image row cascades to its jobs at the DB level (see the
    # ondelete="CASCADE" FK), but that only removes rows - job result/file
    # storage on disk has to be cleaned up here first.
    job_ids = db.scalars(select(Job.id).where(Job.image_id == image_id))
    for job_id in job_ids:
        delete_job_files(job_id)

    delete_image_files(image.storage_path)
    db.delete(image)
    db.commit()
