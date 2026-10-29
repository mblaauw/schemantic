# Changelog

All notable changes to this project. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added (series checks, before-after)
- `schemantic series <specs>` checks the parts of a series against each other: `of` and numbering, one language,
  one meaning for arrows (a warning: a part may show other flows on purpose), and one colour per thing across parts.
  On the series the evals produced it finds exactly what the judge reported: channels drawn as people in part 1
  and as a platform component in part 2, and arrows meaning requests in one part and data in the other. Two
  examples had claimed to be parts of one series in two languages; the event bus is now its own series.
- The `before-after` archetype: two columns under a label each (Before / After, Nu / Straks, or `layout.labels`),
  panels facing each other row by row, the change shown as status on the after side. The after label is in the
  accent colour. Example: `examples/invoicing-before-after.yaml`.

### Changed (print, one layout document, one icon file)
- Paper: `a3-landscape` and `a4-landscape` lay the plate out at the sheet's width (96 px per inch, so type prints at
  its own size) and as tall as its content, then centre it on the sheet and scale it down when it is taller. The SVG
  is the sheet in mm (its drawing stays in CSS px), and the PNG is the exact sheet at `--dpi`. A new `print-size`
  error says when the smallest text would print under 6 pt. Before, paper was a fixed pixel canvas: a plate slightly
  too tall failed with a flood of overflow errors; now the toegang example prints on A3 at 97 %, and on A4 the
  findings say why it does not fit.
- The layout document's groups carry their boxes, so the structural snapshot is read entirely from it and
  `js/snapshot.js` is gone; every stored snapshot still matches.
- The 4,879 icon files are one `assets/icons/icons.json` (name to drawing): 19 MB and 4,883 files become 1.5 MB and
  4, which makes clones, skill installs and offline kits smaller and their checksums quicker. Rendered icons are
  unchanged.

### Changed (focus and rhythm, from a design review of the 0.2 work)
- A `topic` line above the title: what the plate is about, quiet and small, so the title is free to be the claim.
  The examples taught the opposite (three of five had a topic as title and the claim in the subtitle); every
  example now has a claim title. SKILL.md says where the subject goes.
- Open questions get one label in reading order (Q1, Q2; V1 in Dutch) on the card or chip and in the footer, in a
  small rounded rectangle, so they no longer look like the round step badges, and the footer list reads as a key
  rather than a repeat. Info flags are notes (N1). A warning flag listed in `extra` now gets its label too.
- Panels end with their content instead of stretching to the row: empty space inside a frame read as missing
  content (the judge's most common defect), outside it reads as rhythm. Panels spanning rows, and rows that pin
  chips to the bottom, still fill.
- Lint: `footer-share` warns when the footer takes more than 15% of the plate (review question 6); `widow` warns
  when the topic, title or subtitle leaves one word on its last line; `canvas-fit` names only the outermost element
  that runs off (one cause was 18 findings), and repeated findings for one element are merged with a count. An
  arrow between two panels with no route gets a hint about placement, not "connect the panels instead".
- SKILL.md: when the message names a route through particular parts, connect those cards so it can be traced (the
  judge failed four plates on paths drawn panel to panel).
- Python 3.10 or later (3.9 was never tested and is end of life). The doctor reports an older `python3` and builds
  its venv with the newest `python3.x` it finds.
- Goldens change for every example and fixture: the topic line, the question labels, and shorter panels in rows.
  The toegang example no longer fits an A3 sheet with its topic line (22 px over); the A3 test uses the event bus
  until print sizes scale to paper.

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

### Added (Phase D: the skill)
- D1: `references/analysis.md`: how to build an inventory from notes, a repository or a process description, the
  editorial passes (grouping, message, cut), and three worked examples with complete, linted specs.
- D2: a `brief` (message, reader, why, left out, assumptions) and `sources` in the spec, and `refs` on cards
  (exported as `data-refs`); a `traceability` warning for cards without a source. SKILL.md has the agent write and
  audit the brief before any panel.
- D3: SKILL.md routes on the reader's question, names each archetype's misfit, defaults to column-flow, and states
  the series rule (more than 6 panels or 30 cards).
- D4: `references/review.md` asks yes/no defect questions, including holes and the footer; visual review stops after
  three rounds.
- D5: a third-person description with English and Dutch triggers (under 1,024 characters, tested).
- D6: setup through the doctor; every command uses the interpreter it prints and `scripts/plate.py`.
- D7: `build` writes `<name>.md`, an outline of the plate (title, claim, panels and cards, flows, open questions,
  principles), also used as the SVG's `<desc>`.
- D8: `evals/`: eight cases (prompt, fictional inputs, rubric), an automated grader, a judge prompt and a runner.
  First results (Sonnet 5.5 and Haiku 5.5): without the skill 0/8 pass the automated grade on either model; with it
  8/8 build lint-clean with claim titles and nothing invented, and Haiku's judged defects halve (3.8 to 2.0 per
  plate). The grader matches word stems and card refs, and skips the invented-name check when the plate translates
  its inputs. Remaining defects and the full table are in `evals/README.md`.

### Added (Phase E)
- E1: the `swimlane` archetype: one lane per actor with its name on the left, steps as cards in phase columns
  (`layout.columns`, card `col`) that line up across lanes, numbered handoffs. Step badges now only avoid what their
  arrow avoids, so they can sit where an arrow enters a lane. Example: `examples/incident-swimlane.yaml`.
- E2: the `nested-zones` archetype: labelled dashed frames (account, cluster, namespace) nested up to three deep,
  side by side, holding panels; `outside` panels in a column on the right. Gaps between zones are router channels.
  Example: `examples/kliniek-zones.yaml`.
- The `process-strip` panel pattern: 3–7 numbered steps in a row (fixture `tests/fixtures/process-strip.yaml`).
- The router tries more straight positions along a shared span before bending.

### Added (Phase F: docs and hygiene)
- F2: a user-facing README: what it is, install as a skill, one build command, a gallery per archetype, the linted
  spec sample, status, how it works, licences. Design rationale and findings moved to `docs/design-notes.md`.
- F3: `docs/architecture.md`: the pipeline, the module map, the JS/Python boundary, how the router chooses, parity and
  snapshots, and how to add an archetype.
- F4: `CONTRIBUTING.md` (setup, tests, the golden, snapshot and gallery policy, rules) and this changelog.
- F5: `schemantic gallery` builds every example and writes WebP images to `assets/gallery/` with a manifest; a test
  fails when the gallery no longer matches the examples. The old 1.6 MB PNG copies are gone.
- F6: `references/lint-fixes.md` is generated from `schemantic/findings.py` (`schemantic docs`, tested).
- F7: a test checks that the README, SKILL.md and the archetypes reference list exactly the built archetypes and
  patterns.
- F1: the code is MIT (`LICENSE`), so it can be used, forked and taught from; the bundled Tabler icons (MIT) and
  Inter and DejaVu fonts (OFL) keep their own notices in `assets/`. A test checks that the licence, the notices and
  the README agree.

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
- Findings from an outside assessment of the 0.1 code, where still open:
  - F02: image comparisons (goldens and SVG parity) compare colour (Cb and Cr) apart from lightness, at a finer
    threshold, so a role or status colour swapped for one of the same lightness fails; the report counts pixels that
    differ in colour only. Chromium now
    also runs with `--disable-lcd-text`, so Linux antialiases text in grey like macOS instead of with colour fringes.
  - F03: a missing golden or snapshot fails the test; only `--update-golden` writes one.
  - F04: the router charges two bends for every arrow a candidate crosses, so a slightly longer route that crosses
    nothing wins; a crossing it cannot avoid is an `arrow-crossing` warning. A bent flow with no clear route is
    repaired by taking up the bent routes that block it and routing them again, and a second pass reroutes bent
    routes that cross arrows. Over 400 random layouts this routed flows that had none in 23 and removed crossings in
    10, and made none worse. No example's routes change.
  - Change-one-thing tests (`tests/test_metamorphic.py`): reverse or remove a flow, lengthen a note, add a card, swap
    two columns, switch the language, add a principle, swap a role colour; each checks the one effect it must have.
  - F05: `build` writes the deliverables to `_work/` and publishes them only when there are no errors; with errors,
    `preview` in the report names the unpublished files. The deprecated `render` follows the same rule.
  - F06: pattern blocks and their tiers and rows reject unknown fields, so a misspelt field is a schema error.
  - F13: icon names must be lowercase words joined by hyphens, and the semantic check looks them up in the icon index
    rather than as a file path.
  - A layout document between measuring and writing: `js/layout.js` returns every group, box, border, text line,
    icon and drawn connector with its measured position (saved as `_work/<name>.layout.json`), and `export.py`
    writes the SVG from it as a pure function, tested without Chromium. The structural snapshot reads its text from
    the document instead of parsing the SVG. The SVGs are unchanged apart from five rounded-corner coordinates that
    move by 0.01 px.
  - The paint contract is enforced: CSS the SVG cannot draw (shadows, gradients, transforms, opacity,
    text-transform, letter-spacing, decoration, italics, outlines, non-solid borders, `::before`/`::after`) is a
    `paint` error naming the element and property, instead of an unexplained `svg-parity` difference.
  - A `font` error for text in a family that is not bundled, or with characters the bundled fonts lack (CJK, emoji,
    some symbols): Chromium borrowed a system font for those, so parity passed while other machines drew something
    else.
  - The README no longer calls the SVG print-grade, and says who decides what: the agent the content and the
    composition, Chromium the geometry.
  - Air-gapped use: `schemantic offline <folder>` writes a kit with the runtime, the wheels at the tested versions
    with their hashes (`requirements.lock`), Playwright's Chromium, a manifest and `SHA256SUMS`; its `install.sh`
    installs with no network (`pip --no-index --require-hashes`), checks every file, and runs a smoke test that must
    reproduce the builder's layout digest. `schemantic verify` and `schemantic smoke` run those checks alone. Every
    build refuses network requests; a theme with a remote font or image is a `network` error. CI installs a kit on
    Ubuntu and macOS with the network cut off. See `docs/offline.md`.
  - F16: a published plate comes with `<name>.build.json`: the Schemantic, spec, Chromium, Playwright and Python
    versions, and digests of the spec, theme and fonts (also `build` in the report).
- Wrapped rows inside a zone keep their content height; spare height stays in the zone frame instead of opening
  holes in its panels (found by the evals; the nested-zones golden changes: its panels are shorter).
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
