# Spec guide

The full contract is `schemantic/schema/plate.schema.json`; this guide adds the budgets and writing rules that make a
plate readable. Lengths are maximum characters.

## Top level

`schemantic new <archetype> <path>` writes a starter with every part below and TODO wherever the sources must speak;
lint (`placeholder`) names each TODO left.

| Field | Rule |
| --- | --- |
| `canvas.size` | `landscape-4x3` (1600 wide, the default choice), `landscape-16x9` (1920×1080, for slides), or `a3-landscape` / `a4-landscape` for print: laid out at the sheet's width (96 px per inch, so type prints at its own size), as tall as the content, then centred on the sheet and scaled down when taller; lint fails it when the smallest text would print under 6 pt (`print-size`). Build with `--dpi 300`; the SVG is the sheet in mm |
| `canvas.lang` | `nl` or `en` |
| `canvas.profile` | `document` (default: read up close) or `slide` (shown in a meeting, usually with `landscape-16x9`): a larger type ramp, a 13 px type floor, and lint warns past 5 panels or 18 cards (`slide-budget`) |
| `canvas.series`, `part`, `of` | a badge "Part 2 of 3"; give both `part` and `of` |
| `canvas.height` | `fit` (default: the canvas takes its content height; a 16:9 slide keeps its shape) or `fixed` (the preset size; spare height goes to the gaps) |
| `canvas.theme` | optional CSS file, relative to the spec, that recolours or adds roles |
| `topic` (60) | optional: what the plate is about, in a few words ("Order platform after phase 2"); a quiet line above the title, so the title is free to make the claim |
| `title` (80) | the one message, as a claim. Not "Architecture overview": that is a topic. Lint warns when its last line is one word |
| `subtitle` (120) | how the plate makes that claim true |
| `archetype`, `layout` | see `archetypes.md`; `layout.chips_at: bottom` lines chips up at the bottom of a row |
| `flows_mean` | what every arrow means: `data`, `request`, `dependency`, `control` or `sequence` (what comes before what, for a roadmap); sets the legend (lint warns without it) |

## Panels

```yaml
- id: gateway                     # lowercase, a-z 0-9 _ -; used in layout and flows
  title: "API gateway"            # 48
  subtitle: "Authentication, rate limiting and routing"   # 80, optional
  role: platform                  # platform | data | external | actor — colour has meaning, see the legend
  card_columns: 2                 # optional, 1–6; without it, as many columns of 280 px as fit
  arrange: row                    # optional: blocks side by side instead of stacked
  weights: [1.35, 0.8, 1]         # with arrange: row — patterns first, then the cards block
  status: new                     # optional: new | changed | planned | deprecated | removed
  focus: true                     # optional: the one element the plate is about (at most one per plate)
  cards: [...]                    # up to 6
  patterns: [...]                 # up to 2
  chips: [...]                    # up to 2, right under the content
```

Roles: `platform` for what the team builds or runs, `data` for data at rest and data platforms, `external` for
systems outside the team's control, `actor` for people and teams. A theme can add roles (see the README).

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

A note says what the card does in this story, not what the product is in general. When the sources give only a name,
leave the note out; a note written from the name is an invention.

## Patterns

- `tier-strip`: 2–5 tiers (`tier: bronze | silver | gold`, `name`, `note`), for data layers or maturity steps.
- `process-strip`: 3–7 `steps` (`name` 24, `note` 40, `icon`), numbered left to right, for a short sequence inside
  one panel; a sequence between actors is a swimlane.
- `tree`: up to 10 `lines` of monospace text, indented with two spaces per level, for paths and buckets.
- `matrix`: `columns` (up to 5) × `rows` (up to 8), cells `full | partial | none`, for access or usage. When the
  locale's key words (full, limited, no access) do not fit, give `key: {full: ..., partial: ..., none: ...}`.

## Chips

- `warning` (90): an open choice or friction. It is listed under open questions; set
  `footer.open_questions.from_chips: true` or repeat its exact text in `extra`. A card `flag` does the same for one
  card. Every open question gets a label in reading order (Q1, Q2; V1 in Dutch) that shows on the chip or card and
  in the footer, so the reader can go from one to the other. Info flags are notes (N1).
- `info` (90): an assumption or a note the reader needs. A chip holds at most two lines.

## Flows

```yaml
flows_mean: request                                   # data | request | dependency | control | sequence
flows:
  - {from: portal, to: gateway}                       # card to card: the default; give both cards an id
  - {from: clients, to: data, label: "BI and notebooks"}   # label 28; needs room beside the arrow
  - {from: clients, to: identity}                     # panel to panel: when the sources speak of the whole panel
  - {from: services, to: bus, style: async}           # sync (solid, default) | async (dashed) | optional (dotted)
  - {from: orders, to: payments, step: 2}             # a numbered badge, for the order things happen
  - {from: services, to: bus, both: true}             # arrowheads at both ends
  - {from: integration, to: proxy, focus: true}       # the one arrow the plate is about (one focus per plate)
```

Panel headers are quiet: their role's tint, with the title in the role's colour. Only the panels a `focus` is about
(a panel, a card, or the two ends of an arrow) get a filled header, so a plate has one loud place and the eye goes
there first; without a focus, a hub-and-spokes hub is that place. A focused arrow is drawn heavier, in the accent
colour.

The router draws straight arrows across a gutter where it can, and otherwise turns corners through the
gutters (one or two bends), or goes around: out of a box and back into the other on the same side, along a gutter
beyond both (a skip connection past the panels between them). It never crosses another panel or card, nor a
panel's title; it may pass the empty band of a header beside the title, to reach a card in that panel's first row.
Cards joined to each other inside one panel get room for a straight arrow between them. A label sits beside a
vertical run or above a horizontal one; short gutters fit short labels only.

Say what arrows mean once, with `flows_mean`, and keep every arrow in that direction. The legend shows the meaning,
and a line style only when the plate uses it.

## Stories

When the title or subtitle tells a route ("the portal reaches the records system only through one API"), write it
down as a story: the steps a reader's finger follows, first to last. Lint (`story`) checks that a flow runs from
every step to the next, in that direction (or with `both`). Draw the story the title names (`draw: true`): its flows
get step badges 1 to n and the legend names the route, so the reader sees it, not only lint.

```yaml
stories:                                              # up to 4
  - name: "From the portal to the records system"     # 60, the route in the title's words; the legend shows it
    path: [portal, integration, proxy, ehr]           # card or panel ids; 2 to 10
    draw: true                                        # one drawn story per plate; its flows take no `step`
```

A route through cards needs flows between those cards, not their panels; lint says when only the panels are joined.

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
- In `nl` plates, prose is Dutch and technical terms stay English (see `schemantic/locales/nl.yaml`).
- Same thing, same word, on every plate of a series.

## Icons

The full Tabler outline set (4,879 icons) is bundled. Find one by name, tag or architecture word:

```bash
"$PY" "$SKILL/scripts/plate.py" icons queue        # stack-2, list-details, inbox, arrows-right
"$PY" "$SKILL/scripts/plate.py" icons user group   # every word must match
```

An unknown icon in a spec is a lint error whose hint names the three closest icons.
