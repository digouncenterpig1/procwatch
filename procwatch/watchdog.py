"""Watchdog timer that triggers a callback if a process hasn't checked in within a deadline."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, Optional


@dataclass
class WatchdogEntry:
    deadline: float  # seconds
    callback: Callable[[str], None]
    last_seen: float = field(default_factory=time.monotonic)
    fired: bool = False


class Watchdog:
    """Monitors per-process heartbeats and fires callbacks on timeout."""

    def __init__(self, interval: float = 1.0) -> None:
        self._interval = interval
        self._entries: Dict[str, WatchdogEntry] = {}
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def register(self, name: str, deadline: float, callback: Callable[[str], None]) -> None:
        """Register a process with a timeout deadline in seconds."""
        with self._lock:
            self._entries[name] = WatchdogEntry(deadline=deadline, callback=callback)

    def unregister(self, name: str) -> None:
        """Remove a process from watchdog monitoring."""
        with self._lock:
            self._entries.pop(name, None)

    def heartbeat(self, name: str) -> None:
        """Record a heartbeat for the named process, resetting its timer."""
        with self._lock:
            entry = self._entries.get(name)
            if entry is not None:
                entry.last_seen = time.monotonic()
                entry.fired = False

    def start(self) -> None:
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="watchdog")
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=self._interval + 1)
            self._thread = None

    def _run(self) -> None:
        while not self._stop_event.wait(timeout=self._interval):
            now = time.monotonic()
            with self._lock:
                entries = list(self._entries.items())
            for name, entry in entries:
                if not entry.fired and (now - entry.last_seen) >= entry.deadline:
                    entry.fired = True
                    try:
                        entry.callback(name)
                    except Exception:  # noqa: BLE001
                        pass
