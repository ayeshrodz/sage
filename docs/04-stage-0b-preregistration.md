# Stage 0b pre-registration: learning the library

**Registered:** 2026-09-25, before any stage 0b code existed and before the hidden test split was generated.  
**Agreed by:** the project author (P1 and P2 approved in conversation on 2026-09-25).

## Question

Starting from the 28 base instructions only, can the system learn a library from a stream of tasks that makes *unseen* tasks cheaper to solve? Every cost is counted.

## Splits (4 demonstrations per task, natural tasks, 5 held-out queries per stratum)

| Split | Tasks | Who sees what |
|---|---:|---|
| `train` | 200 | The learner sees the demonstrations. |
| `val` | 40 | The learner sees the demonstrations and uses them to accept or reject library changes. It never sees the queries. |
| `test` | 100 | **Hidden.** Evaluated once, after the learner configuration is frozen in a commit. |
| `control-train` / `control-test` | 200 / 100 | The same protocol on a stream **with no shared structure**. Each task is built from 2–3 *fresh* random macros of 2–5 instructions, so every task has the same generative shape as a planted task but nothing recurs across tasks. |

Split names give disjoint random streams (hashed manifests recorded, as in 0a).

## Systems evaluated on `test` (and `control-test`)

All systems use the uniform guide (no learned guidance) and a budget of 20,000 candidate programs per task, the same as in stage 0a.

- **S0:** base instructions only.
- **S1:** base instructions plus the learned library.
- **S0+planted:** base instructions plus the planted library. This is a reference ceiling only.

## Learner (stage 0b, S1)

A wake–sleep loop:
- **Wake:** uniform search with the current library over the training tasks.
- **Sleep:** candidate entries are recurring, stack-balanced instruction fragments of the solved programs, ranked by a compression score.
- **Acceptance:** candidates are accepted only if they improve the solve rate on `val`. This is the controlled-improvement rule.

Its hyperparameters (rounds, budgets, batch size, fragment lengths) may be tuned on `train` and `val` only. They are frozen in a commit before the single `test` run. The learner is run with **3 learning seeds**, which change search tie-breaking and therefore which solutions it finds.

## Pre-registered criteria

- **P1 (primary).** The mean over the 3 seeds of S1's solve rate on `test` is **at least 53%**, halfway between S0 (20%) and S0+planted (85%) as measured in stage 0a. On the control stream, the mean of S1's solve rate on `control-test` minus S0's is **at most 5 percentage points**.
- **P2.** Consider the planted entries that appear at the top level of at least 5% of `train` targets. An entry counts as recovered if some learned entry behaves identically to it on a fixed probe set of people, places and items. P2 passes if the mean over the 3 seeds of the recovered fraction is **at least 50%**.
- **P3-lite.** S1's median search operations per `test` task are lower than S0's.

"Solved" means the search found a program that fits every demonstration. Correctness on held-out queries (iid, size, topology) is reported alongside for every system but is not a pass criterion, because stage 0a showed it is capped by task ambiguity.

## Also reported, without thresholds

- Library size per round.
- Reuse rate: the share of solved `test` tasks whose program calls a learned entry.
- Recovered entries by name.
- Total learning cost (wake, validation and sleep operations).
- The per-task saving on `test`.
- The break-even number of test tasks.
- Per-seed results.

A failed criterion is reported as failed. The hidden split is not re-run after seeing its results.
