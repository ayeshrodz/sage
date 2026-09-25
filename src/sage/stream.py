"""Task streams for stage 0d: recurring task types, each seen as fresh instances.

A *type* is a hidden target program drawn from the planted task generator
(the same acceptance filters as every earlier stage). An *instance* is a
fresh draw of a type: new demonstration worlds and query entities, plus
held-out iid queries for the evaluator. Instances pass the same degeneracy
and "no program of <= 3 base instructions fits" checks as every task since
0a; demonstrations are redrawn if they fail.

  zipf_stream     n_types types; each position draws type k (in a random
                  ranking) with probability proportional to 1 / k^exponent
  norecur_stream  n instances of n distinct types: nothing recurs
"""

from __future__ import annotations

import hashlib
import math
import random
from dataclasses import dataclass

from .machine import Token
from .search import short_program_exists
from .tasks import GENERATOR_VERSION, Task, _pick_examples, examples_digest, generate_task


@dataclass(frozen=True)
class Instance:
    index: int
    type_id: int
    target: tuple[str, ...]
    task: Task  # the solver's view: demonstrations only
    queries: tuple  # held-out iid queries, evaluator only


def make_instance(rng: random.Random, program: list[Token], base: list[Token], n_demos: int = 4,
                  n_queries: int = 5, max_tries: int = 30):
    """Fresh demonstrations and queries for a type, or None if none pass the checks."""
    for _ in range(max_tries):
        demos = _pick_examples(rng, program, "train", n_demos, informative=n_demos - 1)
        if demos is None or len({d.answer for d in demos}) < 2:
            continue
        if short_program_exists(Task("", demos), base, 3):
            continue
        queries = _pick_examples(rng, program, "train", n_queries, informative=math.ceil(0.8 * n_queries))
        if queries is None:
            continue
        return demos, queries
    return None


def _task_id(target, demos) -> str:
    return hashlib.sha256((repr(target) + examples_digest(demos)).encode()).hexdigest()[:16]


def zipf_stream(name: str, seed: int, n_types: int, n_instances: int, exponent: float, tokens: dict, entries):
    base = [t for t in tokens.values() if t.is_base]
    types: list[tuple[str, ...]] = []
    seen: set = set()
    k = 0
    while len(types) < n_types:
        rng = random.Random(f"{GENERATOR_VERSION}:{name}:type:{seed}:{k}")
        k += 1
        _, h = generate_task(rng, tokens, entries, 4, 1)
        if h.target not in seen:
            seen.add(h.target)
            types.append(h.target)
    ranking = list(range(n_types))
    random.Random(f"{name}:rank:{seed}").shuffle(ranking)
    weights = [1.0 / (r + 1) ** exponent for r in range(n_types)]
    draw = random.Random(f"{name}:draw:{seed}")
    instances = []
    for i in range(n_instances):
        for attempt in range(20):
            tid = ranking[draw.choices(range(n_types), weights)[0]]
            made = make_instance(random.Random(f"{GENERATOR_VERSION}:{name}:inst:{seed}:{i}:{attempt}"),
                                 [tokens[n] for n in types[tid]], base)
            if made:
                break
        else:
            raise RuntimeError(f"could not draw instance {i}")
        demos, queries = made
        instances.append(Instance(i, tid, types[tid], Task(_task_id(types[tid], demos), demos), queries))
    return instances


def norecur_stream(name: str, seed: int, n: int, tokens: dict, entries):
    seen: set = set()
    instances = []
    k = 0
    while len(instances) < n:
        rng = random.Random(f"{GENERATOR_VERSION}:{name}:{seed}:{k}")
        k += 1
        task, h = generate_task(rng, tokens, entries, 4, 5)
        if h.target in seen:
            continue
        seen.add(h.target)
        i = len(instances)
        instances.append(Instance(i, i, h.target, task, h.queries["iid"]))
    return instances


def stream_manifest(name: str, seed: int, instances) -> dict:
    return {
        "stream": name, "seed": seed, "generator_version": GENERATOR_VERSION,
        "instances": [{"index": s.index, "type_id": s.type_id, "target": list(s.target),
                       "demos_sha256": examples_digest(s.task.demos), "queries_sha256": examples_digest(s.queries)}
                      for s in instances],
    }
