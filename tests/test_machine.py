import random
import unittest

from sage.library import planted_library
from sage.machine import MAX_STACK, Counter, Instr, _closure, macro, run, token
from sage.worlds import REGIMES, generate_world


def naive_closure(adj, start):
    seen, frontier = set(), set(start)
    while frontier:
        nxt = set()
        for u in frontier:
            for v in adj[u]:
                if v not in seen:
                    seen.add(v)
                    nxt.add(v)
        frontier = nxt
    return frozenset(seen)


class MachineTest(unittest.TestCase):
    def setUp(self):
        self.tokens, self.entries = planted_library()
        self.worlds = [generate_world(random.Random(f"m{i}"), REGIMES[r]) for i, r in
                       enumerate(["train", "train", "topology", "size"])]

    def test_closure_matches_naive(self):
        for w in self.worlds:
            for rel in ("parent", "inside"):
                for u in range(0, w.n, 7):
                    start = frozenset((u,))
                    self.assertEqual(_closure(w.out[rel], start, Counter()), naive_closure(w.out[rel], start))
                    self.assertEqual(_closure(w.inn[rel], start, Counter()), naive_closure(w.inn[rel], start))

    def test_siblings_match_definition(self):
        sib = self.tokens["siblings"]
        for w in self.worlds:
            for x in w.of_type("person"):
                parents = w.out["parent"][x]
                expected = frozenset(c for p in parents for c in w.inn["parent"][p]) - {x}
                self.assertEqual(run(w, x, [sib]), expected)
                self.assertNotIn(x, run(w, x, [sib]))

    def test_macro_equals_its_parts(self):
        for e in self.entries:
            parts = [self.tokens[p] for p in e.token.parts]
            for w in self.worlds[:2]:
                for x in w.of_type("person")[:10]:
                    self.assertEqual(run(w, x, [e.token]), run(w, x, parts), e.token.name)

    def test_unbalanced_programs_are_rejected(self):
        w = self.worlds[0]
        x = w.of_type("person")[0]
        with self.assertRaises(ValueError):
            run(w, x, [self.tokens["push"]])
        with self.assertRaises(ValueError):
            run(w, x, [self.tokens["minus_pop"]])
        with self.assertRaises(ValueError):
            run(w, x, [self.tokens["push"]] * (MAX_STACK + 1) + [self.tokens["minus_pop"]] * (MAX_STACK + 1))

    def test_stack_signature(self):
        t = token("t", (Instr("push"), Instr("push"), Instr("minus_pop"), Instr("minus_pop")))
        self.assertEqual((t.need, t.rise, t.delta), (0, 2, 0))
        self.assertTrue(t.applicable(1))
        self.assertFalse(t.applicable(MAX_STACK - 1))
        pop = self.tokens["minus_pop"]
        self.assertFalse(pop.applicable(0))
        self.assertTrue(pop.applicable(1))

    def test_cost_counter_is_deterministic(self):
        w = self.worlds[0]
        prog = [self.tokens["cousins"], self.tokens["housemates"]]
        counts = []
        for _ in range(2):
            c = Counter()
            for x in w.of_type("person"):
                run(w, x, prog, c)
            counts.append((c.ops, c.instrs))
        self.assertEqual(counts[0], counts[1])
        self.assertGreater(counts[0][0], 0)


if __name__ == "__main__":
    unittest.main()
