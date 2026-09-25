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
