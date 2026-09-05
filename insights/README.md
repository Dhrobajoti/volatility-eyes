# insights

The optional LLM-based "first look" analysis service. Runs a small local
model via [Ollama](https://ollama.com) to summarize a memory image's triage
plugin output for an investigator, and (planned, not yet built) answer
follow-up questions in a chat interface.

## Optional by design

This service, and its `ollama` dependency, are gated behind the Compose
**`insights` profile** - `docker compose up` never starts them. To run with
Insights enabled:

```bash
docker compose --profile insights up -d --build
docker compose exec ollama ollama pull qwen2.5:3b-instruct   # first time only
```

Nothing else in the stack depends on these two containers being up. The
backend's `/api/insights/health` route reports reachability, and the
frontend hides the Insights UI (or shows a clear "unavailable" state)
whenever it isn't reachable - this is a real requirement, not a nicety:
Ollama/an LLM is comparatively resource-hungry, and an investigator on a
constrained machine should be able to run the rest of the tool with zero
extra CPU/RAM/disk cost from this feature.

## Design: why this service is stateless

All orchestration - which plugins to run, gathering their results, deciding
what's "baseline" for the image's OS, persisting the conversation - lives in
the main `backend`/`worker`, exactly the same code path as a human clicking
"Run" on a plugin. This service does exactly one thing: given an
already-assembled context, produce grounded text. That split is deliberate:
- The AI never gets its own separate way to run a volatility3 plugin - every
  plugin it triggers is a completely normal `Job` row (tagged
  `triggered_by="insight_session:<id>"` so it's distinguishable in the UI),
  subject to the exact same validation and tracking as anything a human
  clicks.
- If this service is ever swapped for a hosted API (Claude/OpenAI) instead
  of a local model, nothing about session/job persistence has to change.

## Current contract

`GET /health` -> `{"status": "ok"}`

`POST /summarize`
```json
{
  "image": {"filename": "...", "os_hint": "windows", "os_version": "5.1 SP3 (Build 2600)"},
  "plugin_results": [
    {"plugin_name": "windows.pslist.PsList", "row_count": 17, "shown_rows": [...], "truncated": false},
    {"plugin_name": "windows.malfind.Malfind", "error": "plugin run failed"}
  ]
}
```
->
```json
{"summary": "...", "model_used": "qwen2.5:3b-instruct"}
```

`plugin_results` rows are pre-trimmed by the volatility3 service (see
`volatility3/app/insights/baseline.py`) before they ever reach this service -
capped row counts and truncated long string fields, so a small model's
context window isn't blown out by, say, a 4000-row filescan dump.

## Grounding

The system prompt (`app/prompt.py`) explicitly forbids inventing facts not
present in the supplied plugin data, and requires every claim to name the
specific plugin/PID/offset it's based on. This is enforced by prompting, not
by code - it is not a hard guarantee. The backend additionally stores which
job IDs contributed to each summary, so the UI can render "based on: ->
pslist job, malfind job" links regardless of whether the model's own prose
cites them well.

## Model

Default: `qwen2.5:3b-instruct` (fast enough for CPU-only inference, no GPU
required). Override via the `OLLAMA_MODEL` env var if you have more
resources available and want better analysis quality - anything Ollama
serves with chat support works.

## Not yet built

- The chat/follow-up-question interface (tool-calling loop letting the model
  request additional plugin runs from a curated safe allow-list).
- Linux/Mac baseline bundles are defined but unverified - no Linux/Mac
  sample was available to confirm the plugin output shape against.
- A hosted-API backend option (the original stub's `backend: "local"|"hosted"`
  toggle) - local-only for now, which is also the right default for real
  casework (case data never leaves the machine).
