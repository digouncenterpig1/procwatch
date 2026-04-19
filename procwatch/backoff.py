"""Backoff strategies for process restart delays."""

import random
from typing import Iterator


def constant(delay: float) -> Iterator[float]:
    """Always wait the same amount of time."""
    while True:
        yield delay


def linear(initial: float, step: float, maximum: float = 300.0) -> Iterator[float]:
    """Increase delay linearly on each restart."""
    delay = initial
    while True:
        yield min(delay, maximum)
        delay += step


def exponential(
    initial: float, factor: float = 2.0, maximum: float = 300.0, jitter: bool = False
) -> Iterator[float]:
    """Exponentially increase delay, optionally with jitter."""
    delay = initial
    while True:
        value = min(delay, maximum)
        if jitter:
            value = random.uniform(0, value)
        yield value
        delay = min(delay * factor, maximum)


def from_config(strategy: str, **kwargs) -> Iterator[float]:
    """Build a backoff iterator from a strategy name and keyword args."""
    strategies = {
        "constant": constant,
        "linear": linear,
        "exponential": exponential,
    }
    if strategy not in strategies:
        raise ValueError(
            f"Unknown backoff strategy '{strategy}'. "
            f"Choose from: {', '.join(strategies)}"
        )
    return strategies[strategy](**kwargs)
