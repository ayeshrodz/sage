# Stage 0c results: a learned guide and a refactoring learner

**Date:** 2026-09-25 · **Code:** frozen at `7b8a29f` (learning runs and the single hidden-test evaluation both ran there). **Pre-registration:** [`06-stage-0c-preregistration.md`](06-stage-0c-preregistration.md), including amendment 1. **Report:** [`reports/stage0c.md`](../reports/stage0c.md); per-task rows in `reports/stage0c.json`; learned libraries, guides, ledgers and logs in `reports/stage0c/`.

The hidden splits `0c-test` and `0c-mismatch-test` were generated and evaluated once.

## Verdict on the pre-registered criteria

The criteria are judged on the primary configuration; the secondary one is reported alongside, as registered.

| Criterion | Primary | Secondary | Threshold |
|---|---|---|---|
| **P1′** mean solve rate on `0c-test` | **62% PASS** | 41% fail | ≥ 53% |
| **P3′** S0's work per correct answer ÷ S3's, learning amortized over 1,000 tasks | **0.3× FAIL** | 0.6× fail | ≥ 5× |
| **P-guide** teacher-forced percentile of the needed tokens | **20% FAIL** | 22% fail | ≤ 10% |
| **Control** gain on the mismatched family | **+3 points PASS** | −3 points pass | ≤ +5 points |

## What happened

| System, on `0c-test` (100 hidden tasks) | Solved | Correct (iid / size / topology) | Work per correct answer |
|---|---:|---:|---:|
| S0: base instructions only | 21% | 12% / 7% / 6% | 1.8M |
| 0b libraries, plain search (seeds 0 / 1 / 2) | 42% / 37% / 28% | — | — |
| **0c libraries, plain search** (no guide; primary seeds) | **65% / 52% / 57%** | 45% / 35% / 41% | 1.8M / 1.7M / 2.7M |
| **S3 primary: 0c library + learned guide** | **65% / 50% / 70%** | 46% / 34% / 49% | 2.4M / 4.2M / 2.6M |
| S3 secondary | 50% / 35% / 37% | 39% / 18% / 22% | 0.8M / 1.9M / 1.6M |
| S0+planted: the true library, plain search | 83% | 67% / 64% / 63% | 0.43M |

On the mismatched family (control library B), the A-trained S3 solves 20–25% against S0's 20%.

## Findings

1. **Capability: the loop works, and P1′ passes.** Starting from 28 instructions and 200 training tasks, the system learns libraries of 12–26 entries. It recovers 4–8 of the 13 planted skills per seed, in their exact set-safe forms (*siblings* = `push out.parent in.parent minus_pop`), and builds hierarchy (*aunts/uncles* and *cousins* are built from *siblings*). It then solves 62% of unseen compositional tasks, where S0 solves 21% and the true library 83%. That covers about two-thirds of the gap between the two.
2. **The refactoring learner builds better libraries.** This comparison is clean. Under *identical* plain search on the same fresh test, 0c's libraries solve 58% on average and 0b's solve 36%. Rewriting solutions in terms of existing entries, requiring entries to be set-safe, treating filters as arguments, and learning under guided search together made the libraries better.
3. **The knowledge is family-specific.** Evaluated on a different task family (library B) with the same generator shape, the A-trained system gains only +3 points. This redesigned control does what 0b's could not: the benefit comes from what the system learned about its own family, not from generic tricks.
4. **At test time, the guide doesn't pay for itself.** With the same library, guided search at a 5,000-candidate cap solves about as many tasks as plain search at 20,000 (62% against 58%). It spends *more* work doing so: 1.1–1.4M against 0.6–1.1M per task. The guide ranks the needed skill in the top fifth (20%), not the top tenth. And every state it evaluates costs about 2–3k operations of perception and scoring, against roughly 50–100 to simply execute a candidate. This is the pilot's routing-cost lesson again, now inside search.
5. **The economics fail as registered, and by a wide margin.**
   - **Learning cost.** Learning costs 1.0–1.6B operations per primary seed, about 45% of it wake searches and 35% validation searches. Amortized over 1,000 tasks, that makes S3 3× *more* expensive per correct answer than S0. Even ignoring learning, it is 0.6×.
   - **Secondary configuration.** The cheaper secondary configuration does better on cost (1.3× operationally; seed 0 pays back its learning after about 790 tasks) but solves fewer tasks.
6. **The 5× bar was beyond reach on this test even with the true library.** On `0c-test`, S0 was a stronger baseline than on 0b's test (12% correct; 1.8M work per correct, against 4.8M before). Under plain search, even the true planted library is only 4.3× cheaper per correct answer. With plain search, a good library multiplies *capability* much more than it cuts *cost per answer*. Cost per answer only falls with guidance that is both sharp and cheap, which is exactly the requirement the pilot set out.
7. **Learning is fragile across seeds.** Libraries range from 12 to 26 entries and solve rates from 50% to 70%, depending on which tasks happen to be solved early.

## What changed during development (from amendment 1)

The registered task-level guide could not see compositions: it ranked needed tokens around the 33rd percentile and solved 6–12 of 40 val tasks. A state-conditioned guide, which re-reads the search state after every step, reached 28 of 40, but made learning cost 1.6B operations. Deferred evaluation, lower budgets and caching brought that down to 0.3–1.0B, at a cost in capability. All of these steps, and the choice between the two configurations, were fixed before the hidden test existed. The val projections recorded then were for P3′ and P-guide to fail and for the primary configuration to pass P1′, and the test confirmed all of them.

## What this means for SAGE

- **The capability half of the thesis holds at this small scale.** A compact system turned effortful solutions into transferable, family-specific procedures that solve most unseen tasks in the family.
- **The efficiency half does not yet hold.** The component meant to keep a growing library cheap, the router or guide, costs more per decision than it saves, and learning costs about a thousand tasks' worth of work to pay back.

That locates the next problem precisely: **routing must become both sharper and far cheaper per decision**, close to the cost of executing a single candidate. In the terms of your progression, that is the *compilation* step: turning slow deliberation into cheap reflexes. So far we have compiled procedures (the library), but not decisions (the routing).

## Options for the next step

1. **Stage 0d: reuse on recurring tasks.** Most real task streams repeat themselves. Replay a Zipf-skewed stream in which task *types* recur. Keep a cache of verified programs keyed by a cheap task signature, so a hit costs one verification on the demonstrations instead of a search. This tests the "familiar classes of problems with less work" part of your objective directly, and it's where compiled procedures should give large, measurable savings. It is cheap to run. **This is my recommendation.**
2. **Cheap routing.** Replace per-state scoring with decisions made once per task, for example retrieving whole candidate programs from similar past tasks and verifying them first. Or distil the policy into a small lookup table (a "reflex"). The goal is a guide whose total cost per task is below about 50k operations.
3. **Cheaper learning.** Most of the learning cost is searches on training tasks that fail. Adaptive budgets, and learning from partial solutions, could cut it by several times.
4. **Where a small LLM fits.** These numbers matter for your small-model idea. A single call to even a tiny language model costs orders of magnitude more work than this whole search, so it belongs *offline*: during sleep, proposing or refactoring library entries. Its cost would then be amortized, and it would stay out of the per-task loop.
