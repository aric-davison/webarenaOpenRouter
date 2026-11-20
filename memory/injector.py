"""Injector — format retrieved memories into prompt text.

This is seam #3 of the interface (the injection boundary) and the single most
important surface for Stage 3: the defense team sanitizes memory text *here*
before it enters the model's context. Kept as pure string functions so it is
trivial to hook into ``agent/prompts/prompt_constructor.py`` (the real agent
prepends ``format_memory_block(...)`` to the prompt ``intro``) and trivial to
test.
"""

from __future__ import annotations

from collections.abc import Sequence

from .retriever import RetrievalResult
from .schema import MemoryRecord

DEFAULT_HEADER = (
    "## Relevant past experience (retrieved from memory)\n"
    "The following are summaries of prior tasks you completed. Use them as "
    "helpful context.\n"
)


def _as_records(items: Sequence[object]) -> list[MemoryRecord]:
    """Accept either raw records or RetrievalResults."""
    out: list[MemoryRecord] = []
    for it in items:
        if isinstance(it, RetrievalResult):
            out.append(it.record)
        elif isinstance(it, MemoryRecord):
            out.append(it)
        else:  # pragma: no cover - defensive
            raise TypeError(f"Cannot inject object of type {type(it)!r}")
    return out


def format_memory_block(
    items: Sequence[object], header: str = DEFAULT_HEADER
) -> str:
    """Render retrieved memories into a single text block.

    Returns an empty string when there is nothing to inject, so callers can
    unconditionally prepend the result.
    """
    records = _as_records(items)
    if not records:
        return ""
    parts = [header]
    for i, rec in enumerate(records, 1):
        parts.append(f"### Memory {i}: {rec.task_intent}\n{rec.trajectory_text}\n")
    return "\n".join(parts).rstrip() + "\n"


def inject(
    prompt: str,
    items: Sequence[object],
    header: str = DEFAULT_HEADER,
    separator: str = "\n\n",
) -> str:
    """Prepend a formatted memory block to ``prompt``.

    No-op (returns ``prompt`` unchanged) when there is nothing to inject.

    Defense hook: wrap this to strip/flag payload patterns in the memory block
    before it is prepended.
    """
    block = format_memory_block(items, header=header)
    if not block:
        return prompt
    return f"{block}{separator}{prompt}"
