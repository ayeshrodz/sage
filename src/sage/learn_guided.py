"""Stage 0c learner (S3): guided wake-sleep with refactoring, dreams and a learned guide.

Round structure
  Wake      guided search on training tasks that are unsolved and have not yet
            been tried with the current library version (at most `max_tries`
            attempts per task). Solutions are kept as flat instruction sequences.
  Refactor  every solution is rewritten in terms of the current library
            (greedy longest match), so new entries can be built from old ones.
  Mine      recurring token fragments become candidate entries, ranked by a
            compression score (tasks using it x tokens saved - its length).
            Candidates may not contain filters (filters are arguments, added by
            composition), must keep the stack balanced, and must behave
            differently from every known token on single-entity *and* set
            probes (merging variants such as drop_x vs minus_pop only when they
            truly agree).
  Accept    retrain the guide (warm start, fresh dreams) with the candidate
            batch and keep it only if guided validation improves: tasks solved,
            then candidates spent (controlled improvement). Otherwise try the
            top half of the batch. If nothing is accepted but new solutions
            arrived, a guide retrained on the current library is adopted when
            validation does not get worse.
  Prune     at the end, entries that no refactored solution uses are dropped
            if validation does not get worse.

Every unit of work is recorded in a ledger (element operations for search,
perception and dreams; multiply-adds for the guide), so the learning cost L
can be amortized in the stage 0c criteria.
"""

from __future__ import annotations

import random
import time
from collections import Counter as Tally
from dataclasses import asdict, dataclass, field

from .dreams import sample_dream, standalone, type_signatures
from .features import state_features
from .guide import Guide
from .learn import probe_set
from .machine import MAX_STACK, Counter, Token, base_instructions, execute, run, token
from .search import search_policy


@dataclass
class GuidedConfig:
    rounds: int = 8
    wake_budget: int = 5_000
    val_budget: int = 5_000
    solve_cap: int = 5_000  # S3's own stopping rule at test time (the registered budget, 20,000, is the ceiling)
    max_tries: int = 3
    batch: int = 6
    min_support: int = 2
    max_frag_tokens: int = 4
    max_body: int = 12
    dreams_initial: int = 150
    dreams_per_update: int = 50
    dream_pool: int = 300
    guide_epochs: int = 2
    guide_warm_epochs: int = 1
    guide_lr: float = 0.3
    guide_l2: float = 1e-4
    min_feature_count: int = 2  # features seen fewer times in training are ignored
    floor: float = 0.05
    prior_weight: float = 0.3
    accept_ties: bool = True  # accept a batch when guided validation does not get worse (Minton's rule)
    root_depth: int = 3  # path depth of perception at the start state
    state_depth: int = 2  # path depth of perception at later states
    max_policy_calls: int = 100  # per search; later states reuse their parent's order
    retry_half: bool = False  # if a batch is rejected, try its top half
    refresh: bool = False  # when nothing is accepted but new solutions arrived, adopt a retrained guide if validation holds
    seed: int = 0


@dataclass
class Ledger:
    wake_ops: int = 0
    val_ops: int = 0
    perception_ops: int = 0
    dream_ops: int = 0
    guide_train_madds: int = 0
    guide_score_madds: int = 0
    refactor_ops: int = 0

    def total(self) -> int:
        return sum(asdict(self).values())


def set_probes(seed: int = 778) -> list:
    """(world, x, set) probes: small person sets with and without x, to tell set semantics apart."""
    rng = random.Random(f"set-probe:{seed}")
    out = []
    for w, x in probe_set():
        if w.etype[x] != "person":
            continue
        people = [p for p in w.of_type("person") if p != x]
        others = frozenset(rng.sample(people, min(2, len(people))))
        out += [(w, x, others | {x}), (w, x, others)]
    return out


def rich_behaviour(tok: Token, singles, sets) -> tuple:
    a = tuple(run(w, x, [tok]) for w, x in singles)
    b = tuple(execute(w, x, s, (), tok.body, Counter())[0] for w, x, s in sets)
    return a + b


def refactor(flat: tuple[str, ...], bodies: list[tuple[tuple[str, ...], str]], ledger: Ledger | None = None) -> list[str]:
    """Rewrite a flat instruction sequence with library entries, longest match first."""
    out, i, work = [], 0, 0
    while i < len(flat):
        for body, name in bodies:
            work += 1
            if flat[i:i + len(body)] == body:
                out.append(name)
                i += len(body)
                break
        else:
            out.append(flat[i])
            i += 1
    if ledger is not None:
        ledger.refactor_ops += work
    return out


def library_bodies(library: list[Token]) -> list[tuple[tuple[str, ...], str]]:
    return sorted(((tuple(i.name for i in t.body), t.name) for t in library), key=lambda b: (-len(b[0]), b[1]))


def _contains(a: tuple, b: tuple) -> bool:
    return any(a[i:i + len(b)] == b for i in range(len(a) - len(b) + 1))


class GuidedLearner:
    def __init__(self, train, val, cfg: GuidedConfig, log=print):
        self.train, self.val, self.cfg, self.log = train, val, cfg, log
        self.base = base_instructions()
        self.ledger = Ledger()
        self.rng = random.Random(f"guided:{cfg.seed}")
        self.singles, self.sets = probe_set(), set_probes()
        self.known = {rich_behaviour(b, self.singles, self.sets) for b in self.base if standalone(b)}
        self.known.add(tuple(frozenset((x,)) for _, x in self.singles) + tuple(s for *_, s in self.sets))
        self.learned: list[Token] = []
        self.next_id = 0
        self.version = 0
        self.solutions: dict[int, tuple[str, ...]] = {}
        self.tries: dict[int, int] = {}
        self.tried_version: dict[int, int] = {}
        self.dreams: list[tuple[object, tuple[str, ...]]] = []  # (dreamed task, flat program)
        self.state_cache: dict[tuple, dict] = {}  # (task key, flat prefix length) -> perception
        self.worlds = [d.world for t in train for d in t.demos]
        self.history: list[dict] = []

    # -- pieces -----------------------------------------------------------------------
    def tokens(self, library):
        return self.base + library

    def add_dreams(self, library, n: int) -> None:
        c = Counter()
        tokens = self.tokens(library)
        by_name = {t.name: t for t in tokens}
        sigs = type_signatures(tokens, self.worlds, c, seed=f"sig:{self.cfg.seed}:{self.version}")
        learned = [t.name for t in library]
        bodies = library_bodies(library)
        uses = Tally(n for flat in self.solutions.values() for n in refactor(flat, bodies, self.ledger))
        weights = {n: 1 + uses[n] for n in learned}
        made = 0
        for _ in range(n * 5):
            if made == n:
                break
            drawn = sample_dream(self.rng, by_name, sigs, learned, self.worlds, c, weights=weights)
            if drawn is None:
                continue
            self.dreams.append(drawn)
            made += 1
        self.dreams = self.dreams[-self.cfg.dream_pool:]
        self.ledger.dream_ops += c.ops

    def perceive(self, demos, state, last, counter) -> dict:
        depth = self.cfg.root_depth if last is None else self.cfg.state_depth
        return state_features(demos, state, last, counter, depth)

    def replay(self, key, task, flat, library, bodies, by_name, counter) -> list:
        """(state features, next token) at every step of a program rewritten over `library`.

        The state after a token prefix depends only on the flat instruction
        prefix, so perception is cached by (task, flat position) and reused
        when the library, and hence the tokenization, changes.
        """
        state = tuple((frozenset((d.x,)), ()) for d in task.demos)
        last, pos, out = None, 0, []
        for name in refactor(flat, bodies, self.ledger):
            ck = (key, pos)
            if ck not in self.state_cache:
                f = self.perceive(task.demos, state, None if pos == 0 else "?", counter)
                f.pop("last:?", None)
                f.pop("last:^", None)
                self.state_cache[ck] = f
            feats = dict(self.state_cache[ck])
            feats[f"last:{last or '^'}"] = 1.0
            out.append((feats, {name: 1.0}))
            body = by_name[name].body
            state = tuple(execute(d.world, d.x, cur, stack, body, counter) for d, (cur, stack) in zip(task.demos, state))
            last, pos = name, pos + len(body)
        return out

    def examples(self, library):
        bodies = library_bodies(library)
        by_name = {t.name: t for t in self.tokens(library)}
        c = Counter()
        ex = [e for i, flat in self.solutions.items()
              for e in self.replay(("t", i), self.train[i], flat, library, bodies, by_name, c)]
        ex += [e for task, flat in self.dreams
               for e in self.replay(("d", id(task)), task, flat, library, bodies, by_name, c)]
        self.ledger.perception_ops += c.ops
        return ex

    def train_guide(self, library, previous: Guide | None, epochs: int) -> Guide:
        ex = self.examples(library)
        g = Guide.build([t.name for t in self.tokens(library)], ex, min_count=self.cfg.min_feature_count,
                        previous=previous)
        g.madds, g.beta, g.floor = 0, self.cfg.prior_weight, self.cfg.floor
        self.ledger.guide_train_madds += g.fit_online(ex, epochs=epochs, lr=self.cfg.guide_lr, l2=self.cfg.guide_l2,
                                                      seed=f"sgd:{self.cfg.seed}:{self.version}:{len(ex)}")
        return g

    def solve(self, library, guide: Guide, task, budget: int, tag: str):
        """Policy-guided search; the returned ops include perception and scoring work."""
        return solve_with_policy(self.tokens(library), guide, task, budget, tag, self.cfg)

    def validate(self, library, guide: Guide) -> tuple[int, int]:
        solved = cands = 0
        for i, task in enumerate(self.val):
            res = self.solve(library, guide, task, self.cfg.val_budget, f"val:{self.cfg.seed}:{i}")
            self.ledger.val_ops += res.ops
            solved += res.found
            cands += res.candidates
        return solved, -cands

    def candidates(self) -> list[Token]:
        cfg = self.cfg
        by_name = {t.name: t for t in self.tokens(self.learned)}
        bodies = library_bodies(self.learned)
        support: dict[tuple[str, ...], set[int]] = {}
        for tid, flat in self.solutions.items():
            seq = tuple(refactor(flat, bodies, self.ledger))
            for i in range(len(seq)):
                for k in range(2, cfg.max_frag_tokens + 1):
                    if i + k > len(seq):
                        break
                    support.setdefault(seq[i:i + k], set()).add(tid)
        ranked = sorted(((len(t) * (len(f) - 1) - len(f), f) for f, t in support.items()
                         if len(t) >= cfg.min_support), key=lambda sf: (-sf[0], sf[1]))
        batch, frags, seen = [], [], set()
        for score, frag in ranked:
            if len(batch) == cfg.batch or score <= 0:
                break
            if any(n.startswith("only_") for n in frag):
                continue
            if any(_contains(f, frag) or _contains(frag, f) for f in frags):
                continue
            body = tuple(i for n in frag for i in by_name[n].body)
            tok = token("?", body, frag)
            if tok.need or tok.delta or tok.rise > MAX_STACK or len(body) > cfg.max_body:
                continue
            beh = rich_behaviour(tok, self.singles, self.sets)
            if beh in self.known or beh in seen or all(not s for s in beh):
                continue
            seen.add(beh)
            frags.append(frag)
            batch.append(tok)
        return batch

    def named(self, toks: list[Token]) -> list[Token]:
        out = []
        for t in toks:
            out.append(token(f"L{self.next_id}", t.body, t.parts))
            self.next_id += 1
        return out

    # -- main loop ----------------------------------------------------------------------
    def run(self) -> dict:
        t_start = time.process_time()
        cfg = self.cfg
        self.add_dreams([], cfg.dreams_initial)
        guide = self.train_guide([], None, cfg.guide_epochs)
        current = self.validate([], guide)
        self.log(f"  round 0: val solved {current[0]}/{len(self.val)} (guide over base instructions)")
        for rnd in range(1, cfg.rounds + 1):
            new = 0
            for i, task in enumerate(self.train):
                if i in self.solutions or self.tries.get(i, 0) >= cfg.max_tries:
                    continue
                if self.tried_version.get(i) == self.version:
                    continue
                res = self.solve(self.learned, guide, task, cfg.wake_budget, f"wake:{cfg.seed}:{rnd}:{i}")
                self.ledger.wake_ops += res.ops
                self.tries[i] = self.tries.get(i, 0) + 1
                self.tried_version[i] = self.version
                if res.found:
                    tokens = self.tokens(self.learned)
                    self.solutions[i] = tuple(ins.name for t in res.program for ins in tokens[t].body)
                    new += 1

            batch = self.candidates()
            accepted: list[Token] = []
            attempts = [batch, batch[: len(batch) // 2]] if cfg.retry_half else [batch]
            for attempt in (attempts if batch else []):
                if not attempt:
                    continue
                trial = self.learned + self.named(attempt)
                self.add_dreams(trial, cfg.dreams_per_update)
                g = self.train_guide(trial, guide, cfg.guide_warm_epochs)
                score = self.validate(trial, g)
                if score > current or (cfg.accept_ties and score[0] >= current[0]):
                    accepted, self.learned, guide, current = trial[len(self.learned):], trial, g, score
                    for t in accepted:
                        self.known.add(rich_behaviour(t, self.singles, self.sets))
                    self.version += 1
                    break
            if cfg.refresh and not accepted and new:
                g = self.train_guide(self.learned, guide, cfg.guide_warm_epochs)
                score = self.validate(self.learned, g)
                if score >= current:
                    guide, current = g, score
            self.history.append({
                "round": rnd, "train_solved": len(self.solutions), "new_solutions": new,
                "proposed": [" ".join(t.parts) for t in batch],
                "accepted": [f"{t.name} = {' '.join(t.parts)}" for t in accepted],
                "library_size": len(self.learned), "val_solved": current[0], "val_candidates": -current[1],
                "ledger_total": self.ledger.total(),
            })
            self.log(f"  round {rnd}: train solved {len(self.solutions)}/{len(self.train)} (+{new}),"
                     f" library {len(self.learned)}, val solved {current[0]}/{len(self.val)}"
                     f" (cands {-current[1]:,}), accepted {[' '.join(t.parts) for t in accepted]}")
            if not accepted and new == 0:
                break

        bodies = library_bodies(self.learned)
        uses = Tally(n for flat in self.solutions.values() for n in refactor(flat, bodies, self.ledger))
        unused = [t for t in self.learned if uses[t.name] == 0]
        pruned = []
        if unused:
            kept = [t for t in self.learned if t not in unused]
            g = self.train_guide(kept, guide, cfg.guide_warm_epochs)
            score = self.validate(kept, g)
            if score >= current:
                pruned = [" ".join(t.parts) for t in unused]
                self.learned, guide, current = kept, g, score
        self.log(f"  pruned {len(pruned)}; final library {len(self.learned)},"
                 f" val solved {current[0]}/{len(self.val)}; learning work {self.ledger.total():,}")
        return {
            "config": asdict(cfg),
            "library": [{"name": t.name, "parts": list(t.parts), "body": [i.name for i in t.body]} for t in self.learned],
            "uses": {t.name: uses[t.name] for t in self.learned},
            "pruned": pruned,
            "history": self.history,
            "train_solved": len(self.solutions),
            "val_solved": current[0],
            "ledger": asdict(self.ledger),
            "learning_work": self.ledger.total(),
            "cpu_s": time.process_time() - t_start,
            "guide": guide.to_json(),
        }


def solve_with_policy(tokens: list[Token], guide: Guide, task, budget: int, tag: str, cfg: GuidedConfig):
    names = [t.name for t in tokens]

    def policy(state, last):
        c = Counter()
        depth = cfg.root_depth if last is None else cfg.state_depth
        costs, madds = guide.costs(state_features(task.demos, state, last, c, depth), names)
        return costs, c.ops + madds

    tiebreak = list(range(len(tokens)))
    random.Random(tag).shuffle(tiebreak)
    return search_policy(tokens, policy, tiebreak, task, budget, cfg.max_policy_calls)


def load_learned(entries: list[dict]) -> list[Token]:
    by_name = {b.name: b for b in base_instructions()}
    return [token(e["name"], tuple(by_name[n].body[0] for n in e["body"]), tuple(e["parts"])) for e in entries]
