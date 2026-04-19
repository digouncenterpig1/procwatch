"""In-memory event log — keeps a bounded history of process lifecycle events."""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Iterator, List, Optional


@dataclass
class Event:
    name: str          # process name
    kind: str          # start | stop | crash | throttle
    ts: float = field(default_factory=time.time)
    detail: Optional[str] = None

    def to_dict(self) -> dict:
        return {"name": self.name, "kind": self.kind, "ts": self.ts, "detail": self.detail}


class EventLog:
    def __init__(self, maxlen: int = 500) -> None:
        self._log: Deque[Event] = deque(maxlen=maxlen)

    def record(self, name: str, kind: str, detail: Optional[str] = None) -> Event:
        ev = Event(name=name, kind=kind, detail=detail)
        self._log.append(ev)
        return ev

    def all(self) -> List[Event]:
        return list(self._log)

    def for_process(self, name: str) -> List[Event]:
        return [e for e in self._log if e.name == name]

    def since(self, ts: float) -> List[Event]:
        return [e for e in self._log if e.ts >= ts]

    def clear(self) -> None:
        self._log.clear()

    def __len__(self) -> int:
        return len(self._log)

    def __iter__(self) -> Iterator[Event]:
        return iter(self._log)


# Module-level default log shared across the application
_default: EventLog = EventLog()


def get_default() -> EventLog:
    return _default


def reset_default() -> None:
    """Reset the default log (useful in tests)."""
    global _default
    _default = EventLog()
