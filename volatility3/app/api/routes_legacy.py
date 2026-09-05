import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import legacy
from ..db import get_db
from ..models.image import Image
from ..schemas.image import ImageOut
from ..schemas.insight import InsightAvailability  # reused: identical {available, detail} shape
from ..storage.images import absolute_path_for

router = APIRouter(prefix="/api/legacy", tags=["legacy"])


@router.get("/health", response_model=InsightAvailability)
async def legacy_health() -> InsightAvailability:
    available, detail = await legacy.check_available()
    return InsightAvailability(available=available, detail=detail)


@router.get("/plugins")
def legacy_plugins() -> list[dict]:
    try:
        return legacy.list_plugins()
    except legacy.LegacyServiceError as exc:
        raise HTTPException(status_code=503, detail=f"Legacy service unavailable: {exc}") from exc


@router.post("/images/{image_id}/identify", response_model=ImageOut)
def identify_legacy(image_id: uuid.UUID, db: Session = Depends(get_db)) -> Image:
    image = db.get(Image, image_id)
    if image is None:
        raise HTTPException(status_code=404, detail="Image not found")

    # Synchronous on purpose (unlike v3 identify, which is async/Celery):
    # imageinfo's KDBG scan is not that slow in practice (seconds, not
    # minutes - confirmed directly), and this is an explicit on-demand
    # click, not something that runs automatically on every upload.
    try:
        result = legacy.identify(absolute_path_for(image.storage_path))
    except legacy.LegacyServiceError as exc:
        raise HTTPException(status_code=503, detail=f"Legacy service unavailable: {exc}") from exc

    profiles = result.get("profiles") or []
    image.legacy_profile = profiles[0] if profiles else None
    db.commit()
    db.refresh(image)
    return image
