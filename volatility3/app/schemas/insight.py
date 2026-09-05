import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from ..models.insight import InsightRole, InsightSessionStatus


class InsightSessionCreate(BaseModel):
    image_id: uuid.UUID


class InsightMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: InsightRole
    content: str
    referenced_job_ids: list[str] | None
    created_at: datetime


class InsightSessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    image_id: uuid.UUID
    image_filename: str | None
    source_job_id: uuid.UUID | None
    status: InsightSessionStatus
    model_used: str | None
    error: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime


class InsightSessionDetailOut(InsightSessionOut):
    messages: list[InsightMessageOut]


class InsightAvailability(BaseModel):
    available: bool
    detail: str | None = None
