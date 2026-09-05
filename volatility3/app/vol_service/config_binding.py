"""Binds user-submitted parameter values into a volatility3 context's config.

Mirrors `populate_config` in volatility3/volatility3/cli/__init__.py:715, scoped
to a single plugin's own requirements (the automagic-satisfied requirements,
e.g. the image's TranslationLayerRequirement, are set separately by
`runner.py` via `automagic.LayerStacker.single_location`, not through this
function).
"""

from __future__ import annotations

import os
import pathlib
from typing import Any

from volatility3.framework import interfaces
from volatility3.framework.configuration import requirements


def bind_params(
    context: interfaces.context.ContextInterface,
    plugin_config_path: str,
    plugin_cls: type[interfaces.plugins.PluginInterface],
    params: dict[str, Any],
) -> None:
    for requirement in plugin_cls.get_requirements():
        if requirement.name not in params:
            continue
        value = params[requirement.name]
        if value is None:
            continue

        if isinstance(requirement, requirements.URIRequirement) and isinstance(
            value, str
        ):
            value = _coerce_uri(value)

        if isinstance(requirement, requirements.ListRequirement):
            if not isinstance(value, list):
                raise TypeError(
                    f"Configuration for ListRequirement was not a list: {requirement.name}"
                )
            value = [requirement.element_type(x) for x in value]

        extended_path = interfaces.configuration.path_join(
            plugin_config_path, requirement.name
        )
        context.config[extended_path] = value


def _coerce_uri(value: str) -> str:
    """Turns a bare filesystem path into a `file://` URI, leaving real URIs alone."""
    from urllib.parse import urlparse

    scheme = urlparse(value).scheme
    if scheme and len(scheme) > 1:
        return value
    if not os.path.exists(value):
        raise FileNotFoundError(f"Non-existent file {value} passed to URIRequirement")
    return pathlib.Path(os.path.abspath(value)).as_uri()
