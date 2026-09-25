"""Best-first program search over tokens, with exact cost accounting.

Search state is, for every demonstration, the machine state (current set,
stack); two partial programs that reach the same state on every demonstration
are merged (observational equivalence). Candidates are ordered by a guide's
prior over tokens, children are generated lazily so that a sharp guide never
touches most of a large library, and tokens of equal prior are tried in a
per-task random order. Stack validity is checked before execution, so
ill-formed candidates cost nothing.

A program is accepted when the stack is empty and the current set equals the
demonstrated answer on every demonstration. That is the *runtime verifier*;
whether the program is actually right is decided later, by the evaluator, on
held-out queries.
"""

from __future__ import annotations

import heapq
import itertools
import math
from dataclasses import dataclass

from .machine import MAX_STACK, Counter, Token, execute
from .tasks import Task

ROUTE_DIM = 32  # multiply-adds to score one token in a brute-force router


def guide_costs(n_tokens: int, relevant: set[int], guide: str, delta: float = math.log(100), q: float = 0.9):
    """-log p(token) under a simulated guide (see pilot/utility_curve.py)."""
    if guide == "uniform" or not relevant:
        return [math.log(n_tokens)] * n_tokens
    r = len(relevant)
    if guide == "margin":
        z = r * math.exp(delta) + (n_tokens - r)
        p_rel, p_irr = math.exp(delta) / z, 1.0 / z
    elif guide == "mass":
        p_rel, p_irr = q / r, (1.0 - q) / max(1, n_tokens - r)
    else:
        raise ValueError(guide)
    return [-math.log(p_rel if i in relevant else p_irr) for i in range(n_tokens)]


@dataclass
class SearchResult:
    found: bool
    program: tuple[int, ...]  # token indices
    candidates: int
    ops: int  # element operations spent executing candidates
    instrs: int


def search(tokens: list[Token], costs: list[float], tiebreak: list[int], task: Task, budget: int) -> SearchResult:
    order = sorted(range(len(tokens)), key=lambda i: (costs[i], tiebreak[i]))
    by_depth = [[i for i in order if tokens[i].applicable(d)] for d in range(MAX_STACK + 1)]
    demos = task.demos
    goal = tuple(d.answer for d in demos)
    start = tuple((frozenset((d.x,)), ()) for d in demos)
    counter = Counter()
    if tuple(s[0] for s in start) == goal:
        return SearchResult(True, (), 0, 0, 0)

    tie = itertools.count()
    heap = [(costs[by_depth[0][0]], next(tie), 0.0, start, 0, (), 0)]
    visited = {start}
    candidates = 0
    while heap and candidates < budget:
        _, _, g, state, depth, program, rank = heapq.heappop(heap)
        options = by_depth[depth]
        tok_i = options[rank]
        if rank + 1 < len(options):
            sib = options[rank + 1]
            heapq.heappush(heap, (g + costs[sib], next(tie), g, state, depth, program, rank + 1))
        body = tokens[tok_i].body
        child = tuple(execute(d.world, d.x, cur, stack, body, counter) for d, (cur, stack) in zip(demos, state))
        candidates += 1
        if child in visited:
            continue
        child_depth = depth + tokens[tok_i].delta
        child_program = program + (tok_i,)
        if child_depth == 0 and all(c[0] == a for c, a in zip(child, goal)):
            return SearchResult(True, child_program, candidates, counter.ops, counter.instrs)
        visited.add(child)
        nxt = by_depth[child_depth]
        if nxt:
            child_g = g + costs[tok_i]
            heapq.heappush(heap, (child_g + costs[nxt[0]], next(tie), child_g, child, child_depth, child_program, 0))
    return SearchResult(False, (), candidates, counter.ops, counter.instrs)


def short_program_exists(task: Task, tokens: list[Token], max_len: int) -> bool:
    """Does any program of at most `max_len` tokens fit every demonstration?

    Breadth-first with observational equivalence. The task generator uses it
    with base instructions to reject targets that collapse to something short
    (siblings of siblings is mostly just {x}), so every kept task needs
    composition.
    """
    demos = task.demos
    goal = tuple(d.answer for d in demos)
    start = tuple((frozenset((d.x,)), ()) for d in demos)
    if tuple(s[0] for s in start) == goal:
        return True
    counter = Counter()
    visited = {start}
    frontier = [(start, 0)]
    for _ in range(max_len):
        nxt = []
        for state, depth in frontier:
            for tok in tokens:
                if not tok.applicable(depth):
                    continue
                child = tuple(execute(d.world, d.x, cur, stack, tok.body, counter) for d, (cur, stack) in zip(demos, state))
                if child in visited:
                    continue
                child_depth = depth + tok.delta
                if child_depth == 0 and all(c[0] == a for c, a in zip(child, goal)):
                    return True
                visited.add(child)
                nxt.append((child, child_depth))
        frontier = nxt
    return False


def search_policy(tokens: list[Token], policy, tiebreak: list[int], task: Task, budget: int,
                  max_calls: int = 300) -> SearchResult:
    """Best-first search whose token order is chosen per state by `policy`, evaluated lazily.

    `policy(state, last_token_name) -> (costs, work)` returns -log p for every
    token given the state the search is in, and the work it spent (perception
    plus scoring). A state's successors are ordered by its own costs, so the
    prior of a program is the product of the policy's step probabilities.

    Evaluation is deferred (as in Fast Downward): a new state is queued with
    its parent's best step cost as an estimate and is only perceived and
    scored if it is popped for expansion. After `max_calls` policy calls,
    states reuse their parent's order instead. The work of policy calls is
    included in `ops`.
    """
    T = len(tokens)
    demos = task.demos
    goal = tuple(d.answer for d in demos)
    start = tuple((frozenset((d.x,)), ()) for d in demos)
    counter = Counter()
    if tuple(s[0] for s in start) == goal:
        return SearchResult(True, (), 0, 0, 0)
    calls = 0
    extra = 0

    def ordering(state, depth, last, inherited):
        nonlocal calls, extra
        if calls < max_calls or inherited is None:
            costs, work = policy(state, last)
            calls += 1
            extra += work
        else:
            costs = inherited
        order = [i for i in sorted(range(T), key=lambda i: (costs[i], tiebreak[i])) if tokens[i].applicable(depth)]
        return costs, order

    tie = itertools.count()
    # Entries: (priority, tie, g, state, depth, program, rank, costs, order, last).
    # rank == -1 marks a state that has not been evaluated yet (costs are the parent's).
    heap = [(0.0, next(tie), 0.0, start, 0, (), -1, None, None, None)]
    visited = {start}
    candidates = 0
    while heap and candidates < budget:
        _, _, g, state, depth, program, rank, costs, order, last = heapq.heappop(heap)
        if rank == -1:
            costs, order = ordering(state, depth, last, costs)
            if order:
                heapq.heappush(heap, (g + costs[order[0]], next(tie), g, state, depth, program, 0, costs, order, last))
            continue
        tok_i = order[rank]
        if rank + 1 < len(order):
            sib = order[rank + 1]
            heapq.heappush(heap, (g + costs[sib], next(tie), g, state, depth, program, rank + 1, costs, order, last))
        body = tokens[tok_i].body
        child = tuple(execute(d.world, d.x, cur, stack, body, counter) for d, (cur, stack) in zip(demos, state))
        candidates += 1
        if child in visited:
            continue
        child_depth = depth + tokens[tok_i].delta
        child_program = program + (tok_i,)
        if child_depth == 0 and all(c[0] == a for c, a in zip(child, goal)):
            return SearchResult(True, child_program, candidates, counter.ops + extra, counter.instrs)
        visited.add(child)
        child_g = g + costs[tok_i]
        estimate = costs[order[0]]
        heapq.heappush(heap, (child_g + estimate, next(tie), child_g, child, child_depth, child_program, -1, costs,
                              None, tokens[tok_i].name))
    return SearchResult(False, (), candidates, counter.ops + extra, counter.instrs)
