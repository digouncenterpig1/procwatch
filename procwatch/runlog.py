"""Persistent run log: records process lifecycle events to a JSONL file."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Optional


@dataclass
class RunEntry:
    process: str
    event: str  # 'start' | 'stop' | 'crash' | 'restart'
    timestamp: float
    pid: Optional[int] = None
    exit_code: Optional[int] = None
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "process": self.process,
            "event": self.event,
            "timestamp": self.timestamp,
            "pid": self.pid,
            "exit_code": self.exit_code,
            **self.extra,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RunEntry":
        known = {"process", "event", "timestamp", "pid", "exit_code"}
        extra = {k: v for k, v in data.items() if k not in known}
        return cls(
            process=data["process"],
            event=data["event"],
            timestamp=data["timestamp"],
            pid=data.get("pid"),
            exit_code=data.get("exit_code"),
            extra=extra,
        )


class RunLog:
    """Append-only JSONL run log with optional line-limit rotation."""

    def __init__(self, path: str | Path, max_lines: int = 10_000) -> None:
        self._path = Path(path)
        self._max_lines = max_lines
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, entry: RunEntry) -> None:
        with self._path.open("a") as fh:
            fh.write(json.dumps(entry.to_dict()) + "\n")
        self._maybe_rotate()

    def record(self, process: str, event: str, **kwargs) -> None:
        ts = datetime.now(timezone.utc).timestamp()
        entry = RunEntry(process=process, event=event, timestamp=ts, **kwargs)
        self.append(entry)

    def read(self) -> list[RunEntry]:
        if not self._path.exists():
            return []
        entries = []
        with self._path.open() as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        entries.append(RunEntry.from_dict(json.loads(line)))
                    except (json.JSONDecodeError, KeyError):
                        pass
        return entries

    def iter_for(self, process: str) -> Iterator[RunEntry]:
        for entry in self.read():
            if entry.process == process:
                yield entry

    def _maybe_rotate(self) -> None:
        if not self._path.exists():
            return
        lines = self._path.read_text().splitlines()
        if len(lines) > self._max_lines:
            keep = lines[-self._max_lines :]
            self._path.write_text("\n".join(keep) + "\n")
