"""Per-process restart cooldown tracker.

Tracks the last restart time for each process and enforces a minimum
wait period before another restart is allowed.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class CooldownPolicy:
    """Configuration for restart cooldown behaviour."""
    min_wait: float = 1.0   # seconds between restarts
    max_wait: float = 60.0  # upper bound when multiplier is used
    multiplier: float = 1.0  # >1.0 for progressive cooldown

    def __post_init__(self) -> None:
        if self.min_wait < 0:
            raise ValueError("min_wait must be >= 0")
        if self.max_wait < self.min_wait:
            raise ValueError("max_wait must be >= min_wait")
        if self.multiplier < 1.0:
            raise ValueError("multiplier must be >= 1.0")


class CooldownTracker:
    """Tracks per-process cooldown state."""

    def __init__(self, policy: CooldownPolicy) -> None:
        self._policy = policy
        self._last_restart: Dict[str, float] = {}
        self._restart_count: Dict[str, int] = {}

    def record_restart(self, name: str) -> None:
        """Record that *name* was just restarted."""
        self._last_restart[name] = time.monotonic()
        self._restart_count[name] = self._restart_count.get(name, 0) + 1

    def is_cooling_down(self, name: str) -> bool:
        """Return True if *name* must wait before the next restart."""
        return self.time_remaining(name) > 0.0

    def time_remaining(self, name: str) -> float:
        """Seconds until *name* may be restarted, or 0.0 if ready."""
        last = self._last_restart.get(name)
        if last is None:
            return 0.0
        count = self._restart_count.get(name, 1)
        wait = min(
            self._policy.min_wait * (self._policy.multiplier ** (count - 1)),
            self._policy.max_wait,
        )
        elapsed = time.monotonic() - last
        return max(0.0, wait - elapsed)

    def reset(self, name: str) -> None:
        """Clear cooldown state for *name* (e.g. after a clean run)."""
        self._last_restart.pop(name, None)
        self._restart_count.pop(name, None)

    def restart_count(self, name: str) -> int:
        """Return how many times *name* has been restarted."""
        return self._restart_count.get(name, 0)
