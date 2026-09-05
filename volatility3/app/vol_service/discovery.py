"""Plugin discovery for volatility3.

Wraps `framework.import_files` + `framework.list_plugins()` behind a small,
process-local cache: import_files walks the filesystem importing every plugin
module so PluginInterface subclasses register themselves, which is not free to
repeat on every request.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Optional

import volatility3.plugins
from volatility3 import framework
from volatility3.framework import constants, interfaces

from .exceptions import PluginNotFoundError
from .requirement_schema import ParamField, to_field

_lock = threading.Lock()
_plugins: Optional[dict[str, type]] = None


@dataclass
class PluginSummary:
    name: str
    os: Optional[str]
    description: str


@dataclass
class PluginSchema:
    name: str
    os: Optional[str]
    description: str
    fields: list[ParamField] = field(default_factory=list)


def _os_category(plugin_cls: type) -> Optional[str]:
    categories = plugin_cls.__module__.split(".")
    for os_name in constants.OS_CATEGORIES:
        if os_name in categories:
            return os_name
    return None


def _registry() -> dict[str, type]:
    """Builds (once per process) and returns the dotted-name -> plugin-class map."""
    global _plugins
    if _plugins is None:
        with _lock:
            if _plugins is None:
                framework.require_interface_version(2, 0, 0)
                framework.import_files(volatility3.plugins, True)
                _plugins = dict(framework.list_plugins())
    return _plugins


def refresh_plugin_registry() -> None:
    """Forces a rebuild of the plugin registry on next access."""
    global _plugins
    with _lock:
        _plugins = None


def list_plugins() -> list[PluginSummary]:
    registry = _registry()
    return [
        PluginSummary(
            name=name,
            os=_os_category(cls),
            description=(cls.__doc__ or "").strip(),
        )
        for name, cls in sorted(registry.items())
    ]


def get_plugin_class(plugin_name: str) -> type[interfaces.plugins.PluginInterface]:
    registry = _registry()
    plugin_cls = registry.get(plugin_name)
    if plugin_cls is None:
        raise PluginNotFoundError(plugin_name)
    return plugin_cls


def get_plugin_schema(plugin_name: str) -> PluginSchema:
    plugin_cls = get_plugin_class(plugin_name)
    fields = [
        f
        for f in (to_field(requirement) for requirement in plugin_cls.get_requirements())
        if f is not None
    ]
    return PluginSchema(
        name=plugin_name,
        os=_os_category(plugin_cls),
        description=(plugin_cls.__doc__ or "").strip(),
        fields=fields,
    )
