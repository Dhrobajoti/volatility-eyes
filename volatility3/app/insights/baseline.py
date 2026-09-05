"""The fixed "first look" plugin bundle an Insight session runs before
asking the model for anything, plus trimming plugin output down to
something that fits in a small local model's context window.

Only the Windows bundle has been run against real images and had its output
checked. Linux/Mac bundles are the closest analog by plugin name/purpose but
are unverified - no Linux/Mac sample was available to confirm against
(the same honesty applied to OS-version detection elsewhere in vol_service).
"""

from __future__ import annotations

from typing import Any

BASELINE_BUNDLES: dict[str, list[str]] = {
    "windows": [
        "windows.pslist.PsList",
        "windows.pstree.PsTree",
        "windows.netscan.NetScan",
        "windows.malfind.Malfind",
        "windows.cmdline.CmdLine",
    ],
    "linux": [
        "linux.pslist.PsList",
        "linux.psaux.PsAux",
        "linux.sockstat.Sockstat",
        "linux.malware.malfind.Malfind",
    ],
    "mac": [
        "mac.pslist.PsList",
        "mac.psaux.Psaux",
        "mac.netstat.Netstat",
        "mac.malfind.Malfind",
    ],
}


def get_baseline_plugins(os_hint: str | None) -> list[str]:
    return BASELINE_BUNDLES.get(os_hint or "", [])


# volatility2 (legacy engine) baseline - used instead of BASELINE_BUNDLES when
# an image only works under v3's automagic fails outright (see
# generate_baseline_summary's engine-selection logic). All five are present
# in volatility2/app/catalog.py's curated PLUGIN_NAMES and, unlike v3, cover
# process listing/tree, network, injected-code, and command-line triage with
# plugins confirmed to actually run against XP/2003-era images.
LEGACY_BASELINE_PLUGINS = ["pslist", "pstree", "connscan", "malfind", "cmdline"]


# Kept intentionally small: this feeds a lightweight local model with a
# limited context window, and stuffing thousands of rows in both wastes the
# window on repetition and slows inference for no analytical benefit - a
# human skimming the same plugin output wouldn't read all 4000 filescan rows
# either, they'd look at the first page and drill in from there.
#
# These numbers are not arbitrary - the first real end-to-end test measured
# the naive version (40 rows/plugin, 300-char fields, pretty-printed JSON)
# at 12,976 prompt tokens, which took ~2 minutes just to *process* on CPU
# before generation even started, and the run failed on timeout entirely.
# Cut down hard in response to that measurement, not guessed in advance.
MAX_ROWS_PER_PLUGIN = 15
MAX_FIELD_CHARS = 120

# Raw hex/disassembly bytes are the biggest single offenders (a malfind row's
# Hexdump/Disasm can each run to hundreds of characters) and carry near-zero
# value for a *prose summary* - a language model gets nothing analytically
# useful out of a byte dump, and the volatility3 output already labels the
# region as suspicious via other fields (Protection, Tag, PID) that survive.
# Dropped here, not just truncated; can be reintroduced for a "explain this
# specific PID" follow-up in the future chat feature where it'd earn its cost.
DROPPED_FIELDS = {"Hexdump", "Disasm"}


def _truncate_value(value: Any) -> Any:
    if isinstance(value, str) and len(value) > MAX_FIELD_CHARS:
        return value[:MAX_FIELD_CHARS] + f"...[{len(value) - MAX_FIELD_CHARS} more chars]"
    return value


def _truncate_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        k: _truncate_value(v)
        for k, v in row.items()
        if k != "__children" and k not in DROPPED_FIELDS
    }


def trim_for_context(data: list[dict[str, Any]]) -> dict[str, Any]:
    """Returns {row_count, shown_rows, truncated} for one plugin's result."""
    flat: list[dict[str, Any]] = []

    def walk(nodes: list[dict[str, Any]]) -> None:
        for node in nodes:
            flat.append(node)
            children = node.get("__children") or []
            if children:
                walk(children)

    walk(data)

    shown = [_truncate_row(r) for r in flat[:MAX_ROWS_PER_PLUGIN]]
    return {
        "row_count": len(flat),
        "shown_rows": shown,
        "truncated": len(flat) > MAX_ROWS_PER_PLUGIN,
    }


# volatility2 plugins have no structured/JSON output (see
# storage/results.py's LEGACY_RESULT_FILENAME comment) - just the plugin's
# plain-text console output - so there's no row list to cap, only raw
# character length. 2000 chars is a rough token-budget analog to
# MAX_ROWS_PER_PLUGIN * MAX_FIELD_CHARS above (15 * 120 = 1800), not an
# independent guess.
MAX_TEXT_CHARS = 2000


def trim_text_for_context(text: str) -> dict[str, Any]:
    """Returns {text, truncated, total_chars} for one legacy plugin's output."""
    total_chars = len(text)
    truncated = total_chars > MAX_TEXT_CHARS
    return {
        "text": text[:MAX_TEXT_CHARS],
        "truncated": truncated,
        "total_chars": total_chars,
    }
