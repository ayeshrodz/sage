# SAGE

A research project asking whether a reasoning system's capability can grow with what it has *stored* (verified programs and memories) while the compute it spends per task stays small. The long-run aim is compact, CPU-runnable AI with a small active core and a large, mostly inactive store of skills.

**Status:** experiment 0, stages 0a–0c complete.

- **0a:** a given library cuts work at least 90×.
- **0b:** a library learned from scratch recovers real procedures but stalls without a guide.
- **0c:** a refactoring learner with a state-conditioned guide solves 62% of unseen compositional tasks. That passes P1′, and the knowledge is family-specific (the control passes). But it fails the efficiency criteria: the guide costs more per decision than it saves, and learning takes about a thousand tasks to repay.

The proposed next step is stage 0d: reuse on recurring tasks.

## Documents

1. [`docs/00-handoff-openai.md`](docs/00-handoff-openai.md): the original research record and plan developed with an OpenAI model, kept verbatim.
2. [`docs/01-independent-analysis.md`](docs/01-independent-analysis.md): an independent review. It frames SAGE around the utility problem and proposes the staged experiment 0.
3. [`docs/02-objective-and-decisions.md`](docs/02-objective-and-decisions.md): the project's objective, in the author's words, and the decision log.
4. [`docs/03-stage-0a-results.md`](docs/03-stage-0a-results.md): stage 0a results, findings and the proposal for stage 0b.
5. [`docs/04-stage-0b-preregistration.md`](docs/04-stage-0b-preregistration.md): stage 0b criteria, amendment and frozen configuration, registered before the hidden test.
6. [`docs/05-stage-0b-results.md`](docs/05-stage-0b-results.md): stage 0b results (P1 fail, P2 pass), diagnosis and the stage 0c proposal.
7. [`docs/06-stage-0c-preregistration.md`](docs/06-stage-0c-preregistration.md): stage 0c criteria and amendment, frozen before the hidden test.
8. [`docs/07-stage-0c-results.md`](docs/07-stage-0c-results.md): stage 0c results (P1′ and the control pass; P3′ and P-guide fail) and the options for the next step.

## Layout

```
src/sage/      worlds.py (relational worlds), machine.py (instruction set + cost counting),
               library.py (planted library, distractors), tasks.py (tasks, splits, manifests),
               search.py (guided and policy-guided search), learn.py and learn_guided.py (wake-sleep learners),
               features.py, guide.py, dreams.py (perception, learned guide, dreams), control.py, evaluation.py
experiments/   stage0a.py, stage0b.py, stage0c.py (learn / final phases)
reports/       generated results (Markdown summaries, raw JSON, split manifests)
tests/         unittest suites
pilot/         the toy utility-curve pilot that motivated the design
```

## Running

Python 3.10 or newer. numpy is needed only for the stage 0c guide (`pip install numpy`).

```sh
PYTHONPATH=src python -m unittest discover -s tests       # 33 tests, a few seconds
PYTHONPATH=src python experiments/stage0a.py              # about 2 minutes; writes reports/stage0a.*
PYTHONPATH=src python experiments/stage0a.py --well-posed # the same with ambiguous tasks rejected
PYTHONPATH=src python experiments/stage0b.py learn --stream planted --seed 0   # about 6 CPU minutes
PYTHONPATH=src python experiments/stage0c.py learn --config primary --seed 0   # about 4 CPU minutes
python pilot/utility_curve.py                             # toy pilot; writes pilot/RESULTS.md
```

Costs are reported as deterministic element operations (entities and edges touched), with CPU time alongside. Energy measurement is deferred until the project runs on local hardware with readable energy counters.
