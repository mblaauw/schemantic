"""The layouts added after the first seven: each one's own checks, and what it derives from the spec."""
import copy

import pytest
from conftest import ROOT, sp
from test_render import write

from schemantic import archetypes, pipeline

SEQUENCE = sp.load_spec(ROOT / "examples" / "token-check-sequence.yaml")
COMPARISON = sp.load_spec(ROOT / "examples" / "search-engine-comparison.yaml")
HIERARCHY = sp.load_spec(ROOT / "examples" / "platform-org-hierarchy.yaml")
QUADRANT = sp.load_spec(ROOT / "examples" / "migration-quadrant.yaml")
MAP = sp.load_spec(ROOT / "examples" / "retail-capability-map.yaml")


def details(base, fn):
    spec = copy.deepcopy(base)
    fn(spec)
    return [f["detail"] for f in sp.check(spec) if f["level"] == "error"]


def panel(spec, pid):
    return next(p for p in spec["panels"] if p["id"] == pid)


def card(spec, cid):
    return next(c for p in spec["panels"] for c in p.get("cards", []) if c.get("id") == cid)


@pytest.mark.parametrize("fn, says", [
    (lambda s: card(s, "send").pop("row"), "needs `row`"),
    (lambda s: card(s, "ask").update(row=1), "two cards in row 1"),
    (lambda s: card(s, "verify").update(row=9), "a message runs along one row"),
    (lambda s: s["flows"].append({"from": "take", "to": "send"}), "one message per row"),
    (lambda s: s["flows"].append({"from": "shop", "to": "gateway"}), "between two cards on lifelines"),
    (lambda s: (card(s, "place").update(row=2), s["flows"].__setitem__(1, {"from": "ask", "to": "place"})), "would run through 'verify'"),
])
def test_sequence_checks(fn, says):
    assert any(says in d for d in details(SEQUENCE, fn))


def test_sequence_numbers_its_messages_by_row_and_a_drawn_story_keeps_its_own():
    arche = archetypes.get("sequence")
    assert [f["step"] for f in arche.expand(SEQUENCE)["flows"]] == [1, 2, 3, 4, 5]
    drawn = {**SEQUENCE, "stories": [{"name": "Out", "path": ["send", "take"], "draw": True}]}
    assert "step" not in arche.expand(drawn)["flows"][0]


@pytest.mark.parametrize("fn, says", [
    (lambda s: s["layout"].update(pick=9), "pick is option 9"),
    (lambda s: panel(s, "cost")["cards"].pop(0), "no verdict for Database search"),
    (lambda s: panel(s, "quality")["cards"][0].update(col=2), "one card per option"),
])
def test_comparison_checks(fn, says):
    assert any(says in d for d in details(COMPARISON, fn))


def test_comparison_and_quadrant_keep_panel_colours_out_of_the_legend():
    from schemantic.html import legend_entries
    from schemantic.spec import load_locale
    for spec in (COMPARISON, QUADRANT):
        assert "role" not in {e["kind"] for e in legend_entries(spec, load_locale("en"))}


def test_hierarchy_spans_a_parent_over_its_children_and_draws_the_tree():
    arche = archetypes.get("hierarchy")
    assert arche.grid(HIERARCHY).rows == [["head"] * 4, ["commerce", "commerce", "foundation", "foundation"],
                                          ["shopfront", "checkout", "data", "runtime"]]
    assert {"from": "head", "to": "commerce"} in arche.expand(HIERARCHY)["flows"]


@pytest.mark.parametrize("fn, says", [
    (lambda s: s["layout"]["children"].update(ghost=["data"]), "'ghost' has children but is not in the tree"),
    (lambda s: s["layout"]["children"].update(data=["runtime"]), "placed more than once"),
    (lambda s: s["layout"]["children"]["commerce"].extend(f"p{n}" for n in range(9)), "ends of the tree"),
])
def test_hierarchy_checks(fn, says):
    assert any(says in d for d in details(HIERARCHY, fn))


def test_hierarchy_too_deep():
    def deepen(s):
        s["layout"]["children"] |= {"data": ["deep"], "deep": ["deeper"]}
        s["panels"] += [{**panel(s, "data"), "id": i, "cards": []} for i in ("deep", "deeper")]
    assert any("5 levels" in d for d in details(HIERARCHY, deepen))


def test_a_quadrant_has_four_cells():
    assert details(QUADRANT, lambda s: s["layout"]["cells"].pop())


def test_a_plate_with_nothing_to_explain_has_no_empty_legend(tmp_path):
    spec = copy.deepcopy(QUADRANT)
    panel(spec, "first").pop("focus")
    report = pipeline.build(write(tmp_path, spec, "q"), tmp_path, deliver=False)
    assert report["errors"] == [] and report["warnings"] == []
    assert "Legend" not in (tmp_path / "_work" / "q.svg").read_text(encoding="utf-8")


def test_capability_map_lines_up_its_columns():
    assert archetypes.get("capability-map").panel_defaults(MAP, panel(MAP, "insight"))["card_columns"] == 5
