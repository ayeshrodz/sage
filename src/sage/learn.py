"""Stage 0b learner: wake-sleep library learning with controlled acceptance.

Wake   try every still-unsolved training task by uniform search with the
       current library, within a budget; keep solved programs as flat
       sequences of base instructions.
Sleep  propose library entries from recurring, stack-balanced fragments of
       the solved programs. Rank them by a compression score: a fragment of
       length L that occurs in k tasks saves about k*(L-1) tokens and costs
       L to store. Drop fragments that behave like an existing token on a
       fixed probe set, or that are always empty.
Accept a batch of top candidates only if it improves the validation score
       (tasks solved, then total candidates spent) - the controlled
       improvement rule. If the batch fails, try its members one at a time.
Prune  at the end, drop entries that no training solution uses, if that
       does not hurt the validation score (Minton's utility filter).

All search work (wake, validation, pruning checks) is counted, so the cost
of learning can be amortized against its savings.
"""

from __future__ import annotations

import random
import time
from collections import defaultdict
from dataclasses import asdict, dataclass

from .machine import MAX_STACK, Token, base_instructions, run, token
from .search import guide_costs, search
from .worlds import REGIMES, generate_world


@dataclass
class LearnConfig:
    rounds: int = 8
    wake_budget: int = 20_000
    val_budget: int = 10_000
    batch: int = 4
    min_support: int = 2
    min_len: int = 2
    max_len: int = 8
    seed: int = 0


def probe_set(seed: int = 777) -> list:
    """Fixed probe inputs of every entity type, used to compare behaviours."""
    rng = random.Random(f"learn-probe:{seed}")
    probes = []
    for _ in range(3):
        w = generate_world(rng, REGIMES["train"])
        for etype, k in (("person", 6), ("place", 3), ("item", 3)):
            ids = w.of_type(etype)
            probes += [(w, x) for x in rng.sample(ids, min(k, len(ids)))]
    return probes


def behaviour(tok: Token, probes) -> tuple[frozenset, ...]:
    return tuple(run(w, x, [tok]) for w, x in probes)


def entry_from_names(name: str, instr_names, base_by_name: dict[str, Token]) -> Token:
    return token(name, tuple(base_by_name[n].body[0] for n in instr_names), tuple(instr_names))


class Tally:
    def __init__(self) -> None:
        self.candidates = 0
        self.ops = 0

    def add(self, res) -> None:
        self.candidates += res.candidates
        self.ops += res.ops


def solve(tokens: list[Token], tasks, budget: int, tag: str, tally: Tally | None = None):
    """Uniform-guide search on each task; tie-breaking depends on `tag` and the task index."""
    costs = guide_costs(len(tokens), set(), "uniform")
    results = []
    for i, task in enumerate(tasks):
        tiebreak = list(range(len(tokens)))
        random.Random(f"{tag}:{i}").shuffle(tiebreak)
        res = search(tokens, costs, tiebreak, task, budget)
        if tally is not None:
            tally.add(res)
        results.append(res)
    return results


def val_score(results) -> tuple[int, int]:
    """Higher is better: tasks solved, then fewer candidates spent."""
    return sum(r.found for r in results), -sum(r.candidates for r in results)


def mine(solutions: dict[int, tuple[str, ...]], cfg: LearnConfig) -> list[tuple[int, tuple[str, ...]]]:
    support: dict[tuple[str, ...], set[int]] = defaultdict(set)
    for tid, seq in solutions.items():
        for i in range(len(seq)):
            for length in range(cfg.min_len, cfg.max_len + 1):
                if i + length > len(seq):
                    break
                support[seq[i:i + length]].add(tid)
    ranked = [(len(t) * (len(f) - 1) - len(f), f) for f, t in support.items() if len(t) >= cfg.min_support]
    ranked.sort(key=lambda sf: (-sf[0], sf[1]))
    return ranked


def _contains(a: tuple, b: tuple) -> bool:
    return any(a[i:i + len(b)] == b for i in range(len(a) - len(b) + 1))


def learn(train, val, cfg: LearnConfig, log=print) -> dict:
    t_start = time.process_time()
    base = base_instructions()
    base_by_name = {b.name: b for b in base}
    probes = probe_set()
    known = {behaviour(b, probes) for b in base if b.need == 0 and b.delta == 0 and b.rise == 0}
    known.add(tuple(frozenset((x,)) for _, x in probes))
    learned: list[Token] = []
    solutions: dict[int, tuple[str, ...]] = {}
    uses: dict[str, int] = defaultdict(int)
    waked: set[str] = set()  # entries that were in the library during at least one wake phase
    wake, valt = Tally(), Tally()
    history = []

    def evaluate(lib, tag):
        return val_score(solve(base + lib, val, cfg.val_budget, f"val:{cfg.seed}:{tag}", valt))

    current = evaluate(learned, "r0")
    log(f"  round 0: val solved {current[0]}/{len(val)}")
    for rnd in range(1, cfg.rounds + 1):
        tokens = base + learned
        waked.update(t.name for t in learned)
        todo = [i for i in range(len(train)) if i not in solutions]
        results = solve(tokens, [train[i] for i in todo], cfg.wake_budget, f"wake:{cfg.seed}:{rnd}", wake)
        new = 0
        for i, res in zip(todo, results):
            if res.found:
                new += 1
                solutions[i] = tuple(ins.name for t in res.program for ins in tokens[t].body)
                for t in res.program:
                    uses[tokens[t].name] += 1

        # Sleep: rank fragments, keep new, non-trivial, balanced behaviours.
        batch: list[Token] = []
        seen_frags: list[tuple[str, ...]] = []
        for score, frag in mine(solutions, cfg):
            if len(batch) == cfg.batch:
                break
            if score <= 0 or any(_contains(f, frag) or _contains(frag, f) for f in seen_frags):
                continue
            tok = entry_from_names(f"L{len(learned) + len(batch)}", frag, base_by_name)
            if tok.need or tok.delta or tok.rise > MAX_STACK:
                continue
            fp = behaviour(tok, probes)
            if fp in known or all(not s for s in fp):
                continue
            batch.append(tok)
            seen_frags.append(frag)

        accepted: list[Token] = []
        if batch:
            trial = evaluate(learned + batch, f"r{rnd}b")
            if trial > current:
                accepted, current = batch, trial
            else:
                best = None
                for k, tok in enumerate(batch):
                    single = evaluate(learned + [tok], f"r{rnd}s{k}")
                    if single > current and (best is None or single > best[0]):
                        best = (single, tok)
                if best:
                    current, accepted = best[0], [best[1]]
        for tok in accepted:
            learned.append(token(f"L{len(learned)}", tok.body, tok.parts))
            known.add(behaviour(tok, probes))
        history.append({
            "round": rnd, "train_solved": len(solutions), "new_solutions": new,
            "proposed": [" ".join(t.parts) for t in batch], "accepted": [" ".join(t.parts) for t in accepted],
            "library_size": len(learned), "val_solved": current[0], "val_candidates": -current[1],
        })
        log(f"  round {rnd}: train solved {len(solutions)}/{len(train)} (+{new}), library {len(learned)},"
            f" val solved {current[0]}/{len(val)}, accepted {[' '.join(t.parts) for t in accepted]}")
        if not accepted and new == 0:
            break

    # Prune entries that went through a wake phase without being used, if validation does not get worse.
    unused = [t for t in learned if t.name in waked and uses.get(t.name, 0) == 0]
    pruned: list[str] = []
    if unused:
        kept = [t for t in learned if t not in unused]
        after = evaluate(kept, "prune")
        if after >= current:
            pruned = [" ".join(t.parts) for t in unused]
            learned, current = kept, after
    log(f"  pruned {len(pruned)}; final library {len(learned)}, val solved {current[0]}/{len(val)}")

    return {
        "config": asdict(cfg),
        "library": [list(t.parts) for t in learned],
        "uses": {" ".join(t.parts): uses.get(t.name, 0) for t in learned},
        "pruned": pruned,
        "history": history,
        "train_solved": len(solutions),
        "val_solved": current[0],
        "cost": {"wake_candidates": wake.candidates, "wake_ops": wake.ops,
                 "val_candidates": valt.candidates, "val_ops": valt.ops,
                 "cpu_s": time.process_time() - t_start},
    }


def load_library(entries: list[list[str]]) -> list[Token]:
    base_by_name = {b.name: b for b in base_instructions()}
    return [entry_from_names(f"L{i}", parts, base_by_name) for i, parts in enumerate(entries)]
