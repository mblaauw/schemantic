"""layer-cake: stacked layers, top to bottom, with optional rails on the left and right for concerns that touch
every layer. A layer lays its cards out in one row by default."""
from __future__ import annotations

from . import Archetype, GridSpec, error, side_track

# Rail width as a share of the body, per layout.rail_width (clamped by side_track).
RAIL_SHARE = {"narrow": 15, "normal": 19, "wide": 25}


class LayerCake(Archetype):
    name = "layer-cake"
    required = frozenset({"layers"})
    allowed = frozenset({"layers", "left", "right", "chips_at", "rail_width"})

    def validate(self, spec: dict) -> list[dict]:
        """A card's `layer` names a layer, sits in a rail, and the rail's layered cards go top to bottom."""
        lay, out = spec["layout"], []
        rails = {lay.get("left"), lay.get("right")} - {None}
        for p in spec["panels"]:
            order = []
            for i, c in enumerate(p.get("cards", [])):
                if not c.get("layer"):
                    continue
                where = c.get("id") or f"{p['id']}.card{i}"
                if p["id"] not in rails:
                    out.append(error("layout", where, "only a rail's cards take a layer"))
                elif c["layer"] not in lay["layers"]:
                    out.append(error("layout", where, f"layer '{c['layer']}' is not one of {', '.join(lay['layers'])}"))
                else:
                    order.append((lay["layers"].index(c["layer"]), where))
            for (a, _), (b, where) in zip(order, order[1:], strict=False):
                if b < a:
                    out.append(error("layout", where, "a rail's cards follow the layers top to bottom; move this card up"))
        return out

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
