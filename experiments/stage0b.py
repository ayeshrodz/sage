"""Stage 0b: learning the library (pre-registered in docs/04-stage-0b-preregistration.md).

Phases:
  learn  --stream planted|control --seed S
         wake-sleep learning on `train` with acceptance on `val`; writes
         reports/stage0b/library_<stream>_s<S>.json. Never touches `test`.
  final  generates the hidden `test` splits (first and only time), evaluates
         S0, S1 (each learned library) and S0+planted, checks P1, P2 and
         P3-lite, and writes reports/stage0b.{md,json} plus manifests.
         Refuses to run twice unless --force is given.

Usage:
  PYTHONPATH=src python experiments/stage0b.py learn --stream planted --seed 0
  PYTHONPATH=src python experiments/stage0b.py final
"""

from __future__ import annotations

import argparse
import json
import platform
import random
import statistics
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sage.learn import LearnConfig, behaviour, learn, load_library, probe_set, solve  # noqa: E402
from sage.library import base_tokens, planted_library  # noqa: E402
from sage.machine import run  # noqa: E402
from sage.tasks import GENERATOR_VERSION, STRATA, make_split, manifest  # noqa: E402

OUT = ROOT / "reports" / "stage0b"
SPLIT_SIZES = {"train": 200, "val": 40, "test": 100}
TEST_BUDGET = 20_000
TRAIN_SINGLE_SHARE = 0.5  # curriculum on training streams only (amendment 1)
SEEDS = (0, 1, 2)
P1_MIN, P1_CONTROL_MAX, P2_MIN = 0.53, 0.05, 0.50


def git_revision() -> str:
    try:
        rev = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
        dirty = bool(subprocess.check_output(["git", "status", "--porcelain", "src", "experiments"], cwd=ROOT, text=True))
        return rev + ("+dirty" if dirty else "")
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def split(stream: str, name: str):
    tokens, entries = planted_library()
    prefix = "" if stream == "planted" else "control-"
    return make_split(f"0b-{prefix}{name}", 0, SPLIT_SIZES[name], tokens, entries, n_demos=4,
                      structure=stream, single_share=TRAIN_SINGLE_SHARE if name == "train" else 0.0)


def phase_learn(args) -> None:
    cfg = LearnConfig(seed=args.seed, rounds=args.rounds, wake_budget=args.wake_budget,
                      val_budget=args.val_budget, batch=args.batch)
    train, _ = split(args.stream, "train")
    val, _ = split(args.stream, "val")
    print(f"learning: stream={args.stream} seed={args.seed} {cfg}", flush=True)
    result = learn(train, val, cfg, log=lambda m: print(m, flush=True))
    result.update({"stream": args.stream, "git": git_revision()})
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"library_{args.stream}_s{args.seed}.json").write_text(json.dumps(result, indent=1))


def evaluate(tokens, tasks, hidden, learned_names=frozenset()):
    results = solve(tokens, tasks, TEST_BUDGET, "eval")
    rows = []
    for res, h in zip(results, hidden):
        program = [tokens[i] for i in res.program]
        correct = {s: res.found and all(run(q.world, q.x, program) == q.answer for q in h.queries[s]) for s in STRATA}
        rows.append({"task_id": h.task_id, "found": res.found, "correct": correct, "candidates": res.candidates,
                     "ops": res.ops, "uses_learned": any(t.name in learned_names for t in program),
                     "program": [" ".join(t.parts) if t.name in learned_names else t.name for t in program]})
    n = len(rows)
    return {
        "solved": sum(r["found"] for r in rows) / n,
        **{f"correct_{s}": sum(r["correct"][s] for r in rows) / n for s in STRATA},
        "median_candidates": statistics.median(r["candidates"] for r in rows),
        "median_ops": statistics.median(r["ops"] for r in rows),
        "mean_ops": statistics.fmean(r["ops"] for r in rows),
        "reuse": (sum(r["uses_learned"] for r in rows if r["found"]) / max(1, sum(r["found"] for r in rows))),
    }, rows


def phase_final(args) -> None:
    if (ROOT / "reports" / "stage0b.md").exists() and not args.force:
        sys.exit("stage 0b final results already exist; the hidden split is evaluated once (use --force to override)")
    t0 = time.time()
    tokens_by_name, entries = planted_library()
    base = list(base_tokens().values())
    planted = [e.token for e in entries]
    probes = probe_set()
    out = {"env": {"git": git_revision(), "python": platform.python_version(), "platform": platform.platform(),
                   "generator_version": GENERATOR_VERSION}, "streams": {}}
    manifests = []
    for stream in ("planted", "control"):
        test, hidden = split(stream, "test")
        manifests.append(manifest(f"0b-{'' if stream == 'planted' else 'control-'}test", 0, test, hidden))
        s0, s0_rows = evaluate(base, test, hidden)
        entry = {"S0": s0, "S0_rows": s0_rows, "S1": {}}
        if stream == "planted":
            entry["S0+planted"], entry["S0+planted_rows"] = evaluate(base + planted, test, hidden)
            # P2 reference set: planted entries used at top level by >=5% of train targets
            _, train_hidden = split("planted", "train")
            counts = Counter(n for h in train_hidden for n in set(h.target))
            common = [e for e in entries if counts[e.token.name] >= 0.05 * len(train_hidden)]
            entry["p2_reference"] = {e.token.name: counts[e.token.name] for e in common}
        for seed in SEEDS:
            lib_file = OUT / f"library_{stream}_s{seed}.json"
            lib = json.loads(lib_file.read_text())
            learned = load_library(lib["library"])
            s1, s1_rows = evaluate(base + learned, test, hidden, frozenset(t.name for t in learned))
            s1["library_size"] = len(learned)
            s1["learning_cost"] = lib["cost"]
            learn_ops = lib["cost"]["wake_ops"] + lib["cost"]["val_ops"]
            saving = s0["mean_ops"] - s1["mean_ops"]
            s1["mean_saving_per_task"] = saving
            s1["break_even_tasks"] = (learn_ops / saving) if saving > 0 else None
            if stream == "planted":
                fps = {behaviour(t, probes) for t in learned}
                recovered = [e.token.name for e in common if behaviour(e.token, probes) in fps]
                s1["recovered"] = recovered
                s1["recovered_fraction"] = len(recovered) / len(common)
            entry["S1"][seed] = {"summary": s1, "rows": s1_rows}
            print(f"  {stream} seed {seed}: S1 solved {s1['solved']:.0%} ({time.time() - t0:.0f}s)", flush=True)
        out["streams"][stream] = entry

    pl, co = out["streams"]["planted"], out["streams"]["control"]
    mean = lambda xs: sum(xs) / len(xs)  # noqa: E731
    p1_main = mean([pl["S1"][s]["summary"]["solved"] for s in SEEDS])
    p1_ctrl = mean([co["S1"][s]["summary"]["solved"] for s in SEEDS]) - co["S0"]["solved"]
    p2 = mean([pl["S1"][s]["summary"]["recovered_fraction"] for s in SEEDS])
    p3 = [pl["S1"][s]["summary"]["median_ops"] < pl["S0"]["median_ops"] for s in SEEDS]
    verdict = {
        "P1_planted": {"value": p1_main, "threshold": P1_MIN, "pass": p1_main >= P1_MIN},
        "P1_control": {"value": p1_ctrl, "threshold": P1_CONTROL_MAX, "pass": p1_ctrl <= P1_CONTROL_MAX},
        "P2": {"value": p2, "threshold": P2_MIN, "pass": p2 >= P2_MIN},
        "P3_lite": {"per_seed": p3, "pass": all(p3)},
    }
    out["verdict"] = verdict
    (ROOT / "reports" / "stage0b.json").write_text(json.dumps(out, indent=1, default=list))
    (OUT / "test_manifests.json").write_text(json.dumps(manifests, indent=1))
    write_report(out, time.time() - t0)


def write_report(out, wall) -> None:
    pct = lambda x: f"{x:.0%}"  # noqa: E731
    v = out["verdict"]
    lines = [
        "# Stage 0b results: learning the library",
        "",
        f"Generated by `experiments/stage0b.py final` at git `{out['env']['git']}` (generator"
        f" {out['env']['generator_version']}, Python {out['env']['python']}). Hidden `test` splits: 100 tasks per"
        f" stream, 4 demonstrations, uniform guide, budget {TEST_BUDGET:,} candidates. Pre-registration:"
        " `docs/04-stage-0b-preregistration.md`.",
        "",
        "## Pre-registered criteria",
        "",
        "| Criterion | Value | Threshold | Result |",
        "|---|---:|---:|---|",
        f"| P1: mean S1 solve rate on planted `test` | {pct(v['P1_planted']['value'])} | ≥ {pct(P1_MIN)} |"
        f" {'PASS' if v['P1_planted']['pass'] else 'FAIL'} |",
        f"| P1: control S1 − S0 solve rate | {v['P1_control']['value'] * 100:+.0f} pts | ≤ +5 pts |"
        f" {'PASS' if v['P1_control']['pass'] else 'FAIL'} |",
        f"| P2: mean fraction of common planted entries recovered | {pct(v['P2']['value'])} | ≥ {pct(P2_MIN)} |"
        f" {'PASS' if v['P2']['pass'] else 'FAIL'} |",
        f"| P3-lite: S1 median search ops < S0 (every seed) | {v['P3_lite']['per_seed']} | all true |"
        f" {'PASS' if v['P3_lite']['pass'] else 'FAIL'} |",
        "",
    ]
    for stream, entry in out["streams"].items():
        lines += [f"## Stream: {stream}", "",
                  "| System | Library | Solved | Correct iid | size | topology | Median candidates | Median ops |"
                  " Reuse | Learning ops | Break-even tasks |",
                  "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
        rows = [("S0", entry["S0"], "0")]
        if "S0+planted" in entry:
            rows.append(("S0+planted", entry["S0+planted"], "13"))
        rows += [(f"S1 seed {s}", entry["S1"][s]["summary"], str(entry["S1"][s]["summary"]["library_size"]))
                 for s in entry["S1"]]
        for name, s, size in rows:
            cost = s.get("learning_cost")
            learn_ops = f"{cost['wake_ops'] + cost['val_ops']:,}" if cost else "—"
            be = s.get("break_even_tasks")
            be_txt = f"{be:,.0f}" if be else ("—" if cost is None else "never")
            lines.append(
                f"| {name} | {size} | {pct(s['solved'])} | {pct(s['correct_iid'])} | {pct(s['correct_size'])}"
                f" | {pct(s['correct_topology'])} | {int(s['median_candidates']):,} | {int(s['median_ops']):,}"
                f" | {pct(s['reuse']) if name.startswith('S1') else '—'} | {learn_ops} | {be_txt} |")
        if stream == "planted":
            lines += ["", "P2 reference set (planted entries in ≥5% of train targets, with counts): "
                      + ", ".join(f"{k} ({c})" for k, c in entry["p2_reference"].items()) + ".", ""]
            for s in entry["S1"]:
                lines.append(f"- Seed {s} recovered: {', '.join(entry['S1'][s]['summary']['recovered']) or 'none'}.")
        lines.append("")
    lines += ["Learned libraries, round-by-round histories and per-task rows: `reports/stage0b/` and"
              " `reports/stage0b.json`.", "", f"Wall time of the final phase: {wall:.0f}s."]
    text = "\n".join(lines) + "\n"
    (ROOT / "reports" / "stage0b.md").write_text(text)
    print(text)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="phase", required=True)
    lp = sub.add_parser("learn")
    lp.add_argument("--stream", choices=("planted", "control"), default="planted")
    lp.add_argument("--seed", type=int, default=0)
    lp.add_argument("--rounds", type=int, default=LearnConfig.rounds)
    lp.add_argument("--wake-budget", type=int, default=LearnConfig.wake_budget)
    lp.add_argument("--val-budget", type=int, default=LearnConfig.val_budget)
    lp.add_argument("--batch", type=int, default=LearnConfig.batch)
    fp = sub.add_parser("final")
    fp.add_argument("--force", action="store_true")
    args = ap.parse_args()
    phase_learn(args) if args.phase == "learn" else phase_final(args)


if __name__ == "__main__":
    main()
