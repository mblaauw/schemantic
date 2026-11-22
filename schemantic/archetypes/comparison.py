"""comparison: which option, and why. Options as columns under a band, criteria as rows, a card in every cell with the
verdict; the option the plate recommends is marked and tinted down through every criterion. Built on the swimlane: the
same rows and columns, read as a table."""
from __future__ import annotations

from ..findings import finding
from . import GridSpec
from .swimlane import Swimlane

VERDICT_ICONS = ("circle-check", "alert-triangle", "circle-x")


class Comparison(Swimlane):
    name = "comparison"
    required = frozenset({"criteria", "options"})
    allowed = frozenset({"criteria", "options", "pick", "verdicts", "chips_at"})
    legend_roles = False
    cards_are_things = False

    def placed(self, spec: dict) -> list[str]:
        return spec["layout"]["criteria"]

    def validate(self, spec: dict) -> list[dict]:
        lay, out = spec["layout"], []
        n = len(lay["options"])
        if lay.get("pick") and not 1 <= lay["pick"] <= n:
            out.append(finding("layout", "layout.pick", f"pick is option {lay['pick']}; there are {n}"))
        for p in spec["panels"]:
            if p["id"] not in lay["criteria"]:
                continue
            cols = [c.get("col") for c in p.get("cards", [])]
            missing = [lay["options"][i] for i in range(n) if i + 1 not in cols]
            if missing:
                out.append(finding("layout", p["id"], f"no verdict for {', '.join(missing)}: a criterion has one card per "
                                   "option, its `col` naming the option"))
            if len([c for c in cols if c]) != len({c for c in cols if c}) or any(c and c > n for c in cols):
                out.append(finding("layout", p["id"], f"one card per option, with `col` from 1 to {n}"))
        return out

    def legend(self, spec: dict, labels: dict) -> list[dict]:
        """A verdict icon is a judgement, and a reader takes it for the sources' own unless the plate says whose it is."""
        icons = {c.get("icon") for p in spec["panels"] if p["id"] in spec["layout"]["criteria"] for c in p.get("cards", [])}
        shown = [i for i in VERDICT_ICONS if i in icons]
        label = spec["layout"].get("verdicts") or labels["verdict"]
        return [{"kind": "verdict", "key": "verdict", "icons": shown, "label": label}] if shown else []

    def grid(self, spec: dict) -> GridSpec:
        lay = spec["layout"]
        return GridSpec(rows=[["_options"]] + [[c] for c in lay["criteria"]], columns=["minmax(0, 1fr)"],
                        bands={"_options": lay["options"]}, marks={"_options": lay["pick"]} if lay.get("pick") else {},
                        mark_label="pick")

    def standalone(self, spec: dict) -> set[str]:
        return set(spec["layout"]["criteria"])

    def panel_defaults(self, spec: dict, panel: dict) -> dict:
        lay = spec["layout"]
        if panel["id"] not in lay["criteria"]:
            return {}
        return {"lane": True, "role": "frame", "card_columns": len(lay["options"]), **({"now": lay["pick"]} if lay.get("pick") else {})}


ARCHETYPE = Comparison()
