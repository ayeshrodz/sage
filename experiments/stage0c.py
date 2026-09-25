"""Stage 0c: a learned, state-conditioned guide and a refactoring learner.

Pre-registration: docs/06-stage-0c-preregistration.md (with amendment 1).

Phases:
  learn  --config primary|secondary --seed S
         guided wake-sleep on `0c-train` with acceptance on `0c-val`;
         writes reports/stage0c/learn_<config>_s<S>.json. Never touches a test split.
  final  generates `0c-test` and `0c-mismatch-test` (first and only time),
         evaluates S0, S0+planted, S3 (both configurations, all seeds) and
         the ablations, checks P1', P3', P-guide and the control, and writes
         reports/stage0c.{md,json} plus manifests. Refuses to run twice
         unless --force is given.

Usage:
  PYTHONPATH=src python experiments/stage0c.py learn --config primary --seed 0
  PYTHONPATH=src python experiments/stage0c.py final
"""

from __future__ import annotations

import argparse
import json
import platform
import statistics
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sage.control import control_library  # noqa: E402
from sage.evaluation import policy_percentiles, recovered, reference_program  # noqa: E402
from sage.guide import Guide  # noqa: E402
from sage.learn import load_library, solve  # noqa: E402
from sage.learn_guided import GuidedConfig, GuidedLearner, load_learned, solve_with_policy  # noqa: E402
from sage.library import base_tokens, planted_library  # noqa: E402
from sage.machine import base_instructions, run  # noqa: E402
from sage.tasks import GENERATOR_VERSION, STRATA, make_split, manifest  # noqa: E402

OUT = ROOT / "reports" / "stage0c"
BUDGET = 20_000
N_FUTURE = 1_000
SEEDS = (0, 1, 2)
P1_MIN, P3_MIN, PGUIDE_MAX, CONTROL_MAX = 0.53, 5.0, 0.10, 0.05

# Frozen before the hidden splits were generated (amendment 1). "primary" is judged against the
# pre-registered criteria; "secondary" is the pre-declared low-cost alternative, reported alongside.
CONFIGS = {
    "primary": dict(rounds=8, wake_budget=10_000, val_budget=5_000, solve_cap=5_000, max_policy_calls=300,
                    state_depth=2, min_feature_count=2, guide_epochs=3, guide_warm_epochs=1, dreams_initial=200,
                    dreams_per_update=60, dream_pool=400, retry_half=True, refresh=True),
    "secondary": dict(rounds=8, wake_budget=2_000, val_budget=2_000, solve_cap=2_000, max_policy_calls=200,
                      state_depth=1, min_feature_count=4, guide_epochs=3, guide_warm_epochs=1, dreams_initial=200,
                      dreams_per_update=60, dream_pool=400, retry_half=True, refresh=True),
}


def git_revision() -> str:
    try:
        rev = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
        dirty = bool(subprocess.check_output(["git", "status", "--porcelain", "src", "experiments"], cwd=ROOT, text=True))
        return rev + ("+dirty" if dirty else "")
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def planted_split(name: str, n: int, single_share: float = 0.0):
    tokens, entries = planted_library()
    return make_split(name, 0, n, tokens, entries, n_demos=4, single_share=single_share)


def phase_learn(args) -> None:
    cfg = GuidedConfig(seed=args.seed, **CONFIGS[args.config])
    train, _ = planted_split("0c-train", 200, single_share=0.5)
    val, _ = planted_split("0c-val", 40)
    print(f"learning: config={args.config} seed={args.seed} {cfg}", flush=True)
    result = GuidedLearner(train, val, cfg, log=lambda m: print(m, flush=True)).run()
    result.update({"config_name": args.config, "git": git_revision()})
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"learn_{args.config}_s{args.seed}.json").write_text(json.dumps(result))


def correctness(program, hidden) -> dict[str, bool]:
    return {s: all(run(q.world, q.x, program) == q.answer for q in hidden.queries[s]) for s in STRATA}


def summarize(results, tokens, hidden) -> tuple[dict, list]:
    rows = []
    for res, h in zip(results, hidden):
        program = [tokens[i] for i in res.program]
        corr = correctness(program, h) if res.found else {s: False for s in STRATA}
        rows.append({"task_id": h.task_id, "found": res.found, "correct": corr, "candidates": res.candidates,
                     "work": res.ops, "program": [t.name for t in program]})
    n = len(rows)
    total = sum(r["work"] for r in rows)
    solved = sum(r["found"] for r in rows)
    correct = sum(r["correct"]["iid"] for r in rows)
    return {
        "solved": solved / n,
        **{f"correct_{s}": sum(r["correct"][s] for r in rows) / n for s in STRATA},
        "total_work": total,
        "mean_work": total / n,
        "work_per_solved": total / solved if solved else None,
        "work_per_correct": total / correct if correct else None,
        "median_candidates": statistics.median(r["candidates"] for r in rows),
    }, rows


def phase_final(args) -> None:
    if (ROOT / "reports" / "stage0c.md").exists() and not args.force:
        sys.exit("stage 0c final results already exist; the hidden splits are evaluated once (use --force)")
    t0 = time.time()
    base = list(base_tokens().values())
    _, entries = planted_library()
    planted = [e.token for e in entries]
    test, test_h = planted_split("0c-test", 100)
    b_tokens, b_entries = control_library()
    mism, mism_h = make_split("0c-mismatch-test", 0, 100, b_tokens, b_entries, n_demos=4)
    out = {"env": {"git": git_revision(), "python": platform.python_version(), "platform": platform.platform(),
                   "generator_version": GENERATOR_VERSION},
           "control_library": {e.token.name: " ".join(e.token.parts) for e in b_entries}}
    manifests = [manifest("0c-test", 0, test, test_h), manifest("0c-mismatch-test", 0, mism, mism_h)]

    def log(msg):
        print(f"  [{time.time() - t0:5.0f}s] {msg}", flush=True)

    s0, s0_rows = summarize(solve(base, test, BUDGET, "eval"), base, test_h)
    s0m, s0m_rows = summarize(solve(base, mism, BUDGET, "eval"), base, mism_h)
    log(f"S0: test solved {s0['solved']:.0%}, mismatch solved {s0m['solved']:.0%}")
    sp, sp_rows = summarize(solve(base + planted, test, BUDGET, "eval"), base + planted, test_h)
    log(f"S0+planted: test solved {sp['solved']:.0%}")
    out.update({"S0": s0, "S0_mismatch": s0m, "S0_planted": sp,
                "rows": {"S0": s0_rows, "S0_mismatch": s0m_rows, "S0_planted": sp_rows}})

    ablation_0b = {}
    for seed in SEEDS:
        f = ROOT / "reports" / "stage0b" / f"library_planted_s{seed}.json"
        lib = load_library(json.loads(f.read_text())["library"])
        ablation_0b[seed], _ = summarize(solve(base + lib, test, BUDGET, "eval"), base + lib, test_h)
    out["ablation_0b_libraries"] = ablation_0b
    log("0b libraries on the fresh test: " + ", ".join(f"{v['solved']:.0%}" for v in ablation_0b.values()))

    w0 = s0["work_per_correct"] if s0["work_per_correct"] else None
    out["S3"] = {}
    for name, overrides in CONFIGS.items():
        runs = {}
        for seed in SEEDS:
            lj = json.loads((OUT / f"learn_{name}_s{seed}.json").read_text())
            cfg = GuidedConfig(**lj["config"])
            learned = load_learned(lj["library"])
            guide = Guide.from_json(lj["guide"])
            tokens = base_instructions() + learned
            by_name = {t.name: t for t in tokens}
            res = [solve_with_policy(tokens, guide, t, min(cfg.solve_cap, BUDGET), f"eval:{i}", cfg)
                   for i, t in enumerate(test)]
            s3, rows = summarize(res, tokens, test_h)
            resm = [solve_with_policy(tokens, guide, t, min(cfg.solve_cap, BUDGET), f"eval:{i}", cfg)
                    for i, t in enumerate(mism)]
            s3m, rows_m = summarize(resm, tokens, mism_h)
            noguide, _ = summarize(solve(tokens, test, BUDGET, "eval"), tokens, test_h)
            rec = recovered(learned)
            pg = [policy_percentiles(guide, t.demos, reference_program(h.target, rec), by_name, cfg.root_depth,
                                     cfg.state_depth) for t, h in zip(test, test_h)]
            L = lj["learning_work"]
            c3 = s3["correct_iid"]
            w3 = s3["mean_work"]
            W3 = (L + N_FUTURE * w3) / (N_FUTURE * c3) if c3 else None
            W3op = w3 / c3 if c3 else None
            break_even = (L / (c3 * w0 - w3)) if (w0 and c3 and c3 * w0 > w3) else None
            runs[seed] = {
                "test": s3, "mismatch": s3m, "no_guide_ablation": noguide,
                "library": [" ".join(e["parts"]) for e in lj["library"]], "library_size": len(learned),
                "recovered": rec, "p_guide_teacher_forced": statistics.fmean(a for a, _ in pg),
                "p_guide_first_token": statistics.fmean(b for _, b in pg),
                "learning_work": L, "ledger": lj["ledger"], "learning_cpu_s": lj["cpu_s"],
                "W3_amortized": W3, "W3_operational": W3op, "break_even_tasks": break_even,
                "rows": rows, "rows_mismatch": rows_m,
            }
            log(f"S3 {name} seed {seed}: test solved {s3['solved']:.0%}, mismatch {s3m['solved']:.0%},"
                f" no-guide {noguide['solved']:.0%}, P-guide {runs[seed]['p_guide_teacher_forced']:.3f}")
        mean = lambda xs: sum(xs) / len(xs)  # noqa: E731
        solved = mean([r["test"]["solved"] for r in runs.values()])
        W3s = [r["W3_amortized"] for r in runs.values()]
        ratio = (w0 / mean(W3s)) if (w0 and all(W3s)) else None
        pgm = mean([r["p_guide_teacher_forced"] for r in runs.values()])
        ctrl = mean([r["mismatch"]["solved"] for r in runs.values()]) - s0m["solved"]
        out["S3"][name] = {
            "config": overrides, "runs": runs,
            "verdict": {
                "P1": {"value": solved, "threshold": P1_MIN, "pass": solved >= P1_MIN},
                "P3": {"value": ratio, "threshold": P3_MIN, "pass": bool(ratio and ratio >= P3_MIN),
                       "operational_ratio": (w0 / mean([r["W3_operational"] for r in runs.values()])
                                             if w0 and all(r["W3_operational"] for r in runs.values()) else None)},
                "P_guide": {"value": pgm, "threshold": PGUIDE_MAX, "pass": pgm <= PGUIDE_MAX},
                "control": {"value": ctrl, "threshold": CONTROL_MAX, "pass": ctrl <= CONTROL_MAX},
            },
        }
    (ROOT / "reports" / "stage0c.json").write_text(json.dumps(out, default=list))
    (OUT / "test_manifests.json").write_text(json.dumps(manifests, indent=1))
    write_report(out, time.time() - t0)


def write_report(out, wall) -> None:
    pct = lambda x: "—" if x is None else f"{x:.0%}"  # noqa: E731
    num = lambda x: "—" if x is None else f"{x:,.0f}"  # noqa: E731
    lines = [
        "# Stage 0c results: a learned guide and a refactoring learner", "",
        f"Generated by `experiments/stage0c.py final` at git `{out['env']['git']}` (generator"
        f" {out['env']['generator_version']}, Python {out['env']['python']}). Hidden splits `0c-test` and"
        f" `0c-mismatch-test`: 100 tasks each, 4 demonstrations, budget ceiling {BUDGET:,} candidates."
        " Pre-registration: `docs/06-stage-0c-preregistration.md` (with amendment 1).", "",
        "## Pre-registered criteria", "",
        "| Configuration | P1′ solved (≥ 53%) | P3′ W0/W3 at N = 1,000 (≥ 5×) | P-guide (≤ 10%) | Control gain (≤ +5 pts) |",
        "|---|---:|---:|---:|---:|",
    ]
    for name, s in out["S3"].items():
        v = s["verdict"]
        mark = lambda ok: "PASS" if ok else "FAIL"  # noqa: E731
        p3 = "—" if v["P3"]["value"] is None else f"{v['P3']['value']:.1f}×"
        lines.append(f"| {name} | {pct(v['P1']['value'])} {mark(v['P1']['pass'])} | {p3} {mark(v['P3']['pass'])}"
                     f" | {v['P_guide']['value']:.1%} {mark(v['P_guide']['pass'])}"
                     f" | {v['control']['value'] * 100:+.0f} {mark(v['control']['pass'])} |")
    s0, sp = out["S0"], out["S0_planted"]
    lines += ["", "## Planted test (`0c-test`)", "",
              "| System | Library | Solved | Correct iid / size / topology | Mean work per task | Work per correct |"
              " Learning work | Break-even tasks |",
              "|---|---:|---:|---:|---:|---:|---:|---:|",
              f"| S0 | 0 | {pct(s0['solved'])} | {pct(s0['correct_iid'])} / {pct(s0['correct_size'])} /"
              f" {pct(s0['correct_topology'])} | {num(s0['mean_work'])} | {num(s0['work_per_correct'])} | — | — |",
              f"| S0+planted | 13 | {pct(sp['solved'])} | {pct(sp['correct_iid'])} / {pct(sp['correct_size'])} /"
              f" {pct(sp['correct_topology'])} | {num(sp['mean_work'])} | {num(sp['work_per_correct'])} | — | — |"]
    for name, s in out["S3"].items():
        for seed, r in s["runs"].items():
            t = r["test"]
            lines.append(f"| S3 {name} s{seed} | {r['library_size']} | {pct(t['solved'])} | {pct(t['correct_iid'])} /"
                         f" {pct(t['correct_size'])} / {pct(t['correct_topology'])} | {num(t['mean_work'])} |"
                         f" {num(t['work_per_correct'])} | {num(r['learning_work'])} | {num(r['break_even_tasks'])} |")
    lines += ["", "## Ablations and control", "",
              "| System | Planted test solved | Mismatch test solved | P-guide first token |",
              "|---|---:|---:|---:|",
              f"| S0 | {pct(s0['solved'])} | {pct(out['S0_mismatch']['solved'])} | — |"]
    for name, s in out["S3"].items():
        for seed, r in s["runs"].items():
            lines.append(f"| S3 {name} s{seed} (library + guide) | {pct(r['test']['solved'])} |"
                         f" {pct(r['mismatch']['solved'])} | {r['p_guide_first_token']:.1%} |")
            lines.append(f"| S3 {name} s{seed} library, no guide | {pct(r['no_guide_ablation']['solved'])} | — | — |")
    for seed, v in out["ablation_0b_libraries"].items():
        lines.append(f"| 0b library s{seed}, no guide | {pct(v['solved'])} | — | — |")
    lines += ["", "## Recovered planted entries", ""]
    for name, s in out["S3"].items():
        for seed, r in s["runs"].items():
            lines.append(f"- {name} s{seed} ({r['library_size']} entries): {', '.join(sorted(r['recovered'])) or 'none'}")
    lines += ["", "Control library B: " + "; ".join(f"{k} = {v}" for k, v in out["control_library"].items()) + ".",
              "", "Per-task rows, learned libraries, guides and ledgers: `reports/stage0c.json`, `reports/stage0c/`.",
              "", f"Wall time of the final phase: {wall:.0f}s."]
    text = "\n".join(lines) + "\n"
    (ROOT / "reports" / "stage0c.md").write_text(text)
    print(text)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="phase", required=True)
    lp = sub.add_parser("learn")
    lp.add_argument("--config", choices=tuple(CONFIGS), default="primary")
    lp.add_argument("--seed", type=int, default=0)
    fp = sub.add_parser("final")
    fp.add_argument("--force", action="store_true")
    args = ap.parse_args()
    phase_learn(args) if args.phase == "learn" else phase_final(args)


if __name__ == "__main__":
    main()
