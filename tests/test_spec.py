"""Spec checks: no browser, fast. Each test breaks the reference spec in one way and expects one named check."""
import json

import pytest

from conftest import EXAMPLES, ROOT, pl


def errors(spec: dict) -> list[dict]:
    found = pl.schema_errors(spec) or pl.semantic_errors(spec)
    return [e for e in found if e["level"] == "error"]


def checks(spec: dict) -> set[str]:
    return {e["check"] for e in errors(spec)}


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.stem)
def test_examples_are_valid(path):
    assert errors(pl.load_spec(path)) == []


UNBUILT = [a for a in json.loads((ROOT / "schema" / "plate.schema.json").read_text())["properties"]["archetype"]["enum"]
           if a not in pl.BUILT_ARCHETYPES]


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
    assert pl.area_tokens(spec) == [
        ["clients", "gateway", "services", "x"],
        ["identity", "identity", "identity", "x"],
        ["data", "data", "data", "x"],
    ]
    # The side spoke is as wide as one top spoke; the hub row fills, spoke rows hug their content.
    assert pl.column_weights(spec, 4) == [1, 1, 1, 1]
    assert pl.default_row_heights(spec, pl.area_tokens(spec)) == ["auto", "fill", "auto"]


def test_hub_spreads_uneven_rows_over_shared_columns(example):
    spec = hub_spec(example, hub="identity", top=["clients", "gateway", "services"], bottom=["data", "x"])
    assert pl.area_tokens(spec)[2] == ["data"] * 3 + ["x"] * 3


def test_layer_cake_rails_span_every_layer(example):
    example["archetype"] = "layer-cake"
    example["layout"] = {"layers": ["clients", "gateway"], "left": "identity"}
    assert pl.area_tokens(example) == [["identity", "clients"], ["identity", "gateway"]]


def test_layout_key_from_another_archetype(example):
    example["archetype"] = "hub-and-spokes"
    # row_heights applies to every archetype; areas and column_widths belong to column-flow alone.
    assert {e["id"] for e in errors(example)} == {"layout.hub", "layout.areas", "layout.column_widths"}


def test_panel_placed_twice(example):
    hub_spec(example, hub="identity", top=["clients", "gateway"], bottom=["services", "data"], right="clients")
    assert [e["id"] for e in errors(example)] == ["clients"]


def test_hub_needs_two_spokes(example):
    hub_spec(example, hub="identity", top=["clients"])
    assert [e["id"] for e in errors(example)] == ["layout.hub"]
