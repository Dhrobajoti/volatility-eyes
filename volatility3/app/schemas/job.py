import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from ..models.job import JobStatus


class JobCreate(BaseModel):
    image_id: uuid.UUID
    plugin_name: str
    params: dict[str, Any] = {}
    # "v3" (default) uses volatility3/vol_service. "v2" uses the legacy
    # volatility2 service - params must include "profile" (from the image's
    # legacy_profile) for that engine; see volatility2/README.md.
    engine: Literal["v3", "v2"] = "v3"


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    image_id: uuid.UUID
    image_filename: str | None = None
    plugin_name: str
    params: dict[str, Any]
    engine: str
    status: JobStatus
    progress_pct: float
    progress_description: str | None
    result_path: str | None
    row_count: int | None
    error: dict[str, Any] | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class JobResultOut(BaseModel):
    columns: list[str] | None = None
    data: list[dict[str, Any]] = []
    # Set instead of `data` for engine="v2" jobs - volatility2 has no
    # reliable structured output across its plugin catalog (see
    # volatility2/README.md), so results are the plugin's own text output.
    raw_text: str | None = None
