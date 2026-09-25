import unittest
from collections import Counter as Tally

from sage.library import base_tokens, planted_library
from sage.machine import Counter
from sage.reuse import ReuseMemory, simulate
from sage.stream import norecur_stream, stream_manifest, zipf_stream


class ReuseTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tokens, cls.entries = planted_library()
        cls.zipf = zipf_stream("reuse-test", 0, n_types=4, n_instances=16, exponent=1.0,
                               tokens=cls.tokens, entries=cls.entries)
        cls.norecur = norecur_stream("reuse-test-nr", 0, 5, cls.tokens, cls.entries)

    def program(self, inst):
        return [self.tokens[n] for n in inst.target]

    def test_streams_are_deterministic_and_skewed(self):
        again = zipf_stream("reuse-test", 0, n_types=4, n_instances=16, exponent=1.0,
                            tokens=self.tokens, entries=self.entries)
        self.assertEqual(stream_manifest("z", 0, again), stream_manifest("z", 0, self.zipf))
        counts = Tally(s.type_id for s in self.zipf)
        self.assertGreater(max(counts.values()), 16 / 4)  # some type recurs more than uniformly
        same = [s for s in self.zipf if s.type_id == counts.most_common(1)[0][0]]
        self.assertGreater(len({s.task.task_id for s in same}), 1)  # recurrences are fresh instances

    def test_norecur_types_are_distinct(self):
        self.assertEqual(len({s.target for s in self.norecur}), len(self.norecur))

    def test_true_program_hits_on_a_new_instance_of_its_type(self):
        counts = Tally(s.type_id for s in self.zipf)
        tid = counts.most_common(1)[0][0]
        first, second = [s for s in self.zipf if s.type_id == tid][:2]
        m = ReuseMemory()
        key = m.key(first.task, Counter())
        m.store(key, self.program(first), 0)
        c = Counter()
        self.assertEqual(m.key(second.task, Counter()), key)
        hit = m.lookup(key, second.task, c)
        self.assertIsNotNone(hit)
        self.assertGreater(c.ops, 0)

    def test_identical_programs_merge_and_raise_trust(self):
        inst = self.zipf[0]
        m = ReuseMemory()
        key = m.key(inst.task, Counter())
        a = m.store(key, self.program(inst), 0)
        b = m.store(key, self.program(inst), 1)
        self.assertIs(a, b)
        self.assertEqual((a.trust, m.size()), (2, 1))

    def test_lookup_respects_the_verification_cap(self):
        inst = self.norecur[0]
        m = ReuseMemory(max_checks=2)
        key = m.key(inst.task, Counter())
        for other in self.norecur[1:4]:
            m.store(key, self.program(other), 0)
        c = Counter()
        m.lookup(key, inst.task, c)
        self.assertLessEqual(c.instrs, 2 * 4 * 40)  # at most 2 candidates run on at most 4 demos

    def test_simulation_pairs_with_the_memoryless_system(self):
        # Fallback that never finds anything: R must cost exactly S plus lookup work, with no hits.
        fallback = [{"found": False, "work": 1000, "program": []} for _ in self.zipf]
        rows = simulate(self.zipf, fallback, lambda r: [], 50)
        self.assertEqual(sum(r["mode"] == "hit" for r in rows), 0)
        for r in rows:
            self.assertEqual(r["work"], 1000 + r["lookup_work"])
        # Fallback that finds the true program: every later instance of a solved type hits.
        by_name = {b.name: b for b in base_tokens().values()}
        fallback = [{"found": True, "work": 1000, "program": [i.name for t in self.program(s) for i in t.body]}
                    for s in self.zipf]
        rows = simulate(self.zipf, fallback, lambda r: [by_name[n] for n in r["program"]], 50)
        seen = set()
        for inst, r in zip(self.zipf, rows):
            if inst.type_id in seen:
                self.assertEqual(r["mode"], "hit")
                self.assertTrue(r["correct"])
            seen.add(inst.type_id)


if __name__ == "__main__":
    unittest.main()
