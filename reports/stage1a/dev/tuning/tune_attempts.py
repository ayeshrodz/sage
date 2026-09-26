"""Development only: acceptance of B's program attempts as a function of the number of attempts and temperature.

Every request of 1a-dev-types gets attempt 0 (greedy) and attempts 1-7 at each temperature, with B's seeds, without
early stopping, so any number of attempts <= 8 can be evaluated offline. Prompts 1a-p1.
"""
import json
import sys
import time

sys.path.insert(0, "/home/user/sage/src")
from sage.wrangle.llm import LlamaCpp, PROGRAM_STOP, extract_code, program_messages  # noqa: E402
from sage.wrangle.requests import norecur_stream  # noqa: E402
from sage.wrangle.sandbox import call, compile_function, reproduces  # noqa: E402
from sage.wrangle.systems import seed_of  # noqa: E402

OUT = "reports/stage1a/dev/tuning/tune_attempts.json"


def attempt(model, r, a, temperature):
    t0 = time.process_time()
    rep = model.chat(program_messages(r.examples), temperature, 384, seed_of("1a-dev-types", r.index, a), PROGRAM_STOP)
    code = extract_code(rep.text)
    fn = compile_function(code)
    fits = reproduces(fn, r.examples)
    general = fits and all(call(fn, x) == g for x, g in zip(r.queries, r.gold))
    return {"a": a, "t": temperature, "fits": fits, "general": general, "cpu": time.process_time() - t0,
            "tokens": rep.completion_tokens, "code": code}


if __name__ == "__main__":
    model = LlamaCpp("/home/user/sage/models/qwen2.5-coder-1.5b-instruct-q4_k_m.gguf")
    rows = []
    t = time.time()
    for r in norecur_stream("1a-dev-types"):
        calls = [attempt(model, r, 0, 0.0)]
        for temperature in (0.7, 1.0):
            calls += [attempt(model, r, a, temperature) for a in range(1, 8)]
        rows.append({"index": r.index, "type_id": r.type_id, "calls": calls})
        if len(rows) % 10 == 0:
            print(f"{len(rows)}/50 ({time.time() - t:.0f}s)", flush=True)
            json.dump(rows, open(OUT, "w"))
    json.dump(rows, open(OUT, "w"))
    for temperature in (0.7, 1.0):
        curve = []
        for k in range(1, 9):
            acc = gen = 0
            for row in rows:
                seq = [c for c in row["calls"] if c["a"] == 0 or c["t"] == temperature][:k]
                first = next((c for c in seq if c["fits"]), None)
                acc += first is not None
                gen += first is not None and first["general"]
            curve.append((k, acc, gen))
        print(f"T={temperature}: attempts -> (accepted, accepted and general):", curve, flush=True)
