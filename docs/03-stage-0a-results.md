# Stage 0a results: the economics of a given library

**Date:** 2026-09-25 · **Code:** git `e20df17` · **Reports:** [`reports/stage0a.md`](../reports/stage0a.md) (natural tasks), [`reports/stage0a_wellposed.md`](../reports/stage0a_wellposed.md) (well-posed tasks); raw per-task rows and split manifests alongside.

**Gate verdict: passed.** Handing the search the planted library cuts the cost of solving these tasks by more than two orders of magnitude, so the tasks are deep enough to be worth learning a library for. Stage 0b (learning the library) is justified.

## What was built

| Piece | File | What it does |
|---|---|---|
| Worlds | `src/sage/worlds.py` | Typed relational worlds: people, places and items; `parent`, `friend`, `lives_in`, `inside`, `owns` and `near`; three regimes (training, 5–10× larger, different topology); random relabelling so ids carry no information. |
| Core | `src/sage/machine.py` | A 28-instruction set over entity sets with a 3-deep stack (`out.parent`, `clos.inside`, `only_color.red`, `push`, `minus_pop`, …). A library entry is a macro, a named instruction sequence. Every run counts element operations, meaning entities and edges touched. |
| Planted library | `src/sage/library.py` | 13 hidden entries built hierarchically (siblings → aunts_uncles → cousins; housemates → local_friends; …), used with Zipf-skewed frequency, plus random distractor macros. |
| Tasks and splits | `src/sage/tasks.py` | The solver sees only demonstrations. The evaluator keeps the target and held-out queries in three strata (iid, size, topology). Splits have hashed manifests. Tasks that a program of ≤3 base instructions already solves are rejected, so every task needs composition. |
| Search | `src/sage/search.py` | Best-first search with observational equivalence, lazy successors and the pilot's three simulated guides. |
| Tests | `tests/` | 20 `unittest` checks: closure and sibling semantics, macro = its parts, stack validity, renaming and edge-order invariance, family acyclicity, split determinism and disjointness, hidden fields absent from the solver's view. |

Everything is standard-library Python. The whole 0a grid (2 × 40 tasks × 15 conditions) runs in under two minutes on a 4-core cloud container.

## Main results (4 demonstrations, natural tasks, 40 tasks per row)

| Library | Guide | Solved | Correct: iid / size / topology | Median candidates | Median search ops | Routing ops | Median CPU |
|---|---|---:|---:|---:|---:|---:|---:|
| none | uniform | 20% | 5% / 8% / 8% | ≥20,000 | 232,621 | 0 | 170 ms |
| none | mass (sharp) | 40% | 28% / 22% / 22% | ≥20,000 | 264,400 | 896 | 181 ms |
| planted | uniform | 85% | 70% / 65% / 62% | 4,735 | 207,013 | 0 | 67 ms |
| planted | mass (sharp) | 100% | 90% / 90% / 92% | 18 | 1,214 | 1,312 | 0.4 ms |
| planted + 100 | uniform | 48% | 35% / 35% / 30% | ≥20,000 | 667,312 | 0 | 233 ms |
| planted + 1,000 | uniform | 12% | 2% / 0% / 0% | ≥20,000 | 1,028,626 | 0 | 328 ms |
| planted + 1,000 | margin (fixed) | 100% | 88% / 88% / 90% | 1,050 | 51,289 | 33,312 | 21 ms |
| planted + 1,000 | mass (sharp) | 100% | 90% / 90% / 92% | 17 | 1,257 | 33,312 | 1.3 ms |

"≥" marks medians censored at the 20,000-candidate budget, so the no-library costs are lower bounds.

## Findings

1. **The gate passes by a wide margin.** With the planted library and a sharp guide, every task is solved from about 18 candidate programs, about 2,500 element operations (1,200 for search plus 1,300 for routing) and 0.4 ms of CPU. Without the library, search solves 20–40% of tasks and spends at least 230,000 operations (170 ms) per task. That is a ≥90× reduction in total work (≥190× in search alone) and ≥400× in CPU time, and all three are lower bounds. This is the target of your progression: *effortful search → stored procedure → cheap solution*.
2. **Procedures transfer.** Once the right program is found, it is equally correct on worlds 5–10× larger and with different family, friend and place topologies (90% / 90% / 92%). Symbolic procedures extrapolate by construction; the open question is only whether the system finds them.
3. **The utility problem appears in the real domain, as the pilot predicted.** Unguided, 100 distractor entries cut the solve rate from 85% to 48%, and 1,000 cut it to 12%. The fixed-margin guide stays flat up to 141 entries and then needs 60× more candidates at 1,041, the same knee near e^4.6 ≈ 100 entries the pilot showed.
4. **Once search is cheap, routing is the cost.** At 1,041 entries, brute-force scoring (33,312 operations) is 96% of the total work for the sharp guide. Sublinear routing is a requirement for the large-store vision, not an optimization.
5. **A library needs a guide, and a guide needs a library.** A sharp guide with no library still solves only 40% (28% correct), because programs are too long. The library cuts depth, the guide cuts breadth, and neither substitutes for the other.
6. **New finding: ambiguity sets the correctness ceiling, not search.** Even with the right library and a perfect guide, 10% of answers are wrong at 4 demonstrations and 22% at 2. These are *Occam errors*: the search returns the shortest program that fits, and the demonstrations don't rule it out. For example, the target ends with `only_size.large`, but every demonstrated answer happened to be large.
   - When the generator acts as a teacher and rejects tasks where dropping one step of the target still fits the demonstrations (`--well-posed`), correctness rises to 95% at 4 demonstrations and 98% at 2. The random stream is shared between the two runs, so only the rejected tasks differ.
   - The lesson for SAGE's core: a cheap procedure is only as good as the evidence that picked it. The system needs to *notice* when several procedures fit and disagree, then either ask for another example or abstain. People do this naturally.

## Caveats

- The guides are simulated: they are told which tokens the target uses. Stage 0a measures what a guide must achieve; stage 0c tests whether a learned guide achieves it.
- 40 tasks per cell gives roughly ±8 percentage points of sampling error on rates. The large effects are far outside that; differences of a few points are not.
- This is the development set only. Nothing is learned in 0a, so there is nothing to leak; the hidden test split comes into use in 0b.
- Tasks that a ≤3-instruction program solves are rejected (11 of 76 draws at 4 demonstrations, 29 of 102 at 2). That rejection is deliberate, because the question is composition. The rejection counts are reported in each file.
- An "element operation" is a unit of work, not joules. Wall and CPU time are recorded alongside, and they track the operation counts here.

## Proposed next step: stage 0b, learning the library

**Question.** Starting from the base instructions only, can the system recover a useful library from a stream of tasks, and does that library make *unseen* tasks cheaper to solve, with every cost counted?

**Loop (wake–sleep).**
1. **Wake:** try to solve each training task by search with the current library, within a budget, and keep the solved programs.
2. **Sleep:** propose new entries from recurring, stack-balanced instruction fragments in the solved programs. Score each by how much it would shorten the corpus (a compression score, as in DreamCoder and Stitch). Then keep only entries that lower search cost on a validation slice (Minton's utility filter).
3. **Repeat.** Each round, tasks that were too deep before become reachable.

**Setup.** A training stream of about 200 tasks and a validation slice from dev, then the hidden test split (about 100 tasks, separate seed namespace) evaluated once at the end.

**Controls.**
- A no-structure stream whose targets are random base programs of matching length; a learned library should not help there.
- A shuffled stream order, with 3 seeds.
- Reporting the reuse rate, to check against the "library learning doesn't" failure.

**Measures.**
- Solve rate and cost on the hidden test, compared with S0 (the floor) and S0+planted (the ceiling).
- Library size and recovery of planted entries.
- Total wake and sleep operations, amortized over the test tasks, and the break-even number of uses.

**Proposed pre-registered thresholds (to agree before running the hidden test):**
- **P1:** with the learned library, uniform search solves at least halfway from S0 to S0+planted on the hidden test (≥ 53%, given 20% and 85% here). On the no-structure stream, it beats S0 by no more than 5 points.
- **P2:** the learned library contains, up to behaviour on probe worlds, at least half of the planted entries used by ≥5% of training tasks.
- **P3-lite:** the library's per-task routing cost stays below its search savings. The full P3 waits for the learned guide in 0c.

**A small add-on for finding 6.** Let search continue after the first fit to collect the few shortest consistent programs. Then measure whether disagreement among them on the query predicts errors. If it does, "abstain or ask for one more example" becomes a cheap, honest uncertainty signal for the core.

**Where the small LLM fits.** It comes after 0c, as planned in `02-objective-and-decisions.md`: first as a costed proposer for tasks search fails on, and as a namer of learned entries. Bringing it in during 0b would muddy the attribution of whatever the library learns.
