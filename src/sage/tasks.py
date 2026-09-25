"""Induction tasks built from the planted library, and evaluator-owned splits.

A task is a hidden target program. The solver receives only a `Task`: a few
demonstrations (world, query entity x, answer). The evaluator keeps a
`HiddenTask` with the target and held-out queries in three strata:

  iid       fresh worlds from the training regime
  size      much larger worlds (80-150 people)
  topology  deeper families, hub-shaped friend graphs, chain-shaped places

Demonstrations favour informative queries (non-empty answers) but always
include one uniformly chosen query entity, so edge cases such as people with
no siblings appear. Every task and split is identified by a hash, and the
split manifest records those hashes with the generator version.
"""

from __future__ import annotations

import hashlib
import math
import random
from dataclasses import dataclass

from .library import CONNECTOR_TYPE, CONNECTORS, FILTERS, Entry
from .machine import Token, run, token
from .worlds import REGIMES, RELATIONS, World, generate_world

GENERATOR_VERSION = "0a.1"
STRATA = ("iid", "size", "topology")
STRATUM_REGIME = {"iid": "train", "size": "size", "topology": "topology"}


@dataclass(frozen=True)
class Example:
    world: World
    x: int
    answer: frozenset


@dataclass(frozen=True)
class Task:
    """Everything the solver may see."""

    task_id: str
    demos: tuple[Example, ...]


@dataclass(frozen=True)
class HiddenTask:
    """Owned by the evaluator; never passed to a solver."""

    task_id: str
    target: tuple[str, ...]  # token names at the top level
    queries: dict  # stratum -> tuple[Example, ...]


def world_digest(w: World) -> str:
    parts = [w.etype, w.color, w.size] + [tuple(sorted(w.edges(r))) for r in RELATIONS]
    return hashlib.sha256(repr(parts).encode()).hexdigest()


def examples_digest(examples) -> str:
    rows = [(world_digest(e.world), e.x, tuple(sorted(e.answer))) for e in examples]
    return hashlib.sha256(repr(rows).encode()).hexdigest()


def sample_target(rng: random.Random, entries: list[Entry], min_length: int,
                  single: bool = False) -> tuple[str, ...] | None:
    """2-3 planted entries in sequence (1 if `single`), with optional connectors and a final filter."""
    parts: list[str] = []
    length = 0
    cur_type = "person"
    n_entries = 1 if single else rng.choice((2, 3))
    for i in range(n_entries):
        eligible = [e for e in entries if e.in_type == cur_type]
        if not eligible:
            return None
        e = rng.choices(eligible, [e.weight for e in eligible])[0]
        parts.append(e.token.name)
        length += e.token.length
        cur_type = e.out_type
        if i < n_entries - 1 and CONNECTORS[cur_type] and rng.random() < 0.3:
            c = rng.choice(CONNECTORS[cur_type])
            parts.append(c)
            length += 1
            cur_type = CONNECTOR_TYPE[c]
    if rng.random() < 0.5:
        parts.append(rng.choice(FILTERS))
        length += 1
    return tuple(parts) if length >= min_length else None


# Type-respecting relation steps: instruction name -> type of its output.
_STEPS = {
    "person": {"out.parent": "person", "in.parent": "person", "out.friend": "person", "clos.parent": "person",
               "rclos.parent": "person", "out.lives_in": "place", "out.owns": "item"},
    "place": {"in.lives_in": "person", "out.near": "place", "out.inside": "place", "in.inside": "place",
              "clos.inside": "place", "rclos.inside": "place"},
    "item": {"in.owns": "person"},
}


def _random_macro(rng: random.Random, start: str):
    """A fresh random macro that respects entity types: a 2-3 step relation path,
    or push + a path returning to the start type + a set operation."""
    for _ in range(100):
        steps, t = [], start
        for _ in range(rng.choice((2, 3))):
            name = rng.choice(sorted(_STEPS[t]))
            steps.append(name)
            t = _STEPS[t][name]
        if rng.random() < 0.5:
            return steps, t
        if t == start:
            return ["push"] + steps + [rng.choice(("minus_pop", "inter_pop", "union_pop"))], t
    return steps, t


def sample_control_target(rng: random.Random, base: list[Token], min_length: int, single: bool = False):
    """Same shape as a planted target, but built from 2-3 *fresh* random macros.

    Macros are drawn per task (see `_random_macro`), so nothing recurs across
    control tasks except by chance and a library learned from a control
    stream has no task-family structure to exploit.
    """
    by_name = {b.name: b for b in base}
    names, program, length, t = [], [], 0, "person"
    for _ in range(1 if single else rng.choice((2, 3))):
        steps, t = _random_macro(rng, t)
        tok = token("[" + " ".join(steps) + "]", tuple(by_name[n].body[0] for n in steps))
        names.append(tok.name)
        program.append(tok)
        length += tok.length
    if rng.random() < 0.5:
        f = rng.choice(FILTERS)
        names.append(f)
        program.append(by_name[f])
        length += 1
    return (tuple(names), program) if length >= min_length else None


def _pick_examples(rng, program, regime, count, informative, max_worlds=40):
    """`count` examples from fresh worlds: `informative` of them with non-empty answers."""
    examples = []
    for _ in range(max_worlds):
        if len(examples) == count:
            return tuple(examples)
        w = generate_world(rng, REGIMES[regime])
        people = w.of_type("person")
        if len(examples) < informative:
            rng.shuffle(people)
            for x in people:
                ans = run(w, x, program)
                if ans:
                    examples.append(Example(w, x, ans))
                    break
        else:
            x = rng.choice(people)
            examples.append(Example(w, x, run(w, x, program)))
    return None


def ambiguous(target: tuple[str, ...], tokens: dict[str, Token], demos, queries: dict) -> bool:
    """Does deleting one step of the target still fit the demos but change a held-out answer?

    Such a task is under-determined: a solver that prefers short programs will
    find the shorter variant and be wrong on unseen worlds.
    """
    for i in range(len(target)):
        variant = [tokens[n] for n in target[:i] + target[i + 1:]]
        if variant and all(run(d.world, d.x, variant) == d.answer for d in demos):
            if any(run(q.world, q.x, variant) != q.answer for qs in queries.values() for q in qs):
                return True
    return False


def generate_task(rng: random.Random, tokens: dict[str, Token], entries: list[Entry],
                  n_demos: int, n_queries: int, min_length: int = 6, short_len: int = 3,
                  well_posed: bool = False, structure: str = "planted", single_share: float = 0.0,
                  max_tries: int = 500, stats: dict | None = None):
    """One task whose demonstrations no program of <= `short_len` base instructions fits.

    `structure` is "planted" (targets built from the planted library) or
    "control" (targets built from fresh random macros; see
    `sample_control_target`). With `well_posed`, also reject tasks that are
    `ambiguous` (the generator acting as a teacher who picks demonstrations
    that pin the target down). `single_share` is the probability that a task
    uses a single entry or macro (a curriculum of stepping stones); at 0 the
    random stream is identical to earlier versions.
    """
    from .search import short_program_exists  # search imports Task from here

    stats = stats if stats is not None else {}
    base = [t for t in tokens.values() if t.is_base]
    for _ in range(max_tries):
        single = single_share > 0 and rng.random() < single_share
        min_len = 4 if single else min_length
        if structure == "planted":
            target = sample_target(rng, entries, min_len, single)
            if target is None:
                continue
            program = [tokens[name] for name in target]
        else:
            drawn = sample_control_target(rng, base, min_len, single)
            if drawn is None:
                continue
            target, program = drawn
        demos = _pick_examples(rng, program, "train", n_demos, informative=n_demos - 1)
        if demos is None or len({d.answer for d in demos}) < 2:
            stats["rejected_degenerate"] = stats.get("rejected_degenerate", 0) + 1
            continue
        if short_program_exists(Task("", demos), base, short_len):
            stats["rejected_short"] = stats.get("rejected_short", 0) + 1
            continue
        queries = {}
        for stratum in STRATA:
            q = _pick_examples(rng, program, STRATUM_REGIME[stratum], n_queries,
                               informative=math.ceil(0.8 * n_queries))
            if q is None:
                break
            queries[stratum] = q
        else:
            if well_posed and structure == "planted" and ambiguous(target, tokens, demos, queries):
                stats["rejected_ambiguous"] = stats.get("rejected_ambiguous", 0) + 1
                continue
            task_id = hashlib.sha256((repr(target) + examples_digest(demos)).encode()).hexdigest()[:16]
            stats["accepted"] = stats.get("accepted", 0) + 1
            return Task(task_id, demos), HiddenTask(task_id, target, queries)
    raise RuntimeError("could not generate a well-posed task")


def make_split(name: str, seed: int, n_tasks: int, tokens, entries, n_demos: int, n_queries: int = 5,
               well_posed: bool = False, structure: str = "planted", single_share: float = 0.0,
               stats: dict | None = None):
    """A deterministic split; different names give disjoint random streams."""
    tasks, hidden = [], []
    for i in range(n_tasks):
        rng = random.Random(f"{GENERATOR_VERSION}:{name}:{seed}:{i}")
        t, h = generate_task(rng, tokens, entries, n_demos, n_queries, well_posed=well_posed,
                             structure=structure, single_share=single_share, stats=stats)
        tasks.append(t)
        hidden.append(h)
    return tasks, hidden


def manifest(name: str, seed: int, tasks, hidden) -> dict:
    return {
        "split": name,
        "seed": seed,
        "generator_version": GENERATOR_VERSION,
        "tasks": [
            {
                "task_id": t.task_id,
                "target": list(h.target),
                "demos_sha256": examples_digest(t.demos),
                "queries_sha256": {s: examples_digest(q) for s, q in h.queries.items()},
            }
            for t, h in zip(tasks, hidden)
        ],
    }
