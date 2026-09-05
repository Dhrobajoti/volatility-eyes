"""Publishes job progress to Redis pub/sub so the WebSocket route can forward
it to the browser without polling the database.

Publishing is best-effort: a job's correctness must never depend on Redis
being reachable, so connection errors are logged and swallowed rather than
raised (the DB row is always the source of truth for status/progress; the
websocket is a live-updates convenience on top of it).
"""

from __future__ import annotations

import json
import logging
import uuid

import redis

from .config import get_settings

vollog = logging.getLogger(__name__)

_client: redis.Redis | None = None


def _get_client() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.Redis.from_url(get_settings().redis_url)
    return _client


def channel_name(job_id: uuid.UUID) -> str:
    return f"job:{job_id}:progress"


def publish(job_id: uuid.UUID, pct: float, description: str, terminal: bool = False) -> None:
    payload = json.dumps({"pct": pct, "description": description, "terminal": terminal})
    try:
        _get_client().publish(channel_name(job_id), payload)
    except redis.RedisError:
        vollog.warning("Failed to publish progress for job %s", job_id, exc_info=True)
