"""Layout checks on the measured page (js/lint.js): text, overlap, containment, canvas fit, arrows, chips, density."""
from __future__ import annotations

from .browser import call
from .config import TYPE_FLOOR_PX

# Panel content filling less than this share of its panel reads as "visibly emptier" (review question 4);
# 0.6 flagged the one panel a reviewer called empty in the first test plate and none of the others.
DENSITY_MIN = 0.6


def dom_lint(page, segs: list[dict]) -> dict:
    """{issues, density} for the plate in `page`, with the routed connectors in `segs`."""
    return call(page, "lint", {"floor": TYPE_FLOOR_PX, "segs": segs, "densityMin": DENSITY_MIN})
