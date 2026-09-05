"""Exceptions raised by the vol_service wrapper layer.

These are plain Python exceptions with no FastAPI/Celery dependency, so the API
layer (or any other caller) is responsible for translating them into the
appropriate transport-specific error (HTTP status code, task failure, etc).
"""

from __future__ import annotations

from typing import Any


class VolServiceError(Exception):
    """Base class for all vol_service errors."""


class PluginNotFoundError(VolServiceError):
    def __init__(self, plugin_name: str):
        super().__init__(f"No such plugin: {plugin_name}")
        self.plugin_name = plugin_name


class MissingParametersError(VolServiceError):
    """Raised when volatility3 reports unsatisfied requirements for a plugin run.

    Wraps `exceptions.UnsatisfiedException.unsatisfied` (a dict of config-path ->
    RequirementInterface) into a list of field-level errors that a web API can
    turn directly into a 422 response.
    """

    def __init__(self, field_errors: list[dict[str, Any]]):
        super().__init__(
            "Missing or unsatisfied parameters: "
            + ", ".join(f["name"] for f in field_errors)
        )
        self.field_errors = field_errors

    @classmethod
    def from_unsatisfied(cls, unsatisfied: dict) -> "MissingParametersError":
        field_errors = []
        for config_path, requirement in unsatisfied.items():
            field_errors.append(
                {
                    "name": requirement.name,
                    "config_path": config_path,
                    "description": requirement.description,
                }
            )
        return cls(field_errors)
