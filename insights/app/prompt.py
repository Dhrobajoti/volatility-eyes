"""Builds the prompt handed to the local model for a baseline "first look"
summary. Kept deliberately blunt about grounding: a model that's willing to
speculate freely is actively dangerous in a forensics tool, so the system
prompt repeats the "only from the data given" constraint more than once
rather than trusting one polite mention of it.
"""

from __future__ import annotations

import json
from typing import Any

SYSTEM_PROMPT = """You are assisting a digital forensics investigator who is reviewing a
memory image with Volatility (v3, or v2 "legacy engine" for older images v3 can't parse -
the IMAGE info below tells you which). You will be given the image's basic info and the
output of several triage plugins that have already been run. v2 plugin output is shown as
its raw console text rather than structured rows - read it the same way you'd read a
terminal transcript.

Your job: write a concise, plain-language "first look" summary an investigator can skim in
under a minute - aim for 150-250 words, as a short list of findings, not an essay. Call out
anything that looks unusual (unexpected parent/child process
relationships, processes with no matching image on disk, injected code, suspicious network
connections, unusual command lines) - but ONLY based on the data actually provided below.

Hard rules:
- Do not invent processes, PIDs, IPs, or facts that are not in the data given to you.
- If nothing in the data looks unusual, say so plainly rather than manufacturing a finding.
- When you reference something, name the specific plugin and identifier (PID, offset, etc.)
  it came from, so the investigator can look it up themselves.
- You are producing an investigative lead, not a verdict - do not use definitive language
  like "this is malware"; use "this is worth investigating" framing instead.
- Some plugin sections may be marked as truncated (only the first N rows shown) or as having
  failed to run - acknowledge that rather than treating the shown subset as exhaustive.
"""

# Used instead of SYSTEM_PROMPT for a per-job "Insights" request (the button
# beside "Export as Text" on a single completed job's result page) - a
# narrower ask than the whole-image baseline: look hard at ONE plugin's
# output for anomalies/flag-worthy indicators, not a broad first-look tour.
SYSTEM_PROMPT_SINGLE_JOB = """You are assisting a digital forensics investigator who is looking at
the output of ONE specific plugin run and wants a focused read of just that data, not a
broad overview of the whole image. You will be given the image's basic info and that one
plugin's output (volatility2/"legacy engine" output is shown as raw console text rather than
structured rows - read it the same way you'd read a terminal transcript).

Your job: point out anything in this specific output worth flagging for further
investigation - unusual values, suspicious indicators, or "capture the flag"-style artifacts
(e.g. odd strings, unexpected network endpoints or ports, injected-looking memory regions,
suspicious command lines, paths, or registry keys) - framed as leads to check, not
conclusions. Aim for 100-200 words as a short list; if there are several, rank the most
notable first.

Hard rules:
- Do not invent values that are not in the data given to you.
- If nothing stands out, say so plainly rather than manufacturing a finding.
- When you reference something, name the specific identifier (PID, offset, IP, port, path,
  etc.) from the data so the investigator can look it up themselves.
- You are producing an investigative lead, not a verdict - avoid definitive language like
  "this is malware"; use "this is worth investigating" framing instead.
- If the output is marked truncated, acknowledge that rather than treating the shown subset
  as exhaustive.
"""


def build_messages(
    image_info: dict[str, Any], plugin_results: list[dict[str, Any]], mode: str = "baseline"
) -> list[dict[str, str]]:
    system_prompt = SYSTEM_PROMPT_SINGLE_JOB if mode == "single_job" else SYSTEM_PROMPT
    results_label = "PLUGIN OUTPUT:" if mode == "single_job" else "TRIAGE PLUGIN RESULTS:"

    # Compact (no indent) on purpose: pretty-printing is pure token waste
    # here - the first real end-to-end test showed indent=2 alone contributing
    # heavily to a 12,976-token prompt that never finished processing in time.
    context_lines = [
        "IMAGE:",
        json.dumps(image_info),
        "",
        results_label,
    ]
    for entry in plugin_results:
        plugin_name = entry.get("plugin_name", "unknown")
        if "error" in entry:
            context_lines.append(f"\n## {plugin_name}\n(failed to run: {entry['error']})")
            continue
        if "text" in entry:
            # volatility2 (legacy engine) shape: plain console text, no row
            # structure - see volatility3/app/insights/baseline.py's
            # trim_text_for_context.
            total_chars = entry.get("total_chars", 0)
            truncated = entry.get("truncated", False)
            header = f"\n## {plugin_name} (volatility2 output, {total_chars} chars"
            header += ", truncated)" if truncated else ")"
            context_lines.append(header)
            context_lines.append(entry.get("text", ""))
            continue
        row_count = entry.get("row_count", 0)
        truncated = entry.get("truncated", False)
        shown = entry.get("shown_rows", [])
        header = f"\n## {plugin_name} ({row_count} total rows"
        header += f", showing first {len(shown)})" if truncated else ")"
        context_lines.append(header)
        context_lines.append(json.dumps(shown, default=str, separators=(",", ":")))

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "\n".join(context_lines)},
    ]
