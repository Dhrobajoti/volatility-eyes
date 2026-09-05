import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base
from .image import Image


class InsightSessionStatus(str, enum.Enum):
    gathering = "gathering"  # running/collecting the baseline plugin bundle
    summarizing = "summarizing"  # waiting on the LLM
    ready = "ready"
    failed = "failed"


class InsightRole(str, enum.Enum):
    user = "user"
    assistant = "assistant"


class InsightSession(Base):
    __tablename__ = "insight_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    image_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("images.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Set only for a per-job "Insights" analysis (JobDetailPage's Insights
    # button); null for a whole-image baseline session. SET NULL (not
    # CASCADE) on job deletion - the session's stored message stays valid
    # and readable even if the job it was about is later removed.
    source_job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[InsightSessionStatus] = mapped_column(
        Enum(InsightSessionStatus, name="insight_session_status"),
        default=InsightSessionStatus.gathering,
        nullable=False,
    )
    model_used: Mapped[str | None] = mapped_column(String, nullable=True)
    error: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    image: Mapped[Image] = relationship(lazy="joined")

    @property
    def image_filename(self) -> str | None:
        return self.image.filename if self.image else None


class InsightMessage(Base):
    __tablename__ = "insight_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("insight_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[InsightRole] = mapped_column(Enum(InsightRole, name="insight_role"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # Job ids whose data grounds this message's claims - the UI renders these
    # as "based on: <plugin> ->" links so nothing is asserted without a
    # concrete, independently-checkable source.
    referenced_job_ids: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
