"""decision-tree: which path applies to my case. A tree drawn top down from `root`, with each panel a question or an outcome;
an arrow is an answer and says so in its label. The tree follows from the flows: an arrow's end hangs under the first panel
that reaches it, and any later arrow to it is drawn across the tree."""
from __future__ import annotations

from ..findings import finding
from . import GridSpec
from .hierarchy import Hierarchy


class DecisionTree(Hierarchy):
    name = "decision-tree"
    required = frozenset({"root"})
    allowed = frozenset({"root", "chips_at"})
    legend_keys = {}
    legend_roles = False  # a filled header marks an outcome; the colours say nothing else
    cards_are_things = False
    ends_on_panels = True

    def children(self, spec: dict) -> dict[str, list[str]]:
        root = spec["layout"]["root"]
        tree, seen, level = {}, {root}, [root]
        while level:
            next_level = []
            for pid in level:
                for f in spec.get("flows", []):
                    if f["from"] == pid and f["to"] not in seen:
                        seen.add(f["to"])
                        tree.setdefault(pid, []).append(f["to"])
                        next_level.append(f["to"])
            level = next_level
        return tree

    def validate(self, spec: dict) -> list[dict]:
        ids, out = {p["id"] for p in spec["panels"]}, []
        for i, f in enumerate(spec.get("flows", [])):
            if f["from"] not in ids or f["to"] not in ids:
                out.append(finding("layout", f"flows/{i}", "an answer runs from a question to a panel, not to or from a card"))
            elif not f.get("label"):
                out.append(finding("layout", f"flows/{i}",
                                   f"the arrow from '{f['from']}' to '{f['to']}' does not say which answer it is; give it a label"))
        if out:
            return out
        for pid in ids - set(self.placed(spec)):
            out.append(finding("layout", pid, f"no answer leads to panel '{pid}'"))
        for f in spec.get("flows", []):
            answers = [g.get("label") for g in spec["flows"] if g["from"] == f["from"]]
            if len(answers) < 2:
                out.append(finding("layout", f["from"],
                                   f"'{f['from']}' has one answer, so it decides nothing; give it another or drop the question"))
            elif len(set(answers)) < len(answers):
                out.append(finding("layout", f["from"], f"two answers of '{f['from']}' say the same"))
        return out or super().validate(spec)

    def grid(self, spec: dict) -> GridSpec:
        """Questions at their own level, and every outcome in the last row, so all the ends of the tree read as one line.
        The cells above an early outcome stay empty, with its arrow running through them."""
        leaves = self.leaves(spec, spec["layout"]["root"])
        levels = self.levels(spec)
        rows = [["."] * len(leaves) for _ in levels]
        for depth, level in enumerate(levels):
            for pid in level:
                row = rows[-1] if pid in leaves else rows[depth]
                for leaf in self.leaves(spec, pid):
                    row[leaves.index(leaf)] = pid
        return GridSpec(rows=rows, columns=["minmax(0, 1fr)"] * len(leaves), open_cells=True)

    def loud(self, spec: dict) -> set[str]:
        return {p["id"] for p in spec["panels"]} - {f["from"] for f in spec.get("flows", [])}

    def expand(self, spec: dict) -> dict:
        return spec


ARCHETYPE = DecisionTree()
