"""Tests for procwatch.throttle."""

import time
import pytest
from procwatch.throttle import RestartThrottle


def test_not_throttled_initially():
    t = RestartThrottle(max_restarts=3, window_seconds=60)
    assert not t.is_throttled()


def test_throttled_after_max_restarts():
    t = RestartThrottle(max_restarts=3, window_seconds=60)
    for _ in range(3):
        t.record()
    assert t.is_throttled()


def test_not_throttled_below_max():
    t = RestartThrottle(max_restarts=5, window_seconds=60)
    for _ in range(4):
        t.record()
    assert not t.is_throttled()


def test_reset_clears_throttle():
    t = RestartThrottle(max_restarts=2, window_seconds=60)
    t.record()
    t.record()
    assert t.is_throttled()
    t.reset()
    assert not t.is_throttled()


def test_old_events_evicted(monkeypatch):
    """Events outside the window should not count."""
    base = 1_000.0
    calls = iter([base, base, base + 61, base + 61, base + 61])
    monkeypatch.setattr(time, "monotonic", lambda: next(calls))

    t = RestartThrottle(max_restarts=2, window_seconds=60)
    t.record()  # at base
    t.record()  # at base  -> throttled
    # now time has jumped past window; is_throttled evicts both
    assert not t.is_throttled()


def test_time_until_clear_none_when_empty():
    t = RestartThrottle()
    assert t.time_until_clear() is None


def test_time_until_clear_positive():
    t = RestartThrottle(max_restarts=3, window_seconds=30)
    t.record()
    remaining = t.time_until_clear()
    assert remaining is not None
    assert 0 < remaining <= 30
