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

## Amendment 1 (2026-09-25, before `0c-test` and `0c-mismatch-test` were generated)

All development used `0c-train` and `0c-val` only, with seed 0.

### What development showed

| Development step | Val solved | Learning work | Guide ranking on val* |
|---|---:|---:|---:|
| Task-level guide, as registered (features of the task seen from *x*, once) | 6–12 / 40 | 0.18–0.88B | 31–35% |
| + calibration: frequency prior, larger floor | 9 / 40 | 0.30B | 35% |
| + Minton's rule (accept a batch unless validation gets worse) | 12 / 40 | 0.31B | 33% |
| **State-conditioned guide** (a policy that looks at the current search state) | **28 / 40** | 1.62B | 18% |
| + deferred evaluation, cheaper learning (secondary configuration) | 18 / 40 at 2k | 0.32B | 17% |
| Richer learning with current code (primary configuration) | 24 / 40 at 5k | 1.02B | 24% |

\*Teacher-forced mean percentile rank of the reference program's tokens (the P-guide measure defined below). Evaluator-side only.

Two lessons came out of this. First, a task-level guide cannot see a composition of 2–3 skills from its features, while a guide that re-reads the state after every step can. Second, the per-state guide costs perception and scoring at every state it evaluates, and that cost eats most of what it saves. That is the pilot's routing-cost lesson, reappearing inside search.

### Changes, fixed from here on

1. **The guide is state-conditioned.**
   - It sees path features from the *current* set to the demonstrated answers. The start state looks 3 steps ahead; later states look 2 steps (primary) or 1 step (secondary).
   - It also gets one-step completion checks (filter, `drop_x`, set operation with the saved set), the stack depth and the last token.
   - It is trained by replaying solved programs and dreams step by step, with the model mixed with the overall token frequency (weight 0.3) and a uniform floor (0.05).
2. **Search** evaluates the policy lazily, deferring evaluation until a state is popped (as in Fast Downward), with a cap on policy calls per search. Later states reuse their parent's order.
3. **Acceptance** keeps a batch unless guided validation solves fewer tasks (Minton's rule). If a batch is rejected, its top half is tried. When nothing is accepted, a retrained guide is adopted if validation holds.
4. **Dreams** include the instruction set's own idioms (`push <path> <set op>`, `<path> drop_x`), and draw learned entries in proportion to their use.
5. **S3 stops at its own cap** within the registered 20,000-candidate ceiling: 5,000 candidates (primary) or 2,000 (secondary). On val, raising the cap from 5,000 to 20,000 solved no additional tasks.
6. **P-guide for a state-conditioned guide.** The reference program is replayed on each task's demonstrations. At each step, we take the percentile rank of the reference's next token given the state its prefix reaches (teacher forcing). Those ranks are averaged over steps, tasks and seeds, and the 10% threshold is unchanged. The rank of the first token at the start state is reported alongside.
7. **Two configurations are run on the hidden test.** Both are frozen in `experiments/stage0c.py`:
   - `primary`: wake budget 10,000; validation budget 5,000; cap 5,000; 300 policy calls; 2-step state perception.
   - `secondary`: wake budget 2,000; validation budget 2,000; cap 2,000; 200 policy calls; 1-step state perception; features must be seen ≥4 times.

   **Selection rule:** the configuration that passes the most criteria when estimated on val is the primary one, and the criteria are judged on it; the other is reported alongside. Estimated on val, the richer configuration passes P1′ (60%) and the lean one passes none, so the richer one is primary.

### Projections on val, recorded before the test

Against S0 on val (3 correct answers out of 40, 3.18M work per correct answer):

| Configuration | Operational ratio | Amortized ratio (N = 1,000) | Break-even | Guide ranking |
|---|---:|---:|---:|---:|
| primary | 1.5× | 0.8× | ~1,900 tasks | 24% |
| secondary | 3.9× | 2.0× | ~310 tasks | 17% |

**Both are expected to fail P3′ and P-guide.** P1′ is expected to pass only for the primary configuration. These projections are made on 40 validation tasks with one seed and are recorded here so the test can confirm or contradict them.

### Unchanged

The splits, the single generation and evaluation of the hidden splits, all thresholds, N = 1,000, the control design, and the 20,000-candidate ceiling for S0 and S0+planted.
