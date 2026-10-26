# Spec guide

The full contract is `schema/plate.schema.json`; this guide adds the budgets and writing rules that make a
plate readable. Lengths are maximum characters.

## Top level

| Field | Rule |
| --- | --- |
| `canvas.size` | `landscape-4x3` (1600×1200, the default choice) or `landscape-16x9` (1920×1080, for slides; less height) |
| `canvas.lang` | `nl` or `en` |
| `canvas.series`, `part`, `of` | a badge "Part 2 of 3"; give both `part` and `of` |
| `title` (80) | the one message, as a claim. Not "Architecture overview" |
| `subtitle` (120) | how the plate makes that claim true |
| `archetype`, `layout` | see `archetypes.md` |

## Panels

```yaml
- id: gateway                     # lowercase, a-z 0-9 _ -; used in layout and flows
  title: "API gateway"            # 48
  subtitle: "Authentication, rate limiting and routing"   # 80, optional
  role: platform                  # platform | storage | external — colour has meaning, see the legend
  card_columns: 2                 # optional, 1–6
  arrange: row                    # optional: blocks side by side instead of stacked
  weights: [1.35, 0.8, 1]         # with arrange: row — patterns first, then the cards block
  cards: [...]                    # up to 6
  patterns: [...]                 # up to 2
  chips: [...]                    # up to 2, pinned to the bottom
```

Roles: `platform` for what the team builds or runs, `storage` for data at rest and data platforms,
`external` for users, partners and systems outside the team's control.

## Cards

```yaml
- id: dlq                         # optional; needed only when a flow starts or ends at this card
  icon: alert-triangle            # from the list below
  name: "Dead-letter queue"       # 40
  qualifier: "managed"            # 40, optional, shown in brackets after the name
  note: "events no consumer could handle"   # 70, lowercase start, no full stop
  bullets: ["first responder replays or skips"]   # up to 3, 60 each
```

A note says what the card does in this story, not what the product is in general.

## Patterns

- `tier-strip`: 2–5 tiers (`tier: bronze | silver | gold`, `name`, `note`), for data layers or maturity steps.
- `tree`: up to 10 `lines` of monospace text, indented with two spaces per level, for paths and buckets.
- `matrix`: `columns` (up to 5) × `rows` (up to 8), cells `full | partial | none`, for access or usage.

## Chips

- `warning` (90): an open choice or friction. It is repeated under open questions; set
  `footer.open_questions.from_chips: true` or repeat its exact text in `extra`.
- `info` (90): an assumption or a note the reader needs. A chip holds at most two lines.

## Flows

```yaml
flows:
  - {from: clients, to: identity}                     # panel to panel: the default
  - {from: data, to: clients, label: "BI and notebooks"}   # label 28; needs room beside the arrow
  - {from: dlq, to: oncall}                           # card to card: give both cards an id
  - {from: services, to: bus, both: true}             # arrowheads at both ends
```

The router draws straight arrows across a gutter where it can, and otherwise turns corners through the
gutters (one or two bends). It never crosses another panel or card. A label sits beside a vertical run or
above a horizontal one; short gutters fit short labels only.

Flow direction is the direction of the request or the data, as the legend says. Pick one per plate.

## Footer

```yaml
footer:
  columns: [1.6, 1.4, 1.1, 0.9]   # relative widths of the footer panels present
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

alert-triangle api arrow-down arrow-right bell bolt box briefcase browser building building-store calendar
certificate chart-bar clock cloud code cpu credit-card database device-mobile eye file-search file-text flag
folder gauge git-branch git-merge headset info-circle key lock lock-access map message-circle network package
plug refresh robot rocket route server settings shield-lock shopping-cart stack-2 table test-pipe tool trash
truck user users users-group world
