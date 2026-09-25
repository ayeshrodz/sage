# SAGE: independent review and a proposed revision of experiment 0

**Date:** 2026-09-25  
**Reviewer:** Claude (Anthropic), reviewing [`00-handoff-openai.md`](00-handoff-openai.md)  
**Status:** a proposal for discussion. Nothing here is decided until we agree on it.  
**Update 2026-09-25:** the reframe and the relational domain were accepted (see [`02-objective-and-decisions.md`](02-objective-and-decisions.md)); stage 0a has run and passed its gate (see [`03-stage-0a-results.md`](03-stage-0a-results.md)).

**How to read this.** §0 is the short version. §1 restates SAGE so you can check that I understood it. §2 and §3 say what I would keep and what I would change, and why. §4 is a small pilot I ran to test the most important concern. §5 is the revised experiment, §6 maps each original idea onto it, and §7 lists the decisions I need from you. §8 audits the references and adds the missing ones.

---

## 0. Short version

1. **Keep the handoff's discipline.** It pre-registers its gates, separates operational from amortized cost, keeps the evaluator out of the system's reach and treats a negative result as a result. All of that is right, and rarer than it should be.
2. **Experiment 0 tests the wrong hypothesis.** On graph tasks whose rules are given, a symbolic program (BFS) extrapolates by construction and a neural baseline will not, so the outcome is predictable. More importantly, it says nothing about SAGE's distinctive claim, which is that *stored procedures let capability grow while active compute stays bounded*.
3. **SAGE's core loop is old, and so is its known failure.** "Solve expensively, store the solution, reuse it cheaply" is what macro-operators did in the 1970s and 80s. It is also explanation-based learning and Soar chunking (1980s), and DreamCoder-style library learning (2020s). That work found the **utility problem**: every stored item widens search and adds matching and selection work, and past some library size, learning makes the system *slower*. LLM-agent papers from 2024 to 2026 keep running into it again. Their libraries barely get reused, and choosing the right skill gets harder as libraries grow. The handoff touches parts of this but never names it. I think it should be the central research question.
4. **Two design flaws to fix.**
   - The runtime diagram sends candidate answers to the external oracle. That gives the system ground truth at test time.
   - If the rules are given, the exact solver is both the floor and the ceiling, so nothing is learned.

   Both are fixed by making each task an *induction* problem. The system sees demonstrations of a hidden procedure, which act as a visible but fallible runtime verifier. It is scored on held-out queries, which act as the hidden oracle.
5. **Neural parts should propose, not execute.** Put learning where approximation is harmless because verification catches the errors: guiding search, routing and ranking. Execute programs symbolically, which is exact and extrapolates by construction. That takes the hardest open problem, neural extrapolation, off the critical path and keeps everything CPU-friendly.
6. **A toy pilot that runs in under a minute shows the shape of the problem (§4).**
   - A library turns an infeasible search into a cheap one.
   - Adding library entries without a guide makes search infeasible again. With a weak verifier, it also makes most answers *wrong*.
   - A guide keeps search flat only if its discrimination grows like the log of the library size.
   - Once search is flat, routing becomes the dominant cost unless it is sublinear.
7. **Proposed experiment 0 is planted-library induction on typed relational worlds (§5).** It keeps your relational and graph domain and runs in five stages with decision gates. Stage 0a involves no learning and is cheap and decisive: it measures the economics of a *given* library before we try to learn one.

---

## 1. What I understand SAGE to be

**Thesis.** Capability should scale with *stored* knowledge, which is cheap, cold and large, rather than with *active* computation, which is expensive, hot and small. A small reusable core executes procedures drawn from a large, mostly idle store. Expensive deliberation is reserved for novel tasks. Recurring tasks are compiled into cheap paths, and offline consolidation improves the store. The long-run picture is up to ~1 TB of cold store with an active working set well under 16 GB.

The thesis splits into four hypotheses that can succeed or fail independently:

| | Hypothesis | The failure it has to survive |
|---|---|---|
| H1 | **Amortization.** Repeated exposure turns search into cheap reuse, *net of* lookup and verification. | Lookup and false matches cost more than they save. |
| H2 | **Compositional transfer.** Stored procedures make *novel* tasks cheaper, not only repeats. | The library is rarely reused on new tasks. |
| H3 | **Bounded active compute.** As the store grows by orders of magnitude, per-task compute and working set stay bounded while coverage grows. | Search breadth and selection errors grow with the store. |
| H4 | **Neural execution.** A small learned interpreter runs procedures that extrapolate beyond training sizes. | Networks learn templates rather than algorithms. |

H1 to H3 are what make SAGE distinctive. H4 is a separate and crowded research area (CLRS, R02, R01). It isn't needed for H1 to H3 if the interpreter is symbolic. The handoff's experiment 0 mostly tests H4 and a little of H1 (its C0 vs. C1 comparison).

**A note on the CPU analogy.** A processor running stored programs is efficient for two reasons. People write the programs offline, and the memory hierarchy exploits *locality*. SAGE has to write its own programs, so discovery cost is the whole problem rather than a side cost. A program store also pays off only if the task stream actually repeats itself. Both should be measured variables, not assumptions.

---

## 2. What to keep from the handoff

- **Falsifiability.** Gates are fixed before hidden results are viewed, and a negative result can be published (§1, §6.4, §6.5, §12).
- **Operational vs. amortized cost, with a break-even number of uses** (§6.4). This is exactly the right accounting for H1.
- **Evaluator independence.** Proposals may come from anywhere, but the evaluator, the hidden test set and the promotion decision stay separate, and early SAGE never edits its own evaluator (§4.5).
- **Split hygiene.** Seeds, hashes and generator versions are recorded, and answers are checked for invariance under node renaming and edge order (§6.3).
- **The "must earn its place" roadmap**, and the retractions in §8. For example, "40 cycles to one macro is not automatically cheaper" is the utility problem in miniature.
- **A Pareto frontier** over accuracy, cost, latency and memory instead of one scalar (§6.4).

---

## 3. What I would change, most consequential first

### 3.1 Test SAGE's thesis (H1 to H3), not neural extrapolation (H4)

The handoff notices the problem itself: §9 asks for "an additional family that tests *learning the rule* rather than only executing BFS". The plan is still built around it, though. Systems A, B and C compete on shortest-path and reachability tasks with given rules. The most likely outcome is already known from the literature: a correct program extrapolates, and most networks trained on 4 to 10 nodes degrade on 500 unless their architecture is aligned with the algorithm, which is R02's point. That result wouldn't tell us whether a growing store of procedures makes a system cheaper per correct answer, which is the thing SAGE is about.

### 3.2 Take the oracle out of the runtime loop

The architecture diagram (handoff §5) sends each typed candidate answer to an "external task oracle / verifier". If the system can consult the oracle before committing, it can retry until it is right. Accuracy then means nothing and only cost is left. Separate the two roles:

- **Runtime verifier:** whatever the task itself supplies, such as its demonstrations and type constraints. It is available at runtime and it is *fallible*, because a program can fit every demonstration and still be wrong.
- **Evaluation oracle:** ground truth on held-out queries. The system never sees it.

The gap between the two, a program that is demo-consistent but wrong, is itself a key metric. It is the handoff's subquestion 4 ("can the verifier detect that before adoption?") made measurable.

### 3.3 Make every task an induction problem

If the rules are given, system O solves every task exactly at minimal cost. Learned systems can only tie or lose, and "program discovery" means rediscovering a routine we already handed over. Instead, make each task a few input→output demonstrations of a hidden procedure plus held-out queries. O then becomes the generator's hidden program: the floor on execution cost rather than a competitor. The meaningful baselines become search without a library, search with the planted library, and direct neural prediction.

### 3.4 Put SAGE in its lineage, and adopt that lineage's central failure as the research question

| SAGE idea | Closest prior work | What that work learned |
|---|---|---|
| Save solutions as macros | STRIPS macro-operators (Fikes, Hart & Nilsson 1972); Korf (1985) | Macros pay only when they cut search depth by more than they add branching. |
| Compile deliberation into reflexes | Soar chunking (Laird, Rosenbloom & Newell 1986); ACT-R knowledge compilation | Some learned rules cost more to *match* than they save ("expensive chunks", Tambe, Newell & Rosenbloom 1990). The fix was to restrict what a rule may express so that match cost stays bounded. |
| Store verified solutions for reuse | Explanation-based learning (Mitchell, Keller & Kedar-Cabelli 1986); PRODIGY (Minton 1990) | **The utility problem.** Without measuring each rule's utility, learning slowed the system down. Keeping only rules where frequency × savings exceeds match cost made it faster. |
| Offline consolidation ("sleep") | DreamCoder wake–sleep (Ellis et al. 2021); complementary learning systems (McClelland, McNaughton & O'Reilly 1995) | Compressing solved programs into abstractions, plus training on "dreamed" tasks, works in small domains. It is expensive and depends on the curriculum. |
| A growing program library | Stitch (Bowers et al. 2023); LILO (Grand et al. 2024) | Compression-based library learning is fast now. **But:** "Library learning doesn't" (Berlot-Attwell et al. 2024) found that two LLM library learners almost never reused their libraries. Their gains came from self-correction and self-consistency. |
| A router over a large store | Voyager's skill library (Wang et al. 2023); 2026 skill-library studies | Selection degrades as libraries grow. One study measured a drop of up to 21 points at 202 skills, mostly from wrong-skill choice ("skill shadowing") rather than context size (Song & Wei 2026). Another found top-5 retrieval reached only 73.5% over 690 skills (Kolluru & Sportsman 2026). |
| Small active compute, large store | Mixture of experts (Shazeer et al. 2017); product-key memory (Lample et al. 2019); memory layers at scale (Berges et al. 2024); RETRO (Borgeaud et al. 2022); LLM in a flash (Alizadeh et al. 2024) | Mainstream ML already builds "big cold, small hot" systems. What decides whether they work is retrieval quality and bandwidth, not storage. |
| The router decides how hard to think | Rational metareasoning (Russell & Wefald 1991); cascades (FrugalGPT, Chen et al. 2023); amortized inference (Gershman & Goodman 2014) | Cheap-first cascades pay when verification is cheap and the cheap path is often right. |
| A small recurrent core (system B) | Deep-thinking networks (Schwarzschild et al. 2021; Bansal et al. 2022); HRM (Wang et al. 2025); TRM (Jolicoeur-Martineau 2025) | TRM has 7M parameters and reaches 45% on ARC-AGI-1 by iterative refinement. It is the natural "tiny core" baseline. |
| Programs vs. neural prediction | Induction vs. transduction on ARC (Li et al. 2024) | The two solve *different* tasks, and an ensemble beats either. |
| Neural-guided search | DeepCoder (Balog et al. 2017); BUSTLE; CrossBeam | Small networks that rank primitives cut search cost by orders of magnitude. |

This lineage turns SAGE from "a new architecture" into a sharp question with a known failure mode:

> **Can learned guidance plus verification escape the utility problem, so that capability grows with the store while per-task compute stays bounded?**

As far as I know, this is under-studied in controlled settings. It is testable on an i5, and it is the question the 1 TB / 16 GB aspiration actually depends on. The handoff has pieces of it: §6.5 says a macro "may shorten *source length* while increasing runtime", and §9 says to track "library growth and indexing overhead". It never names the problem or draws on the decades of work behind it.

### 3.5 The utility problem has two faces

- **Computational.** Every stored procedure widens search, and routing and matching work grow with the store.
- **Statistical.** A bigger hypothesis space contains more programs that fit the demonstrations by accident. And because the library defines which programs count as "short", a junk library is a junk prior. By the usual Occam/PAC intuition, spurious-fit risk grows roughly with ln(number of hypotheses) ÷ (number of demonstrations). The 2026 skill-shadowing result is this face in LLM agents: more skills, more wrong selections.

The handoff's accounting covers the first face but not the second. The pilot in §4 shows that the second can turn a cost problem into a correctness problem.

### 3.6 "Compilation" means four different things with different economics

| Kind | What it saves | What it costs | Does it matter for experiment 0? |
|---|---|---|---|
| Caching (task → program) | the whole search, on a repeat | lookup, verification, false hits | Yes (H1) |
| Abstraction (library learning) | search depth on *new* tasks | branching, routing, spurious fits | Yes (H2, H3) |
| Execution optimization (native code, fusion) | time per call | compile time | Barely. Search costs orders of magnitude more than execution. |
| Distillation into a fast proposer (the "reflex") | search breadth | training, plus errors that need a fallback | Yes (H3). This is the guide. |

Measure them separately. A single "compiled vs. not" switch mixes all four.

### 3.7 Neural components should propose, not execute

Networks are good at ranking and guessing but bad at exact extrapolation. Programs are exact but expensive to find. So let a small network propose, meaning it ranks library entries, guides search and routes between paths. Let a symbolic interpreter execute, and let the demonstrations accept or reject. Mistakes by the network then mostly cost time. They cost correctness only when the demonstrations are too weak to reject a wrong program (§3.5, §4).

This removes H4 from the critical path without giving it up. Learned primitives (R01's line) become interesting later, once tasks need primitives nobody can write by hand, such as noisy or perceptual inputs.

### 3.8 Make the primary cost a deterministic operation count

Wall time and joules on a laptop i5 are noisy. Turbo boost, thermal state and background processes can move them by several percent from run to run, which can swamp the effects we care about. Instead, count work:

- candidate programs evaluated and primitive operations executed,
- routing comparisons and verifier calls,
- offline consolidation and guide-training work.

These counts reproduce exactly, allow paired comparisons and are what a utility analysis needs. Report CPU time and peak RSS as secondary metrics, and check once, by regression, that time tracks the counts. On Linux, `perf stat` instruction counts are a good hardware-level cross-check.

Energy is harder to get:

- Linux has restricted reading RAPL energy counters to root since late 2020, after the PLATYPUS side-channel attack.
- Windows has no simple equivalent.

So treat joules as a secondary estimate unless you can read RAPL. Keep the handoff's rule of reporting the uncertainty.

### 3.9 Map regimes instead of a single pass or fail

Whether SAGE's approach pays depends on four things:

- how skewed reuse is in the task stream (a Zipf exponent),
- how deeply tasks compose,
- how large the library is,
- how strong the runtime verifier is (the number of demonstrations and whether they cover edge cases).

A map of net benefit over those axes tells us *when* the idea works. That is more useful, and harder to fool ourselves with, than one threshold. Include a control stream with no shared structure, where the library *should not* help. If it seems to help there, something is leaking.

---

## 4. Pilot: the utility problem in a toy (under a minute on a laptop CPU)

The script is [`pilot/utility_curve.py`](../pilot/utility_curve.py): pure Python, no dependencies. The full output is in [`pilot/RESULTS.md`](../pilot/RESULTS.md).

**Setup.**
- **Programs:** chains of unary functions on integers mod 101, built from 10 primitives (x+1, 2x, x², 1/x, and so on).
- **Planted library:** 8 macros of 3 primitives each.
- **Targets:** each chains 3 planted macros, filtered so that it needs at least 7 primitives. The primitives obey identities (m∘m = id for some macros, 2x∘x/2 = id), and unfiltered targets often collapsed to a few primitives.
- **Solver and oracle:** the solver sees 2 or 4 input→output demonstrations; the oracle checks all 101 inputs.
- **Search:** best-first, pruning programs that give identical outputs on the demonstrations. Ties are broken at random and costs are counted.
- **Library sizes:** the planted macros plus 0 to 10,000 random distractor macros. 30 tasks per row, with a budget of 60,000 candidate programs per task.
- **Guides:** three *simulated* guides. They know which tokens are relevant, so this measures how good a guide must be, not whether one can be learned.
  - *uniform:* no guide at all.
  - *margin:* relevant tokens get a fixed 100× likelihood advantage (4.6 nats), so their share shrinks as the library grows.
  - *mass:* relevant tokens keep 90% of the probability mass at any library size.

**Four demonstrations per task: solve rate and median candidate programs generated.**

| Library (tokens) | uniform | margin | mass | mass: total ops (share spent on routing) |
|---|---|---|---|---|
| none (10) | 3%, ≥60,000 | 17%, ≥60,000 | 7%, ≥60,000 | 240,320 (0.1%) |
| planted (18) | 100%, 3,204 | 100%, 21 | 100%, 21 | 828 (70%) |
| + 10 distractors (28) | 100%, 10,478 | 100%, 24 | 100%, 24 | 1,184 (76%) |
| + 100 (118) | 20%, ≥60,000 | 100%, 25 | 100%, 25 | 4,076 (93%) |
| + 1,000 (1,018) | 7%, ≥60,000 | 100%, 1,038 | 100%, 23 | 32,858 (99%) |
| + 10,000 (10,018) | 3%, ≥60,000 | 53%, 50,165 | 100%, 19 | 320,804 (99.9%) |

**Two demonstrations per task: share of answers that are actually correct.** With only 2 demonstrations almost every run finds *some* consistent program, so being solved no longer means being correct.

| Library | uniform | margin | mass |
|---|---|---|---|
| none | 0% | 7% | 3% |
| planted | 77% | 100% | 100% |
| + 10 | 40% | 100% | 100% |
| + 100 | 7% | 100% | 100% |
| + 1,000 | 0% | 83% | 100% |
| + 10,000 | 0% | 10% | 100% |

**What it shows.**

1. **A library shortens depth.** Without one, targets of 7 to 9 primitives are out of reach. With the planted macros they cost about 3,200 candidates unguided, or about 20 guided.
2. **Adding entries without a guide backfires fast.** Ten distractors multiply the cost by 3.3, close to the (28/18)³ ≈ 3.8 that breadth-first arithmetic predicts. A hundred distractors put 80% of tasks out of budget.
3. **A guide with fixed discrimination holds only until the library outgrows it.** With a 4.6-nat margin, cost stays flat up to about 100 tokens (≈ e^4.6). It then rises about 40× by 1,000 tokens, and nearly half the tasks fail at 10,000. To keep search flat, the guide's discrimination must grow like ln(library size): **every 10× growth of the store needs about 2.3 more nats of separation.** That is a concrete requirement for SAGE's router, and a thing to measure in any learned router.
4. **Once search is flat, routing is the cost.** With the sharpening guide, search stays at about 20 candidates, but scoring every token (32 multiply-adds each) is 99.9% of the work at 10,000 tokens. The exact crossover depends on the cost units; the scaling, flat for search and linear for routing, does not. The cold-store vision needs sublinear routing, through an index or a hierarchy, and that has to be measured rather than assumed.
5. **With a weak verifier, growth produces wrong answers, not just slow ones.** With 2 demonstrations, unguided correctness falls from 77% to 0% as distractors are added, because the search finds shorter, accidentally consistent programs first. Even with 4 demonstrations, the few spurious fits in the pilot are near-misses. They agree with the target on 99 of 101 inputs and differ only where 1/x is special-cased at 0. That is a toy edge-case bug, and random demonstrations rarely probe edge cases.

**Caveats.** The domain is toy arithmetic, and the guides are simulated with oracle knowledge of relevance. "Operations" are comparable across categories only roughly. The pilot says what a SAGE router *must* achieve, not that one can. Stage 0c (§5.8) is where we find out.

---

## 5. Proposed experiment 0: planted-library induction

### 5.1 Question

> In a stream of tasks that share hidden structure, does a learned library plus a learned guide lower the total compute per correct answer on *new* tasks, counting search, routing, verification and consolidation? And does that benefit survive growing the library by orders of magnitude?

### 5.2 Task format

- **Task:** 3 to 6 demonstrations of a hidden program, each a (world, query entity *x*, answer) triple, plus held-out queries.
- **Runtime verifier:** the demonstrations, plus type checks. **Oracle:** the held-out queries, owned by the evaluator.
- **What the generator guarantees:**
  - demonstrations include the program's edge cases where it has any (empty answers, people with no parents, cycles);
  - answers are invariant under entity renaming and edge order (the handoff's property checks);
  - queries are stratified by edge-case type.
- **Ambiguity:** we measure and report how often a task has a shorter program that fits the demonstrations but disagrees on the queries, then flag or drop those tasks.
- **Uncertainty at runtime:** when several demo-consistent programs disagree on a query, that disagreement is the uncertainty signal. This answers the handoff's open question about unsupported inputs and uncertainty.

### 5.3 Domain: typed relational worlds

This keeps your relational and graph direction, adds rule learning, and gives size and topology shifts for free.

- **Entities:** persons, places and items, with categorical attributes (colour, size).
- **Relations, each with its own topology:**
  - `parent`: a forest of family trees;
  - `friend`: a random graph;
  - `lives_in`: person → place;
  - `inside`: a containment tree of places;
  - `owns`: person → item;
  - `near`: place ↔ place.
- **Topology regimes for out-of-distribution tests:**
  - family depth ≤ 3 in training, 4 to 6 in test;
  - Erdős–Rényi friend graphs in training, small-world or hub-heavy in test;
  - balanced place trees in training, chain-like in test.
- **Sizes:** 10 to 30 entities for training and development, and 50, 100 and 500 for the size-shift strata (the handoff's strata, applied to worlds).
- **DSL:** typed and set-valued, with the cost of every operator counted. Programs have the form `λx. e`.
  - `{x}` turns the query entity into a set;
  - `out[R]`, `in[R]` and `closure[R]` follow relations;
  - `only[type=T]` and `only[attr=v]` filter;
  - `union`, `inter` and `minus` combine sets;
  - `count` and `exists` summarize.
- **Planted library:** about 20 to 40 hidden abstractions, some built from others, used with Zipf-skewed frequencies. For example:
  - `children = in[parent]` and `grandparents = out[parent]∘out[parent]`;
  - `siblings(S) = children(out[parent](S)) minus S`;
  - `cousins(S) = children(siblings(out[parent](S)))`;
  - `ancestors = closure[parent]`;
  - `housemates(S) = in[lives_in](out[lives_in](S)) minus S`;
  - `region = closure[inside]`.
- **Example task:** "red friends of my cousins" is `λx. only[color=red](out[friend](cousins({x})))`.

**Alternative or second domain: list functions** (the DreamCoder list domain; Rule's list-function set). They are simpler to build and closer to published baselines. Worth adding later as a replication, so that findings aren't an artifact of one domain.

### 5.4 Splits and controls

- **Seeds:** development and hidden-test seeds are disjoint, with hashes and generator versions recorded (as in the handoff).
- **Distribution shifts:**
  - size: larger worlds;
  - topology: new generators;
  - composition: held-out pairs of known abstractions;
  - novelty: an abstraction that no training task uses.
- **Controls:**
  - *No-structure stream.* Programs are sampled from the base DSL only, so the library should not help. If it does, look for leakage.
  - *Mismatched library.* Learn on stream A and test on stream B, which has a different planted library.
  - *Shuffled stream order*, with at least 3 seeds.
  - *Zipf-exponent sweep* for reuse.

### 5.5 Systems

| ID | System | What it isolates |
|---|---|---|
| S0 | Enumerative best-first search over the base DSL, pruning programs with identical outputs | The floor, with no learning |
| S0+L★ | S0 with the planted library handed to it | The best case for having a library |
| S0+L★+D | The above plus 10¹ to 10⁴ distractor entries | The utility problem, measured |
| S1 | Wake–sleep library learning: search, then compress solved programs into new entries; no guide | Can the library be learned? (DreamCoder without its recognition model) |
| S2 | Learned guide, no library | Guidance alone (DeepCoder-style) |
| S3 | Library plus a learned guide, trained on solved tasks and on "dreams" | The SAGE-0 candidate |
| S3+R | S3 plus a task cache and a cheap-first cascade | The reflex path; the handoff's C1 vs. C0 |
| T | Neural transduction: a small model predicts answers directly (TRM-style or a small transformer) | Program-free baseline (the handoff's A and B) |
| T⊕S3 | Induction plus transduction ensemble | Do they fail on different tasks? |
| ILP (optional) | Popper (Cropper & Morel 2021) on the same background relations | A strong symbolic rule learner |

**Guide design that stays cheap on a CPU:**
- **Encoder:** for each demonstration, a histogram of the labelled paths linking *x* to its answer entities, as in the Path Ranking Algorithm (Lao & Cohen 2010).
- **Model:** a small MLP that scores library entries from those histograms.
- **Training data:**
  - solved tasks;
  - "dreams": programs sampled from the current library and executed on fresh worlds, which give free training tasks. This is DreamCoder's trick, and the concrete, testable form of the handoff's "sleep".

### 5.6 Metrics

- **Correctness** on held-out queries (exact set match), broken down by shift stratum and edge-case type.
- **Cost** as counted operations, split into search, routing, verification, execution and offline work (consolidation plus guide training). CPU time and peak RSS are secondary; energy is reported only if RAPL is readable.
- **Anytime curves:** fraction solved against log(budget). Report the area under the curve rather than a result at one chosen budget.
- **Spurious-fit rate:** answers that are demo-consistent but wrong on the queries.
- **Per-entry utility:** uses × average savings − routing cost. Entries below zero are candidates for pruning, which is Minton's filter.
- **Reuse rate:** the share of new-task solutions that call entries learned from *other* tasks, plus the cost change when the library is removed at test time. This is the "library learning doesn't" check.
- **Library recovery:** the share of planted abstractions matched, up to semantic equivalence on probe worlds. It is a diagnostic, not a gate.
- **Operational and amortized cost with the break-even number of uses** (kept from the handoff).

### 5.7 Predictions to pre-register

The bracketed numbers get set together after stage 0a and before any hidden evaluation.

- **P1 (H1, H2).** On planted streams, S1 lowers median cost per correct answer by at least [x]× relative to S0. On the no-structure stream it lowers it by less than [y]%.
- **P2.** S1 recovers at least [z]% of the planted abstractions, up to equivalence.
- **P3 (H3).** Without a guide, cost against library size is U-shaped. With S3's guide it stays within [w]× from 10² to 10⁴ entries, *routing included*.
- **P4.** Programs keep at least 95% of their in-distribution accuracy on larger worlds. T degrades, and T⊕S3 scores at least as well as the better of T and S3.
- **P5.** On Zipf-skewed streams, S3+R lowers operational cost per correct answer relative to S3 and breaks even within [k] uses. On uniform streams it doesn't help.
- **P6.** At a fixed number of demonstrations, the spurious-fit rate rises with library size unless the guide's discrimination keeps pace.

### 5.8 Stages and decision gates

| Stage | Work | Learning | Gate before moving on |
|---|---|---|---|
| 0a | Worlds, DSL with operation counting, planted-library generator with split hashes, oracle, S0. Then run S0 vs. S0+L★ vs. S0+L★+D with simulated guides, i.e. the pilot on the real domain. | None | The planted library must cut cost by a large factor. If it doesn't, the tasks are too shallow; deepen them before doing anything else. |
| 0b | S1 library learning, with the controls | Symbolic | S1 beats S0 on planted streams but not on the no-structure stream, and the reuse is real. |
| 0c | S2 and S3; inflate the library to 10⁴ entries | A small neural guide | P3, with routing counted. This is the headline SAGE claim. |
| 0d | S3+R across a Zipf sweep; operational vs. amortized cost | None | P5 |
| 0e | T and T⊕S3; the shift strata | Neural | P4 |

Stages 0a to 0d are cheap on a CPU: search runs in Python or NumPy, and the guide has under 1M parameters. Stage 0e is the heaviest. Keep T small (at most about 5M parameters) and accept training runs of several hours on the i5.

---

## 6. Where each original idea goes

| Handoff idea | Where it sits in the revised plan | What earns the next step |
|---|---|---|
| Typed sparse workspace | World representation and DSL types | — |
| Router: exact → memory → program → iterative solver | A cheap-first cascade with runtime verification (S3+R), treated as a metareasoning choice | A measured break-even point |
| Program archive; C0 vs. C1 | S1 and S3 vs. S0, with per-entry utility and pruning | P1, P3 |
| Reflex compilation | The learned guide (an amortized proposer) plus the task cache | P5 |
| Sleep / offline consolidation | Wake–sleep: compression plus dreams | P1, P2 |
| Learned ISA | Learned abstractions over a fixed base DSL now; genuinely new primitives later (R01's NLI line) | Gains a fixed DSL can't reach |
| Neural interpreter (H4) | A separate track after 0e (R01, R02, CLRS) | A task where symbolic primitives are unavailable (noisy or perceptual inputs) |
| Energy-based / equilibrium solver | A candidate for T, or a search guide | Beats T at equal cost |
| Fast weights / test-time training | Rule-shift streams, where the hidden program changes mid-stream | Beats explicit session memory |
| Associative memory, superposition | A candidate retrieval index in 0c once the library reaches 10⁴ or more | Beats an ANN index on recall × cost |
| Tsetlin machines, ternary weights, BitNet | Only if the guide's inference dominates cost | Profiled, not assumed |
| Frontier teacher, evolution | An LLM as a proposal distribution: a costed ablation after 0c | Cost per correct answer, teacher tokens included |
| 1 TB cold / 16 GB active | The 0c curve: per-task cost against library size over orders of magnitude, routing included | P3 holding out to 10⁵ or 10⁶ entries |
| Language codec | Unchanged; later | — |

---

## 7. Decisions I need from you

1. **Reframe.** Do you agree to make library economics (H1 to H3) the core of experiment 0, with the neural interpreter (H4) as a later, separate track? This is the big one.
2. **Domain.** Typed relational worlds or list functions? I recommend relational worlds because they keep your domain and test rule learning. List functions are simpler to build and closer to published baselines. Either way, the other can come later as a replication.
3. **Machine.** What OS runs on the i5 (Linux, Windows or WSL), which CPU generation, and which Python version? Can you read RAPL counters (Linux with root access)? This decides whether energy is a real metric or a secondary estimate.
4. **Ambition.** Is this personal exploration, or are you aiming at a workshop paper? A paper needs the external baselines (Popper, a DreamCoder-style comparison) and more seeds.
5. **LLMs.** Should an LLM appear later as a costed proposal baseline, or stay out of the project entirely?

If you agree with 1 and 2, the next concrete step is stage 0a. That means building the package (worlds, the DSL with operation counting, the planted-library generator with split hashes, the oracle, S0 search and property tests) and rerunning the pilot's grid on the real domain.

---

## 8. References

### 8.1 Audit of the handoff's reference ledger

I checked these on 2026-09-25 through web search. arXiv pages could not be opened directly from this environment, so the checks go no deeper than titles, authors and abstracts.

| ID | Status |
|---|---|
| R01 | **Confirmed.** Macfarlane, Bonnet, van Hoof & Lelis, ICLR 2026; arXiv 2604.18907. The model learns its own primitive vocabulary with a differentiable executor and refines programs by gradient descent at test time. |
| R02 | **Confirmed.** Nerem, Chen, Dasgupta & Wang, COLT 2026, PMLR 336:5273–5331; arXiv 2503.19173. |
| R06 | **Exists, but the venue is *Communications AI & Computing*** (Nature Portfolio), not *Nature*. Ghosh & Goodman, "Partial recurrence can enable robust and efficient computation", 2026. |
| R08 | **Confirmed.** Klindt et al., "A unifying framework from neural superposition to sparse interpretable codes", *Nature Machine Intelligence* 8:1025–1037 (2026). |
| R17 | **Now located.** Guo, Qi, Gu, Cheng & Xiong, "Skill-DisCo: Distilling and Compiling Agent Traces into Reusable Procedural Skills", arXiv 2606.26669 (evaluated on ALFWorld and WebArena). The Microsoft affiliation is not confirmed. |
| R23 | **Confirmed.** Srikanth et al. (Weco AI), "Recursive self-improvement of AI research agents", arXiv 2609.26457: an eight-day run with seven accepted rewrites. |
| R24 | **Confirmed.** Chen, Wang & Qu, "Recursive Self-Improvement in AI: From Bounded Self-Refinement to Autonomous Research Loops", arXiv 2607.07663, built on a 1,250-paper corpus. |
| Others | Not re-checked. None of them is load-bearing for the revised experiment 0. |

### 8.2 Added references

★ marks references checked by web search in this session. The rest come from my own knowledge; verify them before citing any of them in a paper.

**Speed-up learning and the utility problem**
- Fikes, Hart & Nilsson (1972). Learning and executing generalized robot plans. *Artificial Intelligence* 3. (STRIPS macro-operators.)
- Korf (1985). Macro-operators: a weak method for learning. *Artificial Intelligence* 26(1).
- Laird, Rosenbloom & Newell (1986). Chunking in Soar: the anatomy of a general learning mechanism. *Machine Learning* 1(1).
- Mitchell, Keller & Kedar-Cabelli (1986). Explanation-based generalization: a unifying view. *Machine Learning* 1(1).
- Minton (1990). Quantitative results concerning the utility of explanation-based learning. *Artificial Intelligence* 42(2–3).
- Tambe, Newell & Rosenbloom (1990). The problem of expensive chunks and its solution by restricting expressiveness. *Machine Learning* 5(3).
- Anderson (1982). Acquisition of cognitive skill. *Psychological Review* 89(4). (ACT-R knowledge compilation.)

**Library learning and program synthesis**
- Balog et al. (2017). DeepCoder: learning to write programs. ICLR.
- Odena et al. (2021). BUSTLE: bottom-up program synthesis through learning-guided exploration. ICLR. Shi et al. (2022). CrossBeam: learning to search in bottom-up program synthesis. ICLR.
- Ellis et al. (2021). DreamCoder: bootstrapping inductive program synthesis with wake-sleep library learning. PLDI.
- Bowers et al. (2023). Top-down synthesis for library learning (Stitch). POPL.
- Grand et al. (2024). LILO: learning interpretable libraries by compressing and documenting code. ICLR.
- ★ Berlot-Attwell, Rudzicz & Si (2024). Library learning doesn't: the curious case of the single-use "library". NeurIPS MATH-AI workshop; arXiv 2410.20274.
- ★ LLM library learning fails: a LEGO-Prover case study (2025). arXiv 2504.03048.
- ★ Li et al. (2024). Combining induction and transduction for abstract reasoning. arXiv 2411.02272.
- Cropper & Morel (2021). Learning programs by learning from failures (Popper). *Machine Learning* 110.
- Lao & Cohen (2010). Relational retrieval using a combination of path-constrained random walks. *Machine Learning* 81.
- Rule (2020). *The child as hacker: building more human-like models of learning.* PhD thesis, MIT. (Source of the list-function tasks.)

**Skill libraries in agents: the utility problem, 2023 to 2026**
- Wang et al. (2023). Voyager: an open-ended embodied agent with large language models. arXiv 2305.16291.
- ★ Song & Wei (2026). More skills, worse agents? Skill shadowing degrades performance when expanding skill libraries. arXiv 2605.24050.
- ★ Kolluru & Sportsman (2026). Comparative approaches to agent retrieval over large skill libraries. arXiv 2608.06196.

**Small active compute, large memory**
- Shazeer et al. (2017). Outrageously large neural networks: the sparsely-gated mixture-of-experts layer. ICLR.
- Lample et al. (2019). Large memory layers with product keys. NeurIPS.
- ★ Berges et al. (2024). Memory layers at scale. arXiv 2412.09764.
- Borgeaud et al. (2022). Improving language models by retrieving from trillions of tokens (RETRO). ICML.
- Alizadeh et al. (2024). LLM in a flash: efficient large language model inference with limited memory. ACL.

**Small recursive reasoners and neural algorithmic reasoning (H4 and system T)**
- Xu et al. (2020). What can neural networks reason about? ICLR. Xu et al. (2021). How neural networks extrapolate: from feedforward to graph neural networks. ICLR.
- Schwarzschild et al. (2021). Can you learn an algorithm? Generalizing from easy to hard problems with recurrent networks. NeurIPS. Bansal et al. (2022). End-to-end algorithm synthesis with recurrent networks: logical extrapolation without overthinking. NeurIPS.
- Veličković et al. (2022). The CLRS algorithmic reasoning benchmark. ICML.
- ★ Wang et al. (2025). Hierarchical Reasoning Model. arXiv 2506.21734.
- ★ Jolicoeur-Martineau (2025). Less is more: recursive reasoning with tiny networks (TRM: 7M parameters, 45% on ARC-AGI-1, 8% on ARC-AGI-2). arXiv 2510.04871.

**Routing, amortization, consolidation and measurement**
- Russell & Wefald (1991). *Do the Right Thing: Studies in Limited Rationality.* MIT Press.
- Gershman & Goodman (2014). Amortized inference in probabilistic reasoning. CogSci.
- Chen, Zaharia & Zou (2023). FrugalGPT: how to use large language models while reducing cost and improving performance. arXiv 2305.05176.
- McClelland, McNaughton & O'Reilly (1995). Why there are complementary learning systems in the hippocampus and neocortex. *Psychological Review* 102(3). Kumaran, Hassabis & McClelland (2016). What learning systems do intelligent agents need? *Trends in Cognitive Sciences* 20(7).
- Chollet (2019). On the measure of intelligence. arXiv 1911.01547. (Defines intelligence as skill-acquisition efficiency: a good long-run frame for SAGE's "capability per unit of compute".)
- Lipp et al. (2021). PLATYPUS: software-based power side-channel attacks on x86. IEEE S&P. (This is why RAPL energy counters are root-only on Linux.)
