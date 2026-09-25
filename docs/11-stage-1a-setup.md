# Stage 1a setup: status and how to run the model

**Date:** 2026-09-25 · **Pre-registration:** [`10-stage-1a-preregistration.md`](10-stage-1a-preregistration.md)

## Status

Everything for stage 1a is built and tested except the model run itself:
- the workload,
- the systems,
- the memory,
- the classical baseline,
- the harness and reports.

The model can't be downloaded here, because this cloud environment's network policy denies `huggingface.co`. The run can go ahead either here, once that host is allowed, or on the author's own computer. Both are described below.

Nothing has been run on the registered streams, and their manifests have not been generated. The prompts and model settings are still open for tuning on the development streams.

## What is built

| Part | File | What it does |
|---|---|---|
| Workload | `src/sage/wrangle/transforms.py`, `requests.py` | 50 transformation types, each with a realistic input generator and a hidden reference implementation. Requests of 3 examples and 5 queries; Zipf and no-recurrence streams; hashed manifests. |
| Sandbox | `src/sage/wrangle/sandbox.py` | Runs generated functions with a whitelist of built-ins, only the `re`, `datetime`, `math`, `string` and `calendar` modules, and a time limit. |
| Model | `src/sage/wrangle/llm.py` | The two prompts (write a function; answer directly as a JSON list) and the reply parsers. Three backends: llama.cpp in-process (the registered setting), a local Ollama server, and a scripted stand-in for tests. All tunable settings live in `ModelConfig` and `PROMPT_VERSION`. |
| Systems | `src/sage/wrangle/systems.py` | D, B and E, one request at a time. S, E+M and S+ are replayed over a stream from those records, as in stage 0d. |
| Memory | `src/sage/wrangle/memory.py` | Verified functions with trust counts. Lookup checks every stored function against the request's examples, in order of trust, then recent use. |
| Classical search | `src/sage/wrangle/synth.py` | E: an autofill-style synthesizer over fields, slices, case changes and constants. It returns the simplest consistent program, preferring more general parts. |
| Harness | `experiments/stage1a.py` | Phases `generate`, `solve`, `report` and `final`. See the top of the file. |
| Tests | `tests/test_wrangle.py` | 19 tests (58 in the whole suite). |

## Checked here without the model

- **Dry run of the whole pipeline.** A stand-in "fake model" answered the program prompts with the classical synthesizer and the direct prompts with the unchanged inputs. This exercised per-request records, the memory replays, the development report and the final report with W1–W4.
- **The llama.cpp code path.**
  - A tiny random-weight model was written locally as a test fixture.
  - It checked:
    - loading and the model's chat template;
    - prompt and generated token counts;
    - greedy decoding is deterministic;
    - sampling with the same seed reproduces;
    - CPU time includes llama.cpp's inference threads;
    - B's three attempts followed by the direct fallback.
  - It also checked that the harness:
    - resumes an interrupted run;
    - refuses to resume one with different settings or on another machine;
    - refuses the registered streams before `generate`.

## Classical search on the development streams (no model)

| Stream | Requests (types) | E correct | E CPU per request | E+M answered from memory | Precision of those answers |
|---|---:|---:|---:|---:|---:|
| `1a-dev` | 100 (30) | 66% | about 3 ms | 51% | 98% |
| `1a-dev-types` | 50 (50) | 64% | about 4 ms | 8% | 3 of 4 |

- **Where E succeeds:** outputs assembled from pieces of the input: names, e-mail parts, phone formats, reordered numeric dates, file names, SKUs.
- **Where E fails:** outputs that need knowledge or arithmetic. These are the 18 types where the model has to earn its cost:
  - month names, weekdays and quarters;
  - money formatting, rounding, percentages and compact numbers;
  - hex to RGB;
  - camelCase and snake_case conversion;
  - reversing or counting words;
  - URL parts;
  - 12-hour times;
  - company names from e-mail addresses;
  - hashtags.
- **Transfer across types.** On `1a-dev-types` every type occurs once, yet memory answered 4 requests with functions stored for *other* types:
  - "the last word" learned for ZIP codes answered last names correctly;
  - "the digits" learned for phone numbers answered SKU numbers correctly;
  - "the last path part" learned for file paths answered years in dates correctly;
  - "the last three characters" learned for SKU colours answered file extensions wrongly.

  A store of verified procedures is reused beyond the task it was learned for. The same mechanism is also a source of confident errors.

## Running the model stage

The pre-registration fixes the model: **Qwen2.5-Coder-1.5B-Instruct, Q4_K_M GGUF** (about 1.1 GB), run on the CPU with llama.cpp.

Every stage 1a run must be on **one machine**, because CPU time is the cost measure. The harness writes the machine into every results file and refuses to resume a run on a different one.

### Where

- **Here, in this cloud environment.** Allow `huggingface.co` in the environment's Network access settings. Its downloads may also redirect to hosts under `hf.co`, which then need allowing too. Then ask Claude to continue.
- **On your own computer.** You need Python 3.10 or newer, about 2 GB of free disk, and either a C/C++ compiler or a prebuilt llama-cpp-python wheel.

### Steps

1. **Setup** (on Windows, set `PYTHONPATH=src` in the shell instead of prefixing each command):

   ```sh
   git clone https://github.com/ayeshrodz/sage && cd sage && git checkout claude/openai-research-analysis-17ru8g
   python -m pip install numpy llama-cpp-python
   # if that fails to build: python -m pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu
   mkdir -p models
   curl -L -o models/qwen2.5-coder-1.5b-instruct-q4_k_m.gguf \
     https://huggingface.co/Qwen/Qwen2.5-Coder-1.5B-Instruct-GGUF/resolve/main/qwen2.5-coder-1.5b-instruct-q4_k_m.gguf
   PYTHONPATH=src python -m unittest discover -s tests
   ```

2. **Development, free to repeat.** Every type once, then the 100-request recurring stream:

   ```sh
   PYTHONPATH=src python experiments/stage1a.py solve --system B --stream dev-types
   PYTHONPATH=src python experiments/stage1a.py solve --system D --stream dev-types
   PYTHONPATH=src python experiments/stage1a.py report --stream dev-types
   PYTHONPATH=src python experiments/stage1a.py solve --system B --stream dev
   PYTHONPATH=src python experiments/stage1a.py solve --system D --stream dev
   PYTHONPATH=src python experiments/stage1a.py report --stream dev
   ```

   - **What may be tuned:** only what the pre-registration allows:
     - the prompts in `llm.py` (raise `PROMPT_VERSION` when they change);
     - `CONFIG` in `experiments/stage1a.py`: attempts, temperature and token limits;
     - the thread count, `--threads`.
   - **Re-running:** add `--restart` to rerun a system on a stream after a change.
   - **What to watch in the report:**
     - B's model-call diagnostics: the attempt at which a function was accepted, fallbacks, and replies with no function or with one that doesn't fit;
     - S's hit rate and hit precision on `dev`;
     - D against B.

3. **Freeze.** Add Amendment 1 to the pre-registration with the final prompt version, `CONFIG`, thread count, backend and the development results. Commit and push it.

4. **Generate** the registered streams once, then commit `reports/stage1a/manifests.json`:

   ```sh
   PYTHONPATH=src python experiments/stage1a.py generate
   ```

5. **Registered runs, once each.** If a run is interrupted, the same command resumes it.

   ```sh
   for s in zipf norecur; do
     for sys in E B D; do PYTHONPATH=src python experiments/stage1a.py solve --system $sys --stream $s; done
   done
   PYTHONPATH=src python experiments/stage1a.py final
   ```

### How long

- **Per call:** a guess for a 4-core CPU is 5–20 seconds per model call. B makes 1 to 4 calls per request (3 attempts at most, plus the direct fallback); D makes one.
- **Totals:** 350 registered requests for each of B and D should take roughly 2–5 hours in all; the development streams add about half that again.
- **Check on dev:** the development runs print the real speed, so check it there first.

### Ollama instead of llama-cpp-python

If llama-cpp-python won't install:
1. Install [Ollama](https://ollama.com) and run `ollama pull qwen2.5-coder:1.5b`. This is the same model, also 4-bit.
2. Run `python -m pip install psutil`, so the Ollama server's CPU time is counted.
3. Add `--backend ollama` to the `solve` commands.

The registration names llama.cpp in-process, so using Ollama for the registered runs has to be recorded in Amendment 1.
