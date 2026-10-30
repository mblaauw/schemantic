"""capability-map: what we have, and where the gaps are. One row per domain, its name on the left, its capabilities
sharing the row's width, so no row ends in a hole; `per_row` lines the columns up instead. `status` carries the
assessment (planned is a gap, deprecated is on its way out), so a reader scans the map without arrows. Colour stays out
of it: a domain is neither a platform nor data."""
from __future__ import annotations

from . import Archetype, GridSpec


class CapabilityMap(Archetype):
    name = "capability-map"
    required = frozenset({"domains"})
    allowed = frozenset({"domains", "per_row", "chips_at"})
    cards_are_things = False
    legend_roles = False
    legend_keys = {"status_new": "status_new_plain", "status_changed": "status_changed_plain"}

    def placed(self, spec: dict) -> list[str]:
        return spec["layout"]["domains"]

    def grid(self, spec: dict) -> GridSpec:
        return GridSpec(rows=[[d] for d in spec["layout"]["domains"]], columns=["minmax(0, 1fr)"])

    def standalone(self, spec: dict) -> set[str]:
        return set(spec["layout"]["domains"])

    def panel_defaults(self, spec: dict, panel: dict) -> dict:
        if panel["id"] not in spec["layout"]["domains"]:
            return {}
        return {"lane": True, "role": "frame", "keep_grid": True,
                "card_columns": spec["layout"].get("per_row") or max(len(panel.get("cards", [])), 1)}


ARCHETYPE = CapabilityMap()
