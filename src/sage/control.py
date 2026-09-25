"""Control library B for stage 0c: a different task family with the same generator shape.

B has 13 hierarchical entries drawn by a fixed random process that shares the
planted library's shape:
- the same instruction vocabulary;
- type-respecting relation paths and `push <path> <set op>` idioms (the same
  macro generator as the 0b control stream);
- entries built from earlier entries;
- person inputs and Zipf-skewed use.

Every B entry must behave differently from every base instruction, every
planted entry and every earlier B entry on the P2 probe set, and must give
non-empty answers for at least half of the person probes. Tasks are made from
B by the same task generator as the planted stream. Evaluating the *A-trained*
system on them measures how much of its benefit is specific to the family it
learned.
"""

from __future__ import annotations

import random

from .learn import behaviour, probe_set
from .library import Entry, base_tokens, planted_library
from .machine import MAX_STACK, macro
from .tasks import _STEPS, _random_macro


def control_library(seed: int = 2026, size: int = 13):
    rng = random.Random(f"control-library:{seed}")
    by_name = dict(base_tokens())
    _, planted = planted_library()
    singles = probe_set()
    persons = [(w, x) for w, x in singles if w.etype[x] == "person"]
    known = {behaviour(t, singles) for t in by_name.values() if t.need == 0 and t.delta == 0 and t.rise == 0}
    known |= {behaviour(e.token, singles) for e in planted}
    known.add(tuple(frozenset((x,)) for _, x in singles))
    person_steps = sorted(n for n, t in _STEPS["person"].items() if t == "person")
    entries: list[Entry] = []
    while len(entries) < size:
        k = len(entries)
        prev = [e for e in entries if e.out_type == "person"]
        if prev and k >= 3 and rng.random() < 0.35:
            e = rng.choice(prev)
            if rng.random() < 0.5:
                step = rng.choice(sorted(_STEPS["person"]))
                parts, out_type = [e.token.name, step], _STEPS["person"][step]
            else:
                parts, out_type = [rng.choice(person_steps), e.token.name], "person"
        else:
            parts, out_type = _random_macro(rng, "person")
        tok = macro(f"b{k}", parts, by_name)
        if tok.need or tok.delta or tok.rise > MAX_STACK:
            continue
        beh = behaviour(tok, singles)
        if beh in known:
            continue
        if sum(bool(run_out) for (w, x), run_out in zip(singles, beh) if w.etype[x] == "person") < len(persons) / 2:
            continue
        known.add(beh)
        by_name[tok.name] = tok
        entries.append(Entry(tok, "person", out_type, 1.0 / (k + 1)))
    return by_name, entries
