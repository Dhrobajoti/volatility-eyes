"""Maps volatility3 RequirementInterface objects to JSON-serializable form fields.

Mirrors `populate_requirements_argparse` in
volatility3/volatility3/cli/__init__.py:876 field-for-field: only the same
requirement types the CLI turns into `--flags` are turned into form fields here.
Everything else (ModuleRequirement, VersionRequirement,
TranslationLayerRequirement, SymbolTableRequirement, PluginRequirement, ...) is
skipped, because those are satisfied by automagic once an image is selected and
were never CLI-visible either (see the `else: continue` in the source).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from volatility3.framework import interfaces
from volatility3.framework.configuration import requirements


@dataclass
class ParamField:
    name: str
    type: str  # "integer" | "string" | "boolean" | "bytes" | "array" | "enum"
    required: bool
    description: str
    default: Any = None
    # only for type == "array"
    item_type: Optional[str] = None
    min_elements: Optional[int] = None
    max_elements: Optional[int] = None
    # only for type == "enum"
    choices: Optional[list[str]] = None


_SIMPLE_TYPE_NAMES = {
    bool: "boolean",
    int: "integer",
    str: "string",
    bytes: "bytes",
}


def to_field(requirement: interfaces.configuration.RequirementInterface) -> Optional[ParamField]:
    if isinstance(requirement, interfaces.configuration.SimpleTypeRequirement):
        if isinstance(requirement, requirements.BooleanRequirement):
            type_name = "boolean"
        else:
            type_name = _SIMPLE_TYPE_NAMES.get(requirement.instance_type, "string")
        return ParamField(
            name=requirement.name,
            type=type_name,
            required=not requirement.optional,
            description=requirement.description,
            default=requirement.default,
        )

    if isinstance(requirement, requirements.ListRequirement):
        item_type = _SIMPLE_TYPE_NAMES.get(requirement.element_type, "string")
        return ParamField(
            name=requirement.name,
            type="array",
            required=not requirement.optional,
            description=requirement.description,
            default=requirement.default,
            item_type=item_type,
            min_elements=requirement.min_elements,
            max_elements=requirement.max_elements or None,
        )

    if isinstance(requirement, requirements.ChoiceRequirement):
        return ParamField(
            name=requirement.name,
            type="enum",
            required=not requirement.optional,
            description=requirement.description,
            default=requirement.default,
            choices=list(requirement.choices),
        )

    # ModuleRequirement / VersionRequirement / TranslationLayerRequirement /
    # SymbolTableRequirement / PluginRequirement / MultiRequirement / anything
    # else: not user-facing, satisfied by automagic or plugin composition.
    return None
