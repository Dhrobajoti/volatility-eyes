"""HTTP client for the volatility2 legacy analysis service - see
volatility2/README.md for the full design and why this exists.

Same shape as volatility3/app/insights/client.py deliberately: best-effort
reachability checks, and every call is synchronous (called from Celery
tasks, not request handlers).
"""

from __future__ import annotations

from typing import Any

import httpx

from ..config import get_settings


class LegacyServiceError(Exception):
    """Raised when the legacy service can't be reached or errors out."""


async def check_available() -> tuple[bool, str | None]:
    settings = get_settings()
    try:
        async with httpx.AsyncClient(timeout=settings.legacy_health_timeout_seconds) as client:
            resp = await client.get(f"{settings.volatility2_base_url}/health")
            resp.raise_for_status()
            return True, None
    except httpx.HTTPError as exc:
        return False, str(exc)


def list_plugins() -> list[dict[str, Any]]:
    settings = get_settings()
    with httpx.Client(timeout=settings.legacy_health_timeout_seconds) as client:
        resp = client.get(f"{settings.volatility2_base_url}/plugins")
        resp.raise_for_status()
        return resp.json()["plugins"]


def identify(image_path: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        with httpx.Client(timeout=settings.legacy_run_timeout_seconds) as client:
            resp = client.post(f"{settings.volatility2_base_url}/identify", json={"image_path": image_path})
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPError as exc:
        raise LegacyServiceError(str(exc)) from exc


def run_plugin(
    image_path: str, profile: str, plugin_name: str, extra_args: list[str] | None = None
) -> dict[str, Any]:
    settings = get_settings()
    try:
        with httpx.Client(timeout=settings.legacy_run_timeout_seconds) as client:
            resp = client.post(
                f"{settings.volatility2_base_url}/run",
                json={
                    "image_path": image_path,
                    "profile": profile,
                    "plugin_name": plugin_name,
                    "extra_args": extra_args or [],
                },
            )
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPError as exc:
        raise LegacyServiceError(str(exc)) from exc
