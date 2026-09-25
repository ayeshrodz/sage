# Stage 0b results: learning the library

**Date:** 2026-09-25 · **Code:** frozen at `7900cab`; libraries learned and test evaluated at `bb47197`, whose `src/` and `experiments/` are identical to `7900cab`. **Pre-registration:** [`04-stage-0b-preregistration.md`](04-stage-0b-preregistration.md), including amendment 1 and the frozen configuration. **Report:** [`reports/stage0b.md`](../reports/stage0b.md), with per-task rows in `reports/stage0b.json` and the learned libraries, histories and logs in `reports/stage0b/`.

The hidden `test` splits were generated and evaluated exactly once.

## Verdict on the pre-registered criteria

| Criterion | Result | Value | Threshold |
|---|---|---:|---:|
| **P1** planted: mean S1 solve rate on hidden `test` | **FAIL** | 32% | ≥ 53% |
| **P1** control: S1 − S0 on `control-test` | **FAIL** | +9 points | ≤ +5 points |
| **P2** common planted entries recovered (mean of 3 seeds) | **PASS** | 52% | ≥ 50% |
| **P3-lite** S1 median search ops below S0's | **FAIL** | all 3 seeds higher | all lower |

## What happened

| Planted stream (hidden test, 100 tasks) | Solved | Correct (iid / size / topology) |
|---|---:|---:|
| S0: base instructions only | 11% | 5% / 2% / 3% |
| **S1: learned library** (seeds 0 / 1 / 2) | **37% / 33% / 26%** | 25% / 21% / 15% (iid) |
| S0+planted: the true library, as a reference | 77% | 66% / 61% / 63% |

The hidden test turned out harder than stage 0a's dev set: S0 solved 11% here against 20% there, and S0+planted 77% against 85%. The 53% bar was set from the 0a numbers. Measured against this test's own floor and ceiling, S1 covers about a third of the gap: (32 − 11) / (77 − 11). It fails either way.

## Findings

1. **The system did learn real procedures from scratch.** In all three seeds, the first useful discovery was *siblings*, exactly as planted: `push out.parent in.parent minus_pop`. Entries built on top of it followed: *aunts/uncles* (`out.parent` + siblings), *nieces/nephews* (siblings + `in.parent`), a *cousins*-like entry, and *housemates*. Four or five of the nine common planted entries were recovered per seed (P2 passes at 52%). This is the *unfamiliar task → effortful solution → transferable procedure* step of your progression, observed rather than assumed.
2. **The learned library is genuinely reused.** 100% of S1's solved test tasks call learned entries. This is unlike the LLM library learners in "Library learning doesn't", which almost never reused theirs. S1 solves 18–29 test tasks that S0 cannot, and loses only 3.
3. **Learning stalled at about 16 entries: the utility problem, observed in a learner.** The acceptance gate only admits entries that improve validation under *unguided* search, and every entry widens every search. So the library stopped growing before it learned *grandparents*, *friends of friends*, *neighbours* or *local friends*. The gate protected the system from the utility problem, and that protection is exactly what capped it. Stage 0a already showed that a library this size needs a guide, and 0b shows that a *learner* needs one too.
4. **Much of the library is redundant variants of one idea.** The libraries contain siblings with `drop_x` instead of `minus_pop`, siblings with a colour filter baked in the middle, siblings with a `clos.parent` prefix, and so on. The learner mines fragments but never *refactors*: it does not express new entries in terms of existing ones, and it does not treat filters as arguments. Each variant costs breadth.
5. **The control was not structureless, and generic idioms help.** The no-structure stream still gained +9 points, against +21 on the planted stream. Random typed paths reuse a small vocabulary of step pairs (`clos.parent rclos.parent`, `out.owns in.owns`), and the learner exploited them; the dev runs had already hinted at this. Roughly 40% of the capability gain is generic and the rest is family-specific. For SAGE this is two-sided. It is a weakness of this control design. It is also a real phenomenon: some procedures are worth keeping even when tasks are unrelated.
6. **Capability rose; efficiency barely moved. This is exploratory and was not pre-registered.**

   | Work per correct answer (iid) | S0 | S1 seed 0 / 1 / 2 | S0+planted |
   |---|---:|---:|---:|
   | Planted stream | 4.8M ops | 2.8M / 3.0M / 4.4M | 0.52M |
   | Control stream | 2.4M ops | 4.2M / 5.5M / 4.9M | — |

   - On the planted stream, the learned library is up to 1.7× cheaper per correct answer. The true library is 9× cheaper, so most of the possible saving is still missing.
   - Learning cost 550–665M operations per seed (5.5–6.3 CPU minutes). It pays back after about 300 correct answers for seeds 0 and 1, and about 1,500 for seed 2.
   - On the control stream, the library buys extra answers at a *higher* cost per answer. So the efficiency gain is specific to the task family, even though part of the capability gain is not.
7. **P3-lite was a badly chosen metric.** Most test tasks hit the 20,000-candidate budget in every system. The median therefore compares the cost of *failing*, and learned macros make each failed candidate more expensive. Cost per correct answer (finding 6) is the right economic measure. Future criteria will use it.
8. **Correctness remains capped by ambiguity** (as in 0a). Solved exceeds correct by 6–12 points on the planted stream, and by 23–31 points on the control stream, whose random macros produce more under-determined tasks.

## Caveats

- Recovery is judged on single-entity probe inputs. On those, `… drop_x` behaves like `push … minus_pop`, so a `drop_x` variant counts as recovering the planted entry even though the two differ on multi-entity sets. Seed 2's *siblings* is such a variant.
- 3 seeds, 100 test tasks per stream: expect about ±5–9 points on solve rates.
- The curriculum (amendment 1) and `trim_filters` were decided on `train`/`val` before the test existed. Both are documented in the pre-registration.

## What this means for SAGE

The core mechanism exists and can be measured: a small system discovered, verified and reused procedures, and they transferred to larger and differently shaped worlds. But without a learned guide, **learning cannot outgrow the utility problem**. The library stops at the size that unguided search can afford, it fills with near-duplicates, and the saving per answer stays small. Stages 0a and 0b now point at the same missing piece.

## Proposed next step: stage 0c, the learned guide plus a refactoring learner

1. **Guide.** A small model maps a task's demonstrations to a probability for each token. Its input features are histograms of the labelled paths linking *x* to its answers, and it is a small MLP (hundreds of thousands of parameters, trainable on CPU in minutes). Training data comes from solved training tasks and from "dreams": programs sampled from the current library and run on fresh worlds. Search uses the guide's probabilities in place of the uniform prior.
2. **Guided wake–sleep.** Library acceptance is judged under *guided* search, so entries no longer pay the full breadth cost and the library can keep growing.
3. **Refactoring learner.**
   - Rewrite solved programs in terms of existing entries before mining, so that new entries are built from old ones.
   - Merge behaviourally identical variants.
   - Treat filters as arguments: one `siblings` plus a filter, instead of four coloured siblings.
4. **Measurement fixes.**
   - A *fresh* hidden test split (the 0b test has now been seen).
   - Cost per correct answer as the primary cost metric.
   - A redesigned control that matches the planted stream's generic idiom statistics (for example, the same 2-step fragment frequencies) but has no recurring multi-step entries, so it measures the family-specific benefit directly.

**Draft criteria for your approval** (the numbers would be registered before the new test split exists):
- **P1′:** guided S3 solves at least 53% of the fresh planted test.
- **P3′:** S3's work per correct answer is at least 5× lower than S0's, with learning cost reported and amortized.
- **P-guide:** the guide ranks the target's tokens in its top 10% on average on held-out tasks. This is the "discrimination must keep pace with library size" requirement from the pilot, made testable.
- **Control:** S3's gain on the redesigned control is at most 5 points.
