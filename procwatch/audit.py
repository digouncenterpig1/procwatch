"""Audit log — records operator actions (start, stop, reload, kill) with timestamps."""
from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional


@dataclass
class AuditEntry:
    action: str          # e.g. "start", "stop", "reload", "kill"
    process: str         # process name
    actor: str           # "operator" | "supervisor" | "signal"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    detail: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "AuditEntry":
        return AuditEntry(**d)


class AuditLog:
    """Append-only JSONL audit log with an optional in-memory tail."""

    def __init__(self, path: str | Path, maxlen: int = 500) -> None:
        self._path = Path(path)
        self._maxlen = maxlen
        self._lock = threading.Lock()
        self._tail: List[AuditEntry] = []

    # ------------------------------------------------------------------
    def record(self, action: str, process: str, actor: str = "operator",
               detail: Optional[str] = None) -> AuditEntry:
        entry = AuditEntry(action=action, process=process, actor=actor, detail=detail)
        with self._lock:
            self._tail.append(entry)
            if len(self._tail) > self._maxlen:
                self._tail.pop(0)
            self._append(entry)
        return entry

    def tail(self, n: int = 50) -> List[AuditEntry]:
        with self._lock:
            return list(self._tail[-n:])

    def read_all(self) -> List[AuditEntry]:
        if not self._path.exists():
            return []
        entries: List[AuditEntry] = []
        with self._path.open() as fh:
            for line in fh:
                line = line.strip()
                if line:
                    entries.append(AuditEntry.from_dict(json.loads(line)))
        return entries

    # ------------------------------------------------------------------
    def _append(self, entry: AuditEntry) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a") as fh:
            fh.write(json.dumps(entry.to_dict()) + "\n")
