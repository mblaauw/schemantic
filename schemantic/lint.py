"""Layout checks on the measured page (js/lint.js): text, overlap, containment, canvas fit, arrows, chips, density."""
from __future__ import annotations

from .browser import call
from .config import TYPE_FLOOR_PX

# A run of empty space inside a body panel longer than this reads as a hole in the plate (review question 4).
VOID_WARN_PX = 96
VOID_ERROR_PX = 160
# The footer is context; above this share of the plate's height it competes with the body (review question 6).
FOOTER_SHARE = 0.15


def widow_findings(layout: dict, spec: dict) -> list[dict]:
    """A topic, title or subtitle whose last line is a single word (from the line breaks in the layout document)."""
    block = next((it for it in layout["items"] if it["kind"] == "group" and it["id"] == "titleblock"), None)
    if not block:
        return []
    runs: list[list[str]] = []  # consecutive lines in one font are one text
    last = None
    for it in block["items"]:
        if it["kind"] != "text":
            continue
        font = (it["font"]["size"], it["font"]["weight"])
        if font != last:
            runs.append([])
        runs[-1].append(it["text"])
        last = font
    out = []
    for lines in runs:
        field = next((f for f in ("title", "subtitle", "topic") if " ".join(spec.get(f, "").split()) == " ".join(lines)), None)
        if field and len(lines) > 1 and len(lines[-1].split()) == 1:
            out.append({"level": "warning", "check": "widow", "id": field,
                        "detail": f"the {field} breaks over {len(lines)} lines and leaves '{lines[-1]}' on its own"})
    return out


def dom_lint(page, segs: list[dict]) -> dict:
    """{issues, density, voids} for the plate in `page`, with the routed connectors in `segs`."""
    return call(page, "lint", {"floor": TYPE_FLOOR_PX, "segs": segs, "voidWarn": VOID_WARN_PX, "voidError": VOID_ERROR_PX,
                               "footerShare": FOOTER_SHARE})
