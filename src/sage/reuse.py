"""Reuse memory for stage 0d: remember verified programs, recognise recurring tasks cheaply.

The memory stores every program the system finds that fits a task's
demonstrations, with a *trust* count (instances it has fitted). A new task is
keyed by the entity types in its demonstrated answers (cheap, visible to the
solver, identical across instances of a type). Stored programs under that key
are verified on the new demonstrations in order of trust, then most recent
use. Each verification checks the first demonstration first and stops at the
first mismatch. The first program that fits every demonstration answers the
task (a hit); at most `max_checks` programs are verified per task. On a miss
the caller runs its usual search and stores what it finds; identical
programs are merged.

All work is counted in element operations: reading the answers to form the
key, running candidate programs during verification, and one unit per
candidate considered for bookkeeping.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .machine import Counter, Token, run


@dataclass
class Stored:
    body: tuple[str, ...]  # flat instruction names, the identity of a program
    program: list[Token]
    trust: int = 1
    last_used: int = 0


@dataclass
class ReuseMemory:
    max_checks: int = 50
    by_key: dict = field(default_factory=dict)  # key -> list[Stored]
    by_body: dict = field(default_factory=dict)  # (key, body) -> Stored

    @staticmethod
    def key(task, counter: Counter) -> frozenset:
        types = set()
        for d in task.demos:
            counter.ops += len(d.answer)
            types.update(d.world.etype[e] for e in d.answer)
        return frozenset(types)

    @staticmethod
    def verify(program: list[Token], task, counter: Counter) -> bool:
        return all(run(d.world, d.x, program, counter) == d.answer for d in task.demos)

    def lookup(self, key, task, counter: Counter) -> Stored | None:
        candidates = sorted(self.by_key.get(key, []), key=lambda s: (-s.trust, -s.last_used))[: self.max_checks]
        counter.ops += len(candidates)
        for s in candidates:
            if self.verify(s.program, task, counter):
                return s
        return None

    def store(self, key, program: list[Token], clock: int) -> Stored:
        body = tuple(i.name for t in program for i in t.body)
        s = self.by_body.get((key, body))
        if s is not None:
            s.trust += 1
            s.last_used = clock
            return s
        s = Stored(body, list(program), 1, clock)
        self.by_body[(key, body)] = s
        self.by_key.setdefault(key, []).append(s)
        return s

    def size(self) -> int:
        return len(self.by_body)


def simulate(instances, fallback: list[dict], program_of, max_checks: int = 50) -> list[dict]:
    """Run a reuse memory over a stream, falling back to precomputed search results.

    `fallback[i]` is the memoryless system's result on instance i (found,
    work, and its program); a miss costs exactly that search, so the reuse
    system and the memoryless one are compared on identical instances with
    identical fallbacks. `program_of(result)` rebuilds the program tokens.
    """
    memory = ReuseMemory(max_checks)
    rows = []
    for i, inst in enumerate(instances):
        c = Counter()
        key = memory.key(inst.task, c)
        hit = memory.lookup(key, inst.task, c)
        if hit is not None:
            hit.trust += 1
            hit.last_used = i
            program, found, mode, trust = hit.program, True, "hit", hit.trust - 1
            work = c.ops
        else:
            res = fallback[i]
            found, mode, trust = res["found"], "search", 0
            program = program_of(res) if found else []
            work = c.ops + res["work"]
            if found:
                memory.store(key, program, i)
        correct = found and all(run(q.world, q.x, program) == q.answer for q in inst.queries)
        rows.append({"index": i, "type_id": inst.type_id, "mode": mode, "found": found, "correct": correct,
                     "work": work, "lookup_work": c.ops, "trust_used": trust, "memory_size": memory.size()})
    return rows

