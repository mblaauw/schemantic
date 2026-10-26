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

## Running

Each run gives an agent the case prompt and inputs in an empty working folder, and nothing else. **With the skill**
the agent is also given `SKILL.md`'s path; **without** it is not, and may produce the plate any way it can. Collect
everything it writes into `runs/<model>/<with|without>/<case>/`, then grade:

```bash
python evals/grade.py evals/cases/<case> runs/<model>/<with|without>/<case>   # the automated half
```

and have a separate agent apply `judge.md` to the same folder (the judged half). A run passes when both halves pass.
`run_all.py` grades every run folder and prints the table below.

## Results

Not run yet in this release; see the latest entry in `CHANGELOG.md`.
