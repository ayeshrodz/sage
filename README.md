# SAGE

A research project asking whether a reasoning system's capability can grow with what it has *stored* (verified programs and memories) while the compute it spends per task stays small.

**Status:** design stage. There are no SAGE results yet, only a plan, a review of that plan, and a toy pilot.

## Documents

- [`docs/00-handoff-openai.md`](docs/00-handoff-openai.md): the research record and experiment-0 plan developed with an OpenAI model (handoff dated 2026-09-26, NZ time). Kept verbatim.
- [`docs/01-independent-analysis.md`](docs/01-independent-analysis.md): an independent review of that plan. It frames SAGE around the utility problem, audits the references and proposes a revised experiment 0 (planted-library induction on typed relational worlds) with decision gates.

## Pilot

[`pilot/utility_curve.py`](pilot/utility_curve.py) is a toy illustration of how search cost and correctness change as a program library grows. It is pure Python 3.9 or newer, has no dependencies and runs in under a minute on a laptop CPU. The last run's output is in [`pilot/RESULTS.md`](pilot/RESULTS.md).

```sh
python pilot/utility_curve.py           # full grid; rewrites pilot/RESULTS.md
python pilot/utility_curve.py --quick   # smoke test; prints only
```
