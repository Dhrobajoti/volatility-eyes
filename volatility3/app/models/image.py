import enum
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


class ImageStatus(str, enum.Enum):
    uploading = "uploading"
    identifying = "identifying"
    ready = "ready"
    error = "error"


class Image(Base):
    __tablename__ = "images"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    filename: Mapped[str] = mapped_column(String, nullable=False)
    storage_path: Mapped[str] = mapped_column(String, nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str] = mapped_column(String, nullable=False)
    os_hint: Mapped[str | None] = mapped_column(String, nullable=True)
    os_version: Mapped[str | None] = mapped_column(String, nullable=True)
    # volatility2 profile string (e.g. "WinXPSP2x86"), set on demand via the
    # legacy service's /identify - separate from os_hint/os_version, which
    # are volatility3 concepts and use a different vocabulary entirely.
    legacy_profile: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[ImageStatus] = mapped_column(
        Enum(ImageStatus, name="image_status"), default=ImageStatus.ready, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_by: Mapped[str | None] = mapped_column(String, nullable=True)
