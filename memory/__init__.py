"""Memory layer for the eTAMP attack replication (attack team, Stage 2 / M2.1).

A minimal, interface-first agent memory: store past-task trajectories, retrieve
the top-k relevant ones for a new task's intent, and inject them into the
prompt. This is the exact component the defense team hardens in Stage 3, so the
public API below is the inter-team contract — keep it stable.

Three seams, each a defense hook:
    * MemoryStore.add        — the write boundary
    * Retriever.retrieve     — the retrieval boundary
    * injector.inject        — the injection boundary (into the prompt)

Typical use (exploitation phase):
    >>> from memory import MemoryStore, Retriever, inject
    >>> store = MemoryStore("memory/store.json")
    >>> retr = Retriever(store, top_k=1)
    >>> hits = retr.retrieve("buy a lantern for camping")
    >>> prompt = inject(base_prompt, hits)
"""

from __future__ import annotations

from .schema import MemoryRecord
from .store import MemoryStore
from .embedder import Embedder, TfidfEmbedder, cosine
from .retriever import Retriever, RetrievalResult
from .injector import inject, format_memory_block

__all__ = [
    "MemoryRecord",
    "MemoryStore",
    "Embedder",
    "TfidfEmbedder",
    "cosine",
    "Retriever",
    "RetrievalResult",
    "inject",
    "format_memory_block",
]
