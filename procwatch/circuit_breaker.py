"""Circuit breaker for suppressing restarts of persistently failing processes."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class State(str, Enum):
    CLOSED = "closed"      # normal — restarts allowed
    OPEN = "open"          # tripped — restarts suppressed
    HALF_OPEN = "half_open"  # probe allowed


@dataclass
class CircuitBreaker:
    """Trips open after *failure_threshold* failures within *window* seconds.

    While open, ``allow_restart()`` returns False.  After *recovery_timeout*
    seconds the breaker moves to HALF_OPEN and allows a single probe restart.
    A successful run resets it to CLOSED; another failure re-opens it.
    """

    failure_threshold: int = 5
    window: float = 60.0
    recovery_timeout: float = 30.0

    _state: State = field(default=State.CLOSED, init=False, repr=False)
    _failures: list[float] = field(default_factory=list, init=False, repr=False)
    _opened_at: Optional[float] = field(default=None, init=False, repr=False)

    def _evict(self, now: float) -> None:
        cutoff = now - self.window
        self._failures = [t for t in self._failures if t >= cutoff]

    def record_failure(self, now: Optional[float] = None) -> None:
        now = now if now is not None else time.monotonic()
        if self._state == State.HALF_OPEN:
            self._state = State.OPEN
            self._opened_at = now
            return
        self._failures.append(now)
        self._evict(now)
        if len(self._failures) >= self.failure_threshold:
            self._state = State.OPEN
            self._opened_at = now
            self._failures.clear()

    def record_success(self) -> None:
        self._state = State.CLOSED
        self._failures.clear()
        self._opened_at = None

    def allow_restart(self, now: Optional[float] = None) -> bool:
        now = now if now is not None else time.monotonic()
        if self._state == State.CLOSED:
            return True
        if self._state == State.OPEN:
            if self._opened_at is not None and (now - self._opened_at) >= self.recovery_timeout:
                self._state = State.HALF_OPEN
                return True
            return False
        # HALF_OPEN — only one probe; flip back to OPEN until outcome known
        return False

    @property
    def state(self) -> State:
        return self._state

    def to_dict(self) -> dict:
        return {
            "state": self._state.value,
            "failure_threshold": self.failure_threshold,
            "window": self.window,
            "recovery_timeout": self.recovery_timeout,
        }
