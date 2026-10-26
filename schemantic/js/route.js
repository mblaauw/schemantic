// Orthogonal connector router. Endpoints are panels or cards; every route is checked against the measured boxes,
// so the spec never names a coordinate. Candidates: straight across a gutter, L (one bend), Z through a gutter
// channel (two bends). The cheapest clear one wins: length, plus a fixed price per bend, plus distance off-centre.
schemantic.route = (flows) => {
  const S = schemantic;
  const plate = S.plate();
  const P = plate.getBoundingClientRect();
  const rel = (el) => S.rel(el, P);
  const byId = (id) => document.querySelector(`[data-id="${CSS.escape(id)}"]`);
  const { r2, hits } = S;
  const mid = (a, b) => (a + b) / 2;
  const col = S.token("--arrow");
  const muted = S.token("--muted");
  const font = S.token("--font").replace(/"/g, "'");
  const labelSize = S.px("--label-size");
  const labelWeight = S.token("--label-weight");
  const stroke = S.px("--arrow-width");
  const onHead = S.token("--on-head");
  const dashes = { async: S.token("--dash-async"), optional: S.token("--dash-optional") };
  // Visual geometry comes from tokens; the rest are routing heuristics.
  const PAD = S.px("--arrow-gap");
  const HEAD = S.px("--arrow-head");
  const WING = S.px("--arrow-wing");
  const RADIUS = S.px("--arrow-radius");
  const LANE = S.px("--arrow-lane");
  const MIN_OVERLAP = 24; // shared span two boxes need for a straight arrow
  const CLEAR = 6; // free space kept around every segment
  const BEND = 60; // price of one bend, in px of route length
  const MIN_RUN = 16; // shortest middle segment

  // Boxes an arrow must not cross; panel headers count, so a card's arrow never runs through its own title.
  const solids = [
    ...plate.querySelectorAll(
      '[data-kind="panel"], [data-kind="card"], [data-kind="pattern"], [data-kind="chip"], [data-kind="titleblock"], .ph',
    ),
  ].map((el) => ({ el, box: rel(el) }));
  // Channels: the centre line of every gutter between two body panels, plus a lane on either side of it.
  const bodyPanels = [...document.querySelectorAll('#body [data-kind="panel"]')].map(rel);
  const chX = new Map();
  const chY = new Map();
  for (const a of bodyPanels) {
    for (const b of bodyPanels) {
      if (b.l > a.r && b.l - a.r < 100) {
        const c = mid(a.r, b.l);
        for (const o of [0, -LANE, LANE]) chX.set(r2(c + o), Math.abs(o));
      }
      if (b.t > a.b && b.t - a.b < 100) {
        const c = mid(a.b, b.t);
        for (const o of [0, -LANE, LANE]) chY.set(r2(c + o), Math.abs(o));
      }
    }
  }
  // Outer channels: along the body's edges, in the plate margin, for routes that must go around everything.
  // They cost more than any gutter channel, so they are the last resort.
  const OUTER = 80;
  const body = rel(document.getElementById("body"));
  for (const c of [body.l - 20, body.r + 20]) if (c > CLEAR && c < P.width - CLEAR) chX.set(r2(c), OUTER);
  for (const c of [body.t - 9, body.b + 9]) if (c > CLEAR && c < P.height - CLEAR) chY.set(r2(c), OUTER);
  // A U-route (out of one side, along a channel, back in on the same side) costs a little more than a Z.
  const U_COST = 40;

  const segBox = (p, q, m) => ({
    l: Math.min(p[0], q[0]) - m,
    r: Math.max(p[0], q[0]) + m,
    t: Math.min(p[1], q[1]) - m,
    b: Math.max(p[1], q[1]) + m,
  });
  const span = (a, b, c, d) => Math.min(Math.max(a, b), Math.max(c, d)) - Math.max(Math.min(a, b), Math.min(c, d));
  // Two parallel segments running on top of each other.
  const collinear = (p, q, u, v) => {
    const ph = p[1] === q[1];
    if (ph !== (u[1] === v[1])) return false;
    return ph
      ? Math.abs(p[1] - u[1]) < LANE - 2 && span(p[0], q[0], u[0], v[0]) > 0
      : Math.abs(p[0] - u[0]) < LANE - 2 && span(p[1], q[1], u[1], v[1]) > 0;
  };
  const runs = (pts) => pts.slice(1).map((q, k) => [pts[k], q]);
  const placed = [];
  const clear = (pts, obstacles, both, labels = true) => {
    const n = pts.length - 1;
    for (let k = 0; k < n; k++) {
      const p = pts[k];
      const q = pts[k + 1];
      const len = Math.abs(q[0] - p[0]) + Math.abs(q[1] - p[1]);
      const need = k === n - 1 || (both && k === 0) ? HEAD + 6 : k === 0 ? 8 : MIN_RUN;
      if (len < need) return false;
      const sb = segBox(p, q, CLEAR);
      if (sb.l < 0 || sb.t < 0 || sb.r > P.width || sb.b > P.height) return false;
      if (obstacles.some((o) => hits(sb, o)) || (labels && labelBoxes.some((o) => hits(sb, o)))) return false;
      if (placed.some((r) => runs(r.pts).some(([u, v]) => collinear(p, q, u, v)))) return false;
    }
    return true;
  };

  const candidates = (a, b) => {
    const out = [];
    const add = (pts, off) => out.push({ pts, off });
    const cx = (o) => mid(o.l, o.r);
    const cy = (o) => mid(o.t, o.b);
    // Points on a side: the centre, then the point nearest the other box.
    const pick = (lo, hi, toward) => {
      const m = mid(lo, hi);
      const n = Math.min(Math.max(toward, lo + 16), hi - 16);
      return hi - lo < 32 || Math.abs(n - m) < 1
        ? [[m, 0]]
        : [
            [m, 0],
            [n, Math.abs(n - m)],
          ];
    };
    // Straight: across the gap between facing sides, centred on the shared span, then a quarter off-centre.
    const oy = [Math.max(a.t, b.t), Math.min(a.b, b.b)];
    const ox = [Math.max(a.l, b.l), Math.min(a.r, b.r)];
    // Centred on the shared span; then one lane off-centre (two flows between the same boxes run side by side);
    // then a quarter off-centre.
    const along = (lo, hi) => [
      ...[0, -1, 1].map((s) => [mid(lo, hi) + s * LANE * 1.6, LANE * 1.6 * Math.abs(s)]),
      ...[-1, 1].map((s) => [mid(lo, hi) + (s * (hi - lo)) / 4, (hi - lo) / 4]),
    ];
    if (oy[1] - oy[0] > MIN_OVERLAP) {
      for (const [y, off] of along(...oy)) {
        if (a.r <= b.l)
          add(
            [
              [a.r + PAD, y],
              [b.l - PAD, y],
            ],
            off,
          );
        else if (b.r <= a.l)
          add(
            [
              [a.l - PAD, y],
              [b.r + PAD, y],
            ],
            off,
          );
      }
    }
    if (ox[1] - ox[0] > MIN_OVERLAP) {
      for (const [x, off] of along(...ox)) {
        if (a.b <= b.t)
          add(
            [
              [x, a.b + PAD],
              [x, b.t - PAD],
            ],
            off,
          );
        else if (b.b <= a.t)
          add(
            [
              [x, a.t - PAD],
              [x, b.b + PAD],
            ],
            off,
          );
      }
    }
    // L: leave A vertically, enter B from the side; or leave A sideways, enter B from top or bottom.
    for (const [x, o1] of pick(a.l, a.r, cx(b))) {
      for (const [y, o2] of pick(b.t, b.b, cy(a))) {
        if (x < b.l || x > b.r) {
          const ex = x < b.l ? b.l - PAD : b.r + PAD;
          if (y > a.b)
            add(
              [
                [x, a.b + PAD],
                [x, y],
                [ex, y],
              ],
              o1 + o2,
            );
          if (y < a.t)
            add(
              [
                [x, a.t - PAD],
                [x, y],
                [ex, y],
              ],
              o1 + o2,
            );
        }
      }
    }
    for (const [y, o1] of pick(a.t, a.b, cy(b))) {
      for (const [x, o2] of pick(b.l, b.r, cx(a))) {
        if (y < b.t || y > b.b) {
          const ey = y < b.t ? b.t - PAD : b.b + PAD;
          if (x > a.r)
            add(
              [
                [a.r + PAD, y],
                [x, y],
                [x, ey],
              ],
              o1 + o2,
            );
          if (x < a.l)
            add(
              [
                [a.l - PAD, y],
                [x, y],
                [x, ey],
              ],
              o1 + o2,
            );
        }
      }
    }
    // Z: sideways out of A, along a vertical channel, sideways into B (and the same turned a quarter).
    for (const [c, oc] of chX) {
      for (const [y1, o1] of pick(a.t, a.b, cy(b))) {
        for (const [y2, o2] of pick(b.t, b.b, cy(a))) {
          if (Math.abs(y1 - y2) < 1) continue;
          if (a.r < c && c < b.l)
            add(
              [
                [a.r + PAD, y1],
                [c, y1],
                [c, y2],
                [b.l - PAD, y2],
              ],
              oc + o1 + o2,
            );
          if (b.r < c && c < a.l)
            add(
              [
                [a.l - PAD, y1],
                [c, y1],
                [c, y2],
                [b.r + PAD, y2],
              ],
              oc + o1 + o2,
            );
        }
      }
    }
    for (const [c, oc] of chY) {
      for (const [x1, o1] of pick(a.l, a.r, cx(b))) {
        for (const [x2, o2] of pick(b.l, b.r, cx(a))) {
          if (Math.abs(x1 - x2) < 1) continue;
          if (a.b < c && c < b.t)
            add(
              [
                [x1, a.b + PAD],
                [x1, c],
                [x2, c],
                [x2, b.t - PAD],
              ],
              oc + o1 + o2,
            );
          if (b.b < c && c < a.t)
            add(
              [
                [x1, a.t - PAD],
                [x1, c],
                [x2, c],
                [x2, b.b + PAD],
              ],
              oc + o1 + o2,
            );
        }
      }
    }
    // U: out of A and into B on the same side, along a channel beyond both (for boxes side by side with others between).
    for (const [c, oc] of chY) {
      for (const [x1, o1] of pick(a.l, a.r, cx(b))) {
        for (const [x2, o2] of pick(b.l, b.r, cx(a))) {
          if (Math.abs(x1 - x2) < 1) continue;
          if (c > a.b && c > b.b)
            add(
              [
                [x1, a.b + PAD],
                [x1, c],
                [x2, c],
                [x2, b.b + PAD],
              ],
              oc + o1 + o2 + U_COST * 2,
            );
          if (c < a.t && c < b.t)
            add(
              [
                [x1, a.t - PAD],
                [x1, c],
                [x2, c],
                [x2, b.t - PAD],
              ],
              oc + o1 + o2 + U_COST * 2,
            );
        }
      }
    }
    for (const [c, oc] of chX) {
      for (const [y1, o1] of pick(a.t, a.b, cy(b))) {
        for (const [y2, o2] of pick(b.t, b.b, cy(a))) {
          if (Math.abs(y1 - y2) < 1) continue;
          if (c > a.r && c > b.r)
            add(
              [
                [a.r + PAD, y1],
                [c, y1],
                [c, y2],
                [b.r + PAD, y2],
              ],
              oc + o1 + o2 + U_COST * 2,
            );
          if (c < a.l && c < b.l)
            add(
              [
                [a.l - PAD, y1],
                [c, y1],
                [c, y2],
                [b.l - PAD, y2],
              ],
              oc + o1 + o2 + U_COST * 2,
            );
        }
      }
    }
    const length = (pts) => runs(pts).reduce((s, [p, q]) => s + Math.abs(q[0] - p[0]) + Math.abs(q[1] - p[1]), 0);
    return out
      .map((c) => ({ ...c, cost: length(c.pts) + BEND * (c.pts.length - 2) + c.off * 0.5 }))
      .sort((p, q) => p.cost - q.cost);
  };

  const problems = [];
  const routed = [];
  const jobs = flows
    .map((fl, i) => {
      const A = byId(fl.from);
      const B = byId(fl.to);
      if (!A || !B) {
        problems.push({ i, kind: "endpoint", problem: "endpoint not found" });
        return null;
      }
      if (A === B) {
        problems.push({ i, kind: "self", problem: "from and to are the same element" });
        return null;
      }
      if (A.contains(B) || B.contains(A)) {
        problems.push({ i, kind: "nested", problem: "connects a card to its own panel; connect it to another box" });
        return null;
      }
      const obstacles = solids
        .filter(
          (s) =>
            !(s.el === A || s.el === B || s.el.contains(A) || s.el.contains(B) || A.contains(s.el) || B.contains(s.el)),
        )
        .map((s) => s.box);
      return { i, fl, A, B, obstacles, cands: candidates(rel(A), rel(B)) };
    })
    .filter(Boolean);
  const ov = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  ov.setAttribute("data-raw-svg", "");
  ov.setAttribute("width", P.width);
  ov.setAttribute("height", P.height);
  ov.style.cssText = "position:absolute;left:0;top:0;pointer-events:none;overflow:visible";
  plate.appendChild(ov);

  // Labels: beside a vertical run or above/below a horizontal one, on the longest run first, clear of every box,
  // every arrow and every other label.
  const labelBoxes = [];
  const allBoxes = solids.map((s) => s.box);
  const textAttrs = `font-family="${font}" font-size="${labelSize}" font-weight="${labelWeight}"`;
  const measure = (text) => {
    ov.innerHTML = `<text x="0" y="0" ${textAttrs}>${S.esc(text)}</text>`;
    const r = ov.firstChild.getBoundingClientRect();
    ov.innerHTML = "";
    return { w: r.width, asc: P.top - r.top, desc: r.bottom - P.top };
  };
  const runLength = ([p, q]) => Math.abs(q[0] - p[0]) + Math.abs(q[1] - p[1]);
  const longestFirst = (pts) => runs(pts).sort((s, t) => runLength(t) - runLength(s));
  const placeLabel = (r) => {
    if (!r.fl.label) return;
    const { w, asc, desc } = measure(r.fl.label);
    const spots = [];
    for (const [p, q] of longestFirst(r.pts)) {
      if (p[0] === q[0]) {
        // Beside a vertical run: centred, then at its top or bottom end, to leave a lane free for a crossing route.
        const [top, bottom] = [Math.min(p[1], q[1]), Math.max(p[1], q[1])];
        if (bottom - top > asc + desc + 8)
          for (const y of [mid(p[1], q[1]) + 4, top + asc + 1, bottom - desc - 1])
            spots.push([p[0] + 9, y], [p[0] - 9 - w, y]);
      } else if (Math.abs(q[0] - p[0]) > w + 20) {
        const x = mid(p[0], q[0]) - w / 2;
        spots.push([x, p[1] - 6 - desc], [x, p[1] + 6 + asc]);
      }
    }
    const spot = spots.find(([x, y]) => {
      const b = { l: x - 3, r: x + w + 3, t: y - asc - 3, b: y + desc + 3 };
      return (
        b.l > 0 &&
        b.t > 0 &&
        b.r < P.width &&
        b.b < P.height &&
        !allBoxes.some((o) => hits(b, o)) &&
        !labelBoxes.some((o) => hits(b, o)) &&
        !placed.some((o) => runs(o.pts).some(([u, v]) => hits(b, segBox(u, v, 1.5))))
      );
    });
    if (!spot) {
      problems.push({ i: r.i, kind: "label", problem: `no room for the label "${r.fl.label}"; shorten it or drop it` });
      return;
    }
    r.labelBox = { l: spot[0], r: spot[0] + w, t: spot[1] - asc, b: spot[1] + desc };
    labelBoxes.push(r.labelBox);
    r.svg =
      (r.svg || "") +
      `<text data-label="${r.i}" data-text x="${r2(spot[0])}" y="${r2(spot[1])}" ${textAttrs} fill="${muted}">${S.esc(r.fl.label)}</text>`;
    r.label = { x: spot[0], y: spot[1], text: r.fl.label };
  };

  // Straight flows claim their gutters first and get their labels; bent ones then route around both, and get
  // theirs last.
  // A flow is straight when a straight candidate clears every box (other routes aside).
  const free = (pts, obstacles) => runs(pts).every(([p, q]) => !obstacles.some((o) => hits(segBox(p, q, CLEAR), o)));
  const bent = (j) => (j.cands.some((c) => c.pts.length === 2 && free(c.pts, j.obstacles)) ? 0 : 1);
  jobs.sort((p, q) => bent(p) - bent(q) || p.i - q.i);
  // Take a label off the plate, so it can be placed again around a route that needed its spot.
  const unplace = (r) => {
    labelBoxes.splice(labelBoxes.indexOf(r.labelBox), 1);
    r.svg = (r.svg || "").replace(/<text data-label="\d+" data-text[^>]*>.*?<\/text>/, "");
    r.labelBox = null;
    r.label = null;
  };
  const route = (j) => {
    let pick = j.cands.find((c) => clear(c.pts, j.obstacles, j.fl.both));
    if (!pick && labelBoxes.length) {
      // Blocked only by labels: take the route, then move the labels it touches to another spot along their arrow.
      pick = j.cands.find((c) => clear(c.pts, j.obstacles, j.fl.both, false));
      if (pick) {
        const moved = routed.filter(
          (o) => o.labelBox && runs(pick.pts).some(([u, v]) => hits(o.labelBox, segBox(u, v, CLEAR))),
        );
        for (const o of moved) unplace(o);
        placed.push({ pts: pick.pts });
        for (const o of moved) placeLabel(o);
        placed.pop();
      }
    }
    if (!pick) {
      problems.push({
        i: j.i,
        kind: "route",
        problem:
          "no clear route between the two boxes; connect their panels instead, or move one so they share a gutter",
      });
      return null;
    }
    const r = { ...j, pts: pick.pts };
    placed.push(r);
    routed.push(r);
    return r;
  };
  const first = jobs
    .filter((j) => !bent(j))
    .map(route)
    .filter(Boolean);
  for (const r of first) placeLabel(r);
  const later = jobs.filter(bent).map(route).filter(Boolean);

  // Step badges: a numbered disc on the longest run with room, before labels so labels keep clear of it.
  const BADGE = 9;
  for (const r of routed) {
    if (!r.fl.step) continue;
    const spot = longestFirst(r.pts)
      .filter((run) => runLength(run) >= 2 * BADGE + 2 * HEAD)
      .map(([p, q]) => [mid(p[0], q[0]), mid(p[1], q[1])])
      .find(([x, y]) => {
        const b = { l: x - BADGE - 2, r: x + BADGE + 2, t: y - BADGE - 2, b: y + BADGE + 2 };
        return !allBoxes.some((o) => hits(b, o)) && !labelBoxes.some((o) => hits(b, o));
      });
    if (!spot) {
      problems.push({
        i: r.i,
        kind: "label",
        problem: `no room for step badge ${r.fl.step}; shorten the plate or drop the step`,
      });
      continue;
    }
    const [x, y] = spot;
    labelBoxes.push({ l: x - BADGE, r: x + BADGE, t: y - BADGE, b: y + BADGE });
    r.svg =
      (r.svg || "") +
      `<circle cx="${r2(x)}" cy="${r2(y)}" r="${BADGE}" fill="${col}"/>` +
      `<text x="${r2(x)}" y="${r2(y + 4)}" text-anchor="middle" font-family="${font}" font-size="11" font-weight="700" fill="${onHead}">${r.fl.step}</text>`;
    r.step = { x, y, n: r.fl.step };
  }
  for (const r of later) placeLabel(r);

  // Draw: straight arrows as a line, bent ones as a path with rounded corners; heads are filled triangles.
  const head = (tip, from) => {
    const len = Math.hypot(tip[0] - from[0], tip[1] - from[1]);
    const dx = (tip[0] - from[0]) / len;
    const dy = (tip[1] - from[1]) / len;
    const bx = tip[0] - dx * HEAD;
    const by = tip[1] - dy * HEAD;
    const d = `M${r2(tip[0])} ${r2(tip[1])}L${r2(bx - dy * WING)} ${r2(by + dx * WING)}L${r2(bx + dy * WING)} ${r2(by - dx * WING)}Z`;
    return { base: [bx, by], svg: `<path d="${d}" fill="${col}"/>` };
  };
  const rounded = (pts) => {
    let d = `M${r2(pts[0][0])} ${r2(pts[0][1])}`;
    for (let k = 1; k < pts.length - 1; k++) {
      const [p, c, n] = [pts[k - 1], pts[k], pts[k + 1]];
      const lin = Math.hypot(c[0] - p[0], c[1] - p[1]);
      const lout = Math.hypot(n[0] - c[0], n[1] - c[1]);
      const rad = Math.min(RADIUS, lin / 2, lout / 2);
      const a = [c[0] - ((c[0] - p[0]) / lin) * rad, c[1] - ((c[1] - p[1]) / lin) * rad];
      const b = [c[0] + ((n[0] - c[0]) / lout) * rad, c[1] + ((n[1] - c[1]) / lout) * rad];
      d += `L${r2(a[0])} ${r2(a[1])}Q${r2(c[0])} ${r2(c[1])} ${r2(b[0])} ${r2(b[1])}`;
    }
    const e = pts[pts.length - 1];
    return `${d}L${r2(e[0])} ${r2(e[1])}`;
  };
  const art = {};
  for (const r of routed) {
    const pts = r.pts.map((p) => [...p]);
    const n = pts.length - 1;
    const end = head(pts[n], pts[n - 1]);
    pts[n] = end.base;
    let heads = end.svg;
    if (r.fl.both) {
      const start = head(pts[0], pts[1]);
      pts[0] = start.base;
      heads = start.svg + heads;
    }
    const dash = dashes[r.fl.style] ? ` stroke-dasharray="${dashes[r.fl.style]}"` : "";
    const line =
      pts.length === 2
        ? `<line x1="${r2(pts[0][0])}" y1="${r2(pts[0][1])}" x2="${r2(pts[1][0])}" y2="${r2(pts[1][1])}" stroke="${col}" stroke-width="${stroke}" stroke-linecap="round"${dash}/>`
        : `<path d="${rounded(pts)}" fill="none" stroke="${col}" stroke-width="${stroke}" stroke-linecap="round" stroke-linejoin="round"${dash}/>`;
    const name = S.esc(`flow: ${r.fl.from} -> ${r.fl.to}`);
    art[r.i] = `<g id="flow-${r.i}" data-flow="${r.i}" inkscape:label="${name}">${line}${heads}${r.svg || ""}</g>`;
  }

  ov.innerHTML = Object.keys(art)
    .sort((p, q) => p - q)
    .map((k) => art[k])
    .join("");
  const panelOf = (el) => el.closest('[data-kind="panel"]').dataset.id;
  const segs = routed
    .sort((p, q) => p.i - q.i)
    .map((r) => {
      const s = {
        i: r.i,
        from: r.fl.from,
        to: r.fl.to,
        fromPanel: panelOf(r.A),
        toPanel: panelOf(r.B),
        points: r.pts,
        label: r.label || null,
      };
      if (s.label) s.label.box = rel(ov.querySelector(`[data-label="${r.i}"]`));
      return s;
    });
  return { segs, problems };
};
