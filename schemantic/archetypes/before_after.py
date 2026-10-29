"""before-after: what changes. Two columns, the plate as it is and as it will be, under a label each; the panels at
the same place in `before` and `after` face each other in one row, so a reader sees what became what. The change
itself shows as status on the after side (new, changed, removed), not as arrows, which keep their own meaning; a quiet
chevron in the gutter between two facing panels reads "becomes"."""
from __future__ import annotations

from . import Archetype, GridSpec


class BeforeAfter(Archetype):
    name = "before-after"
    required = frozenset({"before", "after"})
    allowed = frozenset({"before", "after", "labels", "chips_at"})

    def placed(self, spec: dict) -> list[str]:
        return spec["layout"]["before"] + spec["layout"]["after"]

    def labels(self, spec: dict) -> list[str]:
        from ..spec import load_locale
        return spec["layout"].get("labels") or load_locale(spec["canvas"]["lang"])["before_after"]

    def grid(self, spec: dict) -> GridSpec:
        lay = spec["layout"]
        n = max(len(lay["before"]), len(lay["after"]))
        side = lambda ids, i: ids[i] if i < len(ids) else "."  # noqa: E731
        rows = [["_before", "_after"]] + [[side(lay["before"], i), side(lay["after"], i)] for i in range(n)]
        before, after = self.labels(spec)
        return GridSpec(rows=rows, columns=["minmax(0, 1fr)", "minmax(0, 1fr)"],
                        bands={"_before": [before], "_after": [after]})

    def panel_defaults(self, spec: dict, panel: dict) -> dict:
        """A before panel with an after panel facing it carries a quiet chevron in the gutter between them: becomes."""
        lay = spec["layout"]
        return {"becomes": True} if panel["id"] in lay["before"][:len(lay["after"])] else {}


ARCHETYPE = BeforeAfter()
