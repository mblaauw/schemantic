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

## 2. Settle the message and the layout

Decide, in a sentence each, the one claim the plate makes and who reads it. The claim becomes the title: a claim the
panels support, not a topic ("Architecture overview" is a topic); the subject goes in `topic`, a quiet line above
it. Then pick the layout on the reader's question. When unsure, use `column-flow`.

| The reader asks… | Archetype | Not this when… |
| --- | --- | --- |
| "How does a request or data get from A to Z?" | `column-flow` | everything hangs off one central part: hub-and-spokes |
| "What sits around the one central thing, and how does it connect?" | `hub-and-spokes` | there is an order to the parts: column-flow |
| "What builds on what, and what cuts across all of it?" | `layer-cake` | layers talk sideways more than up and down: column-flow |
| "Who does what, in which order, and where does work change hands?" | `swimlane` | it is about systems, not people: column-flow |
| "Where does everything run, and what is inside what?" | `nested-zones` | the question is how things talk, not where they live: column-flow |
| "What changes, and what does each part become?" | `before-after` | the change has more than about four parts: a series of plates |
| "What comes when, and where are we now?" | `roadmap` | it is who hands work to whom: swimlane |
| "Who calls whom, in what order, for this one request?" | `sequence` | people hand work over: swimlane; it is the whole system: column-flow |
| "What can we do, and where are the gaps?" | `capability-map` | how the parts talk matters: column-flow |
| "Which option, and why?" | `comparison` | there is one design and no choice: any other |
| "What is made of what, or who reports to whom?" | `hierarchy` | things have more than one parent: column-flow |
| "Where does each thing sit on two axes?" | `quadrant` | one axis is time: roadmap |

A `capability-map`, `comparison` or `quadrant` says it by position and needs no arrows; a `hierarchy` draws them from
its tree. On those, the arrow rules below apply only to the arrows you do draw.

Settle the reader's language (`nl` or `en`, following the user; in `nl` technical terms stay English). More than 6
panels or 30 cards is two plates, each with its own message: a series (`series`, `part`, `of`); once every part
builds, run `"$PY" "$SKILL/scripts/plate.py" series plates/*.yaml` so the parts agree (language, what arrows mean or a subtitle that says so, one colour
per thing). `references/archetypes.md` has each layout's keys and limits; the schema refuses any other name.

## 3. Start the spec, brief first

Start from the layout's starter, saved where the user keeps their work:

```bash
"$PY" "$SKILL/scripts/plate.py" new <archetype> plates/<name>.yaml --lang en
```

It has every part (brief, sources, panels, flows, a story, footer) with TODO wherever the sources must speak; lint
names each TODO left. Fill the `brief` and `sources` before any panel:

```yaml
brief:
  message: "The one claim the plate makes"
  reader: "Who reads it, and what they must take away"
  why: "Why this archetype"
  left_out: ["What the sources hold that the plate leaves out, and why"]
  assumptions: ["What is assumed rather than found"]
sources:
  - {id: notes, kind: notes, ref: "Design review, 12 May", path: ../inputs/notes.md}
```

Give a source its `path` when it is on disk (a file, or a folder of files), relative to the spec: lint then checks each
quote against it. Plan the panels, their cards, the flows and the open questions. Everything that says something about
the world names its source: `refs: ["<source id>: <path, line or short quote>"]` on cards, arrows and warnings,
`status_ref` beside a `status`. Quote word for word, in the source's language. Then audit the plan against the sources,
and fix it before writing more:

- What the sources do not say is marked or left out. Mark what you have reason to draw with `assumed: <why>`: the plate
  tags the card or panel and draws the arrow amber and dashed, so a reader can tell it from a fact. dbt builds Silver and
  Gold, so an arrow runs out of Bronze: `refs` if the notes say so, `assumed` if you worked it out. Leave out what has no
  basis at all. The brief's `assumptions` are for what cannot be marked on the plate.
- A `status` is what the sources say about that thing. Someone asking for a report does not make it `planned`, and "not
  decided" is a warning, not a status: with nothing to quote, draw no status.
- A panel name uses the sources' words. A grouping you coin that a reader would take for a real domain or team
  ("Customers and sales") gets `assumed`, or a plainer name.
- The title, subtitle, principles and notes say only what the sources say. An "only", an "every", a "never" or a detail
  you inferred goes in the brief, or is left out. Check every "every" against the plate's own open questions.
- Every uncertainty in the sources is a warning chip, a card flag or an open question. Before you keep a question,
  look for its answer: one the sources settle ("everything publishes", "test mirrors production") is a fact to draw. A
  question the sources do not raise goes in your reply to the user, not on the plate.
- Every route the title or subtitle names ("A via B to C") is a `story` through cards that exist.

## 4. Fill the spec

Replace every TODO, and rename, add or drop panels and cards as the plan says. The examples in `$SKILL/examples/`
show finished plates; follow `references/spec-guide.md` for every field, the text budgets and the writing rules. The
short version:

- 3 to 6 panels, 2 to 6 cards each. A card is a thing with a name; its note says what the sources say it does in
  this story. When they give only a name, leave the note out: never write one from the name.
- Say once what arrows mean (`flows_mean`). Connect cards: give them ids and run each arrow from the card that acts
  to the card it acts on. End an arrow on a panel only when the sources speak of the whole panel, or of every card
  in it.
- Everything the title or subtitle says moves, calls, reads or feeds gets an arrow on this plate; a step that lives
  only in a note is a gap. On a series, draw a stand-in panel for what sits on the other part, named for what it
  holds ("Lending"), never "Part 1"; `references/analysis.md` has a worked series. Write the main route
  as a `story` with `draw: true`: lint checks that a finger can follow it, and the plate numbers its steps.
- Show change with `status` (new, changed, planned, deprecated, removed) and the one element that matters with
  `focus`.
- A `warning` chip or card `flag` marks an open choice; it appears again under open questions.
- Principles are decisions, written as full sentences a team could check.
- Icons: `"$PY" "$SKILL/scripts/plate.py" icons <word>` searches 4,879 of them.

## 5. Build, fix, repeat

```bash
"$PY" "$SKILL/scripts/plate.py" build plates/<name>.yaml --out plates/out --review
```

One command checks the spec, lays the plate out, routes the connectors, lints the result and writes
`plates/out/<name>.svg`, `.png` and `.md` (the outline). It prints JSON and exits 1 on errors; then it publishes
nothing, and `preview` in the report names the unpublished files in `plates/out/_work/`. Start with `summary`: one
line per check, errors first, with its count and `hint` (the first fix to try); its first line is the one to fix
first. Each finding under `errors` and `warnings` has `check`, `id` and `detail`; `references/lint-fixes.md` has
the full table. `changed` names the parts your last edit changed, so you see whether it did what you meant. Fix
every error in the spec and build again. Treat `void` and `traceability` warnings as real. After five rounds without
progress, restructure: move cards between panels, change the archetype, or split the plate.

## 6. Look at it

Once the build is clean, read every crop the report lists under `review`, not only the first: the whole plate, then
the title block, each panel and the footer, at a size where every note is legible (a full PNG is scaled down until
small text blurs). Answer the defect questions in `references/review.md`. After the first round, `review` lists the
whole plate and the parts that changed since the last round, and `review_unchanged` the rest: read those too if you
rebuilt before reading them. Every "yes" is a spec change and another build, not
a hand edit. Stop after three review rounds; tell the user what is still imperfect rather than looping.

## 7. Deliver

Give the user the PNG, SVG, spec and outline (`.md`) paths; the one message; the open questions; and the `assumptions`
in the report. If they ask for changes, edit the spec and go back to step 5. For print, build with
`canvas.size: a3-landscape` and `--dpi 300`; for a meeting, `landscape-16x9` with `canvas.profile: slide`; for hand-off to a design tool, add `--outline-text`.

## Rules

- Never write coordinates, sizes or colours into the spec; never edit the SVG, PNG or HTML.
- Never invent components, names or facts to fill a panel. Thin content means fewer panels or an open question.
- Never ship a plate with lint errors. If one cannot be fixed in the spec, say which check and why.
- Examples and references are fictional; do not copy their content into the user's plate.
