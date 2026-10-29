"""hub-and-spokes: one framed central panel with up to four spokes above, four below, and one on each side.

Each spoke row is its own grid in one body cell, so a row divides the hub's width evenly whatever the other row
holds. Side spokes span every row and are as wide as one spoke of the fuller row."""
from __future__ import annotations

from . import Archetype, GridSpec, error, side_track


class HubAndSpokes(Archetype):
    name = "hub-and-spokes"
    required = frozenset({"hub"})
    allowed = frozenset({"hub", "top", "bottom", "left", "right", "chips_at"})

    def validate(self, spec: dict) -> list[dict]:
        if len(self.placed(spec)) < 3:
            return [error("layout", "layout.hub", "a hub needs at least two spokes (top, bottom, left, right)")]
        return []

    @staticmethod
    def groups(spec: dict) -> dict[str, list[str]]:
        # Group names start with '_', which a panel id cannot.
        lay = spec["layout"]
        return {g: lay[k] for g, k in (("_top", "top"), ("_bottom", "bottom")) if lay.get(k)}

    def grid(self, spec: dict) -> GridSpec:
        lay = spec["layout"]
        groups = self.groups(spec)
        rows = ([["_top"]] if "_top" in groups else []) + [[lay["hub"]]] + ([["_bottom"]] if "_bottom" in groups else [])
        sides = [bool(lay.get("left")), bool(lay.get("right"))]
        left, right = ([lay["left"]] if sides[0] else []), ([lay["right"]] if sides[1] else [])
        rows = [left + row + right for row in rows]
        # With n spokes in a row, a spoke is (H - (n-1)·gutter)/n of the hub width H. Solving for the side width S
        # against the body width (100%) gives S = f·100% + k·gutter, so CSS does the arithmetic with the gutter
        # token and the gutters inside the body are counted. n is at least 2, so a lone spoke never makes the
        # side as wide as the hub.
        n, ns = max(len(lay.get("top", [])), len(lay.get("bottom", [])), 2), sum(sides)
        a, b = 1 / n, (n - 1) / n          # spoke = a·H - b·gutter
        f = a / (1 + ns * a)
        k = f * (ns * b - ns) - b
        side = side_track(spec, f"calc({f * 100:.4f}% + {k:.4f} * var(--gutter-x))")
        columns = [side] * sides[0] + ["minmax(0, 1fr)"] + [side] * sides[1]
        return GridSpec(rows=rows, columns=columns, groups=groups)

    def panel_defaults(self, spec: dict, panel: dict) -> dict:
        if panel["id"] == spec["layout"]["hub"]:
            return {"hub": True}
        if any(panel["id"] in ids for ids in self.groups(spec).values()):
            return {"nested": True}  # placed by its spoke row's grid, not by a body grid area
        return {}


ARCHETYPE = HubAndSpokes()
