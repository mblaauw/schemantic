"""Route the spec's flows in the page (js/route.js) and file the router's problems under lint checks."""
from __future__ import annotations

from .browser import call
from .findings import finding

# Router problem kinds and the lint check each belongs to.
FLOW_CHECKS = {"route": "arrow-routing", "label": "arrow-label", "endpoint": "flow", "self": "flow", "nested": "flow"}


def draw_flows(page, spec: dict) -> dict:
    """Draw the connectors into the page. Returns {segs, problems}; segs carry each route's points and label box."""
    out = call(page, "route", spec.get("flows", []))
    for x in out["problems"]:
        x["check"] = FLOW_CHECKS[x["kind"]]
    return out


# Between two panels there is no card to connect instead: the fix is where they sit, or room.
PANELS_HINT = "Place the two panels in neighbouring columns or rows so they share a gutter, or cut content to give room."


def problems_as_findings(flows: dict) -> list[dict]:
    return [finding(x["check"], f"flows/{x['i']}", x["problem"],
                    **({"hint": PANELS_HINT} if x["kind"] == "route" and not x.get("cards") else {}))
            for x in flows["problems"]]
