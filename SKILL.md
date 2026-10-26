---
name: schemantic
description: Turn a description of a system into a finished architecture plate, a one-page print-grade overview diagram, as SVG and PNG. Use when someone asks for an architecture overview, plate, one-pager, system landscape, platform picture, or "draw how these parts fit together", whether from a conversation, notes, a design doc or a codebase. Writes a small YAML spec (no coordinates), renders it in Chromium, and fixes the spec until lint is clean.
---

# Schemantic: from a description to a finished plate

You write a YAML **spec** that says what is on the plate: panels, cards, flows, principles, open questions.
Chromium does the layout, a router draws the arrows, and `lint.py` measures the result and names every
problem by element id. You never write coordinates and never edit the SVG: every fix goes into the spec.

In the commands below, `$SKILL` is the folder that holds this file.

## 0. Setup, once per machine

```bash
test -x "$SKILL/.venv/bin/python" || (python3 -m venv "$SKILL/.venv" \
  && "$SKILL/.venv/bin/pip" install -q -r "$SKILL/requirements.txt" \
  && "$SKILL/.venv/bin/python" -m playwright install chromium)
```

Fonts are bundled; nothing else needs installing.

## 1. Understand what the plate must say

Settle these before writing YAML. Take them from the conversation; ask only when one is missing and changes
the plate.

- **The one message.** The title states it as a claim ("Orders platform after phase 2 — access and data flow"),
  the subtitle says how ("One identity provider and one API gateway decide who reaches which service").
- **The reader.** Architects get technical terms; a steering group gets fewer cards and more principles.
- **Language.** `nl` or `en`, following the user. In `nl`, technical terms stay English (`catalog`, `pipeline`,
  `deploy`, `API gateway`); lint enforces the list in `locales/nl.yaml`.
- **Series.** If the story needs more than one plate, plan the parts first and give each `series`, `part`, `of`.

If the system does not fit one plate (more than about 5 panels or 25 cards), split it into a series now.

## 2. Choose the layout

| The system is mainly… | Archetype |
| --- | --- |
| a path from left to right: users → entry → services → data | `column-flow` |
| one central thing that many parts connect to (bus, gateway, platform, team) | `hub-and-spokes` |
| stacked levels, each building on the one below, with concerns that cut through all of them | `layer-cake` |

Read `references/archetypes.md` for each layout's keys, limits and a skeleton. Other archetype names in the
schema are planned but not built; lint refuses them.

## 3. Write the spec

Save it where the user keeps their work, for example `plates/<name>.yaml`. Start from the closest example in
`$SKILL/examples/` and follow `references/spec-guide.md` for every field, the text budgets and the writing rules.
The short version:

- 3 to 6 panels, 2 to 6 cards each. A card is a thing with a name; its note says what it does for this story.
- Flows carry the story. Connect panels by default; connect a card (`from: <card id>`) only when that card is
  the point. Give the card an `id` to do that.
- A `warning` chip marks an open choice; it appears again under open questions. An `info` chip states an
  assumption.
- Principles are decisions, written as rules a team can check ("Every request carries a token").

## 4. Lint, fix, repeat

```bash
"$SKILL/.venv/bin/python" "$SKILL/scripts/lint.py" plates/<name>.yaml --out plates/out
```

Lint prints JSON and exits 1 on errors. Each finding has `check`, `id` and `detail`. Fix every error in the
spec using `references/lint-fixes.md`, then run lint again. Treat `density` warnings as real: the fix is
content, a merged panel, or a different layout. Stop after five rounds without progress and restructure:
move cards between panels, change the archetype, or split the plate.

## 5. Render and look at it

```bash
"$SKILL/.venv/bin/python" "$SKILL/scripts/render.py" plates/<name>.yaml --out plates/out
```

This writes `plates/out/<name>.svg` and `plates/out/<name>.png`. Open the PNG (read the image) and answer the
questions in `references/review.md`. A "no" is a spec change and another lint round, not a hand edit.

## 6. Deliver

Give the user the PNG and SVG paths and the spec path, the one message the plate makes, and its open
questions. Mention anything you assumed. If they ask for changes, edit the spec and go back to step 4.

## Rules

- Never write coordinates, sizes or colours into the spec; never edit the SVG, PNG or HTML.
- Never invent facts about the user's system to fill a panel. Thin content means fewer panels or an open
  question, not filler.
- Never ship a plate with lint errors. If one cannot be fixed in the spec, say which check and why.
