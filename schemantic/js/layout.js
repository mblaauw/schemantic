// Walk the laid-out plate into a layout document: what to draw and where, as Chromium measured it. Nested groups
// (one per element with a kind and an id, with its box: left, top, right, bottom) hold rects, border lines, text lines, icons, and the connectors and
// decorations already drawn as SVG in the page. Python writes the SVG from it (export.py), so the exporter is a
// pure function of this document, and the document can be read, saved and tested on its own.
// Returns { width, height, items, used } where `used` maps each font face to the characters drawn (for subsetting).
schemantic.layout = () => {
  const S = schemantic;
  const plate = S.plate();
  const P = plate.getBoundingClientRect();
  const used = {};
  const { num } = S;
  const f = S.r2;
  const use = (family, weight, s) => {
    const k = `${family.split(",")[0].replace(/["']/g, "").trim()}|${weight}`;
    used[k] = (used[k] || "") + s;
  };
  const paint = (c) => {
    const pc = S.rgba(c);
    if (!pc) return null;
    return pc[3] < 1 ? { color: S.hex(pc), opacity: f(pc[3]) } : { color: S.hex(pc) };
  };
  // Measured at the real size: Chromium rounds ascent per size, so a 100 px probe scaled down drifts by a pixel.
  const offsets = {};
  const baseline = (cs) => {
    const key = `${cs.fontFamily}|${cs.fontWeight}|${cs.fontSize}`;
    if (key in offsets) return offsets[key];
    const probe = document.createElement("div");
    probe.style.cssText = `position:absolute;left:-9999px;top:0;font-family:${cs.fontFamily};font-weight:${cs.fontWeight};font-size:${cs.fontSize};line-height:normal;white-space:nowrap`;
    probe.innerHTML = 'H<span style="display:inline-block;width:1px;height:0;vertical-align:baseline"></span>';
    document.body.appendChild(probe);
    const rg = document.createRange();
    rg.setStart(probe.firstChild, 0);
    rg.setEnd(probe.firstChild, 1);
    const top = rg.getClientRects()[0].top;
    const base = probe.lastChild.getBoundingClientRect().bottom;
    probe.remove();
    offsets[key] = base - top;
    return offsets[key];
  };

  // A box's background and borders: one stroked rect when all four borders match (inset by half the stroke, as
  // CSS paints it), else a filled rect and a line per border.
  const box = (el, cs, out) => {
    const r = el.getBoundingClientRect();
    const x = r.left - P.left;
    const y = r.top - P.top;
    const w = r.width;
    const h = r.height;
    if (w < 0.5 || h < 0.5) return;
    const sides = ["Top", "Right", "Bottom", "Left"];
    const bw = sides.map((s) => (cs[`border${s}Style`] === "none" ? 0 : num(cs[`border${s}Width`])));
    const bc = sides.map((s) => cs[`border${s}Color`]);
    const radii = ["TopLeft", "TopRight", "BottomRight", "BottomLeft"].map((s) => num(cs[`border${s}Radius`]));
    const fill = paint(cs.backgroundColor);
    const uniform = bw[0] > 0 && bw.every((v) => v === bw[0]) && bc.every((c) => c === bc[0]);
    const stroke = uniform ? paint(bc[0]) : null;
    if (stroke) {
      const s = bw[0];
      out.push({
        kind: "rect",
        x: f(x + s / 2),
        y: f(y + s / 2),
        w: f(w - s),
        h: f(h - s),
        radii: radii.map((v) => f(Math.max(0, v - s / 2))),
        fill,
        stroke,
        strokeWidth: f(s),
      });
      return;
    }
    if (fill) out.push({ kind: "rect", x: f(x), y: f(y), w: f(w), h: f(h), radii: radii.map(f), fill });
    const lines = [
      [x, y + bw[0] / 2, x + w, y + bw[0] / 2],
      [x + w - bw[1] / 2, y, x + w - bw[1] / 2, y + h],
      [x, y + h - bw[2] / 2, x + w, y + h - bw[2] / 2],
      [x + bw[3] / 2, y, x + bw[3] / 2, y + h],
    ];
    lines.forEach((l, i) => {
      const st = bw[i] > 0 ? paint(bc[i]) : null;
      if (st)
        out.push({
          kind: "line",
          x1: f(l[0]),
          y1: f(l[1]),
          x2: f(l[2]),
          y2: f(l[3]),
          stroke: st,
          strokeWidth: f(bw[i]),
        });
    });
  };

  // A text node as the lines Chromium broke it into: each line starts where its first visible character does, and
  // the SVG viewer shapes the line with the same embedded font (kerning and ligatures included).
  const text = (node, out) => {
    const el = node.parentElement;
    const cs = getComputedStyle(el);
    const s = node.textContent;
    if (!s.trim() || cs.visibility === "hidden") return;
    const fs = num(cs.fontSize);
    const ascent = baseline(cs);
    const pre = cs.whiteSpace.startsWith("pre");
    use(cs.fontFamily, cs.fontWeight, s);
    const font = { family: cs.fontFamily, size: f(fs), weight: cs.fontWeight };
    const lines = [];
    let cur = null;
    const rg = document.createRange();
    for (let i = 0; i < s.length; i++) {
      rg.setStart(node, i);
      rg.setEnd(node, i + 1);
      const rects = rg.getClientRects();
      if (!rects.length) continue;
      const q = rects[0];
      if (!cur || Math.abs(q.top - cur.top) > fs * 0.5) {
        cur = { top: q.top, left: null, t: "" };
        lines.push(cur);
      }
      if (cur.left === null) {
        if (!pre && s[i].trim() === "") continue;
        cur.left = q.left;
      }
      cur.t += s[i];
    }
    for (const l of lines) {
      const t = pre ? l.t.replace(/\s+$/, "") : l.t.replace(/\s+/g, " ").trim();
      if (!t || l.left === null) continue;
      out.push({
        kind: "text",
        x: f(l.left - P.left),
        y: f(l.top - P.top + ascent),
        text: t,
        font,
        fill: paint(cs.color),
        preserve: pre,
      });
    }
  };

  const icon = (el, cs, out) => {
    const r = el.getBoundingClientRect();
    const c = S.rgba(cs.color);
    out.push({
      kind: "icon",
      x: f(r.left - P.left),
      y: f(r.top - P.top),
      size: r.width,
      stroke: c ? S.hex(c) : "currentColor",
      strokeWidth: el.getAttribute("stroke-width") || "1.75",
      svg: el.innerHTML,
    });
  };

  // The paint contract: what the document can describe is backgrounds, solid borders, radii, text (family, size,
  // weight, colour) and icons. CSS that paints anything else would show in the page and not in the SVG, so it is
  // reported by element and property instead of surfacing later as an unexplained parity difference.
  const unsupported = [];
  const set = (v, none) => v && !none.includes(v);
  const CONTRACT = [
    ["box-shadow", (cs) => set(cs.boxShadow, ["none"])],
    ["text-shadow", (cs) => set(cs.textShadow, ["none"])],
    ["background-image", (cs) => set(cs.backgroundImage, ["none"])],
    ["transform", (cs) => set(cs.transform, ["none"])],
    ["opacity", (cs) => set(cs.opacity, ["1"])],
    ["filter", (cs) => set(cs.filter, ["none"])],
    ["clip-path", (cs) => set(cs.clipPath, ["none"])],
    ["text-transform", (cs) => set(cs.textTransform, ["none"])],
    ["letter-spacing", (cs) => set(cs.letterSpacing, ["normal", "0px"])],
    ["word-spacing", (cs) => set(cs.wordSpacing, ["normal", "0px"])],
    ["text-decoration", (cs) => set(cs.textDecorationLine, ["none"])],
    ["font-style", (cs) => set(cs.fontStyle, ["normal"])],
    ["outline", (cs) => set(cs.outlineStyle, ["none"]) && num(cs.outlineWidth) > 0],
    [
      "border-style",
      (cs) => ["Top", "Right", "Bottom", "Left"].some((s) => set(cs[`border${s}Style`], ["none", "solid", "hidden"])),
    ],
    ["list-style", (cs) => cs.display === "list-item" && set(cs.listStyleType, ["none"])],
  ];
  const check = (node, cs) => {
    const where = node.closest("[data-id]")?.dataset.id || "(plate)";
    const what = node.classList[0] ? `.${node.classList[0]}` : node.tagName.toLowerCase();
    for (const [prop, used] of CONTRACT)
      if (used(cs)) unsupported.push({ id: where, element: what, property: prop, value: cs.getPropertyValue(prop) });
    for (const pseudo of ["::before", "::after"]) {
      const content = getComputedStyle(node, pseudo).content;
      if (set(content, ["none", "normal"]))
        unsupported.push({ id: where, element: `${what}${pseudo}`, property: "content", value: content });
    }
  };

  const walk = (node, out) => {
    if (node.nodeType === 3) {
      text(node, out);
      return;
    }
    if (node.nodeType !== 1) return;
    const cs = getComputedStyle(node);
    if (cs.display === "none" || cs.visibility === "hidden") return;
    if (node.hasAttribute("data-raw-svg")) {
      // Connectors, labels, step badges, dashes: the page already drew them as SVG.
      out.push({ kind: "svg", svg: node.innerHTML });
      for (const t of node.querySelectorAll("text"))
        use(t.getAttribute("font-family"), t.getAttribute("font-weight") || "400", t.textContent);
      return;
    }
    if (node.hasAttribute("data-icon")) {
      icon(node, cs, out);
      return;
    }
    check(node, cs);
    // Every element with a kind and an id becomes a named group, nested as in the page, so an editor shows layers.
    const { kind, id } = node.dataset || {};
    let inner = out;
    if (kind && id) {
      const title =
        kind === "panel" ? node.querySelector(".ph-title") : kind === "card" ? node.querySelector(".cn > span") : null;
      const b = node.getBoundingClientRect();
      const group = {
        kind: "group",
        type: kind,
        id,
        label: `${kind}: ${title ? title.textContent.trim() : id}`,
        box: [f(b.left - P.left), f(b.top - P.top), f(b.right - P.left), f(b.bottom - P.top)],
        items: [],
      };
      if (node.dataset.refs) group.refs = node.dataset.refs;
      out.push(group);
      inner = group.items;
    }
    box(node, cs, inner);
    for (const c of node.childNodes) walk(c, inner);
  };
  const items = [];
  walk(plate, items);
  return { width: f(P.width), height: f(P.height), items, used, unsupported };
};
