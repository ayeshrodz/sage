"""Evaluator-side measures that need hidden knowledge (targets), never used by learners.

- `recovered`: which planted entries a learned library reproduces, judged by
  behaviour on the single-entity P2 probe set (stage 0b's recovery test).
- `reference_program`: a hidden target rewritten over a learner's tokens.
  Recovered planted entries become the learned entry, others are expanded
  into their parts recursively, down to base instructions.
- `guide_percentile`: the mean percentile rank (0 = top) that a guide gives
  to the distinct tokens of a task's reference program (P-guide).
"""

from __future__ import annotations

from .features import state_features
from .guide import percentile_ranks
from .machine import Counter, execute
from .learn import behaviour, probe_set
from .library import PLANTED_SPEC, planted_library

PLANTED_PARTS = {name: parts for name, parts, _, _ in PLANTED_SPEC}


def recovered(learned, singles=None) -> dict[str, str]:
    """planted entry name -> name of the first learned token that behaves identically."""
    singles = singles if singles is not None else probe_set()
    tokens, entries = planted_library()
    fps = {}
    for t in learned:
        fps.setdefault(behaviour(t, singles), t.name)
    out = {}
    for e in entries:
        name = fps.get(behaviour(e.token, singles))
        if name is not None:
            out[e.token.name] = name
    return out


def reference_program(target, rec: dict[str, str]) -> list[str]:
    def expand(n: str) -> list[str]:
        if n in rec:
            return [rec[n]]
        if n in PLANTED_PARTS:
            return [m for p in PLANTED_PARTS[n] for m in expand(p)]
        return [n]
    return [m for n in target for m in expand(n)]


def guide_percentile(guide, feats, reference: list[str]) -> float:
    p, _ = guide.probs(feats)
    ranks = percentile_ranks(p)
    names = [n for n in dict.fromkeys(reference) if n in guide.t_index]
    return sum(ranks[guide.t_index[n]] for n in names) / len(names)


def policy_percentiles(guide, demos, reference: list[str], by_name: dict, root_depth: int = 3,
                       state_depth: int = 2) -> tuple[float, float]:
    """Teacher-forced ranks along the reference program.

    Returns (mean over steps of the percentile rank of the reference's next
    token given the state its prefix reaches, percentile rank of the first
    token at the start state). A token missing from the guide counts as 1.0.
    """
    state = tuple((frozenset((d.x,)), ()) for d in demos)
    last, ranks = None, []
    for name in reference:
        feats = state_features(demos, state, last, Counter(), root_depth if last is None else state_depth)
        p, _ = guide.probs(feats)
        r = percentile_ranks(p)
        ranks.append(r[guide.t_index[name]] if name in guide.t_index else 1.0)
        body = by_name[name].body
        state = tuple(execute(d.world, d.x, cur, stack, body, Counter()) for d, (cur, stack) in zip(demos, state))
        last = name
    return sum(ranks) / len(ranks), ranks[0]
