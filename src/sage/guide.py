"""The learned guide: a small linear softmax model from task features to tokens.

Given a task's features (src/sage/features.py), the guide returns a
probability for every token (base instruction or library entry). Search turns
these into costs, -log p, so likely tokens are tried first. Probabilities are
mixed with a small uniform floor so that no token is ever unreachable.

Training uses soft labels: the share of each token in a solved or dreamed
program. It is full-batch gradient descent with Adam, warm-started from the
previous guide by token and feature *name*, so the vocabulary can grow and
shrink between library versions.

Arithmetic is counted in multiply-adds as a sparse implementation would do
it: 2 * nnz(X) * T per training iteration (forward and gradient) and
nnz(x) * T to score one task.
"""

from __future__ import annotations

import math

import numpy as np


class Guide:
    def __init__(self, tokens: list[str], features: list[str]):
        self.tokens = list(tokens)
        self.features = list(features)
        self.t_index = {t: i for i, t in enumerate(self.tokens)}
        self.f_index = {f: i for i, f in enumerate(self.features)}
        self.W = np.zeros((len(self.features), len(self.tokens)))
        self.b = np.zeros(len(self.tokens))
        self.prior = np.full(len(self.tokens), 1.0 / max(1, len(self.tokens)))  # overall token frequency
        self.beta = 0.0  # weight of the prior in the final distribution
        self.floor = 0.02  # weight of the uniform floor
        self.madds = 0  # multiply-adds spent training this guide (cumulative over warm starts)

    # -- construction -----------------------------------------------------------------
    @classmethod
    def build(cls, tokens: list[str], examples, min_count: int = 2, previous: "Guide | None" = None) -> "Guide":
        counts: dict[str, int] = {}
        for feats, _ in examples:
            for f in feats:
                counts[f] = counts.get(f, 0) + 1
        features = sorted(f for f, c in counts.items() if c >= min_count or f == "bias")
        g = cls(tokens, features)
        if previous is not None:
            rows = [(i, previous.f_index[f]) for i, f in enumerate(features) if f in previous.f_index]
            cols = [(j, previous.t_index[t]) for j, t in enumerate(tokens) if t in previous.t_index]
            if rows and cols:
                ri, rp = zip(*rows)
                ci, cp = zip(*cols)
                g.W[np.ix_(ri, ci)] = previous.W[np.ix_(rp, cp)]
                g.b[list(ci)] = previous.b[list(cp)]
        return g

    def _matrix(self, examples):
        X = np.zeros((len(examples), len(self.features)))
        Y = np.zeros((len(examples), len(self.tokens)))
        nnz = 0
        for r, (feats, label) in enumerate(examples):
            for f, v in feats.items():
                c = self.f_index.get(f)
                if c is not None:
                    X[r, c] = v
                    nnz += 1
            total = sum(label.values())
            for t, v in label.items():
                if t in self.t_index:
                    Y[r, self.t_index[t]] = v / total
        return X, Y, nnz

    # -- training ---------------------------------------------------------------------
    def fit(self, examples, iters: int = 60, lr: float = 0.05, l2: float = 1e-3) -> int:
        """Full-batch Adam on soft-label cross-entropy. Returns multiply-adds spent."""
        X, Y, nnz = self._matrix(examples)
        n, T = Y.shape
        mW = np.zeros_like(self.W)
        vW = np.zeros_like(self.W)
        mb = np.zeros_like(self.b)
        vb = np.zeros_like(self.b)
        b1, b2, eps = 0.9, 0.999, 1e-8
        for step in range(1, iters + 1):
            Z = X @ self.W + self.b
            Z -= Z.max(axis=1, keepdims=True)
            P = np.exp(Z)
            P /= P.sum(axis=1, keepdims=True)
            G = (P - Y) / n
            gW = X.T @ G + l2 * self.W
            gb = G.sum(axis=0)
            mW = b1 * mW + (1 - b1) * gW
            vW = b2 * vW + (1 - b2) * gW * gW
            mb = b1 * mb + (1 - b1) * gb
            vb = b2 * vb + (1 - b2) * gb * gb
            corr1, corr2 = 1 - b1 ** step, 1 - b2 ** step
            self.W -= lr * (mW / corr1) / (np.sqrt(vW / corr2) + eps)
            self.b -= lr * (mb / corr1) / (np.sqrt(vb / corr2) + eps)
        spent = iters * (2 * nnz * T + 4 * n * T)
        self.madds += spent
        return spent

    def fit_online(self, examples, epochs: int = 3, lr: float = 0.3, l2: float = 1e-4, seed: str = "sgd") -> int:
        """Online Adagrad on soft-label cross-entropy, one example at a time.

        Counted as 4 * nnz(x) * T multiply-adds per example (score, gradient,
        accumulator, update) plus O(T) for the softmax and bias.
        """
        import random as _random

        rows = []
        for feats, label in examples:
            cols = [self.f_index[f] for f in feats if f in self.f_index]
            vals = np.array([feats[f] for f in feats if f in self.f_index])
            y = np.zeros(len(self.tokens))
            total = sum(label.values())
            for t, v in label.items():
                if t in self.t_index:
                    y[self.t_index[t]] = v / total
            rows.append((np.array(cols, dtype=int), vals, y))
        if rows:
            freq = sum(y for _, _, y in rows) + 0.5 / len(self.tokens)
            self.prior = freq / freq.sum()
        accW = np.full_like(self.W, 1e-6)
        accb = np.full_like(self.b, 1e-6)
        rng = _random.Random(seed)
        T = len(self.tokens)
        spent = 0
        for _ in range(epochs):
            order = list(range(len(rows)))
            rng.shuffle(order)
            for r in order:
                cols, vals, y = rows[r]
                z = self.b + vals @ self.W[cols]
                z -= z.max()
                pr = np.exp(z)
                pr /= pr.sum()
                g = pr - y
                gW = np.outer(vals, g) + l2 * self.W[cols]
                accW[cols] += gW * gW
                self.W[cols] -= lr * gW / np.sqrt(accW[cols])
                accb += g * g
                self.b -= lr * g / np.sqrt(accb)
                spent += 4 * len(cols) * T + 6 * T
        self.madds += spent
        return spent

    # -- use --------------------------------------------------------------------------
    def probs(self, feats: dict[str, float]) -> tuple[np.ndarray, int]:
        """The guide's final distribution over self.tokens and the multiply-adds spent.

        The model's softmax is mixed with the overall token frequency (weight
        `beta`, an empirical prior that keeps frequently useful tokens in
        reach when the task evidence is weak) and a uniform floor.
        """
        z = self.b.copy()
        nnz = 0
        for f, v in feats.items():
            c = self.f_index.get(f)
            if c is not None:
                z += v * self.W[c]
                nnz += 1
        z -= z.max()
        p = np.exp(z)
        p /= p.sum()
        T = len(self.tokens)
        p = (1 - self.beta - self.floor) * p + self.beta * self.prior + self.floor / T
        return p, nnz * T + 6 * T

    def costs(self, feats: dict[str, float], order: list[str]) -> tuple[list[float], int]:
        """-log p for the tokens named in `order` (the token list the search uses)."""
        p, madds = self.probs(feats)
        tiny = self.floor / max(1, len(self.tokens))
        return [-math.log(p[self.t_index[n]] if n in self.t_index else tiny) for n in order], madds

    # -- persistence ------------------------------------------------------------------
    def to_json(self) -> dict:
        return {"tokens": self.tokens, "features": self.features, "W": self.W.round(6).tolist(),
                "b": self.b.round(6).tolist(), "prior": self.prior.round(8).tolist(), "beta": self.beta,
                "floor": self.floor, "madds": self.madds}

    @classmethod
    def from_json(cls, d: dict) -> "Guide":
        g = cls(d["tokens"], d["features"])
        g.W = np.array(d["W"], dtype=float).reshape(len(g.features), len(g.tokens))
        g.b = np.array(d["b"], dtype=float)
        g.prior = np.array(d["prior"], dtype=float)
        g.beta, g.floor = d["beta"], d["floor"]
        g.madds = d.get("madds", 0)
        return g


def percentile_ranks(p: np.ndarray) -> np.ndarray:
    """Rank of each entry divided by the number of entries (0 = most probable), ties averaged."""
    T = len(p)
    order = np.argsort(-p, kind="stable")
    ranks = np.empty(T)
    i = 0
    sorted_p = p[order]
    while i < T:
        j = i
        while j + 1 < T and sorted_p[j + 1] == sorted_p[i]:
            j += 1
        ranks[order[i:j + 1]] = (i + j) / 2
        i = j + 1
    return ranks / T
