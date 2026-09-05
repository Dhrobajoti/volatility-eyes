import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from ..models.image import ImageStatus


class ImageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str
    size_bytes: int
    sha256: str
    os_hint: str | None
    os_version: str | None
    legacy_profile: str | None
    status: ImageStatus
    created_at: datetime
