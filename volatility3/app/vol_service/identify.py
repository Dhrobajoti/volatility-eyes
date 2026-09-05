"""Cheap OS identification for an uploaded memory image.

Runs *only* the LayerStacker automagic (not the OS-specific symbol-table
automagics like KernelPDBScanner/LinuxSymbolFinder/MacSymbolFinder) against a
bare probe that just needs a "primary" translation layer. This is the same
layer-stacking step every plugin run does first, but stopped before any
kernel-symbol/PDB resolution - confirmed empirically to take ~2-5s on a
~500MB image with no network access, vs. 30-90s+ for a full plugin run that
also downloads/parses the OS's symbol table.

Windows/Linux/Mac stacker classes (windows.py/linux.py/mac.py in
volatility3/framework/automagic/) each produce a differently-named layer
class (e.g. WindowsIntelPAE / LinuxIntel32e / MacIntel) when they recognize
the image; Linux/Mac stackers additionally set layer.metadata["os"], Windows'
does not (confirmed by direct testing) - so this checks both the metadata and
the layer class name/module for the OS name, rather than relying on either
alone.

Detection can fail to identify Linux/Mac images if no matching kernel banner
is present in the local symbol cache (the same bundled/cached-ISF dependency
that affects running any Linux/Mac plugin) - this is a real limitation, not a
bug in this module. On failure, os_hint is simply left unset and the user can
still browse/run any plugin manually.
"""

from __future__ import annotations

from typing import Optional

import volatility3.plugins
from volatility3 import framework
from volatility3.framework import automagic, constants, contexts, interfaces
from volatility3.framework.configuration import requirements


class _IdentifyProbe(interfaces.configuration.ConfigurableInterface):
    """Minimal ConfigurableInterface requiring only a primary translation layer."""

    @classmethod
    def get_requirements(cls):
        return [
            requirements.TranslationLayerRequirement(
                name="primary", description="primary layer"
            )
        ]


def identify_os(image_path: str) -> Optional[str]:
    """Returns "windows" | "linux" | "mac", or None if undetermined."""
    ctx = contexts.Context()
    framework.import_files(volatility3.plugins, True)

    ctx.config[
        "automagic.LayerStacker.single_location"
    ] = requirements.URIRequirement.location_from_file(image_path)

    automagics = automagic.available(ctx)
    stacker_only = [
        a for a in automagics if type(a).__name__ in ("LayerStacker", "ConstructionMagic")
    ]

    automagic.run(stacker_only, ctx, _IdentifyProbe, "identify")

    layer = ctx.layers.get("primary")
    if layer is None:
        return None

    metadata_os = (getattr(layer, "metadata", None) or {}).get("os")
    candidates = [metadata_os or "", type(layer).__name__, type(layer).__module__]
    haystack = " ".join(candidates).lower()

    for os_name in constants.OS_CATEGORIES:  # ["windows", "mac", "linux"]
        if os_name in haystack:
            return os_name
    return None
