# Stage 1a results: a real workload with a small language model

**Date:** 2026-09-26 · **Code:** frozen by amendment 1 at `fe9d1f4`. The registered streams were generated at `b8d9310` and run once each on this cloud container (Intel Xeon, 2.10 GHz, 4 logical cores). Later commits only add report files. **Pre-registration:** [`10-stage-1a-preregistration.md`](10-stage-1a-preregistration.md), including amendment 1. **Report:** [`reports/stage1a.md`](../reports/stage1a.md). Per-request records, including every model reply, are in `reports/stage1a/`.

## Verdict on the pre-registered criteria

S (a memory of verified functions in front of the model) against B (the model every time), as registered.

| Criterion | Value | Threshold | Result |
|---|---:|---:|---|
| **W1** share of `1a-zipf` answered from memory | **73.7%** | ≥ 50% | **PASS** |
| **W2** B ÷ S CPU time per correct request (`1a-zipf`) | **2.9×** | ≥ 2× | **PASS** |
| **W3** S − B request accuracy (`1a-zipf`) | **+3.3 points** | ≥ −2 points | **PASS** |
| **W4** S ÷ B total CPU time (`1a-norecur`) | **0.986** | ≤ 1.05 | **PASS** |

## What happened

`1a-zipf` has 300 requests of 43 types. Requests are correct only if all 5 outputs are exactly right.

| System | Correct requests | From memory | Model calls | CPU per correct request |
|---|---:|---:|---:|---:|
| D: the model answers directly | 71.3% | — | 300 | 20.3 s |
| B: the model writes a function (up to 7 attempts), else answers directly | 88.3% | — | 1,328 | 42.4 s |
| **S: memory, then B** | **91.7%** | **73.7%** | 459 | **14.4 s** |
| E: classical search, no model | 76.3% | — | 0 | 5 ms |
| E+M: memory, then E | 76.3% | 68.0% | 0 | 2 ms |
| **S+: memory, then E, then B** | **93.3%** | **77.7%** | 280 | **9.1 s** |

- **Memory answers.** 221 requests were answered from memory, with a median of 41 µs of CPU each. A request that goes to B costs 37 s on average. 98.2% of the memory's answers were correct.
- **Memory size.** At the end, memory held 33 functions.
- **Learning curve.** S's CPU per request fell from 22.8 s over the first 50 requests to about 5 s in the windows where 88–90% of requests hit memory.
- **Nothing recurs.** On `1a-norecur` memory changes almost nothing: the total CPU ratio is 0.986, with the same accuracy.
- **Against D** (added by amendment 1, without thresholds):
  - S is **1.4×** cheaper per correct request and **20.3 points** more accurate. S+ is **2.2×** cheaper and **22.0 points** more accurate.
  - S also uses 8% less CPU in total, and S+ 41% less.
  - Without recurrence it's the other way round: S uses 3.0× the CPU of D and S+ 1.4×, though they are 8 and 14 points more accurate.

## Findings

1. **Verified functions are more reliable than the model's own answers.**
   - The model answering directly got 71% of requests right. With memory, 92–93% were right.
   - The gap is largest where the model makes small instance-level slips that a function doesn't:

     | Type | D, answering directly | S, with memory |
     |---|---:|---:|
     | `reverse_words`: D gets the word order wrong | 4% | 100% |
     | `name_titlecase`: D writes "OscaR", or drops a letter ("Than" for "Ethan") | 10% | 100% |
     | `first_name`: D keeps a middle name | 43% | 100% |

   - Trust tracks reliability, as in stage 0d. A function's trust is the number of requests it has answered. Hits made with functions of trust 1 were correct 88.5% of the time, trust 2–4 97.8%, and trust 5 or more **100%** (150 hits).
   - Stage 0d's result now holds on real data with a real model: a procedure verified again and again becomes more reliable than fresh reasoning.
2. **On this workload, memory also makes the model cheaper to use than asking it directly.**
   - S+ is correct on 93% of requests at less than half D's CPU per correct request. S+ makes 280 model calls, against D's 300.
   - Most of the cost is paid once per type: 7 model attempts buy a function that is then reused hundreds of times for microseconds each.
3. **The saving depends on the workload: how much recurs, and whether the model can write a function for the frequent types.**
   - **Break-even rule.** S uses less CPU than D when its hit rate *h* exceeds 1 − (D's cost per request ÷ S's cost per miss).
   - **On this stream:**
     - a request to D costs 14.5 s;
     - an S miss costs 50.3 s with 7 attempts, so S needs to answer more than **71%** of requests from memory; it answered 73.7%;
     - an S miss costs 21.5 s with 1 attempt, so the threshold is **33%**.
   - **On the development stream** the mix was worse, and S cost 2.4× more per correct request than D:
     - only 70% of its requests repeated an earlier type, against 86% here;
     - 28% were of types the model never wrote a working function for, against 12% here;
     - S answered only 44% from memory.
   - One Zipf draw is one workload. Read these ratios as "what memory does on a workload like this", not as a constant.
4. **The small model's weak point is writing the procedure, not reusing it.**
   - Of its 1,239 program attempts on `1a-zipf`, 1,021 produced a function that didn't fit the examples.
   - Functions were accepted at attempts 1–7 on 63, 43, 32, 31, 16, 15 and 11 requests, and 89 requests fell back to a direct answer.
   - Prompt wording didn't help during tuning; sampling more did.
   - **Memory's 4 wrong answers** all came from over-specific functions of trust 1–2, fitted to three examples that missed an edge case:
     - "19813.5" instead of "19813.50" (the examples had no trailing zero);
     - "0:46 AM" instead of "12:46 AM" (the examples had no time after midnight).
   - This is stage 0d's "unreliable first solution", now in a real model.
5. **Fewer attempts are more economical.** This is the secondary analysis, replayed from B's records (on `1a-zipf`):

   | Attempts | S correct | S CPU per correct | S+ correct | S+ CPU per correct | D ÷ S+ |
   |---|---:|---:|---:|---:|---:|
   | 1 | 88.0% | 9.8 s | 91.0% | 3.9 s | 5.2× |
   | 7 (registered) | 91.7% | 14.4 s | 93.3% | 9.1 s | 2.2× |

   The rule in amendment 1 chose 7 attempts to maximize the number of types with a function. That buys 2–4 points of accuracy at 1.5–2.4× the cost per correct request.
6. **My expectation was wrong.** Before the run I expected W2 to fail and S to cost more than D per correct request. I based that on the development stream, whose mix of frequent types turned out to be much less favourable (finding 3).

## What this means for SAGE

This is the first evidence on a real workload, with a real model, that the SAGE loop works end to end:
1. an effortful solution: up to 7 model attempts, each checked against the examples;
2. a stored, verified procedure;
3. cheap, reliable reuse, taking microseconds instead of seconds and more accurate than the model itself.

A 1.5B model with a memory of 33 small functions was 20–22 points more accurate than the model alone, and used less CPU per correct answer, on a CPU-only machine.

The limits are just as clear:
- **Recurrence.** The benefit exists only where requests recur. Without recurrence, memory costs nothing extra against B, but B itself costs 3× more than asking the model directly.
- **Acquisition.** The bottleneck is getting a general procedure in the first place. The small model rarely writes one, and three examples can't expose every edge case.
- **Scale.** Memory held only 33 functions. Recognition at scale, stage 0d's first option, is still untested on real data.

## Options for the next step

1. **A teacher writes, a student serves (my recommendation).** On a miss, a stronger model writes the function: a local 7B model, or a frontier model used rarely. The small model and memory serve everything else. Measure accuracy and total cost, *including* the teacher's. This tests the project's central aim directly: capturing expensive capability as procedures a consumer CPU can run. It also attacks both weak points found here, acquisition cost and over-specific functions.
2. **Reliable first solutions.** Check generality before a function is stored or trusted: probe inputs the system generates itself, or at least two fitted requests before a function serves an answer (trust ≥ 2 was 97.8% precise, trust 1 88.5%).
3. **Larger and more realistic workloads.** Use hundreds of types, real spreadsheet columns and real request logs, with recognition at scale (10³–10⁵ stored functions).
4. **Energy on consumer hardware.** Run D, S and S+ on the author's i5 and measure joules per correct answer. That is the deployment measure the project ultimately cares about.
