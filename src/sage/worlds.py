"""Typed relational worlds: people, places and items linked by labelled relations.

A world is generated in a canonical order and then relabelled with a random
permutation, so entity ids carry no information about roles or generation
order. Each relation is stored as out- and in-adjacency (frozensets), so edge
order cannot affect any answer.

Regimes control the size and topology of worlds. Training and test regimes
differ in family depth, friend-graph shape and place-tree shape, which gives
the size and topology shifts used in evaluation.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

TYPES = ("person", "place", "item")
COLORS = ("red", "green", "blue")
SIZES = ("small", "large")
RELATIONS = ("parent", "friend", "lives_in", "inside", "owns", "near")
TRANSITIVE = ("parent", "inside")  # relations whose closure is a primitive


@dataclass(frozen=True)
class Regime:
    name: str
    people: tuple[int, int]  # inclusive range
    family_depth: tuple[int, int]  # generations, inclusive range
    friend_graph: str  # "er" (Erdős–Rényi) or "hub" (preferential attachment)
    place_tree: str  # "balanced" or "chain"


REGIMES = {
    "train": Regime("train", (12, 24), (3, 3), "er", "balanced"),
    "size": Regime("size", (80, 150), (3, 3), "er", "balanced"),
    "topology": Regime("topology", (12, 24), (5, 6), "hub", "chain"),
}


@dataclass(frozen=True)
class World:
    etype: tuple[str, ...]
    color: tuple[str, ...]
    size: tuple[str, ...]
    out: dict  # relation -> tuple of frozensets, indexed by entity
    inn: dict

    @property
    def n(self) -> int:
        return len(self.etype)

    def of_type(self, t: str) -> list[int]:
        return [e for e, et in enumerate(self.etype) if et == t]

    def edges(self, rel: str) -> set[tuple[int, int]]:
        return {(u, v) for u, vs in enumerate(self.out[rel]) for v in vs}

    def relabel(self, perm: list[int]) -> "World":
        """The same world with entity e renamed perm[e]."""
        inv = [0] * self.n
        for e, p in enumerate(perm):
            inv[p] = e
        return build_world(
            [self.etype[inv[p]] for p in range(self.n)],
            [self.color[inv[p]] for p in range(self.n)],
            [self.size[inv[p]] for p in range(self.n)],
            {r: [(perm[u], perm[v]) for u, v in self.edges(r)] for r in RELATIONS},
        )


def build_world(etype, color, size, edges: dict) -> World:
    n = len(etype)
    out, inn = {}, {}
    for rel in RELATIONS:
        o = [set() for _ in range(n)]
        i = [set() for _ in range(n)]
        for u, v in edges.get(rel, ()):
            o[u].add(v)
            i[v].add(u)
        out[rel] = tuple(frozenset(s) for s in o)
        inn[rel] = tuple(frozenset(s) for s in i)
    return World(tuple(etype), tuple(color), tuple(size), out, inn)


def generate_world(rng: random.Random, regime: Regime) -> World:
    n_people = rng.randint(*regime.people)
    n_places = max(3, n_people // 3)
    n_items = max(2, n_people // 2)
    people = list(range(n_people))
    places = list(range(n_people, n_people + n_places))
    items = list(range(n_people + n_places, n_people + n_places + n_items))
    edges: dict[str, set[tuple[int, int]]] = {r: set() for r in RELATIONS}

    # Family forest: people are spread over generations; each person below the
    # first generation has two parents, a couple drawn from the generation
    # above with a preference for couples that already have children.
    depth = min(rng.randint(*regime.family_depth), n_people // 2)
    gens: list[list[int]] = [[] for _ in range(depth)]
    for i, p in enumerate(rng.sample(people, n_people)):
        gens[i % depth].append(p)
    for g in range(1, depth):
        above = gens[g - 1][:]
        rng.shuffle(above)
        couples = [tuple(above[i:i + 2]) for i in range(0, len(above) - 1, 2)]
        if not couples:
            continue
        weights = [1.0] * len(couples)
        for child in gens[g]:
            k = rng.choices(range(len(couples)), weights)[0]
            weights[k] += 2.0
            for parent in couples[k]:
                edges["parent"].add((child, parent))

    # Friends, stored in both directions.
    if regime.friend_graph == "er":
        p = min(1.0, 3.0 / max(1, n_people - 1))
        for a in people:
            for b in people:
                if a < b and rng.random() < p:
                    edges["friend"] |= {(a, b), (b, a)}
    else:  # hub: preferential attachment, one or two links per newcomer
        degree = {people[0]: 1}
        for a in people[1:]:
            targets = set()
            for _ in range(rng.choice((1, 2))):
                targets.add(rng.choices(list(degree), [d for d in degree.values()])[0])
            for b in targets:
                edges["friend"] |= {(a, b), (b, a)}
                degree[b] += 1
            degree[a] = len(targets)

    # Places: a containment tree via `inside`, plus a `near` ring with chords.
    for i, place in enumerate(places[1:], start=1):
        if regime.place_tree == "balanced":
            parent = places[(i - 1) // 3]
        else:
            parent = places[i - 1] if rng.random() < 0.8 else places[rng.randrange(i)]
        edges["inside"].add((place, parent))
    for i, place in enumerate(places):
        other = places[(i + 1) % n_places]
        if other != place:
            edges["near"] |= {(place, other), (other, place)}
    for _ in range(n_places // 3):
        a, b = rng.sample(places, 2)
        edges["near"] |= {(a, b), (b, a)}

    # Everyone lives somewhere (biased towards the deeper, later places);
    # every item has one owner.
    for person in people:
        k = min(n_places - 1, int(n_places * rng.random() ** 0.5))
        edges["lives_in"].add((person, places[k]))
    for item in items:
        edges["owns"].add((rng.choice(people), item))

    n = n_people + n_places + n_items
    etype = ["person"] * n_people + ["place"] * n_places + ["item"] * n_items
    color = [rng.choice(COLORS) for _ in range(n)]
    size = [rng.choice(SIZES) for _ in range(n)]
    world = build_world(etype, color, size, edges)
    perm = list(range(n))
    rng.shuffle(perm)
    return world.relabel(perm)
