"""sequence: who talks to whom, in what order, for one request. One column per participant with its lifeline, time
running down; a card's `row` says when it acts, and each message is an arrow between two cards in one row, numbered by
row. A card is what that participant does at that moment."""
from __future__ import annotations

from ..findings import finding
from . import Archetype, GridSpec


class Sequence(Archetype):
    name = "sequence"
    required = frozenset({"participants"})
    allowed = frozenset({"participants", "chips_at"})
    cards_are_things = False
    max_cards = 12

    def placed(self, spec: dict) -> list[str]:
        return spec["layout"]["participants"]

    @staticmethod
    def where(spec: dict) -> dict[str, tuple[int, int]]:
        """Card id -> (column, row), for the cards on a lifeline that have a row."""
        out = {}
        for x, pid in enumerate(spec["layout"]["participants"]):
            panel = next((p for p in spec["panels"] if p["id"] == pid), {})
            for i, c in enumerate(panel.get("cards", [])):
                if c.get("row"):
                    out[c.get("id") or f"{pid}.card{i}"] = (x, c["row"])
        return out

    def validate(self, spec: dict) -> list[dict]:
        out, at = [], self.where(spec)
        for p in spec["panels"]:
            if p["id"] not in spec["layout"]["participants"]:
                continue
            rows = [c.get("row") for c in p.get("cards", [])]
            if None in rows:
                out.append(finding("layout", p["id"], "every card on a lifeline needs `row`, the moment it acts"))
            for r in sorted({r for r in rows if r and rows.count(r) > 1}):
                out.append(finding("layout", p["id"], f"two cards in row {r}; a participant does one thing per row"))
        taken: dict[int, str] = {}
        for i, f in enumerate(spec.get("flows", [])):
            a, b = at.get(f["from"]), at.get(f["to"])
            if not a or not b:
                out.append(finding("layout", f"flows/{i}", "a message runs between two cards on lifelines"))
            elif a[1] != b[1] or a[0] == b[0]:
                out.append(finding("layout", f"flows/{i}", f"'{f['from']}' (row {a[1]}) and '{f['to']}' (row {b[1]}): a message "
                                   "runs along one row, between two participants"))
            elif a[1] in taken:
                out.append(finding("layout", f"flows/{i}", f"row {a[1]} already holds {taken[a[1]]}; one message per row"))
            else:
                taken[a[1]] = f"{f['from']} -> {f['to']}"
                between = [c for c, (x, r) in at.items() if r == a[1] and min(a[0], b[0]) < x < max(a[0], b[0])]
                if between:
                    out.append(finding("layout", f"flows/{i}", f"the message in row {a[1]} would run through '{between[0]}'; "
                                       "move that card to a row of its own"))
        return out

    def grid(self, spec: dict) -> GridSpec:
        ids = spec["layout"]["participants"]
        return GridSpec(rows=[ids], columns=["minmax(0, 1fr)"] * len(ids))

    def standalone(self, spec: dict) -> set[str]:
        return set(spec["layout"]["participants"])

    def expand(self, spec: dict) -> dict:
        """Number the messages by row, unless a drawn story numbers its own route."""
        if any(s.get("draw") for s in spec.get("stories", [])):
            return spec
        at = self.where(spec)
        order = sorted({at[f["from"]][1] for f in spec.get("flows", []) if f["from"] in at})
        return {**spec, "flows": [{**f, "step": f.get("step") or order.index(at[f["from"]][1]) + 1} for f in spec.get("flows", [])]}

    def panel_defaults(self, spec: dict, panel: dict) -> dict:
        if panel["id"] not in spec["layout"]["participants"]:
            return {}
        lifelines = [p for p in spec["panels"] if p["id"] in spec["layout"]["participants"]]
        rows = max((c.get("row") or 1 for p in lifelines for c in p.get("cards", [])), default=1)
        return {"lane": True, "lifeline": True, "cell": True, "card_rows": rows}


ARCHETYPE = Sequence()
