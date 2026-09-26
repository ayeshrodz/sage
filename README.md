# SAGE

A research project asking whether a reasoning system's capability can grow with what it has *stored* (verified programs and memories) while the compute it spends per task stays small. The long-run aim is compact, CPU-runnable AI with a small active core and a large, mostly inactive store of skills.

**Status:** stages 0a–0d and 1a are complete. Stage 1a, a real workload with a small language model, passed all four of its pre-registered criteria.

- **0a:** a given library cuts work at least 90×.
- **0b:** a library learned from scratch recovers real procedures but stalls without a guide.
- **0c:** a refactoring learner with a state-conditioned guide solves 62% of unseen compositional tasks. That passes P1′, and the knowledge is family-specific (the control passes). But it fails the efficiency criteria: the guide costs more per decision than it saves, and learning takes about a thousand tasks to repay.
- **0d:** a memory of verified programs makes recognized recurring tasks about 1,000× cheaper and more accurate than fresh search. It raises accuracy by 14 points and halves the work per correct answer across a recurring stream, at no cost when nothing recurs. But about 30% of recurrences go unrecognized (P1d failed; P2d–P4d passed).
- **1a:** a real workload with a real model. Data-wrangling requests by example ("Mary Chen" → "M.C.") are answered by Qwen2.5-Coder-1.5B on a 4-core CPU. On a 300-request recurring stream, a memory of verified functions answers 74% of requests in microseconds. It is 2.9× cheaper per correct answer than having the model write functions each time, and more accurate. W1–W4 all pass. It also beats asking the model directly: 92–93% correct against 71%, at 1.4–2.2× less CPU per correct answer. But that depends on requests recurring, and on the model being able to write a function for the frequent types. The weak point is writing the procedure, not reusing it (`docs/12-stage-1a-results.md`).

## Documents

1. [`docs/00-handoff-openai.md`](docs/00-handoff-openai.md): the original research record and plan developed with an OpenAI model, kept verbatim.
2. [`docs/01-independent-analysis.md`](docs/01-independent-analysis.md): an independent review. It frames SAGE around the utility problem and proposes the staged experiment 0.
3. [`docs/02-objective-and-decisions.md`](docs/02-objective-and-decisions.md): the project's objective, in the author's words, and the decision log.
4. [`docs/03-stage-0a-results.md`](docs/03-stage-0a-results.md): stage 0a results, findings and the proposal for stage 0b.
5. [`docs/04-stage-0b-preregistration.md`](docs/04-stage-0b-preregistration.md): stage 0b criteria, amendment and frozen configuration, registered before the hidden test.
6. [`docs/05-stage-0b-results.md`](docs/05-stage-0b-results.md): stage 0b results (P1 fail, P2 pass), diagnosis and the stage 0c proposal.
7. [`docs/06-stage-0c-preregistration.md`](docs/06-stage-0c-preregistration.md): stage 0c criteria and amendment, frozen before the hidden test.
8. [`docs/07-stage-0c-results.md`](docs/07-stage-0c-results.md): stage 0c results (P1′ and the control pass; P3′ and P-guide fail) and the options for the next step.
9. [`docs/08-stage-0d-preregistration.md`](docs/08-stage-0d-preregistration.md): stage 0d criteria and amendment, registered before the streams existed.
10. [`docs/09-stage-0d-results.md`](docs/09-stage-0d-results.md): stage 0d results (P2d–P4d pass, P1d fails), why recurrences are missed, and the options for the next step.
11. [`docs/10-stage-1a-preregistration.md`](docs/10-stage-1a-preregistration.md): stage 1a criteria (W1–W4), registered before any stage 1a code or stream existed.
12. [`docs/11-stage-1a-setup.md`](docs/11-stage-1a-setup.md): what stage 1a consists of, what was checked without the model, and how to run the model stage.
13. [`docs/12-stage-1a-results.md`](docs/12-stage-1a-results.md): stage 1a results (W1–W4 pass), the comparison with asking the model directly, when memory pays, and the options for the next step.

## Layout

```
src/sage/      worlds.py (relational worlds), machine.py (instruction set + cost counting),
               library.py (planted library, distractors), tasks.py (tasks, splits, manifests),
               search.py (guided and policy-guided search), learn.py and learn_guided.py (wake-sleep learners),
               features.py, guide.py, dreams.py (perception, learned guide, dreams), control.py, evaluation.py,
               stream.py and reuse.py (recurring-task streams, reuse memory)
               wrangle/ for stage 1a: transforms.py and requests.py (workload), sandbox.py, memory.py,
               synth.py (classical search), llm.py (prompts, llama.cpp and Ollama backends), systems.py
experiments/   stage0a.py, stage0b.py, stage0c.py, stage0d.py, stage1a.py
reports/       generated results (Markdown summaries, raw JSON, split manifests)
tools/         model_parts.py (splits the model into checksummed parts for GitHub, and joins them)
tests/         unittest suites
pilot/         the toy utility-curve pilot that motivated the design
```

## Running

Python 3.10 or newer. numpy is needed for the stage 0c guide (`pip install numpy`), and llama-cpp-python for the stage 1a model (`pip install -e ".[llm]"`).

```sh
PYTHONPATH=src python -m unittest discover -s tests       # 60 tests, a few seconds
PYTHONPATH=src python experiments/stage0a.py              # about 2 minutes; writes reports/stage0a.*
PYTHONPATH=src python experiments/stage0a.py --well-posed # the same with ambiguous tasks rejected
PYTHONPATH=src python experiments/stage0b.py learn --stream planted --seed 0   # about 6 CPU minutes
PYTHONPATH=src python experiments/stage0c.py learn --config primary --seed 0   # about 4 CPU minutes
python pilot/utility_curve.py                             # toy pilot; writes pilot/RESULTS.md
PYTHONPATH=src python experiments/stage1a.py solve --system E --stream dev   # stage 1a classical search, seconds
PYTHONPATH=src python experiments/stage1a.py report --stream dev
```

The stage 1a model runs, including the model download, are described in `docs/11-stage-1a-setup.md`.

Costs are reported as deterministic element operations (entities and edges touched), with CPU time alongside. Energy measurement is deferred until the project runs on local hardware with readable energy counters.
