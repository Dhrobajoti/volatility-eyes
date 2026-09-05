"""The optional LLM-analysis microservice - see README.md for the full
contract and design rationale. Deliberately stateless: all persistence
(sessions, messages, job history) lives in the main backend's Postgres; this
service only ever receives a fully-assembled context and returns text.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from . import ollama_client
from .prompt import build_messages

app = FastAPI(title="Volatility Eyes Insights")


class SummarizeRequest(BaseModel):
    image: dict[str, Any]
    plugin_results: list[dict[str, Any]]
    # "baseline" (default, whole-image first-look) or "single_job" (focused
    # anomaly/flag-point read of one already-run job's output).
    mode: str = "baseline"


class SummarizeResponse(BaseModel):
    summary: str
    model_used: str


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/summarize", response_model=SummarizeResponse)
def summarize(body: SummarizeRequest) -> SummarizeResponse:
    messages = build_messages(body.image, body.plugin_results, mode=body.mode)
    try:
        content = ollama_client.chat(messages)
    except ollama_client.OllamaError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return SummarizeResponse(summary=content, model_used=ollama_client.OLLAMA_MODEL)
