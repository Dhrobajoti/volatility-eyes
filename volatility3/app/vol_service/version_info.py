"""Best-effort OS version string, for display only (not used for plugin
filtering - see module docstring in identify.py for why per-plugin version
compatibility isn't something volatility3 exposes generically).

Unlike `identify_os` (cheap, layer-stacking only), this runs a real plugin
(`windows.info.Info`) - the closest volatility3 analog to volatility2's
`imageinfo` - which means it pays the full automagic/PDB-download cost
(30-90s on a cold symbol cache, fast once cached). Only implemented for
Windows: Linux/Mac kernel banners are exact version strings on their own
(e.g. "Linux version 5.4.0...") captured for free during identification, but
extracting them was left for a follow-up rather than shipped unverified
without a Linux/Mac sample to test against.
"""

from __future__ import annotations

import tempfile
from typing import Optional

from .runner import run_plugin


def get_windows_version(image_path: str) -> Optional[str]:
    with tempfile.TemporaryDirectory() as output_dir:
        try:
            result = run_plugin(image_path, "windows.info.Info", {}, output_dir)
        except Exception:
            return None

    fields = {row.get("Variable"): row.get("Value") for row in result.data}

    # NtMajorVersion/NtMinorVersion (from KUSER_SHARED_DATA) are the real "5.1"
    # style OS version. Deliberately NOT using the plugin's own "Major/Minor"
    # row - that one is read from the KD version block, where MajorVersion is
    # actually a debug-protocol flag byte (typically 15) and MinorVersion is
    # the build number, not a version number - confirmed empirically against
    # a WinXP SP3 image (Major/Minor = "15.2600", NtMajorVersion/Minor = "5.1").
    major = fields.get("NtMajorVersion")
    minor = fields.get("NtMinorVersion")
    csd_version = fields.get("CSDVersion")
    build_lab = fields.get("NTBuildLab")

    parts = []
    if major and minor:
        parts.append(f"{major}.{minor}")
    if csd_version and csd_version.strip("0").strip() not in ("", "None"):
        parts.append(f"SP{csd_version}")
    if build_lab:
        parts.append(f"(Build {build_lab.split('.')[0]})")

    return " ".join(parts) if parts else build_lab or None
