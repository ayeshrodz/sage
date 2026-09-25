# SAGE: research record and executable experiment plan

**Handoff version:** 2026-09-26 (Pacific/Auckland)  
**Status:** research hypothesis; no SAGE implementation or benchmark result is claimed here.  
**Purpose:** give a new Codex project enough context to implement, test, and revise the first experiment.  
**Provenance:** reconstructed from the conversation excerpt available in this handoff and the cited links. Earlier turns that are absent from the excerpt cannot be reproduced verbatim. Links below include those visible in the conversation; the list cannot honestly be guaranteed to contain every link from missing turns.

## 1. Executive summary

SAGE is a proposed resource-efficient learning and reasoning system. Its central question is whether reusable computation can stay small while stored memories, procedures and capabilities grow. It aims to solve unfamiliar structured tasks with an adaptive solver, save successful solutions as executable programs, and execute recurring tasks through cheaper paths. The proposed first experiment runs on an existing i5 machine with roughly 32 GB RAM; it needs neither a language model nor a new GPU.

**Research hypothesis, not established result:** after repeated exposure to related task families, a learned-program system can preserve out-of-distribution (OOD) accuracy while reducing measured compute per correct solution relative to its own uncompiled mode and fair baselines. The stronger claim that this produces general intelligence, a new scaling law, or monotonic gains is untested.

**Current decision:** build a narrow, controlled program-discovery and compilation experiment first. Start with symbolic graph and relational tasks with an exact oracle. Compare an exact algorithmic baseline, a parameter-matched neural baseline, a reusable recurrent baseline and a learned-program candidate. Add associative memory, equilibrium dynamics, fast weights, reflex compilation and architecture search only after an ablation shows a concrete need.

## 2. Motivation, constraints and terminology

The user's starting intuition was that a capable system should not have to expand its *active* neural machinery in direct proportion to everything it learns. Like a processor loading programs, a small reusable substrate might draw on large mostly inactive stores. The aspirational system could have up to about 1 TB of cold storage while routine working memory stays comfortably under 16 GB. That is an architectural target, not a requirement for experiment 0 or an existing demonstrated system.

- **Core / interpreter:** trainable shared machinery that selects and executes actions over structured state.
- **Workspace:** typed entities, attributes, relationships, intermediate values and uncertainty for the current task.
- **Episode:** an input, execution trace, answer, verifier result and runtime metrics.
- **Program:** a typed, inspectable sequence or graph of operations reusable across instances. A repeated opcode string alone does not establish an interpretable algorithm.
- **Macro:** a reusable composition with measured total execution cost, including lookup and dispatch.
- **Reflex:** a cheap rule or decision structure generated from proven frequent cases.
- **Cold memory:** storage that is fetched selectively; it is not a promise of constant-time or zero-energy retrieval.
- **OOD:** a declared held-out distribution shift such as larger graphs, changed topology, different entity names or unseen task compositions.

Keep input and output language interfaces outside the first benchmark: use a typed task representation. English examples illustrate the goal but introduce parsing ambiguity. For example, “A west of B; B north of C; C inside D; D moves east” requires an explicit coordinate frame and movement semantics before one can label A relative to C. The simulator must specify those rules and generate unambiguous oracle answers.

## 3. How the proposal evolved

| Phase | Idea explored | Why it mattered | Current disposition |
|---|---|---|---|
| Initial | Small reusable cognition with huge inactive storage | Separates active compute from accumulated information | Remains guiding constraint; quantify all storage and retrieval costs |
| SAGE-0 through SAGE-4 | Persistent sparse workspace, recursive kernel, event-triggered updates, semantic/episodic and procedural memory | Reuse state and avoid recomputing stable variables | Implement a minimal typed workspace first; measure sparsity rather than assume it |
| SAGE-5 through SAGE-8 | Compile reasoning traces; self-generated tasks; frontier teachers; evaluated evolution | Make hard solutions reusable and allow candidate improvements | Program compilation enters experiment 0; teachers and evolution remain later phases |
| SAGE-9/10 | Language codec and ternary/sparse CPU runtime | Preserve separation between reasoning and surface language; lower data movement | Postpone until a correct algorithmic core exists |
| New literature round | Learned instruction language and neural algorithmic reasoning | Test whether the system discovers transferable procedures | Became the central experimental hypothesis |
| New literature round | Energy minimization, sparse pathways, fast weights, associative completion | Alternative mechanisms for search, routing and short-lived adaptation | Competing ablations, not prerequisites |
| New literature round | Superposition, Tsetlin rules, reservoir systems | Possible compact representation and execution paths | Investigate only if targeted baseline comparisons justify them |
| Current | Neuro-programmatic experiment with objective verifier | Separates invention from evaluation and makes progress falsifiable | Implement the smallest testable version |

The prior discussion sometimes framed these architectural sketches as if they were established engineering results. They are combinations of separate research directions. Positive results from a paper on one task do not validate the combined SAGE architecture or its performance on general reasoning.

## 4. Literature and how it affects the design

### 4.1 Programs and extrapolation

The ICLR 2026 *Gradient-Based Program Synthesis with Neurally Interpreted Languages* explores learning discrete symbolic-like instructions and an interpreter end-to-end [R01]. This supports testing an acquired operation vocabulary. It does **not** show that a 2–5M-parameter SAGE will autonomously invent a useful general-purpose ISA. The COLT 2026 shortest-path paper establishes Bellman–Ford-like behavior for a sparsity-regularized GNN under its stated setting [R02]. This motivates size extrapolation and explicit algorithmic probes; it does not establish broad compositional reasoning.

**Design change:** make executable procedures first-class. Evaluate the semantics, input sensitivity and transfer of each proposed opcode, rather than simply counting frequent trace fragments.

### 4.2 Adaptive computation and event-driven inference

Energy-Based Transformers infer candidate predictions through iterative energy minimization [R03]. Predictive coding supplies a separate local-error-based inspiration [R04, R05]. Sparse or partially recurrent topology [R06] and learned pathways [R07] offer potential compute savings. None proves that local asynchronous updates beat a conventional optimized CPU routine for the first graph tasks.

**Design change:** a residual-based or energy-based solver is an optional compared variant. Define the energy function, convergence tolerance and maximum updates. Log actual touched nodes and joules; never equate theoretical sparsity with measured speed or power improvement.

### 4.3 Representation and memory

Work on superposition connects sparse feature representations and compressed sensing [R08]. Associative memory and memristive implementations explore pattern completion and specialized hardware [R09]. Test-time training and fast-weight interpretations treat temporary state as an adapted function [R10, R11]. V-JEPA 2 supports modeling decision-relevant latent representations rather than reconstructing raw pixels [R12]. Hardware-specific energy claims must not be transferred to an ordinary i5/SSD implementation.

**Design change:** define typed sparse state and a retrieval interface, but use a simple indexed store initially. Compare associative recall and fast adaptation with it only after the task needs them. There is no numeric guarantee that 4,096 physical dimensions reliably encode 100,000 usable concepts for these tasks.

### 4.4 Compilation and physical efficiency

Tsetlin-machine accelerators explore low-power Boolean rule learning [R13]; BitNet documents ternary LLM inference implementations [R14]; reservoir approaches explore recurrent computation [R15]. Distillation of slow deliberation to fast behavior [R16], SkillDisCo [R17], and sleep-time compute [R18] motivate an offline consolidation phase. Results in those papers are task- and hardware-specific.

**Design change:** first compile and validate small programs as ordinary CPU code. Quantization, Boolean logic accelerators, background training and ternary kernels come after direct measurement against the basic implementation.

### 4.5 Controlled improvement

AlphaEvolve [R19], Darwin Gödel Machine [R20], Absolute Zero [R21], Nested Learning [R22], and AIDE² [R23] inspire candidate generation, automated testing, archive promotion and multiple update rates. A broad 2026 survey notes the importance and limits of evaluator quality [R24]. Energy-aware recurrent computation [R25] suggests power as a measured objective, not a shortcut to brain equivalence.

**Design change:** proposals may come from an AI teacher, but the evaluator, hidden test set and promotion decision stay independently controlled. Benchmark generalization and total task cost before keeping a mutation. Early SAGE does not modify its own evaluator.

## 5. The current architecture, with boundaries

```text
Typed input / later language codec
            |
            v
Sparse task workspace and uncertainty state
            |
            v
Router: exact operation -> indexed memory -> learned program -> iterative solver
            |                                        |
            +--------------------+-------------------+
                                 v
                      Typed candidate answer
                                 |
                                 v
                      External task oracle / verifier

Offline: trace archive -> candidate programs -> held-out evaluation -> promotion
```

A router may send a task straight to a known exact operation. This is valuable engineering, but a benchmark in which the exact solver already handles every task gives a learned system no meaningful reasoning advantage. Report the exact solver separately and choose task families whose challenge is *inferring* a reusable procedure from examples or combining known primitives under new conditions.

Possible future state hierarchy: millisecond workspace; session fast weights; persistent episodes and semantic store; slower program consolidation; occasional architecture experiments. “Sleep” means scheduled offline training/validation, not a biologically substantiated sleep mechanism.

## 6. Experiment 0: testable question and scope

**Primary question:** Can a small model learn or select compositional programs that extrapolate to larger and differently structured relational tasks, and can validated compilation lower *total* repeated-task cost without hurting accuracy?

**Subquestions:**

1. Does program execution improve OOD accuracy compared with parameter-matched neural inference?
2. Can a learned interpreter execute length- or size-general procedures, as opposed to memorizing templates?
3. Does compilation reduce wall time, CPU energy and bytes touched after including discovery, training, storage, lookup and dispatch in amortized reports?
4. When does a program fail on a new topology or composition, and can the verifier detect that before adoption?

### 6.1 Task universe

Implement a deterministic generator returning a typed graph, query and exact oracle answer. Start with one connected family (reachability, shortest paths or relation composition) before mixing categories. The earlier proposed menu of sorting, mazes, sets, arithmetic, causal chains, planning and ARC-like tasks is a staged curriculum, **not** a credible one-shot v0 training set.

Suggested first family:

- Directed and undirected graphs with typed edges; path existence and shortest-path distance for unweighted graphs.
- Relation composition over directed labeled edges with carefully specified composition rules.
- Graph transformation actions, then queries over the changed graph.
- Explicit negatives and unanswerable cases; avoid label leakage from generator order or node names.
- Balanced short/long paths and carefully stratified disconnected cases.

Use train graphs with 4–10 nodes; validation with distinct random seeds and graph families; held-out test strata at 11–20, 21–50, 51–100 and 101–500 nodes where feasible. Train/test splits must separate *generating grammars or topology regimes* as well as sizes. Larger graphs alone are weak evidence of compositional generalization if the generator remains simplistic.

### 6.2 Systems and fair baselines

| ID | System | Role |
|---|---|---|
| O | BFS / Bellman–Ford / symbolic oracle | Correctness and CPU cost floor for tasks whose rules are provided |
| A | Small Transformer or recurrent encoder with task head | Standard learned baseline; matched training budget and parameter range |
| B | Shared recurrent state update with adaptive halt | Tests recurrence and compute allocation |
| C | Learned discrete opcode selection plus typed executor | Tests program learning and transfer |
| C0 | C without program archive or compilation | Within-model comparison for compilation |
| C1 | C with proposed program archive, validated and reused | Tests true cost of reuse |

A hard-coded executor operation is permitted, but list its semantics and cost. If system C contains built-in graph traversal while A does not, the comparison measures the provided prior; show that transparently and include a symbolic program-synthesis or search baseline using the *same* primitives. Match optimization steps, examples, seed count and tuning budget; report model and archive size separately.

The earlier suggested 64–128 state slots, dimension 128–256, 32 opcodes, length 1–32 and 2–5M trainable parameters are **initial search ranges, not validated specifications**. At 500-node tests, fixed 128 slots cannot represent arbitrary graphs without external addressable memory; either implement a variable-size store or constrain what is being claimed. Profile memory before selecting dimensions.

### 6.3 Proposed minimal implementation sequence

1. Write a generator with reproducible seeds, typed schema and independent exact oracle. Include mutation-based checks of answer invariance under node renaming and edge order.
2. Freeze a small development set and a hidden held-out evaluation set with separate seeds and topology regimes. Record hashes, generator version and task distributions.
3. Implement oracle and a simple learned baseline. Produce a reproducible baseline report before adding the program learner.
4. Define a typed DSL: `LOOKUP_NEIGHBORS`, `VISIT`, `COMPARE`, `UPDATE_DISTANCE`, `BRANCH`, `HALT` are examples. Explicitly distinguish hand-given primitives from genuinely learned operations. Interpreter termination, data types and maximum execution steps must be deterministic.
5. Implement system C, trace logging and a simple candidate program search/selection procedure. Prioritize tractability on CPU; start with 1–10-node tasks and scale only when training works.
6. Validate a candidate program against fresh development examples, property-based tests and a separate OOD gate. Deduplicate equivalent programs; reject if coverage or accuracy regresses.
7. Promote to the archive and route repeated tasks through it. Measure lookup overhead, false routing, fallback frequency and end-to-end cost.
8. Run paired comparisons over multiple seeds, report confidence intervals and failure traces. Only then consider a learned opcode vocabulary or macro induction.

A file layout for a Codex repository:

```text
sage/
  README.md
  pyproject.toml
  configs/
  src/sage/tasks/{schema,generator,oracle}.py
  src/sage/models/{baseline,recurrent,program}.py
  src/sage/runtime/{dsl,interpreter,router,archive}.py
  src/sage/eval/{splits,metrics,energy,report}.py
  tests/{oracle_properties,interpreter_semantics}.py
  experiments/
  reports/
```

Use unit/property tests where they protect the independent oracle, execution semantics and split isolation. Save all metrics with code revision, hardware, power sampling method, seeds and configuration. Pin dependency versions after establishing the environment.

### 6.4 Measurement and pass/fail criteria

Primary metrics: exact-match accuracy (and task-specific validity), OOD accuracy by shift, CPU package joules per *correct* task if available, wall time including routing and retrieval, peak resident RAM, bytes read/written, executed instructions, touched nodes and archive size. When package energy telemetry is unavailable, report calibrated wall power and uncertainty separately rather than present estimated joules as precise measurements. Warm and cold runs are separate.

Report two efficiencies:

- **Operational:** measured cost for steady-state requests including lookup, fallback and correctness checks.
- **Amortized:** operational cost plus offline training, teacher, search and compilation cost distributed over an explicitly stated number of uses. Find the break-even number of uses; do not hide offline compute.

Pre-register a narrow gate, for example: C must beat A/B on a held-out size/topology regime over three or more seeds without worse in-distribution accuracy beyond a declared margin; C1 must have lower median end-to-end energy or latency than C0 for a specified request mix with comparable correct answers; macro speedups must persist after lookup cost. The exact numeric margins and request mix should be fixed in configuration *before* viewing hidden results. A shortcut or an exact hand-coded BFS win is not evidence of learned algorithm discovery.

Use a Pareto frontier over accuracy, energy, latency and peak memory. The earlier multiplicative “intelligence density” formula (OOD capability divided by joules × active bytes × latency) is a useful intuition, but accuracy must be precisely defined and the denominator can double-count correlated costs. Do not make that arbitrary scalar the sole acceptance test.

### 6.5 Ablations and failure diagnoses

- No archive; archive with random routing; archive with oracle routing.
- Fixed versus learned opcodes, with matched primitive access.
- One-step versus recurrent execution and capped reasoning steps.
- Retrieval disabled/enabled if external memory is used.
- Macro length, graph size, topology, edge order and arbitrary node renaming.
- Accuracy by path length, disconnected cases and generator family.
- Training stability across seeds; program validity, interpreter step cap and nontermination.
- Total cost under low and high reuse. A macro may shorten *source length* while increasing runtime.

Stop or revise if C cannot learn elementary tasks, if C loses size extrapolation to simpler algorithms, if the evaluator can be gamed, or if archive retrieval dominates all saved compute. A negative result is still a valid result: it clarifies which proposed mechanism does not earn its cost.

## 7. Later roadmap and what must earn its place

1. **Persistent episodic/semantic memory:** introduce tasks requiring storage across sessions; compare indexed retrieval, associative completion and cache policies.
2. **Fast weights:** introduce rapid adaptation under changing rules; compare with explicit session memory.
3. **Sparse/event-triggered solver:** introduce local updates and count actual changed nodes and energy.
4. **Learned ISA and topology:** allow new primitive semantics or pathway configurations; test backward compatibility and cost. Simply giving more opcodes is not success.
5. **Offline consolidation:** propose macros, rules or simpler representations from successful traces; evaluate on held-out cases.
6. **Teacher-assisted research:** outside model proposes tasks or programs; track teacher cost and avoid leaking held-out tests.
7. **Architecture evolution:** isolate candidates, independently evaluate, archive only statistically meaningful gains and retain rollback.
8. **Language codec and multimodal grounding:** connect structured reasoning to text and sensory tasks; measure parsing and grounding separately.
9. **Quantization/hardware work:** profile BF16, INT8, INT4, ternary or bitwise representations on actual target CPU after a working baseline.

No stage implies the next one is justified. The 1 TB/16 GB aspiration becomes meaningful only when capability and retrieval quality continue improving over a range of archive sizes with bounded measured active working sets.

## 8. Explicit revisions to earlier enthusiasm

- **“Invent its own CPU architecture”** is a long-term analogy. First test whether a restricted interpreter learns transferable operations; unrestricted self-modification is outside experiment 0.
- **“40 cycles to one macro”** is not automatically cheaper: a macro can call the same steps; measure actual executed work and lookup.
- **“Capability doubles while computation barely changes”** needs a measurable capability set and fixed task distribution. Growing cold storage, indexing and teacher costs count.
- **“Equilibrium solves reasoning”** is an experiment, not a replacement decision. Energy minimization can be slow or converge to the wrong answer.
- **“Superposition means 100,000 concepts in 4,096 dimensions”** is illustrative only; capacity and interference depend on activation statistics and retrieval error.
- **“Fast weights are more powerful than KV cache”** depends on task and implementation; compare directly.
- **“Teacher disappears from runtime”** can hold architecturally, but teacher cost remains part of acquisition cost and provenance.
- **“SAGE could become smarter while idle”** means measured improvement on future held-out tasks after offline consolidation, not self-reported progress.
- **“General intelligence”** is not an outcome of graph benchmarks. Claims must stay at the scope actually measured.
- **“No English after parsing”** is a useful isolation strategy, though the cost and reliability of a future language codec remain open.

## 9. Design decisions and open questions for the new Codex project

- Start in Python with PyTorch for learned components and ordinary typed Python (or optimized compiled code after profiling) for the executor. Do not choose an exotic runtime before a baseline exists.
- Decide the first single task family and rules formally. Graph path tasks provide exact verification but have a very strong symbolic baseline; select an additional family that tests *learning the rule* rather than only executing BFS.
- Decide whether program opcodes are pretrained, searched, differentiably induced or learned as latent embeddings; document what is actually learned.
- Decide how a routed program handles uncertainty and detects unsupported inputs.
- Design held-out splits that cannot be reached via generated examples or teacher prompts; maintain evaluator separation.
- Set an energy sampling method appropriate to the actual i5 and operating system; record idle baseline and thermal conditions.
- Track program library growth and indexing overhead versus capability growth. If active memory grows linearly, the key aspiration fails even if accuracy improves.

## 10. Copyable Codex kickoff prompt

> Read `SAGE_project_handoff.md` completely. Build experiment 0 only. First inspect the local machine and repository, then implement a typed reproducible graph-task generator, independent exact oracle, held-out split construction, and a simple learned baseline. Add a typed program interpreter and program-learning candidate with the same exposed primitives as a symbolic synthesis baseline. Log OOD correctness, instruction counts, routing/lookup cost, wall time, peak memory and energy if reliable telemetry exists. Keep the hidden evaluation separated from candidate generation. Run a small smoke experiment and report failures and costs honestly. Treat all architectural claims in this document as hypotheses. Do not add language, self-modifying architecture, a frontier teacher or a GPU requirement until the initial comparison earns it.

## 11. Reference ledger

These are links explicitly visible in the provided conversation excerpt, with a few checked against the public sources on 2026-09-26. “Prior discussion” means a source was cited in the conversation; it does not mean this handoff independently reviewed the entire paper. Source titles and research results belong to their authors. SAGE design conclusions are our proposed inferences.

| ID | Source and link | Use / caution |
|---|---|---|
| R01 | [Gradient-Based Program Synthesis with Neurally Interpreted Languages, ICLR 2026](https://proceedings.iclr.cc/paper_files/paper/2026/hash/c9cde817d04811ba28e44071bd9f76a5-Abstract-Conference.html) | Learned discrete symbolic-like language and interpreter; scope is paper tasks |
| R02 | [Graph neural networks extrapolate out-of-distribution for shortest paths, COLT 2026](https://proceedings.mlr.press/v336/nerem26a.html) | Sparse regularization and Bellman–Ford under stated assumptions |
| R03 | [Energy-Based Transformers are Scalable Learners and Thinkers, ICLR 2026](https://proceedings.iclr.cc/paper_files/paper/2026/hash/e19a65fd53b6f9a88b354da98813465d-Abstract-Conference.html) | Iterative energy minimization, not proof of SAGE equilibrium architecture |
| R04 | [Predictive-coding survey, ACM DOI](https://doi.org/10.1145/3797870) | Asynchronous/local-inference inspiration; check full text before citing specifics |
| R05 | [Predictive coding neuroscience review](https://www.sciencedirect.com/science/article/pii/S0149763423004426) | Brain-theory caveats; not an engineering validation |
| R06 | [Partially recurrent neural networks, Nature DOI](https://doi.org/10.1038/s44488-026-00013-z) | Sparse topology result in particular tested systems |
| R07 | [Pathways and continual learning, PMLR](https://proceedings.mlr.press/v267/chen25bt.html) | Sparse activation pathways and retention |
| R08 | [Superposition and sparse coding, Nature Machine Intelligence](https://www.nature.com/articles/s42256-026-01259-z) | Representation capacity and interference; no promised capacity figure |
| R09 | [Multilayer associative memory on memristive hardware, Nature Communications](https://doi.org/10.1038/s41467-026-69958-0) | Specialized-hardware associative memory; no general CPU speed claim |
| R10 | [Test-time training language model implementation](https://github.com/test-time-training/ttt-lm-pytorch) | Fast adaptive state implementation |
| R11 | [Test-time regression framework, JMLR](https://www.jmlr.org/papers/v27/25-0903.html) | Unifying view of context-dependent updates |
| R12 | [V-JEPA 2, Meta AI](https://ai.meta.com/research/vjepa/) | Latent prediction and planning; different modality and scale |
| R13 | [Tsetlin accelerator, IEEE DOI](https://doi.org/10.1109/TCSI.2025.3564875) | Low-power logic hardware result relative to its stated comparator |
| R14 | [BitNet official repository](https://github.com/microsoft/BitNet) | Ternary implementation and benchmark details |
| R15 | [Reservoir language modeling, Physical Review Applied](https://journals.aps.org/prapplied/abstract/10.1103/sd11-x3ny) | Alternative dynamical workspace idea |
| R16 | [Distilling System 2 into System 1](https://arxiv.org/abs/2407.06023) | Moving slow reasoning into faster behavior |
| R17 | SkillDisCo, Microsoft 2026: **exact link absent from supplied excerpt** | Mentioned in prior discussion; locate paper and verify claim before citing |
| R18 | [Sleep-Time Compute](https://arxiv.org/abs/2504.13171) | Offline preparation in its stateful reasoning setting |
| R19 | [AlphaEvolve, Google DeepMind](https://deepmind.google/blog/alphaevolve-a-gemini-powered-coding-agent-for-designing-advanced-algorithms/) | Generated algorithms evaluated against objective metrics |
| R20 | [Darwin Gödel Machine](https://arxiv.org/abs/2505.22954) | Archive-based code modification on stated benchmarks |
| R21 | [Absolute Zero Reasoner](https://arxiv.org/abs/2505.03335) | Self-generated executable problems and verification |
| R22 | [Nested Learning, Google Research](https://research.google/blog/introducing-nested-learning-a-new-ml-paradigm-for-continual-learning/) | Multiple adaptation timescales |
| R23 | [AIDE²: Recursive self-improvement of AI research agents](https://arxiv.org/abs/2609.26457) | 2026-09-22 preprint; reported eight-day, seven-improvement agent experiment, not a general RSI proof |
| R24 | [Recursive Self-Improvement in AI: survey of 1,250 papers](https://arxiv.org/abs/2607.07663) | Verification hierarchy and limitations of open-ended claims |
| R25 | [Energy efficiency and predictive-coding-like dynamics](https://pmc.ncbi.nlm.nih.gov/articles/PMC9768680/) | Motivates direct energy measurement; system/task-specific |
| R26 | [Continual-learning information bottleneck article](https://www.sciencedirect.com/science/article/pii/S0031320325006806) | Efficient subnetworks in its experimental context |

**Verification note:** R01, R02, R03, R23 and R24 were independently located during preparation. Other links were transcribed from the supplied conversation; check original papers and experimental conditions before making precise numerical claims in a publication. The previous discussion mentioned additional categories such as MoE, HDC and graph/pathway methods without complete source identifiers in the provided excerpt. No missing reference has been invented.

## 12. What constitutes a successful first milestone

A working reproducible repository with a correct task oracle, disjoint evaluation splits, executable DSL, neural and symbolic baselines, result logs, and one honest report showing where a learned program system helps or fails. A negative result with good controls is preferable to a grand architecture diagram with no independently measured improvement.
