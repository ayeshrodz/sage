"""The planted library (the hidden structure tasks are built from) and distractors.

Planted entries are written in terms of base instructions and earlier entries,
so the library is hierarchical (cousins uses aunts_uncles, which uses
siblings). Each entry has an input and output entity type, used only by the
task generator to build well-typed targets; search itself is untyped.

Distractors are random stack-balanced instruction sequences, kept only if their
behaviour on a fixed set of probe inputs differs from every base instruction,
planted entry and earlier distractor. They stand in for library entries that
are irrelevant to the current task stream.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from .machine import MAX_STACK, Token, base_instructions, macro, run, token
from .worlds import REGIMES, World, generate_world

# name, parts, input type, output type. Listed from most to least frequent:
# task generation uses Zipf weights 1/rank over this order.
PLANTED_SPEC = [
    ("siblings", ["push", "out.parent", "in.parent", "minus_pop"], "person", "person"),
    ("grandparents", ["out.parent", "out.parent"], "person", "person"),
    ("housemates", ["push", "out.lives_in", "in.lives_in", "minus_pop"], "person", "person"),
    ("friends_of_friends", ["push", "out.friend", "out.friend", "minus_pop"], "person", "person"),
    ("aunts_uncles", ["out.parent", "siblings"], "person", "person"),
    ("cousins", ["aunts_uncles", "in.parent"], "person", "person"),
    ("grandchildren", ["in.parent", "in.parent"], "person", "person"),
    ("nieces_nephews", ["siblings", "in.parent"], "person", "person"),
    ("home_region", ["out.lives_in", "clos.inside"], "person", "place"),
    ("neighbours", ["push", "out.lives_in", "out.near", "in.lives_in", "minus_pop"], "person", "person"),
    ("local_friends", ["push", "housemates", "swap", "out.friend", "inter_pop"], "person", "person"),
    ("extended_family", ["push", "grandparents", "rclos.parent", "minus_pop"], "person", "person"),
    ("family_items", ["push", "siblings", "union_pop", "out.owns"], "person", "item"),
]

# Base instructions the generator may place between planted entries.
CONNECTORS = {
    "person": ["out.friend", "out.parent", "in.parent", "out.lives_in", "out.owns"],
    "place": ["in.lives_in", "out.near", "out.inside"],
    "item": [],
}
CONNECTOR_TYPE = {"out.friend": "person", "out.parent": "person", "in.parent": "person",
                  "out.lives_in": "place", "out.owns": "item", "in.lives_in": "person",
                  "out.near": "place", "out.inside": "place"}
FILTERS = ["only_color.red", "only_color.green", "only_color.blue", "only_size.small", "only_size.large"]


@dataclass(frozen=True)
class Entry:
    token: Token
    in_type: str
    out_type: str
    weight: float


def base_tokens() -> dict[str, Token]:
    return {t.name: t for t in base_instructions()}


def planted_library() -> tuple[dict[str, Token], list[Entry]]:
    """All tokens by name (base + planted) and the planted entries in order."""
    known = base_tokens()
    entries = []
    for rank, (name, parts, tin, tout) in enumerate(PLANTED_SPEC, start=1):
        tok = macro(name, parts, known)
        known[name] = tok
        entries.append(Entry(tok, tin, tout, 1.0 / rank))
    return known, entries


def probe_inputs(seed: int = 12345, worlds: int = 3, per_world: int = 5) -> list[tuple[World, int]]:
    rng = random.Random(f"probe:{seed}")
    probes = []
    for _ in range(worlds):
        w = generate_world(rng, REGIMES["train"])
        people = w.of_type("person")
        probes += [(w, x) for x in rng.sample(people, min(per_world, len(people)))]
    return probes


def fingerprint(tok: Token, probes) -> tuple[frozenset, ...]:
    return tuple(run(w, x, [tok]) for w, x in probes)


def distractors(count: int, seed: int = 0, lengths=(2, 3, 4, 5)) -> list[Token]:
    """`count` semantically distinct, stack-balanced random macros (nested prefixes across counts)."""
    rng = random.Random(f"distractors:{seed}")
    base = [t for t in base_instructions()]
    probes = probe_inputs()
    _, planted = planted_library()
    seen = {fingerprint(t, probes) for t in base if t.need == 0 and t.delta == 0 and t.rise == 0}
    seen |= {fingerprint(e.token, probes) for e in planted}
    seen.add(tuple(frozenset((x,)) for _, x in probes))  # identity
    out: list[Token] = []
    attempts = 0
    while len(out) < count:
        attempts += 1
        if attempts > 200 * (count + 10):
            raise RuntimeError("could not generate enough distinct distractors")
        parts = [rng.choice(base) for _ in range(rng.choice(lengths))]
        body = tuple(i for p in parts for i in p.body)
        tok = token(f"d{len(out)}", body, tuple(p.name for p in parts))
        if tok.need or tok.delta or tok.rise > MAX_STACK:
            continue
        fp = fingerprint(tok, probes)
        if fp in seen or all(not s for s in fp):
            continue
        seen.add(fp)
        out.append(tok)
    return out
