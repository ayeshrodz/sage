import unittest

from sage.learn import LearnConfig, behaviour, load_library, mine, probe_set
from sage.library import planted_library
from sage.tasks import make_split, manifest


class LearnTest(unittest.TestCase):
    def test_mining_ranks_recurring_fragments(self):
        sib = ("push", "out.parent", "in.parent", "minus_pop")
        solutions = {0: sib + ("out.friend",), 1: ("in.parent",) + sib, 2: ("out.owns", "in.owns")}
        ranked = mine(solutions, LearnConfig())
        frags = [f for _, f in ranked]
        self.assertEqual(frags[0], sib)  # longest fragment shared by two tasks
        self.assertNotIn(("out.owns", "in.owns"), frags)  # support 1 < min_support

    def test_loaded_entry_behaves_like_planted(self):
        tokens, _ = planted_library()
        (entry,) = load_library([["push", "out.parent", "in.parent", "minus_pop"]])
        probes = probe_set()
        self.assertEqual(behaviour(entry, probes), behaviour(tokens["siblings"], probes))

    def test_curriculum_off_leaves_stream_unchanged(self):
        tokens, entries = planted_library()
        a = make_split("s", 0, 3, tokens, entries, n_demos=4)
        b = make_split("s", 0, 3, tokens, entries, n_demos=4, single_share=0.0)
        self.assertEqual(manifest("s", 0, *a), manifest("s", 0, *b))

    def test_curriculum_adds_single_entry_tasks(self):
        tokens, entries = planted_library()
        planted = {e.token.name for e in entries}
        _, hidden = make_split("c", 0, 12, tokens, entries, n_demos=4, single_share=1.0)
        for h in hidden:
            self.assertEqual(sum(n in planted for n in h.target), 1)

    def test_control_targets_use_fresh_macros(self):
        tokens, entries = planted_library()
        planted = {e.token.name for e in entries}
        tasks, hidden = make_split("ctl", 0, 5, tokens, entries, n_demos=4, structure="control")
        for t, h in zip(tasks, hidden):
            self.assertFalse(planted & set(h.target))
            self.assertTrue(any(n.startswith("[") for n in h.target))
            self.assertEqual(len(t.demos), 4)


if __name__ == "__main__":
    unittest.main()
