# Archetypes

Every archetype uses the same panels, cards, chips, patterns, flows and footer. They differ only in
`layout`: how panels are placed. Lint names any layout key that does not belong to the chosen archetype.

## column-flow

A path the reader follows left to right, with optional rows underneath (a data platform under the services,
for example). You draw the grid by naming cells, like CSS `grid-template-areas`.

<!-- lint -->
```yaml
archetype: column-flow
layout:
  areas:                                  # 1 to 3 rows, at most 5 columns; '.' is an empty cell
    - "clients identity gateway services"
    - "data    data     data    data"      # a panel may span cells, as long as it forms a rectangle
  column_widths: [1, 1.1, 1, 1.2]         # optional, relative
  row_heights: [fill, auto]               # optional: fill shares the height, auto hugs the content
```

- Flows between neighbours run straight across the gutter. Flows to a spanning row below run straight down.
- A wide bottom panel takes `arrange: row` with `weights`, so its blocks sit side by side.
- Example: `examples/orderplatform-toegang.yaml`.

## hub-and-spokes

One central panel (the hub) with up to 10 spokes around it: up to 4 above, up to 4 below, and one on each
side. Top and bottom spokes share the hub's width evenly, even when their counts differ; side spokes run the
full height. The hub gets a stronger frame and the free height.

<!-- lint: examples/orderplatform-eventbus.yaml -->
```yaml
archetype: hub-and-spokes
layout:
  hub: bus
  top: [orders, payments, shipping]       # producers, callers or sources usually go on top
  bottom: [search, analytics, notify]     # consumers or targets below
  right: ops                              # optional; also `left`. Good for operators and owners
  row_heights: [auto, fill, auto]         # optional; this is the default (top, hub, bottom)
```

- Give each spoke one flow to or from the hub; the router draws them straight.
- The hub holds the substance: cards for what it offers, and a `matrix` (who uses what) fits well.
- Spokes stay small: one or two cards each. A side spoke is tall, so give it 3–4 cards with bullets.
- Needs at least two spokes. Example: `examples/orderplatform-eventbus.yaml`.

## layer-cake

Stacked layers, top to bottom, each one building on the one below. Optional rails on the left and right
for concerns that touch every layer (security, observability, governance).

<!-- lint: examples/ontwikkelplatform-lagen.yaml -->
```yaml
archetype: layer-cake
layout:
  layers: [experience, delivery, runtime, infra]   # 2 to 5, top first
  left: security                                   # optional rails
  right: observability
  row_heights: [auto, auto, auto, auto]            # optional; auto is the default
```

- A layer lays its cards out in one row by default (`card_columns` = number of cards); 3–5 cards fit well.
- Flows between layers run straight down. A flow from a rail card to a layer card turns corners through
  the gutter; put the target card at the end of its layer nearest the rail, or the route is blocked.
- Rails are tall and narrow: short notes, bullets, and an info chip keep them from looking empty.
- Example: `examples/ontwikkelplatform-lagen.yaml`.

## Not built yet

`banded-matrix`, `nested-zones`, `swimlane`, `before-after`, `roadmap`, `landscape-map` are in the schema as
planned names. Lint refuses them. Until they exist:

- a swimlane or roadmap → `column-flow` with one row per lane and the phases as columns;
- a before/after → a series of two plates (`part: 1` and `part: 2`);
- nested zones → `layer-cake`, or `column-flow` with one spanning panel per zone.
