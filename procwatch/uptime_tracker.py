"""Tracks cumulative uptime windows for managed processes."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class UptimeWindow:
    """A single contiguous uptime window."""
    started_at: float
    ended_at: Optional[float] = None

    @property
    def duration(self) -> float:
        end = self.ended_at if self.ended_at is not None else time.monotonic()
        return max(0.0, end - self.started_at)

    def to_dict(self) -> dict:
        return {
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "duration": self.duration,
        }


class UptimeTracker:
    """Maintains a history of uptime windows for a single process."""

    def __init__(self, max_windows: int = 50) -> None:
        self._max_windows = max_windows
        self._windows: List[UptimeWindow] = []
        self._current: Optional[UptimeWindow] = None

    def start(self, now: Optional[float] = None) -> None:
        """Mark the process as started."""
        if self._current is not None:
            # Close the dangling window defensively
            self._current.ended_at = now or time.monotonic()
            self._flush(self._current)
        self._current = UptimeWindow(started_at=now or time.monotonic())

    def stop(self, now: Optional[float] = None) -> None:
        """Mark the process as stopped."""
        if self._current is None:
            return
        self._current.ended_at = now or time.monotonic()
        self._flush(self._current)
        self._current = None

    def _flush(self, window: UptimeWindow) -> None:
        self._windows.append(window)
        if len(self._windows) > self._max_windows:
            self._windows = self._windows[-self._max_windows :]

    @property
    def current_uptime(self) -> float:
        """Seconds the process has been up in the current window."""
        return self._current.duration if self._current else 0.0

    @property
    def total_uptime(self) -> float:
        """Cumulative uptime across all recorded windows."""
        historical = sum(w.duration for w in self._windows)
        return historical + self.current_uptime

    @property
    def is_running(self) -> bool:
        return self._current is not None

    def windows(self) -> List[dict]:
        return [w.to_dict() for w in self._windows]

    def to_dict(self) -> dict:
        return {
            "is_running": self.is_running,
            "current_uptime": self.current_uptime,
            "total_uptime": self.total_uptime,
            "window_count": len(self._windows),
        }
