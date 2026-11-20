"""Retriever — rank stored memories against a query intent (top-k).

This is seam #2 of the interface (the retrieval boundary). In Stage 3 the
defense team can wrap ``retrieve`` to filter, re-rank, or drop suspicious
records before they ever reach the injector.
"""

from __future__ import annotations

from dataclasses import dataclass

from .embedder import Embedder, TfidfEmbedder, cosine
from .schema import MemoryRecord
from .store import MemoryStore


def record_document(record: MemoryRecord) -> str:
    """The text a record is embedded/matched on.

    We embed the *whole experience* — the task intent plus the trajectory
    content — not the intent alone. This is faithful to trajectory memory:
    a Task-A record ("read the blog") becomes relevant to a Task-B shopping
    intent through its *content* (which mentions lanterns, camping, the
    sponsored product), not through its intent string, which shares little
    vocabulary with the later task. Retrieving on intent alone was shown by
    the self-test to miss the poison entirely.
    """
    return f"{record.task_intent}\n{record.trajectory_text}"


@dataclass
class RetrievalResult:
    record: MemoryRecord
    score: float


class Retriever:
    """Embedding + top-k cosine retrieval over a MemoryStore.

    Parameters
    ----------
    store:
        The memory to search.
    embedder:
        Any ``Embedder``. Defaults to the zero-dependency ``TfidfEmbedder``.
    top_k:
        Default number of records to return.
    min_score:
        Records scoring below this are dropped (0.0 keeps everything with any
        overlap). Lets the honest/clean condition retrieve nothing relevant.
    """

    def __init__(
        self,
        store: MemoryStore,
        embedder: Embedder | None = None,
        top_k: int = 1,
        min_score: float = 0.0,
    ) -> None:
        self.store = store
        self.embedder = embedder or TfidfEmbedder()
        self.top_k = top_k
        self.min_score = min_score

    def _ensure_fit(self, records: list[MemoryRecord]) -> None:
        """Fit the embedder on the corpus of stored intents (idempotent-ish).

        For corpus-based embedders (TF-IDF) the vocabulary must cover the
        stored documents. We refit on every retrieve for correctness; the
        store is small, so cost is negligible.
        """
        corpus = [record_document(r) for r in records]
        if corpus:
            self.embedder.fit(corpus)

    def retrieve(
        self, query_intent: str, top_k: int | None = None
    ) -> list[RetrievalResult]:
        """Return the top-k records most similar to ``query_intent``.

        Defense hook: override/wrap to sanitize or drop records here.
        """
        k = self.top_k if top_k is None else top_k
        records = self.store.all()
        if not records:
            return []

        self._ensure_fit(records)
        documents = [record_document(r) for r in records]
        record_vecs = self.embedder.encode(documents)
        query_vec = self.embedder.encode([query_intent])[0]

        scored = [
            RetrievalResult(rec, cosine(query_vec, rv))
            for rec, rv in zip(records, record_vecs)
        ]
        scored = [s for s in scored if s.score > self.min_score]
        scored.sort(key=lambda s: s.score, reverse=True)
        return scored[:k]
