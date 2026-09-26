# Stage 1a pre-registration: a real workload with a small language model

**Registered:** 2026-09-25, before any stage 1a code existed and before any stage 1a stream was generated.  
**Agreed by:** the project author asked for this stage on 2026-09-25 ("set up the real workload stage with the small LLM"). The criteria and thresholds below were set by the reviewer, with the reasoning given, and the author may revise them before the model run.

## Question

Stage 0d showed that a memory of verified programs makes recognized recurring tasks about 1,000× cheaper and more accurate than solving them again, but only in a synthetic world. Stage 1a asks the same question the way it would be asked in deployment:

> On a realistic stream of recurring, checkable requests, what share can be answered locally from verified memory instead of calling a language model, at what cost, and with what accuracy, compared with calling the model on every request?

## Workload: data-wrangling requests by example

Each request shows **3 input → output examples** of a text transformation and asks for the same transformation on **5 new inputs**. This is the everyday "fill in the rest of this column" task that spreadsheet autofill handles.

There are 50 transformation types in the areas people clean data in: names, email addresses, phone numbers, dates, money and numbers, URLs and file paths, postal addresses, product codes, free text and times. Examples:
- "Mary Chen" → "M.C.";
- "2024-03-15" → "March 15, 2024";
- "$1,234.50" → "1234.50";
- "orderTotalAmount" → "order_total_amount".

Inputs come from varied, realistic generators: names from many cultures, several email domains, dates from 1990 to 2030, and so on. Each type's gold outputs come from a reference implementation that no system sees.

- **Correct request:** all 5 outputs exactly match the gold outputs. Per-output accuracy is also reported.
- **`1a-dev`:** used freely for development.
- **`1a-zipf`:** 300 requests over the 50 types. Type k (in a random ranking) occurs with probability ∝ 1/k, so common types recur as fresh requests with new data.
- **`1a-norecur`:** 50 requests, each type once.

The registered streams are generated once, after the code is frozen, with hashed manifests. They are processed with the model once.

## Model

**Qwen2.5-Coder-1.5B-Instruct**, 4-bit GGUF (Q4_K_M), run on the CPU through llama.cpp (llama-cpp-python) using all cores. If this exact model cannot be obtained, a substitute of similar size is named in an amendment before the model run.

## Systems

- **D, direct answers:** the model is shown the examples and the new inputs and writes the 5 outputs. One call per request.
- **B, the model every time (the deployment baseline):**
  - The model writes a Python function from the examples, with up to 3 attempts (the first greedy, then sampled).
  - A function is accepted only if it reproduces all 3 examples, and it then answers the 5 inputs.
  - If no attempt is accepted, B falls back to a direct answer.
- **S, SAGE memory in front of the model:**
  - Every accepted function is stored with a trust count.
  - For a new request, stored functions are checked against the request's 3 examples, in order of trust and then recent use.
  - The first that reproduces them all answers locally, with no model call.
  - Otherwise S runs exactly B's procedure on that request and stores the accepted function, if any.
  - Because the miss path is B's own run on the same request (fixed seeds), S and B are paired request by request, as in stage 0d.
- **E and E+M, classical search without any model:** an enumerative program synthesizer over a small string language (fields, slices, case changes, constants and concatenation, in the style of spreadsheet autofill), without and with the same memory. It runs today in this environment and is the no-model reference.
- **S+ (secondary, pre-declared): the cheapest reliable path first.** Memory, then classical search, then the model.

**Sandbox.** Generated functions run with restricted built-ins and only the `re`, `datetime`, `math`, `string` and `calendar` modules, under a time limit. This is adequate for synthetic data; it is not a security boundary for real data.

## Cost

- **Primary:** compute time in seconds on the evaluation machine, measured as the CPU time of the evaluating process. The model runs in-process, so its inference threads are included.
- **Also reported:** model calls, prompt and generated tokens, and an estimate of model arithmetic (2 × parameters × tokens).
- All local work is included: verification, execution and search.

## Pre-registered criteria

- **W1, local answering.** S answers **at least 50%** of `1a-zipf` requests from memory, without calling the model.
- **W2, cost.** B's compute time per correct request divided by S's is **at least 2×** on `1a-zipf`.
- **W3, accuracy.** S's request accuracy on `1a-zipf` is **at most 2 points below** B's.
- **W4, overhead.** On `1a-norecur`, S's total compute time is **at most 1.05×** B's.

### Reasoning

- **W1:** answering most requests locally is the deployment claim itself. It can only pass if the model writes *general* functions for the common types, so it also tests the "reliable first solution" weakness found in stage 0d.
- **W2:** halving the cost of serving the same requests is meaningful to anyone deploying a model. Misses cost exactly what B costs, so W2 mostly follows from W1 at equal accuracy.
- **W3:** "no loss of accuracy", within 2 points.
- **W4:** recognition must be nearly free when nothing recurs.

## Development and freezing

- **Tunable on `1a-dev` only:** the prompts, the number of attempts, the sampling temperature and the token limits.
- **Frozen by amendment:** the final settings are recorded in an amendment, and committed, before the registered streams are processed with the model.
- **Classical search:** E's settings are fixed in code before the streams are generated.

## Also reported, without thresholds

- D, E, E+M and S+ on both streams.
- Model calls avoided.
- Accuracy and cost per type.
- Hit precision by trust.
- The learning curve over the stream (windows of 50 requests).
- The break-even number of requests.

## Amendment 1 (2026-09-26, before `1a-zipf` and `1a-norecur` were generated)

**Nothing registered changes.** The workload, the systems, the criteria W1–W4 and their thresholds stand as written. This amendment:
- freezes the settings that were tunable on the development streams;
- records how they were chosen;
- adds two comparisons, without thresholds.

### Model and machine

- **Model:** `qwen2.5-coder-1.5b-instruct-q4_k_m.gguf`, from `Qwen/Qwen2.5-Coder-1.5B-Instruct-GGUF` on Hugging Face, where the file was last changed in commit `2ab9f8f4`.
  - It is 1,117,320,768 bytes, with SHA-256 `cc324af070c2ecbfd324a30884d2f951a7ff756aba85cb811a6ec436933bb046`, which matches Hugging Face's listing.
  - It was downloaded with the `hf` tool from PyPI, after the author allowed Hugging Face in the environment's network settings for the download.
- **Runtime:** llama-cpp-python 0.3.35, in-process, 4 threads (all logical cores), a context of 4,096 tokens.
- **Machine:** this cloud container, an Intel Xeon at 2.10 GHz with 4 logical cores. All registered runs happen on it; the harness refuses to resume a run on another processor.

### Frozen settings

- **Prompts:** `1a-p1`, as registered. The texts are in `src/sage/wrangle/llm.py`, unchanged since `5451376`.
- **B's attempts:** 7 program attempts. The first is greedy; the rest are sampled at temperature **1.0** with llama-cpp-python's defaults (top-k 40, top-p 0.95, min-p 0.05). The registered starting point was 3 attempts at 0.7.
- **Token limits:** 384 for a function, 256 for a direct answer. Replies average 31–40 tokens; 1 of 750 sampled replies reached the limit.
- **E:** unchanged since `5451376`.
- **Where they are set:** `CONFIG` in `experiments/stage1a.py`. Each results file records all of these in its header.

### How the settings were chosen (development streams only)

1. **Baseline** with the registered starting settings (`reports/stage1a/dev/baseline-p1/`):
   - B found a function that fits the examples for only 19 of the 50 types on `1a-dev-types`. 102 of its 121 program attempts produced a function that didn't fit, even for trivial types whose direct answers were right.
   - On `1a-dev`:
     - D was correct on 78% of requests, at 15.8 CPU s per correct request;
     - B was correct on 68%, at 33.7 s;
     - S was correct on 73%, at 25.3 s, answering 40% from memory, all correctly.
2. **Prompt variants** (`reports/stage1a/dev/tuning/tune_prompts.*`):
   - The variants were: a clearer input/output layout with a one-sentence rule stated first; the same with a worked example; the same with retries that show the model where its function failed; and both together.
   - They found functions for 20, 17, 15 and 16 types, against the baseline's 19. Each cost more.
   - `1a-p1` stays.
3. **Attempts and temperature** (`reports/stage1a/dev/tuning/tune_attempts.*`):
   - Which types got a function varied from run to run: 29 types got one in at least one variant, but only 2 in all of them. Sampling, not wording, decides.
   - With 1–8 attempts, the numbers of types with a fitting function were:

     | Attempts | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
     |---|---:|---:|---:|---:|---:|---:|---:|---:|
     | Temperature 0.7 | 12 | 17 | 19 | 22 | 25 | 27 | 28 | 29 |
     | Temperature 1.0 | 12 | 15 | 17 | 22 | 25 | 28 | 29 | 32 |

   - About 92% of the fitting functions were also correct on new inputs.
   - The selection rule was written down before this curve was computed (`tuning/attempts_rule.txt`):
     - take the temperature with more functions at 8 attempts;
     - then take the fewest attempts that reach at least 90% of that number.
   - The rule gives temperature 1.0 and 7 attempts: 29 types, against the 28.8 required.
4. **Development results with the frozen settings** (`reports/stage1a/dev/summary_*.md`). D's records are from the baseline run: it doesn't use B's settings.

   | `1a-dev`: 100 requests, 30 types | Correct | Answered from memory | CPU per correct request |
   |---|---:|---:|---:|
   | D | 78% | — | 15.8 s |
   | B | 71% | — | 54.1 s |
   | S | 77% | 44% (98% of those correct) | 38.5 s |
   | E | 66% | — | 5 ms |
   | S+ | 81% | 55% (96% of those correct) | 25.6 s |

   - **On `1a-dev-types`** (every type once), B is correct on 76% of requests, against 72% at baseline; S gets 1 hit and has a total CPU ratio of 0.99 to B.
   - **Expectation, stated before the registered run:**
     - W3 and W4 should pass.
     - W1 is near its threshold: 44% on `1a-dev`, where 30% of requests are a type's first occurrence; about 15% will be on `1a-zipf`.
     - W2 is likely to fail: 1.4× on `1a-dev`.
     - With 7 attempts, S will probably cost more per correct request than D.

### Added comparisons, without thresholds

- **S against D and S+ against D.** On the development streams, answering directly (D) is both more accurate and cheaper than program induction (B), so for this model D, not B, is the strongest system without memory. W1–W4 still compare S with B, as registered. But the results will also say plainly whether memory beats simply asking the model: cost per correct request, accuracy and total CPU time, against D, on both streams.
- **Fewer program attempts.** From B's own records, B, S and S+ are replayed with at most 1 to 7 attempts, with their accuracy, CPU per correct request and share answered from memory, and S and S+ against D.
  - This is valid because B stops at its first fitting function and its seeds depend only on the request and the attempt, so with fewer attempts it makes the same first calls.
  - Where B would then fall back to a direct answer it never gave, the answer and its cost are D's on the same request: the same prompt with greedy decoding.
  - Every model call's CPU time is recorded for this (`systems.py`, added now).
  - This shows the trade-off the development streams exposed. More attempts put more types into memory, but every miss then costs more: on `1a-dev`, S+ is 1.6× cheaper per correct request than D with 1 attempt, and 1.7× dearer with 7.
