"""Stage 0d: reuse on recurring tasks (pre-registration: docs/08-stage-0d-preregistration.md).

Phases:
  generate            builds `0d-zipf` (200 types, 1,000 instances, Zipf 1.0) and
                      `0d-norecur` (300 distinct types) once; writes hashed manifests to
                      reports/stage0d/ and a local pickle cache (not committed).
  solve --system S0   runs a memoryless system on every instance of both streams
  solve --system S3 --seed S
                      (S3 = the frozen stage 0c primary system of that seed) and records
                      found / program / work / correctness per instance.
  final               replays the reuse memory (R0 over S0, R3 over S3) on the same
                      instances, checks P1d-P4d and writes reports/stage0d.{md,json}.
                      Refuses to run twice unless --force is given.

Usage:
  PYTHONPATH=src python experiments/stage0d.py generate
  PYTHONPATH=src python experiments/stage0d.py solve --system S0
  PYTHONPATH=src python experiments/stage0d.py solve --system S3 --seed 0
  PYTHONPATH=src python experiments/stage0d.py final
"""

from __future__ import annotations

import argparse
import json
import pickle
import platform
import statistics
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sage.guide import Guide  # noqa: E402
from sage.learn import solve  # noqa: E402
from sage.learn_guided import GuidedConfig, load_learned, solve_with_policy  # noqa: E402
from sage.library import base_tokens, planted_library  # noqa: E402
from sage.machine import base_instructions, run  # noqa: E402
from sage.reuse import simulate  # noqa: E402
from sage.stream import norecur_stream, stream_manifest, zipf_stream  # noqa: E402
from sage.tasks import GENERATOR_VERSION  # noqa: E402

OUT = ROOT / "reports" / "stage0d"
CACHE = OUT / "cache"
S0_BUDGET = 20_000
SEEDS = (0, 1, 2)
STREAMS = {"zipf": ("0d-zipf", dict(n_types=200, n_instances=1000, exponent=1.0)),
           "norecur": ("0d-norecur", dict(n=300))}
MAX_CHECKS = 50
P1_MIN, P2_MIN, P3_MAX, P4_MIN = 10.0, -0.03, 1.05, 2.0


def git_revision() -> str:
    try:
        rev = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
        dirty = bool(subprocess.check_output(["git", "status", "--porcelain", "src", "experiments"], cwd=ROOT, text=True))
        return rev + ("+dirty" if dirty else "")
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def build_streams(prefix: str = "", zipf=None, norecur=None):
    tokens, entries = planted_library()
    zname, zargs = STREAMS["zipf"]
    nname, nargs = STREAMS["norecur"]
    return {"zipf": zipf_stream(prefix + zname, 0, tokens=tokens, entries=entries, **(zipf or zargs)),
            "norecur": norecur_stream(prefix + nname, 0, tokens=tokens, entries=entries, **(norecur or nargs))}


def phase_generate(args) -> None:
    manifest_file = OUT / "stream_manifests.json"
    if manifest_file.exists() and not args.force:
        sys.exit("the stage 0d streams were already generated (use --force)")
    t0 = time.time()
    streams = build_streams()
    OUT.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    with open(CACHE / "streams.pkl", "wb") as f:
        pickle.dump(streams, f)
    names = {k: STREAMS[k][0] for k in streams}
    manifest_file.write_text(json.dumps([stream_manifest(names[k], 0, v) for k, v in streams.items()], indent=1))
    for k, v in streams.items():
        types = {s.type_id for s in v}
        print(f"{k}: {len(v)} instances of {len(types)} types ({time.time() - t0:.0f}s)")


def load_streams():
    with open(CACHE / "streams.pkl", "rb") as f:
        return pickle.load(f)


def record(res, tokens, inst) -> dict:
    program = [tokens[i] for i in res.program]
    correct = res.found and all(run(q.world, q.x, program) == q.answer for q in inst.queries)
    return {"found": res.found, "correct": bool(correct), "work": res.ops, "candidates": res.candidates,
            "program": [ins.name for t in program for ins in t.body]}


def phase_solve(args) -> None:
    streams = load_streams()
    out = {"system": args.system, "seed": args.seed, "git": git_revision(), "streams": {}}
    t0 = time.time()
    if args.system == "S0":
        base = list(base_tokens().values())
        for k, stream in streams.items():
            results = solve(base, [s.task for s in stream], S0_BUDGET, f"0d:{k}")
            out["streams"][k] = [record(r, base, s) for r, s in zip(results, stream)]
            print(f"S0 {k}: {sum(r.found for r in results)}/{len(stream)} solved ({time.time() - t0:.0f}s)", flush=True)
    else:
        lj = json.loads((ROOT / "reports" / "stage0c" / f"learn_primary_s{args.seed}.json").read_text())
        cfg = GuidedConfig(**lj["config"])
        tokens = base_instructions() + load_learned(lj["library"])
        guide = Guide.from_json(lj["guide"])
        out["learning_work"] = lj["learning_work"]
        for k, stream in streams.items():
            rows = []
            for i, s in enumerate(stream):
                res = solve_with_policy(tokens, guide, s.task, min(cfg.solve_cap, S0_BUDGET), f"0d:{k}:{i}", cfg)
                rows.append(record(res, tokens, s))
                if (i + 1) % 100 == 0:
                    print(f"S3 s{args.seed} {k}: {i + 1}/{len(stream)} ({time.time() - t0:.0f}s)", flush=True)
            out["streams"][k] = rows
    OUT.mkdir(parents=True, exist_ok=True)
    name = "S0" if args.system == "S0" else f"S3_s{args.seed}"
    (OUT / f"solve_{name}.json").write_text(json.dumps(out))


def compare(stream, s_rows, r_rows) -> dict:
    """Memoryless (S) against reuse (R) on the same instances."""
    n = len(stream)
    solved_before, seen = [], set()
    for inst, r in zip(stream, r_rows):
        solved_before.append(inst.type_id in seen)
        if r["found"]:
            seen.add(inst.type_id)
    rep = [i for i in range(n) if solved_before[i]]
    s_tot, r_tot = sum(r["work"] for r in s_rows), sum(r["work"] for r in r_rows)
    s_cor, r_cor = sum(r["correct"] for r in s_rows), sum(r["correct"] for r in r_rows)
    hits = [r for r in r_rows if r["mode"] == "hit"]
    return {
        "instances": n,
        "repeats_of_solved_types": len(rep),
        "p1_ratio": (statistics.fmean(s_rows[i]["work"] for i in rep) / statistics.fmean(r_rows[i]["work"] for i in rep))
        if rep else None,
        "s_correct": s_cor / n, "r_correct": r_cor / n, "p2_diff": (r_cor - s_cor) / n,
        "s_solved": sum(r["found"] for r in s_rows) / n, "r_solved": sum(r["found"] for r in r_rows) / n,
        "work_ratio": r_tot / s_tot,
        "s_work_per_correct": s_tot / s_cor if s_cor else None,
        "r_work_per_correct": r_tot / r_cor if r_cor else None,
        "p4_ratio": (s_tot / s_cor) / (r_tot / r_cor) if s_cor and r_cor else None,
        "s_total_work": s_tot, "r_total_work": r_tot,
        "hits": len(hits), "hit_precision": (sum(r["correct"] for r in hits) / len(hits)) if hits else None,
        "hit_precision_by_trust": {
            label: (lambda xs: (sum(r["correct"] for r in xs) / len(xs), len(xs)) if xs else (None, 0))(
                [r for r in hits if lo <= r["trust_used"] <= hi])
            for label, lo, hi in (("1", 1, 1), ("2-4", 2, 4), ("5+", 5, 10 ** 9))},
        "mean_lookup_work": statistics.fmean(r["lookup_work"] for r in r_rows),
        "median_hit_work": statistics.median(r["work"] for r in hits) if hits else None,
        "final_memory": r_rows[-1]["memory_size"],
        "windows": [(statistics.fmean(r["work"] for r in s_rows[w:w + 100]),
                     statistics.fmean(r["work"] for r in r_rows[w:w + 100])) for w in range(0, n, 100)],
    }


def phase_final(args) -> None:
    if (ROOT / "reports" / "stage0d.md").exists() and not args.force:
        sys.exit("stage 0d final results already exist (use --force)")
    streams = load_streams()
    by_name = {b.name: b for b in base_instructions()}
    program_of = lambda res: [by_name[n] for n in res["program"]]  # noqa: E731
    s0 = json.loads((OUT / "solve_S0.json").read_text())
    out = {"env": {"git": git_revision(), "python": platform.python_version(), "generator_version": GENERATOR_VERSION},
           "R0": {}, "R3": {}}
    for k, stream in streams.items():
        r0 = simulate(stream, s0["streams"][k], program_of, MAX_CHECKS)
        out["R0"][k] = compare(stream, s0["streams"][k], r0)
    for seed in SEEDS:
        s3 = json.loads((OUT / f"solve_S3_s{seed}.json").read_text())
        out["R3"][seed] = {"learning_work": s3["learning_work"]}
        for k, stream in streams.items():
            r3 = simulate(stream, s3["streams"][k], program_of, MAX_CHECKS)
            out["R3"][seed][k] = compare(stream, s3["streams"][k], r3)
        z = out["R3"][seed]["zipf"]
        w0 = out["R0"]["zipf"]["s_work_per_correct"]  # S0's work per correct answer on the stream
        n, L = z["instances"], s3["learning_work"]
        incl = (L + z["r_total_work"]) / (z["r_correct"] * n) if z["r_correct"] else None
        c, w = z["r_correct"], z["r_total_work"] / n
        out["R3"][seed]["learning_included"] = {
            "work_per_correct": incl, "ratio_vs_S0": (w0 / incl) if (w0 and incl) else None,
            "break_even_tasks": (L / (c * w0 - w)) if (w0 and c * w0 > w) else None}
    mean = lambda xs: sum(xs) / len(xs)  # noqa: E731
    v = {
        "P1d": mean([out["R3"][s]["zipf"]["p1_ratio"] for s in SEEDS]),
        "P2d": mean([out["R3"][s]["zipf"]["p2_diff"] for s in SEEDS]),
        "P3d": mean([out["R3"][s]["norecur"]["work_ratio"] for s in SEEDS]),
        "P4d": mean([out["R3"][s]["zipf"]["p4_ratio"] for s in SEEDS]),
    }
    out["verdict"] = {"P1d": {"value": v["P1d"], "pass": v["P1d"] >= P1_MIN},
                      "P2d": {"value": v["P2d"], "pass": v["P2d"] >= P2_MIN},
                      "P3d": {"value": v["P3d"], "pass": v["P3d"] <= P3_MAX},
                      "P4d": {"value": v["P4d"], "pass": v["P4d"] >= P4_MIN}}
    (ROOT / "reports" / "stage0d.json").write_text(json.dumps(out, default=list))
    write_report(out)


def write_report(out) -> None:
    pct = lambda x: "—" if x is None else f"{x:.1%}"  # noqa: E731
    num = lambda x: "—" if x is None else f"{x:,.0f}"  # noqa: E731
    mult = lambda x: "—" if x is None else f"{x:.1f}×"  # noqa: E731
    v = out["verdict"]
    mark = lambda ok: "PASS" if ok else "FAIL"  # noqa: E731
    lines = [
        "# Stage 0d results: reuse on recurring tasks", "",
        f"Generated by `experiments/stage0d.py final` at git `{out['env']['git']}` (generator"
        f" {out['env']['generator_version']}). Streams: `0d-zipf` (200 types, 1,000 instances, Zipf 1.0) and"
        f" `0d-norecur` (300 distinct types). Reuse memory: key = answer entity types, up to {MAX_CHECKS}"
        " verifications per task, trust then recency order. Pre-registration: `docs/08-stage-0d-preregistration.md`.", "",
        "## Pre-registered criteria (R3 against S3, mean of 3 seeds)", "",
        "| Criterion | Value | Threshold | Result |", "|---|---:|---:|---|",
        f"| P1d: S3 ÷ R3 mean work on recurring, already-solved types | {mult(v['P1d']['value'])} | ≥ 10× | {mark(v['P1d']['pass'])} |",
        f"| P2d: R3 − S3 iid-correct rate (zipf) | {v['P2d']['value'] * 100:+.1f} pts | ≥ −3 pts | {mark(v['P2d']['pass'])} |",
        f"| P3d: R3 ÷ S3 total work (norecur) | {v['P3d']['value']:.3f} | ≤ 1.05 | {mark(v['P3d']['pass'])} |",
        f"| P4d: S3 ÷ R3 work per correct answer (zipf) | {mult(v['P4d']['value'])} | ≥ 2× | {mark(v['P4d']['pass'])} |",
        "", "## Per system and seed (zipf stream)", "",
        "| Pair | Correct S / R | Solved S / R | Work per correct S / R | P1d ratio | P4d ratio | Hits | Hit precision | Median hit work | Memory |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    rows = [("S0 / R0", out["R0"]["zipf"])] + [(f"S3 / R3 s{s}", out["R3"][s]["zipf"]) for s in SEEDS]
    for label, z in rows:
        lines.append(f"| {label} | {pct(z['s_correct'])} / {pct(z['r_correct'])} | {pct(z['s_solved'])} / {pct(z['r_solved'])}"
                     f" | {num(z['s_work_per_correct'])} / {num(z['r_work_per_correct'])} | {mult(z['p1_ratio'])}"
                     f" | {mult(z['p4_ratio'])} | {z['hits']} | {pct(z['hit_precision'])} | {num(z['median_hit_work'])}"
                     f" | {z['final_memory']} |")
    lines += ["", "## No-recurrence stream", "", "| Pair | Work ratio R ÷ S | Hits | Correct S / R |", "|---|---:|---:|---:|"]
    rows = [("S0 / R0", out["R0"]["norecur"])] + [(f"S3 / R3 s{s}", out["R3"][s]["norecur"]) for s in (0, 1, 2)]
    for label, z in rows:
        lines.append(f"| {label} | {z['work_ratio']:.3f} | {z['hits']} | {pct(z['s_correct'])} / {pct(z['r_correct'])} |")
    lines += ["", "## Learning included (stage 0c learning work of each seed, zipf stream)", "",
              "| Seed | Learning work | R3 work per correct, learning included | Ratio vs S0 | Break-even stream length |",
              "|---|---:|---:|---:|---:|"]
    for s in (0, 1, 2):
        li = out["R3"][s]["learning_included"]
        lines.append(f"| {s} | {num(out['R3'][s]['learning_work'])} | {num(li['work_per_correct'])} |"
                     f" {mult(li['ratio_vs_S0'])} | {num(li['break_even_tasks'])} |")
    lines += ["", "## Learning curve (mean work per task, windows of 100 instances, zipf)", "",
              "| Window | S0 | R0 | S3 (mean of seeds) | R3 (mean of seeds) |", "|---|---:|---:|---:|---:|"]
    w0 = out["R0"]["zipf"]["windows"]
    for j, (s0w, r0w) in enumerate(w0):
        s3w = sum(out["R3"][s]["zipf"]["windows"][j][0] for s in (0, 1, 2)) / 3
        r3w = sum(out["R3"][s]["zipf"]["windows"][j][1] for s in (0, 1, 2)) / 3
        lines.append(f"| {j * 100 + 1}–{j * 100 + 100} | {num(s0w)} | {num(r0w)} | {num(s3w)} | {num(r3w)} |")
    lines += ["", "Hit precision by the trust of the program used (zipf, R3): " + "; ".join(
        f"seed {s}: " + ", ".join(f"trust {k}: {pct(p)} (n={n})" for k, (p, n) in out['R3'][s]['zipf']['hit_precision_by_trust'].items())
        for s in (0, 1, 2)) + ".", "", "Per-instance data: `reports/stage0d/`; manifests: `reports/stage0d/stream_manifests.json`."]
    text = "\n".join(lines) + "\n"
    (ROOT / "reports" / "stage0d.md").write_text(text)
    print(text)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="phase", required=True)
    g = sub.add_parser("generate")
    g.add_argument("--force", action="store_true")
    s = sub.add_parser("solve")
    s.add_argument("--system", choices=("S0", "S3"), required=True)
    s.add_argument("--seed", type=int, default=0)
    f = sub.add_parser("final")
    f.add_argument("--force", action="store_true")
    args = ap.parse_args()
    {"generate": phase_generate, "solve": phase_solve, "final": phase_final}[args.phase](args)


if __name__ == "__main__":
    main()
