"""Development only: compare program-prompt variants for system B on 1a-dev-types (never on registered streams)."""
import json
import sys
import time

sys.path.insert(0, "/home/user/sage/src")
from sage.wrangle.llm import (SYSTEM, LlamaCpp, PROGRAM_STOP, direct_messages, extract_code,  # noqa: E402
                              parse_direct)
from sage.wrangle.requests import norecur_stream  # noqa: E402
from sage.wrangle.sandbox import call, compile_function, reproduces  # noqa: E402
from sage.wrangle.systems import seed_of  # noqa: E402

q = json.dumps
RULES = ("First write a comment that states the rule in one sentence, then the function. "
         "The function must work for any other input of the same kind: don't hard-code values from the examples. "
         "Prefer plain string methods (split, join, slicing, upper, lower) where they suffice. "
         "You may import re, datetime, math, string or calendar. Reply with only the code, in one ```python block.")
SHOT_USER = ("Write a Python function `f(s)` that turns each input string into its output string, following these "
             "examples:\n\nInput: \"Smith, John (Sales)\"\nOutput: \"Sales\"\n\nInput: \"Okoro, Ada (Research)\"\n"
             "Output: \"Research\"\n\nInput: \"Lee, Min (IT)\"\nOutput: \"IT\"\n\n" + RULES)
SHOT_REPLY = "```python\n# Rule: take the text between the parentheses.\ndef f(s):\n    return s.split(\"(\")[1].split(\")\")[0]\n```"


def p2_user(examples):
    shown = "\n\n".join(f"Input: {q(x)}\nOutput: {q(y)}" for x, y in examples)
    return ("Write a Python function `f(s)` that turns each input string into its output string, following these "
            f"examples:\n\n{shown}\n\n" + RULES)


def messages(examples, shot):
    m = [{"role": "system", "content": SYSTEM}]
    if shot:
        m += [{"role": "user", "content": SHOT_USER}, {"role": "assistant", "content": SHOT_REPLY}]
    return m + [{"role": "user", "content": p2_user(examples)}]


def feedback(fn, examples):
    if fn is None:
        return "Your reply did not contain a working function `f`. Write it again. Reply with only the code, in one ```python block."
    lines = []
    for x, y in examples:
        got = call(fn, x)
        if got != y:
            lines.append(f"f({q(x)}) returned {q(got) if got is not None else 'an error'} but should return {q(y)}")
    return ("That function is wrong on these examples:\n" + "\n".join(lines) +
            "\n\nWrite a corrected function. Reply with only the code, in one ```python block.")


def run_variant(model, reqs, shot, repair, attempts=3, temperature=0.7):
    rows = []
    for r in reqs:
        t0 = time.process_time()
        base = messages(r.examples, shot)
        convo = list(base)
        fn = code = None
        acc_at, n_calls = None, 0
        for a in range(attempts):
            temp = 0.0 if a == 0 else temperature
            msgs = convo if repair else base
            rep = model.chat(msgs, temp, 384, seed_of("1a-dev-types", r.index, a), PROGRAM_STOP)
            n_calls += 1
            c = extract_code(rep.text)
            f = compile_function(c)
            if reproduces(f, r.examples):
                fn, code, acc_at = f, c, a + 1
                break
            if repair:
                convo = base + [{"role": "assistant", "content": rep.text + "\n```"}, {"role": "user", "content": feedback(f, r.examples)}]
        if fn is not None:
            outs = [call(fn, x) or "" for x in r.queries]
        else:
            rep = model.chat(direct_messages(r.examples, r.queries), 0.0, 256, seed_of("1a-dev-types", r.index, 99), None)
            n_calls += 1
            outs = parse_direct(rep.text, len(r.queries))
        nc = sum(o == g for o, g in zip(outs, r.gold))
        rows.append({"index": r.index, "accepted_at": acc_at, "n_correct": nc, "correct": nc == 5,
                     "cpu": time.process_time() - t0, "calls": n_calls, "code": code})
    return rows


if __name__ == "__main__":
    model = LlamaCpp("/home/user/sage/models/qwen2.5-coder-1.5b-instruct-q4_k_m.gguf")
    reqs = norecur_stream("1a-dev-types")
    out = {}
    for name, shot, repair in [("p2", False, False), ("p2+shot", True, False), ("p2+repair", False, True),
                               ("p2+shot+repair", True, True)]:
        t = time.time()
        rows = run_variant(model, reqs, shot, repair)
        acc = sum(r["accepted_at"] is not None for r in rows)
        wrong_acc = sum(r["accepted_at"] is not None and not r["correct"] for r in rows)
        print(f"{name:16s} accepted {acc}/50 (at 1/2/3: {[sum(r['accepted_at'] == k for r in rows) for k in (1, 2, 3)]}),"
              f" accepted but wrong {wrong_acc}, correct {sum(r['correct'] for r in rows)}/50,"
              f" outputs {sum(r['n_correct'] for r in rows)}/250, calls {sum(r['calls'] for r in rows)},"
              f" CPU {sum(r['cpu'] for r in rows):.0f}s ({time.time() - t:.0f}s)", flush=True)
        out[name] = rows
    json.dump(out, open("reports/stage1a/dev/tuning/tune_prompts.json", "w"))
