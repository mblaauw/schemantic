"""layer-cake: stacked layers, top to bottom, with optional rails on the left and right for concerns that touch
every layer. A layer lays its cards out in one row by default."""
from __future__ import annotations

from . import Archetype, GridSpec, side_track

# Rail width as a share of the body, per layout.rail_width (clamped by side_track).
RAIL_SHARE = {"narrow": 15, "normal": 19, "wide": 25}


class LayerCake(Archetype):
    name = "layer-cake"
    required = frozenset({"layers"})
    allowed = frozenset({"layers", "left", "right", "chips_at", "rail_width"})

    def grid(self, spec: dict) -> GridSpec:
        lay = spec["layout"]
        sides = [bool(lay.get("left")), bool(lay.get("right"))]
        left, right = ([lay["left"]] if sides[0] else []), ([lay["right"]] if sides[1] else [])
        rows = [left + [layer] + right for layer in lay["layers"]]
        rail = side_track(spec, f"{RAIL_SHARE[lay.get('rail_width', 'normal')]}%")
        columns = [rail] * sides[0] + ["minmax(0, 1fr)"] + [rail] * sides[1]
        return GridSpec(rows=rows, columns=columns)

    def panel_defaults(self, spec: dict, panel: dict) -> dict:
        if panel["id"] in spec["layout"]["layers"] and panel.get("cards") and not panel.get("card_columns"):
            return {"card_columns": len(panel["cards"])}
        return {}


ARCHETYPE = LayerCake()
