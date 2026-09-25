"""Requests and streams for stage 1a.

A request shows 3 input -> output examples of one transformation and asks for
5 new inputs to be transformed. The gold outputs are kept for the evaluator.

  zipf_stream     n requests; type k (in a random ranking) occurs with
                  probability proportional to 1 / k^exponent
  norecur_stream  every type exactly once, in random order
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass

from .transforms import TYPES

VERSION = "1a.1"


@dataclass(frozen=True)
class Request:
    index: int
    type_id: int
    examples: tuple[tuple[str, str], ...]  # visible to systems
    queries: tuple[str, ...]  # visible to systems
    gold: tuple[str, ...]  # evaluator only


def make_request(rng: random.Random, index: int, type_id: int, n_examples: int = 3, n_queries: int = 5) -> Request:
    t = TYPES[type_id]
    for _ in range(200):
        inputs: list[str] = []
        for _ in range(1000):  # distinct inputs, with a guard for types with few possible inputs
            if len(inputs) == n_examples + n_queries:
                break
            x = t.gen(rng)
            if x not in inputs:
                inputs.append(x)
        else:
            raise RuntimeError(f"type {t.name} cannot produce {n_examples + n_queries} distinct inputs")
        outputs = [t.f(x) for x in inputs]
        if len(set(outputs[:n_examples])) == n_examples:  # informative examples
            break
    return Request(index, type_id, tuple(zip(inputs[:n_examples], outputs[:n_examples])),
                   tuple(inputs[n_examples:]), tuple(outputs[n_examples:]))


def zipf_stream(name: str, n: int, exponent: float = 1.0, seed: int = 0) -> list[Request]:
    ranking = list(range(len(TYPES)))
    random.Random(f"{VERSION}:{name}:rank:{seed}").shuffle(ranking)
    weights = [1.0 / (k + 1) ** exponent for k in range(len(TYPES))]
    draw = random.Random(f"{VERSION}:{name}:draw:{seed}")
    return [make_request(random.Random(f"{VERSION}:{name}:{seed}:{i}"), i, ranking[draw.choices(range(len(TYPES)), weights)[0]])
            for i in range(n)]


def norecur_stream(name: str, seed: int = 0) -> list[Request]:
    order = list(range(len(TYPES)))
    random.Random(f"{VERSION}:{name}:order:{seed}").shuffle(order)
    return [make_request(random.Random(f"{VERSION}:{name}:{seed}:{i}"), i, tid) for i, tid in enumerate(order)]


def manifest(name: str, requests: list[Request]) -> dict:
    return {"stream": name, "version": VERSION, "requests": [
        {"index": q.index, "type": TYPES[q.type_id].name,
         "sha256": hashlib.sha256(repr((q.examples, q.queries, q.gold)).encode()).hexdigest()} for q in requests]}
