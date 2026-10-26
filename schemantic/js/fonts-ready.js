// Resolves once every declared face has loaded, not only the ones layout has asked for so far. Evaluated on its
// own (before the other scripts), also on the SVG page used for rasterising.
() =>
  Promise.all([...document.fonts].map((f) => f.load()))
    .then(() => document.fonts.ready)
    .then(() => true);
