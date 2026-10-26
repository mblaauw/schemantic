# Changelog

All notable changes to this project. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

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
