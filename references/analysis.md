# From sources to a plate

A plate is only as good as the analysis behind it. Work in four passes: inventory, grouping, the message, and the
cut. Write the result as the spec's `brief`, then audit it against the sources before writing any panel.

## 1. Inventory: what exists, according to the sources

List every thing the sources name, one line each: **what it is**, **its kind** (person or team, system, data
store, external system, decision, open point), **where it comes from**, and **what it talks to**. Keep the source
reference: it becomes the card's `refs`. Do not add things the sources do not name; a gap is an open question.

### From a conversation or notes

- **Actors:** people, roles and teams ("second line", "data engineers", "partners").
- **Systems:** named products and services ("Zendesk", "the order service"), and what each does in this story.
- **Data:** where information lives ("tickets", "the lakehouse", "customer profiles").
- **Decisions:** sentences that settle something ("we keep one identity provider"). These become principles.
- **Open points:** anything undecided, disputed or unknown ("not decided whether ..."). These become warning
  chips or open questions, never facts.

### From a repository

Read these, in this order, and note the file and key for each finding:

| File | What it gives |
| --- | --- |
| `README*`, `docs/`, ADRs (`docs/adr/`, `adr/`) | the system's purpose, its parts, decisions already made |
| `docker-compose*.yml` | services (one card each), images, `depends_on` and ports (flows), volumes (data) |
| Kubernetes manifests, Helm `values.yaml` | Deployments and Services (cards), Ingress (entry points), ConfigMaps (dependencies) |
| Terraform (`*.tf`) | managed resources: databases, queues, buckets, caches (data panel), networks and accounts (infrastructure) |
| CI workflows (`.github/workflows/`, `.gitlab-ci.yml`) | how changes reach production, which environments exist |
| package manifests (`pyproject.toml`, `package.json`, `go.mod`) | frameworks and clients, which hint at what talks to what |
| service entrypoints, routers | the API surface each service offers |
| environment variables (`*_URL`, `*_HOST`, `.env.example`) | which service calls which, and external systems |

A dependency the code shows but no document explains is still a fact; a component a document names but the code
does not contain is planned or gone: ask, or make it an open question. With nothing to quote, it gets no status.

### From a process description

- **Actors:** who does each step (a person, a team, a system acting on its own).
- **Steps:** each action, in order, with its actor.
- **Handoffs:** where work moves from one actor to another; these are the flows.
- **Systems per step:** what each actor uses there.

## 2. Grouping: 3 to 6 panels

Group the inventory by one rule and say which: **responsibility** (what a part does), **boundary** (inside or
outside the team's control), **owner** (which team runs it), or **stage** (where in the flow it sits). Mixing rules
makes panels a reader cannot name. Each panel gets 2 to 6 cards; a panel with one card belongs in another panel, a
panel with seven needs splitting.

## 3. The message

Write the title as a claim the grouping supports ("Every customer question lands in one Zendesk queue"). If no claim
fits, the grouping is wrong, or the plate is two plates. The subtitle says how the claim is true.
When the title or subtitle names a route ("A via B to C"), that route is the claim: connect its cards, not their
panels, and write it as a `story` so lint checks a finger can follow it. Each worked example below does.

## 4. The cut

- Leave out what does not serve the message, and list it in the brief's `left_out`.
- Turn every uncertainty into a warning chip or open question; never resolve it by guessing.
- Over budget (more than 6 panels or 30 cards): split into a series, one message per plate.

## Worked example A: meeting notes

Source (`notes`, fictional): *Support review, 3 March. Customers reach us by e-mail and through the web form; both
land in Zendesk. First line answers questions; second line takes bugs and reproduces them. Confirmed bugs go to Jira
through the Zendesk integration, and the product team triages Jira every Monday. Articles in the help centre (Zendesk
Guide) are out of date and nobody owns them. We want a status page, but have not decided between Statuspage and
building our own.*

Inventory: customers (actor, notes); e-mail and web form (entry points, notes); Zendesk (system); first line and
second line (teams); Jira (system); product team (team); help centre (system, owner unknown: open point); status page
(undecided: open point). Decisions: everything lands in Zendesk; only confirmed bugs go to Jira.

Grouping by stage: where questions come from, where they are handled, where bugs go. Message: one queue, and only
bugs leave it. Archetype: column-flow, a path from left to right. The subtitle names a route (a bug's way out,
through second line to Jira), so its cards get ids, flows join those cards, and the route is a story.

<!-- lint: full -->
```yaml
canvas: {size: landscape-4x3, lang: en}
title: "Every customer question lands in one Zendesk queue"
subtitle: "Support answers in Zendesk; only confirmed bugs leave it, through Jira"
archetype: column-flow
brief:
  message: "One queue for every question; bugs are the only thing that leaves it."
  reader: "The support and product leads, deciding on the status page and help centre ownership"
  why: "column-flow: the story is a path from customer to engineering"
  left_out: ["Monday triage agenda: a meeting detail, not architecture"]
sources:
  - {id: notes, kind: notes, ref: "Support review, 3 March"}
layout:
  areas: ["customers support engineering"]
panels:
  - id: customers
    title: "Ways in"
    role: external
    cards:
      - {id: mail, icon: mail, name: "E-mail", note: "lands in Zendesk as a ticket", refs: ["notes: both land in Zendesk"]}
      - {id: form, icon: forms, name: "Web form", note: "lands in Zendesk as a ticket", refs: ["notes: both land in Zendesk"]}
      - {icon: book, name: "Help centre", note: "Zendesk Guide; articles out of date", refs: ["notes: articles ... out of date"]}
    chips:
      - {kind: warning, text: "Who owns the help centre articles?", refs: ["notes: nobody owns them"]}
  - id: support
    title: "Support"
    subtitle: "All work happens in Zendesk"
    role: platform
    cards:
      - {id: zendesk, icon: ticket, name: "Zendesk", note: "one queue for every question", refs: ["notes: both land in Zendesk"]}
      - {icon: headset, name: "First line", note: "answers questions", refs: ["notes: First line answers questions"]}
      - {id: second, icon: bug, name: "Second line", note: "takes bugs and reproduces them", refs: ["notes: second line takes bugs"]}
  - id: engineering
    title: "Engineering"
    role: platform
    cards:
      - {id: jira, icon: list-details, name: "Jira", note: "confirmed bugs, through the integration", refs: ["notes: through the Zendesk integration"]}
      - {icon: users-group, name: "Product team", note: "triages Jira every Monday", refs: ["notes: triages Jira every Monday"]}
    chips:
      - {kind: warning, text: "Status page: Statuspage or our own?", refs: ["notes: have not decided between Statuspage and building our own"]}
flows_mean: request
flows:
  - {from: mail, to: zendesk, refs: ["notes: both land in Zendesk"]}
  - {from: form, to: zendesk, refs: ["notes: both land in Zendesk"]}
  - {from: zendesk, to: second, refs: ["notes: second line takes bugs"]}
  - {from: second, to: jira, refs: ["notes: Confirmed bugs go to Jira"]}
stories:
  - name: "A bug leaves Zendesk only through Jira"
    path: [form, zendesk, second, jira]
footer:
  principles:
    - "Every customer question becomes a Zendesk ticket."
    - "Only bugs confirmed by second line move to Jira."
  open_questions: {from_chips: true}
  legend: auto
```

## Worked example B: a repository

Sources (fictional): `docker-compose.yml` has services `web` (nginx serving the single-page app), `api` (FastAPI),
`worker` (Celery) and `redis`; `api` and `worker` both read `DATABASE_URL` and `REDIS_URL`; `terraform/main.tf`
declares `aws_db_instance.main` (PostgreSQL), `aws_s3_bucket.uploads` and `aws_elasticache_cluster.queue`; the
README says uploads are scanned before they are stored, and a `TODO` in `worker/tasks.py` asks whether scanning
should move to a managed service.

Inventory, with refs: browser app and nginx (`compose: web`), API (`compose: api`), worker (`compose: worker`), PostgreSQL
(`tf: aws_db_instance.main`), upload bucket (`tf: aws_s3_bucket.uploads`), Redis queue (`tf:
aws_elasticache_cluster.queue`; `compose: redis` locally). Flows from the environment variables: API and worker to
the database and the queue. Open point: the `TODO`.

Grouping by responsibility. Message: the API takes every request; slow work goes through a queue to the worker.
That is a route (API, queue, worker, bucket), so the flows join those cards and the route is a story. No source says the
browser app calls the API, though nothing else could take its requests: that arrow is `assumed`, and the plate shows it.

<!-- lint: full -->
```yaml
canvas: {size: landscape-4x3, lang: en}
title: "The API answers every request; slow work goes to a worker"
subtitle: "Uploads are queued in Redis and scanned by the worker before they are stored"
archetype: column-flow
brief:
  message: "Requests stay fast because the worker does the slow work behind a queue."
  reader: "Engineers joining the team"
  why: "column-flow: requests travel left to right, into the stores"
  left_out: ["nginx configuration details"]
sources:
  - {id: compose, kind: repository, ref: "docker-compose.yml"}
  - {id: tf, kind: repository, ref: "terraform/main.tf"}
  - {id: readme, kind: document, ref: "README.md"}
  - {id: code, kind: repository, ref: "worker/tasks.py"}
layout:
  areas:
    - "web app data"
panels:
  - id: web
    title: "Front end"
    role: platform
    cards:
      - {id: browser, icon: browser, name: "Browser app", note: "single-page app, served by nginx", refs: ["compose: services.web"]}
      - {icon: server, name: "nginx", note: "serves the single-page app", refs: ["compose: services.web"]}
  - id: app
    title: "Application"
    role: platform
    card_columns: 1
    cards:
      - {id: api, icon: api, name: "API", qualifier: "FastAPI", note: "takes every request", refs: ["compose: services.api"]}
      - {id: worker, icon: settings, name: "Worker", qualifier: "Celery", note: "scans uploads, then stores them",
         refs: ["compose: services.worker", "readme: uploads are scanned before they are stored"],
         flag: {kind: warning, text: "Move scanning to a managed service?", refs: ["code: TODO in worker/tasks.py"]}}
  - id: data
    title: "Data"
    role: data
    card_columns: 1
    cards:
      - {id: queue, icon: stack-2, name: "Redis queue", note: "jobs from API to worker", refs: ["tf: aws_elasticache_cluster.queue"]}
      - {icon: database, name: "PostgreSQL", note: "read by the API and the worker", refs: ["tf: aws_db_instance.main", "compose: DATABASE_URL"]}
      - {id: bucket, icon: bucket, name: "Upload bucket", note: "scanned files only", refs: ["tf: aws_s3_bucket.uploads"]}
flows_mean: data
flows:
  - {from: browser, to: api, assumed: "nginx serves the app; no source names what it calls"}
  - {from: api, to: queue, refs: ["compose: REDIS_URL on api"]}
  - {from: queue, to: worker, style: async, refs: ["compose: REDIS_URL on worker"]}
  - {from: worker, to: bucket, refs: ["readme: uploads are scanned before they are stored"]}
stories:
  - name: "An upload, from the API through the queue to the bucket"
    path: [api, queue, worker, bucket]
footer:
  principles:
    - "Nothing slow runs inside a request; it becomes a job on the queue."
  open_questions: {from_chips: true}
  legend: auto
```

## Worked example C: a process

Source (fictional): *An employee submits an expense claim in the expense app with a photo of the receipt. Their
manager approves or rejects it. Finance checks claims over 500 euro against the policy. Approved claims are paid with
the next salary run by payroll.*

Inventory: employee, manager, finance, payroll (actors); expense app (system); steps: submit, approve, check over
500 euro, pay with salary. Handoffs: employee to manager; manager to finance over 500 euro, and straight to payroll
otherwise; finance to payroll. Both paths are drawn, or the plate says every claim passes finance.

Grouping by actor, in the order of the steps. A process with handoffs between people is a swimlane: one lane per
actor, steps in phase columns, numbered handoffs.

<!-- lint: full -->
```yaml
canvas: {size: landscape-4x3, lang: en}
title: "Only expense claims over 500 euro wait for finance"
subtitle: "A manager approves every claim; finance checks the large ones; payroll pays with the next salary"
archetype: swimlane
brief:
  message: "Every claim takes the same path; only the finance check depends on the amount."
  reader: "Employees and managers who submit or approve claims"
  why: "swimlane: handoffs between people, in order"
sources:
  - {id: process, kind: process, ref: "Expense claims procedure"}
layout:
  lanes: [employee, manager, finance, payroll]
  columns: ["Submit", "Approve", "Check", "Pay"]
panels:
  - id: employee
    title: "Employee"
    role: actor
    cards:
      - {id: submit, icon: receipt, name: "Submit claim", note: "in the expense app, with a receipt photo", col: 1,
         refs: ["process: submits an expense claim"]}
  - id: manager
    title: "Manager"
    role: actor
    cards:
      - {id: approve, icon: circle-check, name: "Approve or reject", note: "every claim; over 500 euro to finance", col: 2,
         refs: ["process: approves or rejects it"]}
  - id: finance
    title: "Finance"
    role: actor
    cards:
      - {id: check, icon: scale, name: "Policy check", note: "claims over 500 euro", col: 3,
         refs: ["process: claims over 500 euro"]}
  - id: payroll
    title: "Payroll"
    role: actor
    cards:
      - {id: pay, icon: cash, name: "Pay out", note: "with the next salary run", col: 4,
         refs: ["process: paid with the next salary run"]}
flows_mean: control
flows:
  - {from: submit, to: approve, step: 1, refs: ["process: Their manager approves or rejects it"]}
  - {from: approve, to: check, step: 2, refs: ["process: Finance checks claims over 500 euro"]}
  - {from: check, to: pay, step: 3, refs: ["process: Approved claims are paid"]}
  - {from: approve, to: pay, refs: ["process: Approved claims are paid"]}
stories:
  - name: "A claim over 500 euro"
    path: [submit, approve, check, pay]
  - name: "A claim of 500 euro or less"
    path: [submit, approve, pay]
footer:
  principles:
    - "Every claim is approved by the employee's manager."
    - "Finance checks only the claims over 500 euro."
  legend: auto
```

## Worked example D: a series

Source (`inventory`, fictional): *Library platform. Lending: catalogue, loans, reservations, renewals, fines. Members:
accounts, cards, notices. Branches: opening hours, stock, returns, transfers. Back office: invoicing, purchasing,
payroll. Reporting: dashboards, exports. Everything publishes events to the event hub; reporting reads from it. Lending
calls members; branches call lending.*

The inventory tells two stories, the calls between areas and the events across them, and one plate carries one message.
Part 1 takes the calls between lending, members and branches. Part 2, below, takes the events. Its title makes two
claims, so both get arrows: a stand-in panel holds what part 1 owns, named for what it holds, and the hub is a card of
its own in the middle. An arrow from a whole panel is right here: every card in it publishes, so one arrow says it
without seven. The inventory names no owner or status, so no card has a note and nothing is asked about either.

<!-- lint: full -->
```yaml
canvas: {size: landscape-4x3, lang: en, series: "Library platform", part: 2, of: 2}
title: "Every area publishes events to one hub, and reporting reads from it"
subtitle: "Lending, members and branches are on part 1; the back office publishes here too"
archetype: hub-and-spokes
brief:
  message: "One hub carries every event; reporting reads only from there."
  reader: "The board, after part 1"
  why: "hub-and-spokes: one thing in the middle, publishers above and readers below"
  assumptions: ["Everything in the inventory means every area, the back office included"]
sources:
  - {id: inventory, kind: document, ref: "Platform inventory"}
layout:
  hub: hub
  top: [lending, office]
  bottom: [reporting]
panels:
  - id: hub
    title: "Events"
    role: data
    cards:
      - {id: bus, icon: topology-star, name: "Event hub", refs: ["inventory: the event hub"]}
  - id: lending
    title: "Lending, members and branches"
    subtitle: "Part 1 shows their calls"
    role: platform
    card_columns: 3
    cards:
      - {id: lend, icon: books, name: "Lending", refs: ["inventory: Lending"]}
      - {id: mem, icon: id, name: "Members", refs: ["inventory: Members"]}
      - {id: bra, icon: building, name: "Branches", refs: ["inventory: Branches"]}
  - id: office
    title: "Back office"
    role: platform
    card_columns: 3
    cards:
      - {id: inv, icon: receipt, name: "Invoicing", refs: ["inventory: Back office"]}
      - {id: pur, icon: shopping-cart, name: "Purchasing", refs: ["inventory: Back office"]}
      - {id: pay, icon: cash, name: "Payroll", refs: ["inventory: Back office"]}
  - id: reporting
    title: "Reporting"
    role: data
    card_columns: 2
    cards:
      - {id: dash, icon: chart-bar, name: "Dashboards", refs: ["inventory: Reporting"]}
      - {id: exp, icon: file-export, name: "Exports", refs: ["inventory: Reporting"]}
flows_mean: data
flows:
  - {from: lending, to: hub, label: "events", refs: ["inventory: Everything publishes events to the event hub"]}
  - {from: office, to: hub, label: "events", refs: ["inventory: Everything publishes events to the event hub"]}
  - {from: hub, to: reporting, label: "reads", refs: ["inventory: reporting reads from it"]}
footer:
  principles:
    - "Reporting reads events from the hub."
  legend: auto
```
