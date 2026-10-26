"""column-flow: a path the reader follows left to right, with optional rows underneath. The author names the
grid cells, like CSS grid-template-areas; a panel may span cells as long as it forms a rectangle."""
from __future__ import annotations

from . import Archetype, GridSpec, error

MAX_COLUMNS = 5


class ColumnFlow(Archetype):
    name = "column-flow"
    required = frozenset({"areas"})
    allowed = frozenset({"areas", "column_widths", "row_heights", "chips_at"})

    def placed(self, spec: dict) -> list[str]:
        return []  # cells repeat ids on purpose; placement is checked from the grid

    def validate(self, spec: dict) -> list[dict]:
        rows = [row.split() for row in spec["layout"]["areas"]]
        widths = {len(r) for r in rows}
        if len(widths) != 1:
            return [error("layout", "layout.areas", f"every row needs the same number of cells, got {sorted(widths)}")]
        out, ncols = [], widths.pop()
        if ncols > MAX_COLUMNS:
            out.append(error("budget", "layout.areas", f"{ncols} body columns; the budget is {MAX_COLUMNS}. Split the plate."))
        cw = spec["layout"].get("column_widths")
        if cw and len(cw) != ncols:
            out.append(error("layout", "layout.column_widths", f"{len(cw)} widths for {ncols} columns"))
        return out

    def grid(self, spec: dict) -> GridSpec:
        lay = spec["layout"]
        rows = [row.split() for row in lay["areas"]]
        widths = lay.get("column_widths") or [1] * len(rows[0])
        return GridSpec(rows=rows, columns=[f"minmax(0, {w}fr)" for w in widths])


ARCHETYPE = ColumnFlow()
