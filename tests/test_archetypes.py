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


def test_a_lifeline_holds_twelve_cards_and_other_panels_six():
    many = [{"name": f"Step {n}", "row": n, **({"id": "place"} if n == 4 else {})} for n in range(1, 13)]
    assert not details(SEQUENCE, lambda s: panel(s, "orders").update(cards=many))
    assert details(SEQUENCE, lambda s: panel(s, "orders").update(cards=[*many, {"name": "x", "row": 12}]))  # the schema's cap
    assert any("a panel holds 6" in d for d in details(MAP, lambda s: panel(s, "sell").update(cards=[{"name": f"C{n}"} for n in range(7)])))


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


def test_a_dashed_message_is_a_reply_in_the_legend():
    from schemantic.html import legend_entries
    from schemantic.spec import load_locale
    assert "Reply or event" in {e["label"] for e in legend_entries(SEQUENCE, load_locale("en"))}


def test_a_map_has_no_phases_and_a_tree_leads():
    from schemantic.html import legend_entries
    from schemantic.spec import load_locale
    assert "New" in {e["label"] for e in legend_entries(MAP, load_locale("en"))}
    assert "Leads" in {e["label"] for e in legend_entries(archetypes.get("hierarchy").expand(HIERARCHY), load_locale("en"))}


def test_comparison_and_quadrant_keep_panel_colours_out_of_the_legend():
    from schemantic.html import legend_entries
    from schemantic.spec import load_locale
    for spec in (COMPARISON, QUADRANT, MAP):
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


def test_capability_map_rows_share_their_width_unless_columns_are_asked_for():
    arche = archetypes.get("capability-map")
    assert arche.panel_defaults(MAP, panel(MAP, "insight"))["card_columns"] == 3
    lined = {**MAP, "layout": {**MAP["layout"], "per_row": 5}}
    assert arche.panel_defaults(lined, panel(MAP, "insight"))["card_columns"] == 5


def test_a_data_model_holds_entities_and_says_how_many_on_each_side():
    spec = sp.load_spec(ROOT / "examples" / "tool-library-data-model.yaml")
    labels = {(f["from"], f["to"]): f["label"] for f in archetypes.get("data-model").expand(spec)["flows"]}
    assert labels["member", "loan"] == "1:n borrows"
    no_label = copy.deepcopy(spec)
    no_label["flows"][0].pop("label")
    assert archetypes.get("data-model").expand(no_label)["flows"][0]["label"] == "1:n"
    with_cards = copy.deepcopy(spec)
    with_cards["panels"][0]["cards"] = [{"name": "A card"}]
    assert any("is an entity and holds cards" in f["detail"] for f in sp.check(with_cards))


def test_a_decision_tree_follows_from_its_answers():
    spec = sp.load_spec(ROOT / "examples" / "harbour-permit-decision-tree.yaml")
    arche = archetypes.get("decision-tree")
    assert arche.children(spec) == {"length": ["cargo", "stay"], "cargo": ["commercial", "large"], "stay": ["long", "short"]}
    assert arche.grid(spec).rows[0] == ["length"] * 4
    assert arche.loud(spec) == {"commercial", "large", "long", "short"}
    assert arche.expand(spec)["flows"] == spec["flows"]
    uneven = copy.deepcopy(spec)
    uneven["flows"] = [f for f in uneven["flows"] if f["from"] != "stay"]
    uneven["flows"][1]["to"] = "short"
    uneven["panels"] = [p for p in uneven["panels"] if p["id"] not in ("stay", "long")]
    assert arche.grid(uneven).rows == [["length"] * 3, ["cargo", "cargo", "."], ["commercial", "large", "short"]]
    converging = sp.load_spec(ROOT / "tests" / "fixtures" / "decision-converging.yaml")
    assert arche.children(converging)["safety"] == ["page", "ticket"] and arche.children(converging)["passenger"] == ["log"]


@pytest.mark.parametrize(("fn", "says"), [
    (lambda s: s["flows"][0].pop("label"), "does not say which answer"),
    (lambda s: s["flows"][1].update(label="yes"), "say the same"),
    (lambda s: s["flows"].pop(1), "one answer"),
    (lambda s: s["flows"][0].update(to="cargo.card0"), "not to or from a card"),
    (lambda s: s["panels"].append({"id": "spare", "title": "Spare", "role": "data"}), "no answer leads"),
])
def test_decision_tree_checks(fn, says):
    spec = sp.load_spec(ROOT / "examples" / "harbour-permit-decision-tree.yaml")
    fn(spec)
    assert any(says in f["detail"] for f in sp.check(spec))


def test_only_a_state_machine_draws_an_arrow_to_its_own_box():
    spec = sp.load_spec(ROOT / "examples" / "ferry-booking-state-machine.yaml")
    assert not [f for f in sp.check(spec) if f["check"] == "flow"]
    spec = sp.load_spec(ROOT / "examples" / "orderplatform-toegang.yaml")
    spec["flows"][0]["to"] = spec["flows"][0]["from"]
    assert any("are the same element" in f["detail"] for f in sp.check(spec))


def test_a_state_machine_marks_its_start_and_ends():
    from schemantic.outline import lines
    spec = archetypes.get("state-machine").expand(sp.load_spec(ROOT / "examples" / "ferry-booking-state-machine.yaml"))
    assert {p["id"]: p.get("mark") for p in spec["panels"]} == {
        "requested": "start", "held": None, "confirmed": None, "expired": "end", "cancelled": "end", "boarded": "end"}
    assert any(line.startswith("Requested [start]") for line in lines(spec))


@pytest.mark.parametrize(("fn", "says"), [
    (lambda s: s["flows"][0].pop("label"), "does not say what causes it"),
    (lambda s: s["flows"][0].update(to="held.card0"), "which are panels"),
    (lambda s: s["layout"].update(start="nowhere"), "named as a start or end"),
    (lambda s: s.pop("flows"), "no transitions"),
])
def test_state_machine_checks(fn, says):
    spec = sp.load_spec(ROOT / "examples" / "ferry-booking-state-machine.yaml")
    fn(spec)
    assert any(says in f["detail"] for f in sp.check(spec))


@pytest.mark.parametrize(("fn", "says"), [
    (lambda s: s["flows"].remove(next(f for f in s["flows"] if f["to"] == "expired")), "nothing leads from the start"),
    (lambda s: s["layout"]["ends"].remove("boarded"), "nothing leaves state 'boarded'"),
    (lambda s: s["layout"]["ends"].append("held"), "a transition leaves it"),
])
def test_a_state_machine_warns_about_states_it_cannot_reach_or_leave(fn, says):
    spec = sp.load_spec(ROOT / "examples" / "ferry-booking-state-machine.yaml")
    fn(spec)
    assert any(says in f["detail"] and f["level"] == "warning" for f in sp.check(spec))


def test_only_a_single_row_of_states_gets_room_under_it():
    arche = archetypes.get("state-machine")
    assert arche.grid(sp.load_spec(ROOT / "examples" / "ferry-booking-state-machine.yaml")).room_below == "0"
    assert arche.grid(sp.load_spec(ROOT / "tests" / "fixtures" / "state-single-row.yaml")).room_below != "0"


def test_cardinality_belongs_on_a_data_model():
    spec = sp.load_spec(ROOT / "examples" / "orderplatform-toegang.yaml")
    spec["flows"][0]["cardinality"] = "1:n"
    assert any("cardinality belongs on a data-model" in f["detail"] for f in sp.check(spec))
