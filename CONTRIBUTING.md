# Contributing

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m playwright install chromium
python -m schemantic doctor
```

## Tests and checks

```bash
python -m pytest -q -n auto                      # everything: spec, checks, router, docs, snapshots, goldens
ruff check . && npx @biomejs/biome@2.3.11 check schemantic/js
```

`-n auto` runs one worker per core (pytest-xdist); the suite takes about a third of the time it takes alone. CI runs
both on Ubuntu and macOS with Python 3.14, and on Ubuntu with Python 3.10.

## Goldens, snapshots and the gallery

A change that alters a render fails the golden and snapshot tests on purpose. When the change is intended:

1. `python -m pytest -q --update-golden` rewrites `tests/golden/` and `tests/snapshots/`. Without the flag, a missing
   golden or snapshot fails the test; CI never writes its own baseline.
2. Open the new PNGs and look at them; a snapshot diff in git shows which elements moved.
3. `python -m schemantic gallery` rebuilds the README images (a test fails until you do).
4. Say in the commit message what changed visually.

## Rules

- Never add coordinates, pixel sizes or colours to the spec format; layout stays derived. Visual values live in
  `schemantic/templates/tokens.css`.
- Every example lints clean with 0 parity pixels, and without warnings: agents copy what the examples do.
- A spec change ships with its docs: the schema description, `references/spec-guide.md`, and the archetypes
  reference when a layout changes. Marked YAML samples in the docs are linted by the tests.
- A new lint check gets a row in `schemantic/findings.py` (then `python -m schemantic docs`) and a test that
  triggers it.
- Examples are fictional; the repository names no real organisation.
- One task per commit, with a message that names it; keep `CHANGELOG.md` current.
