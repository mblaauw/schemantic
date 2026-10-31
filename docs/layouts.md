# Layouts

Every layout Schemantic can draw, as a sketch. The sketches show the idea, not a real plate: the words are placeholders. Each
row links to a finished plate built from a fictional spec. The keys and limits of each layout are in
[`references/archetypes.md`](../references/archetypes.md).

The colours mean the same everywhere: blue for what the team builds or runs, green for data, grey for what is outside its
control, purple for people. A filled header is the one place the plate is about.

Pick on the reader's question. When unsure, use `column-flow`. More than 6 panels or 30 cards is two plates, a series,
each with its own message.

## column-flow

<img src="img/layouts/column-flow.svg" alt="column-flow" width="360">

**The reader asks:** How does a request or data get from A to Z?

**Not this when:** Everything hangs off one central part: `hub-and-spokes`.

**Finished plate:** [`examples/orderplatform-toegang.yaml`](../examples/orderplatform-toegang.yaml) ([image](../assets/gallery/orderplatform-toegang.webp))

## hub-and-spokes

<img src="img/layouts/hub-and-spokes.svg" alt="hub-and-spokes" width="360">

**The reader asks:** What sits around the one central thing, and how does it connect?

**Not this when:** There is an order to the parts: `column-flow`.

**Finished plate:** [`examples/orderplatform-eventbus.yaml`](../examples/orderplatform-eventbus.yaml) ([image](../assets/gallery/orderplatform-eventbus.webp))

## layer-cake

<img src="img/layouts/layer-cake.svg" alt="layer-cake" width="360">

**The reader asks:** What builds on what, and what cuts across all of it?

**Not this when:** Layers talk sideways more than up and down: `column-flow`.

**Finished plate:** [`examples/ontwikkelplatform-lagen.yaml`](../examples/ontwikkelplatform-lagen.yaml) ([image](../assets/gallery/ontwikkelplatform-lagen.webp))

## swimlane

<img src="img/layouts/swimlane.svg" alt="swimlane" width="360">

**The reader asks:** Who does what, in which order, and where does work change hands?

**Not this when:** It is about systems, not people: `column-flow`.

**Finished plate:** [`examples/incident-swimlane.yaml`](../examples/incident-swimlane.yaml) ([image](../assets/gallery/incident-swimlane.webp))

## nested-zones

<img src="img/layouts/nested-zones.svg" alt="nested-zones" width="360">

**The reader asks:** Where does everything run, and what is inside what?

**Not this when:** The question is how things talk, not where they live: `column-flow`.

**Finished plate:** [`examples/kliniek-zones.yaml`](../examples/kliniek-zones.yaml) ([image](../assets/gallery/kliniek-zones.webp))

## before-after

<img src="img/layouts/before-after.svg" alt="before-after" width="360">

**The reader asks:** What changes, and what does each part become?

**Not this when:** The change has more than about four parts: a series of plates.

**Finished plate:** [`examples/invoicing-before-after.yaml`](../examples/invoicing-before-after.yaml) ([image](../assets/gallery/invoicing-before-after.webp))

## roadmap

<img src="img/layouts/roadmap.svg" alt="roadmap" width="360">

**The reader asks:** What comes when, and where are we now?

**Not this when:** It is who hands work to whom: `swimlane`.

**Finished plate:** [`examples/portal-roadmap.yaml`](../examples/portal-roadmap.yaml) ([image](../assets/gallery/portal-roadmap.webp))

## sequence

<img src="img/layouts/sequence.svg" alt="sequence" width="360">

**The reader asks:** Who calls whom, in what order, for this one request?

**Not this when:** People hand work over: `swimlane`; it is the whole system: `column-flow`.

**Finished plate:** [`examples/token-check-sequence.yaml`](../examples/token-check-sequence.yaml) ([image](../assets/gallery/token-check-sequence.webp))

## capability-map

<img src="img/layouts/capability-map.svg" alt="capability-map" width="360">

**The reader asks:** What can we do, and where are the gaps?

**Not this when:** How the parts talk matters: `column-flow`.

**Finished plate:** [`examples/retail-capability-map.yaml`](../examples/retail-capability-map.yaml) ([image](../assets/gallery/retail-capability-map.webp))

## comparison

<img src="img/layouts/comparison.svg" alt="comparison" width="360">

**The reader asks:** Which option, and why?

**Not this when:** There is one design and no choice: any other.

**Finished plate:** [`examples/search-engine-comparison.yaml`](../examples/search-engine-comparison.yaml) ([image](../assets/gallery/search-engine-comparison.webp))

## hierarchy

<img src="img/layouts/hierarchy.svg" alt="hierarchy" width="360">

**The reader asks:** What is made of what, or who reports to whom?

**Not this when:** Things have more than one parent: `column-flow`.

**Finished plate:** [`examples/platform-org-hierarchy.yaml`](../examples/platform-org-hierarchy.yaml) ([image](../assets/gallery/platform-org-hierarchy.webp))

## quadrant

<img src="img/layouts/quadrant.svg" alt="quadrant" width="360">

**The reader asks:** Where does each thing sit on two axes?

**Not this when:** One axis is time: `roadmap`.

**Finished plate:** [`examples/migration-quadrant.yaml`](../examples/migration-quadrant.yaml) ([image](../assets/gallery/migration-quadrant.webp))

## Inside a panel

Any panel can hold a pattern beside or instead of its cards, in any layout. The fields are in
[`references/spec-guide.md`](../references/spec-guide.md).

| Pattern | | What it shows |
| --- | --- | --- |
| `tier-strip` | <img src="img/layouts/pattern-tier-strip.svg" alt="tier-strip" width="170"> | Tiles in a row, each tier leading to the next: bronze, silver, gold. |
| `process-strip` | <img src="img/layouts/pattern-process-strip.svg" alt="process-strip" width="170"> | Numbered steps in a row, inside one panel. |
| `tree` | <img src="img/layouts/pattern-tree.svg" alt="tree" width="170"> | An indented listing: folders, keys, topics. |
| `matrix` | <img src="img/layouts/pattern-matrix.svg" alt="matrix" width="170"> | Rows against columns, each cell full, partial or none: who may do what. |

## Marks on any layout

| Mark | Means | In the spec |
| --- | --- | --- |
| A filled header, or a heavy blue outline | the one point of the plate | `focus` |
| A tag beside a name | new, changed, planned, phasing out, removed | `status` |
| A dashed box | planned, not built yet | `status: planned` |
| An amber dashed arrow, or an "assumed" tag | the sources do not say this | `assumed: <why>` |
| A dashed or dotted arrow | asynchronous, or optional | `style: async`, `style: optional` |
| A number on an arrow | a step in the route the title tells | a story with `draw: true` |
| Q1 on a card or chip, again in the footer | an open question | a `warning` chip or card `flag` |
