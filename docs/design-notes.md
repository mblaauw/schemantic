# Design notes

Why Schemantic is built the way it is, and what building it taught. For how the code fits together, see
[`architecture.md`](architecture.md).

## Measure, then emit

HTML-to-SVG converters in the Satori style have no CSS Grid, and an architecture plate is a grid. Laying the plate
out in a real browser and emitting SVG from the measured geometry gives both: the browser's layout engine, and an
SVG of native `rect`, `path`, `text` and `line` elements a designer can edit. The PNG is a raster of that same SVG,
so the two never disagree.

The SVG embeds a subset of the bundled fonts, so it renders the same in any browser. Tools that ignore `@font-face`
in SVG (Inkscape, Cairo) need Inter installed, or the `--outline-text` export.

## No coordinates in the spec

The spec says what is on the plate and where in words (columns, a hub, layers, lanes, zones), never in pixels.
That is what lets an agent converge: lint names a problem by element id (`flows/3`, `services.card2`), the fix is a
change in words, and the next build lays everything out again.

## Findings

- **Parity is structural.** Chromium snaps HTML text to whole pixels; the SVG keeps fractions, so 0.9% of pixels
  differ with no visible change. After a 1.5 px blur a correct plate scores 0. The verdict is local (any region or
  32 × 32 tile over a few pixels), because a reworded word leaves about 100 pixels in one place, which a canvas-wide
  share let through.
- **Baselines are measured at the real size.** A 100 px probe scaled down drifted by a pixel once Inter replaced the
  system font, enough to fail parity on bold titles.
- **Linux needs `--font-render-hinting=none` and `--disable-lcd-text`.** Without the first, Chromium rounds glyph
  advances to whole pixels on Linux, text runs a few pixels wider than on macOS, and lines wrap differently. Without
  the second, Linux antialiases text with colour fringes, which a colour-aware image comparison sees on every bold
  glyph. With both, the layout and the pixels match, and the same goldens pass on both.
- **Holes are the common defect, and the fix is content.** A density ratio missed panels that looked empty; the
  void check (the largest empty run inside a panel) matches what reviewers see. Most voids came from a fixed canvas
  dumping its spare height into one row, which `canvas.height: fit` removes.
- **A footer is context.** Dark header bars on footer panels drew the eye away from the body and took 17–18% of the
  canvas; quiet labels and a legend strip bring it under 13%.
- **Connectors are routed, not drawn.** Every route is checked against the measured boxes. A rail card connected to
  the card at the far end of a layer had no clear route; lint said so, and the fix was card order in the spec.
  Straight arrows and their labels are placed first; bent routes then avoid them, and may move a label along its
  arrow.
- **Long Dutch compounds overflow.** "gestandaardiseerd" overflowed a tier tile; lint caught it and block weights
  fixed it. The never-translate check matches substrings for the same reason ("productcatalogus").
- **Dashes are drawn as SVG.** Chromium's dash pattern for CSS borders cannot be reproduced exactly, so dashed
  outlines, strike-throughs and legend line samples are drawn as SVG in the page, and the exporter copies them.
