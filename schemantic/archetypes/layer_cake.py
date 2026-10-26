"""layer-cake: stacked layers, top to bottom, with optional rails on the left and right for concerns that touch
every layer. A layer lays its cards out in one row by default."""
from __future__ import annotations

from . import Archetype, GridSpec

# Rails are this share of a layer's width.
RAIL_WEIGHT = 0.22


class LayerCake(Archetype):
    name = "layer-cake"
    required = frozenset({"layers"})
    allowed = frozenset({"layers", "left", "right", "row_heights", "chips_at"})

    def grid(self, spec: dict) -> GridSpec:
        lay = spec["layout"]
        sides = [bool(lay.get("left")), bool(lay.get("right"))]
        left, right = ([lay["left"]] if sides[0] else []), ([lay["right"]] if sides[1] else [])
        rows = [left + [layer] + right for layer in lay["layers"]]
        rail = f"minmax(0, {RAIL_WEIGHT}fr)"
        columns = [rail] * sides[0] + ["minmax(0, 1fr)"] + [rail] * sides[1]
        return GridSpec(rows=rows, columns=columns)

    def panel_defaults(self, spec: dict, panel: dict) -> dict:
        if panel["id"] in spec["layout"]["layers"] and panel.get("cards") and not panel.get("card_columns"):
            return {"card_columns": len(panel["cards"])}
        return {}


ARCHETYPE = LayerCake()
