"""nested-zones: where things run. Zones are labelled dashed frames (an account, a cluster, a namespace), nested up
to three levels, holding panels; panels outside every zone stand in a column beside them."""
from __future__ import annotations

from . import Archetype, GridSpec, error, side_track

MAX_DEPTH = 3


def walk(zones: list[dict], depth: int = 1):
    """(zone, depth) for every zone in the tree."""
    for z in zones:
        yield z, depth
        yield from walk(z.get("zones", []), depth + 1)


class NestedZones(Archetype):
    name = "nested-zones"
    required = frozenset({"zones"})
    allowed = frozenset({"zones", "outside", "chips_at"})

    def placed(self, spec: dict) -> list[str]:
        lay = spec["layout"]
        return [pid for z, _ in walk(lay["zones"]) for pid in z.get("panels", [])] + list(lay.get("outside", []))

    def validate(self, spec: dict) -> list[dict]:
        out, seen = [], set()
        for z, depth in walk(spec["layout"]["zones"]):
            if depth > MAX_DEPTH:
                out.append(error("layout", f"zone.{z['id']}",
                                 f"zones nest {depth} deep; at most {MAX_DEPTH} (an account, a cluster, a namespace)"))
            if z["id"] in seen:
                out.append(error("layout", f"zone.{z['id']}", f"two zones have id '{z['id']}'"))
            seen.add(z["id"])
            if not z.get("zones") and not z.get("panels"):
                out.append(error("layout", f"zone.{z['id']}", "an empty zone; give it panels or zones, or leave it out"))
        return out

    def grid(self, spec: dict) -> GridSpec:
        lay = spec["layout"]
        zoned = [pid for z, _ in walk(lay["zones"]) for pid in z.get("panels", [])]
        outside = list(lay.get("outside", []))
        rows = [["_zones"] + (["_outside"] if outside else [])]
        columns = ["minmax(0, 1fr)"] + ([side_track(spec, "20%")] if outside else [])
        groups = {"_zones": zoned, **({"_outside": outside} if outside else {})}
        kinds = {"_zones": "zones", "_outside": "stack"}
        return GridSpec(rows=rows, columns=columns, groups=groups, group_kind=kinds, zones=lay["zones"])

    def panel_defaults(self, spec: dict, panel: dict) -> dict:
        return {"nested": True}  # every panel sits in a zone or in the outside column


ARCHETYPE = NestedZones()
