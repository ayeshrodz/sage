"""Dreams: practice tasks the learner invents from its own library.

A dream is a short program sampled from the current library (learned entries
preferred, base relation steps otherwise, sometimes a final filter), run on
worlds the learner has already seen in its training demonstrations. It yields
a task whose program is known, which trains the guide to recognise entries
before they ever appear in a solved task (the "sleep" half of DreamCoder).

Programs are kept well-typed using type signatures measured empirically: a
token is usable from entity type t if it gives non-empty answers on sampled
entities of type t, and its output type is the majority type of those answers.
All execution is counted.
"""

from __future__ import annotations

import random
from collections import Counter as Tally

from .machine import MAX_STACK, Counter, Token, run
from .tasks import Example, Task
from .worlds import TYPES

FILTERS = ("only_color.red", "only_color.green", "only_color.blue", "only_size.small", "only_size.large")


def standalone(tok: Token) -> bool:
    return tok.need == 0 and tok.delta == 0 and tok.rise <= MAX_STACK


def type_signatures(tokens: list[Token], worlds, counter: Counter, per_type: int = 6, seed: str = "sig") -> dict:
    """token name -> {input type: output type} for standalone tokens."""
    rng = random.Random(seed)
    probes = {t: [] for t in TYPES}
    for w in worlds[:4]:
        for t in TYPES:
            ids = w.of_type(t)
            probes[t] += [(w, x) for x in rng.sample(ids, min(per_type // 2 + 1, len(ids)))]
    sigs: dict[str, dict[str, str]] = {}
    for tok in tokens:
        if not standalone(tok) or tok.name.startswith("only_"):
            continue
        for t in TYPES:
            outs = [run(w, x, [tok], counter) for w, x in probes[t]]
            nonempty = [(w, o) for (w, _), o in zip(probes[t], outs) if o]
            if len(nonempty) >= 2:
                kinds = Tally(w.etype[e] for w, o in nonempty for e in o)
                sigs.setdefault(tok.name, {})[t] = kinds.most_common(1)[0][0]
    return sigs


SET_OPS = ("minus_pop", "inter_pop", "union_pop")


def _path(rng: random.Random, sigs: dict, names: list[str], start: str, end: str | None, max_len: int = 3):
    """1-3 base steps from type `start` (ending at type `end` when given), or None."""
    for _ in range(20):
        steps, t = [], start
        for _ in range(rng.randint(1, max_len)):
            opts = [n for n in names if t in sigs[n]]
            if not opts:
                break
            n = rng.choice(opts)
            steps.append(n)
            t = sigs[n][t]
        if steps and (end is None or t == end):
            return steps, t
    return None


def sample_dream(rng: random.Random, by_name: dict[str, Token], sigs: dict, learned: list[str],
                 worlds, counter: Counter, n_demos: int = 4, p_learned: float = 0.5, p_idiom: float = 0.3,
                 weights: dict[str, float] | None = None):
    """One dreamed task and its program as a flat tuple of instruction names, or None.

    A program is 1-3 units. A unit is a learned entry (probability p_learned
    when one fits the current type), an instruction-set idiom (probability
    p_idiom: `push <path back to the same type> <set op>` or `<path> drop_x`),
    or a single base relation step. A final filter is added 30% of the time.
    Learned entries are drawn in proportion to `weights` (for example, how
    often each entry is used in solved tasks) when given.
    """
    base_steps = [n for n in sigs if n not in learned]
    parts: list[str] = []
    t = "person"
    for _ in range(rng.choices((1, 2, 3), (0.3, 0.4, 0.3))[0]):
        lrn = [n for n in learned if t in sigs.get(n, {})]
        r = rng.random()
        if lrn and r < p_learned:
            name = rng.choices(lrn, [weights.get(n, 1.0) for n in lrn])[0] if weights else rng.choice(lrn)
            parts.append(name)
            t = sigs[name][t]
            continue
        if r < p_learned + p_idiom:
            if rng.random() < 0.7:
                path = _path(rng, sigs, base_steps, t, t)
                if path:
                    parts += ["push"] + path[0] + [rng.choice(SET_OPS)]
                    continue
            elif t == "person":
                path = _path(rng, sigs, base_steps, t, "person")
                if path:
                    parts += path[0] + ["drop_x"]
                    continue
        bas = [n for n in base_steps if t in sigs[n]]
        if not bas:
            break
        name = rng.choice(bas)
        parts.append(name)
        t = sigs[name][t]
    if not parts:
        return None
    if rng.random() < 0.3:
        parts.append(rng.choice(FILTERS))
    program = [by_name[n] for n in parts]
    demos = []
    for k in range(n_demos):
        w = rng.choice(worlds)
        people = w.of_type("person")
        if k < n_demos - 1:
            for x in rng.sample(people, min(10, len(people))):
                ans = run(w, x, program, counter)
                if ans:
                    demos.append(Example(w, x, ans))
                    break
        else:
            x = rng.choice(people)
            demos.append(Example(w, x, run(w, x, program, counter)))
    if len(demos) < n_demos or len({d.answer for d in demos}) < 2:
        return None
    flat = tuple(i.name for tok in program for i in tok.body)
    return Task("dream", tuple(demos)), flat
