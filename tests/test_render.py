"""End-to-end: the real CLIs in Chromium. Renders are compared with tests/golden/ the same way lint compares
the SVG with the HTML, so sub-pixel noise passes and a moved, dropped or rewrapped element fails."""
import json
import re
import shutil
import subprocess
import sys

import pytest
import yaml
from playwright.sync_api import sync_playwright

from conftest import EXAMPLES, ROOT, pl

GOLDEN = ROOT / "tests" / "golden"


def run(script: str, *args) -> tuple[int, dict]:
    proc = subprocess.run([sys.executable, str(ROOT / "scripts" / script), *map(str, args)],
                          capture_output=True, text=True, cwd=ROOT)
    return proc.returncode, json.loads(proc.stdout)


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.stem)
def test_render_matches_golden(path, tmp_path, update_golden):
    code, report = run("render.py", path, "--out", tmp_path, "--scale", 1)
    assert code == 0, report
    fresh, golden = tmp_path / f"{path.stem}.png", GOLDEN / f"{path.stem}.png"
    if update_golden or not golden.exists():
        GOLDEN.mkdir(exist_ok=True)
        shutil.copyfile(fresh, golden)
        pytest.skip(f"wrote {golden.relative_to(ROOT)}; review it and commit")
    diff = pl.image_diff(golden, fresh, tmp_path / "golden-diff.png")
    assert diff["share"] <= pl.PARITY_ERROR_SHARE, (
        f"{diff['detail']}. Mask: {tmp_path / 'golden-diff.png'}, render: {fresh}. "
        "If the change is intended, run pytest --update-golden and commit the new image.")


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.stem)
def test_lint_is_clean(path, tmp_path):
    code, report = run("lint.py", path, "--out", tmp_path)
    assert (code, report["errors"]) == (0, [])


def test_render_refuses_unbuilt_archetype(example, tmp_path):
    example["archetype"] = "roadmap"
    spec = tmp_path / "roadmap.yaml"
    spec.write_text(yaml.safe_dump(example, allow_unicode=True), encoding="utf-8")
    code, report = run("render.py", spec, "--out", tmp_path)
    assert code == 1 and report["rendered"] is False
    assert [e["check"] for e in report["errors"]] == ["archetype"]
    assert not (tmp_path / "roadmap.svg").exists()


def write(tmp_path, spec, name):
    path = tmp_path / f"{name}.yaml"
    path.write_text(yaml.safe_dump(spec, allow_unicode=True), encoding="utf-8")
    return path


def test_connector_turns_corners_from_a_card():
    # Dead-letter queue (a card inside the hub) to On-call (a card in the side spoke) has no straight line.
    spec = pl.load_spec(ROOT / "examples" / "orderplatform-eventbus.yaml")
    i = next(k for k, f in enumerate(spec["flows"]) if f["from"] == "dlq")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = pl.open_plate(browser, pl.build_html(spec), spec)
        routed = pl.draw_flows(page, spec)
        browser.close()
    seg = next(s for s in routed["segs"] if s["i"] == i)
    assert routed["problems"] == []
    assert len(seg["points"]) > 2 and (seg["fromPanel"], seg["toPanel"]) == ("bus", "ops")


def test_unroutable_card_connector_is_reported(tmp_path):
    # Admission control moved to the far end of its layer: every route from the Security rail crosses other cards.
    spec = pl.load_spec(ROOT / "examples" / "ontwikkelplatform-lagen.yaml")
    runtime = next(p for p in spec["panels"] if p["id"] == "runtime")
    runtime["cards"].append(runtime["cards"].pop(0))
    code, report = run("render.py", write(tmp_path, spec, "blocked"), "--out", tmp_path)
    assert code == 1
    assert [x["flow"]["to"] for x in report["flow_problems"]] == ["admission"]


def test_two_way_flow_gets_two_heads(tmp_path):
    spec = pl.load_spec(EXAMPLES[0])
    one_way = spec["flows"][0]
    spec["flows"] = [dict(one_way, both=True)]
    code, _ = run("render.py", write(tmp_path, spec, "both"), "--out", tmp_path)
    assert code == 0
    svg = (tmp_path / "both.svg").read_text(encoding="utf-8")
    num = r"-?[\d.]+"
    head = rf'<path d="M{num} {num}L{num} {num}L{num} {num}Z" fill="#2F7FC6"(/>|></path>)'  # a filled triangle in --arrow
    assert len(re.findall(head, svg, flags=re.IGNORECASE)) == 2
