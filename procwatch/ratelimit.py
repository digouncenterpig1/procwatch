"""Simple token-bucket rate limiter for restart attempts."""

import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RateLimiter:
    """Token-bucket rate limiter.

    Args:
        rate: tokens replenished per second
        burst: maximum token capacity
    """

    rate: float
    burst: float
    _tokens: float = field(init=False)
    _last: float = field(init=False)

    def __post_init__(self) -> None:
        if self.rate <= 0:
            raise ValueError(f"rate must be positive, got {self.rate}")
        if self.burst <= 0:
            raise ValueError(f"burst must be positive, got {self.burst}")
        self._tokens = self.burst
        self._last = time.monotonic()

    def _replenish(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last
        self._tokens = min(self.burst, self._tokens + elapsed * self.rate)
        self._last = now

    def allow(self) -> bool:
        """Return True and consume a token if allowed, else False."""
        self._replenish()
        if self._tokens >= 1.0:
            self._tokens -= 1.0
            return True
        return False

    def time_until_next(self) -> float:
        """Seconds until the next token is available (0 if already available)."""
        self._replenish()
        if self._tokens >= 1.0:
            return 0.0
        return (1.0 - self._tokens) / self.rate

    def reset(self) -> None:
        """Refill bucket to burst capacity."""
        self._tokens = self.burst
        self._last = time.monotonic()


def from_config(rate: float, burst: Optional[float] = None) -> RateLimiter:
    """Convenience constructor; burst defaults to rate if omitted."""
    return RateLimiter(rate=rate, burst=burst if burst is not None else rate)
