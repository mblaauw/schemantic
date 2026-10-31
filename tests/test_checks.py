"""B8: every lint check has a hint, a generated doc row, and a test here that triggers it."""
import copy
import json
import re
import sys
from pathlib import Path

import pytest
from conftest import ROOT, sp
from test_render import write

from schemantic import cli, findings, pipeline

BASE = sp.load_spec(ROOT / "examples" / "orderplatform-toegang.yaml")
LAYERS = sp.load_spec(ROOT / "examples" / "ontwikkelplatform-lagen.yaml")
SKIP = sp.load_spec(ROOT / "tests" / "fixtures" / "skip-connection.yaml")  # its skip arrow must cross a down arrow
ROADMAP = sp.load_spec(ROOT / "examples" / "portal-roadmap.yaml")
BEFORE_AFTER = sp.load_spec(ROOT / "examples" / "invoicing-before-after.yaml")


def panel(spec, pid):
    return next(p for p in spec["panels"] if p["id"] == pid)


def mutate(fn, base=BASE):
    spec = copy.deepcopy(base)
    fn(spec)
    return spec


# check -> the change to BASE that must produce it, or (change, other base). Spec-stage checks need no browser.
SPEC_TRIGGERS = {
    "timeline": (lambda s: s.update(flows=[{"from": f["to"], "to": f["from"]} for f in s["flows"]], stories=[]), ROADMAP),
    "schema": lambda s: s.update(title="x" * 81),
    "id": lambda s: (s["panels"][0]["cards"][0].update(id="x"), s["panels"][1]["cards"][0].update(id="x")),
    "layout": lambda s: s["footer"].update(columns=[1, 1]),
    "budget": lambda s: s["layout"].update(areas=["clients identity gateway services data data"]),
    "pattern": lambda s: panel(s, "identity")["patterns"][0]["rows"][0]["cells"].append("full"),
    "flow": lambda s: s["flows"].append({"from": "gateway", "to": "billing"}),
    "canvas": lambda s: s["canvas"].update(part=4),
    "chip-mirror": lambda s: s["footer"].update(open_questions={"extra": ["Event bus nu of pas in fase 3?"]}),
    "icon": lambda s: s["panels"][0]["cards"][0].update(icon="unicorn"),
    "role": lambda s: s["panels"][0].update(role="security"),
    "focus": lambda s: (panel(s, "gateway").update(focus=True), panel(s, "identity").update(focus=True)),
    "traceability": lambda s: s.update(sources=[{"id": "notes", "kind": "notes", "ref": "review notes"}]),
    "flows-mean": lambda s: s.pop("flows_mean"),
    "slide-budget": lambda s: s["canvas"].update(profile="slide"),
    "role-fit": lambda s: panel(s, "services").update(role="actor"),
    "placeholder": lambda s: s.update(subtitle="TODO: how the plate makes the claim true"),
    "story": lambda s: s.update(stories=[{"name": "Straight to the services", "path": ["clients", "gateway"]}]),
    "route-end": lambda s: s.update(stories=[{"name": "Through the gateway", "path": ["clients", "gateway"]}]),
    "orphan": lambda s: s.update(flows=[f for f in s["flows"] if "services" not in (f["from"], f["to"])]),
    "language": lambda s: s["panels"][0]["cards"][0].update(note="leest de productcatalogus"),
}


LONG_CHIP = "Uitzonderingen op een policy lopen altijd via een pull request met review door security"


def skip_two_layers(s):
    """A card in the top layer straight to one in the bottom layer: every way crosses the two layers between."""
    s["flows"].append({"from": "experience.card1", "to": "infra.card2"})


LAYOUT_TRIGGERS = {
    "card-width": (lambda s: panel(s, "erp").update(card_columns=1), "", BEFORE_AFTER),
    "text-overflow": (lambda s: panel(s, "data")["patterns"][0]["tiers"][1].update(note="gestandaardiseerdeproductgegevens"), "", BASE),
    # Panels grow with their content, so only a theme that caps a panel's height can squeeze one.
    "containment": (lambda s: None, "#plate .panel { max-height: 160px; }", BASE),
    "canvas-fit": (lambda s: None, ".titleblock { margin-right: -160px; }", BASE),
    "overlap": (lambda s: None, ".card + .card { margin-top: -30px; }", BASE),
    "type-floor": (lambda s: None, ":root { --t-body: 9px; }", BASE),
    "contrast": (lambda s: None, ":root { --muted: #C8CDD2; }", BASE),
    "arrow-routing": (skip_two_layers, "", LAYERS),
    "arrow-label": (lambda s: s["flows"][0].update(label="OIDC"), "", BASE),
    "arrow-crossing": (lambda s: None, "", SKIP),
    "print-size": (lambda s: s["canvas"].update(size="a4-landscape"), "", BASE),
    # Pentests at the infrastructure layer would run past the rail's end: the rail keeps its spread, and says so
    "rail-layer": (lambda s: panel(s, "security")["cards"][3].update(layer="infra"), "", LAYERS),
    "footer-share": (lambda s: None, "#plate .footer .pb { padding-bottom: 80px; }", BASE),
    "widow": (lambda s: s.update(title="Domains publish each fact once; every consumer reads it from the bus"), "", BASE),
    "paint": (lambda s: None, ".ph-title { letter-spacing: 2px; }", BASE),
    "font": (lambda s: s["panels"][0]["cards"][0].update(note="kantoor in 東京"), "", BASE),
    "network": (lambda s: None, '@font-face { font-family: Remote; src: url("https://192.0.2.1/remote.woff2"); } '
                                '.ph-title { font-family: Remote, Inter; }', BASE),
    "chip-length": (lambda s: panel(s, "security")["chips"][0].update(text=LONG_CHIP),
                    "", LAYERS),
    # A short panel ends with its content; a hole is left only where a panel spans rows (a rail beside four layers).
    "void": (lambda s: panel(s, "security").update(cards=[c for c in panel(s, "security")["cards"] if c.get("id") == "policy"],
                                                   chips=[]), "", LAYERS),
}
OTHER = {"yaml", "svg-parity", "internal", "series", "archetype"}  # series: test_series.py; archetype: test_scaffold.py


def test_every_check_is_triggered_and_documented():
    assert set(findings.CHECKS) == set(SPEC_TRIGGERS) | set(LAYOUT_TRIGGERS) | OTHER
    assert all(c.hint.endswith(".") for c in findings.CHECKS.values())


def test_lint_fixes_doc_is_generated_from_the_table():
    assert findings.LINT_FIXES.read_text(encoding="utf-8") == findings.lint_fixes_md(), "run: python -m schemantic docs"


@pytest.mark.parametrize("check", sorted(SPEC_TRIGGERS))
def test_spec_check_triggers(check):
    trigger = SPEC_TRIGGERS[check]
    found = sp.check(mutate(*trigger) if isinstance(trigger, tuple) else mutate(trigger))
    assert check in {f["check"] for f in found}


@pytest.mark.parametrize("check", sorted(LAYOUT_TRIGGERS))
def test_layout_check_triggers(check, tmp_path):
    fn, theme, base = LAYOUT_TRIGGERS[check]
    report = pipeline.build(write(tmp_path, mutate(fn, base), "t"), tmp_path, deliver=False, theme_css=theme)
    found = report["errors"] + report["warnings"]
    assert check in {f["check"] for f in found}, [f["check"] for f in found]
    assert all(line["hint"] for line in report["summary"])  # every check's hint, once


def test_yaml_triggers(tmp_path):
    (tmp_path / "bad.yaml").write_text('title: "x\n', encoding="utf-8")
    assert [f["check"] for f in sp.read_spec(tmp_path / "bad.yaml")[1]] == ["yaml"]


def test_svg_parity_triggers(tmp_path, monkeypatch):
    real = pipeline.export_svg

    def drop_a_name(layout, spec):  # an exporter that loses one card name: the SVG no longer matches the page
        svg, fonts = real(layout, spec)
        return svg.replace(">Token validatie</text>", "></text>"), fonts
    monkeypatch.setattr(pipeline, "export_svg", drop_a_name)
    report = pipeline.build(write(tmp_path, BASE, "p"), tmp_path, deliver=False)
    assert "svg-parity" in {f["check"] for f in report["errors"]}


def test_internal_triggers(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(pipeline, "build", lambda *a, **k: 1 / 0)
    assert cli.main(["build", str(ROOT / "examples" / "orderplatform-toegang.yaml"), "--out", str(tmp_path)]) == 1
    report = json.loads(capsys.readouterr().out)
    assert [f["check"] for f in report["errors"]] == ["internal"]


# C12: themes
THEME = ROOT / "examples" / "themes" / "warm.css"


def test_theme_recolours_and_adds_a_role(tmp_path):
    spec = mutate(lambda s: panel(s, "identity").update(role="security"))
    assert "role" in {f["check"] for f in sp.check(spec)}  # without the theme the role does not exist
    report = pipeline.build(write(tmp_path, spec, "warm"), tmp_path, theme=THEME)
    assert report["errors"] == [], report["errors"]
    svg = (tmp_path / "warm.svg").read_text(encoding="utf-8").lower()
    assert "#8a1538" in svg and "#7a3412" in svg and "Beveiligingsmaatregelen" in (tmp_path / "warm.svg").read_text(encoding="utf-8")


def test_theme_path_in_the_spec_is_relative_to_it(tmp_path):
    spec = mutate(lambda s: s["canvas"].update(theme="missing.css"))
    report = pipeline.build(write(tmp_path, spec, "t"), tmp_path, deliver=False)
    assert [(f["check"], f["id"]) for f in report["errors"]] == [("canvas", "canvas.theme")]


# C1 and C2: no holes, a low footer, in both canvas modes
@pytest.mark.parametrize("mode", ["fit", "fixed"])
@pytest.mark.parametrize("path", sorted((ROOT / "examples").glob("*.yaml")), ids=lambda p: p.stem)
def test_examples_have_no_voids_and_a_low_footer(path, mode, tmp_path):
    spec = mutate(lambda s: s["canvas"].update(height=mode), sp.load_spec(path))
    report = pipeline.build(write(tmp_path, spec, path.stem), tmp_path, deliver=False)
    limit = 96 if mode == "fit" else 160
    # A fixed canvas the rows cannot fill leaves a band under the footer, which is warned about on its own
    # (test_void_checks_empty_cells_spread_cards_and_a_blank_band); here the holes are those inside the plate.
    inside = {k: v for k, v in report["voids"].items() if k != "canvas"}
    assert max(inside.values()) <= limit, inside
    boxes = json.loads(Path(report["snapshot"]).read_text(encoding="utf-8"))["boxes"]
    height = float(re.search(r'height="([\d.]+)"', (tmp_path / "_work" / f"{path.stem}.svg").read_text()[:400]).group(1))
    footer = boxes["footer"][3] - boxes["footer"][1]
    assert footer <= 0.13 * height + 2, f"footer {footer}px of {height}px"


def test_route_end_finds_an_arrow_about_a_card_and_a_card_the_title_names():
    label = mutate(lambda s: s["flows"].append({"from": "clients", "to": "gateway", "label": "routing"}))
    assert any("Routing" in f["detail"] for f in sp.check(label) if f["check"] == "route-end")
    named = mutate(lambda s: s.update(subtitle="Audit log bewaart alles"))
    assert any("Audit log" in f["detail"] for f in sp.check(named) if f["check"] == "route-end")


def test_role_fit_flags_one_thing_in_two_colours():
    spec = mutate(lambda s: panel(s, "clients")["cards"].append({"icon": "server", "name": "Routing"}))
    assert any("one thing" in f["detail"] for f in sp.check(spec) if f["check"] == "role-fit")
    panel(spec, "clients")["cards"][-1]["status"] = "removed"  # what is going away may sit where it was
    assert not any("one thing" in f["detail"] for f in sp.check(spec) if f["check"] == "role-fit")


def test_role_fit_flags_a_mixed_panel_but_not_one_person_beside_tools():
    icons = lambda *names: [{"icon": n, "name": f"Card {i}"} for i, n in enumerate(names)]  # noqa: E731
    mixed = mutate(lambda s: panel(s, "services").update(cards=icons("users", "headset", "server", "database")))
    assert [f["id"] for f in sp.check(mixed) if f["check"] == "role-fit"] == ["services"]
    one = mutate(lambda s: panel(s, "services").update(cards=icons("users", "server", "database", "cloud")))
    assert "role-fit" not in {f["check"] for f in sp.check(one)}


def traced(**extra):
    """The reference plate with one source, and refs on all but what a test leaves off."""
    spec = copy.deepcopy(BASE)
    spec["sources"] = [{"id": "notes", "kind": "notes", "ref": "review notes", **extra}]
    for p in spec["panels"]:
        p.pop("status", None)
        for ch in p.get("chips", []):
            ch["refs"] = ["notes: line 1"]
        for c in p.get("cards", []):
            c["refs"] = ["notes: line 1"]
            c.pop("status", None)
            c.get("flag", {}).update(refs=["notes: line 1"])
    for f in spec["flows"]:
        f["refs"] = ["notes: line 1"]
    return spec


def test_every_arrow_status_and_warning_names_a_source_or_says_it_is_assumed():
    assert "traceability" not in {f["check"] for f in sp.check(traced())}
    spec = traced()
    del spec["flows"][0]["refs"]
    panel(spec, "gateway")["cards"][0]["status"] = "new"
    panel(spec, "services")["chips"][0]["refs"] = []
    ids = {f["id"] for f in sp.check(spec) if f["check"] == "traceability"}
    assert ids == {"flows/0", panel(spec, "gateway")["cards"][0].get("id", "gateway.card0"), "services/chips/0"}
    spec["flows"][0]["assumed"] = "the gateway must reach it"
    assert "flows/0" not in {f["id"] for f in sp.check(spec) if f["check"] == "traceability"}


def test_a_plate_of_assumptions_is_called_out():
    spec = traced()
    for f in spec["flows"]:
        f["assumed"] = "worked out"
        del f["refs"]
    for c in panel(spec, "gateway")["cards"] + panel(spec, "services")["cards"]:
        c["assumed"] = "worked out"
    assert "(plate)" in {f["id"] for f in sp.check(spec) if f["check"] == "traceability"}


def test_a_quote_must_be_in_the_source_it_names(tmp_path):
    (tmp_path / "notes.md").write_text("The **gateway**, as agreed,\nchecks every token.\n", encoding="utf-8")
    spec = traced(path="notes.md")
    found = lambda: [f["id"] for f in sp.source_quotes(spec, tmp_path)]  # noqa: E731
    spec["flows"][0]["refs"] = ["notes: the gateway, as agreed, checks every token"]  # markup and line ends do not count
    assert found() == []
    spec["flows"][0]["refs"] = ["notes: the gateway ... every token"]  # a quote may skip words
    assert found() == []
    spec["flows"][0]["refs"] = ["notes: the gateway retries every token"]
    assert found() == ["flows/0"]
    spec["sources"][0]["path"] = "missing.md"
    assert found() == ["sources/notes"]


def test_a_ref_into_a_folder_may_name_a_file(tmp_path):
    (tmp_path / "repo").mkdir()
    (tmp_path / "repo" / "compose.yml").write_text("services: {api: {}}\n", encoding="utf-8")
    spec = traced(path="repo")
    spec["flows"][0]["refs"] = ["notes: compose.yml:1"]
    assert sp.source_quotes(spec, tmp_path) == []
    spec["flows"][0]["refs"] = ["notes: services api"]
    assert sp.source_quotes(spec, tmp_path) == []
    spec["flows"][0]["refs"] = ["notes: kubernetes"]
    assert [f["id"] for f in sp.source_quotes(spec, tmp_path)] == ["flows/0"]


def test_an_assumption_is_marked_on_the_plate_and_listed(tmp_path):
    spec = traced()
    spec["flows"][0].update(assumed="the gateway must reach it", refs=[])
    panel(spec, "services")["cards"][0]["assumed"] = "a name for what the notes describe"
    report = pipeline.build(write(tmp_path, spec, "marked"), tmp_path)
    assert report["errors"] == [], report["errors"]
    assert len(report["assumptions"]) == 2 and "the gateway must reach it" in report["assumptions"][1]
    svg = (tmp_path / "marked.svg").read_text(encoding="utf-8")
    assert "#a86a00" in svg.lower() and "aanname" in svg.lower()
    md = (tmp_path / "marked.md").read_text(encoding="utf-8")
    assert "## Aannames" in md and "[aanname]" in md


def test_a_correction_reports_only_what_it_changed(tmp_path):
    path = write(tmp_path, BASE, "plate")
    assert cli.main(["baseline", str(path), "--out", str(tmp_path)]) == 1  # nothing delivered yet
    assert pipeline.build(path, tmp_path)["since_baseline"] is None
    assert pipeline.set_baseline(path, tmp_path)["errors"] == []
    corrected = mutate(lambda s: panel(s, "services")["cards"][0].update(name="Producten"))
    since = pipeline.build(write(tmp_path, corrected, "plate"), tmp_path)["since_baseline"]
    assert [line[:11] for line in since["removed"]] == ["- Catalog —"] and [line[:13] for line in since["added"]] == ["- Producten —"]
    assert since["parts_changed"] == ["services"] and since["parts_moved"] == []


def test_a_correction_shows_an_arrow_that_now_points_elsewhere(tmp_path):
    """An automatic card id follows its position: dropping a card repoints the arrow to the next, and the names show it."""
    base = mutate(lambda s: s["flows"].append({"from": "clients", "to": "identity.card1"}))
    path = write(tmp_path, base, "plate")
    pipeline.build(path, tmp_path)
    pipeline.set_baseline(path, tmp_path)
    corrected = copy.deepcopy(base)
    panel(corrected, "identity")["cards"].pop(0)
    since = pipeline.build(write(tmp_path, corrected, "plate"), tmp_path)["since_baseline"]
    assert any("Service accounts" in line and "→" in line for line in since["removed"])
    assert any("Audit log" in line and "→" in line for line in since["added"])


def test_the_correction_eval_grades_stray_edits():
    sys.path.insert(0, str(ROOT / "evals"))
    import corrections

    before = sp.load_spec(ROOT / "examples" / f"{corrections.EVENTS}.yaml")
    assert corrections.stray(before, before, []) == []
    after = copy.deepcopy(before)
    panel(after, "search")["cards"][0]["name"] = "Product search index"
    panel(after, "ops")["cards"].reverse()  # order does not count
    assert corrections.CASES["rename"][3](after)
    assert corrections.stray(before, after, corrections.CASES["rename"][2]) == []
    after["title"] = "Something else"
    assert corrections.stray(before, after, corrections.CASES["rename"][2]) == ["title"]


def test_a_ref_may_quote_a_todo_but_a_starter_ref_is_a_placeholder():
    spec = mutate(lambda s: panel(s, "services")["cards"][0].update(refs=["tf: TODO in terraform/main.tf"]))
    assert "placeholder" not in {f["check"] for f in sp.check(spec)}
    panel(spec, "services")["cards"][0]["refs"] = ["notes: TODO"]
    assert "placeholder" in {f["check"] for f in sp.check(spec)}


def test_a_repeated_hint_is_given_once_and_summed_up():
    """A fresh starter has dozens of TODOs: the report gives their hint once, and a summary line per check, errors
    first, says how many there are and what to try."""
    issues = [findings.finding("placeholder", f"panels/{n}", "still a placeholder") for n in range(3)]
    issues += [findings.finding("void", "data", "empty", level="warning"), findings.finding("story", "stories/0", "breaks")]
    r = findings.grouped(issues)
    assert [f.get("hint") is not None for f in r["errors"]] == [True, False, False, True]
    assert [(line["check"], line["level"], line["count"]) for line in r["summary"]] == [
        ("placeholder", "error", 3), ("story", "error", 1), ("void", "warning", 1)]
    assert all(line["hint"] == findings.CHECKS[line["check"]].hint for line in r["summary"])
