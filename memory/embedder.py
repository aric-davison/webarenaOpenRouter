"""Embedders — turn text into vectors for similarity retrieval.

The ``Embedder`` protocol is the swap point. The default
``TfidfEmbedder`` is **zero-dependency and uses no API quota** (important on
the free tier — open item 9.3 in the attack plan). A heavier, higher-quality
local option (sentence-transformers) can be dropped in later without touching
the retriever, because both satisfy the same protocol.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Iterable, Protocol, runtime_checkable


@runtime_checkable
class Embedder(Protocol):
    """Anything that can turn a list of strings into fixed-meaning vectors.

    ``fit`` is optional (corpus-based embedders like TF-IDF use it; a neural
    embedder can make it a no-op). ``encode`` must be callable after ``fit``.
    """

    def fit(self, corpus: Iterable[str]) -> "Embedder": ...

    def encode(self, texts: list[str]) -> list[list[float]]: ...


_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


class TfidfEmbedder:
    """A tiny, dependency-free TF-IDF embedder.

    Good enough to verify retrieval end-to-end and to surface a poisoned
    record whose intent overlaps the query intent. Vocabulary is learned from
    the corpus via ``fit``; unknown query tokens are simply ignored.
    """

    def __init__(self) -> None:
        self._vocab: dict[str, int] = {}
        self._idf: list[float] = []
        self._fitted = False

    def fit(self, corpus: Iterable[str]) -> "TfidfEmbedder":
        docs = [_tokenize(t) for t in corpus]
        self._vocab = {}
        for doc in docs:
            for tok in doc:
                if tok not in self._vocab:
                    self._vocab[tok] = len(self._vocab)
        n_docs = max(len(docs), 1)
        df = [0] * len(self._vocab)
        for doc in docs:
            for tok in set(doc):
                df[self._vocab[tok]] += 1
        # smoothed idf
        self._idf = [math.log((1 + n_docs) / (1 + d)) + 1.0 for d in df]
        self._fitted = True
        return self

    def encode(self, texts: list[str]) -> list[list[float]]:
        if not self._fitted:
            # Degenerate but safe: fit on the texts themselves.
            self.fit(texts)
        vectors: list[list[float]] = []
        dim = len(self._vocab)
        for text in texts:
            vec = [0.0] * dim
            counts = Counter(_tokenize(text))
            if counts:
                max_c = max(counts.values())
                for tok, c in counts.items():
                    idx = self._vocab.get(tok)
                    if idx is not None:
                        tf = c / max_c
                        vec[idx] = tf * self._idf[idx]
            vectors.append(vec)
        return vectors


def cosine(a: list[float], b: list[float]) -> float:
    """Cosine similarity, safe on zero vectors (returns 0.0)."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)
