"""Change one thing, expect one effect: each test changes a single property of a valid example and checks what must
change in the report and the structural snapshot, and what must stay. Fast to read, because the input is small."""
import copy
import json
from pathlib import Path

import pytest
from conftest import ROOT, sp
from test_render import write

from schemantic import images, pipeline

BASE = sp.load_spec(ROOT / "examples" / "orderplatform-toegang.yaml")
BODY = ["clients", "identity", "gateway", "services", "data"]


def build(tmp_path: Path, spec: dict, name: str, theme_css: str = "") -> tuple[dict, dict]:
    report = pipeline.build(write(tmp_path, spec, name), tmp_path / name, deliver=False, theme_css=theme_css)
    return report, json.loads(Path(report["snapshot"]).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def base(tmp_path_factory):
    report, snap = build(tmp_path_factory.mktemp("base"), copy.deepcopy(BASE), "base")
    assert report["errors"] == []
    return report, snap


def variant(tmp_path, change, theme_css=""):
    spec = copy.deepcopy(BASE)
    change(spec)
    return build(tmp_path, spec, "variant", theme_css)


def flow(snap, i):
    return next(f for f in snap["flows"] if f["i"] == i)


def columns(snap):
    """The horizontal extent of every body panel: what a change inside one panel must not move."""
    return {p: snap["boxes"][p][0::2] for p in BODY}


def test_reversing_a_flow_reverses_its_route_and_nothing_else(base, tmp_path):
    def reverse(s):
        s["flows"][0] = {"from": "identity", "to": "clients"}
    report, snap = variant(tmp_path, reverse)
    assert report["errors"] == []
    assert flow(snap, 0)["points"] == flow(base[1], 0)["points"][::-1]
    assert snap["boxes"] == base[1]["boxes"]


def test_removing_a_flow_leaves_the_other_routes_alone(base, tmp_path):
    report, snap = variant(tmp_path, lambda s: s["flows"].pop(3))
    assert report["errors"] == []
    before = [f for f in base[1]["flows"] if f["i"] != 3]
    assert [f["points"] for f in snap["flows"]] == [f["points"] for f in before]
    assert snap["boxes"] == base[1]["boxes"]


def test_a_longer_note_grows_its_card_and_moves_no_column(base, tmp_path):
    def lengthen(s):
        s["panels"][0]["cards"][0]["note"] = "leest de product catalog en de prijzen per land"
    report, snap = variant(tmp_path, lengthen)
    assert report["errors"] == []
    old, new = base[1]["boxes"]["clients.card0"], snap["boxes"]["clients.card0"]
    assert new[3] - new[1] > old[3] - old[1]
    assert columns(snap) == columns(base[1])


def test_adding_a_card_adds_one_box_in_its_panel(base, tmp_path):
    def add(s):
        gateway = next(p for p in s["panels"] if p["id"] == "gateway")
        gateway["cards"].append({"icon": "shield-lock", "name": "WAF", "note": "filtert verkeer van buiten"})
    report, snap = variant(tmp_path, add)
    assert report["errors"] == []
    added = set(snap["boxes"]) - set(base[1]["boxes"])
    assert added == {"gateway.card4"}
    card, panel = snap["boxes"]["gateway.card4"], snap["boxes"]["gateway"]
    assert panel[0] <= card[0] and card[2] <= panel[2] and panel[1] <= card[1] and card[3] <= panel[3]
    assert columns(snap) == columns(base[1])


def test_swapping_two_columns_turns_their_arrow_around(base, tmp_path):
    def swap(s):  # a column keeps its width, so the widths swap too
        s["layout"]["areas"][0] = "identity clients gateway services"
        s["layout"]["column_widths"] = [1.1, 1, 1, 1.2]
    report, snap = variant(tmp_path, swap)
    assert report["errors"] == []
    assert snap["boxes"]["identity"][0] < snap["boxes"]["clients"][0]
    old, new = flow(base[1], 0)["points"], flow(snap, 0)["points"]
    assert len(old) == len(new) == 2 and old[0][0] < old[1][0] and new[0][0] > new[1][0]  # still straight, now leftward


def test_another_language_changes_the_words_not_the_body(base, tmp_path):
    def english(s):
        s["canvas"]["lang"] = "en"
    report, snap = variant(tmp_path, english)
    assert report["errors"] == []
    words = lambda sn: {t[2] for t in sn["text"]}  # noqa: E731
    assert "Legend" in words(snap) and "Legenda" in words(base[1])
    assert {p: snap["boxes"][p] for p in BODY} == {p: base[1]["boxes"][p] for p in BODY}


def test_another_principle_grows_the_footer_not_the_body(base, tmp_path):
    def principle(s):
        s["footer"]["principles"].append("Elke service publiceert zijn events naar het lakehouse.")
    report, snap = variant(tmp_path, principle)
    assert report["errors"] == []
    assert {p: snap["boxes"][p] for p in BODY} == {p: base[1]["boxes"][p] for p in BODY}
    assert snap["boxes"]["footer"][3] - snap["boxes"]["footer"][1] >= \
        base[1]["boxes"]["footer"][3] - base[1]["boxes"]["footer"][1]


# F02 in practice: a role colour swapped for one of the same lightness moves nothing, and the image diff still fails
def test_a_role_colour_of_equal_lightness_changes_only_colour(base, tmp_path):
    report, snap = variant(tmp_path, lambda s: None, ":root { --external-head: #6A4454; }")  # lightness of #44546A
    assert report["errors"] == []
    assert snap == base[1]
    diff = images.image_diff(Path(base[0]["snapshot"]).parent / "html.png", Path(report["snapshot"]).parent / "html.png",
                             tmp_path / "mask.png")
    assert diff["fail"] and diff["colour_only"] > 0, diff["detail"]
