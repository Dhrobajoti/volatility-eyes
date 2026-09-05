import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import insights
from ..db import get_db
from ..models.image import Image
from ..models.insight import InsightMessage, InsightSession
from ..models.job import Job, JobStatus
from ..schemas.insight import (
    InsightAvailability,
    InsightMessageOut,
    InsightSessionCreate,
    InsightSessionDetailOut,
    InsightSessionOut,
)
from ..worker.insight_tasks import generate_insight_baseline_task, generate_job_insight_task
from .deps import get_current_user

router = APIRouter(prefix="/api/insights", tags=["insights"])


@router.get("/health", response_model=InsightAvailability)
async def insights_health() -> InsightAvailability:
    """The frontend polls this to decide whether to show the Insights UI at
    all - lets the feature degrade cleanly when the optional `insights`/
    `ollama` containers were never started (see docker-compose.yml)."""
    available, detail = await insights.check_available()
    return InsightAvailability(available=available, detail=detail)


@router.post("/sessions", response_model=InsightSessionOut, status_code=201)
def create_session(
    body: InsightSessionCreate,
    db: Session = Depends(get_db),
    user: str | None = Depends(get_current_user),
) -> InsightSession:
    image = db.get(Image, body.image_id)
    if image is None:
        raise HTTPException(status_code=404, detail="Image not found")

    session = InsightSession(image_id=image.id)
    db.add(session)
    db.commit()
    db.refresh(session)

    generate_insight_baseline_task.delay(str(session.id))
    return session


@router.post("/jobs/{job_id}/analyze", response_model=InsightSessionOut, status_code=201)
def analyze_job(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: str | None = Depends(get_current_user),
) -> InsightSession:
    """Per-job Insights: analyzes just this one job's already-completed
    output for anomalies/flag points, distinct from the whole-image baseline
    session created by POST /sessions."""
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != JobStatus.completed or not job.result_path:
        raise HTTPException(status_code=409, detail="Job has not completed successfully yet")

    session = InsightSession(image_id=job.image_id, source_job_id=job.id)
    db.add(session)
    db.commit()
    db.refresh(session)

    generate_job_insight_task.delay(str(session.id))
    return session


@router.get("/sessions", response_model=list[InsightSessionOut])
def list_sessions(image_id: uuid.UUID | None = None, db: Session = Depends(get_db)) -> list[InsightSession]:
    stmt = select(InsightSession).order_by(InsightSession.created_at.desc())
    if image_id is not None:
        stmt = stmt.where(InsightSession.image_id == image_id)
    return list(db.scalars(stmt))


@router.get("/sessions/{session_id}", response_model=InsightSessionDetailOut)
def get_session(session_id: uuid.UUID, db: Session = Depends(get_db)) -> InsightSession:
    session = db.get(InsightSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Insight session not found")
    message_rows = db.scalars(
        select(InsightMessage)
        .where(InsightMessage.session_id == session_id)
        .order_by(InsightMessage.created_at)
    )
    messages = [InsightMessageOut.model_validate(m) for m in message_rows]
    return InsightSessionDetailOut(
        **InsightSessionOut.model_validate(session).model_dump(),
        messages=messages,
    )
