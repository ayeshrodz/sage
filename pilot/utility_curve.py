"""Toy pilot: does a growing program library pay for itself?

Illustrates the *utility problem* (Minton 1988/1990): stored procedures save
search depth but add breadth, routing work and chances of a spurious fit. It is
NOT a SAGE benchmark. The domain is deliberately trivial so that every cost can
be counted exactly and the whole grid runs in under a minute on a laptop CPU.

Domain
  Values are integers mod P. A program is a sequence of tokens; each token is a
  unary function Z_P -> Z_P. Base tokens are primitives (x+1, 2x, x^2, ...).
  Library tokens are macros: fixed sequences of primitives.

Task
  A hidden target is k planted macros applied in sequence, kept only if no
  shorter program of primitives computes it (the primitives obey identities
  such as dbl∘half = id, so unfiltered targets often collapse). The solver sees
  `n_demos` input/output pairs (the runtime verifier) and must find a
  demo-consistent program. The external oracle then checks that program on all
  P inputs; a demo-consistent program that differs elsewhere is a spurious fit.

Search
  Best-first (uniform-cost) search over token sequences ordered by the guide's
  prior, with lazy child generation and observational-equivalence pruning on
  the demo inputs. Tokens of equal prior are tried in a random order per task.
  Cost is counted, not timed:
    candidates  programs generated and executed on the demo inputs
    prim_ops    primitive applications performed during search
    route_ops   scoring every token once per task (ROUTE_DIM multiply-adds per
                token, i.e. a brute-force learned router; an ANN index or a
                hierarchical router would make this sublinear)

Guides (simulated, not learned)
  uniform  every token equally likely, i.e. breadth-first by program length
  margin   tokens used by the target get a fixed logit advantage `delta` over
           all others, so their probability mass shrinks as the library grows
           (a router whose discrimination does not improve with library size)
  mass     tokens used by the target share a fixed probability mass `q`
           whatever the library size (a router that sharpens as it grows)

Usage
  python pilot/utility_curve.py                 # full grid, writes RESULTS.md
  python pilot/utility_curve.py --quick         # smaller grid for a smoke test
"""

from __future__ import annotations

import argparse
import heapq
import itertools
import math
import random
import statistics
import time
from dataclasses import dataclass
from pathlib import Path

P = 101
ROUTE_DIM = 32
INV2 = pow(2, P - 2, P)

PRIMITIVES = {
    "inc1": lambda x: (x + 1) % P,
    "inc3": lambda x: (x + 3) % P,
    "dec2": lambda x: (x - 2) % P,
    "dbl": lambda x: (2 * x) % P,
    "tri": lambda x: (3 * x) % P,
    "neg": lambda x: (-x) % P,
    "sq": lambda x: (x * x) % P,
    "cube": lambda x: (x * x * x) % P,
    "half": lambda x: (x * INV2) % P,
    "recip": lambda x: pow(x, P - 2, P),  # maps 0 to 0
}
IDENTITY = tuple(range(P))


@dataclass(frozen=True)
class Token:
    name: str
    body: tuple[str, ...]  # primitive names, applied left to right
    table: tuple[int, ...]  # the token's function tabulated over Z_P

    @property
    def length(self) -> int:
        return len(self.body)


def tabulate(body: tuple[str, ...]) -> tuple[int, ...]:
    out = []
    for x in range(P):
        for name in body:
            x = PRIMITIVES[name](x)
        out.append(x)
    return tuple(out)


def compose(tables: list[tuple[int, ...]]) -> tuple[int, ...]:
    out = list(IDENTITY)
    for table in tables:
        out = [table[v] for v in out]
    return tuple(out)


def make_library(rng: random.Random, n_planted: int, macro_len: int, max_distractors: int):
    """Primitives, planted macros and a nested pool of distractor macros.

    Every token is a semantically distinct function (checked on all of Z_P), so
    the distractor pool for D=100 is a prefix of the pool for D=1000, and so on.
    """
    primitives = [Token(n, (n,), tabulate((n,))) for n in PRIMITIVES]
    seen = {t.table for t in primitives} | {IDENTITY}
    names = list(PRIMITIVES)

    def fresh(prefix: str, count: int, lengths: tuple[int, ...]) -> list[Token]:
        tokens = []
        while len(tokens) < count:
            body = tuple(rng.choice(names) for _ in range(rng.choice(lengths)))
            table = tabulate(body)
            if table in seen:
                continue
            seen.add(table)
            tokens.append(Token(f"{prefix}{len(tokens)}", body, table))
        return tokens

    planted = fresh("m", n_planted, (macro_len,))
    distractors = fresh("d", max_distractors, (2, 3, 4, 5))
    return primitives, planted, distractors


@dataclass
class Task:
    target_ids: tuple[int, ...]  # indices into the planted list
    table: tuple[int, ...]
    demo_in: tuple[int, ...]
    demo_out: tuple[int, ...]


def reachable_within(primitives: list[Token], depth: int) -> set[tuple[int, ...]]:
    """Every function some program of at most `depth` primitives computes."""
    seen = {IDENTITY}
    frontier = [IDENTITY]
    for _ in range(depth):
        nxt = []
        for f in frontier:
            for p in primitives:
                g = tuple(p.table[v] for v in f)
                if g not in seen:
                    seen.add(g)
                    nxt.append(g)
        frontier = nxt
    return seen


def make_tasks(rng: random.Random, planted: list[Token], k: int, n_demos: int, count: int, too_short: set):
    """Targets whose function no program of fewer primitives computes.

    The primitives obey many identities (m∘m = id for some macros, dbl∘half = id,
    ...), so an unfiltered k-macro target often collapses to a few primitives
    and would not need the library at all.
    """
    tasks = []
    while len(tasks) < count:
        ids = tuple(rng.randrange(len(planted)) for _ in range(k))
        table = compose([planted[i].table for i in ids])
        if table in too_short:
            continue
        demo_in = tuple(rng.sample(range(P), n_demos))
        tasks.append(Task(ids, table, demo_in, tuple(table[x] for x in demo_in)))
    return tasks


def guide_costs(n_tokens: int, relevant: set[int], guide: str, delta: float, q: float):
    """Return -log p(token) for each token under the (simulated) guide."""
    if guide == "uniform":
        return [math.log(n_tokens)] * n_tokens
    r = len(relevant)
    if guide == "margin":
        z = r * math.exp(delta) + (n_tokens - r)
        p_rel, p_irr = math.exp(delta) / z, 1.0 / z
    elif guide == "mass":
        p_rel, p_irr = q / r, (1.0 - q) / max(1, n_tokens - r)
    else:
        raise ValueError(guide)
    return [-math.log(p_rel if i in relevant else p_irr) for i in range(n_tokens)]


@dataclass
class Outcome:
    found: bool
    correct: bool
    candidates: int
    prim_ops: int
    route_ops: int


def search(tokens: list[Token], costs: list[float], tiebreak: list[int], task: Task, budget: int):
    """Uniform-cost search with lazy successors and observational equivalence.

    A heap entry (priority, tie, g, state, program, rank) stands for the child
    of `state` reached with the rank-th cheapest token; its sibling with the
    next token is pushed only when the entry is popped, so cheap guides never
    touch most of a large library. Tokens of equal cost are tried in the order
    `tiebreak` gives, a random permutation, so that no library position is
    favoured by accident.
    """
    order = sorted(range(len(tokens)), key=lambda i: (costs[i], tiebreak[i]))
    start = task.demo_in
    if start == task.demo_out:
        return True, (), 0, 0
    tie = itertools.count()
    heap = [(costs[order[0]], next(tie), 0.0, start, (), 0)]
    visited = {start}
    candidates = prim_ops = 0
    while heap and candidates < budget:
        _, _, g, state, program, rank = heapq.heappop(heap)
        tok = order[rank]
        if rank + 1 < len(order):
            sib = order[rank + 1]
            heapq.heappush(heap, (g + costs[sib], next(tie), g, state, program, rank + 1))
        table = tokens[tok].table
        child = tuple(table[v] for v in state)
        candidates += 1
        prim_ops += tokens[tok].length * len(state)
        if child in visited:
            continue
        child_program = program + (tok,)
        if child == task.demo_out:
            return True, child_program, candidates, prim_ops
        visited.add(child)
        child_g = g + costs[tok]
        heapq.heappush(heap, (child_g + costs[order[0]], next(tie), child_g, child, child_program, 0))
    return False, (), candidates, prim_ops


def run_condition(tokens, tasks, relevant_of, guide, delta, q, budget, seed):
    outcomes = []
    for index, task in enumerate(tasks):
        costs = guide_costs(len(tokens), relevant_of(task), guide, delta, q)
        tiebreak = list(range(len(tokens)))
        random.Random(seed * 1_000_003 + index).shuffle(tiebreak)
        found, program, candidates, prim_ops = search(tokens, costs, tiebreak, task, budget)
        correct = found and compose([tokens[i].table for i in program]) == task.table
        route_ops = 0 if guide == "uniform" else len(tokens) * ROUTE_DIM
        outcomes.append(Outcome(found, correct, candidates, prim_ops, route_ops))
    return outcomes


def summarize(outcomes: list[Outcome], budget: int) -> dict:
    n = len(outcomes)
    cands = [o.candidates for o in outcomes]
    med = statistics.median(cands)
    total_ops = [o.prim_ops + o.route_ops for o in outcomes]
    return {
        "solved": sum(o.found for o in outcomes) / n,
        "correct": sum(o.correct for o in outcomes) / n,
        "spurious": sum(o.found and not o.correct for o in outcomes) / n,
        "median_candidates": med,
        "censored": med >= budget,
        "route_ops": outcomes[0].route_ops,
        "median_total_ops": statistics.median(total_ops),
    }


def fmt_int(x: float, censored: bool = False) -> str:
    s = f"{int(x):,}"
    return f"≥{s}" if censored else s


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--tasks", type=int, default=30)
    ap.add_argument("--budget", type=int, default=60_000, help="max candidates per task")
    ap.add_argument("--planted", type=int, default=8)
    ap.add_argument("--macro-len", type=int, default=3)
    ap.add_argument("--k", type=int, default=3, help="planted macros per target")
    ap.add_argument("--min-prim-depth", type=int, default=7,
                    help="keep only targets that no shorter program of primitives computes")
    ap.add_argument("--delta", type=float, default=math.log(100), help="logit margin for the margin guide")
    ap.add_argument("--q", type=float, default=0.9, help="relevant mass for the mass guide")
    ap.add_argument("--demos", type=int, nargs="+", default=[2, 4])
    ap.add_argument("--distractors", type=int, nargs="+", default=[0, 10, 100, 1000, 10000])
    ap.add_argument("--quick", action="store_true", help="small grid for a smoke test")
    ap.add_argument("--out", type=Path, default=None, help="default: pilot/RESULTS.md (not written with --quick)")
    args = ap.parse_args()
    if args.quick:
        args.tasks, args.budget, args.distractors = 6, 10_000, [0, 100]
    elif args.out is None:
        args.out = Path(__file__).with_name("RESULTS.md")

    lib_rng = random.Random(args.seed)
    primitives, planted, distractors = make_library(lib_rng, args.planted, args.macro_len, max(args.distractors))
    primitive_index = {t.name: i for i, t in enumerate(primitives)}
    too_short = reachable_within(primitives, args.min_prim_depth - 1)
    guides = ["uniform", "margin", "mass"]

    def relevant_in_library(task: Task) -> set[int]:
        return {len(primitives) + i for i in task.target_ids}

    def relevant_in_primitives(task: Task) -> set[int]:  # no library: target spelled in primitives
        return {primitive_index[n] for i in task.target_ids for n in planted[i].body}

    rows = []
    t0 = time.time()
    for n_demos in args.demos:
        tasks = make_tasks(random.Random(args.seed * 1000 + n_demos), planted, args.k, n_demos, args.tasks, too_short)
        for guide in guides:
            outs = run_condition(primitives, tasks, relevant_in_primitives, guide, args.delta, args.q, args.budget, args.seed)
            rows.append((n_demos, "none (primitives only)", len(primitives), guide, summarize(outs, args.budget)))
        for d in args.distractors:
            tokens = primitives + planted + distractors[:d]
            label = "planted" if d == 0 else f"planted + {d:,} distractors"
            for guide in guides:
                outs = run_condition(tokens, tasks, relevant_in_library, guide, args.delta, args.q, args.budget, args.seed)
                rows.append((n_demos, label, len(tokens), guide, summarize(outs, args.budget)))
            print(f"  n_demos={n_demos} {label:<30} done ({time.time() - t0:5.1f}s)", flush=True)

    lines = [
        "# Pilot results: library size vs. search cost",
        "",
        "Generated by `python pilot/utility_curve.py"
        + (" --quick" if args.quick else "")
        + f"` (seed {args.seed}, {args.tasks} tasks per row, budget {args.budget:,} candidates per task,"
        f" P={P}, {len(primitives)} primitives, {args.planted} planted macros of length {args.macro_len},"
        f" targets of {args.k} macros that need at least {args.min_prim_depth} primitives,"
        f" margin delta={args.delta:.2f} nats, mass q={args.q}).",
        "",
        "Toy illustration only; see the module docstring for what is and is not modelled.",
        "Tokens of equal prior are tried in a random order per task.",
        "`candidates` is censored at the budget for unsolved tasks (shown as ≥).",
        "`total ops` = primitive applications during search + brute-force routing (tokens x "
        f"{ROUTE_DIM}).",
        "",
    ]
    for n_demos in args.demos:
        lines += [
            f"## {n_demos} demonstrations per task",
            "",
            "| library | tokens | guide | solved | correct | spurious | median candidates | median total ops | of which routing |",
            "|---|---:|---|---:|---:|---:|---:|---:|---:|",
        ]
        for nd, label, n_tokens, guide, s in rows:
            if nd != n_demos:
                continue
            lines.append(
                f"| {label} | {n_tokens:,} | {guide} | {s['solved']:.0%} | {s['correct']:.0%} | {s['spurious']:.0%} "
                f"| {fmt_int(s['median_candidates'], s['censored'])} | {fmt_int(s['median_total_ops'])} "
                f"| {fmt_int(s['route_ops'])} |"
            )
        lines.append("")
    lines.append(f"Wall time for the whole grid: {time.time() - t0:.0f}s.")
    print("\n".join(lines))
    if args.out is not None:
        args.out.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
