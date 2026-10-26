// Walk the laid-out plate and write every visible box, border, text line and icon as native SVG, at the
// measured positions. Returns the SVG items and, per font face, the characters drawn (for subsetting).
schemantic.exportSvg = () => {
  const S = schemantic;
  const plate = S.plate();
  const P = plate.getBoundingClientRect();
  const out = [];
  const used = {};
  const { num, esc } = S;
  const f = S.r2;
  const use = (family, weight, s) => {
    const k = `${family.split(",")[0].replace(/["']/g, "").trim()}|${weight}`;
    used[k] = (used[k] || "") + s;
  };
  const paint = (c, key) => {
    const pc = S.rgba(c);
    if (!pc) return null;
    return pc[3] < 1 ? `${key}="${S.hex(pc)}" ${key}-opacity="${f(pc[3])}"` : `${key}="${S.hex(pc)}"`;
  };
  const rr = (x, y, w, h, r) => {
    const [tl, tr, br, bl] = r.map((v) => Math.max(0, Math.min(v, w / 2, h / 2)));
    return (
      `M${f(x + tl)} ${f(y)}H${f(x + w - tr)}${tr ? `A${f(tr)} ${f(tr)} 0 0 1 ${f(x + w)} ${f(y + tr)}` : ""}` +
      `V${f(y + h - br)}${br ? `A${f(br)} ${f(br)} 0 0 1 ${f(x + w - br)} ${f(y + h)}` : ""}` +
      `H${f(x + bl)}${bl ? `A${f(bl)} ${f(bl)} 0 0 1 ${f(x)} ${f(y + h - bl)}` : ""}` +
      `V${f(y + tl)}${tl ? `A${f(tl)} ${f(tl)} 0 0 1 ${f(x + tl)} ${f(y)}` : ""}Z`
    );
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

  const box = (el, cs) => {
    const r = el.getBoundingClientRect();
    const x = r.left - P.left;
    const y = r.top - P.top;
    const w = r.width;
    const h = r.height;
    if (w < 0.5 || h < 0.5) return;
    const sides = ["Top", "Right", "Bottom", "Left"];
    const bw = sides.map((s) => (cs[`border${s}Style`] === "none" ? 0 : num(cs[`border${s}Width`])));
    const bc = sides.map((s) => cs[`border${s}Color`]);
    const rad = ["TopLeft", "TopRight", "BottomRight", "BottomLeft"].map((s) => num(cs[`border${s}Radius`]));
    const fill = paint(cs.backgroundColor, "fill");
    const id = el.dataset?.id ? ` data-id="${esc(el.dataset.id)}"` : "";
    const sameR = rad.every((v) => v === rad[0]);
    const uniform = bw[0] > 0 && bw.every((v) => v === bw[0]) && bc.every((c) => c === bc[0]);
    const st0 = uniform ? paint(bc[0], "stroke") : null;
    if (uniform && st0) {
      const s = bw[0];
      const st = st0;
      const [ix, iy, iw, ih] = [x + s / 2, y + s / 2, w - s, h - s];
      const ir = rad.map((v) => Math.max(0, v - s / 2));
      const pa = `${fill || 'fill="none"'} ${st || ""} stroke-width="${f(s)}"`;
      out.push(
        sameR
          ? `<rect${id} x="${f(ix)}" y="${f(iy)}" width="${f(iw)}" height="${f(ih)}"${ir[0] ? ` rx="${f(ir[0])}"` : ""} ${pa}/>`
          : `<path${id} d="${rr(ix, iy, iw, ih, ir)}" ${pa}/>`,
      );
      return;
    }
    if (fill)
      out.push(
        sameR
          ? `<rect${id} x="${f(x)}" y="${f(y)}" width="${f(w)}" height="${f(h)}"${rad[0] ? ` rx="${f(rad[0])}"` : ""} ${fill}/>`
          : `<path${id} d="${rr(x, y, w, h, rad)}" ${fill}/>`,
      );
    const lines = [
      [x, y + bw[0] / 2, x + w, y + bw[0] / 2],
      [x + w - bw[1] / 2, y, x + w - bw[1] / 2, y + h],
      [x, y + h - bw[2] / 2, x + w, y + h - bw[2] / 2],
      [x + bw[3] / 2, y, x + bw[3] / 2, y + h],
    ];
    lines.forEach((l, i) => {
      if (bw[i] <= 0) return;
      const st = paint(bc[i], "stroke");
      if (st)
        out.push(
          `<line x1="${f(l[0])}" y1="${f(l[1])}" x2="${f(l[2])}" y2="${f(l[3])}" ${st} stroke-width="${f(bw[i])}"/>`,
        );
    });
  };

  const text = (node) => {
    const el = node.parentElement;
    const cs = getComputedStyle(el);
    const s = node.textContent;
    if (!s.trim() || cs.visibility === "hidden") return;
    const fs = num(cs.fontSize);
    const ascent = baseline(cs);
    const pre = cs.whiteSpace.startsWith("pre");
    use(cs.fontFamily, cs.fontWeight, s);
    const attrs = `font-family="${esc(cs.fontFamily.replace(/"/g, "'"))}" font-size="${f(fs)}" font-weight="${cs.fontWeight}" ${paint(cs.color, "fill")}${pre ? ' xml:space="preserve"' : ""}`;
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
      out.push(`<text x="${f(l.left - P.left)}" y="${f(l.top - P.top + ascent)}" ${attrs}>${esc(t)}</text>`);
    }
  };

  const icon = (el, cs) => {
    const r = el.getBoundingClientRect();
    const c = S.rgba(cs.color);
    out.push(
      `<g transform="translate(${f(r.left - P.left)} ${f(r.top - P.top)}) scale(${(r.width / 24).toFixed(4)})" fill="none" stroke="${c ? S.hex(c) : "currentColor"}" stroke-width="${el.getAttribute("stroke-width") || 1.75}" stroke-linecap="round" stroke-linejoin="round">${el.innerHTML}</g>`,
    );
  };

  const walk = (node) => {
    if (node.nodeType === 3) {
      text(node);
      return;
    }
    if (node.nodeType !== 1) return;
    const cs = getComputedStyle(node);
    if (cs.display === "none" || cs.visibility === "hidden") return;
    if (node.hasAttribute("data-raw-svg")) {
      out.push(node.innerHTML);
      for (const t of node.querySelectorAll("text"))
        use(t.getAttribute("font-family"), t.getAttribute("font-weight") || "400", t.textContent);
      return;
    }
    if (node.hasAttribute("data-icon")) {
      icon(node, cs);
      return;
    }
    box(node, cs);
    for (const c of node.childNodes) walk(c);
  };
  walk(plate);
  return { w: f(P.width), h: f(P.height), items: out, used };
};
