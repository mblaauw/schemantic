# Spec guide

The full contract is `schema/plate.schema.json`; this guide adds the budgets and writing rules that make a
plate readable. Lengths are maximum characters.

## Top level

| Field | Rule |
| --- | --- |
| `canvas.size` | `landscape-4x3` (1600 wide, the default choice), `landscape-16x9` (1920×1080, for slides), or `a3-landscape` / `a4-landscape` for print (the sheet at 96 px per inch, height fixed; build with `--dpi 300`) |
| `canvas.lang` | `nl` or `en` |
| `canvas.series`, `part`, `of` | a badge "Part 2 of 3"; give both `part` and `of` |
| `canvas.height` | `fit` (default: the canvas takes its content height; a 16:9 slide keeps its shape) or `fixed` (the preset size; spare height goes to the gaps) |
| `canvas.theme` | optional CSS file, relative to the spec, that recolours or adds roles |
| `title` (80) | the one message, as a claim. Not "Architecture overview" |
| `subtitle` (120) | how the plate makes that claim true |
| `archetype`, `layout` | see `archetypes.md`; `layout.chips_at: bottom` lines chips up at the bottom of a row |
| `flows_mean` | what every arrow means: `data`, `request`, `dependency` or `control`; sets the legend (lint warns without it) |

## Panels

```yaml
- id: gateway                     # lowercase, a-z 0-9 _ -; used in layout and flows
  title: "API gateway"            # 48
  subtitle: "Authentication, rate limiting and routing"   # 80, optional
  role: platform                  # platform | data | external | actor — colour has meaning, see the legend
  card_columns: 2                 # optional, 1–6
  arrange: row                    # optional: blocks side by side instead of stacked
  weights: [1.35, 0.8, 1]         # with arrange: row — patterns first, then the cards block
  status: new                     # optional: new | changed | planned | deprecated | removed
  focus: true                     # optional: the one element the plate is about (at most one per plate)
  cards: [...]                    # up to 6
  patterns: [...]                 # up to 2
  chips: [...]                    # up to 2, right under the content
```

Roles: `platform` for what the team builds or runs, `data` for data at rest and data platforms, `external` for
systems outside the team's control, `actor` for people and teams. A theme can add roles (see the README). The old
name `storage` still works for one release and lints as `deprecated`.

## Cards

```yaml
- id: dlq                         # optional; needed only when a flow starts or ends at this card
  icon: alert-triangle            # find one with: plate.py icons <word>
  name: "Dead-letter queue"       # 40
  qualifier: "managed"            # 40, optional, shown in brackets after the name
  note: "events no consumer could handle"   # 70, lowercase start, no full stop
  bullets: ["first responder replays or skips"]   # up to 3, 60 each
  status: planned                 # optional: a tag after the name; planned is dashed, deprecated muted, removed struck
  flag: {kind: warning, text: "Rate limits per tenant or per client?"}   # optional: numbered marker, text in the footer
  focus: true                     # optional, as on panels
```

A note says what the card does in this story, not what the product is in general.

## Patterns

- `tier-strip`: 2–5 tiers (`tier: bronze | silver | gold`, `name`, `note`), for data layers or maturity steps.
- `process-strip`: 3–7 `steps` (`name` 24, `note` 40, `icon`), numbered left to right, for a short sequence inside
  one panel; a sequence between actors is a swimlane.
- `tree`: up to 10 `lines` of monospace text, indented with two spaces per level, for paths and buckets.
- `matrix`: `columns` (up to 5) × `rows` (up to 8), cells `full | partial | none`, for access or usage. When the
  locale's key words (full, limited, no access) do not fit, give `key: {full: ..., partial: ..., none: ...}`.

## Chips

- `warning` (90): an open choice or friction. It is repeated under open questions; set
  `footer.open_questions.from_chips: true` or repeat its exact text in `extra`. A card `flag` does the same for one
  card, with a number.
- `info` (90): an assumption or a note the reader needs. A chip holds at most two lines.

## Flows

```yaml
flows_mean: request                                   # data | request | dependency | control: what an arrow means
flows:
  - {from: clients, to: identity}                     # panel to panel: the default
  - {from: clients, to: data, label: "BI and notebooks"}   # label 28; needs room beside the arrow
  - {from: dlq, to: oncall}                           # card to card: give both cards an id
  - {from: services, to: bus, style: async}           # sync (solid, default) | async (dashed) | optional (dotted)
  - {from: orders, to: payments, step: 2}             # a numbered badge, for the order things happen
  - {from: services, to: bus, both: true}             # arrowheads at both ends
```

The router draws straight arrows across a gutter where it can, and otherwise turns corners through the
gutters (one or two bends), or goes around: out of a box and back into the other on the same side, along a gutter
beyond both (a skip connection past the panels between them). It never crosses another panel or card. A label sits beside a vertical run or
above a horizontal one; short gutters fit short labels only.

Say what arrows mean once, with `flows_mean`, and keep every arrow in that direction. The legend shows the meaning,
and a line style only when the plate uses it.

## Footer

```yaml
footer:
  columns: [1.6, 1.4, 1.1]        # optional: relative widths of the footer columns (the legend is a strip below)
  context:                         # optional: people or roles
    title: "Roles"
    card_columns: 2
    cards: [...]                   # up to 6
  principles: ["...", "..."]       # up to 5 decisions, each a full sentence
  open_questions: {from_chips: true, extra: ["Event bus now or in phase 3?"]}
  legend: auto
```

## Writing rules

- Sentence case everywhere. No marketing words, no abbreviations the reader has not seen before.
- Names are nouns; notes are short clauses; principles are full sentences.
- In `nl` plates, prose is Dutch and technical terms stay English (see `locales/nl.yaml`).
- Same thing, same word, on every plate of a series.

## Icons

The full Tabler outline set (4,879 icons) is bundled. Find one by name, tag or architecture word:

```bash
"$PY" "$SKILL/scripts/plate.py" icons queue        # stack-2, list-details, inbox, arrows-right
"$PY" "$SKILL/scripts/plate.py" icons user group   # every word must match
```

An unknown icon in a spec is a lint error whose hint names the three closest icons.
