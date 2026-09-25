# Stage 0d results: reuse on recurring tasks

**Date:** 2026-09-25 · **Code:** frozen at `dc9f2a6`. Streams generated once at that code; memoryless solves at `10fc6f7`, which adds only the stream manifests. **Pre-registration:** [`08-stage-0d-preregistration.md`](08-stage-0d-preregistration.md), including amendment 1. **Report:** [`reports/stage0d.md`](../reports/stage0d.md); per-instance results in `reports/stage0d/`; the labelled exploratory breakdown in `reports/stage0d/exploratory_repeats.json`.

## Verdict on the pre-registered criteria

R3 against S3, mean of the 3 seeds.

| Criterion | Value | Threshold | Result |
|---|---:|---:|---|
| **P1d** S3 ÷ R3 mean work on recurring, already-solved types | 2.7× | ≥ 10× | **FAIL** |
| **P2d** R3 − S3 correct rate on the Zipf stream | **+14.2 points** | ≥ −3 points | **PASS** |
| **P3d** R3 ÷ S3 total work when nothing recurs | 0.988 | ≤ 1.05 | **PASS** |
| **P4d** S3 ÷ R3 work per correct answer on the Zipf stream | 2.3× | ≥ 2× | **PASS** |

## What happened

Zipf stream: 1,000 instances of 156 distinct types.

| Seed | Correct: S3 → R3 | Work per correct answer: S3 → R3 | Hits | Hits correct | Median work of a hit |
|---|---:|---:|---:|---:|---:|
| 0 | 38.6% → **47.8%** | 3.66M → **2.14M** | 414 | 90% | 736 |
| 1 | 23.3% → **33.0%** | 7.64M → **4.29M** | 312 | 85% | 714 |
| 2 | 27.9% → **51.7%** | 6.86M → **2.08M** | 479 | 88% | 676 |

- **Learning curve.** R3's mean work per task falls from 1.35M in the first 100 instances to about 1.0–1.1M in the last 300. S3 stays flat at about 1.7M.
- **Nothing recurs.** On the no-recurrence stream, memory changes total work by −1% to −2% with identical accuracy.
- **Memory without a library.** R0 against S0 gains only 1.1×. S0 finds a program for just 9.6% of the stream, and fewer than half of its reused programs are correct.
- **Learning included.** Adding each seed's full stage 0c learning cost, the whole system (R3) needs 2.0×, 1.0× and 1.7× less work per correct answer than S0 over this 1,000-task stream. It breaks even after **326, 960 and 465 tasks**.

## Findings

1. **When memory recognizes a recurring task, it is roughly a thousand times cheaper and much more accurate than thinking again.** *Exploratory.*
   - On later instances of already-solved types, a hit costs about 1,000 operations against S3's 1.1–1.9M mean; the median ratio is 800–2,100×.
   - Hits are correct 85–91% of the time; a fresh search on the *same* instances is correct 37–68% of the time.
   - A program that has fitted several instances is more trustworthy than one fitted to a single instance: hits made with programs of trust 5 or more are correct 88–95% of the time.
   - This is the SAGE progression working as intended: *effortful solution → stored procedure → cheap and reliable reuse*.
2. **Memory makes the whole stream cheaper and more accurate, and costs nothing when it doesn't help.** Accuracy rises by 14 points, work per correct answer halves, and there's no overhead without recurrence.
3. **Roughly 30% of recurrences are not recognized, and they account for almost all of the remaining cost.** 26–38% of later instances of solved types miss, and each miss pays a full search (1.4–2.1M). Misses are 99.8% of R3's work on recurring types, which is why the registered mean-based P1d ratio is 2.7× even though the typical hit saves about 1,000×. There are two causes:
   - **Unreliable first solutions (about 80% of misses).** The program stored for a type was an over-specific fit to its own instance's demonstrations, and it doesn't fit the next instance. This is the ambiguity problem of 0a–0c, now exposed by memory. On the dev stream, a consolidating memory that re-searched with the old and new evidence together failed: the true procedure was out of the search's reach (amendment 1).
   - **Recognition at scale (about 20% of misses).** The right program was in memory, but the coarse key (answer entity types) and the 50-check cap didn't reach it once memory held 126–159 programs. This is the utility problem in retrieval: the cold store only works if recognition stays sharp as it grows.
4. **Memory is only as good as the solutions it stores.** Without a library, S0 rarely finds real solutions, so its memory mostly stores over-specific ones (43% of its hits are correct). Reuse multiplies the value of a good solver; it doesn't replace one.
5. **With reuse, the whole system's learning starts to pay for itself.** In stage 0c, learning never paid back within 1,000 tasks. On a recurring stream with memory, it pays back within about 330–960 tasks. The comparison baseline S0 is weak on this stream (2.7% correct), so read these ratios as "the system learns something S0 can't" rather than as a pure efficiency figure.

## What this means for SAGE

Stage 0d is the first direct evidence for the central intuition: **once a procedure is stored, recurring problems become cheap, and stored procedures that have been verified again and again become more reliable than fresh reasoning.** The remaining gap is not in reuse itself but in the two things around it:
- producing *general* solutions in the first place;
- *recognizing* a stored solution cheaply as memory grows.

The second is the same routing problem that 0c exposed at the level of individual skills, now at the level of whole programs. It is the question the 1 TB cold-store vision depends on.

## Options for the next step

1. **Recognition at scale (my recommendation).** Inflate memory from about 150 to 10³–10⁵ stored programs (distractors from other task families) and measure recall and lookup cost. Then design a cheap index that keeps both flat, for example keys from a few cheap, instance-invariant features of the demonstrations, or a learned hash. This tests the core scaling claim directly, it is where the 30% of misses from lookup failures come from, and it is the program-level version of 0c's unsolved routing problem.
2. **Reliable first solutions.** Make the stored solution general, not just consistent with its instance. One way is to keep a few demo-consistent candidates and check which of them agree on *self-generated* probe queries in the same worlds, storing only programs without competitors. Another is to promote a program to "trusted" only after it has fitted two instances. This targets the larger share of misses and should also raise accuracy.
3. **Online consolidation.** Periodically compress the memory's verified programs into library entries: sleep over experience rather than over a fixed training set. This is the lifelong version of the SAGE loop, and a natural later stage.
