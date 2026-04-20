"""Persist and restore supervisor state across restarts."""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional

log = logging.getLogger(__name__)


@dataclass
class ProcessState:
    name: str
    restart_count: int
    last_exit_code: Optional[int]
    last_started_at: Optional[float]

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "ProcessState":
        return cls(
            name=d["name"],
            restart_count=d.get("restart_count", 0),
            last_exit_code=d.get("last_exit_code"),
            last_started_at=d.get("last_started_at"),
        )


class StateFile:
    """Read/write a JSON state file for persisting process metadata."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    def save(self, states: List[ProcessState]) -> None:
        """Atomically write state to disk."""
        tmp = self._path.with_suffix(".tmp")
        payload = {
            "saved_at": time.time(),
            "processes": [s.to_dict() for s in states],
        }
        try:
            tmp.write_text(json.dumps(payload, indent=2))
            tmp.replace(self._path)
            log.debug("state saved to %s (%d entries)", self._path, len(states))
        except OSError as exc:
            log.warning("could not save state file: %s", exc)
            tmp.unlink(missing_ok=True)

    def load(self) -> Dict[str, ProcessState]:
        """Return a mapping of process name -> ProcessState, or empty dict."""
        if not self._path.exists():
            return {}
        try:
            data = json.loads(self._path.read_text())
            result = {}
            for entry in data.get("processes", []):
                ps = ProcessState.from_dict(entry)
                result[ps.name] = ps
            log.debug("loaded %d state entries from %s", len(result), self._path)
            return result
        except (OSError, json.JSONDecodeError, KeyError) as exc:
            log.warning("could not load state file: %s", exc)
            return {}

    def remove(self) -> None:
        """Delete the state file if it exists."""
        self._path.unlink(missing_ok=True)
