"""A verified-program memory for stage 1a.

Every accepted function is stored with a trust count (requests it has
answered). A new request is checked against stored functions in order of
trust, then most recent use; the first that reproduces all of the request's
examples answers it locally. Identical code is merged. The memory itself
never calls a model.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .sandbox import compile_function, reproduces


@dataclass
class Stored:
    code: str
    fn: object
    trust: int = 1
    last_used: int = 0


@dataclass
class ProgramMemory:
    items: list = field(default_factory=list)
    by_code: dict = field(default_factory=dict)
    checks: int = 0  # functions verified so far, for reporting

    def lookup(self, examples) -> Stored | None:
        for s in sorted(self.items, key=lambda s: (-s.trust, -s.last_used)):
            self.checks += 1
            if reproduces(s.fn, examples):
                return s
        return None

    def store(self, code: str, clock: int) -> Stored | None:
        key = code.strip()
        s = self.by_code.get(key)
        if s is not None:
            s.trust += 1
            s.last_used = clock
            return s
        fn = compile_function(code)
        if fn is None:
            return None
        s = Stored(key, fn, 1, clock)
        self.by_code[key] = s
        self.items.append(s)
        return s

    def __len__(self) -> int:
        return len(self.items)
