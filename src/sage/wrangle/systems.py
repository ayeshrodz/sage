"""The stage 1a systems.

Each of these processes one request and returns a record (see `_record`):
  run_D  one direct call: the model writes the outputs itself
  run_B  up to `attempts` program calls (the first greedy, the rest sampled).
         The first function that reproduces all the examples answers the
         queries; if none does, one direct call answers them
  run_E  the classical synthesizer, with no model; no answer if it finds nothing

The memory systems are replayed over a stream from those records (`replay`),
as in stage 0d. The memory is checked for real and its CPU time measured. A
miss runs exactly the memoryless procedure on the same request, so it takes
that system's recorded result and cost:
  S    memory, then B
  E+M  memory, then E
  S+   memory, then E, then B: the cheapest reliable path first

Costs are CPU seconds of this process, plus any CPU time reported by the
backend for work done outside it (an Ollama server).
"""

from __future__ import annotations

import time
import zlib

from .llm import PROGRAM_STOP, ModelConfig, direct_messages, extract_code, parse_direct, program_messages
from .memory import ProgramMemory
from .sandbox import call, compile_function, reproduces
from .synth import synthesize
from .transforms import TYPES


def seed_of(tag: str, index: int, attempt: int) -> int:
    return zlib.crc32(f"{tag}:{index}:{attempt}".encode())


def _answer(fn, queries) -> list[str]:
    return [call(fn, q) or "" for q in queries]


def _record(req, mode, code, outputs, calls, t0, w0, external=0.0, **extra) -> dict:
    n_correct = sum(o == g for o, g in zip(outputs, req.gold))
    return {"index": req.index, "type": TYPES[req.type_id].name, "mode": mode, "code": code, "outputs": outputs,
            "n_correct": n_correct, "correct": n_correct == len(req.gold), "calls": len(calls),
            "prompt_tokens": sum(c["prompt_tokens"] for c in calls),
            "completion_tokens": sum(c["completion_tokens"] for c in calls),
            "cpu": time.process_time() - t0 + external, "external_cpu": external, "wall": time.perf_counter() - w0,
            "model_calls": calls, **extra}


def _call(model, messages, temperature, max_tokens, seed, stop, kind) -> tuple[dict, str]:
    c0 = time.process_time()
    r = model.chat(messages, temperature, max_tokens, seed, stop)
    return {"kind": kind, "temperature": temperature, "seed": seed, "prompt_tokens": r.prompt_tokens,
            "completion_tokens": r.completion_tokens, "seconds": r.seconds, "external_cpu": r.external_cpu,
            "cpu": time.process_time() - c0 + r.external_cpu, "text": r.text}, r.text


def run_D(model, req, cfg: ModelConfig, tag: str) -> dict:
    t0, w0 = time.process_time(), time.perf_counter()
    c, text = _call(model, direct_messages(req.examples, req.queries), 0.0, cfg.direct_tokens,
                    seed_of(tag, req.index, 99), None, "direct")
    return _record(req, "direct", None, parse_direct(text, len(req.queries)), [c], t0, w0, c["external_cpu"])


def run_B(model, req, cfg: ModelConfig, tag: str) -> dict:
    t0, w0 = time.process_time(), time.perf_counter()
    calls, fn, code = [], None, None
    for a in range(cfg.attempts):
        temperature = 0.0 if a == 0 else cfg.temperature
        c, text = _call(model, program_messages(req.examples), temperature, cfg.program_tokens,
                        seed_of(tag, req.index, a), PROGRAM_STOP, "program")
        c["code"] = extract_code(text)
        f = compile_function(c["code"])
        c["fits"] = reproduces(f, req.examples)
        calls.append(c)
        if c["fits"]:
            fn, code = f, c["code"]
            break
    if fn is not None:
        return _record(req, "program", code, _answer(fn, req.queries), calls, t0, w0,
                       sum(c["external_cpu"] for c in calls))
    c, text = _call(model, direct_messages(req.examples, req.queries), 0.0, cfg.direct_tokens,
                    seed_of(tag, req.index, 99), None, "direct")
    calls.append(c)
    return _record(req, "direct", None, parse_direct(text, len(req.queries)), calls, t0, w0,
                   sum(c["external_cpu"] for c in calls))


def run_E(req) -> dict:
    t0, w0 = time.process_time(), time.perf_counter()
    code, work = synthesize(req.examples)
    fn = compile_function(code)
    if reproduces(fn, req.examples):
        return _record(req, "program", code, _answer(fn, req.queries), [], t0, w0, work=work)
    return _record(req, "none", None, [""] * len(req.queries), [], t0, w0, work=work)


def replay(requests, chain: list[tuple[str, list[dict]]]) -> list[dict]:
    """A verified-program memory in front of a chain of memoryless systems, over a stream.

    `chain` lists (name, records) in the order they are tried on a miss; records
    are the systems' own results on the same requests. The first system whose
    record has an accepted program answers; if none has one, the last system's
    answer stands. The accepted program, if any, is stored.
    """
    by_index = [(name, {r["index"]: r for r in rows}) for name, rows in chain]
    memory = ProgramMemory()
    origin: dict[str, str] = {}  # stored code -> type of the request it was accepted on (the evaluator's view)
    out = []
    for clock, req in enumerate(requests):
        t0 = time.process_time()
        checks = memory.checks
        hit = memory.lookup(req.examples)
        if hit is not None:
            outputs = _answer(hit.fn, req.queries)
            trust = hit.trust
            hit.trust += 1
            hit.last_used = clock
            cpu = time.process_time() - t0
            n_correct = sum(o == g for o, g in zip(outputs, req.gold))
            out.append({"index": req.index, "type": TYPES[req.type_id].name, "mode": "hit", "via": [],
                        "outputs": outputs, "n_correct": n_correct, "correct": n_correct == len(req.gold),
                        "calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "cpu": cpu, "lookup_cpu": cpu,
                        "checks": memory.checks - checks, "trust_used": trust, "origin": origin[hit.code],
                        "memory_size": len(memory)})
            continue
        lookup = time.process_time() - t0
        used = []
        for name, rows in by_index:
            used.append((name, rows[req.index]))
            if rows[req.index]["mode"] == "program":
                break
        final = used[-1][1]
        t1 = time.process_time()
        if final["mode"] == "program":
            s = memory.store(final["code"], clock)
            if s is not None:
                origin.setdefault(s.code, TYPES[req.type_id].name)
        own = lookup + time.process_time() - t1
        out.append({"index": req.index, "type": TYPES[req.type_id].name, "mode": "miss", "via": [n for n, _ in used],
                    "answered_by": final["mode"], "outputs": final["outputs"], "n_correct": final["n_correct"],
                    "correct": final["correct"],
                    "calls": sum(r["calls"] for _, r in used),
                    "prompt_tokens": sum(r["prompt_tokens"] for _, r in used),
                    "completion_tokens": sum(r["completion_tokens"] for _, r in used),
                    "cpu": own + sum(r["cpu"] for _, r in used), "lookup_cpu": lookup,
                    "checks": memory.checks - checks, "memory_size": len(memory)})
    return out
