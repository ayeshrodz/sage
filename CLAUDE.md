# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

SAGE is a research project, not a product. It asks whether capability can grow with *stored*, verified procedures while the compute spent per task stays small. The long-run aim is frontier-level capability on consumer CPUs.

Work proceeds in pre-registered stages, documented in order in `docs/`:
- `docs/02-objective-and-decisions.md` holds the author's objective and the decision log.
- Read the latest results before proposing work. Currently that is `docs/12-stage-1a-results.md`, whose "Options for the next step" recommends stage 1b: a stronger teacher model writes functions when memory misses, and the small local model and memory serve the rest.
- **Open decision for stage 1b:** the author still has to choose the teacher: a frontier API, a local 7B model, or both. API keys belong in environment variables.

## Commands

- Python 3.10 or newer. There is no build step, and no linter or formatter is configured.
- Code is imported with `PYTHONPATH=src`; the package isn't installed.
- On the author's machine, the dependencies (numpy, llama-cpp-python, huggingface_hub) are in `.venv`.

```sh
source .venv/bin/activate
PYTHONPATH=src python -m unittest discover -s tests            # the whole suite (60 tests), seconds
PYTHONPATH=src python -m unittest tests.test_wrangle           # one module
PYTHONPATH=src python -m unittest tests.test_wrangle.SystemsTest.test_B_falls_back_to_a_direct_answer   # one test
```

Each script in `experiments/` lists its phases in its docstring:

```sh
PYTHONPATH=src python experiments/stage0a.py --quick                        # smoke test of stage 0a
PYTHONPATH=src python experiments/stage1a.py solve --system E --stream dev  # classical search, no model needed
PYTHONPATH=src python experiments/stage1a.py solve --system B --stream dev  # needs the model below
PYTHONPATH=src python experiments/stage1a.py report --stream dev
```

The stage 1a model is `models/qwen2.5-coder-1.5b-instruct-q4_k_m.gguf`:
- `models/` is git-ignored.
- Its SHA-256 is in amendment 1 of `docs/10-stage-1a-preregistration.md`.
- Download it with `hf download Qwen/Qwen2.5-Coder-1.5B-Instruct-GGUF qwen2.5-coder-1.5b-instruct-q4_k_m.gguf --local-dir models`.

## Research protocol

This matters more than any code convention here.

- **Pre-register first.** Each stage starts with `docs/NN-stage-XX-preregistration.md`, written before its code or data exist. It gives the question, the systems, the criteria with their thresholds and reasons, and what may be tuned.
- **Development and registered data are separate.**
  - Tune only on development data: the `dev` and `dev-types` streams, `--quick` runs and validation splits.
  - Freeze every setting in an amendment appended to the pre-registration. Commit it *before* the registered splits or streams are generated.
  - Registered data is generated once, with hashed manifests committed, and processed once. The `final` phases refuse to run twice without `--force`, and `stage1a.py solve` refuses the registered streams before `generate` has run.
  - Never tune on, re-run or regenerate registered data.
- **Write selection rules down before computing the numbers they select from.** Example: `reports/stage1a/dev/tuning/attempts_rule.txt`.
- **Report results as registered, pass or fail.** Label exploratory analyses as exploratory. Write down expectations before a run, and say plainly when they were wrong.
- **Compare against the strongest baseline, not only the registered one.** Stage 1a added "memory against the model answering directly" once that turned out to be stronger than the registered baseline.
- **Record each outcome.** Results go in `docs/NN-stage-XX-results.md`, plus a row in the decision log.

## Architecture

The repository holds two tracks.

**Experiment 0 (stages 0a–0d): synthetic typed relational worlds, in `src/sage/*.py`.**
- `machine.py` is a stack machine over entity sets. Instructions and learned library entries are both `Token`s.
- `Counter` counts element operations, the deterministic cost unit of stages 0a–0d.
- `tasks.py` builds tasks, splits and manifests over `worlds.py` and `library.py`.
- `search.py` is best-first search that prunes candidates behaving identically.
- `learn.py` and `learn_guided.py` are wake–sleep learners. They compress solutions into library entries, with a learned numpy guide (`guide.py`) and generated training tasks ("dreams", `dreams.py`).
- `stream.py` and `reuse.py` provide stage 0d's recurring streams and its verified-program memory.

**Stage 1a: real data-wrangling requests with a small LLM, in `src/sage/wrangle/`.**
- **Workload:**
  - `transforms.py` has 50 transformation types with hidden reference functions.
  - `requests.py` builds requests of 3 examples and 5 queries, in Zipf or no-recurrence streams.
  - All randomness is seeded from `VERSION`, the stream name and indices, so a stream is a pure function of the code.
- **Model access, in `llm.py`:**
  - the prompts, versioned by `PROMPT_VERSION`;
  - reply parsing: `extract_code` keeps only definitions, via `ast`;
  - three backends: `LlamaCpp`, which runs in-process so its threads count towards the process's CPU time, the cost measure; `Ollama`; and `Scripted`, for tests.
  - `ModelConfig` holds the tunable settings. The frozen values are `CONFIG` in `experiments/stage1a.py`.
- **Execution and search:**
  - `sandbox.py` runs generated functions with whitelisted built-ins and modules under a timer. It is not a security boundary.
  - `memory.py` is the verified-function memory, ordered by trust, then recent use.
  - `synth.py` is the classical synthesizer, system E.
- **Systems, in `systems.py`:**
  - `run_D`, `run_B` and `run_E` each process one request and return a record: outputs, correctness, calls, tokens, CPU time and every model reply.
  - The memory systems S, E+M and S+ are *replayed* from those records by `replay`. A miss costs exactly what the memoryless system recorded, so memory and no-memory runs are paired request by request. This is the same design as `reuse.simulate` in stage 0d.
- **Harness, `experiments/stage1a.py`:**
  - `solve` writes a header (settings, git revision, machine), then appends one JSONL record per request.
  - It resumes interrupted runs and refuses to mix settings or processors.
  - `report` and `final` compute everything from the records, including the replay with fewer attempts.

**Costs are only comparable within one machine.**
- Stage 1a measured CPU seconds on a 4-core cloud Xeon.
- Later stages run on the author's i5-7500 (4 cores, 4 threads, Ubuntu). Its Intel RAPL energy counters (`/sys/class/powercap/intel-rapl:*`) are readable only by root by default.

## Conventions

- **Reports are generated, not edited.** They are written to `reports/` (`stageXX.md` and `.json`, plus per-instance records) and committed.
- **Development records are committed too,** including superseded baselines such as `reports/stage1a/dev/baseline-p1/`, so that tuning can be audited.
- **Doc numbers come from the reports.** Docs use plain, concrete English, and every figure in them comes from the generated reports.
