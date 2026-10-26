"""Shared library for render.py and lint.py.

Pipeline: YAML spec -> schema + semantic checks -> HTML (CSS Grid, tokens) -> Chromium layout
-> flow arrows computed from measured boxes -> native SVG (rect/path/text/line) -> PNG raster of that SVG.
The model never writes coordinates; every position comes from the browser's layout.
"""
from __future__ import annotations

import base64
import io
import json
import re
from pathlib import Path

import jsonschema
import yaml
from fontTools import subset
from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).resolve().parent.parent
CANVAS_SIZES = {"landscape-4x3": (1600, 1200), "landscape-16x9": (1920, 1080)}
# Gutters hold the flow arrows: 48 px fits a 32 px arrow with 8 px clearance on both sides.
GUTTER_X = 48
# Row gutters also hold a one-line arrow label at 11 px.
GUTTER_Y = 44
TYPE_FLOOR_PX = 11
# Bundled faces (assets/fonts), loaded through @font-face so layout never depends on installed fonts.
# The HTML gets the full files; the SVG gets a subset of the glyphs it uses.
FONTS = [("Inter", 400, "Inter-Regular.woff2"), ("Inter", 500, "Inter-Medium.woff2"),
         ("Inter", 600, "Inter-SemiBold.woff2"), ("Inter", 700, "Inter-Bold.woff2"),
         ("Inter", 800, "Inter-ExtraBold.woff2"), ("DejaVu Sans Mono", 400, "DejaVuSansMono.woff2")]


# ---------------------------------------------------------------- spec

def load_spec(path: str | Path) -> dict:
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_locale(lang: str) -> dict:
    with open(ROOT / "locales" / f"{lang}.yaml", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def schema_errors(spec: dict) -> list[dict]:
    schema = json.loads((ROOT / "schema" / "plate.schema.json").read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    out = []
    for err in sorted(validator.iter_errors(spec), key=lambda e: list(e.path)):
        where = "/".join(str(p) for p in err.path) or "(root)"
        out.append({"level": "error", "check": "schema", "id": where, "detail": err.message})
    return out


def area_tokens(spec: dict) -> list[list[str]]:
    return [row.split() for row in spec["layout"]["areas"]]


def semantic_errors(spec: dict) -> list[dict]:
    """Checks the schema cannot express: areas, ids, flow endpoints, chips, language."""
    out = []
    err = lambda check, id_, detail, level="error": out.append(
        {"level": level, "check": check, "id": id_, "detail": detail})

    rows = area_tokens(spec)
    widths = {len(r) for r in rows}
    if len(widths) != 1:
        err("layout", "layout.areas", f"every row needs the same number of cells, got {sorted(widths)}")
        return out
    ncols = widths.pop()
    if ncols > 5:
        err("budget", "layout.areas", f"{ncols} body columns; the budget is 5. Split the plate.")
    names = {n for r in rows for n in r if n != "."}
    panel_ids = [p["id"] for p in spec["panels"]]
    for n in sorted(names - set(panel_ids)):
        err("layout", "layout.areas", f"area '{n}' has no panel")
    for n in sorted(set(panel_ids) - names):
        err("layout", n, "panel is not placed in layout.areas")
    for n in names:  # each area must be a rectangle
        cells = [(r, c) for r, row in enumerate(rows) for c, v in enumerate(row) if v == n]
        r0, r1 = min(r for r, _ in cells), max(r for r, _ in cells)
        c0, c1 = min(c for _, c in cells), max(c for _, c in cells)
        if len(cells) != (r1 - r0 + 1) * (c1 - c0 + 1):
            err("layout", n, "area is not a rectangle")
    cw = spec["layout"].get("column_widths")
    if cw and len(cw) != ncols:
        err("layout", "layout.column_widths", f"{len(cw)} widths for {ncols} columns")
    rh = spec["layout"].get("row_heights")
    if rh and len(rh) != len(rows):
        err("layout", "layout.row_heights", f"{len(rh)} heights for {len(rows)} rows")

    for p in spec["panels"]:
        if p.get("weights"):
            blocks = len(p.get("patterns", [])) + (1 if p.get("cards") else 0)
            if p.get("arrange") != "row":
                err("layout", p["id"], "weights only apply when arrange is row")
            elif len(p["weights"]) != blocks:
                err("layout", p["id"], f"{len(p['weights'])} weights for {blocks} blocks (patterns first, then cards)")

    known = set(panel_ids)
    for p in spec["panels"]:
        for i, c in enumerate(p.get("cards", [])):
            known.add(c.get("id") or f"{p['id']}.card{i}")
        for pt in p.get("patterns", []):
            if pt["type"] == "matrix":
                for r in pt["rows"]:
                    if len(r["cells"]) != len(pt["columns"]):
                        err("pattern", p["id"], f"matrix row '{r['name']}' has {len(r['cells'])} cells for {len(pt['columns'])} columns")
    for i, f in enumerate(spec.get("flows", [])):
        for end in ("from", "to"):
            if f[end] not in known:
                err("flow", f"flows/{i}", f"endpoint '{f[end]}' does not exist")

    oq = (spec.get("footer") or {}).get("open_questions") or {}
    chips = [ch["text"] for p in spec["panels"] for ch in p.get("chips", []) if ch["kind"] == "warning"]
    if chips and not oq.get("from_chips"):
        missing = [c for c in chips if c not in oq.get("extra", [])]
        for c in missing:
            err("chip-mirror", "footer.open_questions", f"warning chip not repeated in open questions: '{c}'")

    for icon in iter_icons(spec):
        if not (ROOT / "assets" / "icons" / f"{icon}.svg").exists():
            err("icon", icon, "icon not in assets/icons; pick one from the registry")

    loc = load_locale(spec["canvas"]["lang"])
    text = "\n".join(iter_strings(spec)).lower()
    for term, bad in (loc.get("never_translate") or {}).items():
        for b in bad:
            # Substring, not whole word: Dutch compounds hide the term ("productcatalogus").
            if re.search(re.escape(b.lower()), text):
                err("language", term, f"'{b}' found; keep the technical term '{term}' in English")
    return out


def iter_icons(spec: dict):
    for p in spec["panels"]:
        for c in p.get("cards", []):
            if c.get("icon"):
                yield c["icon"]
        for pt in p.get("patterns", []):
            for t in pt.get("tiers", []):
                if t.get("icon"):
                    yield t["icon"]
    ctx = (spec.get("footer") or {}).get("context") or {}
    for c in ctx.get("cards", []):
        if c.get("icon"):
            yield c["icon"]


def iter_strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            if k not in ("id", "icon", "role", "kind", "type", "tier", "areas", "from", "to"):
                yield from iter_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from iter_strings(v)


# ---------------------------------------------------------------- HTML

def grid_css(spec: dict) -> dict:
    """Insert gutter tracks between columns and rows; an area that spans cells also spans the gutter."""
    rows = area_tokens(spec)
    n, m = len(rows[0]), len(rows)
    lines = []
    for r, row in enumerate(rows):
        line = []
        for c, name in enumerate(row):
            line.append(name)
            if c < n - 1:
                line.append(name if row[c + 1] == name else ".")
        lines.append(line)
        if r < m - 1:
            nxt, gap = rows[r + 1], []
            for c in range(n):
                gap.append(row[c] if nxt[c] == row[c] else ".")
                if c < n - 1:
                    same = row[c] == row[c + 1] == nxt[c] == nxt[c + 1]
                    gap.append(row[c] if same else ".")
            lines.append(gap)
    widths = spec["layout"].get("column_widths") or [1] * n
    heights = spec["layout"].get("row_heights") or ["fill"] * m
    cols = f" {GUTTER_X}px ".join(f"minmax(0, {w}fr)" for w in widths)
    rows_css = f" {GUTTER_Y}px ".join("minmax(0, 1fr)" if h == "fill" else "auto" for h in heights)
    areas = " ".join('"' + " ".join(l) + '"' for l in lines)
    return {"columns": cols, "rows": rows_css, "areas": areas}


_icon_cache: dict[str, str] = {}


def icon_markup(name: str) -> str:
    if name not in _icon_cache:
        raw = (ROOT / "assets" / "icons" / f"{name}.svg").read_text(encoding="utf-8")
        inner = raw[raw.index(">", raw.index("<svg")) + 1: raw.rindex("</svg>")]
        inner = re.sub(r'<path stroke="none" d="M0 0h24v24H0z" fill="none"\s*/>', "", inner)
        _icon_cache[name] = re.sub(r"\s+", " ", inner).strip()
    return _icon_cache[name]


def tree_rows(lines: list[str]) -> list[dict]:
    out = []
    for line in lines:
        stripped = line.lstrip(" ")
        out.append({"depth": (len(line) - len(stripped)) // 2, "text": stripped})
    return out


def matrix_values(pt: dict) -> list[str]:
    used = {v for r in pt["rows"] for v in r["cells"]}
    return [v for v in ("full", "partial", "none") if v in used]


def legend_entries(spec: dict, loc: dict) -> list[dict]:
    entries, seen = [], set()
    for p in spec["panels"]:
        if p["role"] not in seen:
            seen.add(p["role"])
            entries.append({"kind": "role", "key": p["role"], "label": loc["legend"][p["role"]]})
    if spec.get("flows"):
        entries.append({"kind": "arrow", "key": "arrow", "label": loc["legend"]["arrow"]})
    kinds = []
    for p in spec["panels"]:
        for ch in p.get("chips", []):
            if ch["kind"] not in kinds:
                kinds.append(ch["kind"])
    for k in ("warning", "info"):
        if k in kinds:
            entries.append({"kind": "chip", "key": k, "label": loc["legend"][k]})
    return entries


def open_questions(spec: dict) -> list[str]:
    oq = (spec.get("footer") or {}).get("open_questions") or {}
    out = []
    if oq.get("from_chips"):
        out += [ch["text"] for p in spec["panels"] for ch in p.get("chips", []) if ch["kind"] == "warning"]
    out += [q for q in oq.get("extra", []) if q not in out]
    return out


def font_face(family: str, weight: int, data: bytes) -> str:
    uri = "data:font/woff2;base64," + base64.b64encode(data).decode("ascii")
    return f"@font-face {{ font-family: '{family}'; font-weight: {weight}; font-style: normal; src: url({uri}) format('woff2'); }}"


def font_css() -> str:
    return "\n".join(font_face(fam, w, (ROOT / "assets" / "fonts" / file).read_bytes()) for fam, w, file in FONTS)


def subset_font_css(used: dict[str, str]) -> str:
    """@font-face rules holding only the glyphs each bundled face draws. `used` maps 'Family|weight' to text."""
    rules = []
    for key, text in used.items():
        family, weight = key.split("|")
        faces = [f for f in FONTS if f[0] == family]
        if not faces:
            continue  # not bundled: the viewer's own fonts decide
        _, w, file = min(faces, key=lambda f: abs(f[1] - int(weight)))  # nearest weight, as the browser picks
        opts = subset.Options()
        opts.flavor = "woff2"
        opts.drop_tables.append("FFTM")  # FontForge timestamp; fontTools cannot subset it and warns
        sub = subset.Subsetter(opts)
        font = subset.load_font(str(ROOT / "assets" / "fonts" / file), opts)
        sub.populate(text=text)
        sub.subset(font)
        buf = io.BytesIO()
        subset.save_font(font, buf, opts)
        rules.append(font_face(family, w, buf.getvalue()))
    return "\n".join(rules)


def build_html(spec: dict) -> str:
    loc = load_locale(spec["canvas"]["lang"])
    width, height = CANVAS_SIZES[spec["canvas"]["size"]]
    env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=select_autoescape(["j2", "html"]))
    css = font_css() + "\n" + (ROOT / "templates" / "tokens.css").read_text(encoding="utf-8") + "\n" + \
          (ROOT / "templates" / "components.css").read_text(encoding="utf-8")
    canvas = spec["canvas"]
    badge = loc["badge"].format(part=canvas["part"], of=canvas["of"]) if canvas.get("part") and canvas.get("of") else None
    footer = spec.get("footer") or {}
    fcols = footer.get("columns") or [1.4, 1.4, 1.1, 0.9]
    return env.get_template("plate.html.j2").render(
        spec=spec, lang=canvas["lang"], L=loc, css=css, width=width, height=height, badge=badge,
        grid=grid_css(spec), footer=footer, footer_columns=" ".join(f"minmax(0, {w}fr)" for w in fcols),
        legend=legend_entries(spec, loc), open_questions=open_questions(spec),
        icons=icon_markup, tree_rows=tree_rows, matrix_values=matrix_values)


# ---------------------------------------------------------------- browser

def open_plate(browser, html: str, spec: dict, scale: float = 1):
    width, height = CANVAS_SIZES[spec["canvas"]["size"]]
    page = browser.new_page(viewport={"width": width, "height": height}, device_scale_factor=scale)
    page.set_content(html)
    page.evaluate(FONTS_READY_JS)
    return page


# Load every declared face before measuring, not only the ones layout has asked for so far.
FONTS_READY_JS = "Promise.all([...document.fonts].map(f => f.load())).then(() => document.fonts.ready).then(() => true)"


FLOWS_JS = r"""
(flows) => {
  const plate = document.getElementById('plate'), P = plate.getBoundingClientRect();
  const box = id => { const el = document.querySelector(`[data-id="${CSS.escape(id)}"]`); if (!el) return null;
    const r = el.getBoundingClientRect(); return {l: r.left - P.left, t: r.top - P.top, r: r.right - P.left, b: r.bottom - P.top}; };
  const css = getComputedStyle(document.documentElement);
  const col = css.getPropertyValue('--arrow').trim(), muted = css.getPropertyValue('--muted').trim();
  const font = css.getPropertyValue('--font').trim().replace(/"/g, "'");
  const segs = [], problems = []; let svg = '';
  const r2 = v => Math.round(v * 100) / 100;
  flows.forEach((fl, i) => {
    const A = box(fl.from), B = box(fl.to);
    if (!A || !B) { problems.push({i, problem: 'endpoint not found'}); return; }
    const pad = 7, minOverlap = 24;
    const oy = [Math.max(A.t, B.t), Math.min(A.b, B.b)], ox = [Math.max(A.l, B.l), Math.min(A.r, B.r)];
    let x1, y1, x2, y2, vertical = false;
    if (A.r <= B.l && oy[1] - oy[0] > minOverlap) { const y = (oy[0] + oy[1]) / 2; [x1, y1, x2, y2] = [A.r + pad, y, B.l - pad, y]; }
    else if (B.r <= A.l && oy[1] - oy[0] > minOverlap) { const y = (oy[0] + oy[1]) / 2; [x1, y1, x2, y2] = [A.l - pad, y, B.r + pad, y]; }
    else if (A.b <= B.t && ox[1] - ox[0] > minOverlap) { const x = (ox[0] + ox[1]) / 2; [x1, y1, x2, y2] = [x, A.b + pad, x, B.t - pad]; vertical = true; }
    else if (B.b <= A.t && ox[1] - ox[0] > minOverlap) { const x = (ox[0] + ox[1]) / 2; [x1, y1, x2, y2] = [x, A.t - pad, x, B.b + pad]; vertical = true; }
    else { problems.push({i, problem: 'no shared gutter between the two panels; move one or split the flow'}); return; }
    const len = Math.hypot(x2 - x1, y2 - y1);
    if (len < 14) { problems.push({i, problem: 'gutter too narrow for an arrow'}); return; }
    const dx = (x2 - x1) / len, dy = (y2 - y1) / len, L = 10, W = 6;
    const bx = x2 - dx * L, by = y2 - dy * L;
    svg += `<line x1="${r2(x1)}" y1="${r2(y1)}" x2="${r2(bx)}" y2="${r2(by)}" stroke="${col}" stroke-width="2.5" stroke-linecap="round"/>`;
    svg += `<path d="M${r2(x2)} ${r2(y2)}L${r2(bx - dy * W)} ${r2(by + dx * W)}L${r2(bx + dy * W)} ${r2(by - dx * W)}Z" fill="${col}"/>`;
    const seg = {i, from: fl.from, to: fl.to, x1, y1, x2, y2, label: null};
    if (fl.label) {
      if (!vertical) problems.push({i, problem: 'labels fit only on vertical arrows; drop the label or explain it in a card'});
      else {
        const lx = x1 + 9, ly = (y1 + y2) / 2 + 4;
        svg += `<text x="${r2(lx)}" y="${r2(ly)}" font-family="${font}" font-size="11.5" font-weight="500" fill="${muted}">${fl.label.replace(/&/g, '&amp;').replace(/</g, '&lt;')}</text>`;
        seg.label = {x: lx, y: ly, text: fl.label};
      }
    }
    segs.push(seg);
  });
  const ov = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  ov.setAttribute('data-raw-svg', ''); ov.setAttribute('width', P.width); ov.setAttribute('height', P.height);
  ov.style.cssText = 'position:absolute;left:0;top:0;pointer-events:none;overflow:visible';
  ov.innerHTML = svg; plate.appendChild(ov);
  for (const s of segs) if (s.label) {  // measure label boxes after insertion
    const t = [...ov.querySelectorAll('text')].find(e => e.textContent === s.label.text);
    const r = t.getBoundingClientRect(); s.label.box = {l: r.left - P.left, t: r.top - P.top, r: r.right - P.left, b: r.bottom - P.top};
  }
  return {segs, problems};
}
"""


def draw_flows(page, spec: dict) -> dict:
    return page.evaluate(FLOWS_JS, spec.get("flows", []))


EXPORT_JS = r"""
() => {
  const plate = document.getElementById('plate'), P = plate.getBoundingClientRect();
  const out = [], used = {};
  const use = (family, weight, s) => { const k = family.split(',')[0].replace(/["']/g, '').trim() + '|' + weight; used[k] = (used[k] || '') + s; };
  const num = v => parseFloat(v) || 0, f = v => Math.round(v * 100) / 100;
  const esc = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  const parse = c => { const m = c && c.match(/rgba?\(([^)]+)\)/); if (!m) return null;
    const p = m[1].split(/[\s,\/]+/).filter(Boolean).map(Number); const a = p.length > 3 ? p[3] : 1;
    if (a === 0) return null; return ['#' + p.slice(0, 3).map(v => Math.round(v).toString(16).padStart(2, '0')).join(''), a]; };
  const paint = (c, key) => { const pc = parse(c); if (!pc) return null;
    return pc[1] < 1 ? `${key}="${pc[0]}" ${key}-opacity="${f(pc[1])}"` : `${key}="${pc[0]}"`; };
  const rr = (x, y, w, h, r) => { const [tl, tr, br, bl] = r.map(v => Math.max(0, Math.min(v, w / 2, h / 2)));
    return `M${f(x + tl)} ${f(y)}H${f(x + w - tr)}` + (tr ? `A${f(tr)} ${f(tr)} 0 0 1 ${f(x + w)} ${f(y + tr)}` : '') +
      `V${f(y + h - br)}` + (br ? `A${f(br)} ${f(br)} 0 0 1 ${f(x + w - br)} ${f(y + h)}` : '') +
      `H${f(x + bl)}` + (bl ? `A${f(bl)} ${f(bl)} 0 0 1 ${f(x)} ${f(y + h - bl)}` : '') +
      `V${f(y + tl)}` + (tl ? `A${f(tl)} ${f(tl)} 0 0 1 ${f(x + tl)} ${f(y)}` : '') + 'Z'; };
  // Measured at the real size: Chromium rounds ascent per size, so a 100 px probe scaled down drifts by up to a pixel.
  const offsets = {};
  const baseline = cs => { const key = cs.fontFamily + '|' + cs.fontWeight + '|' + cs.fontSize; if (key in offsets) return offsets[key];
    const probe = document.createElement('div');
    probe.style.cssText = `position:absolute;left:-9999px;top:0;font-family:${cs.fontFamily};font-weight:${cs.fontWeight};font-size:${cs.fontSize};line-height:normal;white-space:nowrap`;
    probe.innerHTML = 'H<span style="display:inline-block;width:1px;height:0;vertical-align:baseline"></span>';
    document.body.appendChild(probe);
    const rg = document.createRange(); rg.setStart(probe.firstChild, 0); rg.setEnd(probe.firstChild, 1);
    const top = rg.getClientRects()[0].top, base = probe.lastChild.getBoundingClientRect().bottom;
    probe.remove(); return offsets[key] = base - top; };

  const box = (el, cs) => {
    const r = el.getBoundingClientRect(); const x = r.left - P.left, y = r.top - P.top, w = r.width, h = r.height;
    if (w < 0.5 || h < 0.5) return;
    const sides = ['Top', 'Right', 'Bottom', 'Left'];
    const bw = sides.map(s => cs[`border${s}Style`] === 'none' ? 0 : num(cs[`border${s}Width`]));
    const bc = sides.map(s => cs[`border${s}Color`]);
    const rad = ['TopLeft', 'TopRight', 'BottomRight', 'BottomLeft'].map(s => num(cs[`border${s}Radius`]));
    const fill = paint(cs.backgroundColor, 'fill');
    const id = el.dataset && el.dataset.id ? ` data-id="${esc(el.dataset.id)}"` : '';
    const sameR = rad.every(v => v === rad[0]);
    const uniform = bw[0] > 0 && bw.every(v => v === bw[0]) && bc.every(c => c === bc[0]);
    if (uniform) {
      const s = bw[0], st = paint(bc[0], 'stroke'); if (!st && !fill) return;
      const ix = x + s / 2, iy = y + s / 2, iw = w - s, ih = h - s, ir = rad.map(v => Math.max(0, v - s / 2));
      const pa = `${fill || 'fill="none"'} ${st || ''} stroke-width="${f(s)}"`;
      out.push(sameR ? `<rect${id} x="${f(ix)}" y="${f(iy)}" width="${f(iw)}" height="${f(ih)}"${ir[0] ? ` rx="${f(ir[0])}"` : ''} ${pa}/>`
                     : `<path${id} d="${rr(ix, iy, iw, ih, ir)}" ${pa}/>`);
      return;
    }
    if (fill) out.push(sameR ? `<rect${id} x="${f(x)}" y="${f(y)}" width="${f(w)}" height="${f(h)}"${rad[0] ? ` rx="${f(rad[0])}"` : ''} ${fill}/>`
                             : `<path${id} d="${rr(x, y, w, h, rad)}" ${fill}/>`);
    const L = [[x, y + bw[0] / 2, x + w, y + bw[0] / 2], [x + w - bw[1] / 2, y, x + w - bw[1] / 2, y + h],
               [x, y + h - bw[2] / 2, x + w, y + h - bw[2] / 2], [x + bw[3] / 2, y, x + bw[3] / 2, y + h]];
    L.forEach((l, i) => { if (bw[i] > 0) { const st = paint(bc[i], 'stroke'); if (st)
      out.push(`<line x1="${f(l[0])}" y1="${f(l[1])}" x2="${f(l[2])}" y2="${f(l[3])}" ${st} stroke-width="${f(bw[i])}"/>`); } });
  };

  const text = node => {
    const el = node.parentElement, cs = getComputedStyle(el), s = node.textContent;
    if (!s.trim() || cs.visibility === 'hidden') return;
    const fs = num(cs.fontSize), ascent = baseline(cs), pre = cs.whiteSpace.startsWith('pre');
    use(cs.fontFamily, cs.fontWeight, s);
    const attrs = `font-family="${esc(cs.fontFamily.replace(/"/g, "'"))}" font-size="${f(fs)}" font-weight="${cs.fontWeight}" ${paint(cs.color, 'fill')}${pre ? ' xml:space="preserve"' : ''}`;
    const lines = []; let cur = null; const rg = document.createRange();
    for (let i = 0; i < s.length; i++) {
      rg.setStart(node, i); rg.setEnd(node, i + 1);
      const rects = rg.getClientRects(); if (!rects.length) continue; const q = rects[0];
      if (!cur || Math.abs(q.top - cur.top) > fs * 0.5) { cur = {top: q.top, left: null, t: ''}; lines.push(cur); }
      if (cur.left === null) { if (!pre && s[i].trim() === '') continue; cur.left = q.left; }
      cur.t += s[i];
    }
    for (const l of lines) {
      let t = pre ? l.t.replace(/\s+$/, '') : l.t.replace(/\s+/g, ' ').trim();
      if (!t || l.left === null) continue;
      out.push(`<text x="${f(l.left - P.left)}" y="${f(l.top - P.top + ascent)}" ${attrs}>${esc(t)}</text>`);
    }
  };

  const icon = (el, cs) => {
    const r = el.getBoundingClientRect(), c = parse(cs.color);
    out.push(`<g transform="translate(${f(r.left - P.left)} ${f(r.top - P.top)}) scale(${(r.width / 24).toFixed(4)})" fill="none" stroke="${c ? c[0] : '#000'}" stroke-width="${el.getAttribute('stroke-width') || 1.75}" stroke-linecap="round" stroke-linejoin="round">${el.innerHTML}</g>`);
  };

  const walk = node => {
    if (node.nodeType === 3) { text(node); return; }
    if (node.nodeType !== 1) return;
    const cs = getComputedStyle(node);
    if (cs.display === 'none' || cs.visibility === 'hidden') return;
    if (node.hasAttribute('data-raw-svg')) { out.push(node.innerHTML);
      for (const t of node.querySelectorAll('text')) use(t.getAttribute('font-family'), t.getAttribute('font-weight') || '400', t.textContent);
      return; }
    if (node.hasAttribute('data-icon')) { icon(node, cs); return; }
    box(node, cs);
    for (const c of node.childNodes) walk(c);
  };
  walk(plate);
  return {w: f(P.width), h: f(P.height), items: out, used};
}
"""


def export_svg(page, spec: dict) -> tuple[str, list[str]]:
    d = page.evaluate(EXPORT_JS)
    title = spec["title"] + (f" — {spec['subtitle']}" if spec.get("subtitle") else "")
    esc = lambda s: s.replace("&", "&amp;").replace("<", "&lt;")
    head = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{d["w"]:g}" height="{d["h"]:g}" '
            f'viewBox="0 0 {d["w"]:g} {d["h"]:g}" role="img" lang="{spec["canvas"]["lang"]}">\n'
            f'<title>{esc(title)}</title>\n'
            f'<defs><style>\n{subset_font_css(d["used"])}\n</style></defs>\n')
    fonts = sorted(k.replace("|", " ") for k in d["used"])
    return head + "\n".join(d["items"]) + "\n</svg>\n", fonts


def rasterise_svg(browser, svg_path: Path, spec: dict, png_path: Path, scale: float = 2) -> None:
    width, height = CANVAS_SIZES[spec["canvas"]["size"]]
    page = browser.new_page(viewport={"width": width, "height": height}, device_scale_factor=scale)
    page.goto(svg_path.resolve().as_uri())
    page.evaluate(FONTS_READY_JS)
    page.screenshot(path=str(png_path), clip={"x": 0, "y": 0, "width": width, "height": height})
    page.close()
