"""End-to-end: the real CLIs in Chromium. Renders are compared with tests/golden/ the same way lint compares
the SVG with the HTML, so sub-pixel noise passes and a moved, dropped or rewrapped element fails."""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from conftest import EXAMPLES, RENDERED, ROOT, archetypes, browser, html, images, route, sp  # noqa: F401
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
            code, report = run("build", path, "--out", out, "--dpi", 96)
            assert code == 0, report
            done[path] = out
        return done[path]
    return render


@pytest.mark.parametrize("path", RENDERED, ids=lambda p: p.stem)
def test_render_matches_golden(path, renders, tmp_path, update_golden):
    fresh, golden = renders(path) / f"{path.stem}.png", GOLDEN / f"{path.stem}.png"
    # F03: a missing baseline fails; only --update-golden writes one, so CI never accepts its own render.
    assert update_golden or golden.exists(), f"no golden {golden.relative_to(ROOT)}: run pytest --update-golden, review it and commit"
    if update_golden:
        GOLDEN.mkdir(exist_ok=True)
        shutil.copyfile(fresh, golden)
        pytest.skip(f"wrote {golden.relative_to(ROOT)}; review it and commit")
    diff = images.image_diff(golden, fresh, tmp_path / "golden-diff.png")
    assert not diff["fail"], (
        f"{diff['detail']}. Mask: {tmp_path / 'golden-diff.png'}, render: {fresh}. "
        "If the change is intended, run pytest --update-golden and commit the new image.")


@pytest.mark.parametrize("path", RENDERED, ids=lambda p: p.stem)
def test_structure_matches_snapshot(path, renders, update_golden):
    fresh = json.loads((renders(path) / "_work" / f"{path.stem}.snapshot.json").read_text(encoding="utf-8"))
    stored = SNAPSHOTS / f"{path.stem}.json"
    assert update_golden or stored.exists(), f"no snapshot {stored.relative_to(ROOT)}: run pytest --update-golden, review it and commit"
    if update_golden:
        SNAPSHOTS.mkdir(exist_ok=True)
        stored.write_text(json.dumps(fresh, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        pytest.skip(f"wrote {stored.relative_to(ROOT)}; review it and commit")
    changes = images.snapshot_diff(json.loads(stored.read_text(encoding="utf-8")), fresh)
    assert not changes, "\n".join(changes[:20]) + "\nIf intended, run pytest --update-golden and commit."


@pytest.mark.parametrize("path", EXAMPLES + sorted((ROOT / "docs" / "plates").glob("*.yaml")), ids=lambda p: p.stem)
def test_lint_is_clean(path, tmp_path):
    code, report = run("lint", path, "--out", tmp_path)
    assert (code, report["errors"]) == (0, [])


def test_build_refuses_an_unknown_archetype(example, tmp_path):
    example["archetype"] = "banded-matrix"
    spec = tmp_path / "matrix.yaml"
    spec.write_text(yaml.safe_dump(example, allow_unicode=True), encoding="utf-8")
    code, report = run("build", spec, "--out", tmp_path)
    assert code == 1 and report["svg"] is None
    assert [e["check"] for e in report["errors"]] == ["schema"]
    assert not (tmp_path / "matrix.svg").exists()


def boxes_of(page) -> dict:
    """Every element's box, rounded to 2 px, from the layout document (as the structural snapshot has them)."""
    from schemantic import export
    return images.snapshot(export.measure(page), [])["boxes"]


def write(tmp_path, spec, name):
    path = tmp_path / f"{name}.yaml"
    path.write_text(yaml.safe_dump(spec, allow_unicode=True), encoding="utf-8")
    return path


def test_connector_runs_from_a_card_in_one_panel_to_a_card_in_another():
    # Dead-letter queue (a card inside the hub) to On-call (a card in the side spoke); bends are tested in test_router.
    spec = sp.load_spec(ROOT / "examples" / "orderplatform-eventbus.yaml")
    i = next(k for k, f in enumerate(spec["flows"]) if f["from"] == "dlq")
    with sync_playwright() as p:
        chromium = browser.launch(p)
        page = browser.open_plate(chromium, html.build_html(spec), spec)
        routed = route.draw_flows(page, spec)
        chromium.close()
    seg = next(s for s in routed["segs"] if s["i"] == i)
    assert routed["problems"] == []
    assert (seg["from"], seg["to"], seg["fromPanel"], seg["toPanel"]) == ("dlq", "oncall", "bus", "ops")


def test_unroutable_card_connector_is_reported(tmp_path):
    # A card in the top layer straight to one in the bottom layer: every way round crosses the two layers between.
    spec = sp.load_spec(ROOT / "examples" / "ontwikkelplatform-lagen.yaml")
    spec["flows"].append({"from": "experience.card1", "to": "infra.card2"})
    code, report = run("build", write(tmp_path, spec, "blocked"), "--out", tmp_path)
    assert code == 1
    assert [x["flow"]["to"] for x in report["flow_problems"]] == ["infra.card2"]
    # F05: a build with errors publishes nothing; the unpublished files stay in _work/ to look at
    assert report["svg"] is None and report["png"] is None
    assert not list(tmp_path.glob("blocked.svg")) + list(tmp_path.glob("blocked.png"))
    assert Path(report["preview"]["png"]).exists() and Path(report["preview"]["png"]).parent.name == "_work"


# F05, F16: a clean build publishes the plate with a manifest of what made it
def test_clean_build_publishes_with_a_manifest(tmp_path):
    code, report = run("build", ROOT / "examples" / "orderplatform-eventbus.yaml", "--out", tmp_path, "--dpi", 96)
    assert code == 0 and report["preview"] is None
    names = {p.name for p in tmp_path.iterdir() if p.is_file()}
    assert names == {f"orderplatform-eventbus.{ext}" for ext in ("svg", "png", "md", "build.json")}
    made = json.loads((tmp_path / "orderplatform-eventbus.build.json").read_text(encoding="utf-8"))
    assert made == report["build"]
    assert {"schemantic", "spec_version", "spec_sha256", "chromium", "playwright", "fonts"} <= set(made)
    assert "Inter-Regular.woff2" in made["fonts"]
    # The layout document the SVG was written from stays in _work/ to inspect: groups named by their element
    layout = json.loads((tmp_path / "_work" / "orderplatform-eventbus.layout.json").read_text(encoding="utf-8"))
    def groups(items):
        for it in items:
            if it["kind"] == "group":
                yield it["id"]
                yield from groups(it["items"])
    assert {"bus", "bus.card0", "footer"} <= set(groups(layout["items"])) and layout["unsupported"] == []


def test_two_way_flow_gets_two_heads(tmp_path):
    spec = sp.load_spec(EXAMPLES[0])
    one_way = spec["flows"][0]
    spec["flows"] = [dict(one_way, both=True)]
    spec.pop("stories", None)  # they follow flows this test removes
    code, _ = run("build", write(tmp_path, spec, "both"), "--out", tmp_path)
    assert code == 0
    svg = (tmp_path / "both.svg").read_text(encoding="utf-8")
    num = r"-?[\d.]+"
    ink = config.tokens()["--arrow"]
    head = rf'<path d="M{num} {num}L{num} {num}L{num} {num}Z" fill="{ink}"(/>|></path>)'  # a filled triangle in --arrow
    assert len(re.findall(head, svg, flags=re.IGNORECASE)) == 2


def hub_variant(top: int, bottom: int) -> dict:
    """The eventbus plate with `top` producers and `bottom` consumers (spokes cloned when it needs more)."""
    spec = sp.load_spec(ROOT / "examples" / "orderplatform-eventbus.yaml")
    by_id = {p["id"]: p for p in spec["panels"]}
    for key in ("arrange", "weights"):  # a narrower hub has no room for its matrix beside the cards
        by_id["bus"].pop(key, None)
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
                boxes = boxes_of(page)
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
@pytest.mark.parametrize("script", ["lint", "build"])
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
    spec["footer"].pop("columns", None)
    with sync_playwright() as p:
        chromium = browser.launch(p)
        page = browser.open_plate(chromium, html.build_html(spec), spec)
        boxes = boxes_of(page)
        chromium.close()
    assert abs(boxes["footer.legend"][2] - boxes["body"][2]) <= 2


# A8: a one-word and a one-character change fail the golden comparison, inside the card they touch
@pytest.mark.parametrize("change", ["JWT check bij iedere request", "JWT check bij elke requests"])
def test_golden_catches_a_local_text_change(change, tmp_path):
    spec = sp.load_spec(ROOT / "examples" / "orderplatform-toegang.yaml")
    gateway = next(p for p in spec["panels"] if p["id"] == "gateway")
    gateway["cards"][0]["note"] = change
    code, _ = run("build", write(tmp_path, spec, "changed"), "--out", tmp_path, "--dpi", 96)
    assert code == 0
    diff = images.image_diff(GOLDEN / "orderplatform-toegang.png", tmp_path / "changed.png", tmp_path / "mask.png")
    card = json.loads((tmp_path / "_work" / "changed.snapshot.json").read_text())["boxes"]["gateway.card0"]
    assert diff["fail"]
    assert all(card[0] <= r[0] and r[2] <= card[2] and card[1] <= r[1] and r[3] <= card[3] for r in diff["regions"])


# F02: a role colour swapped for one of the same lightness fails, and the report says it is colour only
def test_image_diff_catches_a_colour_of_equal_lightness(tmp_path):
    from PIL import Image, ImageDraw

    for name, fill in (("red", (200, 50, 50)), ("green", (50, 120, 83))):  # both lightness 95
        img = Image.new("RGB", (200, 120), "white")
        ImageDraw.Draw(img).rectangle((40, 30, 160, 90), fill=fill)
        img.save(tmp_path / f"{name}.png")
    assert Image.open(tmp_path / "red.png").convert("L").getpixel((100, 60)) == \
        Image.open(tmp_path / "green.png").convert("L").getpixel((100, 60))
    diff = images.image_diff(tmp_path / "red.png", tmp_path / "green.png", tmp_path / "mask.png")
    assert diff["fail"] and diff["colour_only"] > 0, diff["detail"]


# A9: an installed skill folder is read-only; the doctor and a render still work, writing only elsewhere
def test_read_only_skill_folder(tmp_path):
    skill = tmp_path / "skill"
    patterns = shutil.ignore_patterns(".venv", ".git", "out", "tests", "__pycache__", ".pytest_cache", "runs")

    def ignore(folder, names):  # CI keeps pytest's temp folder inside the checkout; never copy it into itself
        return set(patterns(folder, names)) | {n for n in names if tmp_path.is_relative_to(Path(folder) / n)}

    shutil.copytree(ROOT, skill, ignore=ignore)
    before = {p for p in skill.rglob("*")}
    for p in [skill, *skill.rglob("*")]:
        p.chmod(p.stat().st_mode & ~0o222)
    try:
        env = {**__import__("os").environ, "SCHEMANTIC_HOME": str(tmp_path / "home")}
        doc = subprocess.run([sys.executable, str(skill / "scripts" / "doctor.py"), "--no-install"],
                             capture_output=True, text=True, env=env)
        report = json.loads(doc.stdout)
        assert doc.returncode == 0 and report["ok"] and report["python"] == sys.executable, report
        proc = subprocess.run([report["python"], str(skill / "scripts" / "plate.py"), "build",
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


# C6, C7, C14: line styles, status tags, focus, in the exported SVG
def test_async_flows_are_dashed_and_in_the_legend(renders):
    svg = (renders(ROOT / "examples" / "orderplatform-eventbus.yaml") / "orderplatform-eventbus.svg").read_text(encoding="utf-8")
    # Patterns are fitted to each run and allow for the round caps; what shows is the dash plus the width and the gap
    # minus it. Even the short arrows into the bus show a clear gap, so they read as dashed rather than solid.
    seen = [(float(d) + float(w), float(g) - float(w)) for w, d, g in
            re.findall(r'stroke-width="([\d.]+)" stroke-linecap="round" stroke-dasharray="([\d.]+) ([\d.]+)"', svg)]
    assert len(seen) >= 7 and all(dash >= 4 and gap >= 4 for dash, gap in seen), seen  # six arrows and the legend
    assert "Asynchronous: event or message" in svg and "Direction of data" in svg


def test_status_tags_and_planned_outline_export(renders):
    svg = (renders(ROOT / "examples" / "orderplatform-toegang.yaml") / "orderplatform-toegang.svg").read_text(encoding="utf-8")
    assert ">nieuw</text>" in svg and ">gepland</text>" in svg
    assert f'stroke-dasharray="{config.tokens()["--dash-planned"]}"' in svg


# C3: rail and side-spoke notes stay readable
def test_side_column_notes_wrap_at_most_twice():
    for name, sides in (("ontwikkelplatform-lagen", ["security", "observability"]), ("orderplatform-eventbus", ["ops"])):
        spec = sp.load_spec(ROOT / "examples" / f"{name}.yaml")
        with sync_playwright() as p:
            chromium = browser.launch(p)
            page = browser.open_plate(chromium, html.build_html(spec), spec)
            lines = page.evaluate("""(ids) => ids.flatMap((id) => [...document.querySelectorAll(`[data-id="${id}"] .cnote`)]
                .map((el) => Math.round(el.getBoundingClientRect().height / parseFloat(getComputedStyle(el).lineHeight))))""", sides)
            chromium.close()
        assert max(lines) <= 3, (name, lines)  # a note on at most three lines: it wraps at most twice


# C4: a compact matrix
def test_matrix_is_as_wide_as_its_content(renders):
    out = renders(ROOT / "examples" / "orderplatform-eventbus.yaml")
    snap = json.loads((out / "_work" / "orderplatform-eventbus.snapshot.json").read_text())
    left, _, right, _ = snap["boxes"]["bus.matrix0"]
    assert right - left - 24 < 420  # row label to last column, inside the 12 px padding


# C11: print sizes
def test_a3_at_300_dpi(tmp_path):
    # Taller than the sheet, so it is scaled to fit: the SVG is the sheet in mm, the PNG the exact sheet at 300 dpi
    spec = sp.load_spec(ROOT / "examples" / "orderplatform-toegang.yaml")
    spec["canvas"]["size"] = "a3-landscape"
    code, report = run("build", write(tmp_path, spec, "a3"), "--out", tmp_path, "--dpi", 300)
    assert (code, report["errors"]) == (0, [])
    from PIL import Image
    with Image.open(tmp_path / "a3.png") as im:
        assert im.size == (4961, 3508) and round(im.info["dpi"][0]) == 300
    assert 0.9 < report["paper"]["scale"] < 1
    assert 'width="420mm" height="297mm"' in (tmp_path / "a3.svg").read_text(encoding="utf-8")[:400]


# The A4 sheet is too small for the event bus plate: one finding says how small its text would print
def test_a4_names_the_print_size(tmp_path):
    spec = sp.load_spec(ROOT / "examples" / "orderplatform-eventbus.yaml")
    spec["canvas"]["size"] = "a4-landscape"
    code, report = run("lint", write(tmp_path, spec, "a4"), "--out", tmp_path)
    found = [e for e in report["errors"] if e["check"] == "print-size"]
    assert code == 1 and len(found) == 1 and "pt (the floor is 6 pt)" in found[0]["detail"]


# C9: a skip connection goes around, along the row gutter, not through the panels between
def test_skip_connection_routes_along_the_row_gutter(renders):
    path = ROOT / "tests" / "fixtures" / "skip-connection.yaml"
    snap = json.loads((renders(path) / "_work" / "skip-connection.snapshot.json").read_text())
    route = next(f for f in snap["flows"] if (f["from"], f["to"]) == ("clients", "services"))
    top_row_bottom = snap["boxes"]["clients"][3]
    data_top = snap["boxes"]["data"][1]
    (x1, y1), (_, y_mid), _, (x4, y4) = route["points"]
    assert len(route["points"]) == 4 and top_row_bottom < y_mid < data_top and y1 > top_row_bottom and y4 > top_row_bottom
    code, report = run("lint", path, "--out", renders(path))
    assert (code, report["errors"]) == (0, [])


# C10: an SVG people can edit
def test_svg_has_named_groups_and_a_description(renders):
    import xml.etree.ElementTree as ET
    path = ROOT / "examples" / "orderplatform-toegang.yaml"
    root = ET.parse(renders(path) / "orderplatform-toegang.svg").getroot()
    ns = {"s": "http://www.w3.org/2000/svg"}
    ids = {g.get("id") for g in root.iter("{http://www.w3.org/2000/svg}g") if g.get("id")}
    spec = sp.load_spec(path)
    assert {f"panel-{p['id']}" for p in spec["panels"]} <= ids
    assert {f"flow-{i}" for i in range(len(spec["flows"]))} <= ids
    assert "card-gateway.card1" in ids
    assert root.find("s:desc", ns).text.startswith(spec["subtitle"])


def test_outline_text_replaces_text_with_paths(tmp_path):
    pytest.importorskip("uharfbuzz")
    code, report = run("build", ROOT / "examples" / "orderplatform-eventbus.yaml", "--out", tmp_path, "--outline-text")
    assert (code, report["errors"]) == (0, [])
    svg = (tmp_path / "orderplatform-eventbus.svg").read_text(encoding="utf-8")
    assert "<text" not in svg and "@font-face" not in svg
    # The outlines land where Chromium drew the text: against the text version, only rasteriser noise differs.
    with sync_playwright() as p:
        chromium = browser.launch(p)
        browser.rasterise_svg(chromium, tmp_path / "orderplatform-eventbus.svg", tmp_path / "outlined.png", scale=1)
        chromium.close()
    diff = images.image_diff(tmp_path / "_work" / "svg.png", tmp_path / "outlined.png", tmp_path / "mask.png")
    width, height = browser.svg_size(tmp_path / "orderplatform-eventbus.svg")
    assert diff["count"] < 0.0005 * width * height, diff["detail"]


@pytest.mark.skipif(not shutil.which("rsvg-convert"), reason="needs rsvg-convert (librsvg)")
def test_outlined_svg_looks_the_same_outside_chromium(tmp_path):
    """librsvg ignores the embedded fonts and sets live text in a system font, so only the outlined SVG is the same
    plate there; shapes, connectors and icons must match Chromium's PNG either way."""
    pytest.importorskip("uharfbuzz")
    code, report = run("build", ROOT / "examples" / "portal-roadmap.yaml", "--out", tmp_path, "--outline-text")
    assert (code, report["errors"]) == (0, [])
    png = tmp_path / "portal-roadmap.png"
    width, height = images.Image.open(png).size
    subprocess.run(["rsvg-convert", "-w", str(width), "-h", str(height), "-b", "white", "-o", tmp_path / "rsvg.png",
                    tmp_path / "portal-roadmap.svg"], check=True)
    diff = images.image_diff(png, tmp_path / "rsvg.png", tmp_path / "mask.png")
    assert not diff["fail"] and diff["count"] < 0.0005 * width * height, diff["detail"]


# D2 and D7: sources travel with the cards; build writes an outline next to the images
def test_refs_reach_the_svg_and_the_outline_is_written(tmp_path):
    spec = sp.load_spec(ROOT / "examples" / "orderplatform-toegang.yaml")
    spec["sources"] = [{"id": "adr", "kind": "document", "ref": "docs/adr/0007-gateway.md"}]
    for p in spec["panels"]:
        for c in p.get("cards", []):
            c["refs"] = ["adr: section 2"]
    code, report = run("build", write(tmp_path, spec, "traced"), "--out", tmp_path)
    assert (code, report["errors"], report["warnings"]) == (0, [], [])
    assert 'data-refs="adr: section 2"' in (tmp_path / "traced.svg").read_text(encoding="utf-8")
    md = (tmp_path / "traced.md").read_text(encoding="utf-8")
    assert md.startswith("# " + spec["title"]) and "## Open vragen" in md and "Token validatie" in md


# A rail card with a layer sits level with that layer's cards, and the arrow it sends there runs straight
def test_rail_cards_sit_level_with_their_layer(renders):
    path = ROOT / "examples" / "ontwikkelplatform-lagen.yaml"
    snap = json.loads((renders(path) / "_work" / f"{path.stem}.snapshot.json").read_text(encoding="utf-8"))
    boxes = snap["boxes"]
    assert abs(boxes["policy"][1] - boxes["admission"][1]) <= 2
    assert abs(boxes["security.card0"][1] - boxes["experience.card0"][1]) <= 2
    flow = next(f for f in snap["flows"] if f["from"] == "policy")
    assert len(flow["points"]) == 2  # straight


# The slide profile: larger type, a higher floor; a lane header that the larger title outgrows is caught
def test_slide_profile_scales_type_and_lint_catches_header_overflow(tmp_path):
    spec = sp.load_spec(ROOT / "examples" / "incident-swimlane.yaml")
    spec["canvas"].update(size="landscape-16x9", profile="slide")
    report = pipeline_build(write(tmp_path, spec, "slide"), tmp_path / "a")
    assert report["errors"] == []
    layout = json.loads((Path(report["snapshot"]).parent / "slide.layout.json").read_text(encoding="utf-8"))
    sizes = [it["font"]["size"] for g in layout["items"] for it in g.get("items", []) if it["kind"] == "text"]
    assert max(sizes) >= 52  # the title
    narrow = pipeline_build(write(tmp_path, spec, "narrow"), tmp_path / "b", theme_css=":root { --lane-head: 170px; }")
    assert ("text-overflow", "comms") in [(e["check"], e["id"]) for e in narrow["errors"]]


def pipeline_build(path, out, theme_css=""):
    from schemantic import pipeline
    return pipeline.build(path, out, deliver=False, theme_css=theme_css)


# A long handoff back up a swimlane goes round the edge in a second outer lane, past one that already uses the first
def test_a_swimlane_handoff_crosses_the_lanes_between_its_steps(renders):
    """A handoff over a lane runs through that lane's empty cell, not round the plate's edge: here the draft goes
    straight down past the committee to the team lead, and the decision straight up from the portal to the applicant."""
    path = ROOT / "tests" / "fixtures" / "swimlane-return.yaml"
    snap = json.loads((renders(path) / "_work" / f"{path.stem}.snapshot.json").read_text(encoding="utf-8"))
    edge = snap["boxes"]["body"][2]
    assert all(x <= edge for f in snap["flows"] for x, _ in f["points"])
    straight = {(f["from"], f["to"]) for f in snap["flows"] if len(f["points"]) == 2}
    assert {("draft", "sign"), ("publish", "decision")} <= straight


# Holes outside panels: a short panel next to taller ones in its row, and an empty run inside a zone frame
def test_void_checks_space_beside_short_panels_and_inside_zones(tmp_path):
    from schemantic import pipeline
    spec = sp.load_spec(ROOT / "examples" / "orderplatform-toegang.yaml")
    clients = next(p for p in spec["panels"] if p["id"] == "clients")
    clients["cards"], clients["chips"] = clients["cards"][:1], []
    found = pipeline.build(write(tmp_path, spec, "short"), tmp_path / "a", deliver=False)["warnings"]
    assert any(w["check"] == "void" and w["id"] == "clients" and "in its row" in w["detail"] for w in found)
    spec = sp.load_spec(ROOT / "examples" / "kliniek-zones.yaml")
    next(p for p in spec["panels"] if p["id"] == "proxy")["cards"] = spec["panels"][0]["cards"][:1]
    found = pipeline.build(write(tmp_path, spec, "zone"), tmp_path / "b", deliver=False)["warnings"]
    # Top-level frames end with their content, so the hole is inside a frame or below a short one beside a tall one
    assert any(w["check"] == "void" and w["id"].startswith("zone.") and ("zone frame" in w["detail"] or "tallest zone"
               in w["detail"]) for w in found), found


def test_void_checks_empty_cells_spread_cards_and_a_blank_band(tmp_path):
    from schemantic import pipeline
    voids = lambda report: [w["id"] for w in report["warnings"] if w["check"] == "void"]  # noqa: E731
    spec = sp.load_spec(ROOT / "examples" / "orderplatform-toegang.yaml")
    spec["layout"]["areas"][1] = "data data data ."
    report = pipeline.build(write(tmp_path, spec, "cell"), tmp_path / "a", deliver=False)
    assert "layout.areas" in voids(report) and report["voids"]["layout.areas.r2c4"] > 96
    # The bus's operations cards are spread 47 px apart, under half their height; with names only they float.
    spec = sp.load_spec(ROOT / "examples" / "orderplatform-eventbus.yaml")
    ops = next(p for p in spec["panels"] if p["id"] == "ops")
    assert "ops" not in voids(pipeline.build(write(tmp_path, spec, "rich"), tmp_path / "b", deliver=False))
    ops["cards"] = [{k: c[k] for k in ("id", "icon", "name") if k in c} for c in ops["cards"]]
    assert "ops" in voids(pipeline.build(write(tmp_path, spec, "bare"), tmp_path / "c", deliver=False))
    spec = sp.load_spec(ROOT / "examples" / "kliniek-zones.yaml")
    spec["canvas"].update(size="landscape-16x9", height="fixed")
    report = pipeline.build(write(tmp_path, spec, "band"), tmp_path / "d", deliver=False)
    assert "canvas" in voids(report) and report["voids"]["canvas"] > 96


def test_cards_joined_inside_their_panel_get_room_for_a_straight_arrow(tmp_path):
    """The default gap between cards is shorter than an arrowhead, so a flow from one card to the card below it used to
    leave the panel and come back; a panel with such a flow spaces its cards so the arrow runs straight down."""
    spec = sp.load_spec(ROOT / "examples" / "kliniek-zones.yaml")
    proxy = next(p for p in spec["panels"] if p["id"] == "proxy")
    proxy["cards"][0]["id"], proxy["cards"][1]["id"] = "mtls", "accesslog"
    spec["flows"].append({"from": "mtls", "to": "accesslog"})
    spec.pop("stories", None)
    code, report = run("lint", write(tmp_path, spec, "linked"), "--out", tmp_path)
    assert code == 0, report["errors"]
    snap = json.loads((tmp_path / "_work" / "linked.snapshot.json").read_text(encoding="utf-8"))
    (flow,) = [f for f in snap["flows"] if (f["from"], f["to"]) == ("mtls", "accesslog")]
    assert len(flow["points"]) == 2 and flow["points"][0][0] == flow["points"][1][0]  # one vertical run
    assert flow["points"][1][1] - flow["points"][0][1] >= 32  # holds a step badge and a head, or two heads and some shaft


def test_a_card_under_a_header_is_reached_up_the_gutter(renders):
    """The calendars come from a wide card in the bottom panel to Sync, above a chip: no straight line, and the route
    starts under its own panel's header. It leaves through the header's empty band and turns in up the gutter."""
    path = ROOT / "tests" / "fixtures" / "gutter-route.yaml"
    code, report = run("lint", path, "--out", renders(path))
    assert (code, report["errors"]) == (0, [])
    snap = json.loads((renders(path) / "_work" / f"{path.stem}.snapshot.json").read_text(encoding="utf-8"))
    (route,) = [f for f in snap["flows"] if (f["from"], f["to"]) == ("clinics", "sync")]
    booking, web = snap["boxes"]["booking"], snap["boxes"]["web"]
    assert len(route["points"]) == 3 and web[2] < route["points"][0][0] < booking[0]  # one bend, up the gutter between


def test_outside_panels_can_stand_in_a_row_under_the_zones(tmp_path):
    """A short panel in the outside column floats beside tall zones with blank space around it; under them it is a row."""
    spec = sp.load_spec(ROOT / "examples" / "kliniek-zones.yaml")
    spec["layout"]["outside_at"] = "bottom"
    code, report = run("lint", write(tmp_path, spec, "below"), "--out", tmp_path)
    assert not [e for e in report["errors"] if e["check"] in ("schema", "layout")], report["errors"]
    boxes = json.loads((tmp_path / "_work" / "below.snapshot.json").read_text(encoding="utf-8"))["boxes"]
    frames = [b for k, b in boxes.items() if k.startswith("zone.") and k.count(".") == 1]
    patients, insurers = boxes["patients"], boxes["insurers"]
    assert patients[1] >= max(b[3] for b in frames if b) and patients[1] == insurers[1] and patients[2] < insurers[0]


def test_a_zone_that_holds_zones_takes_the_whole_row(tmp_path):
    """Beside a cluster of namespaces, a small zone stands stretched; it wraps under the cluster instead, also when
    the outside panels leave the account the whole width of the plate."""
    spec = sp.load_spec(ROOT / "examples" / "kliniek-zones.yaml")
    spec["layout"]["outside_at"] = "bottom"
    cloud = next(z for z in spec["layout"]["zones"] if z["id"] == "cloud")
    moved = cloud["zones"][0]["zones"].pop()
    cloud["zones"].append(moved)
    run("lint", write(tmp_path, spec, "wrap"), "--out", tmp_path)
    boxes = json.loads((tmp_path / "_work" / "wrap.snapshot.json").read_text(encoding="utf-8"))["boxes"]
    assert boxes[f"zone.{moved['id']}"][1] >= boxes["zone.cluster"][3]
