"""capability-map: what we have, and where the gaps are. One row per domain, its name on the left, capabilities as
cards in columns that line up down the plate. `status` carries the assessment (planned is a gap, deprecated is on its
way out), so a reader scans the map without arrows."""
from __future__ import annotations

from . import Archetype, GridSpec


class CapabilityMap(Archetype):
    name = "capability-map"
    required = frozenset({"domains"})
    allowed = frozenset({"domains", "per_row", "chips_at"})

    def placed(self, spec: dict) -> list[str]:
        return spec["layout"]["domains"]

    def width(self, spec: dict) -> int:
        lay = spec["layout"]
        return lay.get("per_row") or max(len(p.get("cards", [])) for p in spec["panels"] if p["id"] in lay["domains"])

    def grid(self, spec: dict) -> GridSpec:
        return GridSpec(rows=[[d] for d in spec["layout"]["domains"]], columns=["minmax(0, 1fr)"])

    def standalone(self, spec: dict) -> set[str]:
        return set(spec["layout"]["domains"])

    def panel_defaults(self, spec: dict, panel: dict) -> dict:
        return {"lane": True, "card_columns": self.width(spec)} if panel["id"] in spec["layout"]["domains"] else {}


ARCHETYPE = CapabilityMap()
