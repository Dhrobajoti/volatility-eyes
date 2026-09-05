import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base
from .image import Image


class JobStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    image_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("images.id", ondelete="CASCADE"), nullable=False, index=True
    )
    plugin_name: Mapped[str] = mapped_column(String, nullable=False)
    params: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    # "v3" (default, volatility3/vol_service) or "v2" (volatility2/legacy
    # service, for images v3's automagic can't handle). Separate code path
    # end to end (routes -> Celery task -> storage) so a v2 job can never
    # affect v3 job execution even if the legacy service is broken/removed.
    engine: Mapped[str] = mapped_column(String, default="v3", nullable=False)
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status"),
        default=JobStatus.queued,
        nullable=False,
        index=True,
    )
    progress_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    progress_description: Mapped[str | None] = mapped_column(String, nullable=True)
    result_path: Mapped[str | None] = mapped_column(String, nullable=True)
    row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    celery_task_id: Mapped[str | None] = mapped_column(String, nullable=True)
    # "user" (default) or "insight_session:<uuid>" - lets the UI badge jobs an
    # AI session triggered on its own, distinct from ones a human clicked.
    # Matters for forensics auditability: you want to be able to answer
    # "did a person or the AI decide to run this" later.
    triggered_by: Mapped[str] = mapped_column(String, default="user", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[str | None] = mapped_column(String, nullable=True)

    # joined (not select-loaded) so listing jobs doesn't N+1 to show the image name
    image: Mapped[Image] = relationship(lazy="joined")

    @property
    def image_filename(self) -> str | None:
        return self.image.filename if self.image else None
