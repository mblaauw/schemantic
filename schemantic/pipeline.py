"""One pipeline, one Chromium, in stages: prepare (read, theme, check), lay out (route, lint, measure), write the SVG,
check parity against the same page, write the deliverables, publish. `lint` is this without the deliverables.
Deliverables are written to <out>/_work/ first and move to <out>/ only when the build has no errors, so a failed build
never publishes a plate."""
from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
from importlib.metadata import version
from pathlib import Path

from playwright.sync_api import sync_playwright

from . import __version__, archetypes, outline
from .browser import launch, on_sheet, open_plate, rasterise_svg
from .config import FONTS_DIR, paper_fit
from .export import export_svg, measure, on_paper
from .findings import finding, grouped
from .html import build_html
from .images import image_diff, snapshot
from .lint import dom_lint, layout_findings
from .review import RASTER_SCALE, changed_parts, moved_parts, write_crops
from .route import draw_flows, problems_as_findings
from .spec import assumed_items, check, number_story, read_spec, source_quotes


def load_theme(spec: dict, spec_path: Path, theme: str | Path | None) -> tuple[str, list[dict]]:
    """The theme CSS: the --theme file if given, else canvas.theme relative to the spec, else none."""
    named = (spec.get("canvas") or {}).get("theme") if isinstance(spec.get("canvas"), dict) else None
    path = Path(theme) if theme else (spec_path.parent / named if named else None)
    if path is None:
        return "", []
    if not path.is_file():
        return "", [finding("canvas", "canvas.theme", f"theme file not found: {path}")]
    return path.read_text(encoding="utf-8"), []


def manifest(spec: dict, spec_path: Path, theme_css: str, chromium: str) -> dict:
    """What made this plate, so a render can be reproduced: versions, and digests of the spec, theme and fonts."""
    digest = lambda data: hashlib.sha256(data).hexdigest()[:16]
    return {"schemantic": __version__, "spec_version": spec.get("spec_version", 1), "spec_sha256": digest(spec_path.read_bytes()),
            "theme_sha256": digest(theme_css.encode()) if theme_css else None, "chromium": chromium,
            "playwright": version("playwright"), "python": platform.python_version(), "platform": platform.system().lower(),
            "fonts": {f.name: digest(f.read_bytes()) for f in sorted(FONTS_DIR.glob("*.woff2"))}}


def prepare(spec_path: Path, theme: str | Path | None, theme_css: str) -> tuple[dict | None, str, list[dict]]:
    """Stage 1, no browser: read the spec, load its theme, and check it. Returns the spec, the theme CSS and findings."""
    spec, issues = read_spec(spec_path)
    if not issues:
        file_css, issues = load_theme(spec, spec_path, theme)
        theme_css = "\n".join(c for c in (file_css, theme_css) if c)
    if not issues:
        issues = check(spec, theme_css)
    if not any(i["level"] == "error" for i in issues):
        issues += source_quotes(spec, spec_path.parent)
        spec = number_story(archetypes.get(spec["archetype"]).expand(spec))
    return spec, theme_css, issues


def open_routed(browser, html: str, spec: dict, refused: list[str]) -> tuple:
    """Load the plate and route its connectors. Panels evened out to the height of their row can close the gap a route
    or a label needed; a plate with such a problem is laid out again without them, since a route matters more."""
    page = open_plate(browser, html, spec, refused=refused)
    flows = draw_flows(page, spec)
    if flows["problems"] and page.locator(".evened").count():
        page.close()
        page = open_plate(browser, html, spec, refused=refused, even=False)
        flows = draw_flows(page, spec)
    return page, flows


def lay_out(page, flows: dict, spec: dict, work: Path, name: str) -> dict:
    """Stage 2, in the page: lint the routed layout, measure it into the layout document (written to _work/) and fit it to
    paper. Returns the layout, flows, DOM lint, paper fit and their findings."""
    dom = dom_lint(page, flows["segs"], slide=spec["canvas"].get("profile") == "slide")
    layout = measure(page)
    (work / f"{name}.layout.json").write_text(json.dumps(layout, ensure_ascii=False), encoding="utf-8")
    fit = paper_fit(spec["canvas"]["size"], layout["width"], layout["height"])
    issues = problems_as_findings(flows) + dom["issues"] + layout_findings(layout, spec, fit)
    return {"layout": layout, "flows": flows, "dom": dom, "fit": fit, "issues": issues}


def write_svg(plate: dict, spec: dict, work: Path, name: str, outline_text: bool) -> dict:
    """Stage 3: the SVG and the structural snapshot, both from the layout document; parity checks the layout with real
    text, so with outline_text the deliverable has glyph paths and a text version stays in _work/ for the check."""
    svg, fonts = export_svg(plate["layout"], spec)
    svg_path = work / f"{name}.svg"
    parity_svg = work / f"{name}.text.svg" if outline_text else svg_path
    parity_svg.write_text(svg, encoding="utf-8")
    if outline_text:
        from .glyphs import outline_text as to_paths
        svg_path.write_text(to_paths(svg), encoding="utf-8")
    snap_path = work / f"{name}.snapshot.json"
    previous = json.loads(snap_path.read_text(encoding="utf-8")) if snap_path.exists() else None
    snap = snapshot(plate["layout"], plate["flows"]["segs"])
    snap_path.write_text(json.dumps(snap, indent=1, ensure_ascii=False), encoding="utf-8")
    return {"svg": svg_path, "parity_svg": parity_svg, "fonts": fonts, "snapshot": snap_path, "snap": snap,
            "changed": changed_parts(previous, snap, spec)}


def parity(page, browser, parity_svg: Path, work: Path, refused: list[str]) -> dict:
    """Stage 4: the page as laid out (connectors included) against the SVG rasterised at the same scale. Closes the
    page: nothing after this reads it."""
    page.locator("#plate").screenshot(path=str(work / "html.png"))
    page.close()
    rasterise_svg(browser, parity_svg, work / "svg.png", scale=1, refused=refused)
    return image_diff(work / "html.png", work / "svg.png", work / "parity-diff.png")


def review_crops(browser, layout: dict, spec: dict, svg: dict, work: Path, name: str, refused: list[str], every: bool) -> dict:
    """Optional: crops of the plate a model can read, in _work/review/<name>/, so the parts of a series built into one
    folder keep their own. Every crop is written each time, so one a model
    has not read yet is never lost to a rebuild; after the first round `crops` holds the whole plate and the parts changed
    since the last round, and `unchanged` the others, unless every part is asked for."""
    dest = work / "review" / name
    last = dest / "snapshot.json"
    previous = None if every or not last.exists() else json.loads(last.read_text(encoding="utf-8"))
    changed = changed_parts(previous, svg["snap"], spec)
    for old in dest.glob("*.png"):
        old.unlink()  # a part renamed or cut differently leaves no stale crop behind
    rasterise_svg(browser, svg["parity_svg"], work / "review.png", scale=RASTER_SCALE, refused=refused)
    crops = write_crops(layout, spec, work / "review.png", dest)
    last.write_text(json.dumps(svg["snap"], ensure_ascii=False), encoding="utf-8")
    keep = lambda c: changed is None or c is crops[0] or c["part"].split(",")[0] in changed  # noqa: E731
    return {"crops": [c for c in crops if keep(c)], "unchanged": [c for c in crops if not keep(c)]}


def deliverables(browser, spec: dict, made: dict, svg_path: Path, fit: dict | None, scale: float, work: Path, name: str,
                 refused: list[str]) -> dict[str, Path]:
    """Stage 5: the outline, the manifest and the PNG, next to the SVG in _work/. A paper plate is rasterised at its
    paper scale and centred on the exact sheet at the requested dpi, and its SVG gets the sheet's size in mm. Returns
    the staged files, which publish() moves to <out>/ when the report is clean."""
    (work / f"{name}.md").write_text(outline.markdown(spec), encoding="utf-8")
    (work / f"{name}.build.json").write_text(json.dumps(made, indent=1) + "\n", encoding="utf-8")
    png = work / f"{name}.png"
    if fit:
        rasterise_svg(browser, svg_path, png, scale=fit["scale"] * scale, refused=refused)
        on_sheet(png, fit, 96 * scale)
        svg_path.write_text(on_paper(svg_path.read_text(encoding="utf-8"), fit), encoding="utf-8")
    else:
        rasterise_svg(browser, svg_path, png, scale=scale, refused=refused)
    return {k: work / f"{name}.{ext}" for k, ext in (("svg", "svg"), ("png", "png"), ("outline", "md"), ("manifest", "build.json"))}


def page_findings(refused: list[str], par: dict) -> list[dict]:
    """What the browser saw: requests that would have left the machine, and the parity verdict."""
    out = [finding("network", "(plate)", f"tried to load {url}") for url in dict.fromkeys(refused)]
    if par["fail"]:
        out.append(finding("svg-parity", "(plate)", par["detail"]))
    elif par["count"]:
        out.append(finding("svg-parity", "(plate)", par["detail"], level="warning"))
    return out


def set_baseline(spec_path: str | Path, out: str | Path) -> dict:
    """Before a correction: keep the plate as delivered, so each build until the next baseline says what differs from it."""
    name, out = Path(spec_path).stem, Path(out)
    md, snap = out / f"{name}.md", out / "_work" / f"{name}.snapshot.json"
    if not md.exists() or not snap.exists():
        return {"errors": [finding("yaml", "(file)", f"no delivered plate '{name}' in {out}: build it first")], "warnings": []}
    dest = out / "_work" / "baseline" / name
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copy(md, dest / "plate.md")
    shutil.copy(snap, dest / "snapshot.json")
    return {"baseline": str(dest), "errors": [], "warnings": []}


def since_baseline(spec: dict, snap: dict, work: Path, name: str) -> dict | None:
    """What differs from the baseline: outline lines gone and new (an arrow that now points elsewhere shows here by the
    names at its ends), the parts whose content changed, and the parts that only moved. None without a baseline."""
    dest = work / "baseline" / name
    if not (dest / "plate.md").exists():
        return None
    old = [line for line in (dest / "plate.md").read_text(encoding="utf-8").splitlines() if line.strip()]
    new = [line for line in outline.markdown(spec).splitlines() if line.strip()]
    base = json.loads((dest / "snapshot.json").read_text(encoding="utf-8"))
    return {"removed": [line for line in old if line not in new], "added": [line for line in new if line not in old],
            "parts_changed": changed_parts(base, snap, spec), "parts_moved": moved_parts(base, snap, spec)}


def publish(staged: dict[str, Path], report: dict, out: Path) -> None:
    """Move the staged deliverables to <out>/ when the report has no errors; otherwise name them under `preview`."""
    if not staged:
        return
    if report["errors"]:
        report["preview"] = {k: str(v) for k, v in staged.items()}
        return
    out.mkdir(parents=True, exist_ok=True)
    for k, src in staged.items():
        os.replace(src, out / src.name)  # atomic per file: a reader sees the old plate or the new one
        if k != "manifest":
            report[k] = str(out / src.name)


def build(spec_path: str | Path, out: str | Path, *, deliver: bool = True, scale: float = 2,
          theme: str | Path | None = None, theme_css: str = "", outline_text: bool = False, review: bool | str = False) -> dict:
    """Run the whole pipeline. With deliver, writes <out>/<name>.svg and .png; work files go to <out>/_work/.
    Returns the report: errors and warnings (each with a hint), density, parity, the build manifest, and the paths
    published (None when the build has errors; then `preview` names the unpublished files in _work/). `changed` names
    the parts (title block, panels, footer) that differ from the previous build in this folder. With review, `review`
    lists crops of the plate a model can read, in <out>/_work/review/<name>/ (also for a build with errors): after the first
    round the whole plate and the parts changed since the last one; `review_unchanged` lists the crops of the others,
    still on disk; review="all" lists every part. `assumptions` lists what the plate marks as assumed, then the brief's.
    `since_baseline` says what differs from the plate `set_baseline` kept, if any."""
    spec_path, out = Path(spec_path), Path(out)
    name, work = spec_path.stem, Path(out) / "_work"
    report = {"spec": str(spec_path), "summary": [], "errors": [], "warnings": [], "density": {}, "voids": {}, "parity": None,
              "svg": None, "png": None, "outline": None, "snapshot": None, "fonts": [], "flow_problems": [], "build": None, "preview": None,
              "changed": None, "review": None, "review_unchanged": None, "assumptions": [], "since_baseline": None}
    spec, theme_css, issues = prepare(spec_path, theme, theme_css)
    if not any(i["level"] == "error" for i in issues):
        report["assumptions"] = assumed_items(spec) + (spec.get("brief") or {}).get("assumptions", [])
    staged: dict[str, Path] = {}  # deliverables written to _work/, waiting for a clean report
    refused: list[str] = []  # network requests the page tried to make
    if not any(i["level"] == "error" for i in issues):
        work.mkdir(parents=True, exist_ok=True)
        html = build_html(spec, theme_css)
        (work / f"{name}.html").write_text(html, encoding="utf-8")
        with sync_playwright() as p:
            browser = launch(p)
            try:
                report["build"] = manifest(spec, spec_path, theme_css, browser.version)
                page, flows = open_routed(browser, html, spec, refused)
                plate = lay_out(page, flows, spec, work, name)
                svg = write_svg(plate, spec, work, name, outline_text)
                par = parity(page, browser, svg["parity_svg"], work, refused)
                if review:
                    shot = review_crops(browser, plate["layout"], spec, svg, work, name, refused, every=review == "all")
                    report.update(review=shot["crops"], review_unchanged=shot["unchanged"])
                if deliver:
                    staged = deliverables(browser, spec, report["build"], svg["svg"], plate["fit"], scale, work, name, refused)
            finally:
                browser.close()
        issues += plate["issues"] + page_findings(refused, par)
        if plate["fit"]:
            report["paper"] = {"size": plate["fit"]["size"], "scale": round(plate["fit"]["scale"], 3)}
        report["since_baseline"] = since_baseline(spec, svg["snap"], work, name)
        report.update(changed=svg["changed"], density=plate["dom"]["density"], voids=plate["dom"]["voids"], fonts=svg["fonts"],
                      snapshot=str(svg["snapshot"]),
                      parity={"pixels": par["count"], "regions": par["regions"], "detail": par["detail"]},
                      flow_problems=[dict(flow=spec["flows"][x["i"]], check=x["check"], problem=x["problem"])
                                     for x in plate["flows"]["problems"]])
    report.update(grouped(issues))
    publish(staged, report, out)
    return report
