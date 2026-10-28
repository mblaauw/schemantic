// Layout checks on the measured page. Every finding names the element id, so the fix goes into the spec.
schemantic.lint = (cfg) => {
  const S = schemantic;
  const plate = S.plate();
  const P = plate.getBoundingClientRect();
  const rel = (el) => S.rel(el, P);
  const { num } = S;
  const issues = [];
  const add = (level, check, id, detail) => issues.push({ level, check, id, detail });
  const idOf = (el) => {
    const k = el.closest("[data-id]");
    return k ? k.dataset.id : "(plate)";
  };
  const kindParent = (el) => (el.parentElement ? el.parentElement.closest("[data-kind]") : null);
  // Content box of a container (inside border and padding), with a pixel of slack.
  const inner = (el) => {
    const r = rel(el);
    const cs = getComputedStyle(el);
    return {
      l: r.l + num(cs.borderLeftWidth) + num(cs.paddingLeft) - 1,
      r: r.r - num(cs.borderRightWidth) - num(cs.paddingRight) + 1,
      t: r.t + num(cs.borderTopWidth) + num(cs.paddingTop) - 1,
      b: r.b - num(cs.borderBottomWidth) - num(cs.paddingBottom) + 1,
    };
  };

  // Text: overflow, type floor, contrast
  const lum = (c) => {
    const ch = S.rgba(c)
      .slice(0, 3)
      .map((v) => {
        const s = v / 255;
        return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
      });
    return 0.2126 * ch[0] + 0.7152 * ch[1] + 0.0722 * ch[2];
  };
  const bgOf = (el) => {
    for (let e = el; e; e = e.parentElement) {
      const c = getComputedStyle(e).backgroundColor;
      if (S.rgba(c)) return c;
    }
    return getComputedStyle(document.body).backgroundColor;
  };
  const worst = {};
  const tw = document.createTreeWalker(plate, NodeFilter.SHOW_TEXT);
  for (let n = tw.nextNode(); n; n = tw.nextNode()) {
    if (!n.textContent.trim()) continue;
    const el = n.parentElement;
    const cs = getComputedStyle(el);
    const fs = num(cs.fontSize);
    const id = idOf(el);
    const snippet = n.textContent.trim();
    if (fs < cfg.floor)
      add("error", "type-floor", id, `${fs}px text "${snippet.slice(0, 30)}" is below ${cfg.floor}px`);
    const rg = document.createRange();
    rg.selectNodeContents(n);
    const tr = rel(rg.getBoundingClientRect());
    const box = el.closest("[data-kind]") || plate;
    const ib = el.closest("svg") ? rel(box) : inner(box);
    if (tr.r > ib.r + 0.5 || tr.l < ib.l - 0.5 || tr.b > ib.b + 0.5) {
      const over = Math.round(Math.max(tr.r - ib.r, ib.l - tr.l, tr.b - ib.b));
      add("error", "text-overflow", id, `"${snippet.slice(0, 40)}" runs ${over}px outside its box`);
    }
    const L1 = lum(cs.color);
    const L2 = lum(bgOf(el));
    const ratio = (Math.max(L1, L2) + 0.05) / (Math.min(L1, L2) + 0.05);
    const large = fs >= 24 || (fs >= 18.66 && num(cs.fontWeight) >= 700);
    const need = large ? 3 : 4.5;
    if (ratio < need && (!(id in worst) || ratio < worst[id].ratio))
      worst[id] = { ratio, need, text: snippet.slice(0, 30) };
  }
  for (const [id, w] of Object.entries(worst))
    add("error", "contrast", id, `"${w.text}" has ${w.ratio.toFixed(2)}:1, needs ${w.need}:1`);

  // Overlap between siblings
  const kinds = [...plate.querySelectorAll("[data-kind]")];
  const groups = new Map();
  for (const el of kinds) {
    const p = kindParent(el) || plate;
    if (!groups.has(p)) groups.set(p, []);
    groups.get(p).push(el);
  }
  for (const list of groups.values()) {
    for (let i = 0; i < list.length; i++) {
      for (let j = i + 1; j < list.length; j++) {
        if (S.overlapArea(rel(list[i]), rel(list[j])) > 2)
          add("error", "overlap", list[i].dataset.id, `overlaps ${list[j].dataset.id}`);
      }
    }
  }
  // Containment: every box stays inside the content box of the box that holds it
  for (const el of kinds) {
    const p = kindParent(el);
    if (!p || ["body", "footer"].includes(p.dataset.kind)) continue;
    const r = rel(el);
    const ib = inner(p);
    const over = Math.max(r.r - ib.r, r.b - ib.b, ib.l - r.l, ib.t - r.t);
    if (over > 1)
      add(
        "error",
        "containment",
        el.dataset.id,
        `runs ${Math.round(over)}px outside ${p.dataset.id}; cut content or give the panel more room`,
      );
  }
  // Canvas fit: the outermost element past the margin, not everything inside it
  const pin = inner(plate);
  const past = kinds.filter((el) => {
    const r = rel(el);
    return r.r > pin.r + 1 || r.b > pin.b + 1 || r.l < pin.l - 1 || r.t < pin.t - 1;
  });
  for (const el of past) {
    if (past.some((o) => o !== el && o.contains(el))) continue;
    const r = rel(el);
    const over = Math.max(r.r - pin.r, r.b - pin.b, pin.l - r.l, pin.t - r.t);
    add("error", "canvas-fit", el.dataset.id, `extends ${Math.round(over)}px past the canvas margin`);
  }

  // Footer: context for the body, so it stays a small share of the plate
  const footer = plate.querySelector('[data-kind="footer"]');
  if (footer) {
    const share = (rel(footer).b - rel(footer).t) / P.height;
    if (share > cfg.footerShare)
      add(
        "warning",
        "footer-share",
        "footer",
        `takes ${Math.round(share * 100)}% of the plate's height; keep it under ${Math.round(cfg.footerShare * 100)}%`,
      );
  }

  // Arrows: every run stays off panels other than the endpoints' own, and off cards other than the endpoints;
  // labels clear of every box
  const panels = kinds.filter((e) => e.dataset.kind === "panel");
  const cards = kinds.filter((e) => e.dataset.kind === "card");
  for (const s of cfg.segs) {
    const crossed = new Set();
    for (let k = 0; k < s.points.length - 1; k++) {
      const [p, q] = [s.points[k], s.points[k + 1]];
      const seg = {
        l: Math.min(p[0], q[0]) - 1,
        r: Math.max(p[0], q[0]) + 1,
        t: Math.min(p[1], q[1]) - 1,
        b: Math.max(p[1], q[1]) + 1,
      };
      for (const el of panels)
        if (![s.fromPanel, s.toPanel].includes(el.dataset.id) && S.overlapArea(seg, rel(el)) > 0)
          crossed.add(`panel ${el.dataset.id}`);
      for (const el of cards)
        if (![s.from, s.to].includes(el.dataset.id) && S.overlapArea(seg, rel(el)) > 0)
          crossed.add(`card ${el.dataset.id}`);
    }
    for (const c of crossed) add("error", "arrow-routing", `flows/${s.i}`, `arrow ${s.from} -> ${s.to} crosses ${c}`);
    if (!s.label) continue;
    for (const el of kinds) {
      if (["body", "footer", "titleblock"].includes(el.dataset.kind)) continue;
      if (S.overlapArea(s.label.box, rel(el)) > 0) {
        add("error", "arrow-label", `flows/${s.i}`, `label "${s.label.text}" touches ${el.dataset.id}`);
        break;
      }
    }
  }
  // Arrows crossing arrows: the router avoids it where a route allows; what is left is worth a look.
  cfg.segs.forEach((s, k) => {
    for (const o of cfg.segs.slice(k + 1))
      if (S.crossings(s.points, o.points))
        add(
          "warning",
          "arrow-crossing",
          `flows/${o.i}`,
          `arrow ${o.from} -> ${o.to} crosses arrow ${s.from} -> ${s.to}`,
        );
  });

  // Chips: at most two lines
  for (const ch of plate.querySelectorAll('[data-kind="chip"]')) {
    const t = ch.lastElementChild;
    const lh = num(getComputedStyle(t).lineHeight) || 17;
    const lines = Math.round(t.getBoundingClientRect().height / lh);
    if (lines > 2) add("error", "chip-length", ch.dataset.id, `${lines} lines; a chip holds at most 2`);
  }

  // Voids: the largest empty vertical run inside a body panel (between its blocks and chips, or below them). The
  // content's share of the panel (density) is kept in the report for information.
  const density = {};
  const voids = {};
  for (const p of panels) {
    if (p.dataset.id.startsWith("footer.")) continue;
    const pb = p.querySelector(".pb");
    const ib = inner(pb);
    const parts = [
      ...pb.querySelectorAll(":scope > .blocks > .cards > *, :scope > .blocks > :not(.cards), :scope > .chips > *"),
    ].map((el) => rel(el));
    const spans = parts.map((r) => [r.t, r.b]).sort((a, b) => a[0] - b[0]);
    let cursor = ib.t + 1;
    let gap = 0;
    let used = 0;
    for (const [t, b] of spans) {
      if (t > cursor) gap = Math.max(gap, t - cursor);
      if (b > cursor) {
        used += b - Math.max(t, cursor);
        cursor = b;
      }
    }
    gap = Math.max(gap, ib.b - 1 - cursor);
    voids[p.dataset.id] = Math.round(gap);
    density[p.dataset.id] = Math.round(Math.min(1, used / (ib.b - ib.t - 2)) * 100) / 100;
    if (gap > cfg.voidError || gap > cfg.voidWarn)
      add(
        gap > cfg.voidError ? "error" : "warning",
        "void",
        p.dataset.id,
        `${Math.round(gap)}px of empty space inside the panel; add real content, move it next to a panel of its height, or merge it`,
      );
  }
  // One finding per check and element: the first detail, and how many more there were
  const once = new Map();
  for (const i of issues) {
    const k = `${i.level}|${i.check}|${i.id}`;
    if (once.has(k)) once.get(k).more += 1;
    else once.set(k, { ...i, more: 0 });
  }
  const merged = [...once.values()].map(({ more, ...i }) =>
    more ? { ...i, detail: `${i.detail} (and ${more} more)` } : i,
  );
  return { issues: merged, density, voids };
};
