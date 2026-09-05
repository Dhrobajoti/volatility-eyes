"""HTTP client for the optional `insights` microservice.

Every call here is best-effort by design: the core app (images, jobs,
plugins) must keep working identically whether `insights`/`ollama` are
running or were never started at all (see docker-compose.yml's `insights`
Compose profile). Nothing in this module raises in a way that should be
allowed to affect anything outside the insights feature itself.
"""

from __future__ import annotations

from typing import Any

import httpx

from ..config import get_settings


class InsightsUnavailableError(Exception):
    """Raised when the insights service can't be reached or errors out."""


async def check_available() -> tuple[bool, str | None]:
    settings = get_settings()
    try:
        async with httpx.AsyncClient(timeout=settings.insights_health_timeout_seconds) as client:
            resp = await client.get(f"{settings.insights_base_url}/health")
            resp.raise_for_status()
            return True, None
    except httpx.HTTPError as exc:
        return False, str(exc)


def summarize(
    image_info: dict[str, Any], plugin_results: list[dict[str, Any]], mode: str = "baseline"
) -> dict[str, Any]:
    """Synchronous on purpose - called from a Celery task, not a request handler.

    mode: "baseline" (broad whole-image first-look, default) or
    "single_job" (focused anomaly/flag-point read of one already-run job's
    output) - selects which system prompt insights/app/prompt.py uses.
    """
    settings = get_settings()
    try:
        with httpx.Client(timeout=settings.insights_summarize_timeout_seconds) as client:
            resp = client.post(
                f"{settings.insights_base_url}/summarize",
                json={"image": image_info, "plugin_results": plugin_results, "mode": mode},
            )
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPError as exc:
        raise InsightsUnavailableError(str(exc)) from exc
