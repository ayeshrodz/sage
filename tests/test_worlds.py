import random
import unittest

from sage.library import planted_library
from sage.machine import run
from sage.worlds import REGIMES, RELATIONS, build_world, generate_world


class WorldTest(unittest.TestCase):
    def test_generation_is_deterministic(self):
        a = generate_world(random.Random("w"), REGIMES["train"])
        b = generate_world(random.Random("w"), REGIMES["train"])
        self.assertEqual(a, b)

    def test_answers_are_invariant_under_renaming(self):
        tokens, entries = planted_library()
        for regime in REGIMES.values():
            rng = random.Random(f"rename:{regime.name}")
            w = generate_world(rng, regime)
            perm = list(range(w.n))
            rng.shuffle(perm)
            w2 = w.relabel(perm)
            for e in entries:
                for x in w.of_type("person")[:8]:
                    ans = run(w, x, [e.token])
                    self.assertEqual(run(w2, perm[x], [e.token]), frozenset(perm[v] for v in ans), e.token.name)

    def test_edge_order_does_not_matter(self):
        w = generate_world(random.Random("edges"), REGIMES["train"])
        rng = random.Random(1)
        shuffled = {}
        for r in RELATIONS:
            edges = list(w.edges(r))
            rng.shuffle(edges)
            shuffled[r] = edges
        self.assertEqual(build_world(w.etype, w.color, w.size, shuffled), w)

    def test_family_structure(self):
        for regime in REGIMES.values():
            w = generate_world(random.Random(f"fam:{regime.name}"), regime)
            for p in w.of_type("person"):
                self.assertIn(len(w.out["parent"][p]), (0, 2))
                self.assertNotIn(p, w.out["parent"][p])
            # parent relation is acyclic: nobody is their own ancestor
            for p in w.of_type("person"):
                seen, frontier = set(), set(w.out["parent"][p])
                while frontier:
                    self.assertNotIn(p, frontier)
                    seen |= frontier
                    frontier = {q for f in frontier for q in w.out["parent"][f]} - seen

    def test_regimes_differ_in_size(self):
        small = generate_world(random.Random("s"), REGIMES["train"])
        large = generate_world(random.Random("s"), REGIMES["size"])
        self.assertGreater(len(large.of_type("person")), 3 * len(small.of_type("person")))


if __name__ == "__main__":
    unittest.main()
