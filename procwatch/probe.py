"""Readiness and liveness probe support for managed processes."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Dict, Optional


@dataclass
class ProbeConfig:
    enabled: bool = True
    interval: float = 10.0        # seconds between probes
    timeout: float = 5.0          # seconds before probe is considered failed
    success_threshold: int = 1    # consecutive successes to mark healthy
    failure_threshold: int = 3    # consecutive failures to mark unhealthy

    def __post_init__(self) -> None:
        if self.interval <= 0:
            raise ValueError("interval must be positive")
        if self.timeout <= 0:
            raise ValueError("timeout must be positive")
        if self.success_threshold < 1:
            raise ValueError("success_threshold must be >= 1")
        if self.failure_threshold < 1:
            raise ValueError("failure_threshold must be >= 1")

    @classmethod
    def from_config(cls, data: dict) -> Optional["ProbeConfig"]:
        if not data:
            return None
        return cls(
            enabled=data.get("enabled", True),
            interval=float(data.get("interval", 10.0)),
            timeout=float(data.get("timeout", 5.0)),
            success_threshold=int(data.get("success_threshold", 1)),
            failure_threshold=int(data.get("failure_threshold", 3)),
        )


@dataclass
class ProbeState:
    healthy: bool = True
    consecutive_successes: int = 0
    consecutive_failures: int = 0
    last_checked: float = field(default_factory=time.monotonic)
    last_result: Optional[bool] = None


class ProbeRunner:
    """Tracks per-process probe state and evaluates health transitions."""

    def __init__(self) -> None:
        self._configs: Dict[str, ProbeConfig] = {}
        self._states: Dict[str, ProbeState] = {}

    def register(self, name: str, config: ProbeConfig) -> None:
        self._configs[name] = config
        self._states[name] = ProbeState()

    def unregister(self, name: str) -> None:
        self._configs.pop(name, None)
        self._states.pop(name, None)

    def record(self, name: str, success: bool) -> bool:
        """Record a probe result; return True if health status changed."""
        cfg = self._configs.get(name)
        state = self._states.get(name)
        if cfg is None or state is None:
            return False

        state.last_checked = time.monotonic()
        state.last_result = success
        prev = state.healthy

        if success:
            state.consecutive_successes += 1
            state.consecutive_failures = 0
            if not state.healthy and state.consecutive_successes >= cfg.success_threshold:
                state.healthy = True
        else:
            state.consecutive_failures += 1
            state.consecutive_successes = 0
            if state.healthy and state.consecutive_failures >= cfg.failure_threshold:
                state.healthy = False

        return state.healthy != prev

    def is_healthy(self, name: str) -> bool:
        state = self._states.get(name)
        return state.healthy if state else True

    def due(self, name: str) -> bool:
        """Return True if the next probe interval has elapsed."""
        cfg = self._configs.get(name)
        state = self._states.get(name)
        if cfg is None or state is None:
            return False
        return (time.monotonic() - state.last_checked) >= cfg.interval

    def state_for(self, name: str) -> Optional[ProbeState]:
        return self._states.get(name)
