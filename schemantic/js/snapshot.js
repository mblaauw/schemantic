// Every element with a data-id and its box relative to the plate, rounded to 2 px, for structural snapshots.
schemantic.boxes = () => {
  const S = schemantic;
  const P = S.plate().getBoundingClientRect();
  const r2 = (v) => Math.round(v / 2) * 2;
  const out = {};
  for (const el of document.querySelectorAll("#plate [data-id]")) {
    const r = S.rel(el, P);
    out[el.dataset.id] = [r.l, r.t, r.r, r.b].map(r2);
  }
  return out;
};
