"""Periodic snapshot watcher — captures supervisor state on an interval."""
from __future__ import annotations

import logging
import threading
import time
from typing import Callable, List, Optional

from procwatch.snapshot import SupervisorSnapshot, take_snapshot

log = logging.getLogger(__name__)

SnapshotCallback = Callable[[SupervisorSnapshot], None]


class SnapshotWatcher:
    """Runs a background thread that periodically snapshots the supervisor."""

    def __init__(self, supervisor, interval: float = 5.0):
        self._supervisor = supervisor
        self._interval = interval
        self._callbacks: List[SnapshotCallback] = []
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self.history: List[SupervisorSnapshot] = []
        self._history_limit = 60

    def add_callback(self, cb: SnapshotCallback) -> None:
        self._callbacks.append(cb)

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="snapshot-watcher")
        self._thread.start()
        log.debug("SnapshotWatcher started (interval=%.1fs)", self._interval)

    def stop(self, timeout: float = 5.0) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=timeout)
        log.debug("SnapshotWatcher stopped")

    def latest(self) -> Optional[SupervisorSnapshot]:
        return self.history[-1] if self.history else None

    def _run(self) -> None:
        while not self._stop_event.wait(self._interval):
            try:
                snap = take_snapshot(self._supervisor)
                self.history.append(snap)
                if len(self.history) > self._history_limit:
                    self.history.pop(0)
                for cb in self._callbacks:
                    try:
                        cb(snap)
                    except Exception:
                        log.exception("Snapshot callback raised")
            except Exception:
                log.exception("Error taking snapshot")
