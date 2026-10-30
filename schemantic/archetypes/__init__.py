"""Archetype registry: one module per body layout.

An archetype owns everything that differs between layouts: which `layout` keys it takes, its own checks, the
body grid it derives, defaults for its panels, and hints for the router. Shared code asks the registry and never
names an archetype. To add one, write a module in this package that defines `ARCHETYPE`, add its `layout` block
to the schema, a section to references/archetypes.md, and an example with its golden and snapshot.
"""
from __future__ import annotations

import importlib
import pkgutil
from dataclasses import dataclass, field


@dataclass
class GridSpec:
    """The body grid an archetype derives from a spec. Names starting with '_' are groups or bands, never panels."""
    rows: list[list[str]]       # per row, the panel id or group/band name in each cell; '.' is empty
    columns: list[str]          # CSS column tracks, gutters excluded
    groups: dict[str, list[str]] = field(default_factory=dict)  # group name -> the panels inside that cell
    group_kind: dict[str, str] = field(default_factory=dict)    # group name -> "row" (default), "stack" or "zones"
    bands: dict[str, list[str]] = field(default_factory=dict)   # band name -> labels of a header row (no panels)
    zones: list[dict] = field(default_factory=list)             # the zone tree rendered in a "zones" group
    marks: dict[str, int] = field(default_factory=dict)         # band name -> the label (1-based) to mark, e.g. now
    mark_label: str = "now"                                     # the locale key of the tag on a marked label


class Archetype:
    name: str = ""
    required: frozenset[str] = frozenset()   # layout keys the archetype needs
    allowed: frozenset[str] = frozenset()    # layout keys it accepts (chips_at applies to every one)
    router_hints: dict = {}                   # reserved for layouts that prefer certain channels
    max_cards: int = 6                        # cards in one panel; a lifeline needs more, as it has one per moment
    dashed_means: str = "style_async"         # the locale key of the legend's line for a dashed arrow
    legend_roles: bool = True                 # False when a panel's colour means nothing on this layout
    cards_are_things: bool = True             # False when cards are steps or verdicts, so their icons do not say who

    def placed(self, spec: dict) -> list[str]:
        """Panel ids as the layout names them, duplicates kept so they can be reported."""
        out = []
        for key in sorted(self.allowed - {"column_widths", "chips_at"}):
            v = spec["layout"].get(key)
            out += v if isinstance(v, list) else ([v] if v else [])
        return out

    def validate(self, spec: dict) -> list[dict]:
        """Checks of this layout beyond the shared ones (placement, rectangles, row heights)."""
        return []

    def grid(self, spec: dict) -> GridSpec:
        raise NotImplementedError

    def panel_defaults(self, spec: dict, panel: dict) -> dict:
        """Extra render properties for a panel (for example, card columns or the hub frame)."""
        return {}

    def loud(self, spec: dict) -> set[str]:
        """Panels with a filled header when the plate has no focus: the layout's own centre, if it has one."""
        return set()

    def standalone(self, spec: dict) -> set[str]:
        """Panels that may stand without a flow: their place on the plate already says how they relate."""
        return set()

    def expand(self, spec: dict) -> dict:
        """What the layout implies, filled into a spec that checked clean: arrows a tree draws, numbers a row gives."""
        return spec


# Side columns (rails, side spokes) stay readable: at least SIDE_MIN_PX at a 1600 px canvas (scaled with the canvas),
# at most SIDE_MAX percent of the body.
SIDE_MIN_PX = 260
SIDE_MAX = 30


def side_track(spec: dict, preferred: str) -> str:
    """A side column's CSS track: the preferred width, clamped to readable bounds."""
    from ..config import CANVAS_SIZES
    min_px = SIDE_MIN_PX * CANVAS_SIZES[spec["canvas"]["size"]][0] / 1600
    return f"clamp({min_px:.0f}px, {preferred}, {SIDE_MAX}%)"


def _discover() -> dict[str, Archetype]:
    found = {}
    for mod in pkgutil.iter_modules(__path__):
        arche = getattr(importlib.import_module(f"{__name__}.{mod.name}"), "ARCHETYPE", None)
        if arche:
            found[arche.name] = arche
    return found


REGISTRY: dict[str, Archetype] = _discover()
BUILT = sorted(REGISTRY)


def get(name: str) -> Archetype | None:
    return REGISTRY.get(name)
