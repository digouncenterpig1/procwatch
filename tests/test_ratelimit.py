"""Tests for procwatch.ratelimit."""

import time
import pytest
from procwatch.ratelimit import RateLimiter, from_config


def test_initial_burst_allows_multiple():
    rl = RateLimiter(rate=1.0, burst=3.0)
    assert rl.allow() is True
    assert rl.allow() is True
    assert rl.allow() is True


def test_exhausted_bucket_blocks():
    rl = RateLimiter(rate=1.0, burst=2.0)
    rl.allow()
    rl.allow()
    assert rl.allow() is False


def test_tokens_replenish_over_time(monkeypatch):
    clock = [0.0]

    def fake_monotonic():
        return clock[0]

    monkeypatch.setattr(time, "monotonic", fake_monotonic)

    rl = RateLimiter(rate=2.0, burst=2.0)
    rl.allow()
    rl.allow()
    assert rl.allow() is False

    clock[0] = 1.0  # 2 tokens replenished
    assert rl.allow() is True
    assert rl.allow() is True
    assert rl.allow() is False


def test_time_until_next_zero_when_available():
    rl = RateLimiter(rate=1.0, burst=1.0)
    assert rl.time_until_next() == 0.0


def test_time_until_next_positive_when_empty():
    rl = RateLimiter(rate=2.0, burst=1.0)
    rl.allow()
    wait = rl.time_until_next()
    assert 0.0 < wait <= 0.5 + 0.05  # ~0.5s at rate=2


def test_reset_refills_bucket():
    rl = RateLimiter(rate=1.0, burst=2.0)
    rl.allow()
    rl.allow()
    assert rl.allow() is False
    rl.reset()
    assert rl.allow() is True


def test_from_config_burst_defaults_to_rate():
    rl = from_config(rate=3.0)
    assert rl.burst == 3.0
    assert rl.rate == 3.0


def test_from_config_explicit_burst():
    rl = from_config(rate=1.0, burst=5.0)
    assert rl.burst == 5.0
