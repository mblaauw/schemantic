"""data-model: what data there is and how it relates. Each panel is an entity holding a fields pattern, placed in named grid
cells as in column-flow; an arrow is a relation between two entities and can say how many on each side."""
from __future__ import annotations

from dataclasses import replace

from ..findings import finding
from . import GridSpec
from .column_flow import ColumnFlow


class DataModel(ColumnFlow):
    name = "data-model"
    relations = True
    ends_on_panels = True
    level_rows = True

    def validate(self, spec: dict) -> list[dict]:
        return super().validate(spec) + [
            finding("layout", p["id"], f"panel '{p['id']}' is an entity and holds cards; what it holds goes in a fields pattern")
            for p in spec["panels"] if p.get("cards")]

    def grid(self, spec: dict) -> GridSpec:
        # Most arrows carry a cardinality and a label. A cell may stay empty, since an entity needs no more width than its fields.
        return replace(super().grid(spec), gutter_x="calc(2.5 * var(--gutter-x))", open_cells=True)

    def advice(self, spec: dict) -> list[dict]:
        rows = [row.split() for row in spec["layout"]["areas"]]
        wide = {a for row in rows for a, b in zip(row, row[1:], strict=False) if a == b and a != "."}
        return [finding("layout", p, f"entity '{p}' spans columns its fields cannot fill; give it one cell and leave the other empty",
                        level="warning") for p in sorted(wide)]

    def expand(self, spec: dict) -> dict:
        def relation(f: dict) -> dict:
            if not f.get("cardinality"):
                return f
            return {**f, "label": " ".join(filter(None, [f["cardinality"], f.get("label")]))}
        return {**spec, "flows": [relation(f) for f in spec.get("flows", [])]}


ARCHETYPE = DataModel()
