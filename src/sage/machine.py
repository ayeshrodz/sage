"""A tiny instruction set over sets of entities, with exact work accounting.

This is SAGE's symbolic core for experiment 0. A program is a sequence of
tokens. A token is either a base instruction or a library entry (a macro: a
named, flattened sequence of base instructions). Execution state is a
*current* set plus a small stack of saved sets; a program starts from {x}, the
query entity, and its answer is the current set once the stack is empty.

Work is counted in element operations: one unit per entity or edge touched
(an `out` over S touches |S| entities plus their out-edges, a filter touches
|S|, a set operation touches both operands, push/swap/drop_x cost 1). This is
the deterministic cost used throughout experiment 0; wall time is secondary.
"""

from __future__ import annotations

from dataclasses import dataclass

from .worlds import COLORS, RELATIONS, SIZES, TRANSITIVE, TYPES, World

MAX_STACK = 3

# (stack items needed, net stack change) for each op
_STACK = {"push": (0, 1), "swap": (1, 0), "minus_pop": (1, -1), "union_pop": (1, -1), "inter_pop": (1, -1)}


@dataclass(frozen=True)
class Instr:
    op: str
    arg: str = ""

    @property
    def name(self) -> str:
        return f"{self.op}.{self.arg}" if self.arg else self.op


@dataclass(frozen=True)
class Token:
    """A base instruction or a macro, with its stack signature precomputed."""

    name: str
    body: tuple[Instr, ...]
    parts: tuple[str, ...]  # names of the tokens it was written with
    need: int  # stack items that must be present before it runs
    rise: int  # highest stack growth while it runs
    delta: int  # net stack change

    @property
    def length(self) -> int:
        return len(self.body)

    @property
    def is_base(self) -> bool:
        return len(self.body) == 1 and self.parts == (self.name,)

    def applicable(self, depth: int) -> bool:
        return depth >= self.need and depth + self.rise <= MAX_STACK


def _signature(body: tuple[Instr, ...]) -> tuple[int, int, int]:
    depth = lowest = highest = 0
    for ins in body:
        need, change = _STACK.get(ins.op, (0, 0))
        lowest = min(lowest, depth - need)
        depth += change
        highest = max(highest, depth)
    return -lowest, highest, depth


def token(name: str, body: tuple[Instr, ...], parts: tuple[str, ...] | None = None) -> Token:
    need, rise, delta = _signature(body)
    return Token(name, body, parts if parts is not None else (name,), need, rise, delta)


def base_instructions() -> list[Token]:
    instrs = []
    for rel in RELATIONS:
        instrs.append(Instr("out", rel))
        if rel not in ("friend", "near"):  # symmetric relations: in == out
            instrs.append(Instr("in", rel))
    for rel in TRANSITIVE:
        instrs += [Instr("clos", rel), Instr("rclos", rel)]
    instrs += [Instr("only_color", c) for c in COLORS]
    instrs += [Instr("only_size", s) for s in SIZES]
    instrs += [Instr("only_type", t) for t in TYPES]
    instrs += [Instr(op) for op in ("push", "swap", "minus_pop", "union_pop", "inter_pop", "drop_x")]
    return [token(i.name, (i,)) for i in instrs]


def macro(name: str, parts: list[str], known: dict[str, Token]) -> Token:
    """A library entry written in terms of already-known tokens."""
    body = tuple(ins for p in parts for ins in known[p].body)
    return token(name, body, tuple(parts))


class Counter:
    __slots__ = ("ops", "instrs")

    def __init__(self) -> None:
        self.ops = 0
        self.instrs = 0


def _closure(adj, start: frozenset, counter: Counter) -> frozenset:
    seen: set[int] = set()
    frontier = list(start)
    work = 0
    while frontier:
        u = frontier.pop()
        nbrs = adj[u]
        work += 1 + len(nbrs)
        for v in nbrs:
            if v not in seen:
                seen.add(v)
                frontier.append(v)
    counter.ops += work
    return frozenset(seen)


def execute(world: World, x: int, cur: frozenset, stack: tuple, body: tuple[Instr, ...], counter: Counter):
    """Run instructions from state (cur, stack). The caller checks stack validity."""
    for ins in body:
        op = ins.op
        counter.instrs += 1
        if op == "out" or op == "in":
            adj = (world.out if op == "out" else world.inn)[ins.arg]
            parts = [adj[u] for u in cur]
            counter.ops += len(cur) + sum(len(p) for p in parts)
            cur = frozenset().union(*parts) if parts else frozenset()
        elif op == "clos":
            cur = _closure(world.out[ins.arg], cur, counter)
        elif op == "rclos":
            cur = _closure(world.inn[ins.arg], cur, counter)
        elif op == "only_color":
            counter.ops += len(cur)
            cur = frozenset(u for u in cur if world.color[u] == ins.arg)
        elif op == "only_size":
            counter.ops += len(cur)
            cur = frozenset(u for u in cur if world.size[u] == ins.arg)
        elif op == "only_type":
            counter.ops += len(cur)
            cur = frozenset(u for u in cur if world.etype[u] == ins.arg)
        elif op == "push":
            counter.ops += 1
            stack = stack + (cur,)
        elif op == "swap":
            counter.ops += 1
            cur, stack = stack[-1], stack[:-1] + (cur,)
        elif op == "drop_x":
            counter.ops += 1
            cur = cur - {x}
        else:  # set operation with the popped set
            top, stack = stack[-1], stack[:-1]
            counter.ops += len(cur) + len(top)
            if op == "minus_pop":
                cur = cur - top
            elif op == "union_pop":
                cur = cur | top
            else:
                cur = cur & top
    return cur, stack


def run(world: World, x: int, program: list[Token] | tuple[Token, ...], counter: Counter | None = None) -> frozenset:
    """Answer of a complete program (stack must be balanced) on query entity x."""
    counter = counter or Counter()
    body = tuple(ins for t in program for ins in t.body)
    need, rise, delta = _signature(body)
    if need or delta or rise > MAX_STACK:
        raise ValueError("program must keep the stack balanced and within MAX_STACK")
    cur, _ = execute(world, x, frozenset((x,)), (), body, counter)
    return cur
