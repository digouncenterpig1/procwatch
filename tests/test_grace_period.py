"""Tests for procwatch.grace_period."""

import pytest

from procwatch.grace_period import GracePeriodConfig, GracePeriodTracker


# ---------------------------------------------------------------------------
# GracePeriodConfig
# ---------------------------------------------------------------------------

def test_default_config_is_valid():
    cfg = GracePeriodConfig()
    assert cfg.seconds == 5.0


def test_negative_seconds_raises():
    with pytest.raises(ValueError, match=">= 0"):
        GracePeriodConfig(seconds=-1.0)


def test_zero_seconds_is_allowed():
    cfg = GracePeriodConfig(seconds=0.0)
    assert cfg.seconds == 0.0


def test_from_config_returns_none_for_empty():
    assert GracePeriodConfig.from_config({}) is None


def test_from_config_builds_object():
    cfg = GracePeriodConfig.from_config({"grace_seconds": 10})
    assert cfg is not None
    assert cfg.seconds == 10.0


def test_from_config_uses_default_when_key_missing():
    cfg = GracePeriodConfig.from_config({"unrelated": True})
    assert cfg.seconds == 5.0


# ---------------------------------------------------------------------------
# GracePeriodTracker
# ---------------------------------------------------------------------------

def _tracker(default: float = 5.0) -> GracePeriodTracker:
    return GracePeriodTracker(default_seconds=default)


def test_not_in_grace_before_start():
    t = _tracker()
    assert t.in_grace_period("svc", now=100.0) is False


def test_in_grace_immediately_after_start():
    t = _tracker(default=5.0)
    t.record_start("svc", now=100.0)
    assert t.in_grace_period("svc", now=100.1) is True


def test_not_in_grace_after_window_elapsed():
    t = _tracker(default=5.0)
    t.record_start("svc", now=100.0)
    assert t.in_grace_period("svc", now=106.0) is False


def test_custom_config_overrides_default():
    t = _tracker(default=5.0)
    t.set_config("svc", GracePeriodConfig(seconds=30.0))
    t.record_start("svc", now=0.0)
    assert t.in_grace_period("svc", now=20.0) is True
    assert t.in_grace_period("svc", now=31.0) is False


def test_time_remaining_decreases():
    t = _tracker(default=10.0)
    t.record_start("svc", now=0.0)
    assert t.time_remaining("svc", now=3.0) == pytest.approx(7.0)
    assert t.time_remaining("svc", now=10.0) == pytest.approx(0.0)
    assert t.time_remaining("svc", now=15.0) == pytest.approx(0.0)


def test_time_remaining_zero_before_start():
    t = _tracker()
    assert t.time_remaining("svc", now=50.0) == 0.0


def test_clear_removes_state():
    t = _tracker(default=5.0)
    t.record_start("svc", now=0.0)
    t.clear("svc")
    assert t.in_grace_period("svc", now=1.0) is False
    assert t.time_remaining("svc", now=1.0) == 0.0


def test_restart_resets_window():
    t = _tracker(default=5.0)
    t.record_start("svc", now=0.0)
    # after grace period
    assert t.in_grace_period("svc", now=10.0) is False
    # process restarts
    t.record_start("svc", now=10.0)
    assert t.in_grace_period("svc", now=12.0) is True
