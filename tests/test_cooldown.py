"""Tests for procwatch.cooldown."""
from __future__ import annotations

import time
import pytest
from unittest.mock import patch

from procwatch.cooldown import CooldownPolicy, CooldownTracker


# ---------------------------------------------------------------------------
# CooldownPolicy validation
# ---------------------------------------------------------------------------

def test_default_policy_is_valid():
    p = CooldownPolicy()
    assert p.min_wait == 1.0
    assert p.max_wait == 60.0
    assert p.multiplier == 1.0


def test_negative_min_wait_raises():
    with pytest.raises(ValueError, match="min_wait"):
        CooldownPolicy(min_wait=-1.0)


def test_max_less_than_min_raises():
    with pytest.raises(ValueError, match="max_wait"):
        CooldownPolicy(min_wait=10.0, max_wait=5.0)


def test_multiplier_below_one_raises():
    with pytest.raises(ValueError, match="multiplier"):
        CooldownPolicy(multiplier=0.5)


# ---------------------------------------------------------------------------
# CooldownTracker behaviour
# ---------------------------------------------------------------------------

def _tracker(min_wait=2.0, multiplier=1.0) -> CooldownTracker:
    return CooldownTracker(CooldownPolicy(min_wait=min_wait, max_wait=120.0, multiplier=multiplier))


def test_not_cooling_down_initially():
    t = _tracker()
    assert not t.is_cooling_down("web")
    assert t.time_remaining("web") == 0.0


def test_cooling_down_immediately_after_restart():
    t = _tracker(min_wait=5.0)
    t.record_restart("web")
    assert t.is_cooling_down("web")
    assert t.time_remaining("web") > 0.0


def test_not_cooling_down_after_wait():
    t = _tracker(min_wait=0.05)
    t.record_restart("web")
    time.sleep(0.1)
    assert not t.is_cooling_down("web")
    assert t.time_remaining("web") == 0.0


def test_restart_count_increments():
    t = _tracker()
    assert t.restart_count("web") == 0
    t.record_restart("web")
    assert t.restart_count("web") == 1
    t.record_restart("web")
    assert t.restart_count("web") == 2


def test_reset_clears_state():
    t = _tracker(min_wait=5.0)
    t.record_restart("web")
    t.reset("web")
    assert not t.is_cooling_down("web")
    assert t.restart_count("web") == 0


def test_progressive_cooldown_grows_with_restarts():
    """With multiplier=2.0 each restart doubles the wait."""
    t = _tracker(min_wait=1.0, multiplier=2.0)
    mono = [0.0]

    def fake_monotonic():
        return mono[0]

    with patch("procwatch.cooldown.time.monotonic", side_effect=fake_monotonic):
        t.record_restart("svc")   # count=1, wait=1.0
        mono[0] = 0.5
        r1 = t.time_remaining("svc")  # 0.5 elapsed -> 0.5 left

        mono[0] = 1.0              # cooldown over
        t.record_restart("svc")   # count=2, wait=2.0
        mono[0] = 1.5
        r2 = t.time_remaining("svc")  # 0.5 elapsed -> 1.5 left

    assert abs(r1 - 0.5) < 1e-9
    assert abs(r2 - 1.5) < 1e-9


def test_progressive_cooldown_caps_at_max_wait():
    t = CooldownTracker(CooldownPolicy(min_wait=1.0, max_wait=3.0, multiplier=10.0))
    for _ in range(5):
        t.record_restart("svc")
    # wait would be 1.0 * 10^4 = 10000, but capped at 3.0
    remaining = t.time_remaining("svc")
    assert remaining <= 3.0
