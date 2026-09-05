"""Runs a single volatility3 plugin against a memory image and returns JSON.

This is the one integration point everything else in the service calls through
(a synchronous smoke test, pytest, and the Celery task all call `run_plugin`
identically) — see volatility3/doc/source/using-as-a-library.rst and
`construct_plugin` (volatility3/volatility3/framework/plugins/__init__.py:18)
for the pattern this mirrors.

A fresh `Context()` is created per call rather than reused across jobs:
`Context` reuse across unrelated images isn't a documented/tested volatility3
pattern, and a Celery worker process handles one job at a time regardless.
`framework.import_files` is idempotent (it checks `sys.modules`), so repeating
it per call is cheap after the first.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Optional

import volatility3.plugins
from volatility3 import framework
from volatility3.framework import automagic, constants, contexts, exceptions, interfaces
from volatility3.framework import plugins as vol_plugins
from volatility3.framework.configuration import requirements

from . import config_binding
from .discovery import get_plugin_class
from .exceptions import MissingParametersError
from .file_handler import file_handler_class
from .json_renderer import render_grid


@dataclass
class RunResult:
    data: list[dict]
    columns: list[str]
    files: list[str] = field(default_factory=list)


def run_plugin(
    image_path: str,
    plugin_name: str,
    params: dict[str, Any],
    output_dir: str,
    progress_cb: Optional[constants.ProgressCallback] = None,
) -> RunResult:
    plugin_cls = get_plugin_class(plugin_name)  # raises PluginNotFoundError

    ctx = contexts.Context()
    framework.import_files(volatility3.plugins, True)

    ctx.config[
        "automagic.LayerStacker.single_location"
    ] = requirements.URIRequirement.location_from_file(image_path)

    automagics = automagic.choose_automagic(automagic.available(ctx), plugin_cls)

    plugin_config_path = interfaces.configuration.path_join(
        "plugins", plugin_cls.__name__
    )
    config_binding.bind_params(ctx, plugin_config_path, plugin_cls, params)

    try:
        constructed = vol_plugins.construct_plugin(
            ctx,
            automagics,
            plugin_cls,
            "plugins",
            progress_cb,
            file_handler_class(output_dir),
        )
    except exceptions.UnsatisfiedException as exc:
        raise MissingParametersError.from_unsatisfied(exc.unsatisfied) from exc

    grid = constructed.run()
    data, columns = render_grid(grid)

    files = sorted(_list_output_files(output_dir))
    return RunResult(data=data, columns=columns, files=files)


def _list_output_files(output_dir: str) -> list[str]:
    if not os.path.isdir(output_dir):
        return []
    return [
        name
        for name in os.listdir(output_dir)
        if not name.startswith("tmp_") and os.path.isfile(os.path.join(output_dir, name))
    ]
