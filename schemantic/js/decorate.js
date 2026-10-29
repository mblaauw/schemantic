// Strokes CSS cannot hand to the exporter exactly: dashed outlines of planned boxes, strike-throughs of removed
// names, and the line-style samples in the legend. Drawn once as SVG over the laid-out plate; the exporter copies
// that SVG as it is, so HTML and SVG match. Runs before routing; it changes no layout.
schemantic.decorate = () => {
  const S = schemantic;
  const plate = S.plate();
  const P = plate.getBoundingClientRect();
  const { r2 } = S;
  const items = [];
  const colour = (c) => S.hex(S.rgba(c) || [0, 0, 0, 1]);
  const dashOf = { sync: "", async: S.token("--dash-async"), optional: S.token("--dash-optional") };

  for (const el of plate.querySelectorAll("[data-dash]")) {
    const cs = getComputedStyle(el);
    const w = S.num(cs.borderTopWidth);
    const r = S.rel(el, P);
    const rx = Math.max(0, S.num(cs.borderTopLeftRadius) - w / 2);
    items.push(
      `<rect x="${r2(r.l + w / 2)}" y="${r2(r.t + w / 2)}" width="${r2(r.r - r.l - w)}" height="${r2(r.b - r.t - w)}" rx="${r2(rx)}" fill="none" stroke="${colour(cs.borderTopColor)}" stroke-width="${w}" stroke-dasharray="${S.token("--dash-planned")}"/>`,
    );
    el.style.borderColor = "transparent";
  }

  for (const el of plate.querySelectorAll("[data-strike]")) {
    const rg = document.createRange();
    rg.selectNodeContents(el);
    const cs = getComputedStyle(el);
    for (const q of rg.getClientRects()) {
      const y = q.top - P.top + q.height * 0.56;
      items.push(
        `<line x1="${r2(q.left - P.left)}" y1="${r2(y)}" x2="${r2(q.right - P.left)}" y2="${r2(y)}" stroke="${colour(cs.color)}" stroke-width="1.25"/>`,
      );
    }
  }

  for (const el of plate.querySelectorAll("[data-line]")) {
    const r = S.rel(el, P);
    const y = (r.t + r.b) / 2;
    const [x1, x2, w] = [r.l + 2, r.r - 2, S.px("--arrow-width")];
    const pattern = dashOf[el.dataset.line];
    const run = [
      [x1, y],
      [x2, y],
    ];
    const dash = pattern && S.fitDash(pattern, run, w);
    items.push(
      `<line x1="${r2(x1)}" y1="${r2(y)}" x2="${r2(x2)}" y2="${r2(y)}" stroke="${S.token("--arrow")}" stroke-width="${w}" stroke-linecap="round"${dash ? ` stroke-dasharray="${dash}"` : ""}/>`,
    );
  }

  if (!items.length) return 0;
  const ov = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  ov.setAttribute("data-raw-svg", "");
  ov.setAttribute("width", P.width);
  ov.setAttribute("height", P.height);
  ov.style.cssText = "position:absolute;left:0;top:0;pointer-events:none;overflow:visible";
  ov.innerHTML = `<g id="decorations" inkscape:label="decorations">${items.join("")}</g>`;
  plate.appendChild(ov);
  return items.length;
};
