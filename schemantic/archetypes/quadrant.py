"""quadrant: where each thing sits on two axes. Four panels in a two-by-two, a label for each half of each axis; the
position is the meaning, so arrows are optional."""
from __future__ import annotations

from . import Archetype, GridSpec


class Quadrant(Archetype):
    name = "quadrant"
    required = frozenset({"cells", "x", "y"})
    allowed = frozenset({"cells", "x", "y", "chips_at"})
    legend_roles = False

    def placed(self, spec: dict) -> list[str]:
        return spec["layout"]["cells"]

    def grid(self, spec: dict) -> GridSpec:
        lay = spec["layout"]
        (a, b, c, d), (high, low) = lay["cells"], lay["y"]
        return GridSpec(rows=[[".", "_x", "_x"], ["_high", a, b], ["_low", c, d]],
                        columns=["var(--axis-width)", "minmax(0, 1fr)", "minmax(0, 1fr)"],
                        bands={"_x": lay["x"], "_high": [high], "_low": [low]})

    def standalone(self, spec: dict) -> set[str]:
        return set(spec["layout"]["cells"])

    def panel_defaults(self, spec: dict, panel: dict) -> dict:
        return {"cell": True, "role": "frame"} if panel["id"] in spec["layout"]["cells"] else {}


ARCHETYPE = Quadrant()
