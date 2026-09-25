import json
import random
import re
import unittest
from collections import Counter as Tally

from sage.wrangle.llm import ModelConfig, Scripted, direct_messages, extract_code, parse_direct, program_messages
from sage.wrangle.memory import ProgramMemory
from sage.wrangle.requests import make_request, manifest, norecur_stream, zipf_stream
from sage.wrangle.sandbox import call, compile_function, reproduces
from sage.wrangle.synth import synthesize
from sage.wrangle.systems import replay, run_B, run_D, run_E
from sage.wrangle.transforms import TYPE_INDEX, TYPES

FIRST_NAME = "```python\ndef f(s):\n    return s.split()[0]\n```"


def request(type_name, i=0):
    return make_request(random.Random(f"test:{type_name}:{i}"), i, TYPE_INDEX[type_name])


def examples_in(messages):
    return [(json.loads(x), json.loads(y))
            for x, y in re.findall(r'^f\((".*")\) == (".*")$', messages[-1]["content"], re.M)]


class WorkloadTest(unittest.TestCase):
    def test_every_type_makes_informative_requests(self):
        self.assertEqual(len(TYPES), 50)
        for t in TYPES:
            q = request(t.name)
            self.assertEqual(len(q.examples), 3)
            self.assertEqual(len({y for _, y in q.examples}), 3, t.name)
            self.assertEqual(len(set(q.queries) | {x for x, _ in q.examples}), 8, t.name)
            self.assertEqual(q.gold, tuple(t.f(x) for x in q.queries))

    def test_streams_are_deterministic_and_as_registered(self):
        z = zipf_stream("wrangle-test", 60)
        self.assertEqual(manifest("z", zipf_stream("wrangle-test", 60)), manifest("z", z))
        counts = Tally(q.type_id for q in z)
        self.assertGreater(max(counts.values()), 60 / 50 * 3)  # skewed: the top type recurs often
        nr = norecur_stream("wrangle-test-nr")
        self.assertEqual(sorted(q.type_id for q in nr), list(range(50)))


class SandboxTest(unittest.TestCase):
    def test_allows_plain_code_and_re(self):
        fn = compile_function("import re\ndef f(s):\n    return re.sub('a', 'b', s)")
        self.assertEqual(call(fn, "banana"), "bbnbnb")

    def test_blocks_modules_files_and_endless_loops(self):
        self.assertIsNone(compile_function("import os\ndef f(s):\n    return s"))
        fn = compile_function("def f(s):\n    return open('/etc/passwd').read()")
        self.assertIsNone(call(fn, "x"))
        fn = compile_function("def f(s):\n    while True:\n        pass")
        self.assertIsNone(call(fn, "x", seconds=0.05))

    def test_non_strings_and_errors_are_not_answers(self):
        self.assertIsNone(call(compile_function("def f(s):\n    return len(s)"), "abc"))
        self.assertIsNone(call(compile_function("def f(s):\n    return s[10]"), "abc"))
        self.assertFalse(reproduces(None, [("a", "a")]))


class ParsingTest(unittest.TestCase):
    def test_extract_code_keeps_only_definitions(self):
        text = ("Here you go:\n```python\nimport re\n\ndef helper(w):\n    return w[0]\n\ndef f(s):\n"
                "    return helper(s)\n\nprint(f('abc'))\nassert f('x') == 'x'\n```\nThis works because...")
        code = extract_code(text)
        self.assertNotIn("print", code)
        self.assertNotIn("assert", code)
        self.assertEqual(call(compile_function(code), "abc"), "a")

    def test_extract_code_without_fence_and_other_names(self):
        code = extract_code("Sure!\n\ndef initials(name):\n    return name[0]\n\nThat is all.")
        self.assertEqual(call(compile_function(code), "Mary"), "M")

    def test_extract_code_picks_the_main_function(self):
        code = extract_code("```py3\ndef convert(s):\n    return first(s)\n\ndef first(s):\n    return s[0]\n```")
        self.assertEqual(call(compile_function(code), "Mary"), "M")

    def test_extract_code_rejects_replies_without_functions(self):
        self.assertIsNone(extract_code("I don't know."))
        self.assertIsNone(extract_code("```python\nx = 1\n```"))

    def test_parse_direct(self):
        self.assertEqual(parse_direct('["a", "b c"]', 2), ["a", "b c"])
        self.assertEqual(parse_direct('1. "a"\n2. "b"', 3), ["a", "b", ""])
        self.assertEqual(parse_direct('"x" -> "a"\nb', 2), ["a", "b"])
        self.assertEqual(parse_direct("['a', 'b']", 2), ["a", "b"])  # a Python list

    def test_prompts_show_the_examples_exactly(self):
        q = request("collapse_spaces")
        self.assertEqual(examples_in(program_messages(q.examples)), list(q.examples))
        text = direct_messages(q.examples, q.queries)[-1]["content"]
        for x in q.queries:
            self.assertIn(json.dumps(x), text)


class SynthTest(unittest.TestCase):
    def test_solves_simple_types(self):
        for name in ("first_name", "initials", "email_domain", "phone_format"):
            q = request(name)
            code, work = synthesize(q.examples)
            fn = compile_function(code)
            self.assertTrue(reproduces(fn, q.examples), name)
            self.assertEqual(tuple(call(fn, x) for x in q.queries), q.gold, name)
            self.assertGreater(work, 0)

    def test_gives_up_on_types_outside_its_language(self):
        code, work = synthesize(request("date_iso_to_long").examples)
        self.assertIsNone(code)
        rec = run_E(request("date_iso_to_long"))
        self.assertEqual(rec["mode"], "none")
        self.assertFalse(rec["correct"])


class SystemsTest(unittest.TestCase):
    def test_B_retries_then_accepts_a_function_that_fits(self):
        replies = iter(["```python\ndef f(s):\n    return s\n```", FIRST_NAME])
        model = Scripted(lambda m, t, s: next(replies))
        rec = run_B(model, request("first_name"), ModelConfig(), "t")
        self.assertEqual(rec["mode"], "program")
        self.assertTrue(rec["correct"])
        self.assertEqual(rec["calls"], 2)
        self.assertEqual([c["temperature"] for c in rec["model_calls"]], [0.0, 0.7])
        self.assertEqual([c["fits"] for c in rec["model_calls"]], [False, True])

    def test_B_falls_back_to_a_direct_answer(self):
        q = request("first_name")
        gold = json.dumps(list(q.gold))
        model = Scripted(lambda m, t, s: gold if "JSON list" in m[-1]["content"] else "no idea")
        rec = run_B(model, q, ModelConfig(attempts=2), "t")
        self.assertEqual((rec["mode"], rec["calls"], rec["correct"]), ("direct", 3, True))
        self.assertTrue(run_D(model, q, ModelConfig(), "t")["correct"])

    def test_seeds_differ_by_attempt_and_request(self):
        seen = []
        model = Scripted(lambda m, t, s: seen.append(s) or "no")
        run_B(model, request("first_name", 0), ModelConfig(), "t")
        run_B(model, request("first_name", 1), ModelConfig(), "t")
        self.assertEqual(len(seen), 8)  # 3 program attempts and 1 direct fallback per request
        self.assertEqual(len(set(seen)), len(seen))

    def test_memory_answers_recurrences_and_misses_cost_what_B_costs(self):
        reqs = [request("first_name", 0), request("email_domain", 1), request("first_name", 2)]
        model = Scripted(lambda m, t, s: "no" if "@" in m[-1]["content"] else FIRST_NAME)
        b = [run_B(model, q, ModelConfig(attempts=1), "t") for q in reqs]
        s = replay(reqs, [("B", b)])
        self.assertEqual([r["mode"] for r in s], ["miss", "miss", "hit"])
        self.assertEqual(s[2]["calls"], 0)
        self.assertEqual(s[2]["origin"], "first_name")
        self.assertTrue(s[2]["correct"])
        for i in (0, 1):
            self.assertGreaterEqual(s[i]["cpu"], b[i]["cpu"])
            self.assertEqual((s[i]["calls"], s[i]["correct"]), (b[i]["calls"], b[i]["correct"]))

    def test_S_plus_tries_classical_search_before_the_model(self):
        reqs = [request("first_name", 0), request("date_iso_to_long", 1)]
        e = [run_E(q) for q in reqs]
        model = Scripted(lambda m, t, s: "no")
        b = [run_B(model, q, ModelConfig(attempts=1), "t") for q in reqs]
        sp = replay(reqs, [("E", e), ("B", b)])
        self.assertEqual([r["via"] for r in sp], [["E"], ["E", "B"]])
        self.assertEqual(sp[0]["calls"], 0)
        self.assertEqual(sp[1]["calls"], b[1]["calls"])


class MemoryTest(unittest.TestCase):
    def test_identical_code_merges_and_trust_orders_lookup(self):
        m = ProgramMemory()
        m.store("def f(s):\n    return s", 0)
        m.store("def f(s):\n    return s.lower()", 1)
        m.store("def f(s):\n    return s.lower()\n", 2)
        self.assertEqual(len(m), 2)
        hit = m.lookup([("abc", "abc")])  # both fit; the more trusted one is checked first
        self.assertEqual(hit.code, "def f(s):\n    return s.lower()")


if __name__ == "__main__":
    unittest.main()
