"""Perception for the guide: generic features of a task's demonstrations.

For every demonstration (world, x, answer A) we follow labelled relation paths
of up to MAX_DEPTH steps from {x} and record, for each path signature s that
reaches part of the answer:

  rec   |R_s ∩ A| / |A|        how much of the answer the path reaches
  prec  |R_s ∩ A| / |R_s|      how much of what it reaches is in the answer
  exact R_s (minus x) == A     the path alone explains the answer

plus the entity types and attribute values of the answers. Values are averaged
over demonstrations. Nothing here refers to any library; the same features
serve any relational task family.

All work is counted: relation steps through the machine's element-operation
counter, and every set comparison as |R_s| + |A| operations. Identical sets
reached by different signatures are expanded only once.
"""

from __future__ import annotations

from collections import defaultdict

from .machine import Counter, Instr, execute
from .worlds import COLORS, SIZES, TYPES

MAX_DEPTH = 3
STEPS = [Instr(op, rel) for op, rel in (
    ("out", "parent"), ("in", "parent"), ("out", "friend"), ("out", "lives_in"), ("in", "lives_in"),
    ("out", "inside"), ("in", "inside"), ("out", "near"), ("out", "owns"), ("in", "owns"),
    ("clos", "parent"), ("rclos", "parent"), ("clos", "inside"), ("rclos", "inside"),
)]


def _size_bucket(n: int) -> str:
    return "0" if n == 0 else "1" if n == 1 else "2-3" if n <= 3 else "4-7" if n <= 7 else "8+"


def demo_features(world, x: int, answer: frozenset, counter: Counter, max_depth: int = MAX_DEPTH) -> dict[str, float]:
    feats: dict[str, float] = {}
    n_ans = len(answer)
    feats[f"size:{_size_bucket(n_ans)}"] = 1.0
    if x in answer:
        feats["x_in_answer"] = 1.0
    if n_ans:
        for t in TYPES:
            share = sum(world.etype[a] == t for a in answer) / n_ans
            if share:
                feats[f"type:{t}"] = share
        for c in COLORS:
            share = sum(world.color[a] == c for a in answer) / n_ans
            if share:
                feats[f"color:{c}"] = share
                if share == 1.0:
                    feats[f"all_color:{c}"] = 1.0
        for s in SIZES:
            share = sum(world.size[a] == s for a in answer) / n_ans
            if share:
                feats[f"size_attr:{s}"] = share
                if share == 1.0:
                    feats[f"all_size:{s}"] = 1.0
        counter.ops += 3 * n_ans

    cache: dict[tuple[frozenset, int], frozenset] = {}
    frontier = [((), frozenset((x,)))]
    for _ in range(max_depth):
        nxt = []
        for sig, cur in frontier:
            for k, step in enumerate(STEPS):
                key = (cur, k)
                if key not in cache:
                    cache[key], _ = execute(world, x, cur, (), (step,), counter)
                reached = cache[key]
                if not reached:
                    continue
                s = sig + (step.name,)
                nxt.append((s, reached))
                if n_ans:
                    counter.ops += len(reached) + n_ans
                    hit = len(reached & answer)
                    if hit:
                        name = ",".join(s)
                        feats[f"rec:{name}"] = hit / n_ans
                        feats[f"prec:{name}"] = hit / len(reached)
                        if reached - {x} == answer or reached == answer:
                            feats[f"exact:{name}"] = 1.0
        frontier = nxt
    return feats


def task_features(demos, counter: Counter, max_depth: int = MAX_DEPTH) -> dict[str, float]:
    """Features averaged over the task's demonstrations (the solver's view only)."""
    total: dict[str, float] = defaultdict(float)
    for d in demos:
        for k, v in demo_features(d.world, d.x, d.answer, counter, max_depth).items():
            total[k] += v
    n = len(demos)
    out = {k: v / n for k, v in total.items()}
    out["bias"] = 1.0
    return out


FINISHERS = ("drop_x", "only_color.red", "only_color.green", "only_color.blue", "only_size.small", "only_size.large")


def state_features(demos, state, last: str | None, counter: Counter, max_depth: int = 2) -> dict[str, float]:
    """Features of a search state (per demonstration: current set, stack) relative to the answers.

    The same path features as `demo_features`, anchored at the current set
    instead of {x}, plus one-step completion checks (would a filter, drop_x or
    a set operation with the saved set finish the job?), the stack depth and
    the last token used. These let a policy choose the next token from where
    the search actually is.
    """
    total: dict[str, float] = defaultdict(float)
    depth = len(state[0][1])
    for d, (cur, stack) in zip(demos, state):
        A = d.answer
        feats: dict[str, float] = {}
        if cur == A:
            feats["done"] = 1.0
        elif A and A <= cur:
            feats["answer_within"] = 1.0
        counter.ops += len(cur) + len(A)
        for name in FINISHERS:
            if name == "drop_x":
                out = cur - {d.x}
            else:
                attr, val = name.split(".")
                table = {"only_color": d.world.color, "only_size": d.world.size}[attr]
                out = frozenset(e for e in cur if table[e] == val)
            counter.ops += len(cur)
            if out == A and out != cur:
                feats[f"finish:{name}"] = 1.0
        if stack:
            top = stack[-1]
            counter.ops += 3 * (len(cur) + len(top))
            for name, out in (("minus_pop", cur - top), ("inter_pop", cur & top), ("union_pop", cur | top)):
                if out == A:
                    feats[f"finish:{name}"] = 1.0
        cache: dict[tuple[frozenset, int], frozenset] = {}
        frontier = [((), cur)] if cur else []
        for _ in range(max_depth):
            nxt = []
            for sig, here in frontier:
                for k, step in enumerate(STEPS):
                    key = (here, k)
                    if key not in cache:
                        cache[key], _ = execute(d.world, d.x, here, (), (step,), counter)
                    reached = cache[key]
                    if not reached:
                        continue
                    s = sig + (step.name,)
                    nxt.append((s, reached))
                    if A:
                        counter.ops += len(reached) + len(A)
                        hit = len(reached & A)
                        if hit:
                            name = ",".join(s)
                            feats[f"rec:{name}"] = hit / len(A)
                            feats[f"prec:{name}"] = hit / len(reached)
                            if reached - {d.x} == A or reached == A:
                                feats[f"exact:{name}"] = 1.0
            frontier = nxt
        for k, v in feats.items():
            total[k] += v
    n = len(demos)
    out = {k: v / n for k, v in total.items()}
    out[f"stack:{depth}"] = 1.0
    out[f"last:{last or '^'}"] = 1.0
    out["bias"] = 1.0
    return out
