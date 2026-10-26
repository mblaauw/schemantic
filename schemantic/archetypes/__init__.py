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

# Named in the schema as the planned contract; refused until a module here builds them.
PLANNED = ["banded-matrix", "nested-zones", "swimlane", "before-after", "roadmap", "landscape-map"]


@dataclass
class GridSpec:
    """The body grid an archetype derives from a spec."""
    rows: list[list[str]]       # per row, the panel id or group name in each cell; '.' is empty
    columns: list[str]          # CSS column tracks, gutters excluded
    heights: list[str]          # 'fill' or 'auto' per row
    groups: dict[str, list[str]] = field(default_factory=dict)  # group name -> panels laid out in their own grid


class Archetype:
    name: str = ""
    required: frozenset[str] = frozenset()   # layout keys the archetype needs
    allowed: frozenset[str] = frozenset()    # layout keys it accepts
    router_hints: dict = {}                   # reserved for layouts that prefer certain channels

    def placed(self, spec: dict) -> list[str]:
        """Panel ids as the layout names them, duplicates kept so they can be reported."""
        out = []
        for key in sorted(self.allowed - {"row_heights", "column_widths"}):
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


def error(check: str, id_: str, detail: str) -> dict:
    return {"level": "error", "check": check, "id": id_, "detail": detail}


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
