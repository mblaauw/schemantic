---
name: schemantic
description: Turns a description of a system, process or platform into a finished one-page architecture plate (SVG, PNG and a text outline) that engineers, architects and management can read. Use it when someone asks for an architecture plate, overview diagram, system landscape, C4 context or container view, deployment view, process overview, infographic or one-pager, or in Dutch an architectuurplaat, overzichtsplaat or plaat, or wants to "draw how these parts fit together", from a conversation, meeting notes, a design document, a repository or a process description. Builds an inventory from the sources, writes a brief, writes a small YAML spec without coordinates, renders it in Chromium and fixes the spec until lint is clean.
---

# Schemantic: from sources to a finished plate

You decide **what** goes on the plate and **where**, in words: panels, cards, flows, principles, open questions.
Chromium does the layout, a router draws the connectors, and lint measures the result and names every problem by
element id. You never write coordinates and never edit the SVG: every fix goes into the spec.

## 0. Setup, once per session

Set `$SKILL` to the absolute path of the folder that holds this `SKILL.md`. Treat that folder as read-only: never
write specs, renders or a venv into it. Run the doctor:

```bash
python3 "$SKILL/scripts/doctor.py"
```

It prints JSON. Use its `python` value as `$PY` in every command below. It picks a Python that already has the
dependencies, or creates a venv in `~/.cache/schemantic` (or `$SCHEMANTIC_HOME`), and proves Chromium starts. If
`ok` is false, tell the user its `problem` and stop. On a machine without network access, the user installs an
offline kit first (`docs/offline.md`); the doctor then finds its venv and Chromium.

## 1. Inventory the sources

Read `references/analysis.md` and follow it for the source you have: a conversation or notes, a repository, or a
process description. List every actor, system, data store, decision and open point the sources name, each with
where it comes from. Do not add what the sources do not name.

## 2. Write the brief, then audit it

Before any panel, write the spec's `brief` and `sources`:

```yaml
brief:
  message: "The one claim the plate makes"
  reader: "Who reads it, and what they must take away"
  why: "Why this archetype"
  left_out: ["What the sources hold that the plate leaves out, and why"]
  assumptions: ["What is assumed rather than found"]
sources:
  - {id: notes, kind: notes, ref: "Design review, 12 May"}
```

Plan the panels, their cards (each with `refs: ["<source id>: <path, line or short quote>"]`), the flows and the
open questions. Then audit the plan against the sources, and fix it before writing more:

- Every card traces to a source. A card you cannot trace is an assumption or an open question, not a fact.
- Every uncertainty in the sources is a warning chip, a card flag or an open question.
- The title is a claim the panels support, not a topic ("Architecture overview" is a topic). The subject goes in
  `topic`, a quiet line above the title.

Settle the reader's language (`nl` or `en`, following the user; in `nl` technical terms stay English) and, if the
story needs more than one plate, the series (`series`, `part`, `of`); once every part builds, run
`"$PY" "$SKILL/scripts/plate.py" series plates/*.yaml` so the parts agree (language, arrows, one colour per thing).

## 3. Choose the layout

Route on the reader's question. When unsure, use `column-flow`.

| The reader asks… | Archetype | Not this when… |
| --- | --- | --- |
| "How does a request or data get from A to Z?" | `column-flow` | everything hangs off one central part: hub-and-spokes |
| "What sits around the one central thing, and how does it connect?" | `hub-and-spokes` | there is an order to the parts: column-flow |
| "What builds on what, and what cuts across all of it?" | `layer-cake` | layers talk sideways more than up and down: column-flow |
| "Who does what, in which order, and where does work change hands?" | `swimlane` | it is about systems, not people: column-flow |
| "Where does everything run, and what is inside what?" | `nested-zones` | the question is how things talk, not where they live: column-flow |
| "What changes, and what does each part become?" | `before-after` | the change has more than about four parts: a series of plates |
| "What comes when, and where are we now?" | `roadmap` | it is who hands work to whom: swimlane |

Series rule: more than 6 panels or 30 cards is two plates, each with its own message. Read
`references/archetypes.md` for each layout's keys, limits and a skeleton; lint refuses names that are not built.

## 4. Write the spec

Save it where the user keeps their work, for example `plates/<name>.yaml`. Start from the closest example in
`$SKILL/examples/` or `references/analysis.md`, and follow `references/spec-guide.md` for every field, the text
budgets and the writing rules. The short version:

- 3 to 6 panels, 2 to 6 cards each. A card is a thing with a name; its note says what it does in this story.
- Say once what arrows mean (`flows_mean`). Connect panels by default; when the title or subtitle names a route
  ("A via B to C"), give those cards ids and connect them card to card, every step, so a finger can follow it.
- Show change with `status` (new, changed, planned, deprecated, removed) and the one element that matters with
  `focus`.
- A `warning` chip or card `flag` marks an open choice; it appears again under open questions.
- Principles are decisions, written as full sentences a team could check.
- Icons: `"$PY" "$SKILL/scripts/plate.py" icons <word>` searches 4,879 of them.

## 5. Build, fix, repeat

```bash
"$PY" "$SKILL/scripts/plate.py" build plates/<name>.yaml --out plates/out
```

One command checks the spec, lays the plate out, routes the connectors, lints the result and writes
`plates/out/<name>.svg`, `.png` and `.md` (the outline). It prints JSON and exits 1 on errors; then it publishes
nothing, and `preview` in the report names the unpublished files in `plates/out/_work/`. Each finding has
`check`, `id`, `detail` and `hint` (the first fix to try); `references/lint-fixes.md` has the full table. Fix every
error in the spec and build again. Treat `void` and `traceability` warnings as real. After five rounds without
progress, restructure: move cards between panels, change the archetype, or split the plate.

## 6. Look at it

Once the build is clean, open the PNG (read the image) and answer the defect questions in `references/review.md`.
Every "yes" is a spec change and another build, not a hand edit. Stop after three review rounds; tell the user what
is still imperfect rather than looping.

## 7. Deliver

Give the user the PNG, SVG, spec and outline (`.md`) paths; the one message; the open questions; and the brief's
assumptions. If they ask for changes, edit the spec and go back to step 5. For print, build with
`canvas.size: a3-landscape` and `--dpi 300`; for a meeting, `landscape-16x9` with `canvas.profile: slide`; for hand-off to a design tool, add `--outline-text`.

## Rules

- Never write coordinates, sizes or colours into the spec; never edit the SVG, PNG or HTML.
- Never invent components, names or facts to fill a panel. Thin content means fewer panels or an open question.
- Never ship a plate with lint errors. If one cannot be fixed in the spec, say which check and why.
- Examples and references are fictional; do not copy their content into the user's plate.
