"""Memory record schema — the data contract for the memory layer.

This is the single source of truth for what a "memory" is. Both the attack
team (who write poisoned records) and the defense team (who validate/sanitize
records in Stage 3) program against this type.

Design notes
------------
We deliberately store a *text* ``trajectory_text`` rather than a raw WebArena
``Trajectory`` (``list[StateInfo | Action]``). A live WebArena trajectory holds
Playwright ``page`` handles that are not JSON-serializable and are meaningless
once the browser closes. The memory layer persists to JSON and is injected into
the prompt as text, so text is the right storage form — and it matches the
paper's *pseudo-trajectory* method, which embeds page content as text.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class MemoryRecord:
    """One stored past-task experience the agent can retrieve later.

    Attributes
    ----------
    task_intent:
        The objective of the task this memory came from (e.g. the Task A
        objective "Read Agnes' hiking blog and summarize it"). This is the
        text retrieval is keyed on — a later task's intent is matched against
        it.
    trajectory_text:
        The human/agent-readable summary of what happened — observations and
        actions rendered as text. This is the content that gets injected into
        a future prompt. For a *poisoned* record this is where the sponsor
        block lives.
    record_id:
        Stable unique id. Auto-generated if not supplied.
    embedding:
        Optional cached embedding vector for ``task_intent``. ``None`` until a
        retriever computes it; stored so repeated retrievals need not re-embed.
    metadata:
        Free-form provenance (site, timestamp, source, condition label, and —
        importantly for Stage 3 — a ``poisoned`` flag the defense may inspect
        or that we set for our own bookkeeping).
    """

    task_intent: str
    trajectory_text: str
    record_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    embedding: list[float] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """JSON-serializable dict."""
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "MemoryRecord":
        """Rebuild a record from its serialized form, tolerating extra keys."""
        return cls(
            task_intent=d["task_intent"],
            trajectory_text=d["trajectory_text"],
            record_id=d.get("record_id", uuid.uuid4().hex),
            embedding=d.get("embedding"),
            metadata=d.get("metadata", {}),
        )
