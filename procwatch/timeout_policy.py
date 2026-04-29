"""Per-process shutdown timeout policies."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class TimeoutPolicy:
    """Configuration for how long to wait for a process to stop gracefully."""

    graceful_timeout: float = 5.0   # seconds to wait after SIGTERM
    kill_timeout: float = 2.0       # seconds to wait after SIGKILL before giving up

    def __post_init__(self) -> None:
        if self.graceful_timeout < 0:
            raise ValueError("graceful_timeout must be >= 0")
        if self.kill_timeout < 0:
            raise ValueError("kill_timeout must be >= 0")

    @classmethod
    def from_config(cls, cfg: dict) -> Optional["TimeoutPolicy"]:
        """Build a TimeoutPolicy from a raw config dict, or return None if empty."""
        if not cfg:
            return None
        return cls(
            graceful_timeout=float(cfg.get("graceful_timeout", 5.0)),
            kill_timeout=float(cfg.get("kill_timeout", 2.0)),
        )


@dataclass
class TimeoutTracker:
    """Tracks per-process timeout policies and deadline state."""

    default_policy: TimeoutPolicy = field(default_factory=TimeoutPolicy)
    _policies: Dict[str, TimeoutPolicy] = field(default_factory=dict, init=False)
    _deadlines: Dict[str, float] = field(default_factory=dict, init=False)

    def set_policy(self, name: str, policy: TimeoutPolicy) -> None:
        self._policies[name] = policy

    def policy_for(self, name: str) -> TimeoutPolicy:
        return self._policies.get(name, self.default_policy)

    def start_graceful(self, name: str, *, _now: Optional[float] = None) -> float:
        """Record that graceful shutdown started; return the deadline timestamp."""
        policy = self.policy_for(name)
        deadline = (_now if _now is not None else time.monotonic()) + policy.graceful_timeout
        self._deadlines[name] = deadline
        return deadline

    def is_expired(self, name: str, *, _now: Optional[float] = None) -> bool:
        """Return True if the graceful timeout deadline has passed."""
        deadline = self._deadlines.get(name)
        if deadline is None:
            return False
        now = _now if _now is not None else time.monotonic()
        return now >= deadline

    def clear(self, name: str) -> None:
        self._deadlines.pop(name, None)

    def all_policies(self) -> Dict[str, TimeoutPolicy]:
        return dict(self._policies)
