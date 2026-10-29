"""The series check: parts read as one story, so they must agree with each other (schemantic series)."""
import copy

import yaml
from conftest import ROOT, sp

from schemantic.series import series_findings

BASE = sp.load_spec(ROOT / "examples" / "orderplatform-toegang.yaml")  # part 2 of 3 of "orderplatform", in Dutch


def parts(tmp_path, *changes):
    paths = []
    for n, change in enumerate(changes, 1):
        spec = copy.deepcopy(BASE)
        spec["canvas"]["part"] = n
        change(spec)
        path = tmp_path / f"part{n}.yaml"
        path.write_text(yaml.safe_dump(spec, allow_unicode=True), encoding="utf-8")
        paths.append(path)
    return paths


def where(found):
    return sorted((f["level"], f["id"]) for f in found)


def test_agreeing_parts_pass_and_a_missing_one_is_named(tmp_path):
    assert where(series_findings(parts(tmp_path, lambda s: None, lambda s: None))) == \
        [("warning", "part1.yaml: canvas.series")]  # part 3 of 3 is not among the files


def test_one_thing_keeps_one_colour(tmp_path):
    def as_people(s):
        next(p for p in s["panels"] if p["id"] == "services")["role"] = "actor"
    found = series_findings(parts(tmp_path, lambda s: None, as_people, lambda s: None))
    assert [(f["level"], f["detail"].split("'")[1]) for f in found if f["level"] == "error"][0] == ("error", "domeinservices")


def test_language_numbering_and_arrows_must_agree(tmp_path):
    def english(s):
        s["canvas"]["lang"] = "en"

    def again(s):
        s["canvas"]["part"] = 1
        s["flows_mean"] = "data"
    found = series_findings(parts(tmp_path, lambda s: None, english, again))
    assert ("error", "part2.yaml: canvas.lang") in where(found)
    assert ("error", "part3.yaml: canvas.part") in where(found)
    assert ("warning", "part3.yaml: flows_mean") in where(found)


def test_the_examples_series_holds(tmp_path):
    found = series_findings([ROOT / "examples" / "orderplatform-toegang.yaml"])
    assert [f for f in found if f["level"] == "error"] == []
