"""Layout checks on the measured page (js/lint.js): text, overlap, containment, canvas fit, arrows, chips, density."""
from __future__ import annotations

from .browser import call
from .config import TYPE_FLOOR_PX

# A run of empty space inside a body panel longer than this reads as a hole in the plate (review question 4).
VOID_WARN_PX = 96
VOID_ERROR_PX = 160


def dom_lint(page, segs: list[dict]) -> dict:
    """{issues, density, voids} for the plate in `page`, with the routed connectors in `segs`."""
    return call(page, "lint", {"floor": TYPE_FLOOR_PX, "segs": segs, "voidWarn": VOID_WARN_PX, "voidError": VOID_ERROR_PX})
