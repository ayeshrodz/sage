# SAGE

A research project asking whether a reasoning system's capability can grow with what it has *stored* (verified programs and memories) while the compute it spends per task stays small. The long-run aim is compact, CPU-runnable AI with a small active core and a large, mostly inactive store of skills.

**Status:** experiment 0, stages 0a and 0b complete. A given library cuts work at least 90× (0a). Learned from scratch, a library recovers real procedures and triples the solve rate, but it stalls at about 16 entries without a learned guide; the 0b pre-registered P1 failed and P2 passed. The next proposal is stage 0c: a learned guide plus a refactoring learner.

## Documents

1. [`docs/00-handoff-openai.md`](docs/00-handoff-openai.md): the original research record and plan developed with an OpenAI model, kept verbatim.
2. [`docs/01-independent-analysis.md`](docs/01-independent-analysis.md): an independent review. It frames SAGE around the utility problem and proposes the staged experiment 0.
3. [`docs/02-objective-and-decisions.md`](docs/02-objective-and-decisions.md): the project's objective, in the author's words, and the decision log.
4. [`docs/03-stage-0a-results.md`](docs/03-stage-0a-results.md): stage 0a results, findings and the proposal for stage 0b.
5. [`docs/04-stage-0b-preregistration.md`](docs/04-stage-0b-preregistration.md): stage 0b criteria, amendment and frozen configuration, registered before the hidden test.
6. [`docs/05-stage-0b-results.md`](docs/05-stage-0b-results.md): stage 0b results (P1 fail, P2 pass), diagnosis and the stage 0c proposal.

## Layout

```
src/sage/      worlds.py (relational worlds), machine.py (instruction set + cost counting),
               library.py (planted library, distractors), tasks.py (tasks, splits, manifests),
               search.py (guided best-first program search), learn.py (wake-sleep library learning)
experiments/   stage0a.py, stage0b.py (learn / final phases)
reports/       generated results (Markdown summaries, raw JSON, split manifests)
tests/         unittest suites
pilot/         the toy utility-curve pilot that motivated the design
```

## Running

Pure Python 3.10 or newer, with no dependencies.

```sh
PYTHONPATH=src python -m unittest discover -s tests       # 25 tests, a few seconds
PYTHONPATH=src python experiments/stage0a.py              # about 2 minutes; writes reports/stage0a.*
PYTHONPATH=src python experiments/stage0a.py --well-posed # the same with ambiguous tasks rejected
PYTHONPATH=src python experiments/stage0b.py learn --stream planted --seed 0   # about 6 CPU minutes
python pilot/utility_curve.py                             # toy pilot; writes pilot/RESULTS.md
```

Costs are reported as deterministic element operations (entities and edges touched), with CPU time alongside. Energy measurement is deferred until the project runs on local hardware with readable energy counters.
