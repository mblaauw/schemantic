// Rail cards placed by layer. A card in a rail (a panel beside several layers) may name the layer it concerns; it
// then sits level with that layer's cards, so the rail reads across. Cards without a layer follow the one before
// at the usual gap. A card that cannot reach its layer (the cards above it take the space) is marked for lint, and a
// rail whose cards would no longer fit keeps its even spread. Runs after fit, before routing; no panel changes size.
schemantic.rails = () => {
  for (const list of document.querySelectorAll("#plate .spread .blocks > .cards")) {
    const cards = [...list.children];
    if (!cards.some((c) => c.dataset.layer)) continue;
    const r = list.getBoundingClientRect();
    const gap = Number.parseFloat(getComputedStyle(list).rowGap) || 0;
    const h = cards.map((c) => c.getBoundingClientRect().height);
    const y = [];
    let at = r.top;
    cards.forEach((c, i) => {
      const layer = c.dataset.layer
        ? document.querySelector(`#plate [data-id="${CSS.escape(c.dataset.layer)}"]`)
        : null;
      const level = layer ? (layer.querySelector('[data-kind="card"]') || layer).getBoundingClientRect().top : at;
      y[i] = Math.max(level, at);
      if (layer && y[i] > level + 1) c.dataset.layerMissed = "";
      at = y[i] + h[i] + gap;
    });
    if (at - gap > r.bottom + 0.5) {
      for (const c of cards) if (c.dataset.layer) c.dataset.layerMissed = "";
      continue;
    }
    list.style.alignContent = "start";
    let prev = r.top;
    cards.forEach((c, i) => {
      c.style.marginTop = `${Math.max(0, y[i] - prev - (i ? gap : 0))}px`;
      prev = y[i] + h[i];
    });
  }
};
