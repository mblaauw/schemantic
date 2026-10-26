// Helpers shared by the page scripts. Loaded once per page, before the others; every other script attaches one
// function to `schemantic`, which Python calls with page.evaluate.
window.schemantic = (() => {
  const S = {};
  S.plate = () => document.getElementById("plate");
  // A box relative to the plate's top-left corner, as {l, t, r, b}.
  S.rel = (el, P = S.plate().getBoundingClientRect()) => {
    const r = el.getBoundingClientRect ? el.getBoundingClientRect() : el;
    return { l: r.left - P.left, t: r.top - P.top, r: r.right - P.left, b: r.bottom - P.top };
  };
  S.num = (v) => Number.parseFloat(v) || 0;
  S.r2 = (v) => Math.round(v * 100) / 100;
  S.esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  // Design tokens from tokens.css (and a theme), so visual values live in one place.
  S.token = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  S.px = (name) => Number.parseFloat(S.token(name));
  // A CSS colour as [r, g, b, a], or null when it is fully transparent or not an rgb() value.
  S.rgba = (c) => {
    const m = c?.match(/rgba?\(([^)]+)\)/);
    if (!m) return null;
    const p = m[1]
      .split(/[\s,/]+/)
      .filter(Boolean)
      .map(Number);
    const a = p.length > 3 ? p[3] : 1;
    return a === 0 ? null : [p[0], p[1], p[2], a];
  };
  S.hex = (rgba) =>
    `#${rgba
      .slice(0, 3)
      .map((v) => Math.round(v).toString(16).padStart(2, "0"))
      .join("")}`;
  S.overlapArea = (a, b) =>
    Math.max(0, Math.min(a.r, b.r) - Math.max(a.l, b.l)) * Math.max(0, Math.min(a.b, b.b) - Math.max(a.t, b.t));
  S.hits = (a, b) => Math.min(a.r, b.r) - Math.max(a.l, b.l) > 0 && Math.min(a.b, b.b) - Math.max(a.t, b.t) > 0;
  return S;
})();
