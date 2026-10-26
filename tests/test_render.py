"""End-to-end: the real CLIs in Chromium. Renders are compared with tests/golden/ the same way lint compares
the SVG with the HTML, so sub-pixel noise passes and a moved, dropped or rewrapped element fails."""
import json
import re
import shutil
import subprocess
import sys

import pytest
import yaml
from conftest import EXAMPLES, ROOT, archetypes, browser, html, images, route, sp  # noqa: F401
from playwright.sync_api import sync_playwright

from schemantic import config

GOLDEN = ROOT / "tests" / "golden"
SNAPSHOTS = ROOT / "tests" / "snapshots"


def run(cmd: str, *args) -> tuple[int, dict]:
    """Run `python -m schemantic <cmd> ...` and parse its JSON."""
    proc = subprocess.run([sys.executable, "-m", "schemantic", cmd, *map(str, args)], capture_output=True, text=True, cwd=ROOT)
    return proc.returncode, json.loads(proc.stdout)


@pytest.fixture(scope="module")
def renders(tmp_path_factory):
    """Each example rendered once at 1x, shared by the golden and snapshot tests."""
    out, done = tmp_path_factory.mktemp("renders"), {}

    def render(path):
        if path not in done:
            code, report = run("render", path, "--out", out, "--scale", 1)
            assert code == 0, report
            done[path] = out
        return done[path]
    return render


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.stem)
def test_render_matches_golden(path, renders, tmp_path, update_golden):
    fresh, golden = renders(path) / f"{path.stem}.png", GOLDEN / f"{path.stem}.png"
    if update_golden or not golden.exists():
        GOLDEN.mkdir(exist_ok=True)
        shutil.copyfile(fresh, golden)
        pytest.skip(f"wrote {golden.relative_to(ROOT)}; review it and commit")
    diff = images.image_diff(golden, fresh, tmp_path / "golden-diff.png")
    assert not diff["fail"], (
        f"{diff['detail']}. Mask: {tmp_path / 'golden-diff.png'}, render: {fresh}. "
        "If the change is intended, run pytest --update-golden and commit the new image.")


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.stem)
def test_structure_matches_snapshot(path, renders, update_golden):
    fresh = json.loads((renders(path) / "_work" / f"{path.stem}.snapshot.json").read_text(encoding="utf-8"))
    stored = SNAPSHOTS / f"{path.stem}.json"
    if update_golden or not stored.exists():
        SNAPSHOTS.mkdir(exist_ok=True)
        stored.write_text(json.dumps(fresh, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        pytest.skip(f"wrote {stored.relative_to(ROOT)}; review it and commit")
    changes = images.snapshot_diff(json.loads(stored.read_text(encoding="utf-8")), fresh)
    assert not changes, "\n".join(changes[:20]) + "\nIf intended, run pytest --update-golden and commit."


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.stem)
def test_lint_is_clean(path, tmp_path):
    code, report = run("lint", path, "--out", tmp_path)
    assert (code, report["errors"]) == (0, [])


def test_render_refuses_unbuilt_archetype(example, tmp_path):
    example["archetype"] = "roadmap"
    spec = tmp_path / "roadmap.yaml"
    spec.write_text(yaml.safe_dump(example, allow_unicode=True), encoding="utf-8")
    code, report = run("render", spec, "--out", tmp_path)
    assert code == 1 and report["rendered"] is False
    assert [e["check"] for e in report["errors"]] == ["archetype"]
    assert not (tmp_path / "roadmap.svg").exists()


def write(tmp_path, spec, name):
    path = tmp_path / f"{name}.yaml"
    path.write_text(yaml.safe_dump(spec, allow_unicode=True), encoding="utf-8")
    return path


def test_connector_turns_corners_from_a_card():
    # Dead-letter queue (a card inside the hub) to On-call (a card in the side spoke) has no straight line.
    spec = sp.load_spec(ROOT / "examples" / "orderplatform-eventbus.yaml")
    i = next(k for k, f in enumerate(spec["flows"]) if f["from"] == "dlq")
    with sync_playwright() as p:
        chromium = browser.launch(p)
        page = browser.open_plate(chromium, html.build_html(spec), spec)
        routed = route.draw_flows(page, spec)
        chromium.close()
    seg = next(s for s in routed["segs"] if s["i"] == i)
    assert routed["problems"] == []
    assert len(seg["points"]) > 2 and (seg["fromPanel"], seg["toPanel"]) == ("bus", "ops")


def test_unroutable_card_connector_is_reported(tmp_path):
    # Admission control moved to the far end of its layer: every route from the Security rail crosses other cards.
    spec = sp.load_spec(ROOT / "examples" / "ontwikkelplatform-lagen.yaml")
    runtime = next(p for p in spec["panels"] if p["id"] == "runtime")
    runtime["cards"].append(runtime["cards"].pop(0))
    code, report = run("render", write(tmp_path, spec, "blocked"), "--out", tmp_path)
    assert code == 1
    assert [x["flow"]["to"] for x in report["flow_problems"]] == ["admission"]


def test_two_way_flow_gets_two_heads(tmp_path):
    spec = sp.load_spec(EXAMPLES[0])
    one_way = spec["flows"][0]
    spec["flows"] = [dict(one_way, both=True)]
    code, _ = run("render", write(tmp_path, spec, "both"), "--out", tmp_path)
    assert code == 0
    svg = (tmp_path / "both.svg").read_text(encoding="utf-8")
    num = r"-?[\d.]+"
    head = rf'<path d="M{num} {num}L{num} {num}L{num} {num}Z" fill="#2F7FC6"(/>|></path>)'  # a filled triangle in --arrow
    assert len(re.findall(head, svg, flags=re.IGNORECASE)) == 2


def hub_variant(top: int, bottom: int) -> dict:
    """The eventbus plate with `top` producers and `bottom` consumers (spokes cloned when it needs more)."""
    spec = sp.load_spec(ROOT / "examples" / "orderplatform-eventbus.yaml")
    by_id = {p["id"]: p for p in spec["panels"]}
    pool = ["orders", "payments", "shipping", "search", "analytics", "notify"]
    for k in range(top + bottom - len(pool)):
        clone = dict(by_id["notify"], id=f"extra{k}", title=f"Consumer {k + 1}")
        spec["panels"].append(clone)
        pool.append(clone["id"])
    use = pool[:top + bottom]
    spec["layout"] = {"hub": "bus", "top": use[:top], "right": "ops", **({"bottom": use[top:]} if bottom else {})}
    spec["panels"] = [p for p in spec["panels"] if p["id"] in use + ["bus", "ops"]]
    spec["flows"] = [{"from": s, "to": "bus"} for s in use[:top]] + [{"from": "bus", "to": s} for s in use[top:]] \
        + [{"from": "dlq", "to": "oncall"}]
    return spec


def test_hub_rows_of_any_size_keep_side_spokes_readable():
    from schemantic.lint import dom_lint
    failures = []
    with sync_playwright() as p:
        chromium = browser.launch(p)
        for top in range(1, 5):
            for bottom in range(0, 5):
                spec = hub_variant(top, bottom)
                assert sp.schema_errors(spec) + sp.semantic_errors(spec) == [], (top, bottom)
                page = browser.open_plate(chromium, html.build_html(spec), spec)
                flows = route.draw_flows(page, spec)
                dom = dom_lint(page, flows["segs"])
                errs = [f"{x['check']} {x['id']}" for x in flows["problems"] + [i for i in dom["issues"] if i["level"] == "error"]]
                boxes = browser.call(page, "boxes")
                page.close()
                ref = max(spec["layout"]["top"], spec["layout"].get("bottom", []), key=len)  # the fuller row
                mean = sum(boxes[s][2] - boxes[s][0] for s in ref) / len(ref)
                if len(ref) == 1:  # a lone spoke spans the hub; the side counts as one of two
                    mean = (mean - config.token_px("--gutter-x")) / 2
                side = boxes["ops"][2] - boxes["ops"][0]
                if errs or abs(side - mean) > 0.1 * mean:
                    failures.append(f"top {top} bottom {bottom}: side {side} vs spoke {mean:.0f}; {errs}")
        chromium.close()
    assert not failures, "\n".join(failures)


# A4: unreadable input gives JSON and exit 1, never a traceback
@pytest.mark.parametrize("script", ["render", "lint", "build"])
@pytest.mark.parametrize("content", ['title: "x\n', "", None], ids=["broken", "empty", "missing"])
def test_unreadable_spec_gives_json(script, content, tmp_path):
    path = tmp_path / "spec.yaml"
    if content is not None:
        path.write_text(content, encoding="utf-8")
    code, report = run(script, path, "--out", tmp_path)
    assert code == 1
    assert [(e["check"], e["id"]) for e in report["errors"]] == [("yaml", "(file)")]


# A5: a label without room is an arrow-label finding, not a routing one
def test_label_without_room_is_arrow_label(tmp_path):
    spec = sp.load_spec(ROOT / "examples" / "orderplatform-toegang.yaml")
    spec["flows"][0]["label"] = "OIDC"  # a horizontal arrow in a 48 px gutter
    code, report = run("lint", write(tmp_path, spec, "label"), "--out", tmp_path)
    assert code == 1
    assert [(e["check"], e["id"]) for e in report["errors"]] == [("arrow-label", "flows/0")]


# A2: without footer.columns the footer still spans the full width
def test_default_footer_fills_the_width(tmp_path):
    spec = sp.load_spec(ROOT / "examples" / "orderplatform-eventbus.yaml")
    del spec["footer"]["columns"]
    with sync_playwright() as p:
        chromium = browser.launch(p)
        page = browser.open_plate(chromium, html.build_html(spec), spec)
        boxes = browser.call(page, "boxes")
        chromium.close()
    assert abs(boxes["footer.legend"][2] - boxes["body"][2]) <= 2


# A8: a one-word and a one-character change fail the golden comparison, inside the card they touch
@pytest.mark.parametrize("change", ["JWT check bij iedere request", "JWT check bij elke requests"])
def test_golden_catches_a_local_text_change(change, tmp_path):
    spec = sp.load_spec(ROOT / "examples" / "orderplatform-toegang.yaml")
    gateway = next(p for p in spec["panels"] if p["id"] == "gateway")
    gateway["cards"][0]["note"] = change
    code, _ = run("render", write(tmp_path, spec, "changed"), "--out", tmp_path, "--scale", 1)
    assert code == 0
    diff = images.image_diff(GOLDEN / "orderplatform-toegang.png", tmp_path / "changed.png", tmp_path / "mask.png")
    card = json.loads((tmp_path / "_work" / "changed.snapshot.json").read_text())["boxes"]["gateway.card0"]
    assert diff["fail"]
    assert all(card[0] <= r[0] and r[2] <= card[2] and card[1] <= r[1] and r[3] <= card[3] for r in diff["regions"])


# A9: an installed skill folder is read-only; the doctor and a render still work, writing only elsewhere
def test_read_only_skill_folder(tmp_path):
    skill = tmp_path / "skill"
    shutil.copytree(ROOT, skill, ignore=shutil.ignore_patterns(".venv", ".git", "out", "tests", "__pycache__", ".pytest_cache"))
    before = {p for p in skill.rglob("*")}
    for p in [skill, *skill.rglob("*")]:
        p.chmod(p.stat().st_mode & ~0o222)
    try:
        env = {**__import__("os").environ, "SCHEMANTIC_HOME": str(tmp_path / "home")}
        doc = subprocess.run([sys.executable, str(skill / "scripts" / "doctor.py"), "--no-install"],
                             capture_output=True, text=True, env=env)
        report = json.loads(doc.stdout)
        assert doc.returncode == 0 and report["ok"] and report["python"] == sys.executable, report
        proc = subprocess.run([report["python"], str(skill / "scripts" / "render.py"),
                               str(skill / "examples" / "orderplatform-toegang.yaml"), "--out", str(tmp_path / "out")],
                              capture_output=True, text=True, env=env)
        assert proc.returncode == 0, proc.stdout + proc.stderr
        assert (tmp_path / "out" / "orderplatform-toegang.png").exists()
        # Root ignores the permissions, and then Python caches bytecode; nothing else may appear.
        new = {p for p in skill.rglob("*") if "__pycache__" not in p.parts} - before
        assert not new, new
        if __import__("os").geteuid() != 0:
            assert not list(skill.rglob("__pycache__"))
    finally:
        for p in [skill, *skill.rglob("*")]:
            p.chmod(p.stat().st_mode | 0o200)
