"""Stage 0a: the economics of a *given* library on typed relational worlds.

No learning happens here. For the same dev tasks we run best-first search with
  none      base instructions only
  planted   base instructions + the planted library
  +D        base + planted + D distractor macros
under three simulated guides (uniform, fixed-margin, fixed-mass; see
src/sage/search.py) and at two verifier strengths (2 and 4 demonstrations).

Gate (docs/01-independent-analysis.md §5.8): the planted library must cut the
cost of solving tasks by a large factor; otherwise the tasks are too shallow.

Usage:
  PYTHONPATH=src python experiments/stage0a.py            # full run
  PYTHONPATH=src python experiments/stage0a.py --quick    # smoke test
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
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sage.library import base_tokens, distractors, planted_library  # noqa: E402
from sage.machine import run  # noqa: E402
from sage.search import ROUTE_DIM, guide_costs, search  # noqa: E402
from sage.tasks import GENERATOR_VERSION, STRATA, make_split, manifest  # noqa: E402

GUIDES = ("uniform", "margin", "mass")


def git_revision() -> str:
    try:
        rev = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
        dirty = bool(subprocess.check_output(["git", "status", "--porcelain", "src", "experiments"], cwd=ROOT, text=True))
        return rev + ("+dirty" if dirty else "")
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def evaluate(program, hidden) -> dict[str, bool]:
    return {s: all(run(q.world, q.x, program) == q.answer for q in hidden.queries[s]) for s in STRATA}


def run_condition(tokens, tasks, hidden, relevant_of, guide, budget, seed):
    rows = []
    for index, (task, h) in enumerate(zip(tasks, hidden)):
        costs = guide_costs(len(tokens), relevant_of(h), guide)
        tiebreak = list(range(len(tokens)))
        random.Random(f"tiebreak:{seed}:{index}").shuffle(tiebreak)
        t0 = time.process_time()
        res = search(tokens, costs, tiebreak, task, budget)
        cpu = time.process_time() - t0
        correct = evaluate([tokens[i] for i in res.program], h) if res.found else {s: False for s in STRATA}
        rows.append({
            "task_id": task.task_id,
            "found": res.found,
            "correct": correct,
            "candidates": res.candidates,
            "search_ops": res.ops,
            "route_ops": 0 if guide == "uniform" else len(tokens) * ROUTE_DIM,
            "cpu_s": cpu,
            "program": [tokens[i].name for i in res.program],
        })
    return rows


def summarize(rows, budget):
    n = len(rows)
    med = statistics.median(r["candidates"] for r in rows)
    return {
        "solved": sum(r["found"] for r in rows) / n,
        **{f"correct_{s}": sum(r["correct"][s] for r in rows) / n for s in STRATA},
        "spurious_iid": sum(r["found"] and not r["correct"]["iid"] for r in rows) / n,
        "median_candidates": med,
        "censored": med >= budget,
        "median_search_ops": statistics.median(r["search_ops"] for r in rows),
        "route_ops": rows[0]["route_ops"],
        "median_total_ops": statistics.median(r["search_ops"] + r["route_ops"] for r in rows),
        "median_cpu_ms": 1000 * statistics.median(r["cpu_s"] for r in rows),
    }


def pct(x):
    return f"{x:.0%}"


def num(x, censored=False):
    return ("≥" if censored else "") + f"{int(x):,}"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--tasks", type=int, default=40)
    ap.add_argument("--budget", type=int, default=20_000, help="max candidate programs per task")
    ap.add_argument("--demos", type=int, nargs="+", default=[4, 2])
    ap.add_argument("--distractors", type=int, nargs="+", default=[10, 100, 1000])
    ap.add_argument("--well-posed", action="store_true",
                    help="reject tasks where dropping one step of the target still fits the demos")
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--out", type=Path, default=ROOT / "reports")
    args = ap.parse_args()
    if args.quick:
        args.tasks, args.budget, args.distractors, args.demos = 8, 3_000, [100], [4]

    wall0 = time.time()
    tokens_by_name, entries = planted_library()
    base = list(base_tokens().values())
    planted = [e.token for e in entries]
    pool = distractors(max(args.distractors), seed=args.seed)
    libraries = [("none", base), ("planted", base + planted)]
    libraries += [(f"planted + {d:,}", base + planted + pool[:d]) for d in args.distractors]

    results, manifests, gen_stats = [], [], {}
    for n_demos in args.demos:
        stats: dict = {}
        # Same split name with or without --well-posed: the random stream is shared, so the two
        # runs differ only in the few tasks rejected as ambiguous (and their replacements).
        split = f"dev-d{n_demos}"
        tasks, hidden = make_split(split, args.seed, args.tasks, tokens_by_name, entries,
                                   n_demos=n_demos, well_posed=args.well_posed, stats=stats)
        gen_stats[n_demos] = stats
        manifests.append({**manifest(split, args.seed, tasks, hidden), "well_posed": args.well_posed})
        for label, toks in libraries:
            names = [t.name for t in toks]
            if label == "none":
                def relevant_of(h, names=names):
                    wanted = {i.name for n in h.target for i in tokens_by_name[n].body}
                    return {k for k, nm in enumerate(names) if nm in wanted}
            else:
                def relevant_of(h, names=names):
                    return {k for k, nm in enumerate(names) if nm in h.target}
            for guide in GUIDES:
                rows = run_condition(toks, tasks, hidden, relevant_of, guide, args.budget, args.seed)
                results.append({"demos": n_demos, "library": label, "tokens": len(toks), "guide": guide,
                                "summary": summarize(rows, args.budget), "rows": rows})
            print(f"  demos={n_demos} {label:<18} done ({time.time() - wall0:5.0f}s)", flush=True)

    env = {"python": platform.python_version(), "platform": platform.platform(),
           "git": git_revision(), "generator_version": GENERATOR_VERSION}
    config = {k: (str(v) if isinstance(v, Path) else v) for k, v in vars(args).items()}
    args.out.mkdir(parents=True, exist_ok=True)
    stem = "stage0a" + ("_wellposed" if args.well_posed else "") + ("_quick" if args.quick else "")
    (args.out / f"{stem}.json").write_text(json.dumps(
        {"config": config, "env": env, "generation": gen_stats, "results": results}, indent=1, default=list))
    (args.out / f"{stem}_manifest.json").write_text(json.dumps(manifests, indent=1))

    lines = [
        "# Stage 0a: economics of a given library" + (" (well-posed tasks)" if args.well_posed else ""),
        "",
        f"Generated by `experiments/stage0a.py{' --well-posed' if args.well_posed else ''}"
        f"{' --quick' if args.quick else ''}` at git `{env['git']}`"
        f" (generator {GENERATOR_VERSION}, Python {env['python']}). {args.tasks} dev tasks per verifier strength,"
        f" budget {args.budget:,} candidate programs per task, seed {args.seed}.",
        f"{len(base)} base instructions, {len(planted)} planted entries, distractors: random stack-balanced"
        " macros of 2-5 instructions with distinct behaviour on probe inputs.",
        "",
        "Guides are *simulated* (they know which tokens the target uses): uniform = no guide;"
        " margin = fixed 100x preference for relevant tokens; mass = relevant tokens keep 90% of"
        f" probability. Routing = {ROUTE_DIM} multiply-adds per token (brute-force scoring).",
        "`correct` = the found program matches the hidden target on every held-out query of the stratum.",
        "Costs are element operations (entities and edges touched); candidates are censored at the budget (≥).",
        "",
    ]
    for n_demos in args.demos:
        st = gen_stats[n_demos]
        lines += [
            f"## {n_demos} demonstrations per task",
            "",
            f"Task generation: {st.get('accepted', 0)} accepted, {st.get('rejected_short', 0)} rejected because a"
            f" program of ≤3 base instructions fit the demonstrations, {st.get('rejected_degenerate', 0)} rejected"
            f" as degenerate, {st.get('rejected_ambiguous', 0)} rejected as ambiguous.",
            "",
            "| library | tokens | guide | solved | correct iid | correct size | correct topology | spurious |"
            " median candidates | median search ops | routing ops | median CPU ms |",
            "|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for r in results:
            if r["demos"] != n_demos:
                continue
            s = r["summary"]
            lines.append(
                f"| {r['library']} | {r['tokens']:,} | {r['guide']} | {pct(s['solved'])} | {pct(s['correct_iid'])}"
                f" | {pct(s['correct_size'])} | {pct(s['correct_topology'])} | {pct(s['spurious_iid'])}"
                f" | {num(s['median_candidates'], s['censored'])} | {num(s['median_search_ops'])}"
                f" | {num(s['route_ops'])} | {s['median_cpu_ms']:.1f} |")
        lines.append("")
    lines.append(f"Wall time: {time.time() - wall0:.0f}s.")
    text = "\n".join(lines) + "\n"
    (args.out / f"{stem}.md").write_text(text)
    print(text)


if __name__ == "__main__":
    main()
