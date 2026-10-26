# Changelog

All notable changes to this project. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added (Phase C)
- C5: role `actor` for people and teams; `storage` is now `data` (the old name lints as `deprecated` for one release);
  legend labels say what each role means. A `role` check catches unknown roles and theme roles without a label.
- C1: `canvas.height: fit` (default) sizes the canvas to its content; `fixed` keeps the preset size and spreads spare
  height over the gaps between rows, capped per gap, never into a panel. Chips sit under their panel's content
  (`layout.chips_at: bottom` lines them up in rows where every panel has chips). A panel spanning several rows
  spreads its cards. A `void` check (warning over 96 px, error over 160 px) replaces the density warning; density stays
  in the report. `row_heights` is deprecated.
- C2: a quieter, lower footer: labels over a hairline instead of header bars, context as a plain list, the legend as
  one strip across the full width, and short open questions or notes stacked when there are many columns. Every
  example's footer is at most 13% of the canvas.
- C6: `flows_mean` (data, request, dependency, control) sets what arrows mean in the legend (lint warns without it);
  `style: async | optional` draws dashed or dotted connectors; `step: n` adds a numbered badge.
- C7: `status: new | changed | planned | deprecated | removed` on cards and panels: a tag, a dashed outline for
  planned, muted for deprecated, struck through for removed; listed in the legend.
- C8: card `flag: {kind, text}`: a numbered marker on the card, its text in open questions (warning) or notes (info).
- C14: `focus: true` on one panel or card gives it an accent outline; lint allows one.
- C3: side columns (rails, side spokes) are at least 260 px wide (at a 1600 px canvas) and at most 30% of the body;
  `layout.rail_width: narrow | normal | wide` for rails.
- C4: a matrix is as wide as its content, left-aligned, with columns of at least 72 px; `key` overrides its labels.
- C11: `a3-landscape` and `a4-landscape` canvases (the sheet at 96 px per inch, height fixed), and `--dpi` (default
  192): A3 at 300 dpi is exactly 4961 × 3508 px, with the dpi recorded in the PNG.
- C9: the router goes around: U-routes (out of one side, along a channel beyond both boxes, back in on the same side),
  channels along the body's outer edges as a last resort, and one-lane offsets for flows between the same boxes.
  Straight flows and their labels are placed first; a bent route blocked only by labels moves them along their arrow.
  The title block is an obstacle. A fixture (`tests/fixtures/skip-connection.yaml`) covers a skip connection.
- C10: the SVG is editable: a named group per panel, card, pattern, chip and flow (with Inkscape labels), nested as
  on the page, and a `<desc>` with the subtitle and an outline of the plate. `--outline-text` writes text as glyph
  paths, shaped with HarfBuzz from the bundled fonts (optional `uharfbuzz`); parity still checks the text version.
- C13: the full Tabler outline set (4,879 icons, 3.19) with a tag index and curated synonyms for architecture words;
  `schemantic icons <words>` searches them, and an unknown icon's hint names the three closest.
- C12: themes. `canvas.theme` (relative to the spec) or `--theme` appends a CSS file after `tokens.css`; a theme can
  recolour and add roles with their own legend labels. `examples/themes/warm.css` shows both.

### Changed
- B1: the code is a package, `schemantic/`, with a CLI: `python -m schemantic build | lint | render | doctor | icons |
  docs` (`pip install -e .` adds a `schemantic` command). `scripts/render.py` and `scripts/lint.py` are deprecated
  shims; `scripts/plate.py` runs the CLI from a skill folder.
- B2: archetypes are a registry, one module each (`schemantic/archetypes/`), found automatically. Adding one needs no
  edits to shared code.
- B3: `build` checks, lays out, routes, lints, exports, checks parity and writes the PNG in one Chromium session, in
  about half the time of the old lint plus render.
- B4: the page scripts live in `schemantic/js/` (common, route, export, lint, snapshot, fonts-ready), checked by Biome;
  Python calls them by name. Router unit tests run on hand-made boxes.
- B5: gutters, connector geometry, label type and the header text colour are tokens in `tokens.css`; no colour is
  hard-coded elsewhere (tested).
- B6: the schema has an `$id`, descriptions on every field, `spec_version: 1`, and per-archetype `layout` rules, so a
  layout key from another archetype is a schema error. Examples declare the schema for editor completion.
- B7: `pyproject.toml` with tested dependency ranges; `requirements.txt` is checked against it. CI runs ruff and Biome,
  and the suite on Ubuntu and macOS with Python 3.10 and 3.14. Chromium runs with `--font-render-hinting=none`, which
  makes Linux layout identical to macOS, so the same goldens pass on both.
- B8: every finding carries a `hint`. `references/lint-fixes.md` is generated from the table in
  `schemantic/findings.py`, and every check has a test that triggers it.

### Fixed
- A1: duplicate panel ids, duplicate card ids, and card ids equal to a panel id or an automatic card id are
  `id` errors naming both places; card ids must match `^[a-z][a-z0-9_-]*$`.
- A2: the default footer widths follow the footer panels present, so a footer without a context panel spans
  the full width; `footer.columns` must match the panel count.
- A3: hub spoke rows are their own grids, so uneven top and bottom rows no longer squeeze the side spoke; the
  side spoke is as wide as one spoke of the fuller row, with gutters counted.
- A4: a missing file, broken YAML or an empty spec returns a `yaml` finding as JSON; any other failure returns
  an `internal` finding instead of a traceback.
- A5: a flow from an element to itself is a `flow` error; a label without room is `arrow-label`.
- A6: `canvas.part` and `canvas.of` come together, with `part ≤ of`.
- A7: the README spec sample lints clean; marked YAML samples in the docs are linted by the tests.
- A8: image comparison fails on any local region or tile over the limit, so a one-word change fails; a
  structural snapshot per example names changed boxes, text lines and connectors.

### Added
- A9: `scripts/doctor.py` finds a Python with the dependencies (or creates a venv in `~/.cache/schemantic`)
  and proves Chromium starts; it never writes into the skill folder. Playwright is no longer pinned
  (`>=1.60,<2`); `tests/golden/VERSION` records what rendered the goldens.

## [0.1.0] - 2026-10-26

Baseline (`a1a9d1e`): column-flow, hub-and-spokes and layer-cake archetypes; connector router with bends and
card endpoints; lint with SVG parity; bundled fonts; golden tests; the Claude skill.
