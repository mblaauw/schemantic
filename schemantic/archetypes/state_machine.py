"""state-machine: what states a thing can be in, and what moves it on. Each panel is a state, placed in named grid cells as in
column-flow; an arrow is a transition and says in its label what causes it. It may go back, or return to its own state."""
from __future__ import annotations

from dataclasses import replace

from ..findings import finding
from . import GridSpec
from .column_flow import ColumnFlow


class StateMachine(ColumnFlow):
    name = "state-machine"
    required = frozenset({"areas", "start"})
    allowed = frozenset({"areas", "start", "ends", "column_widths", "chips_at"})
    self_loops = True
    level_rows = True
    ends_on_panels = True
    legend_roles = False  # the colour says only whether a state is an end, which its tag says too
    cards_are_things = False

    def validate(self, spec: dict) -> list[dict]:
        lay, ids, out = spec["layout"], {p["id"] for p in spec["panels"]}, super().validate(spec)
        for pid in [lay["start"]] + lay.get("ends", []):
            if pid not in ids:
                out.append(finding("layout", "layout", f"'{pid}' is named as a start or end but has no panel"))
        if not spec.get("flows"):
            out.append(finding("layout", "flows", "no transitions; a state machine says what moves one state to the next"))
        for i, f in enumerate(spec.get("flows", [])):
            if f["from"] not in ids or f["to"] not in ids:
                out.append(finding("layout", f"flows/{i}", "a transition runs between states, which are panels, not cards"))
            elif not f.get("label"):
                out.append(finding("layout", f"flows/{i}",
                                   f"the transition from '{f['from']}' to '{f['to']}' does not say what causes it; give it a label"))
        return out

    def grid(self, spec: dict) -> GridSpec:
        # Every arrow carries a label, and an arrow back to its own state needs room above or below it too.
        grid = super().grid(spec)
        # A single row has no gutter below it for an arrow that goes back, so it gets the room under it instead.
        return replace(grid, gutter_x="calc(3 * var(--gutter-x))", gutter_y="calc(1.75 * var(--gutter-y))",
                       room_below="calc(1.75 * var(--gutter-y))" if len(grid.rows) == 1 else "0")

    def advice(self, spec: dict) -> list[dict]:
        lay, flows = spec["layout"], spec.get("flows", [])
        reached, frontier = {lay["start"]}, [lay["start"]]
        while frontier:
            step = {f["to"] for f in flows if f["from"] in frontier} - reached
            reached |= step
            frontier = list(step)
        leaving = {f["from"] for f in flows if f["from"] != f["to"]}
        out = []
        for p in spec["panels"]:
            if p["id"] not in reached:
                out.append(finding("flow", p["id"], f"nothing leads from the start to state '{p['id']}'", level="warning"))
            if p["id"] not in leaving and p["id"] not in lay.get("ends", []):
                out.append(finding("flow", p["id"], f"nothing leaves state '{p['id']}', and it is not in layout.ends", level="warning"))
            if p["id"] in leaving and p["id"] in lay.get("ends", []):
                out.append(finding("flow", p["id"], f"state '{p['id']}' is in layout.ends, but a transition leaves it", level="warning"))
        return out

    def panel_defaults(self, spec: dict, panel: dict) -> dict:
        return {"role": "external" if panel["id"] in spec["layout"].get("ends", []) else "platform"}

    def expand(self, spec: dict) -> dict:
        lay = spec["layout"]
        def marked(p: dict) -> dict:
            mark = "start" if p["id"] == lay["start"] else "end" if p["id"] in lay.get("ends", []) else None
            return {**p, "mark": mark} if mark else p
        return {**spec, "panels": [marked(p) for p in spec["panels"]]}


ARCHETYPE = StateMachine()
