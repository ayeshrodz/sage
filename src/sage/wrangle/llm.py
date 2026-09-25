"""Language models for stage 1a: prompts, reply parsing and backends.

Two prompts, both showing the request's examples as JSON strings so that
spaces and punctuation are unambiguous:
  program_messages  asks for a Python function f(s) (systems B and S)
  direct_messages   asks for the outputs themselves, as a JSON list (system D,
                    and B's fallback)
`extract_code` keeps only the definitions from a reply (imports, functions,
constants), so stray prints or tests in the reply cannot break a good
function; `parse_direct` reads a JSON list, or numbered lines if that fails.

Backends share one method, `chat(messages, temperature, max_tokens, seed,
stop)`, which returns a `Reply`. Temperature 0 means greedy decoding.
  LlamaCpp  the model runs inside this process through llama-cpp-python. This
            is the registered setting: its inference threads count towards
            the process CPU time that is the primary cost.
  Ollama    a local Ollama server over HTTP. The server's CPU time is read
            from its processes with psutil (if installed) and reported as
            external CPU time.
  Scripted  a stand-in whose replies come from a Python function, for tests
            and dry runs.
"""

from __future__ import annotations

import ast
import json
import os
import re
import time
import urllib.request
from dataclasses import dataclass

PROMPT_VERSION = "1a-p1"

SYSTEM = "You are an expert Python programmer. You write short, correct text-processing functions."


@dataclass(frozen=True)
class ModelConfig:
    """Everything about calling the model that may be tuned on `1a-dev`, then frozen by amendment."""

    attempts: int = 3  # program attempts per request: the first greedy, the rest sampled
    temperature: float = 0.7  # for the sampled attempts
    program_tokens: int = 384
    direct_tokens: int = 256


@dataclass
class Reply:
    text: str
    prompt_tokens: int
    completion_tokens: int
    seconds: float  # wall-clock time of the call
    external_cpu: float = 0.0  # CPU seconds spent outside this process (Ollama's server)


def _q(s: str) -> str:
    return json.dumps(s, ensure_ascii=False)


def program_messages(examples) -> list[dict]:
    shown = "\n".join(f"f({_q(x)}) == {_q(y)}" for x, y in examples)
    user = (f"Write a Python function `f(s)` that transforms a string the way these examples show:\n\n{shown}\n\n"
            "The function must work for any other input of the same kind, not just these examples. "
            "You may import re, datetime, math, string or calendar. "
            "Reply with only the code, in one ```python block.")
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]


def direct_messages(examples, queries) -> list[dict]:
    shown = "\n".join(f"{_q(x)} -> {_q(y)}" for x, y in examples)
    asked = "\n".join(f"{i + 1}. {_q(q)}" for i, q in enumerate(queries))
    user = (f"Here are examples of a text transformation:\n\n{shown}\n\n"
            f"Apply the same transformation to each of these inputs:\n\n{asked}\n\n"
            f"Reply with only a JSON list of the {len(queries)} outputs, in the same order.")
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]


PROGRAM_STOP = ["\n```\n"]  # the end of the code block; anything after it is commentary
_FENCE = re.compile(r"```[^\n]*\n(.*?)(?:```|\Z)", re.S)
_KEEP = (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.Assign, ast.AnnAssign)


def _parse_prefix(src: str):
    """The module parsed from the longest prefix of whole lines that parses, or None."""
    lines = src.rstrip().split("\n")
    for end in range(len(lines), 0, -1):
        try:
            return ast.parse("\n".join(lines[:end]))
        except SyntaxError:
            continue
    return None


def extract_code(text: str) -> str | None:
    """Normalized source defining `f`, from a model reply, or None if there is no usable function."""
    m = _FENCE.search(text)
    if m:
        src = m.group(1)
    else:
        start = re.search(r"^(?:def |import |from )", text, re.M)
        if start is None:
            return None
        src = text[start.start():]
    tree = _parse_prefix(src)
    if tree is None:
        return None
    keep = [n for n in tree.body if isinstance(n, _KEEP)]
    defs = [n for n in keep if isinstance(n, ast.FunctionDef)]
    if not defs:
        return None
    code = ast.unparse(ast.Module(keep, []))
    if all(d.name != "f" for d in defs):  # use the main function: one no other function calls, the last such
        called = {n.func.id for d in defs for n in ast.walk(d) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
        code += f"\nf = {([d for d in defs if d.name not in called] or defs)[-1].name}"
    return code


_NUMBERED = re.compile(r"^\s*(?:\d+[.)]|[-*])\s+")


def parse_direct(text: str, n: int) -> list[str]:
    """The n outputs from a direct reply: a JSON list if there is one, otherwise one per line."""
    a, b = text.find("["), text.rfind("]")
    if 0 <= a < b:
        for read in (json.loads, ast.literal_eval):  # a JSON list, or a Python one
            try:
                values = read(text[a:b + 1])
            except (ValueError, SyntaxError, TypeError, MemoryError, RecursionError):
                continue
            if isinstance(values, list):
                return ([str(v) for v in values] + [""] * n)[:n]
    out = []
    for line in text.split("\n"):
        line = _NUMBERED.sub("", line.strip())
        if not line or line.startswith("```"):
            continue
        if "->" in line:
            line = line.rsplit("->", 1)[1].strip()
        try:
            v = json.loads(line)
            line = v if isinstance(v, str) else line
        except ValueError:
            pass
        out.append(line)
    return (out + [""] * n)[:n]


class LlamaCpp:
    """A GGUF model run in this process on the CPU through llama-cpp-python."""

    kind = "llama.cpp"

    def __init__(self, model_path: str, threads: int | None = None, n_ctx: int = 4096):
        from llama_cpp import Llama  # imported here so the rest of the package works without it

        self.threads = threads or os.cpu_count() or 1
        self.llm = Llama(model_path=model_path, n_ctx=n_ctx, n_threads=self.threads, n_threads_batch=self.threads,
                         seed=0, verbose=False)
        self.model = os.path.basename(model_path)
        try:
            self.n_params = int(self.llm._model.n_params())
        except Exception:
            self.n_params = None

    def chat(self, messages, temperature: float, max_tokens: int, seed: int, stop=None) -> Reply:
        t0 = time.perf_counter()
        r = self.llm.create_chat_completion(messages=messages, temperature=temperature, max_tokens=max_tokens,
                                           seed=seed, stop=stop or [])
        u = r["usage"]
        return Reply(r["choices"][0]["message"]["content"] or "", u["prompt_tokens"], u["completion_tokens"],
                     time.perf_counter() - t0)


class Ollama:
    """A model served by a local Ollama server (https://ollama.com), for example `qwen2.5-coder:1.5b`."""

    kind = "ollama"

    def __init__(self, model: str = "qwen2.5-coder:1.5b", host: str = "http://127.0.0.1:11434", threads: int | None = None):
        self.model, self.host, self.threads = model, host.rstrip("/"), threads
        self.n_params = None
        self._opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # never via a proxy
        try:
            import psutil  # noqa: F401
            self.measures_cpu = True
        except ImportError:
            self.measures_cpu = False

    def _server_cpu(self) -> float:
        if not self.measures_cpu:
            return 0.0
        import psutil
        total = 0.0
        for p in psutil.process_iter(["name"]):
            if "ollama" in (p.info["name"] or "").lower():
                try:
                    t = p.cpu_times()
                    total += t.user + t.system
                except psutil.Error:
                    pass
        return total

    def chat(self, messages, temperature: float, max_tokens: int, seed: int, stop=None) -> Reply:
        options = {"temperature": temperature, "seed": seed, "num_predict": max_tokens}
        if stop:
            options["stop"] = stop
        if self.threads:
            options["num_thread"] = self.threads
        body = json.dumps({"model": self.model, "messages": messages, "stream": False, "options": options}).encode()
        req = urllib.request.Request(self.host + "/api/chat", body, {"Content-Type": "application/json"})
        cpu0, t0 = self._server_cpu(), time.perf_counter()
        with self._opener.open(req, timeout=900) as resp:
            data = json.loads(resp.read())
        seconds, cpu = time.perf_counter() - t0, self._server_cpu() - cpu0
        return Reply(data["message"]["content"], data.get("prompt_eval_count", 0), data.get("eval_count", 0), seconds, cpu)


class Scripted:
    """A stand-in model: `respond(messages, temperature, seed)` returns the reply text. Tokens are words."""

    kind = "scripted"

    def __init__(self, respond, model: str = "scripted"):
        self.respond, self.model, self.threads, self.n_params = respond, model, 1, None

    def chat(self, messages, temperature: float, max_tokens: int, seed: int, stop=None) -> Reply:
        t0 = time.perf_counter()
        text = self.respond(messages, temperature, seed)
        return Reply(text, sum(len(m["content"].split()) for m in messages), len(text.split()),
                     time.perf_counter() - t0)
