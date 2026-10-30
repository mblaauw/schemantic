# Skill evals

Eight cases test the skill's real job: from sources to a truthful plate. Each case in `cases/` has a `prompt.md`
(what the user asks), `inputs/` (fictional sources) and a `rubric.yaml` (what a good plate must have).

| Case | Source | What it tests |
| --- | --- | --- |
| 1-notes-nl | Dutch meeting notes | inventory from notes, decisions as principles, the open point as a question, `lang: nl` |
| 2-repo-en | compose file, Terraform, README | inventory from a repository, the TODO as an open question |
| 3-series | a 40-component inventory | the series rule: two or more plates |
| 4-open-choices | a proposal with two undecided choices | both choices visible as warnings and open questions |
| 5-process-swimlane | a process with handoffs | lanes per actor, numbered steps |
| 6-deployment-zones | environments, clusters, namespaces | nested zones |
| 7-phase-change | today versus phase 2 | change status tags (new, removed, planned) |
| 8-language-follows-user | a Dutch note, an English request | the plate's language follows the user, not the source |
| 9-sequence | one payment between systems | picks a sequence; messages along rows |
| 10-capability-map | a review of what exists and what is missing | picks a map; gaps as `planned` |
| 11-comparison | options against four criteria, with a recommendation | picks a comparison; every cell filled, the pick marked |
| 12-hierarchy | a reporting structure | picks a hierarchy |
| 13-quadrant | ideas scored on two axes | picks a quadrant |

## Running

Each run gives an agent the case prompt and inputs in an empty working folder, and nothing else. **With the skill**
the agent is also given the path of a read-only copy of the skill: its runtime files only (`offline.RUNTIME`), so
neither the rubrics nor the tests are within reach. **Without** it is not, and may produce the plate any way it
can. Keep the run folders outside the repository, for the same reason.

```bash
python evals/harness.py prepare <runs> --skill <skill copy> --repeats 3   # run folders and runs/prompts.json
```

Start one agent per entry in `prompts.json`, on the model it names, with its prompt and nothing else. When they are
done, judge them blind: `harness.py blind <runs> <judge dir>` copies every run under a random name with only its case
named, a separate agent applies `judge.md` (and the review questions it points to) to each and writes `judge.json`
there, and `harness.py unblind <runs>` brings the verdicts back. Then:

```bash
python evals/run_all.py <runs>   # both halves, per run, and the totals per model
```

A run passes when both halves pass: the automated half (`grade.py`: the specs lint clean, archetype, language,
components, counts, nothing invented by name) and the judged half (a claim in the title, a fitting layout, nothing
invented, no defect). One run per case is noisy; take three.

## Latest results

Version 0.3.0, the released skill: eight cases, three runs each, judged blind with the same judge and review
questions as the runs below. A run passes when the automated grade passes and the judge finds nothing invented and no
defect; one defect fails it. In brackets, the same cases on 30 October, before the router and skill changes.

| Model | Automated | Judged | Nothing invented | Defects per plate |
| --- | --- | --- | --- | --- |
| Sonnet 5.5 | 24/24 | 3/24 (2/24) | 23/24 (22/24) | 2.12 (2.25) |
| Haiku 5.5 | 24/24 | 5/24 (2/24) | 19/24 (22/24) | 2.25 (2.50) |

Twice as many runs pass (8 against 4), and defects fell by about 8%. Take that as a direction, not a measurement: 48
runs is few, judges differ (some counted a footer of 15% as a defect, others did not), and defect kinds are sorted by
keyword.

| Case | Passed | Defects per plate |
| --- | --- | --- |
| 1 notes | 1/6 (0/6) | 1.67 (2.17) |
| 2 repository | 3/6 (0/6) | 1.50 (3.00) |
| 3 series | 0/6 (0/6) | 4.50 (3.33) |
| 4 open choices | 0/6 (0/6) | 2.00 (3.00) |
| 5 swimlane | 3/6 (4/6) | 0.67 (0.33) |
| 6 deployment | 0/6 (0/6) | 1.67 (2.17) |
| 7 phase change | 1/6 (0/6) | 2.67 (3.17) |
| 8 language | 0/6 (0/6) | 2.83 (1.83) |

By kind, of 105 defects (114 before):

- **Paths, 28 (41)**: the largest drop. Arrows ending on a panel fell from 33% to 23%, and a drawn route is on 38 of 56
  plates (29 of 57). What is left is mostly steps with no arrow at all: agents leave out a step the source implies
  (dbt builds from Bronze, the WMS books shipments) under "never invent", so that rule may be overcorrecting.
- **Holes, 21 (15)**: up. Deployment plates fail on a short zone beside tall ones. `outside_at: bottom` does not solve
  it: at least four agents tried it and backed out, because wider accounts put the data panel beside the cluster,
  stretched, which lint calls an error.
- **Colour, 14 (12)**: people and systems in one panel, an identity provider in a people panel.
- **Footer, 11 (9)**: now that lint warns at an eighth, agents see it, but many short plates cannot get under: a legend
  on two lines is enough. Most leave the warning standing.
- **Truth, 11 (15)**, **open ends, 9 (7)**, **words, 8 (7)**.
- **Invented**: Haiku fell to 19 of 24, on invented parts inside a service and on status questions the source never
  raises, even though it now leaves notes off cards that have only a name.

Series plates got worse: their second part keeps failing on "data reads from the bus", either undrawn or as an open
question the inventory settles, and on opaque stand-in panels ("Part 1 areas").

From the agents' own reports, three things this run found in the tools:

- `--review` deletes earlier crops and moves its baseline on every build, so an agent that builds several times before
  reading sees only the last round's changed parts. Most agents still read only some of the crops.
- The outline of a nested-zones plate lists panels and cards but not the zones they sit in, which on such a plate is
  the point.
- Agents spend a lot on layout: one tried 72 variants to clear one arrow crossing.

**Next targets**: inner zones that stack when an account gets wider, so `outside_at: bottom` works; crops that survive
a rebuild; zones in the outline; a footer limit a short plate can meet; and "draw what the source implies, and list it
as an assumption" in place of leaving the step out.

## History

Each run below names what changed before it and what it found; the targets it names are what the following runs
went after.

### Three runs per case (30 October)

30 October 2026, with the skill as of 0.3.0.dev0 after #17 (drawn stories, starters, review crops of what changed,
grouped findings, the reordered steps). Eight cases, **three runs each**, judged blind under random names with the
same judge and review questions as the two runs of 29 October, so the numbers compare. A run passes when the
automated grade passes and the judge finds nothing invented and no defect; one defect fails it.

| Model | Runs | Automated | Judged | Nothing invented | Defects per plate (29 Oct, one run per case) |
| --- | --- | --- | --- | --- | --- |
| Sonnet 5.5 | 24 | 24/24 | 2/24 | 22/24 | 2.25 (2.1) |
| Haiku 5.5 | 24 | 24/24 | 2/24 | 22/24 | 2.5 (2.5) |

Every plate built clean, and every title made a claim; the rest has not moved. The four passes are all the
swimlane case, which is now nearly solved (0.33 defects per plate across six runs); the worst cases are the series
(3.3), the phase change (3.2), the repository and the open choices (3.0).

By kind, of 114 defects:

- **Paths, 41 (36%)**, the same share as before: drawn stories did not move it. What fails is mostly the other
  routes a title or subtitle names: arrows that end on a panel instead of the card (the event bus, Bronze and Gold,
  the carrier integration), and steps that live only in a card note. Several agents said why: a card-to-card route
  was refused (`arrow-routing`), so they joined the panels instead.
  Cards stacked in one panel (Bronze, Silver, Gold) and cards in panels that share no gutter are the usual
  refusals; a swimlane handoff across a lane routes round the edge of the plate (all three Sonnet swimlanes).
- **Holes, 15**: one short panel alone in a column (the shared tooling account beside two tall accounts), a
  panel spread over rows it has too few cards for, and before-after rows with nothing on one side.
- **Truth, 15**: principles and titles that say a little more than the source (an ordering, "only", a variable
  a service does not have), and a preference centre drawn inside the service that only reads it.
- **Colour, 12**: people in platform panels and the reverse; `role-fit` judges by icons, and these had none that
  said so.
- **Footer, 9**: the review question calls a footer over an eighth (12.5%) a defect, but `footer-share` warns at
  15%, so plates at 13 to 15% pass lint and fail the judge. One number has to go.
- **Open ends, 7** (6 of them Haiku): open questions the source settles ("does test mirror production?").
- **Words, 7**: three channel cards with the same note, notes that repeat their zone's name.

From the agents' own reports: most read only the overview crop, not the part crops; several left an `orphan` or
`void` warning standing rather than invent an arrow or a card (one invented an order of stages to clear `orphan`);
two put nine panels on one deployment plate, past the budget of six, which no check counts; and a short zone beside
tall ones leaves a hole the nested-zones layout cannot close.

Without the skill neither model builds a spec, a lint-clean plate or traceable cards (26 October: 0/8 automated on
both); that has not been rerun since.

**Next targets**, by what they would remove: card-to-card routes the router refuses today (stacked cards in one
panel, a lane between two swimlane steps), so routes stay card to card; one footer threshold; a budget check for
panels and cards on every plate; and a hint on `orphan` that says to leave it, not to invent a flow.

### After the router fixes (30 October, second run)

The router and footer changes of #19, measured on the four cases where paths failed most (repository, series, open
choices, phase change): 24 runs, three per case on each model, same blind judge. The earlier column is the same four
cases in the run above.

| Model | Judged | Nothing invented | Defects per plate | Path defects |
| --- | --- | --- | --- | --- |
| Sonnet 5.5 | 1/12 (0/12) | 11/12 (11/12) | 2.75 (2.92) | 12 (14) |
| Haiku 5.5 | 2/12 (0/12) | 7/12 (10/12) | 3.42 (3.33) | 21 (14) |

Three runs pass where none did, but one judge gave two of them and called both close, and 12 runs per model is few.
Defects per plate did not move, and path defects rose from 28 to 33. **The router fixes did not fix paths.** Refusals
were only part of it: SKILL.md said "connect panels by default", about half of all arrows still ended on a panel, and
most path defects are arrows ending on a panel or steps with no arrow at all. Haiku also invented more (card notes
written from names), though with so few runs that may be noise. The 32 px gap between joined cards had no room for a
badge or a two-way arrow (a judge saw a diamond); it is 46 px now. The skill now says to connect cards by default,
and that every step the title states gets an arrow. That change is not measured yet.

### Latest results before the three-run rerun (29 October)

| Model | Run | Automated | Judged | Nothing invented | Defects per plate |
| --- | --- | --- | --- | --- | --- |
| Sonnet 5.5 | 29 October, second rerun | 8/8 | 2/8 | 7/8 | 2.1 |
| Haiku 5.5 | 29 October, third run | 8/8 | 0/8 | 8/8 | 2.5 |

### First run (26 October 2026)

Eight cases, with and without the skill, on Sonnet 5.5 and Haiku 5.5, one run each. A case passes when the automated grade passes and the judge finds no invented content and no defect.

| Model | Skill | Automated | Judged | Claim title | Nothing invented | Layout fits | Defects per plate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Sonnet 5.5 | without | 0/8 | 0/8 | 0/8 | 7/8 | 8/8 | 2.9 |
| Sonnet 5.5 | with | 8/8 | 0/8 | 8/8 | 8/8 | 8/8 | 2.8 |
| Haiku 5.5 | without | 0/8 | 0/8 | 0/8 | 5/8 | 7/8 | 3.8 |
| Haiku 5.5 | with | 8/8 | 2/8 | 8/8 | 8/8 | 8/8 | 2.0 |

Without the skill neither model produces a spec, a lint-clean build or traceable cards, so the automated half fails
every case; the judge then sees hand-drawn SVG or HTML. With the skill every plate builds clean, every title is a
claim and nothing is invented. Haiku gains the most: fewer invented items and half the defects.

The judge fails a plate on any one defect, which is strict on purpose. What it still found on the 16 plates made
with the skill, most frequent first:

- **Holes** (9 plates): a panel visibly emptier than its neighbours, often under the 96 px void threshold, or a
  short panel beside a tall one. Haiku's case 6 was judged on a render from before the nested-zones fix in this
  release, which removes its worst holes.
- **Footer over an eighth** (5): principles, open questions and a legend on two lines take about a fifth.
- **Paths drawn panel to panel** (4): the title promises a path through named cards that the arrows do not show.
- **Role colour** (4): systems in a people panel, or one colour for everything.
- **Open questions the sources settle** (4).

These are the next targets for lint and the review questions.

### Rerun of 29 October 2026 (with the skill only)

The same eight cases with the skill as it stands after the design tiers (claim titles with a topic line, question
labels, panels that end with their content, footer and widow lint, series checks, before-after, rails by layer,
quieter neighbours around the focus, role-fit, the slide profile, roadmap). Without the skill nothing changed, so it
was not rerun. One run per case; the judge saw the runs under neutral names.

| Model | Automated | Judged | Claim title | Nothing invented | Layout fits | Defects per plate (26 Oct) |
| --- | --- | --- | --- | --- | --- | --- |
| Sonnet 5.5 | 8/8 | 0/8 | 8/8 | 8/8 | 8/8 | 2.2 (2.8) |
| Haiku 5.5 | 8/8 | 0/8 | 8/8 | 7/8 | 8/8 | 1.6 (2.0) |

Defects fell by about a fifth on both models; the judged pass rate did not move (Haiku passed 2 of 8 before, 0
now), since the judge fails a plate on any single defect and one run per case is noisy. By kind:

- Footer over an eighth: 5 plates before, none now (`footer-share`).
- Role colour: 4 before, 2 now (`role-fit` caught and fixed two more during the runs, by the agents' reports).
- Holes are still first (12): with panels ending at their content, the judge now names the space beside a short
  panel ("ends 135 px above the panel beside it"), and an empty area inside a zone frame, which no check measures.
- Paths (6): the arrows join panels where the title names a route through cards, and two swimlane runs could not
  draw an arrow from the bottom lane back to the top one, so the agents left a step out.

The next targets: a hole check for rows and zones, card-to-card routes when the message names a path, and the
router's long upward arrows in a swimlane.

### Rerun of 29 October 2026, second (after the hole, router and path fixes)

The same eight cases with the skill, after the hole check for rows and zones, the second outer lane and the rule
that a route named in the title is traced card by card. The review questions gained the finger test, so the judge
reads paths more strictly than before; to measure that, the first rerun's Haiku plates were judged again, blind,
with the current questions.

| Model | Automated | Judged | Claim title | Nothing invented | Layout fits | Defects per plate |
| --- | --- | --- | --- | --- | --- | --- |
| Sonnet 5.5 | 8/8 | 2/8 | 8/8 | 7/8 | 8/8 | 2.1 |
| Haiku 5.5 | 8/8 | 0/8 | 8/8 | 6/8 | 8/8 | 3.5 |
| Haiku 5.5, first rerun's plates judged again | | 0/8 | 8/8 | 5/8 | 8/8 | 2.25 (1.6 then) |

- Sonnet passes the judged half for the first time (the swimlane and the deployment zones) and holds its defect
  rate under the stricter judge.
- The stricter judge alone adds about 0.6 defects per Haiku plate (1.6 to 2.25 on the same plates). Today's Haiku
  plates are worse than that, at 3.5: holes on 6 plates against 3. The holes are of kinds no check measures: an
  empty grid cell left by `areas`, cards spread apart inside a panel, and a blank band on a fixed or paper canvas.
  Two Haiku agents saw a hole and left it, because lint was clean.
- Paths are the most frequent defect on both models (16 of 45): arrows that end on a panel where the title names
  a card, and routes in the subtitle with no arrow at all.
- Two Haiku plates added small facts in card notes ("the decision becomes final"); one Sonnet series called a
  read optional by drawing it dotted.

Next targets: the three kinds of hole above as lint, a warning when a flow named in the subtitle ends on a panel
that holds the named card, and keeping the dotted style for what the legend says it means.

### Haiku after the hole checks (29 October, third run)

Haiku only, with the skill at the hole checks (empty grid cells, spread cards, blank bands; before zone frames
ended with their content). Judged blind with the same review questions as the second run and its control, so the
three Haiku rows compare directly.

| Haiku 5.5 plates | Judged | Nothing invented | Plates with holes | Defects per plate |
| --- | --- | --- | --- | --- |
| first rerun's, judged again | 0/8 | 5/8 | 3 | 2.25 |
| second rerun | 0/8 | 6/8 | 6 | 3.5 |
| after the hole checks | 0/8 | 8/8 | 2 | 2.5 |

- Holes fell from 6 plates to 2: one is two account frames half empty beside a tall one (zone frames now end with
  their content), the other a gap under 96 px.
- Nothing was invented on any plate, for the first time on Haiku.
- Paths are now most of what is left (7 of 20 defects): arrows that end on a panel, and steps that live only in a
  card note. Colour is next (3): people in a platform panel.

