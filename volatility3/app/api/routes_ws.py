"""Live job progress over WebSocket.

Subscribes to the Redis pub/sub channel `progress_bus` publishes to. On
connect, sends the job's current DB state first so a client that connects
after the job already finished gets the terminal status immediately instead
of hanging forever waiting for a pub/sub message that will never arrive.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import uuid

import redis.asyncio as aioredis
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..config import get_settings
from ..db import SessionLocal
from ..models.job import Job, JobStatus
from ..progress_bus import channel_name

router = APIRouter(tags=["jobs"])

_TERMINAL_STATUSES = {JobStatus.completed, JobStatus.failed, JobStatus.cancelled}


@router.websocket("/api/jobs/{job_id}/progress")
async def job_progress(websocket: WebSocket, job_id: uuid.UUID) -> None:
    await websocket.accept()

    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
    finally:
        db.close()

    if job is None:
        await websocket.close(code=4404)
        return

    await websocket.send_json(
        {
            "pct": job.progress_pct,
            "description": job.progress_description or job.status.value,
            "terminal": job.status in _TERMINAL_STATUSES,
        }
    )
    if job.status in _TERMINAL_STATUSES:
        await websocket.close()
        return

    client = aioredis.Redis.from_url(get_settings().redis_url)
    pubsub = client.pubsub()
    await pubsub.subscribe(channel_name(job_id))
    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            payload = json.loads(message["data"])
            await websocket.send_json(payload)
            if payload.get("terminal"):
                break
    except WebSocketDisconnect:
        pass
    finally:
        with contextlib.suppress(Exception):
            await pubsub.unsubscribe(channel_name(job_id))
            await pubsub.aclose()
            await client.aclose()
