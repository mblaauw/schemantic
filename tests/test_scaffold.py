"""The skill's own tools: starters (`schemantic new`)."""
import re

import pytest
import yaml
from conftest import ROOT, archetypes, sp
from test_render import run, write

from schemantic import scaffold


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

