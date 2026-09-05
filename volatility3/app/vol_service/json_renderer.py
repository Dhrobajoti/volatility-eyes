"""A headless adaptation of volatility3's JsonRenderer.

`JsonRenderer` (volatility3/volatility3/cli/text_renderer.py:535) already does
all the TreeGrid-walking work; the only CLI-specific behaviour is that
`render()` writes to `sys.stdout` via `output_result`. Overriding
`output_result` to capture the value instead is enough to reuse it headlessly.

Two things the CLI normally does for you that we must do ourselves here:
- `renderer.filter` is read by `render()` but is not set by the base
  `Renderer` interface — the CLI only assigns it externally
  (`cli/__init__.py:525`). Without setting it, every call raises
  `AttributeError: 'HeadlessJsonRenderer' object has no attribute 'filter'`.
- `get_render_options()` is a no-op here since there's no interactive renderer
  selection to configure.

`JsonRenderer._type_renderers` (text_renderer.py:536) has no entry for
`format_hints.Hex`/`Bin`, unlike the CLI's own default text renderer
(text_renderer.py:239-241, `f"0x{x:x}"`) and `JsonLinesRenderer`
(text_renderer.py:631-633) - so offsets/addresses (which plugins tag with
`format_hints.Hex`, e.g. pslist's "Offset(V)" column) fall through to the
`"default"` passthrough and render as plain decimal integers instead of the
`0x...` form every forensics tool (including volatility2) uses. Added below
to match the CLI's own convention.
"""

from __future__ import annotations

from typing import Any

from volatility3.cli.text_renderer import JsonRenderer
from volatility3.framework import interfaces
from volatility3.framework.renderers import format_hints


def _hex_or_none(x: Any) -> str | None:
    return None if isinstance(x, interfaces.renderers.BaseAbsentValue) else f"0x{x:x}"


def _bin_or_none(x: Any) -> str | None:
    return None if isinstance(x, interfaces.renderers.BaseAbsentValue) else f"0b{x:b}"


class HeadlessJsonRenderer(JsonRenderer):
    _type_renderers = {
        **JsonRenderer._type_renderers,
        format_hints.Hex: _hex_or_none,
        format_hints.Bin: _bin_or_none,
    }

    def __init__(self) -> None:
        super().__init__()
        self.filter = None
        self.captured: Any = None

    def output_result(self, outfd, result) -> None:
        self.captured = result


def render_grid(grid: interfaces.renderers.TreeGrid) -> tuple[list[dict], list[str]]:
    """Renders a TreeGrid to nested JSON-able dicts, returning (data, column_names)."""
    renderer = HeadlessJsonRenderer()
    renderer.render(grid)
    columns = [column.name for column in grid.columns]
    return renderer.captured, columns
