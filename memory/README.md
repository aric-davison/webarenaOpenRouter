# Memory layer (M2.1) — interface contract

Minimal agent memory for the eTAMP replication: **store** past-task
trajectories, **retrieve** the top-k relevant ones for a new task, and
**inject** them into the agent's prompt.

This module is the component the **defense team hardens in Stage 3**. The public
API below is the contract between our teams — treat it as stable. Internals
(the TF-IDF default embedder, the JSON file format) may change; the signatures
here should not without a heads-up.

## Install / run

No third-party dependencies. From the repo root:

```bash
python -m memory.selftest
```

verifies store + retrieval + injection in isolation (no WebArena, no API, no
browser).

## The three seams (defense hooks)

The attack flows through exactly three boundaries. Each is where a defense can
intervene without touching the rest of the system:

| Seam | Call | What a defense does here |
|------|------|--------------------------|
| **Write** | `MemoryStore.add(record)` | validate / reject / sanitize a record before it is stored |
| **Retrieve** | `Retriever.retrieve(query_intent)` | filter, re-rank, or drop suspicious records before they surface |
| **Inject** | `injector.inject(prompt, records)` | strip / flag payload patterns in the memory text before it enters the prompt |

## Data model — `MemoryRecord` (`memory/schema.py`)

```python
@dataclass
class MemoryRecord:
    task_intent: str            # objective of the task this memory came from (retrieval key)
    trajectory_text: str        # readable summary of obs+actions; this is what gets injected
    record_id: str              # stable unique id (auto)
    embedding: list[float] | None
    metadata: dict              # provenance: {"site": ..., "poisoned": bool, "condition": ...}
```

We store **text**, not a raw WebArena `Trajectory` — a live trajectory holds
Playwright `page` handles that are not JSON-serializable. Text is also the form
the paper's *pseudo-trajectory* method uses: the sponsor block lives in
`trajectory_text` of a poisoned record.

## API

```python
from memory import MemoryStore, Retriever, MemoryRecord, inject

# store (JSON-backed, autosaves)
store = MemoryStore("memory/store.json")
store.add(MemoryRecord(task_intent=..., trajectory_text=...))
store.all(); store.get(id); store.delete(id); store.clear()

# retrieve (top-k cosine; zero-API TF-IDF embedder by default)
retr = Retriever(store, top_k=1, min_score=0.0)   # pass embedder=... to swap
hits = retr.retrieve("buy a solar lantern for camping")  # -> [RetrievalResult(record, score)]

# inject into a prompt (no-op when hits is empty)
prompt = inject(base_prompt, hits)
```

**Retrieval matches on the whole experience** — `task_intent` **+**
`trajectory_text` (see `retriever.record_document`) — not the intent alone. A
Task-A record ("read the blog") becomes relevant to a Task-B shopping intent
through its *content*, which is how the poison surfaces. Retrieving on intent
alone misses it (the self-test demonstrates this).

### Swapping the embedder

`Retriever` takes any object satisfying the `Embedder` protocol
(`fit(corpus)`, `encode(texts) -> vectors`). The default `TfidfEmbedder` is
dependency-free and uses **no API quota** (free-tier constraint). A
sentence-transformers embedder can be dropped in later with no other changes.

## Integration point (for M2.2 / M2.3, not done here)

The real agent builds its prompt in
`agent/prompts/prompt_constructor.py::construct(trajectory, intent, meta_data)`.
The injection hook is: retrieve on `intent`, then prepend
`format_memory_block(hits)` to the prompt `intro`. M2.1 deliberately stops at
the documented interface so the defense team can design in parallel.

## Status

- [x] store / retriever / injector implemented
- [x] isolated self-test passing (`python -m memory.selftest`)
- [x] interface documented (this file) — **ready to share with the defense team**
- [ ] wired into `prompt_constructor` (M2.2 / M2.3)
