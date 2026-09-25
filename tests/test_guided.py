import random
import unittest

import numpy as np

from sage.control import control_library
from sage.dreams import sample_dream, type_signatures
from sage.evaluation import reference_program
from sage.features import state_features
from sage.guide import Guide, percentile_ranks
from sage.learn import behaviour, probe_set
from sage.learn_guided import library_bodies, refactor
from sage.library import base_tokens, planted_library
from sage.machine import Counter, run
from sage.search import guide_costs, search, search_policy
from sage.tasks import make_split


class GuidedTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tokens, cls.entries = planted_library()
        cls.tasks, cls.hidden = make_split("guided-tests", 0, 4, cls.tokens, cls.entries, n_demos=4)

    def test_policy_search_with_uniform_policy_matches_plain_search(self):
        toks = list(base_tokens().values()) + [e.token for e in self.entries]
        uni = guide_costs(len(toks), set(), "uniform")
        for i, task in enumerate(self.tasks[:2]):
            tb = list(range(len(toks)))
            random.Random(i).shuffle(tb)
            a = search(toks, uni, tb, task, 2000)
            b = search_policy(toks, lambda s, l: (uni, 0), tb, task, 2000)
            self.assertEqual((a.found, a.program, a.candidates), (b.found, b.program, b.candidates))

    def test_refactor_preserves_the_program_and_prefers_longest(self):
        sib = self.tokens["siblings"]
        aunts = self.tokens["aunts_uncles"]
        bodies = library_bodies([sib, aunts])
        flat = tuple(i.name for i in aunts.body) + ("in.parent",) + tuple(i.name for i in sib.body)
        names = refactor(flat, bodies)
        self.assertEqual(names, ["aunts_uncles", "in.parent", "siblings"])
        by_name = {"aunts_uncles": aunts, "siblings": sib, **base_tokens()}
        self.assertEqual(tuple(i.name for n in names for i in by_name[n].body), flat)

    def test_guide_learns_a_simple_mapping_and_round_trips(self):
        ex = [({"f:a": 1.0, "bias": 1.0}, {"x": 1.0}), ({"f:b": 1.0, "bias": 1.0}, {"y": 1.0})] * 20
        g = Guide.build(["x", "y", "z"], ex)
        g.fit_online(ex, epochs=5)
        p, madds = g.probs({"f:a": 1.0, "bias": 1.0})
        self.assertAlmostEqual(float(p.sum()), 1.0, places=6)
        self.assertEqual(int(np.argmax(p)), g.t_index["x"])
        self.assertGreater(madds, 0)
        g2 = Guide.from_json(g.to_json())
        np.testing.assert_allclose(g2.probs({"f:b": 1.0, "bias": 1.0})[0], g.probs({"f:b": 1.0, "bias": 1.0})[0], atol=1e-5)

    def test_percentile_ranks_average_ties(self):
        r = percentile_ranks(np.array([0.5, 0.2, 0.2, 0.1]))
        np.testing.assert_allclose(r, [0.0, 0.375, 0.375, 0.75])

    def test_finish_features_detect_a_completing_set_operation(self):
        d = self.tasks[0].demos[0]
        w, x = d.world, d.x
        cur = frozenset(d.answer) | {x}
        state = tuple((cur, (frozenset((x,)),)) if e is d else (frozenset((e.x,)), (frozenset(),))
                      for e in self.tasks[0].demos)
        f = state_features(self.tasks[0].demos, state, "push", Counter(), 1)
        self.assertGreater(f.get("finish:minus_pop", 0), 0)
        self.assertEqual(f["stack:1"], 1.0)
        self.assertEqual(f["last:push"], 1.0)

    def test_reference_program_expands_unrecovered_entries(self):
        ref = reference_program(("cousins", "only_color.red"), {"siblings": "L0"})
        self.assertEqual(ref, ["out.parent", "L0", "in.parent", "only_color.red"])
        self.assertEqual(reference_program(("cousins",), {}), ["out.parent", "out.parent", "push", "out.parent",
                                                              "in.parent", "minus_pop", "in.parent"][1:])

    def test_control_library_is_deterministic_and_new(self):
        a_tokens, a = control_library()
        _, b = control_library()
        self.assertEqual([e.token.body for e in a], [e.token.body for e in b])
        self.assertEqual(len(a), 13)
        probes = probe_set()
        planted = {behaviour(e.token, probes) for e in self.entries}
        for e in a:
            self.assertNotIn(behaviour(e.token, probes), planted)

    def test_dreams_are_consistent_with_their_programs(self):
        toks = list(base_tokens().values()) + [self.tokens["siblings"]]
        by_name = {t.name: t for t in toks}
        worlds = [d.world for t in self.tasks for d in t.demos]
        sigs = type_signatures(toks, worlds, Counter())
        rng = random.Random(3)
        made = 0
        for _ in range(40):
            drawn = sample_dream(rng, by_name, sigs, ["siblings"], worlds, Counter())
            if drawn is None:
                continue
            task, flat = drawn
            program = [by_name[n] for n in flat]
            for ex in task.demos:
                self.assertEqual(run(ex.world, ex.x, program), ex.answer)
            made += 1
        self.assertGreater(made, 10)


if __name__ == "__main__":
    unittest.main()
