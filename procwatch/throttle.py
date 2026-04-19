"""Restart throttling: prevent rapid restart loops."""

import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RestartThrottle:
    """Tracks restart attempts and enforces a cooldown window.

    If a process restarts more than `max_restarts` times within
    `window_seconds`, it is considered thrashing and further restarts
    are blocked until the window resets.
    """

    max_restarts: int = 5
    window_seconds: float = 60.0
    _timestamps: list = field(default_factory=list, repr=False)

    def record(self) -> None:
        """Record a restart event at the current time."""
        now = time.monotonic()
        self._timestamps.append(now)
        self._evict(now)

    def is_throttled(self) -> bool:
        """Return True if the process should NOT be restarted right now."""
        now = time.monotonic()
        self._evict(now)
        return len(self._timestamps) >= self.max_restarts

    def reset(self) -> None:
        """Clear all recorded restart timestamps."""
        self._timestamps.clear()

    def time_until_clear(self) -> Optional[float]:
        """Seconds until the oldest event leaves the window, or None."""
        if not self._timestamps:
            return None
        now = time.monotonic()
        oldest = self._timestamps[0]
        remaining = self.window_seconds - (now - oldest)
        return max(0.0, remaining)

    # ------------------------------------------------------------------
    def _evict(self, now: float) -> None:
        cutoff = now - self.window_seconds
        self._timestamps = [t for t in self._timestamps if t > cutoff]
