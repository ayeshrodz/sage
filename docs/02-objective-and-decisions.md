# SAGE: objective and decision log

## Objective (the author's statement, 2026-09-25)

> We started with a question about the relationship between intelligence and physical resources. Today's most capable AI systems are usually built by training and running very large networks. They can be useful, but acquiring more knowledge and capability often demands large amounts of model storage, active memory, computation and energy. We wanted to investigate a different possibility: could a system keep a small, reusable thinking mechanism while growing what it knows and can do in mostly inactive memory and executable skills?
>
> The ambition is a locally runnable AI that can learn unfamiliar things, reason when needed, remember what it learns, and gradually solve familiar classes of problems with less work. A small CPU machine was the practical starting point; the example long-term target discussed was around 1 TB of possible cold knowledge storage with routine active memory comfortably under 16 GB. That target does not mean the first experiment will use 1 TB or prove general intelligence. It expresses the separation we are trying to investigate: stored capability may grow substantially without the active thinking machinery growing at the same rate.
>
> **Core objective:** Discover and test an architecture in which a compact, reusable cognitive core acquires broadly reusable capabilities through memory and executable procedures, while the active computation, memory traffic, latency and energy needed per task remain low.
>
> The system should spend effort on a new problem when it genuinely needs to reason. Once it has found a reliable solution to a recurring class of problems, it should preserve the transferable procedure and use it cheaply on new instances. Over time, it may learn better representations, operations and routing rules. Improvement must be judged by problems it has not already seen and by measured physical cost, not by whether its explanations sound intelligent.
>
> The SAGE progression:
> - **Novelty:** represent a problem as a compact state and work through it using reusable operations.
> - **Learning:** retain useful experiences, infer general procedures and check whether they transfer.
> - **Compilation:** turn repeatedly successful, expensive reasoning into a cheaper procedure or rule.
> - **Adaptation:** choose the cheapest reliable way to solve each incoming task, while falling back to deeper computation when necessary.
> - **Controlled improvement:** evaluate candidate changes to memory, procedures, representations and eventually architecture on independent tests before adopting them.
>
> This is a research programme, not an assertion that a small system can already match a frontier model. Language fluency, a large archive and a good benchmark score are not the main target by themselves. We want new capability per unit of active physical work, with evidence that the capability transfers beyond memorized examples. […]
>
> **Why the first experiment is deliberately small.** Experiment 0 isolates one possible mechanism: a compact model discovers or selects reusable procedures for structured tasks, and verified compilation lets it execute recurring tasks more cheaply. […] The key progression we want to measure is *unfamiliar task → effortful correct solution → transferable procedure → lower measured cost on future unseen instances*, while counting training, search, retrieval and compilation costs when assessing overall efficiency.

**Long-run motivation (author, 2026-09-25):** bring frontier-level capability to consumer devices by redesigning how AI models are built. The aim is to move from GPU-hungry, very large models towards compact, CPU-runnable systems organized more like a brain: a small active core with a large, mostly inactive store of knowledge and skills.

## How experiment 0 maps onto the progression

| Progression step | Where experiment 0 tests it |
|---|---|
| Novelty | S0: search over the base instruction set (§5.5 of `01-independent-analysis.md`) |
| Learning | S1: library learning from solved tasks, with transfer checked on held-out worlds (stage 0b) |
| Compilation | Library entries (macros) and the learned guide (stages 0b, 0c) |
| Adaptation | The cheap-first cascade with fallback, S3+R (stage 0d) |
| Controlled improvement | Evaluator-owned held-out queries and pre-registered gates at every stage |

The objective's key progression (unfamiliar task → effortful solution → transferable procedure → lower cost on unseen instances) is exactly the stage 0b + 0c measurement.

## Decisions

| Date | Question | Decision | Consequence |
|---|---|---|---|
| 2026-09-25 | Reframe experiment 0? | **Yes.** Library economics (H1–H3) first; the neural interpreter (H4) becomes a later, separate track. | Programs run on a symbolic interpreter; learning goes into proposing and routing. |
| 2026-09-25 | Domain | **Typed relational worlds.** | The base DSL is a small instruction set over entity sets (`src/sage/machine.py`). |
| 2026-09-25 | Hardware and energy | **Postponed.** Work runs in a cloud container for now; the i5 comes back later. | Deterministic operation counts are the primary cost; CPU time is secondary; energy is deferred until we have local hardware with readable counters. |
| 2026-09-25 | Scope | **Personal exploration**, with the long-run aim above. | Rigor stays high (controls, pre-registration), but external baselines such as Popper and DreamCoder are optional for now. |
| 2026-09-25 | LLMs | **Allowed**, starting with a *small* model as a helper. | Enters after stage 0c as a costed proposal distribution: it suggests programs or library entries, the verifier decides, and its inference cost is counted in amortized cost. It never sees hidden queries. |
| 2026-09-25 | Stage 0b outcome | P1 **failed** (32% vs 53%; control +9 vs +5), P2 **passed** (52%), P3-lite failed (a badly chosen metric). See `05-stage-0b-results.md`. | Results stand as registered. Stage 0c (learned guide, refactoring learner, fresh hidden test) is proposed and awaits approval. |
| 2026-09-25 | Stage 0c criteria | **Agreed:** P1′ ≥53% solved, P3′ ≥5× less work per correct answer with learning included, P-guide top 10%, control gain ≤5 points. The reviewer fixed the amortization horizon (N = 1,000 future tasks) and the control form (a mismatched task family) in `06-stage-0c-preregistration.md`. | Registered before any 0c code or split exists. numpy becomes a dependency for the guide. |
| 2026-09-25 | Stage 0c amendment | State-conditioned guide, deferred evaluation, Minton's acceptance rule, stopping caps, teacher-forced P-guide; primary and secondary configurations frozen, with val projections recorded. See `06-stage-0c-preregistration.md`. | Recorded before the hidden splits exist. |
| 2026-09-25 | Stage 0c outcome | Primary: P1′ **passed** (62%), control **passed** (+3), P3′ **failed** (0.3×), P-guide **failed** (20%). See `07-stage-0c-results.md`. | Results stand as registered. Next-step options are proposed; the recommendation is stage 0d (reuse on recurring tasks). |
| 2026-09-25 | Next stage | **Stage 0d: reuse on recurring tasks** (author's choice). The reviewer set the criteria and thresholds (P1d ≥10× cheaper on solved recurring types, P2d accuracy within 3 points, P3d ≤5% overhead without recurrence, P4d ≥2× cheaper per correct answer over the stream) in `08-stage-0d-preregistration.md`. | Registered before any 0d code or stream exists; the author may revise the thresholds before the run. |
| 2026-09-25 | Stage 0b pass marks | **P1 and P2 agreed** (see `04-stage-0b-preregistration.md`). | Registered before the hidden test split exists; the hidden split is run once. |

### Note on the small-model helper

A small local model (for example a 0.5–3B-parameter model running on CPU) can help in three measurable ways:

1. **Proposer:** suggest candidate programs or library entries for tasks that search fails on.
2. **Dreamer:** write plausible new tasks for training the guide.
3. **Namer:** document learned library entries so they can be inspected (as in LILO).

Each role has a clean test: does it lower total cost per correct answer on held-out tasks *including its own inference cost*? If it doesn't, it is removed. Its outputs are only ever candidates; the verifier and the held-out evaluator stay independent.
