"""Running generated Python functions with restricted built-ins and a time limit.

Only a whitelist of built-ins is available, `import` is limited to re,
datetime, math, string and calendar, and each call is interrupted after a
time limit (POSIX only; elsewhere calls run without a limit). This keeps
research runs on synthetic data safe from accidents such as endless loops or
file access. It is not a security boundary for untrusted code on real data;
use a container or subprocess for that.
"""

from __future__ import annotations

import builtins
import signal

ALLOWED_MODULES = {"re", "datetime", "math", "string", "calendar"}
_SAFE = ["abs", "all", "any", "ascii", "bin", "bool", "bytes", "callable", "chr", "dict", "divmod", "enumerate",
         "filter", "float", "format", "frozenset", "hash", "hex", "int", "isinstance", "iter", "len", "list", "map",
         "max", "min", "next", "oct", "ord", "pow", "range", "repr", "reversed", "round", "set", "slice", "sorted",
         "str", "sum", "tuple", "zip", "Exception", "ArithmeticError", "AttributeError", "IndexError", "KeyError",
         "LookupError", "OverflowError", "RuntimeError", "StopIteration", "TypeError", "ValueError",
         "ZeroDivisionError"]


def _import(name, globals=None, locals=None, fromlist=(), level=0):
    if name.split(".")[0] not in ALLOWED_MODULES or level:
        raise ImportError(f"module {name!r} is not allowed")
    return builtins.__import__(name, globals, locals, fromlist, level)


SAFE_BUILTINS = {n: getattr(builtins, n) for n in _SAFE}
SAFE_BUILTINS["__import__"] = _import
_HAS_TIMER = hasattr(signal, "setitimer")


class _Timeout(Exception):
    pass


def _alarm(signum, frame):
    raise _Timeout()


def _limited(fn, arg, seconds: float):
    if not _HAS_TIMER:
        return fn(arg)
    old = signal.signal(signal.SIGALRM, _alarm)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        return fn(arg)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old)


def compile_function(code: str | None, seconds: float = 0.5):
    """The function `f` defined by `code`, or None if it does not compile or define one."""
    if not code:
        return None
    namespace = {"__builtins__": SAFE_BUILTINS}
    try:
        _limited(lambda c: exec(c, namespace), code, seconds)
    except BaseException:
        return None
    fn = namespace.get("f")
    return fn if callable(fn) else None


def call(fn, s: str, seconds: float = 0.2) -> str | None:
    """fn(s) as a string, or None if it fails, times out or returns something else."""
    try:
        out = _limited(fn, s, seconds)
    except BaseException:
        return None
    return out if isinstance(out, str) and len(out) <= 1000 else None


def reproduces(fn, examples) -> bool:
    return fn is not None and all(call(fn, x) == y for x, y in examples)
