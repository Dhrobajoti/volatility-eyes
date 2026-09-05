from __future__ import annotations

import os
from typing import Any

import httpx

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://ollama:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:3b-instruct")
OLLAMA_TIMEOUT_SECONDS = float(os.environ.get("OLLAMA_TIMEOUT_SECONDS", "280"))

# Confirmed by hitting both of these blind on first real end-to-end test:
# - num_ctx: Ollama defaults to a 2048-token context regardless of what the
#   model actually supports, silently truncating anything longer (observed
#   in the ollama logs: "prompt processing, n_tokens = 2048" on a prompt that
#   was longer than that) - must be set explicitly per-request.
# - num_predict: with no cap, the model kept generating well past what a
#   "concise summary" prompt should produce (600+ tokens and climbing) and
#   blew through the request timeout entirely on CPU-only inference. Capped
#   to keep response time bounded on modest hardware; raise if using a
#   faster/GPU-backed setup and want longer analyses.
OLLAMA_NUM_CTX = int(os.environ.get("OLLAMA_NUM_CTX", "8192"))
OLLAMA_NUM_PREDICT = int(os.environ.get("OLLAMA_NUM_PREDICT", "450"))


class OllamaError(Exception):
    pass


def chat(messages: list[dict[str, str]]) -> str:
    try:
        with httpx.Client(timeout=OLLAMA_TIMEOUT_SECONDS) as client:
            resp = client.post(
                f"{OLLAMA_BASE_URL}/api/chat",
                json={
                    "model": OLLAMA_MODEL,
                    "messages": messages,
                    "stream": False,
                    "options": {"num_ctx": OLLAMA_NUM_CTX, "num_predict": OLLAMA_NUM_PREDICT},
                },
            )
    except httpx.HTTPError as exc:
        raise OllamaError(f"Could not reach Ollama at {OLLAMA_BASE_URL}: {exc}") from exc

    if resp.status_code == 404:
        raise OllamaError(
            f"Model '{OLLAMA_MODEL}' is not pulled yet. Run: "
            f"docker compose exec ollama ollama pull {OLLAMA_MODEL}"
        )
    if resp.is_error:
        raise OllamaError(f"Ollama returned {resp.status_code}: {resp.text[:500]}")

    body: dict[str, Any] = resp.json()
    content = body.get("message", {}).get("content")
    if not content:
        raise OllamaError(f"Unexpected Ollama response shape: {body}")
    return content
