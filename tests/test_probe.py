"""Tests for procwatch.probe."""
import pytest

from procwatch.probe import ProbeConfig, ProbeRunner


# ---------------------------------------------------------------------------
# ProbeConfig
# ---------------------------------------------------------------------------

def test_default_config_is_valid():
    cfg = ProbeConfig()
    assert cfg.enabled is True
    assert cfg.interval == 10.0
    assert cfg.failure_threshold == 3


def test_negative_interval_raises():
    with pytest.raises(ValueError, match="interval"):
        ProbeConfig(interval=-1)


def test_zero_success_threshold_raises():
    with pytest.raises(ValueError, match="success_threshold"):
        ProbeConfig(success_threshold=0)


def test_from_config_returns_none_for_empty():
    assert ProbeConfig.from_config({}) is None


def test_from_config_builds_object():
    cfg = ProbeConfig.from_config({"interval": 5, "failure_threshold": 2, "enabled": False})
    assert cfg is not None
    assert cfg.interval == 5.0
    assert cfg.failure_threshold == 2
    assert cfg.enabled is False


# ---------------------------------------------------------------------------
# ProbeRunner
# ---------------------------------------------------------------------------

def _runner_with(name="svc", **kwargs) -> ProbeRunner:
    r = ProbeRunner()
    r.register(name, ProbeConfig(**kwargs))
    return r


def test_initially_healthy():
    r = _runner_with()
    assert r.is_healthy("svc") is True


def test_single_failure_does_not_trip_with_threshold_3():
    r = _runner_with(failure_threshold=3)
    r.record("svc", False)
    assert r.is_healthy("svc") is True


def test_three_failures_trip_unhealthy():
    r = _runner_with(failure_threshold=3)
    for _ in range(3):
        r.record("svc", False)
    assert r.is_healthy("svc") is False


def test_record_returns_true_on_transition():
    r = _runner_with(failure_threshold=1)
    changed = r.record("svc", False)
    assert changed is True


def test_record_returns_false_when_no_transition():
    r = _runner_with(failure_threshold=3)
    changed = r.record("svc", False)
    assert changed is False


def test_recovery_requires_success_threshold():
    r = _runner_with(failure_threshold=1, success_threshold=2)
    r.record("svc", False)          # now unhealthy
    r.record("svc", True)           # 1 success — not yet recovered
    assert r.is_healthy("svc") is False
    r.record("svc", True)           # 2nd success — recovered
    assert r.is_healthy("svc") is True


def test_unregistered_name_is_healthy():
    r = ProbeRunner()
    assert r.is_healthy("ghost") is True


def test_unregister_removes_state():
    r = _runner_with()
    r.unregister("svc")
    assert r.state_for("svc") is None


def test_due_returns_false_immediately(monkeypatch):
    import time
    start = time.monotonic()
    monkeypatch.setattr("procwatch.probe.time.monotonic", lambda: start)
    r = _runner_with(interval=30)
    assert r.due("svc") is False


def test_due_returns_true_after_interval(monkeypatch):
    import time
    t = [time.monotonic()]
    monkeypatch.setattr("procwatch.probe.time.monotonic", lambda: t[0])
    r = _runner_with(interval=5)
    t[0] += 6
    assert r.due("svc") is True
