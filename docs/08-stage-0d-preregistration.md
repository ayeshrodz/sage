# Stage 0d pre-registration: reuse on recurring tasks

**Registered:** 2026-09-25, before any stage 0d code existed and before any stage 0d stream was generated.  
**Agreed by:** the project author chose stage 0d in conversation on 2026-09-25. The criteria and thresholds below were set by the reviewer, with the reasoning given, and the author may revise them before the run.

## Question

The objective says the system should, once it has found a reliable solution to a recurring class of problems, "preserve the transferable procedure and use it cheaply on new instances". Stage 0d tests exactly that. When task *types* recur as fresh instances (new worlds and query entities, same hidden procedure), does a memory of verified programs:

- make recurring types much cheaper,
- keep answers as accurate as before,
- cost almost nothing when nothing recurs, and
- make the whole stream substantially cheaper per correct answer?

This is hypothesis H1 (amortization) from `01-independent-analysis.md`.

## Streams

Generated once, after the code is frozen, from the planted task generator used since 0a (standard 2–3-entry tasks, the same acceptance filters).

- **Type:** a hidden target program.
- **Instance:** a fresh draw of a type: 4 demonstrations (3 informative, 1 random query entity) on new worlds, plus 5 held-out iid queries. Each instance passes the same degeneracy and ≤3-instruction checks as every earlier task; demonstrations are redrawn if they fail.
- **`0d-zipf`:** 200 types, 1,000 instances. Type k (in a random ranking) occurs with probability ∝ 1/k (Zipf exponent 1.0); the order is random.
- **`0d-norecur`:** 300 instances, each of a distinct type, so nothing recurs.

## Systems

- **S0:** base instructions, uniform search, 20,000-candidate budget (as in 0a–0c).
- **S3:** the frozen stage 0c *primary* system, seeds 0, 1 and 2: its learned library and guide, and its own 5,000-candidate cap. It has no memory between tasks.
- **R0 and R3:** S0 and S3 with a **reuse memory**. The memory:
  - **Stores:** every program the system finds that fits a task's demonstrations, together with a *trust* count (the number of instances it has fit).
  - **Looks up:** a new task is keyed by the entity types appearing in its demonstrated answers. That is cheap, visible to the solver, and the same for every instance of a type. Stored programs with that key are verified on the new demonstrations in order of trust, then most recent use, stopping at the first program that fits all of them. Verification checks the first demonstration first and stops at the first mismatch. At most **50** programs are verified per task.
  - **Answers:** on a hit, it answers with the stored program and raises its trust. On a miss, it runs the underlying search exactly as S0 or S3 would, with the same tie-breaking, and stores the result if one is found. Identical programs are merged.

  Every memory starts empty at the beginning of each stream. All of its work (key, verifications, bookkeeping) is counted in element operations. These settings are fixed now and not tuned.

Because a miss runs exactly the same search as the memoryless system on the same instance, R and S are compared on identical instances with identical fallbacks. The only difference is the memory.

## Pre-registered criteria

Each value is computed per seed, then averaged over the 3 seeds.

- **P1d, reuse is cheap.** Take the `0d-zipf` instances whose type R3 has already solved on an earlier instance (the evaluator knows the types; the system does not). On those, S3's mean work per task divided by R3's is **at least 10×**.
- **P2d, accuracy holds.** On `0d-zipf`, R3's iid-correct rate is **no more than 3 points below** S3's.
- **P3d, cheap when nothing recurs.** On `0d-norecur`, R3's total work is **at most 1.05×** S3's.
- **P4d, the whole stream gets cheaper.** On `0d-zipf`, S3's work per correct answer divided by R3's is **at least 2×**. This counts every task, including those neither system can solve.

### Reasoning for the thresholds

- **P1d:** a hit should cost one short verification (hundreds to thousands of operations) where a search costs hundreds of thousands. 10× is "an order of magnitude", the least that would make reuse an important mechanism.
- **P2d:** the same 3-point margin for "no worse" that the original plan proposed.
- **P3d:** recognition must be almost free when it never pays; 5% is a strict bound.
- **P4d:** set lower than P1d on purpose. Types the system cannot solve at all get searched again every time they recur, and memory cannot help with those (stage 0c solved about 62% of types). Halving the cost of the whole stream is still a meaningful claim.

## Also reported, without thresholds

- The same four measures for **R0 against S0**: reuse without any learned library.
- **Learning included:** R3's work per correct answer on `0d-zipf` with the stage 0c learning cost of that seed added, compared with S0's, and the break-even stream length. This is the P3′ economics of 0c, revisited in a recurring setting.
- Mean work per task in windows of 100 instances (the learning curve), memory size, hits, and lookup work as memory grows.
- **Hit precision:** the share of hits that are correct on held-out queries, split by the trust of the program used.

## Reporting

- Pass or fail as registered, per seed and on average.
- Explicitly labelled exploratory analyses.

The streams are generated and evaluated once.
