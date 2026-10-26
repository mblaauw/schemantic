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
does not contain is planned or gone, so ask, or mark it `status: planned`.

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
bugs leave it. Archetype: column-flow, a path from left to right.

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
    title: "Customers"
    role: actor
    cards:
      - {icon: mail, name: "E-mail", note: "lands in Zendesk as a ticket", refs: ["notes: both land in Zendesk"]}
      - {icon: forms, name: "Web form", note: "lands in Zendesk as a ticket", refs: ["notes: both land in Zendesk"]}
      - {icon: book, name: "Help centre", note: "Zendesk Guide; articles out of date", refs: ["notes: articles ... out of date"]}
    chips:
      - {kind: warning, text: "Who owns the help centre articles?"}
  - id: support
    title: "Support"
    subtitle: "All work happens in Zendesk"
    role: platform
    cards:
      - {icon: ticket, name: "Zendesk", note: "one queue for every question", refs: ["notes: both land in Zendesk"]}
      - {icon: headset, name: "First line", note: "answers questions", refs: ["notes: First line answers questions"]}
      - {icon: bug, name: "Second line", note: "takes bugs and reproduces them", refs: ["notes: second line takes bugs"]}
    chips:
      - {kind: warning, text: "Status page: Statuspage or our own?"}
  - id: engineering
    title: "Engineering"
    role: platform
    cards:
      - {icon: list-details, name: "Jira", note: "confirmed bugs, through the integration", refs: ["notes: through the Zendesk integration"]}
      - {icon: users-group, name: "Product team", note: "triages Jira every Monday", refs: ["notes: triages Jira every Monday"]}
flows_mean: request
flows:
  - {from: customers, to: support}
  - {from: support, to: engineering}
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

Inventory, with refs: browser app (`compose: web`), API (`compose: api`), worker (`compose: worker`), PostgreSQL
(`tf: aws_db_instance.main`), upload bucket (`tf: aws_s3_bucket.uploads`), Redis queue (`tf:
aws_elasticache_cluster.queue`; `compose: redis` locally). Flows from the environment variables: API and worker to
the database and the queue. Open point: the `TODO`.

Grouping by responsibility. Message: the API takes every request; slow work goes through a queue to the worker.

<!-- lint: full -->
```yaml
canvas: {size: landscape-4x3, lang: en}
title: "The API answers every request; slow work goes to a worker"
subtitle: "Uploads are queued in Redis and scanned by the worker before they are stored"
archetype: column-flow
brief:
  message: "Requests stay fast because the worker does the slow work behind a queue."
  reader: "Engineers joining the team"
  why: "column-flow: requests travel left to right, with the stores underneath"
  left_out: ["nginx configuration details"]
sources:
  - {id: compose, kind: repository, ref: "docker-compose.yml"}
  - {id: tf, kind: repository, ref: "terraform/main.tf"}
  - {id: readme, kind: document, ref: "README.md"}
  - {id: code, kind: repository, ref: "worker/tasks.py"}
layout:
  areas:
    - "clients app app"
    - "clients data data"
panels:
  - id: clients
    title: "Clients"
    role: external
    cards:
      - {icon: browser, name: "Browser app", note: "single-page app, served by nginx", refs: ["compose: services.web"]}
  - id: app
    title: "Application"
    role: platform
    card_columns: 2
    cards:
      - {id: api, icon: api, name: "API", qualifier: "FastAPI", note: "takes every request", refs: ["compose: services.api"]}
      - {id: worker, icon: settings, name: "Worker", qualifier: "Celery", note: "scans uploads, then stores them",
         refs: ["compose: services.worker", "readme: uploads are scanned before they are stored"],
         flag: {kind: warning, text: "Move scanning to a managed service?"}}
  - id: data
    title: "Data"
    role: data
    card_columns: 3
    cards:
      - {icon: database, name: "PostgreSQL", note: "orders and accounts", refs: ["tf: aws_db_instance.main"]}
      - {icon: stack-2, name: "Redis queue", note: "jobs from API to worker", refs: ["tf: aws_elasticache_cluster.queue"]}
      - {icon: bucket, name: "Upload bucket", note: "scanned files only", refs: ["tf: aws_s3_bucket.uploads"]}
flows_mean: request
flows:
  - {from: clients, to: app}
  - {from: app, to: data}
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
500 euro, pay with salary. Handoffs: employee to manager, manager to finance (only over 500 euro), finance to
payroll.

Grouping by actor, in the order of the steps. A process with handoffs between people is a swimlane; until that
archetype is built, use a column-flow with one panel per actor and numbered steps.

<!-- lint: full -->
```yaml
canvas: {size: landscape-4x3, lang: en}
title: "An expense claim passes three desks before it is paid"
subtitle: "Manager approval for every claim, a finance check above 500 euro, payment with the next salary"
archetype: column-flow
brief:
  message: "Every claim takes the same path; only the finance check depends on the amount."
  reader: "Employees and managers who submit or approve claims"
  why: "column-flow with one panel per actor, as a stand-in for a swimlane"
sources:
  - {id: process, kind: process, ref: "Expense claims procedure"}
layout:
  areas: ["employee manager finance payroll"]
panels:
  - id: employee
    title: "Employee"
    role: actor
    cards:
      - {icon: receipt, name: "Submit claim", note: "in the expense app, with a receipt photo", refs: ["process: submits an expense claim"]}
  - id: manager
    title: "Manager"
    role: actor
    cards:
      - {icon: circle-check, name: "Approve or reject", note: "every claim", refs: ["process: approves or rejects it"]}
  - id: finance
    title: "Finance"
    role: actor
    cards:
      - {icon: scale, name: "Policy check", note: "claims over 500 euro", refs: ["process: claims over 500 euro"]}
  - id: payroll
    title: "Payroll"
    role: actor
    cards:
      - {icon: cash, name: "Pay out", note: "with the next salary run", refs: ["process: paid with the next salary run"]}
flows_mean: control
flows:
  - {from: employee, to: manager, step: 1}
  - {from: manager, to: finance, step: 2}
  - {from: finance, to: payroll, step: 3}
footer:
  principles:
    - "A claim without a receipt photo cannot be submitted."
  legend: auto
```
