"""swimlane: who does what, in which order. One lane per actor (a panel, its name on the left), steps as cards in
phase columns that line up across lanes, handoffs as flows between cards. A band of phase names runs on top."""
from __future__ import annotations

from ..findings import finding
from . import Archetype, GridSpec


class Swimlane(Archetype):
    name = "swimlane"
    required = frozenset({"lanes"})
    allowed = frozenset({"lanes", "columns", "chips_at"})

    @staticmethod
    def width(spec: dict) -> int:
        """Number of step columns: the phases, or the longest lane."""
        lay = spec["layout"]
        lanes = [p for p in spec["panels"] if p["id"] in lay["lanes"]]
        longest = max([max([c.get("col", 0) for c in p.get("cards", [])] + [len(p.get("cards", []))]) for p in lanes] or [1])
        return len(lay.get("columns", [])) or longest

    def validate(self, spec: dict) -> list[dict]:
        out, ncols = [], len(spec["layout"].get("columns", []))
        for p in spec["panels"]:
            if p["id"] not in spec["layout"]["lanes"]:
                continue
            cols = [c["col"] for c in p.get("cards", []) if c.get("col")]
            if ncols and any(col > ncols for col in cols):
                out.append(finding("layout", p["id"], f"a step's col is beyond the {ncols} columns in layout.columns"))
            for col in sorted({c for c in cols if cols.count(c) > 1}):
                out.append(finding("layout", p["id"], f"two steps in column {col} of one lane; a lane has one step per column"))
        return out

    def grid(self, spec: dict) -> GridSpec:
        lay = spec["layout"]
        rows = ([["_phases"]] if lay.get("columns") else []) + [[lane] for lane in lay["lanes"]]
        bands = {"_phases": lay["columns"]} if lay.get("columns") else {}
        return GridSpec(rows=rows, columns=["minmax(0, 1fr)"], bands=bands)

    def panel_defaults(self, spec: dict, panel: dict) -> dict:
        if panel["id"] in spec["layout"]["lanes"]:
            return {"lane": True, "card_columns": self.width(spec)}
        return {}


ARCHETYPE = Swimlane()
