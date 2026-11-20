"""MemoryStore — persistent JSON-backed collection of MemoryRecords.

This is seam #1 of the memory layer's interface (the write boundary). In
Stage 3 the defense team can subclass or wrap ``MemoryStore`` to validate
records on write (``add``) without changing how the rest of the system calls it.
"""

from __future__ import annotations

import json
from pathlib import Path

from .schema import MemoryRecord


class MemoryStore:
    """A collection of memory records persisted to a single JSON file.

    Parameters
    ----------
    path:
        Where the JSON lives. The file is created lazily on first ``save``.
        If it already exists it is loaded on construction.
    autosave:
        When True (default), every mutating call writes through to disk.
    """

    def __init__(self, path: str | Path, autosave: bool = True) -> None:
        self.path = Path(path)
        self.autosave = autosave
        self._records: dict[str, MemoryRecord] = {}
        if self.path.exists():
            self.load()

    # ------------------------------------------------------------------ #
    # mutation
    # ------------------------------------------------------------------ #
    def add(self, record: MemoryRecord) -> str:
        """Insert (or replace, by id) a record. Returns its id.

        Defense hook: override to reject/sanitize records before storing.
        """
        self._records[record.record_id] = record
        if self.autosave:
            self.save()
        return record.record_id

    def delete(self, record_id: str) -> bool:
        """Remove a record by id. Returns True if something was removed."""
        existed = self._records.pop(record_id, None) is not None
        if existed and self.autosave:
            self.save()
        return existed

    def clear(self) -> None:
        """Drop all records."""
        self._records.clear()
        if self.autosave:
            self.save()

    # ------------------------------------------------------------------ #
    # access
    # ------------------------------------------------------------------ #
    def get(self, record_id: str) -> MemoryRecord | None:
        return self._records.get(record_id)

    def all(self) -> list[MemoryRecord]:
        """All records, insertion order."""
        return list(self._records.values())

    def __len__(self) -> int:
        return len(self._records)

    def __iter__(self):
        return iter(self._records.values())

    # ------------------------------------------------------------------ #
    # persistence
    # ------------------------------------------------------------------ #
    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"records": [r.to_dict() for r in self._records.values()]}
        # Write atomically so a crash mid-write can't corrupt the store.
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
        tmp.replace(self.path)

    def load(self) -> None:
        payload = json.loads(self.path.read_text())
        self._records = {}
        for d in payload.get("records", []):
            rec = MemoryRecord.from_dict(d)
            self._records[rec.record_id] = rec
