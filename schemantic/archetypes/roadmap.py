"""roadmap: what comes when. One lane per workstream, items as cards in period columns (a card's `col`, and `span`
for an item that runs over several periods), a band of period names on top with `now` marked. Built on the
swimlane: the same lanes and columns, read as time instead of steps."""
from __future__ import annotations

from . import GridSpec, error
from .swimlane import Swimlane


class Roadmap(Swimlane):
    name = "roadmap"
    required = frozenset({"lanes", "columns"})
    allowed = frozenset({"lanes", "columns", "now", "chips_at"})

    def standalone(self, spec: dict) -> set[str]:
        """A workstream with no dependency is still on the roadmap: its period columns are the relation."""
        return set(spec["layout"]["lanes"])

    def validate(self, spec: dict) -> list[dict]:
        lay, out = spec["layout"], []
        ncols = len(lay["columns"])
        if lay.get("now") and not 1 <= lay["now"] <= ncols:
            out.append(error("layout", "layout.now", f"now is period {lay['now']}; there are {ncols}"))
        for p in spec["panels"]:
            if p["id"] not in lay["lanes"]:
                continue
            taken: dict[int, str] = {}
            for i, c in enumerate(p.get("cards", [])):
                where = c.get("id") or f"{p['id']}.card{i}"
                if not c.get("col"):
                    out.append(error("layout", where, "a roadmap item needs `col`, the period it starts in"))
                    continue
                periods = range(c["col"], c["col"] + c.get("span", 1))
                if periods.stop - 1 > ncols:
                    out.append(error("layout", where, f"runs past the last of the {ncols} periods"))
                for n in periods:
                    if n in taken:
                        out.append(error("layout", where, f"overlaps {taken[n]} in period {n}; one item per period per lane"))
                        break
                    taken[n] = where
        return out

    def grid(self, spec: dict) -> GridSpec:
        lay = spec["layout"]
        rows = [["_periods"]] + [[lane] for lane in lay["lanes"]]
        return GridSpec(rows=rows, columns=["minmax(0, 1fr)"], bands={"_periods": lay["columns"]},
                        marks={"_periods": lay["now"]} if lay.get("now") else {})


ARCHETYPE = Roadmap()
