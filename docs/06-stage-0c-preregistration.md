# Stage 0c pre-registration: a learned guide and a refactoring learner

**Registered:** 2026-09-25, before any stage 0c code existed and before any stage 0c split was generated.  
**Agreed by:** the project author approved the four criteria in conversation on 2026-09-25. The amortization horizon in P3′ and the exact form of the control are fixed here by the reviewer, for the reasons given below.

## Question

Stages 0a and 0b showed that a library only pays off with a guide that picks which entries to try. Can a system that learns *both* its library and its guide from a stream of tasks:

- solve most unseen tasks,
- spend at least 5× less work per correct answer than search without a library, counting what learning cost, and
- rank the skills a task needs near the top?

## Splits

All splits use 4 demonstrations and 5 held-out queries per stratum (iid, size, topology), and all names are new to stage 0c.

| Split | Tasks | Content | Who sees what |
|---|---:|---|---|
| `0c-train` | 200 | Planted library, curriculum (50% single-entry tasks, as in 0b amendment 1) | The learner sees the demonstrations. |
| `0c-val` | 40 | Planted library, standard 2–3-entry tasks | The learner sees the demonstrations and uses them to accept or reject changes; never the queries. |
| `0c-test` | 100 | Planted library, standard | **Hidden.** Generated and evaluated once, after the configuration is frozen. |
| `0c-mismatch-test` | 100 | Control library **B**, standard (see *Control*) | **Hidden.** Generated and evaluated once, at the same time. |

## Systems evaluated

Every system gets a budget of 20,000 candidate programs per task.

- **S0:** base instructions, uniform order (as in 0a and 0b).
- **S3:** base instructions plus the learned library, searched in the order given by the learned guide. Learned with 3 seeds (0, 1, 2).
- **S0+planted:** base plus the true planted library, uniform order. A reference ceiling only.
- **Ablations**, reported without thresholds:
  - S3's library searched without its guide;
  - the three 0b libraries on the fresh test.

## The learner (S3)

1. **Perception.** Each task is summarized by features of its demonstrations: for labelled relation paths of up to 3 steps from *x*, how much of the demonstrated answer each path reaches (recall) and how much of what it reaches is in the answer (precision). The features also include the entity types and attributes of the answers. These features are generic to relational tasks; nothing in them refers to the planted library.
2. **Guide.** A small linear softmax model maps a task's features to a probability for each token (base instruction or library entry). Search orders candidates by these probabilities, mixed with a small uniform floor so that no token becomes unreachable.
3. **Training data for the guide.**
   - Solved training tasks, with their programs rewritten in terms of the current library.
   - "Dreams": programs sampled from the current library and run on worlds taken from the training demonstrations.
4. **Guided wake–sleep with refactoring.** Each round:
   1. Search the unsolved training tasks with the guide.
   2. Rewrite every solution in terms of the current library, so new entries are built from old ones.
   3. Mine recurring fragments as candidate entries, excluding filters (filters are arguments, added by composition, not part of entries).
   4. Merge candidates that behave identically.
   5. Retrain the guide.
   6. Accept the batch only if guided validation improves.
   7. At the end, prune entries that are never used, if validation does not get worse.
5. **Freezing.** Hyperparameters may be tuned on `0c-train`/`0c-val` only. They are frozen in a commit before the hidden splits are generated.

## Cost accounting

**Units.** Machine work is counted in element operations (entities and edges touched), as before. Guide arithmetic is counted in multiply-adds and added one-for-one. That is an approximation, stated here.

**Test-time work per task, w3:** feature extraction + guide scoring + search.

**Learning cost, L:** everything done while learning:
- wake searches;
- feature extraction for training, validation and dream tasks;
- running dream programs;
- guide training;
- validation searches;
- pruning checks.

## Pre-registered criteria

- **P1′.** The mean over the 3 seeds of S3's solve rate on `0c-test` is **at least 53%**. "Solved" means a program fitting every demonstration was found within budget, as in 0b.
- **P3′.** Let W0 be S0's work per correct answer and W3 be S3's work per correct answer with learning included; P3′ passes if **W0 / W3 ≥ 5**. The quantities are:
  - W0 = S0's total work on `0c-test` ÷ S0's number of iid-correct answers.
  - W3(seed) = (L + N · w3) ÷ (N · c3), where w3 is S3's mean work per test task, c3 is its iid-correct rate, and **N = 1,000** future tasks.
  - W3 is the mean of W3(seed) over the seeds.
  - If S0 has no correct answers at all, the ratio is reported as unbounded and the criterion is judged on work per *solved* task instead.
- **P-guide.** Averaged over the 3 seeds and all `0c-test` tasks, the tokens of a task's reference program sit at a mean percentile rank of **at most 10%** in the guide's ordering, where 0% is the top.
  - **Reference program:** the planted target rewritten over S3's tokens. Each planted entry is replaced by the first learned entry that behaves identically on the P2 probe set (the 0b recovery test). Planted entries with no such learned entry are expanded into their parts, recursively, down to base instructions.
  - **Percentile rank:** a token's rank ÷ the number of tokens, with ties averaged.
- **Control.** The mean over the 3 seeds of S3's solve rate on `0c-mismatch-test`, minus S0's solve rate there, is **at most 5 points**.

## Why N = 1,000 and why this control

**N = 1,000.** "With learning cost included" needs a stated number of future uses, or it has no meaning. 1,000 is 5× the training stream and 10× the test set. A library learned from 200 tasks should serve at least that many. The break-even point and the ratio as a function of N are reported alongside, so any other horizon can be read off.

**Control.** The 0b control reused a small vocabulary of short typed paths, so a library learned on it helped it (+9 points). A stream matched on 2-step fragment frequencies was considered and rejected, because a chain fitted to the planted library's bigrams regenerates the planted entries themselves (siblings is its most likely 4-step sequence). Instead, the control asks whether S3's benefit is specific to the family it learned:
- **Control library B:** a second hierarchical library of 13 entries.
  - It is generated by a fixed random process that shares A's shape: the same instruction vocabulary, typed paths and `push … set-op` idioms, similar lengths, a hierarchy, and Zipf-skewed use.
  - It is required to behave differently from every planted entry and every base instruction.
- **Tasks and systems:** B's tasks are built by the same task generator. The *A-trained* S3, with its library and guide, and S0 are both evaluated on them.
- **Reading:** a gain of at most 5 points means S3's benefit comes from what it learned about its own task family, not from generic effects.

## Reporting

- Pass or fail as registered, per seed and on average.
- The ablations.
- Library sizes, contents and recovery of planted entries (the 0b P2 measure).
- Learning cost broken down by component.
- The break-even N.
- Clearly labelled exploratory analyses.

The hidden splits are generated and evaluated once.
