# Archetypes

Every archetype uses the same panels, cards, chips, patterns, flows and footer. They differ only in
`layout`: how panels are placed. Lint names any layout key that does not belong to the chosen archetype.

Rows take their content height and the canvas fits them (`canvas.height: fit`, the default); with
`canvas.height: fixed` the preset size stays and spare height goes to the gaps between rows. A panel that spans
several rows (a rail, a side spoke) spreads its cards over its height. Chips sit under their panel's content;
`layout.chips_at: bottom` pins them to the bottom in rows where every panel has chips, so they line up.

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
```

- Flows between neighbours run straight across the gutter. Flows to a spanning row below run straight down.
- A wide bottom panel takes `arrange: row` with `weights`, so its blocks sit side by side.
- Example: `examples/orderplatform-toegang.yaml`.

## hub-and-spokes

One central panel (the hub) with up to 10 spokes around it: up to 4 above, up to 4 below, and one on each
side. Top and bottom spokes share the hub's width evenly, even when their counts differ; side spokes run the
full height. The hub gets a stronger frame.

<!-- lint: examples/orderplatform-eventbus.yaml -->
```yaml
archetype: hub-and-spokes
layout:
  hub: bus
  top: [orders, payments, shipping]       # producers, callers or sources usually go on top
  bottom: [search, analytics, notify]     # consumers or targets below
  right: ops                              # optional; also `left`. Good for operators and owners
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
  rail_width: normal                               # optional: narrow | normal | wide
```

- A layer lays its cards out in one row by default (`card_columns` = number of cards); 3–5 cards fit well.
- Flows between layers run straight down. A flow from a rail card to a layer card turns corners through
  the gutter; put the target card at the end of its layer nearest the rail, or the route is blocked.
- Rails are tall and narrow: short notes, bullets, and an info chip keep them from looking empty.
- Example: `examples/ontwikkelplatform-lagen.yaml`.

## swimlane

Who does what, in which order, and where work changes hands. One lane per actor (a panel; its name sits on the
left), steps as cards placed in phase columns that line up across lanes, and handoffs as flows between cards. A band
of phase names runs above the lanes.

<!-- lint: examples/incident-swimlane.yaml -->
```yaml
archetype: swimlane
layout:
  lanes: [monitoring, oncall, commander, comms]                       # 2 to 6, top first
  columns: ["Detect", "Triage", "Mitigate", "Communicate", "Learn"]   # optional, up to 8
```

- A card's `col` (1 is the first column) places the step; one step per column per lane.
- Number the handoffs with `step` and say `flows_mean: control` (or `request`): the order is the story.
- Put a lane's open point on a card as a `flag`; a chip spans the whole lane and blocks handoffs crossing it.
- Example: `examples/incident-swimlane.yaml`.

## nested-zones

Where things run: environments, accounts, clusters, namespaces. Zones are labelled dashed frames, side by side at
the top level and nested up to three deep; panels sit inside them. Panels outside every zone (users, partners) stand
in a column on the right.

<!-- lint: examples/kliniek-zones.yaml -->
```yaml
archetype: nested-zones
layout:
  zones:
    - id: dc
      kind: on-premises                 # optional, shown before the title
      title: "Clinic datacentre"
      zones:
        - {id: dmz, kind: network, title: "DMZ", panels: [proxy]}
        - {id: internal, kind: network, title: "Internal network", panels: [ehr, records]}
    - id: cloud
      kind: account
      title: "Cloud, production"
      zones:
        - id: cluster
          kind: cluster
          title: "Kubernetes"
          zones:
            - {id: portal-ns, kind: namespace, title: "portal", panels: [portal]}
            - {id: integration-ns, kind: namespace, title: "integration", panels: [integration]}
  outside: [patients, insurers]
```

- Every panel sits in exactly one zone or in `outside`; a zone holds zones, panels, or both.
- The zone a thing runs in is the point: say it in the title ("Patient data never leaves the clinic's datacentre").
- Flows cross zone frames freely; the gaps between zones are gutters for the router.
- Example: `examples/kliniek-zones.yaml`.

## before-after

What changes. Two columns under a label each, the plate as it is and as it will be; the panels at the same place in
`before` and `after` face each other in one row, so the reader sees what became what. The change itself shows as
`status` on the after side (`new`, `changed`, `removed`), not as arrows: arrows keep the meaning `flows_mean` gives
them, within each side.

<!-- lint: examples/invoicing-before-after.yaml -->
```yaml
archetype: before-after
layout:
  before: [erp, batch, matching]          # 1 to 4 panels, top first
  after: [invoicing, bankapi, recon]      # 1 to 4; row by row, each faces the one before it
```

- `labels: ["Today", "Phase 2"]` overrides the column labels (default Before / After; in Dutch Nu / Straks).
- Leave a row's other side empty by giving one side more panels: a part that is new, or gone.
- The title claims the difference ("Invoices reach the bank the same day"), not the topic.
- Example: `examples/invoicing-before-after.yaml`.

## Not built yet

`banded-matrix`, `roadmap`, `landscape-map` are in the schema as planned names. Lint refuses them. Until they exist:

- a roadmap → `swimlane`, with one lane per workstream and the periods as columns;
