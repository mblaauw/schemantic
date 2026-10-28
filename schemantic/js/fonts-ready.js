// Resolves once every declared face has loaded or failed, not only the ones layout has asked for so far. A face that
// fails (a remote font, refused offline) is reported by the build as a `network` finding, so it must not stop the
// wait. Evaluated on its own (before the other scripts), also on the SVG page used for rasterising.
() =>
  Promise.allSettled([...document.fonts].map((f) => f.load()))
    .then(() => document.fonts.ready)
    .then(() => true);
