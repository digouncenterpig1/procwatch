"""Grace period tracker — enforces a minimum uptime before a process is
considered eligible for restart.  If a process dies before its grace
period has elapsed the death is treated as an immediate crash and the
cooldown/backoff chain is entered from scratch."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class GracePeriodConfig:
    """Per-process grace period settings."""

    seconds: float = 5.0
    """Minimum seconds a process must stay alive to be considered stable."""

    def __post_init__(self) -> None:
        if self.seconds < 0:
            raise ValueError("grace period seconds must be >= 0")

    @classmethod
    def from_config(cls, cfg: dict) -> Optional["GracePeriodConfig"]:
        """Build from a plain dict; returns *None* when the dict is empty."""
        if not cfg:
            return None
        return cls(seconds=float(cfg.get("grace_seconds", 5.0)))


class GracePeriodTracker:
    """Tracks per-process start times and exposes whether the grace period
    has been satisfied."""

    def __init__(self, default_seconds: float = 5.0) -> None:
        self._default = default_seconds
        self._configs: Dict[str, GracePeriodConfig] = {}
        self._started_at: Dict[str, float] = {}

    def set_config(self, name: str, cfg: GracePeriodConfig) -> None:
        self._configs[name] = cfg

    def record_start(self, name: str, *, now: Optional[float] = None) -> None:
        """Call when a process starts (or restarts)."""
        self._started_at[name] = now if now is not None else time.monotonic()

    def in_grace_period(self, name: str, *, now: Optional[float] = None) -> bool:
        """Return *True* if the process is still within its grace window."""
        start = self._started_at.get(name)
        if start is None:
            return False
        elapsed = (now if now is not None else time.monotonic()) - start
        limit = self._configs.get(name, GracePeriodConfig(self._default)).seconds
        return elapsed < limit

    def time_remaining(self, name: str, *, now: Optional[float] = None) -> float:
        """Seconds left in the grace window (0.0 if already elapsed)."""
        start = self._started_at.get(name)
        if start is None:
            return 0.0
        elapsed = (now if now is not None else time.monotonic()) - start
        limit = self._configs.get(name, GracePeriodConfig(self._default)).seconds
        return max(0.0, limit - elapsed)

    def clear(self, name: str) -> None:
        """Remove tracking state for a process (e.g. after a clean stop)."""
        self._started_at.pop(name, None)
