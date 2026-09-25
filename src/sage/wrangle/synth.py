"""Classical program search for stage 1a: a small autofill-style synthesizer, no model.

A program is a concatenation of parts. A part is either a constant string or
an *atom*: case(slice(field(s))), where
  field  s itself, s.split(sep)[k], s.split()[k], digits only, letters only,
         whitespace collapsed, or a common replacement (spaces to hyphens, ...)
  slice  none, a short prefix or suffix, or (on s itself) s[a:b] for a < b <= 10
  case   none, lower, upper, title or capitalize.

The search is over all examples at once. A state is a tuple of positions, one
per example output; an atom or constant is a valid next part only if it
matches every output at its position. States are expanded in order of fewer
parts, then fewer constant characters, so the simplest consistent program is
returned. Among equally simple programs the more general atoms win: atoms are
ordered from general to specific (whole parts before fixed character
positions, first and last parts before middle ones), and of atoms that behave
identically on the examples only the first is kept. The program is emitted as
a normal Python function `f(s)`, the same form a language model produces, so
it goes through the same sandbox and memory.
"""

from __future__ import annotations

import heapq
import itertools

SEPS = [" ", ",", "@", ".", "-", "/", "_", ":", "#"]
PARTS = (0, -1, 1, 2, -2)  # first and last parts before middle ones


def _fields():
    out = [("s", lambda s: s)]
    for k in PARTS:
        out.append((f"s.split()[{k}]", lambda s, k=k: s.split()[k]))
    for sep in SEPS:
        for k in PARTS:
            out.append((f"s.split({sep!r})[{k}]", lambda s, sep=sep, k=k: s.split(sep)[k]))
    out += [
        ("''.join(c for c in s if c.isdigit())", lambda s: "".join(c for c in s if c.isdigit())),
        ("''.join(c for c in s if c.isalpha())", lambda s: "".join(c for c in s if c.isalpha())),
        ("' '.join(s.split())", lambda s: " ".join(s.split())),
    ]
    for a, b in ((" ", "-"), (" ", "_"), ("-", " "), ("_", " "), (",", ""), ("$", ""), ("-", ""), (".", "")):
        out.append((f"s.replace({a!r}, {b!r})", lambda s, a=a, b=b: s.replace(a, b)))
    return out


SLICES = [("", None), ("[:1]", slice(0, 1)), ("[:2]", slice(0, 2)), ("[:3]", slice(0, 3)), ("[-1:]", slice(-1, None)),
          ("[-2:]", slice(-2, None)), ("[-3:]", slice(-3, None)), ("[-4:]", slice(-4, None)),
          ("[1:]", slice(1, None)), ("[:-1]", slice(None, -1))]
SPANS = [(f"[{a}:{b}]", slice(a, b)) for a in range(0, 10) for b in range(a + 1, 11)]
CASES = ["", "lower", "upper", "title", "capitalize"]


def _atom(fcode, ffn, scode, sl, case):
    code = f"({fcode}){scode}" if scode else fcode
    if case:
        code = f"({code}).{case}()"

    def fn(s):
        v = ffn(s)
        if sl is not None:
            v = v[sl]
        return getattr(v, case)() if case else v
    return code, fn


def _atoms():
    general = [_atom(fc, ff, sc, sl, c) for fc, ff in _fields() for sc, sl in SLICES for c in CASES]
    fixed = [_atom("s", lambda s: s, sc, sl, c) for sc, sl in SPANS for c in CASES]  # least general: last
    return general + fixed


ATOMS = _atoms()


def synthesize(examples, max_parts: int = 6, max_const: int = 15, max_states: int = 20000):
    """Python source of the simplest consistent program, the number of atom checks spent, or (None, work)."""
    ins = [x for x, _ in examples]
    outs = [y for _, y in examples]
    n = len(examples)
    work = 0
    seen_values, atoms = set(), []
    for code, fn in ATOMS:  # evaluate every atom on every example input, keep one per distinct behaviour
        vals = []
        for x in ins:
            work += 1
            try:
                v = fn(x)
            except Exception:
                v = None
            if not v:
                break
            vals.append(v)
        else:
            key = tuple(vals)
            if key not in seen_values:
                seen_values.add(key)
                atoms.append((code, vals))
    start, goal = (0,) * n, tuple(len(o) for o in outs)
    tie = itertools.count()
    heap = [(0, 0, next(tie), start, ())]
    visited = {start}
    expanded = 0
    while heap and expanded < max_states:
        n_parts, n_const, _, state, parts = heapq.heappop(heap)
        if state == goal:
            return "def f(s):\n    return " + " + ".join(parts), work
        if n_parts >= max_parts:
            continue
        expanded += 1
        for code, vals in atoms:
            work += 1
            if all(outs[k].startswith(vals[k], state[k]) for k in range(n)):
                nxt = tuple(state[k] + len(vals[k]) for k in range(n))
                if nxt not in visited:
                    visited.add(nxt)
                    heapq.heappush(heap, (n_parts + 1, n_const, next(tie), nxt, parts + (code,)))
        rest = outs[0][state[0]:]
        for L in range(1, min(max_const, len(rest)) + 1):
            c = rest[:L]
            work += 1
            if not all(outs[k].startswith(c, state[k]) for k in range(n)):
                break
            nxt = tuple(state[k] + L for k in range(n))
            if nxt not in visited:
                visited.add(nxt)
                heapq.heappush(heap, (n_parts + 1, n_const + L, next(tie), nxt, parts + (repr(c),)))
    return None, work
