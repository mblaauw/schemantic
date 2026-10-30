"""hierarchy: what is made of what, or who reports to whom. A tree drawn top down from `root` by the `children` of
each panel; a parent spans the columns of everything under it, so each child sits below its parent. The arrows follow
from the tree: flows on the spec are only for what cuts across it."""
from __future__ import annotations

from ..findings import finding
from . import Archetype, GridSpec

MAX_LEVELS, MAX_LEAVES = 4, 8


class Hierarchy(Archetype):
    name = "hierarchy"
    required = frozenset({"root", "children"})
    allowed = frozenset({"root", "children", "chips_at"})
    legend_keys = {"mean_control": "mean_leads"}

    def placed(self, spec: dict) -> list[str]:
        return [spec["layout"]["root"]] + [c for kids in spec["layout"]["children"].values() for c in kids]

    def validate(self, spec: dict) -> list[dict]:
        lay, out = spec["layout"], []
        for parent in lay["children"]:
            if parent not in self.placed(spec):
                out.append(finding("layout", f"layout.children.{parent}", f"'{parent}' has children but is not in the tree"))
        if out or len(set(self.placed(spec))) != len(self.placed(spec)):
            return out  # a panel placed twice is reported with the shared placement checks
        levels = self.levels(spec)
        if len(levels) > MAX_LEVELS:
            out.append(finding("layout", "layout.children",
                               f"{len(levels)} levels; a plate holds {MAX_LEVELS}: draw the deepest branch on a plate of its own"))
        if (n := len(self.leaves(spec, lay["root"]))) > MAX_LEAVES:
            out.append(finding("layout", "layout.children",
                               f"{n} panels at the ends of the tree; a plate holds {MAX_LEAVES}: split it into a series"))
        return out

    def leaves(self, spec: dict, pid: str) -> list[str]:
        kids = spec["layout"]["children"].get(pid) or []
        return [leaf for k in kids for leaf in self.leaves(spec, k)] or [pid]

    def levels(self, spec: dict) -> list[list[str]]:
        lay = spec["layout"]
        out, level = [], [lay["root"]]
        while level:
            out.append(level)
            level = [c for p in level for c in lay["children"].get(p) or []]
        return out

    def grid(self, spec: dict) -> GridSpec:
        leaves = self.leaves(spec, spec["layout"]["root"])
        rows = []
        for level in self.levels(spec):
            row = ["."] * len(leaves)
            for pid in level:
                for leaf in self.leaves(spec, pid):
                    row[leaves.index(leaf)] = pid
            rows.append(row)
        return GridSpec(rows=rows, columns=["minmax(0, 1fr)"] * len(leaves))

    def standalone(self, spec: dict) -> set[str]:
        return set(self.placed(spec))

    def expand(self, spec: dict) -> dict:
        tree = [{"from": parent, "to": kid} for parent, kids in spec["layout"]["children"].items() for kid in kids or []]
        return {**spec, "flows": tree + spec.get("flows", [])}


ARCHETYPE = Hierarchy()
