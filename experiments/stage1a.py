"""Stage 1a: a real workload with a small language model (pre-registration: docs/10-stage-1a-preregistration.md).

Streams (all built deterministically from the code; nothing is cached):
  dev, dev-types      development streams, free to use: 100 Zipf requests, and every type once
  zipf, norecur       the registered streams `1a-zipf` (300 requests) and `1a-norecur` (50)

Phases:
  generate            writes the hashed manifests of the registered streams, once, after the
                      settings are frozen by amendment. `solve` refuses registered streams before this.
  solve --system E|B|D --stream S
                      runs one memoryless system over a stream and appends one record per request
                      to a JSONL file (resumes an interrupted run; --restart starts over).
                      B and D need a model: --backend llama (in-process, the registered setting)
                      with --model path/to/model.gguf, or --backend ollama with --model NAME.
                      --backend fake answers with the classical synthesizer instead of a model,
                      for dry runs of the pipeline only.
  report --stream S   replays the memory systems (S, E+M, S+) and prints a summary of every system
                      run so far on that stream; for development streams.
  final               the registered report: W1-W4 and everything pre-declared, written to
                      reports/stage1a.{md,json}. Refuses to run twice unless --force is given.

Usage:
  PYTHONPATH=src python experiments/stage1a.py solve --system E --stream dev
  PYTHONPATH=src python experiments/stage1a.py solve --system B --stream dev --backend llama \\
      --model models/qwen2.5-coder-1.5b-instruct-q4_k_m.gguf
  PYTHONPATH=src python experiments/stage1a.py report --stream dev
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import json
import os
import platform
import re
import statistics
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sage.wrangle.llm import PROMPT_VERSION, LlamaCpp, ModelConfig, Ollama, Scripted  # noqa: E402
from sage.wrangle.requests import VERSION, manifest, norecur_stream, zipf_stream  # noqa: E402
from sage.wrangle.synth import synthesize  # noqa: E402
from sage.wrangle.systems import replay, run_B, run_D, run_E  # noqa: E402

OUT = ROOT / "reports" / "stage1a"
STREAMS = {
    "dev": ("1a-dev", lambda: zipf_stream("1a-dev", 100)),
    "dev-types": ("1a-dev-types", lambda: norecur_stream("1a-dev-types")),
    "zipf": ("1a-zipf", lambda: zipf_stream("1a-zipf", 300)),
    "norecur": ("1a-norecur", lambda: norecur_stream("1a-norecur")),
}
REGISTERED = ("zipf", "norecur")
CONFIG = ModelConfig()  # tuned on the development streams, then frozen by amendment
DEFAULT_MODEL = {"llama": str(ROOT / "models" / "qwen2.5-coder-1.5b-instruct-q4_k_m.gguf"),
                 "ollama": "qwen2.5-coder:1.5b", "fake": "classical synthesizer"}
W1_MIN, W2_MIN, W3_MIN, W4_MAX = 0.50, 2.0, -0.02, 1.05
WINDOW = 50


def git_revision() -> str:
    try:
        rev = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
        dirty = bool(subprocess.check_output(["git", "status", "--porcelain", "src", "experiments"], cwd=ROOT, text=True))
        return rev + ("+dirty" if dirty else "")
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def machine() -> dict:
    cpu = platform.processor()
    try:
        cpu = re.search(r"model name\s*:\s*(.*)", Path("/proc/cpuinfo").read_text()).group(1)
    except (OSError, AttributeError):
        pass
    return {"platform": platform.platform(), "cpu": cpu, "logical_cores": os.cpu_count(),
            "python": platform.python_version()}


def same_cpu(a: dict, b: dict) -> bool:
    """CPU time is only comparable on the same processor model with the same number of cores."""
    return (a["cpu"], a["logical_cores"]) == (b["cpu"], b["logical_cores"])


def build(stream: str):
    return STREAMS[stream][1]()


def records_path(system: str, stream: str) -> Path:
    return (OUT if stream in REGISTERED else OUT / "dev") / f"{system}_{stream}.jsonl"


def check_manifest(stream: str, requests) -> None:
    f = OUT / "manifests.json"
    if not f.exists():
        sys.exit("the registered streams have not been generated yet: freeze the settings by amendment, then run `generate`")
    registered = {m["stream"]: m for m in json.loads(f.read_text())}
    if registered[STREAMS[stream][0]] != manifest(STREAMS[stream][0], requests):
        sys.exit(f"stream {stream} no longer matches its registered manifest: the generator changed")


def phase_generate(args) -> None:
    f = OUT / "manifests.json"
    if f.exists() and not args.force:
        sys.exit("the stage 1a streams were already generated (use --force)")
    OUT.mkdir(parents=True, exist_ok=True)
    ms = []
    for k in REGISTERED:
        requests = build(k)
        ms.append(manifest(STREAMS[k][0], requests))
        print(f"{STREAMS[k][0]}: {len(requests)} requests of {len({q.type_id for q in requests})} types")
    f.write_text(json.dumps(ms, indent=1))


def fake_model() -> Scripted:
    """Answers program prompts with the classical synthesizer and direct prompts with the inputs unchanged."""
    def respond(messages, temperature, seed):
        text = messages[-1]["content"]
        examples = [(json.loads(x), json.loads(y)) for x, y in re.findall(r'^f\((".*")\) == (".*")$', text, re.M)]
        if examples:
            code, _ = synthesize(examples)
            return f"```python\n{code}\n```" if code else "I could not find a function."
        return json.dumps([json.loads(q) for q in re.findall(r'^\d+\. (".*")$', text, re.M)])
    return Scripted(respond, "fake: classical synthesizer")


def load_model(args):
    model = args.model or DEFAULT_MODEL[args.backend]
    if args.backend == "llama":
        if not Path(model).exists():
            sys.exit(f"model file not found: {model} (see docs/11-stage-1a-running.md)")
        return LlamaCpp(model, threads=args.threads)
    if args.backend == "ollama":
        return Ollama(model, threads=args.threads)
    return fake_model()


def read_records(path: Path) -> tuple[dict | None, list[dict]]:
    if not path.exists():
        return None, []
    lines = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    return lines[0], lines[1:]


def phase_solve(args) -> None:
    requests = build(args.stream)
    if args.stream in REGISTERED:
        if args.system != "E" and args.backend == "fake":
            sys.exit("the fake model is for dry runs on the development streams only")
        check_manifest(args.stream, requests)
    if args.limit:
        requests = requests[:args.limit]
    path = records_path(args.system, args.stream)
    path.parent.mkdir(parents=True, exist_ok=True)
    needs_model = args.system in ("B", "D")
    header = {"system": args.system, "stream": STREAMS[args.stream][0], "generator": VERSION,
              "prompt_version": PROMPT_VERSION if needs_model else None,
              "config": dataclasses.asdict(CONFIG) if needs_model else None,
              "backend": args.backend if needs_model else None, "model": None, "threads": None,
              "machine": machine()}
    model = None
    if needs_model:
        t0 = time.process_time()
        model = load_model(args)
        header.update(model=model.model, threads=model.threads, n_params=model.n_params,
                      load_cpu=time.process_time() - t0)
    header.update(git=git_revision(), started=dt.datetime.now().isoformat(timespec="seconds"))
    old, done = (None, []) if args.restart else read_records(path)
    if old is not None:
        identity = ("system", "stream", "generator", "prompt_version", "config", "backend", "model", "threads")
        changed = [k for k in identity if old.get(k) != header[k]]
        if same_cpu(old["machine"], header["machine"]) is False:
            changed.append("machine")
        if changed:
            sys.exit(f"{path} was started with different {', '.join(changed)}; use --restart to start over")
        if old.get("git") != header["git"]:
            print(f"warning: resuming a run started at git {old.get('git')} from git {header['git']}", flush=True)
    todo = [q for q in requests if q.index not in {r["index"] for r in done}]
    mode = "w" if old is None else "a"
    tag = STREAMS[args.stream][0]
    t0, n = time.time(), len(done)
    with open(path, mode) as f:
        if old is None:
            f.write(json.dumps(header) + "\n")
        for q in todo:
            if args.system == "E":
                rec = run_E(q)
            elif args.system == "B":
                rec = run_B(model, q, CONFIG, tag)
            else:
                rec = run_D(model, q, CONFIG, tag)
            f.write(json.dumps(rec) + "\n")
            f.flush()
            n += 1
            done.append(rec)
            if n % 10 == 0 or n == len(requests):
                acc = sum(r["correct"] for r in done) / len(done)
                print(f"{args.system} {args.stream}: {n}/{len(requests)} requests, {acc:.0%} correct,"
                      f" {sum(r['cpu'] for r in done):.1f} CPU s ({time.time() - t0:.0f}s)", flush=True)


# ---------------------------------------------------------------- evaluation


def share(xs) -> float | None:
    xs = list(xs)
    return sum(xs) / len(xs) if xs else None


def summarize(rows: list[dict], n_params: int | None) -> dict:
    n = len(rows)
    cpu = sum(r["cpu"] for r in rows)
    correct = sum(r["correct"] for r in rows)
    tokens = sum(r["prompt_tokens"] + r["completion_tokens"] for r in rows)
    hits = [r for r in rows if r["mode"] == "hit"]
    types = sorted({r["type"] for r in rows})
    return {
        "requests": n, "correct": correct / n, "output_accuracy": sum(r["n_correct"] for r in rows) / (5 * n),
        "model_calls": sum(r["calls"] for r in rows), "requests_with_model_call": sum(r["calls"] > 0 for r in rows),
        "prompt_tokens": sum(r["prompt_tokens"] for r in rows),
        "completion_tokens": sum(r["completion_tokens"] for r in rows),
        "model_flops": 2 * n_params * tokens if n_params else None,
        "cpu_total": cpu, "cpu_per_request": cpu / n, "cpu_per_correct": cpu / correct if correct else None,
        "answered_by_function": share(r["mode"] in ("program", "hit") or r.get("answered_by") == "program"
                                      for r in rows),
        "hits": len(hits), "hit_rate": len(hits) / n, "hit_precision": share(r["correct"] for r in hits),
        "hit_precision_by_trust": {label: (share(r["correct"] for r in hits if lo <= r["trust_used"] <= hi),
                                           sum(lo <= r["trust_used"] <= hi for r in hits))
                                   for label, lo, hi in (("1", 1, 1), ("2-4", 2, 4), ("5+", 5, 10 ** 9))},
        "foreign_hits": sum(r["origin"] != r["type"] for r in hits),
        "foreign_hit_precision": share(r["correct"] for r in hits if r["origin"] != r["type"]),
        "median_hit_cpu": statistics.median(r["cpu"] for r in hits) if hits else None,
        "mean_lookup_cpu": share(r["lookup_cpu"] for r in rows) if rows and "lookup_cpu" in rows[0] else None,
        "final_memory": rows[-1].get("memory_size") if rows else None,
        "windows": [{"cpu": statistics.fmean(r["cpu"] for r in rows[w:w + WINDOW]),
                     "correct": share(r["correct"] for r in rows[w:w + WINDOW]),
                     "hit_rate": share(r["mode"] == "hit" for r in rows[w:w + WINDOW])} for w in range(0, n, WINDOW)],
        "per_type": {t: {"requests": sum(r["type"] == t for r in rows),
                         "correct": share(r["correct"] for r in rows if r["type"] == t),
                         "cpu": statistics.fmean(r["cpu"] for r in rows if r["type"] == t),
                         "hits": sum(r["type"] == t and r["mode"] == "hit" for r in rows)} for t in types},
    }


def model_diagnostics(rows: list[dict]) -> dict:
    """How B's model calls went: where functions were accepted, and why attempts failed."""
    program = [c for r in rows for c in r["model_calls"] if c["kind"] == "program"]
    direct = [c for r in rows for c in r["model_calls"] if c["kind"] == "direct"]
    accepted = [sum(c["kind"] == "program" for c in r["model_calls"]) for r in rows if r["mode"] == "program"]
    return {"accepted_at_attempt": {k: accepted.count(k) for k in sorted(set(accepted))},
            "direct_fallbacks": sum(r["mode"] == "direct" for r in rows),
            "program_calls": len(program), "no_function": sum(c["code"] is None for c in program),
            "function_not_fitting": sum(c["code"] is not None and not c["fits"] for c in program),
            "mean_program_tokens": share(c["completion_tokens"] for c in program),
            "mean_direct_tokens": share(c["completion_tokens"] for c in direct),
            "mean_call_seconds": share(c["seconds"] for c in program + direct)}


def compare(base: list[dict], mem: list[dict]) -> dict:
    """A memory system against the memoryless system it falls back to, on the same requests."""
    b_cpu, m_cpu = sum(r["cpu"] for r in base), sum(r["cpu"] for r in mem)
    b_cor, m_cor = sum(r["correct"] for r in base), sum(r["correct"] for r in mem)
    cb = cm = 0.0
    ahead = []
    for rb, rm in zip(base, mem):
        cb, cm = cb + rb["cpu"], cm + rm["cpu"]
        ahead.append(cm <= cb)
    k = len(ahead)
    while k > 0 and ahead[k - 1]:
        k -= 1
    return {"hit_share": sum(r["mode"] == "hit" for r in mem) / len(mem),
            "cost_per_correct_ratio": (b_cpu / b_cor) / (m_cpu / m_cor) if b_cor and m_cor else None,
            "accuracy_diff": (m_cor - b_cor) / len(mem), "total_cpu_ratio": m_cpu / b_cpu if b_cpu else None,
            "calls_avoided": sum(r["calls"] for r in base) - sum(r["calls"] for r in mem),
            "break_even_requests": k + 1 if k < len(ahead) else None}


def evaluate(stream: str) -> dict:
    requests = build(stream)
    if stream in REGISTERED:
        check_manifest(stream, requests)
    headers, base = {}, {}
    for system in ("B", "D", "E"):
        h, rows = read_records(records_path(system, stream))
        if h is not None and rows:
            headers[system], base[system] = h, rows
    if not base:
        sys.exit(f"no results on stream {stream} yet")
    n = min(len(rows) for rows in base.values())
    requests = requests[:n]
    base = {k: sorted(v, key=lambda r: r["index"])[:n] for k, v in base.items()}
    for k, v in base.items():
        if [r["index"] for r in v] != [q.index for q in requests]:
            sys.exit(f"{k} on {stream} does not cover the first {n} requests in order")
    systems = dict(base)
    if "B" in base:
        systems["S"] = replay(requests, [("B", base["B"])])
    if "E" in base:
        systems["E+M"] = replay(requests, [("E", base["E"])])
    if "E" in base and "B" in base:
        systems["S+"] = replay(requests, [("E", base["E"]), ("B", base["B"])])
    n_params = next((h.get("n_params") for h in headers.values() if h.get("n_params")), None)
    here = machine()
    out = {"stream": STREAMS[stream][0], "requests": n, "types": len({q.type_id for q in requests}),
           "headers": headers, "replayed_on": here,
           "one_machine": all(same_cpu(h["machine"], here) for h in headers.values()),
           "systems": {k: summarize(v, n_params) for k, v in systems.items()}, "compare": {}}
    for mem, b in (("S", "B"), ("E+M", "E"), ("S+", "B")):
        if mem in systems:
            out["compare"][f"{mem} vs {b}"] = compare(systems[b], systems[mem])
    if "B" in base:
        out["diagnostics"] = model_diagnostics(base["B"])
    out["rows"] = systems
    return out


# ------------------------------------------------------------------ reports

pct = lambda x: "—" if x is None else f"{x:.1%}"  # noqa: E731
mult = lambda x: "—" if x is None else f"{x:.1f}×"  # noqa: E731


def sec(x: float | None) -> str:
    if x is None:
        return "—"
    return f"{x:,.2f} s" if x >= 1 else f"{x * 1e3:.2f} ms" if x >= 1e-3 else f"{x * 1e6:.0f} µs"


ORDER = ("D", "B", "S", "E", "E+M", "S+")


def system_table(ev: dict) -> list[str]:
    lines = ["| System | Correct requests | Correct outputs | Model calls | Tokens (prompt + generated) |"
             " CPU s total | CPU per correct | Hits | Hit precision |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for k in ORDER:
        s = ev["systems"].get(k)
        if s is None:
            continue
        lines.append(f"| {k} | {pct(s['correct'])} | {pct(s['output_accuracy'])} | {s['model_calls']:,} |"
                     f" {s['prompt_tokens']:,} + {s['completion_tokens']:,} | {s['cpu_total']:,.1f} |"
                     f" {sec(s['cpu_per_correct'])} | {s['hits'] if k in ('S', 'E+M', 'S+') else '—'} |"
                     f" {pct(s['hit_precision']) if k in ('S', 'E+M', 'S+') else '—'} |")
    return lines


def dev_report(ev: dict) -> str:
    lines = [f"# Stage 1a development summary: `{ev['stream']}`", "",
             f"{ev['requests']} requests of {ev['types']} types. Development stream: not a registered result.", ""]
    if not ev["one_machine"]:
        lines += ["**Warning:** these results come from different processors, so their CPU times are not comparable.", ""]
    lines += system_table(ev) + [""]
    for name, c in ev["compare"].items():
        lines.append(f"- {name}: hits {pct(c['hit_share'])}, CPU per correct request {name.split(' vs ')[1]} ÷"
                     f" {name.split(' vs ')[0]} {mult(c['cost_per_correct_ratio'])},"
                     f" accuracy {c['accuracy_diff'] * 100:+.1f} pts, total CPU ratio {c['total_cpu_ratio']:.3f},"
                     f" model calls avoided {c['calls_avoided']}")
    if "diagnostics" in ev:
        lines.append(f"- B's model calls: {ev['diagnostics']}")
    for k, h in ev["headers"].items():
        lines.append(f"- {k}: git {h.get('git')}, model {h.get('model')}, prompts {h.get('prompt_version')},"
                     f" config {h.get('config')}, machine {h['machine']['cpu']} × {h['machine']['logical_cores']}")
    lines += ["", "Per type (correct requests):", "", "| Type | n | " + " | ".join(k for k in ORDER if k in ev["systems"]) + " |",
              "|---|---:|" + "---:|" * sum(k in ev["systems"] for k in ORDER)]
    first = next(iter(ev["systems"].values()))["per_type"]
    for t, v in sorted(first.items()):
        lines.append(f"| {t} | {v['requests']} | " + " | ".join(
            pct(ev["systems"][k]["per_type"][t]["correct"]) for k in ORDER if k in ev["systems"]) + " |")
    return "\n".join(lines) + "\n"


def phase_report(args) -> None:
    ev = evaluate(args.stream)
    text = dev_report(ev)
    if args.stream not in REGISTERED:
        (OUT / "dev").mkdir(parents=True, exist_ok=True)
        (OUT / "dev" / f"summary_{args.stream}.md").write_text(text)
    print(text)


def phase_final(args) -> None:
    if (ROOT / "reports" / "stage1a.md").exists() and not args.force:
        sys.exit("stage 1a final results already exist (use --force)")
    evs = {k: evaluate(k) for k in REGISTERED}
    for k, ev in evs.items():
        missing = {"B", "D", "E"} - set(ev["headers"])
        if missing or ev["requests"] != len(build(k)):
            sys.exit(f"stream {k} is incomplete: systems missing {sorted(missing)}, {ev['requests']} requests")
    z, nr = evs["zipf"]["compare"]["S vs B"], evs["norecur"]["compare"]["S vs B"]
    verdict = {"W1": {"value": z["hit_share"], "pass": z["hit_share"] >= W1_MIN},
               "W2": {"value": z["cost_per_correct_ratio"],
                      "pass": z["cost_per_correct_ratio"] is not None and z["cost_per_correct_ratio"] >= W2_MIN},
               "W3": {"value": z["accuracy_diff"], "pass": z["accuracy_diff"] >= W3_MIN},
               "W4": {"value": nr["total_cpu_ratio"], "pass": nr["total_cpu_ratio"] <= W4_MAX}}
    out = {"git": git_revision(), "verdict": verdict,
           "streams": {k: {kk: vv for kk, vv in ev.items() if kk != "rows"} for k, ev in evs.items()}}
    (ROOT / "reports" / "stage1a.json").write_text(json.dumps(out, indent=1))
    OUT.mkdir(parents=True, exist_ok=True)
    for k, ev in evs.items():  # per-request rows of the replayed memory systems
        (OUT / f"replay_{k}.json").write_text(json.dumps({s: ev["rows"][s] for s in ("S", "E+M", "S+")}))
    write_final(out)


def write_final(out: dict) -> None:
    v = out["verdict"]
    mark = lambda ok: "PASS" if ok else "FAIL"  # noqa: E731
    zs = out["streams"]["zipf"]
    hb = zs["headers"]["B"]
    lines = [
        "# Stage 1a results: a real workload with a small language model", "",
        f"Generated by `experiments/stage1a.py final` at git `{out['git']}`. Model: {hb.get('model')} via {hb.get('backend')},"
        f" {hb.get('threads')} threads, on {hb['machine']['cpu']} ({hb['machine']['logical_cores']} logical cores)."
        f" Prompts {hb.get('prompt_version')}, settings {hb.get('config')}."
        " Pre-registration: `docs/10-stage-1a-preregistration.md`.", "",
        *([] if all(out["streams"][k]["one_machine"] for k in REGISTERED) else
          ["**Warning:** the runs used different processors, so their CPU times are not comparable.", ""]),
        "## Pre-registered criteria (S against B)", "",
        "| Criterion | Value | Threshold | Result |", "|---|---:|---:|---|",
        f"| W1: share of `1a-zipf` answered from memory | {pct(v['W1']['value'])} | ≥ 50% | {mark(v['W1']['pass'])} |",
        f"| W2: B ÷ S CPU time per correct request (`1a-zipf`) | {mult(v['W2']['value'])} | ≥ 2× | {mark(v['W2']['pass'])} |",
        f"| W3: S − B request accuracy (`1a-zipf`) | {v['W3']['value'] * 100:+.1f} pts | ≥ −2 pts | {mark(v['W3']['pass'])} |",
        f"| W4: S ÷ B total CPU time (`1a-norecur`) | {v['W4']['value']:.3f} | ≤ 1.05 | {mark(v['W4']['pass'])} |",
    ]
    for k, title in (("zipf", "`1a-zipf`: 300 requests, Zipf 1.0 over 50 types"),
                     ("norecur", "`1a-norecur`: 50 requests, each type once")):
        ev = out["streams"][k]
        lines += ["", f"## {title}", ""] + system_table(ev) + [""]
        for name, c in ev["compare"].items():
            base, mem = name.split(" vs ")[1], name.split(" vs ")[0]
            lines.append(f"- **{name}:** answered from memory {pct(c['hit_share'])}; CPU per correct request"
                         f" {base} ÷ {mem} {mult(c['cost_per_correct_ratio'])}; accuracy {c['accuracy_diff'] * 100:+.1f} points;"
                         f" total CPU ratio {c['total_cpu_ratio']:.3f}; {c['calls_avoided']:,} model calls avoided;"
                         f" break-even after {c['break_even_requests'] or '—'} requests.")
    d = zs["diagnostics"]
    lines += ["", f"B's model calls on `1a-zipf`: functions accepted at attempt 1, 2, 3:"
              f" {', '.join(str(d['accepted_at_attempt'].get(k, 0)) for k in (1, 2, 3))}; direct fallbacks"
              f" {d['direct_fallbacks']}; of {d['program_calls']} program calls, {d['no_function']} gave no function"
              f" and {d['function_not_fitting']} a function that did not fit the examples."]
    s = zs["systems"]["S"]
    lines += ["", "## Memory on `1a-zipf` (S)", "",
              f"- Stored functions at the end: {s['final_memory']}; median CPU time of a hit {sec(s['median_hit_cpu'])};"
              f" mean lookup {sec(s['mean_lookup_cpu'])}.",
              "- Hit precision by trust: " + ", ".join(f"trust {k}: {pct(p)} (n={n})"
                                                       for k, (p, n) in s["hit_precision_by_trust"].items()) + ".",
              f"- Hits by a function stored for another type: {s['foreign_hits']}"
              f" (precision {pct(s['foreign_hit_precision'])}).",
              "", "Learning curve (windows of 50 requests): mean CPU s per request, B → S; S's hit rate.", "",
              "| Requests | B | S | S hit rate |", "|---|---:|---:|---:|"]
    for j, (wb, ws) in enumerate(zip(zs["systems"]["B"]["windows"], s["windows"])):
        lines.append(f"| {j * WINDOW + 1}–{(j + 1) * WINDOW} | {wb['cpu']:.2f} | {ws['cpu']:.2f} | {pct(ws['hit_rate'])} |")
    lines += ["", "## Per type on `1a-zipf` (correct requests)", "",
              "| Type | n | D | B | S | E | S+ | S hits |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for t, b in sorted(zs["systems"]["B"]["per_type"].items(), key=lambda kv: -kv[1]["requests"]):
        row = [pct(zs["systems"][k]["per_type"][t]["correct"]) for k in ("D", "B", "S", "E", "S+")]
        lines.append(f"| {t} | {b['requests']} | " + " | ".join(row) + f" | {zs['systems']['S']['per_type'][t]['hits']} |")
    lines += ["", "Per-request records: `reports/stage1a/`; stream manifests: `reports/stage1a/manifests.json`."]
    text = "\n".join(lines) + "\n"
    (ROOT / "reports" / "stage1a.md").write_text(text)
    print(text)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="phase", required=True)
    g = sub.add_parser("generate")
    g.add_argument("--force", action="store_true")
    s = sub.add_parser("solve")
    s.add_argument("--system", choices=("E", "B", "D"), required=True)
    s.add_argument("--stream", choices=tuple(STREAMS), required=True)
    s.add_argument("--backend", choices=("llama", "ollama", "fake"), default="llama")
    s.add_argument("--model", help="GGUF file (llama) or model name (ollama)")
    s.add_argument("--threads", type=int, help="inference threads (default: all logical cores)")
    s.add_argument("--limit", type=int, help="only the first N requests (development)")
    s.add_argument("--restart", action="store_true", help="discard earlier records of this system and stream")
    r = sub.add_parser("report")
    r.add_argument("--stream", choices=tuple(STREAMS), required=True)
    f = sub.add_parser("final")
    f.add_argument("--force", action="store_true")
    args = ap.parse_args()
    {"generate": phase_generate, "solve": phase_solve, "report": phase_report, "final": phase_final}[args.phase](args)


if __name__ == "__main__":
    main()
