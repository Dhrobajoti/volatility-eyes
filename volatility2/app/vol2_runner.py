# -*- coding: utf-8 -*-
"""Thin subprocess wrapper around volatility2's own vol.py CLI.

volatility2 was never designed as an importable library the way volatility3
is (no `using-as-a-library` equivalent, no requirements-introspection API) -
shelling out to its actual CLI is the correct integration point here, not a
workaround. Confirmed the exact commands/output shape by running them
directly against a real memory image before writing this wrapper.
"""
from __future__ import print_function

import re

# subprocess32 is the Python-3-subprocess backport - stdlib subprocess on
# Python 2.7 has no `timeout=` support on communicate() at all, which matters
# here since a runaway vol.py invocation shouldn't be able to hang this
# service indefinitely.
import subprocess32 as subprocess

VOL2_SCRIPT = "/opt/volatility2/vol.py"
DEFAULT_TIMEOUT_SECONDS = 600

PROFILE_LINE_RE = re.compile(r"Suggested Profile\(s\)\s*:\s*(.+)")
INSTANTIATED_RE = re.compile(r"\(Instantiated with [^)]*\)")

# volatility2 prints one "*** Failed to import ..." line per optional plugin
# module whose dependency isn't installed (some are simply unsupported on
# this OS/Python combo, e.g. mac-only plugins) - this is expected noise, not
# a real error, and would otherwise dominate every response.
NOISE_LINE_RE = re.compile(r"^\*\*\* Failed to import")


class Vol2Error(Exception):
    pass


def _run(args, timeout=DEFAULT_TIMEOUT_SECONDS):
    cmd = ["python", VOL2_SCRIPT] + args
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    try:
        out, _ = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.communicate()
        raise Vol2Error("volatility2 timed out after {0}s running: {1}".format(timeout, " ".join(args)))
    text = out.decode("utf-8", "replace")
    lines = [ln for ln in text.split("\n") if not NOISE_LINE_RE.match(ln)]
    return "\n".join(lines).strip(), proc.returncode


def identify(image_path):
    """Runs imageinfo and parses the suggested profile list."""
    output, _returncode = _run(["-f", image_path, "imageinfo"])
    match = PROFILE_LINE_RE.search(output)
    if not match:
        return {"profiles": [], "raw": output}
    cleaned = INSTANTIATED_RE.sub("", match.group(1))
    profiles = [p.strip() for p in cleaned.split(",") if p.strip()]
    return {"profiles": profiles, "raw": output}


def run_plugin(image_path, profile, plugin_name, extra_args=None):
    args = ["-f", image_path, "--profile=" + profile, plugin_name]
    if extra_args:
        args.extend(extra_args)
    output, returncode = _run(args)
    return {"output": output, "returncode": returncode}
