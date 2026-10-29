"""The skill's own tools: starters (`schemantic new`) and review crops (`build --review`)."""
import re

import pytest
import yaml
from conftest import ROOT, archetypes, sp
from PIL import Image
from test_render import run, write

from schemantic import review, scaffold


def filled(v):
    """A starter as an author fills it in: every TODO replaced by the guidance that follows it."""
    if isinstance(v, str):
        return re.sub(r"\bTODO:?\s*", "", v).strip() or "Filled"
    if isinstance(v, dict):
        return {k: filled(x) for k, x in v.items()}
    if isinstance(v, list):
        return [filled(x) for x in v]
    return v


@pytest.mark.parametrize("name", archetypes.BUILT)
def test_a_starter_fails_only_on_its_todos(name):
    """Every part a finished plate needs is in the starter, valid for its archetype; only the TODOs keep it from building."""
    spec = yaml.safe_load(scaffold.starter(name))
    found = [f for f in sp.check(spec) if f["level"] == "error"]
    assert found and {f["check"] for f in found} == {"placeholder"}
    assert {"brief", "sources", "flows", "flows_mean", "footer"} <= set(spec)


@pytest.mark.parametrize("name", archetypes.BUILT)
def test_a_filled_starter_builds_clean(name, tmp_path):
    code, report = run("lint", write(tmp_path, filled(yaml.safe_load(scaffold.starter(name))), name), "--out", tmp_path)
    assert (code, report["errors"], report["warnings"]) == (0, [], [])


def test_new_writes_a_starter_and_never_overwrites(tmp_path):
    target = tmp_path / "plates" / "mine.yaml"
    code, report = run("new", "swimlane", target, "--lang", "nl")
    assert code == 0 and report["todo"] > 0 and target.exists()
    spec = sp.load_spec(target)
    assert (spec["archetype"], spec["canvas"]["lang"]) == ("swimlane", "nl")
    target.write_text("mine", encoding="utf-8")
    code, report = run("new", "swimlane", target)
    assert code == 1 and [e["check"] for e in report["errors"]] == ["yaml"] and target.read_text(encoding="utf-8") == "mine"
    code, report = run("new", "banded-matrix", tmp_path / "other.yaml")
    assert code == 1 and [e["check"] for e in report["errors"]] == ["archetype"]


def test_a_placeholder_is_named_by_its_path():
    spec = sp.load_spec(ROOT / "examples" / "kliniek-zones.yaml")
    spec["panels"][1]["cards"][0]["note"] = "TODO: what it does"
    assert [(f["check"], f["id"]) for f in sp.check(spec) if f["check"] == "placeholder"] == [
        ("placeholder", "panels/1/cards/0/note")]


def test_a_long_part_is_cut_into_overlapping_pieces_and_the_title_block_is_not():
    wide = [40, 600, 1560, 900]  # a panel spanning the plate
    cut = review.pieces(wide, 1600, 1200)
    assert len(cut) == 2 and cut[0][0] == wide[0] - review.MARGIN and cut[-1][2] == wide[2] + review.MARGIN
    assert cut[0][2] - cut[1][0] == pytest.approx(review.OVERLAP)
    assert all((x1 - x0) * review.MIN_SCALE <= review.LONG_EDGE for x0, _, x1, _ in cut)
    assert len(review.pieces(wide, 1600, 1200, whole=True)) == 1


def test_review_writes_a_readable_crop_of_every_part(tmp_path):
    path = ROOT / "examples" / "kliniek-zones.yaml"
    code, report = run("lint", path, "--out", tmp_path, "--review")
    assert code == 0
    crops = report["review"]
    parts = [c["part"].split(",")[0] for c in crops]
    panels = [p["id"] for p in sp.load_spec(path)["panels"]]
    assert parts[:2] == ["the whole plate", "titleblock"] and parts[-1] == "footer" and set(panels) <= set(parts)
    for c in crops:
        size = Image.open(c["path"]).size
        assert max(size) <= review.LONG_EDGE
        assert c["part"] in ("the whole plate", "titleblock") or c["scale"] >= review.MIN_SCALE
