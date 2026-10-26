"""B8: every lint check has a hint, a generated doc row, and a test here that triggers it."""
import copy
import json

import pytest
from conftest import ROOT, sp
from test_render import write

from schemantic import cli, findings, pipeline

BASE = sp.load_spec(ROOT / "examples" / "orderplatform-toegang.yaml")
LAYERS = sp.load_spec(ROOT / "examples" / "ontwikkelplatform-lagen.yaml")


def panel(spec, pid):
    return next(p for p in spec["panels"] if p["id"] == pid)


def mutate(fn, base=BASE):
    spec = copy.deepcopy(base)
    fn(spec)
    return spec


# check -> (spec, theme css) that must produce it. Spec-stage checks need no browser.
SPEC_TRIGGERS = {
    "schema": lambda s: s.update(title="x" * 81),
    "id": lambda s: (s["panels"][0]["cards"][0].update(id="x"), s["panels"][1]["cards"][0].update(id="x")),
    "archetype": lambda s: s.update(archetype="roadmap"),
    "layout": lambda s: s["footer"].update(columns=[1, 1, 1]),
    "budget": lambda s: s["layout"].update(areas=["clients identity gateway services data data"], row_heights=["fill"]),
    "pattern": lambda s: panel(s, "identity")["patterns"][0]["rows"][0]["cells"].append("full"),
    "flow": lambda s: s["flows"].append({"from": "gateway", "to": "billing"}),
    "canvas": lambda s: s["canvas"].update(part=4),
    "chip-mirror": lambda s: s["footer"].update(open_questions={"extra": ["Event bus nu of pas in fase 3?"]}),
    "icon": lambda s: s["panels"][0]["cards"][0].update(icon="unicorn"),
    "language": lambda s: s["panels"][0]["cards"][0].update(note="leest de productcatalogus"),
}


def admission_last(s):
    runtime = panel(s, "runtime")
    runtime["cards"].append(runtime["cards"].pop(0))


LAYOUT_TRIGGERS = {
    "text-overflow": (lambda s: panel(s, "data")["patterns"][0]["tiers"][1].update(note="gestandaardiseerdeproductgegevens"), "", BASE),
    "containment": (lambda s: [c.update(bullets=["een regel tekst die ruimte inneemt"] * 3) for c in panel(s, "clients")["cards"]], "", BASE),
    "canvas-fit": (lambda s: None, ".titleblock { margin-right: -160px; }", BASE),
    "overlap": (lambda s: None, ".card + .card { margin-top: -30px; }", BASE),
    "type-floor": (lambda s: None, ":root { --t-body: 9px; }", BASE),
    "contrast": (lambda s: None, ":root { --muted: #C8CDD2; }", BASE),
    "arrow-routing": (admission_last, "", LAYERS),
    "arrow-label": (lambda s: s["flows"][0].update(label="OIDC"), "", BASE),
    "chip-length": (lambda s: panel(s, "security")["chips"][0].update(text="Uitzonderingen op policy lopen via een pull request"),
                    "", LAYERS),
    "density": (lambda s: panel(s, "services").update(cards=panel(s, "services")["cards"][:1], chips=[]), "", BASE),
}
OTHER = {"yaml", "svg-parity", "internal"}


def test_every_check_is_triggered_and_documented():
    assert set(findings.CHECKS) == set(SPEC_TRIGGERS) | set(LAYOUT_TRIGGERS) | OTHER
    assert all(c.hint.endswith(".") for c in findings.CHECKS.values())


def test_lint_fixes_doc_is_generated_from_the_table():
    assert findings.LINT_FIXES.read_text(encoding="utf-8") == findings.lint_fixes_md(), "run: python -m schemantic docs"


@pytest.mark.parametrize("check", sorted(SPEC_TRIGGERS))
def test_spec_check_triggers(check):
    found = sp.check(mutate(SPEC_TRIGGERS[check]))
    assert check in {f["check"] for f in found}


@pytest.mark.parametrize("check", sorted(LAYOUT_TRIGGERS))
def test_layout_check_triggers(check, tmp_path):
    fn, theme, base = LAYOUT_TRIGGERS[check]
    report = pipeline.build(write(tmp_path, mutate(fn, base), "t"), tmp_path, deliver=False, theme_css=theme)
    found = report["errors"] + report["warnings"]
    assert check in {f["check"] for f in found}, [f["check"] for f in found]
    assert all(f.get("hint") for f in found)


def test_yaml_triggers(tmp_path):
    (tmp_path / "bad.yaml").write_text('title: "x\n', encoding="utf-8")
    assert [f["check"] for f in sp.read_spec(tmp_path / "bad.yaml")[1]] == ["yaml"]


def test_svg_parity_triggers(tmp_path, monkeypatch):
    real = pipeline.export_svg

    def drop_a_name(page, spec):  # an exporter that loses one card name: the SVG no longer matches the page
        svg, fonts = real(page, spec)
        return svg.replace(">Token validatie</text>", "></text>"), fonts
    monkeypatch.setattr(pipeline, "export_svg", drop_a_name)
    report = pipeline.build(write(tmp_path, BASE, "p"), tmp_path, deliver=False)
    assert "svg-parity" in {f["check"] for f in report["errors"]}


def test_internal_triggers(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(pipeline, "build", lambda *a, **k: 1 / 0)
    assert cli.main(["build", str(ROOT / "examples" / "orderplatform-toegang.yaml"), "--out", str(tmp_path)]) == 1
    report = json.loads(capsys.readouterr().out)
    assert [f["check"] for f in report["errors"]] == ["internal"]
