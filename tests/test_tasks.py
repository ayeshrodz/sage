import random
import unittest

from sage.library import base_tokens, distractors, planted_library
from sage.machine import run
from sage.search import guide_costs, search, short_program_exists
from sage.tasks import STRATA, Task, ambiguous, make_split, manifest


class TaskTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tokens, cls.entries = planted_library()
        cls.dev = make_split("dev", 0, 6, cls.tokens, cls.entries, n_demos=4)
        cls.test = make_split("test", 0, 6, cls.tokens, cls.entries, n_demos=4)

    def test_splits_are_deterministic(self):
        again = make_split("dev", 0, 6, self.tokens, self.entries, n_demos=4)
        self.assertEqual(manifest("dev", 0, *again), manifest("dev", 0, *self.dev))

    def test_dev_and_test_are_disjoint(self):
        dev = manifest("dev", 0, *self.dev)["tasks"]
        test = manifest("test", 0, *self.test)["tasks"]
        self.assertFalse({t["task_id"] for t in dev} & {t["task_id"] for t in test})
        self.assertFalse({t["demos_sha256"] for t in dev} & {t["demos_sha256"] for t in test})

    def test_examples_follow_the_target(self):
        for task, hidden in zip(*self.dev):
            program = [self.tokens[n] for n in hidden.target]
            for ex in task.demos:
                self.assertEqual(run(ex.world, ex.x, program), ex.answer)
            for s in STRATA:
                self.assertTrue(hidden.queries[s])
                for q in hidden.queries[s]:
                    self.assertEqual(run(q.world, q.x, program), q.answer)

    def test_solver_view_hides_target_and_queries(self):
        self.assertEqual(set(Task.__dataclass_fields__), {"task_id", "demos"})

    def test_tasks_need_composition(self):
        base = list(base_tokens().values())
        for task, _ in zip(*self.dev):
            self.assertFalse(short_program_exists(task, base, 3))

    def test_planted_library_solves_with_a_sharp_guide(self):
        toks = list(base_tokens().values()) + [e.token for e in self.entries]
        for task, hidden in zip(*self.dev):
            relevant = {i for i, t in enumerate(toks) if t.name in hidden.target}
            res = search(toks, guide_costs(len(toks), relevant, "mass"), list(range(len(toks))), task, 5000)
            self.assertTrue(res.found)
            program = [toks[i] for i in res.program]
            for ex in task.demos:
                self.assertEqual(run(ex.world, ex.x, program), ex.answer)

    def test_search_respects_budget(self):
        toks = list(base_tokens().values())
        task = self.dev[0][0]
        res = search(toks, guide_costs(len(toks), set(), "uniform"), list(range(len(toks))), task, 50)
        self.assertLessEqual(res.candidates, 50)

    def test_well_posed_tasks_are_not_ambiguous(self):
        tasks, hidden = make_split("wp", 0, 4, self.tokens, self.entries, n_demos=2, well_posed=True)
        for task, h in zip(tasks, hidden):
            self.assertFalse(ambiguous(h.target, self.tokens, task.demos, h.queries))

    def test_distractors_are_distinct_and_nested(self):
        a = distractors(30)
        b = distractors(10)
        self.assertEqual([t.body for t in a[:10]], [t.body for t in b])
        self.assertEqual(len({t.body for t in a}), 30)
        for t in a:
            self.assertEqual((t.need, t.delta), (0, 0))


if __name__ == "__main__":
    unittest.main()
