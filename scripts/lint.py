#!/usr/bin/env python3
"""Lint a plate spec and its rendered layout. Prints a JSON report; exits 1 on any error.

Usage: python3 scripts/lint.py <spec.yaml> [--out DIR]

Spec checks: schema, areas, ids, flow endpoints, chip mirror, icons, never-translate terms.
Layout checks (in Chromium): text overflow, overlap, canvas fit, type floor, contrast,
arrow routing, arrow labels, chip length, panel density, SVG parity with the HTML layout.
Every finding names the element id, so the fix goes into the spec, not into the output.
"""
import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageFilter
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
import platelib as pl  # noqa: E402

# Panel content filling less than this share of its panel reads as "visibly emptier" (review question 4);
# 0.6 flagged the one panel a reviewer called empty in the first test plate and none of the others.
DENSITY_MIN = 0.6
# Parity is structural, not pixel-perfect: Chromium snaps HTML text and borders to whole pixels while the
# SVG keeps fractional positions. A 1.5 px blur absorbs that; a dropped card still leaves thousands of pixels.
PARITY_BLUR_PX = 1.5
PARITY_DELTA = 40           # grey-level difference (0-255) after blur
PARITY_ERROR_SHARE = 0.0001  # 0.01 % of the canvas, about 190 px at 1600 x 1200

LINT_JS = r"""
(cfg) => {
  const plate = document.getElementById('plate'), P = plate.getBoundingClientRect();
  const issues = [], add = (level, check, id, detail) => issues.push({level, check, id, detail});
  const rel = r => ({l: r.left - P.left, t: r.top - P.top, r: r.right - P.left, b: r.bottom - P.top});
  const idOf = el => { const k = el.closest('[data-id]'); return k ? k.dataset.id : '(plate)'; };
  const kindParent = el => el.parentElement ? el.parentElement.closest('[data-kind]') : null;
  const inter = (a, b) => Math.max(0, Math.min(a.r, b.r) - Math.max(a.l, b.l)) * Math.max(0, Math.min(a.b, b.b) - Math.max(a.t, b.t));
  const num = v => parseFloat(v) || 0;

  // Content box of a container (inside border and padding)
  const inner = el => { const r = rel(el.getBoundingClientRect()), cs = getComputedStyle(el);
    return {l: r.l + num(cs.borderLeftWidth) + num(cs.paddingLeft) - 1, r: r.r - num(cs.borderRightWidth) - num(cs.paddingRight) + 1,
            t: r.t + num(cs.borderTopWidth) + num(cs.paddingTop) - 1, b: r.b - num(cs.borderBottomWidth) - num(cs.paddingBottom) + 1}; };

  // Text: overflow, type floor, contrast
  const lum = c => { const m = c.match(/rgba?\(([^)]+)\)/); const p = m[1].split(/[\s,\/]+/).filter(Boolean).map(Number);
    const ch = p.slice(0, 3).map(v => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; });
    return 0.2126 * ch[0] + 0.7152 * ch[1] + 0.0722 * ch[2]; };
  const bgOf = el => { for (let e = el; e; e = e.parentElement) { const c = getComputedStyle(e).backgroundColor;
    if (c && !/rgba\(.*,\s*0\)$/.test(c) && c !== 'transparent') return c; } return 'rgb(255, 255, 255)'; };
  const worst = {};
  const tw = document.createTreeWalker(plate, NodeFilter.SHOW_TEXT);
  for (let n; (n = tw.nextNode());) {
    if (!n.textContent.trim()) continue;
    const el = n.parentElement, cs = getComputedStyle(el), fs = num(cs.fontSize), id = idOf(el);
    if (fs < cfg.floor) add('error', 'type-floor', id, `${fs}px text "${n.textContent.trim().slice(0, 30)}" is below ${cfg.floor}px`);
    const rg = document.createRange(); rg.selectNodeContents(n); const tr = rel(rg.getBoundingClientRect());
    const box = el.closest('[data-kind]') || plate;
    const ib = el.closest('svg') ? rel(box.getBoundingClientRect()) : inner(box);
    if (tr.r > ib.r + 0.5 || tr.l < ib.l - 0.5 || tr.b > ib.b + 0.5)
      add('error', 'text-overflow', id, `"${n.textContent.trim().slice(0, 40)}" runs ${Math.round(Math.max(tr.r - ib.r, ib.l - tr.l, tr.b - ib.b))}px outside its box`);
    const L1 = lum(cs.color), L2 = lum(bgOf(el)), ratio = (Math.max(L1, L2) + 0.05) / (Math.min(L1, L2) + 0.05);
    const large = fs >= 24 || (fs >= 18.66 && num(cs.fontWeight) >= 700), need = large ? 3 : 4.5;
    if (ratio < need && (!(id in worst) || ratio < worst[id].ratio)) worst[id] = {ratio, need, text: n.textContent.trim().slice(0, 30)};
  }
  for (const [id, w] of Object.entries(worst)) add('error', 'contrast', id, `"${w.text}" has ${w.ratio.toFixed(2)}:1, needs ${w.need}:1`);

  // Overlap between siblings, and canvas fit
  const kinds = [...plate.querySelectorAll('[data-kind]')];
  const groups = new Map();
  for (const el of kinds) { const p = kindParent(el) || plate; if (!groups.has(p)) groups.set(p, []); groups.get(p).push(el); }
  for (const list of groups.values()) for (let i = 0; i < list.length; i++) for (let j = i + 1; j < list.length; j++) {
    const a = rel(list[i].getBoundingClientRect()), b = rel(list[j].getBoundingClientRect());
    if (inter(a, b) > 2) add('error', 'overlap', list[i].dataset.id, `overlaps ${list[j].dataset.id}`);
  }
  // Containment: every box stays inside the content box of the box that holds it
  for (const el of kinds) {
    const p = kindParent(el); if (!p || ['body', 'footer'].includes(p.dataset.kind)) continue;
    const r = rel(el.getBoundingClientRect()), ib = inner(p);
    const over = Math.max(r.r - ib.r, r.b - ib.b, ib.l - r.l, ib.t - r.t);
    if (over > 1) add('error', 'containment', el.dataset.id, `runs ${Math.round(over)}px outside ${p.dataset.id}; cut content or give the panel more room`);
  }
  const pin = inner(plate);
  for (const el of kinds) { const r = rel(el.getBoundingClientRect());
    if (r.r > pin.r + 1 || r.b > pin.b + 1 || r.l < pin.l - 1 || r.t < pin.t - 1)
      add('error', 'canvas-fit', el.dataset.id, `extends ${Math.round(Math.max(r.r - pin.r, r.b - pin.b))}px past the canvas margin`); }

  // Arrows: no crossing of panels other than their endpoints; labels clear of every box
  const panels = kinds.filter(e => e.dataset.kind === 'panel');
  for (const s of cfg.segs) {
    const seg = {l: Math.min(s.x1, s.x2) - 1, r: Math.max(s.x1, s.x2) + 1, t: Math.min(s.y1, s.y2) - 1, b: Math.max(s.y1, s.y2) + 1};
    for (const p of panels) {
      const id = p.dataset.id, ends = [s.from, s.to].map(x => x.split('.')[0]);
      if (ends.includes(id)) continue;
      if (inter(seg, rel(p.getBoundingClientRect())) > 0) add('error', 'arrow-routing', `flows/${s.i}`, `arrow ${s.from} -> ${s.to} crosses panel ${id}`);
    }
    const containers = ['body', 'footer', 'titleblock'];
    if (s.label) for (const el of kinds) {
      if (containers.includes(el.dataset.kind)) continue;
      if (inter(s.label.box, rel(el.getBoundingClientRect())) > 0) { add('error', 'arrow-label', `flows/${s.i}`, `label "${s.label.text}" touches ${el.dataset.id}`); break; }
    }
  }

  // Chips: at most two lines
  for (const ch of plate.querySelectorAll('[data-kind="chip"]')) {
    const t = ch.lastElementChild, lh = num(getComputedStyle(t).lineHeight) || 17;
    const lines = Math.round(t.getBoundingClientRect().height / lh);
    if (lines > 2) add('error', 'chip-length', ch.dataset.id, `${lines} lines; a chip holds at most 2`);
  }

  // Density: content height against the panel body it sits in
  const density = {};
  for (const p of panels) {
    if (p.dataset.id.startsWith('footer.')) continue;
    const pb = p.querySelector('.pb'); const ib = inner(pb); const avail = ib.b - ib.t;
    let used = 0, gaps = 0; const kids = [...pb.children];
    for (const k of kids) used += k.getBoundingClientRect().height;
    gaps = (kids.length - 1) * num(getComputedStyle(pb).rowGap || getComputedStyle(pb).gap);
    const fill = Math.min(1, (used + gaps) / avail); density[p.dataset.id] = Math.round(fill * 100) / 100;
    if (fill < cfg.densityMin) add('warning', 'density', p.dataset.id, `content fills ${Math.round(fill * 100)}% of the panel; add substance, merge panels, or give this column less height`);
  }
  return {issues, density};
}
"""


def parity(browser, html: str, spec: dict, svg_path: Path, work: Path) -> dict:
    page = pl.open_plate(browser, html, spec, scale=1)
    pl.draw_flows(page, spec)
    page.locator("#plate").screenshot(path=str(work / "html.png"))
    page.close()
    pl.rasterise_svg(browser, svg_path, spec, work / "svg.png", scale=1)
    a = Image.open(work / "html.png").convert("L").filter(ImageFilter.GaussianBlur(PARITY_BLUR_PX))
    b = Image.open(work / "svg.png").convert("L").filter(ImageFilter.GaussianBlur(PARITY_BLUR_PX))
    if a.size != b.size:
        return {"share": 1.0, "detail": f"size differs: html {a.size} vs svg {b.size}", "bbox": None}
    mask = ImageChops.difference(a, b).point(lambda v: 255 if v > PARITY_DELTA else 0)
    count = mask.histogram()[255]
    mask.save(work / "parity-diff.png")
    return {"share": count / (a.size[0] * a.size[1]), "bbox": mask.getbbox(),
            "detail": f"{count} pixels differ after a {PARITY_BLUR_PX} px blur" + (f", within {mask.getbbox()}" if count else "")}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("spec")
    ap.add_argument("--out", default="out")
    a = ap.parse_args()

    spec_path = Path(a.spec)
    spec = pl.load_spec(spec_path)
    issues = pl.schema_errors(spec)
    if not issues:
        issues = pl.semantic_errors(spec)
    report = {"spec": str(spec_path), "errors": [], "warnings": [], "density": {}, "parity": None}
    if not any(i["level"] == "error" for i in issues):
        out, name = Path(a.out), spec_path.stem
        work = out / "_work"
        work.mkdir(parents=True, exist_ok=True)
        html = pl.build_html(spec)
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = pl.open_plate(browser, html, spec)
            flows = pl.draw_flows(page, spec)
            for x in flows["problems"]:
                issues.append({"level": "error", "check": "arrow-routing", "id": f"flows/{x['i']}", "detail": x["problem"]})
            dom = page.evaluate(LINT_JS, {"floor": pl.TYPE_FLOOR_PX, "segs": flows["segs"], "densityMin": DENSITY_MIN})
            issues += dom["issues"]
            report["density"] = dom["density"]
            svg, _ = pl.export_svg(page, spec)
            svg_path = work / f"{name}.lint.svg"
            svg_path.write_text(svg, encoding="utf-8")
            page.close()
            par = parity(browser, html, spec, svg_path, work)
            browser.close()
        report["parity"] = {"share": round(par["share"], 6), "detail": par["detail"]}
        if par["share"] > PARITY_ERROR_SHARE:
            issues.append({"level": "error", "check": "svg-parity", "id": "(plate)", "detail": par["detail"]})
        elif par["share"] > 0:
            issues.append({"level": "warning", "check": "svg-parity", "id": "(plate)", "detail": par["detail"]})
    report["errors"] = [i for i in issues if i["level"] == "error"]
    report["warnings"] = [i for i in issues if i["level"] == "warning"]
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
