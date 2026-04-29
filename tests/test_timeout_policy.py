"""Tests for procwatch.timeout_policy."""
import pytest

from procwatch.timeout_policy import TimeoutPolicy, TimeoutTracker


# ---------------------------------------------------------------------------
# TimeoutPolicy
# ---------------------------------------------------------------------------

def test_default_values():
    p = TimeoutPolicy()
    assert p.graceful_timeout == 5.0
    assert p.kill_timeout == 2.0


def test_negative_graceful_raises():
    with pytest.raises(ValueError, match="graceful_timeout"):
        TimeoutPolicy(graceful_timeout=-1.0)


def test_negative_kill_raises():
    with pytest.raises(ValueError, match="kill_timeout"):
        TimeoutPolicy(kill_timeout=-0.1)


def test_from_config_returns_none_for_empty():
    assert TimeoutPolicy.from_config({}) is None
    assert TimeoutPolicy.from_config(None) is None


def test_from_config_builds_object():
    p = TimeoutPolicy.from_config({"graceful_timeout": 10, "kill_timeout": 3})
    assert p is not None
    assert p.graceful_timeout == 10.0
    assert p.kill_timeout == 3.0


def test_from_config_uses_defaults_for_missing_keys():
    p = TimeoutPolicy.from_config({"graceful_timeout": 7})
    assert p.kill_timeout == 2.0


# ---------------------------------------------------------------------------
# TimeoutTracker
# ---------------------------------------------------------------------------

def test_policy_for_returns_default_when_unset():
    tracker = TimeoutTracker()
    p = tracker.policy_for("web")
    assert p.graceful_timeout == 5.0


def test_set_and_get_policy():
    tracker = TimeoutTracker()
    tracker.set_policy("web", TimeoutPolicy(graceful_timeout=15.0))
    assert tracker.policy_for("web").graceful_timeout == 15.0


def test_start_graceful_returns_deadline():
    tracker = TimeoutTracker()
    tracker.set_policy("svc", TimeoutPolicy(graceful_timeout=10.0))
    deadline = tracker.start_graceful("svc", _now=100.0)
    assert deadline == 110.0


def test_is_expired_false_before_deadline():
    tracker = TimeoutTracker()
    tracker.start_graceful("svc", _now=100.0)  # deadline = 105.0
    assert not tracker.is_expired("svc", _now=104.9)


def test_is_expired_true_at_deadline():
    tracker = TimeoutTracker()
    tracker.start_graceful("svc", _now=100.0)  # deadline = 105.0
    assert tracker.is_expired("svc", _now=105.0)


def test_is_expired_false_when_no_deadline():
    tracker = TimeoutTracker()
    assert not tracker.is_expired("unknown", _now=999.0)


def test_clear_removes_deadline():
    tracker = TimeoutTracker()
    tracker.start_graceful("svc", _now=0.0)
    tracker.clear("svc")
    assert not tracker.is_expired("svc", _now=999.0)


def test_all_policies_returns_copy():
    tracker = TimeoutTracker()
    tracker.set_policy("a", TimeoutPolicy(graceful_timeout=3.0))
    tracker.set_policy("b", TimeoutPolicy(graceful_timeout=7.0))
    result = tracker.all_policies()
    assert set(result.keys()) == {"a", "b"}
