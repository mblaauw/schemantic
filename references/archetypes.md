# Archetypes

Every archetype uses the same panels, cards, chips, patterns, flows and footer. They differ only in
`layout`: how panels are placed. Lint names any layout key that does not belong to the chosen archetype. The blocks
below show `layout` only; `plate.py new <archetype>` writes a whole spec to start from.

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
- A rail card may name the layer it concerns (`layer: runtime`): it then sits level with that layer's cards, and an
  arrow from it to that layer runs straight. Cards without a layer follow the one before; layered cards go top to
  bottom. Lint warns (`rail-layer`) when the cards above leave no room to reach the layer.
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
- A handoff crosses the empty cells of the lanes between its steps, straight down or up its column; it cannot
  cross a step's card or a lane's name.
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
- One or two short panels beside tall zones leave a hole: put them in a row underneath with `outside_at: bottom`,
  or give a short zone the same treatment by moving its panels to `outside`. A zone that holds zones takes its
  parent's whole width, so a small zone beside it wraps underneath.
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

## roadmap

What comes when, per workstream, and where we are now. One lane per workstream, items as cards in period columns
(a card's `col`, and `span` for an item that runs over several periods), and a band of periods on top with `now`
marked in the accent colour. Built on the swimlane.

<!-- lint: examples/portal-roadmap.yaml -->
```yaml
archetype: roadmap
layout:
  lanes: [identity, selfservice, mobile, platform]       # one per workstream, top first
  columns: ["Q1 2027", "Q2 2027", "Q3 2027", "Q4 2027"]  # the periods
  now: 1                                                 # optional: the current period
```

- Every item has a `col`; items in one lane do not overlap. Use status for what is new or changed.
- Say `flows_mean: sequence` and point each arrow from what comes first to what builds on it, so arrows run forward
  in time; lint warns (`timeline`) when one points back. The `now` period is tinted down through every lane.
- The title claims the order that matters ("Self-service ships before the new mobile app"), not the year.
- Example: `examples/portal-roadmap.yaml`.

## sequence

Who calls whom, in what order, for one request. One column per participant with its lifeline, time running down. A
card is what that participant does at one moment (`row`); a message is a flow between two cards in one row, and the
messages number themselves by row.

<!-- lint: examples/token-check-sequence.yaml -->
```yaml
archetype: sequence
layout:
  participants: [shop, gateway, identity, orders]   # 2 to 6 lifelines, left to right
```

- Every card has a `row`; one card per participant per row, one message per row, up to 12 on a lifeline. A step with no
  message is a card alone. Name a card for what happens, in a word or two: six lifelines leave little width.
- A message crosses other lifelines only where their row is empty: lint names the card in the way.
- `style: async` draws a reply or an event dashed. Keep it to one path: a second path is a second plate.
- The title claims the order that matters ("The gateway checks every token before a request reaches a service").
- Example: `examples/token-check-sequence.yaml`.

## capability-map

What we can do, and where the gaps are. One row per domain, its capabilities sharing the row's width. No arrows:
`status` is the assessment, so the gaps show at a glance.

<!-- lint: examples/retail-capability-map.yaml -->
```yaml
archetype: capability-map
layout:
  domains: [sell, fulfil, aftersales, insight]   # 2 to 6 rows, top first
  per_row: 5                                     # optional: columns that line up; a shorter row then ends in a gap
```

- `planned` is a gap, `deprecated` is on its way out, no status is in place. Only use what the sources assess: a thing
  that works on a scheduler being replaced is not itself on its way out.
- `focus: true` on the domain the title is about. Panel colours stay out of the legend. Flows are allowed, but a map that
  needs many is a column-flow.
- The title claims the finding ("Selling is covered; the gaps are all in after-sales"), not "capability overview".
- Example: `examples/retail-capability-map.yaml`.

## comparison

Which option, and why. Options as columns, criteria as rows, one card in every cell with the verdict; `pick` marks the
option the plate recommends and tints it through every row.

<!-- lint: examples/search-engine-comparison.yaml -->
```yaml
archetype: comparison
layout:
  options: ["Database search", "Self-hosted engine", "Managed search"]   # 2 to 4
  pick: 3                                                                # optional: the recommended option
  criteria: [quality, effort, cost, risk]                                # 2 to 6 rows, top first
```

- Every criterion has one card per option; `col` names the option. The name is the verdict, the note the reason.
- The icon carries the verdict: `circle-check`, `alert-triangle`, `circle-x`. Panel colours mean nothing here and stay
  out of the legend.
- Nothing decided yet? Leave out `pick`, and put the choice in a flag: the plate still shows the trade-off.
- Example: `examples/search-engine-comparison.yaml`.

## hierarchy

What is made of what, or who reports to whom. A tree drawn top down from `root`; a parent spans the columns of
everything under it, so each child stands under its parent. The arrows follow from the tree.

<!-- lint: examples/platform-org-hierarchy.yaml -->
```yaml
archetype: hierarchy
layout:
  root: head
  children:                                # panel -> the panels directly under it
    head: [commerce, foundation]
    commerce: [shopfront, checkout]
    foundation: [data, runtime]
```

- Up to 4 levels and 8 panels at the ends of the tree; each panel has one parent. Say `flows_mean` for what the tree
  means: `control` for reporting lines (the legend says "Leads"), `dependency` for what is made of what.
- `flows` are only for what cuts across the tree, and are drawn on top of the tree's own arrows.
- Example: `examples/platform-org-hierarchy.yaml`.

## quadrant

Where each thing sits on two axes. Four panels in a two-by-two with a label for each half of each axis. The position
is the message, so arrows are optional.

<!-- lint: examples/migration-quadrant.yaml -->
```yaml
archetype: quadrant
layout:
  x: ["Low risk", "High risk"]        # over the left and right columns
  y: ["High value", "Low value"]      # beside the top and bottom rows
  cells: [first, plan, later, leave]  # left to right, top row first
```

- Title a panel with what the sources decide about it ("Move first"). Where they decide nothing, name its place ("High
  value, high effort"): a verdict you made up is an invention, however natural it reads. A note says why a card sits
  there only if the sources do; repeating the axes adds nothing.
- `focus: true` on the quadrant the title is about. Panel colours stay out of the legend.
- Example: `examples/migration-quadrant.yaml`.
