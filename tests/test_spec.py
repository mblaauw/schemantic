"""Spec checks: no browser, fast. Each test breaks the reference spec in one way and expects one named check."""
import json

import pytest
from conftest import EXAMPLES, ROOT, archetypes, browser, html, images, route, sp  # noqa: F401


def errors(spec: dict) -> list[dict]:
    found = sp.schema_errors(spec) or sp.semantic_errors(spec)
    return [e for e in found if e["level"] == "error"]


def checks(spec: dict) -> set[str]:
    return {e["check"] for e in errors(spec)}


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.stem)
def test_examples_are_valid(path):
    assert errors(sp.load_spec(path)) == []


UNBUILT = [a for a in json.loads((ROOT / "schemantic" / "schema" / "plate.schema.json").read_text())["properties"]["archetype"]["enum"]
           if a not in archetypes.BUILT]


@pytest.mark.parametrize("archetype", UNBUILT)
def test_unbuilt_archetype_is_refused(example, archetype):
    example["archetype"] = archetype
    found = errors(example)
    assert [e["check"] for e in found] == ["archetype"]
    assert archetype in found[0]["detail"]


def test_unknown_archetype_fails_schema(example):
    example["archetype"] = "spaghetti"
    assert checks(example) == {"schema"}


def test_flow_to_missing_panel(example):
    example["flows"].append({"from": "gateway", "to": "billing"})
    assert "flow" in checks(example)


def test_area_must_be_rectangle(example):
    example["layout"]["areas"] = ["clients identity gateway services", "data    data     data    clients"]
    assert "layout" in checks(example)


def test_panel_not_placed(example):
    example["layout"]["areas"] = ["clients identity gateway gateway", "data    data     data    data"]
    assert any(e["id"] == "services" for e in errors(example))


def test_warning_chip_must_reach_open_questions(example):
    example["footer"]["open_questions"] = {"extra": []}
    assert "chip-mirror" in checks(example)


def test_unknown_icon(example):
    example["panels"][0]["cards"][0]["icon"] = "unicorn"
    assert "icon" in checks(example)


# F13: an icon name is a name from the index, never a path
@pytest.mark.parametrize("name", ["../../pyproject", "a/b", "Shield", "shield.svg"])
def test_icon_name_is_not_a_path(example, name):
    example["panels"][0]["cards"][0]["icon"] = name
    assert checks(example) == {"schema"}


# F06: a misspelt field inside a pattern is an error, not silently ignored
@pytest.mark.parametrize("where", ["pattern", "item"])
def test_pattern_rejects_unknown_fields(example, where):
    pattern = next(pt for p in example["panels"] for pt in p.get("patterns", []) if pt["type"] == "tier-strip")
    if where == "pattern":
        pattern["capton"] = "Lakehouse"
    else:
        pattern["tiers"][0]["nite"] = "raw"
    assert checks(example) == {"schema"}


def test_technical_term_stays_english_inside_compound(example):
    example["panels"][0]["cards"][0]["note"] = "leest de productcatalogus"
    found = errors(example)
    assert [e["id"] for e in found if e["check"] == "language"] == ["catalog"]


def hub_spec(example, **layout):
    example["archetype"] = "hub-and-spokes"
    example["layout"] = layout
    return example


def test_hub_layout_is_derived(example):
    spec = hub_spec(example, hub="identity", top=["clients", "gateway", "services"], bottom=["data"], right="x")
    # Spoke rows are groups with their own grid; the side spoke spans every row.
    assert archetypes.get(spec["archetype"]).grid(spec).rows == [["_top", "x"], ["identity", "x"], ["_bottom", "x"]]
    assert archetypes.get(spec["archetype"]).grid(spec).groups == {"_top": ["clients", "gateway", "services"], "_bottom": ["data"]}


def test_side_spoke_track_is_one_spoke_of_the_fuller_row_wide(example):
    # One side, four bottom spokes: S = H/4 - 36 and S + 48 + H = 100%, so 100% = 5S + 192 and S = 20% - 38.4px = 20% - 0.8 gutters.
    spec = hub_spec(example, hub="identity", top=["clients"], bottom=["gateway", "services", "data", "x"], left="y")
    side = "clamp(260px, calc(20.0000% + -0.8000 * var(--gutter-x)), 30%)"
    assert archetypes.get(spec["archetype"]).grid(spec).columns == [side, "minmax(0, 1fr)"]


def test_layer_cake_rails_span_every_layer(example):
    example["archetype"] = "layer-cake"
    example["layout"] = {"layers": ["clients", "gateway"], "left": "identity"}
    assert archetypes.get(example["archetype"]).grid(example).rows == [["identity", "clients"], ["identity", "gateway"]]


def test_layout_key_from_another_archetype(example):
    # The schema knows each archetype's layout keys, so the mistake is caught there, with the key named.
    example["archetype"] = "hub-and-spokes"
    found = errors(example)
    assert {e["check"] for e in found} == {"schema"} and {e["id"] for e in found} == {"layout"}
    text = " ".join(e["detail"] for e in found)
    assert "'hub' is a required property" in text and "'areas'" in text and "'column_widths'" in text


# B2 and B6: the registry and the schema agree
def test_registry_matches_schema():
    schema = sp.schema()
    names = schema["properties"]["archetype"]["enum"]
    assert set(names) == set(archetypes.REGISTRY)
    blocks = {b["if"]["properties"]["archetype"]["const"]: b["then"]["properties"]["layout"] for b in schema["allOf"]}
    for name, arche in archetypes.REGISTRY.items():
        assert set(blocks[name]["required"]) == arche.required, name
        assert set(blocks[name]["propertyNames"]["enum"]) == arche.allowed, name
        assert arche.allowed <= set(schema["properties"]["layout"]["properties"]), name


def test_examples_declare_the_schema():
    for path in EXAMPLES:
        assert path.read_text(encoding="utf-8").startswith("# yaml-language-server: $schema=../schemantic/schema/plate.schema.json")


def test_panel_placed_twice(example):
    hub_spec(example, hub="identity", top=["clients", "gateway"], bottom=["services", "data"], right="clients")
    assert [e["id"] for e in errors(example)] == ["clients"]


def test_hub_needs_two_spokes(example):
    hub_spec(example, hub="identity", top=["clients"])
    assert [e["id"] for e in errors(example)] == ["layout.hub"]


# A1: ids
def test_duplicate_panel_id(example):
    example["panels"].append(dict(example["panels"][2]))
    assert [(e["check"], e["id"]) for e in errors(example)] == [("id", "gateway")]


def test_duplicate_card_id(example):
    example["panels"][0]["cards"][0]["id"] = "x"
    example["panels"][1]["cards"][0]["id"] = "x"
    found = errors(example)
    assert [(e["check"], e["id"]) for e in found] == [("id", "x")]
    assert "panels/0/cards/0" in found[0]["detail"] and "panels/1/cards/0" in found[0]["detail"]


def test_card_id_equal_to_panel_id(example):
    example["panels"][0]["cards"][0]["id"] = "gateway"
    assert [(e["check"], e["id"]) for e in errors(example)] == [("id", "gateway")]


def test_card_id_equal_to_an_automatic_id(example):
    example["panels"][0]["cards"][0]["id"] = "gateway.card1"
    assert [e["check"] for e in errors(example)] == ["schema"]  # a dot is not allowed in an id


# A2: footer columns follow the footer panels
def test_footer_columns_must_match_panels(example):
    example["footer"]["columns"] = [1, 1]  # context, principles, open questions: three columns
    assert [(e["check"], e["id"]) for e in errors(example)] == [("layout", "footer.columns")]


def test_default_footer_columns_cover_only_present_panels(example):
    del example["footer"]["context"]
    assert sp.footer_panels(example) == ["principles", "open_questions", "legend"]


# A5: a flow from an element to itself
def test_self_loop_is_a_flow_error(example):
    example["flows"].append({"from": "gateway", "to": "gateway"})
    assert [(e["check"], e["id"]) for e in errors(example)] == [("flow", "flows/6")]


# A6: series badge
def test_part_without_of(example):
    del example["canvas"]["of"]
    assert [(e["check"], e["id"]) for e in errors(example)] == [("canvas", "canvas.of")]


def test_part_larger_than_of(example):
    example["canvas"]["part"] = 4
    assert [(e["check"], e["id"]) for e in errors(example)] == [("canvas", "canvas.part")]


# C8: card flags
def test_flags_are_numbered_and_reach_the_footer(example):
    assert sp.flags(example) == [{"card": "gateway.card1", "kind": "warning", "text": "Rate limits per tenant of per client?",
                                  "label": "V1"}]
    assert sp.open_questions(example)[0] == {"label": "V1", "text": "Rate limits per tenant of per client?", "id": "gateway.card1"}


def test_a_flag_on_a_footer_context_card_is_shown_and_asked(example):
    from schemantic.outline import markdown
    example["footer"]["context"]["cards"][3]["flag"] = {"kind": "warning", "text": "Wie beheert de lakehouse catalog?"}
    assert sp.flags(example)[-1] == {"card": "footer.context.card3", "kind": "warning",
                                     "text": "Wie beheert de lakehouse catalog?", "label": "V3"}
    assert sp.open_questions(example)[2]["id"] == "footer.context.card3"  # after the body's questions, before extra
    assert "- Platformteam — beheert gateway en lakehouse [V3]" in markdown(example)
    assert errors(example) == []


def test_flag_counts_for_the_chip_mirror(example):
    example["footer"]["open_questions"] = {"extra": ["Payments als eigen service of bij de PSP laten?", "Event bus nu of pas in fase 3?"]}
    found = errors(example)
    assert [(e["check"], "Rate limits" in e["detail"]) for e in found] == [("chip-mirror", True)]


def test_row_heights_are_gone(example):
    example["layout"]["row_heights"] = ["fill", "auto"]  # removed in 0.3: rows take their content height
    assert checks(example) == {"schema"}


# C13: icons the agent can find
def test_every_indexed_icon_has_a_drawing():
    from schemantic import icons
    assert set(icons.index()) == set(icons.bodies()) and len(icons.bodies()) == 4879
    assert icons.bodies()["shield"].startswith("<path d=")


def test_icon_search_finds_architecture_words():
    from schemantic import icons
    assert icons.search(["queue"])[:1] == ["stack-2"]
    assert "database" in icons.search(["database"])[:3]
    for word, names in icons.synonyms().items():
        assert all(n in icons.index() for n in names), word


def test_unknown_icon_hint_names_the_closest_ones(example):
    example["panels"][0]["cards"][0]["icon"] = "kafka"
    found = [e for e in sp.semantic_errors(example) if e["check"] == "icon"]
    assert found and found[0]["hint"].startswith("Closest: topology-bus, arrows-exchange, stack-2")


# E1: swimlane layout checks
def swimlane(example, columns=("Detect", "Triage", "Mitigate")):
    example["archetype"] = "swimlane"
    example["layout"] = {"lanes": ["clients", "identity", "gateway", "services", "data"], "columns": list(columns)}
    return example


def test_swimlane_step_beyond_the_columns(example):
    spec = swimlane(example)
    spec["panels"][0]["cards"][0]["col"] = 4
    assert ("layout", "clients") in [(e["check"], e["id"]) for e in errors(spec)]


def test_swimlane_two_steps_in_one_column(example):
    spec = swimlane(example)
    spec["panels"][0]["cards"][0]["col"] = 2
    spec["panels"][0]["cards"][1]["col"] = 2
    found = [e for e in errors(spec) if e["check"] == "layout"]
    assert found and "two steps in column 2" in found[0]["detail"]


def test_swimlane_grid_has_a_phase_band(example):
    g = archetypes.get("swimlane").grid(swimlane(example))
    assert g.rows[0] == ["_phases"] and g.bands == {"_phases": ["Detect", "Triage", "Mitigate"]}


# E2: nested-zones layout checks
def zones(example, tree, outside=()):
    example["archetype"] = "nested-zones"
    example["layout"] = {"zones": tree, **({"outside": list(outside)} if outside else {})}
    return example


def test_zones_place_every_panel(example):
    spec = zones(example, [{"id": "a", "title": "A", "panels": ["clients", "identity", "gateway", "services"]}], ["data"])
    assert errors(spec) == []
    spec = zones(example, [{"id": "a", "title": "A", "panels": ["clients", "identity"]}], ["data"])
    assert {e["id"] for e in errors(spec)} == {"gateway", "services"}


def test_zones_nest_at_most_three_deep(example):
    deep = {"id": "d4", "title": "4", "panels": ["clients", "identity", "gateway", "services", "data"]}
    for n in (3, 2, 1):
        deep = {"id": f"d{n}", "title": str(n), "zones": [deep]}
    assert [(e["check"], e["id"]) for e in errors(zones(example, [deep]))] == [("layout", "zone.d4")]


def test_zones_ids_unique_and_not_empty(example):
    tree = [{"id": "a", "title": "A", "panels": ["clients", "identity", "gateway", "services", "data"]},
            {"id": "a", "title": "B"}]
    details = [e["detail"] for e in errors(zones(example, tree))]
    assert any("two zones" in d for d in details) and any("empty zone" in d for d in details)


# Tier 3: before-after
def before_after(example, before=("clients", "identity"), after=("gateway", "services", "data"), **extra):
    example["archetype"] = "before-after"
    example["layout"] = {"before": list(before), "after": list(after), **extra}
    return example


def test_before_after_faces_panels_row_by_row_under_two_labels(example):
    spec = before_after(example)
    assert errors(spec) == []
    g = archetypes.get("before-after").grid(spec)
    assert g.rows == [["_before", "_after"], ["clients", "gateway"], ["identity", "services"], [".", "data"]]
    assert g.bands == {"_before": ["Nu"], "_after": ["Straks"]}  # Dutch example: the locale's labels
    g = archetypes.get("before-after").grid(before_after(example, labels=["Fase 1", "Fase 2"]))
    assert g.bands == {"_before": ["Fase 1"], "_after": ["Fase 2"]}


def test_before_after_places_every_panel_once(example):
    assert [(e["check"], e["id"]) for e in errors(before_after(example, after=("gateway", "services")))] == \
        [("layout", "data")]  # not placed
    assert [(e["check"], e["id"]) for e in errors(before_after(example, after=("gateway", "services", "clients")))] == \
        [("layout", "clients")]  # placed twice


def test_before_after_takes_only_its_layout_keys(example):
    assert "schema" in checks(before_after(example, lanes=["clients"]))


# A rail card names the layer it concerns
def test_a_rail_cards_layer_is_a_layer_in_order_and_only_in_rails():
    spec = sp.load_spec(ROOT / "examples" / "ontwikkelplatform-lagen.yaml")
    assert errors(spec) == []
    security = next(p for p in spec["panels"] if p["id"] == "security")
    security["cards"][0]["layer"] = "basement"
    assert [(e["check"], e["id"]) for e in errors(spec)] == [("layout", "security.card0")]
    security["cards"][0]["layer"] = "runtime"  # above Scanning, which sits at delivery
    assert any("top to bottom" in e["detail"] for e in errors(spec))
    security["cards"][0]["layer"] = "experience"
    next(p for p in spec["panels"] if p["id"] == "runtime")["cards"][0]["layer"] = "infra"
    assert any("only a rail" in e["detail"] for e in errors(spec))


# Focus: the panels a plate is about keep their colour; the others go quiet. An arrow can be the focus too.
def test_focus_leaves_the_other_panels_quiet(example):
    from schemantic.html import focal_panels
    assert focal_panels(example) == {"gateway"}  # the example focuses the gateway panel
    example["panels"][2].pop("focus")
    example["flows"][1]["focus"] = True  # identity -> gateway
    assert focal_panels(example) == {"identity", "gateway"}
    example["flows"][1].pop("focus")
    assert focal_panels(example) is None


def test_one_focus_counts_arrows_too(example):
    example["flows"][0]["focus"] = True
    assert [(e["check"], e["id"]) for e in errors(example)] == [("focus", "flows/0")]


# Role fit: a panel coloured as people with cards that are things, or the reverse, is worth a look
def test_role_fit_reads_the_cards_icons(example):
    from schemantic import roles
    clients = example["panels"][0]
    clients["role"] = "actor"  # browser, phone, api, users, chart: four of five are things
    assert [f["id"] for f in roles.role_fit_findings(example)] == ["clients"]
    clients["cards"] = [{"icon": "users", "name": "a"}, {"icon": "user-check", "name": "b"}, {"icon": "browser", "name": "c"}]
    assert roles.role_fit_findings(example) == []  # mostly people: fits
    clients["role"] = "platform"
    assert "show people" in roles.role_fit_findings(example)[0]["detail"]


# Roadmap: workstreams over periods, with now marked and items that span
def roadmap(example, now=2):
    example["archetype"] = "roadmap"
    example["layout"] = {"lanes": ["clients", "identity", "gateway", "services", "data"], "columns": ["Q1", "Q2", "Q3", "Q4"],
                         "now": now}
    for p in example["panels"]:
        p["cards"] = [{**c, "col": i + 1} for i, c in enumerate(p.get("cards", [])[:4])]
    return example


def test_roadmap_marks_now_and_places_items_by_period(example):
    spec = roadmap(example)
    assert errors(spec) == []
    g = archetypes.get("roadmap").grid(spec)
    assert g.bands == {"_periods": ["Q1", "Q2", "Q3", "Q4"]} and g.marks == {"_periods": 2}


def test_roadmap_items_need_a_period_and_do_not_overlap(example):
    spec = roadmap(example, now=5)
    clients = spec["panels"][0]["cards"]
    clients[0]["span"] = 2  # Q1-Q2, over the item in Q2
    clients[2].pop("col")
    details = [e["detail"] for e in errors(spec)]
    assert any("overlaps" in d for d in details) and any("needs `col`" in d for d in details)
    assert any("now is period 5" in d for d in details)


def test_rails_and_roadmap_lanes_may_stand_without_a_flow():
    """A rail touches every layer and a roadmap lane sits in time by where it is placed: neither is an orphan."""
    layers = sp.load_spec(ROOT / "examples" / "ontwikkelplatform-lagen.yaml")
    rails = {layers["layout"]["left"], layers["layout"]["right"]}
    layers["flows"] = [f for f in layers["flows"] if not {f["from"], f["to"]} & rails]
    roadmap = sp.load_spec(ROOT / "examples" / "portal-roadmap.yaml")
    assert [f for f in sp.check(layers) + sp.check(roadmap) if f["check"] == "orphan"] == []
    # Without the exemption the rail left without flows (observability) would be an orphan
    assert [f["id"] for f in sp.orphans(layers, archetypes.Archetype())] == ["observability"]


def test_a_story_breaks_where_no_flow_joins_two_steps():
    """A story is a route a finger can follow: each step joined to the next by a flow in its direction, or both ways."""
    spec = sp.load_spec(ROOT / "examples" / "kliniek-zones.yaml")
    assert spec["stories"] and [f for f in sp.check(spec) if f["check"] == "story"] == []
    spec["stories"] = [{"name": "Backwards", "path": ["integration", "portal"]}]
    assert [f["detail"] for f in sp.check(spec) if f["check"] == "story"] == [
        "story 'Backwards' breaks between 'integration' and 'portal': no flow from 'integration' to 'portal'"]
    next(f for f in spec["flows"] if (f["from"], f["to"]) == ("portal", "integration"))["both"] = True
    assert [f for f in sp.check(spec) if f["check"] == "story"] == []


def test_a_story_through_cards_says_when_only_their_panels_are_joined():
    """The review's 'jump': an arrow that ends on a panel while the route goes through one of its cards."""
    spec = sp.load_spec(ROOT / "examples" / "kliniek-zones.yaml")
    portal, integration = (next(p for p in spec["panels"] if p["id"] == pid) for pid in ("portal", "integration"))
    portal["cards"][0]["id"], integration["cards"][0]["id"] = "app", "api"
    spec["stories"] = [{"name": "Card to card", "path": ["app", "api"]}]
    found = [f for f in sp.check(spec) if f["check"] == "story"]
    assert len(found) == 1 and "a flow joins their panels, 'portal' to 'integration'" in found[0]["detail"]
    spec["flows"].append({"from": "app", "to": "api"})
    assert [f for f in sp.check(spec) if f["check"] == "story"] == []


def test_roadmap_lanes_tint_now_and_arrows_run_forward():
    spec = sp.load_spec(ROOT / "examples" / "portal-roadmap.yaml")
    page = html.build_html(spec)
    lanes, now = spec["layout"]["lanes"], spec["layout"]["now"]
    assert page.count(f'class="now-cell" style="grid-column: {now};') == len(lanes)
    assert [f for f in sp.check(spec) if f["check"] == "timeline"] == []
    del spec["layout"]["now"]
    assert 'class="now-cell"' not in html.build_html(spec)


def test_before_after_marks_each_pair_that_faces_each_other():
    spec = sp.load_spec(ROOT / "examples" / "invoicing-before-after.yaml")
    assert html.build_html(spec).count('class="becomes"') == 3
    spec["layout"]["after"] = spec["layout"]["after"][:2]  # the third before panel is gone, with nothing facing it
    spec["panels"] = [p for p in spec["panels"] if p["id"] != "recon"]
    spec["flows"] = [f for f in spec["flows"] if "recon" not in (f["from"], f["to"])]
    assert html.build_html(spec).count('class="becomes"') == 2
