"""Tests for procwatch.circuit_breaker."""
import pytest
from procwatch.circuit_breaker import CircuitBreaker, State


def make_cb(**kw) -> CircuitBreaker:
    defaults = dict(failure_threshold=3, window=60.0, recovery_timeout=30.0)
    defaults.update(kw)
    return CircuitBreaker(**defaults)


def test_initial_state_is_closed():
    cb = make_cb()
    assert cb.state == State.CLOSED
    assert cb.allow_restart() is True


def test_trips_open_after_threshold():
    cb = make_cb(failure_threshold=3)
    now = 0.0
    for i in range(3):
        cb.record_failure(now=now + i)
    assert cb.state == State.OPEN
    assert cb.allow_restart(now=now + 3) is False


def test_does_not_trip_below_threshold():
    cb = make_cb(failure_threshold=3)
    cb.record_failure(now=0.0)
    cb.record_failure(now=1.0)
    assert cb.state == State.CLOSED
    assert cb.allow_restart() is True


def test_old_failures_evicted_from_window():
    cb = make_cb(failure_threshold=3, window=10.0)
    cb.record_failure(now=0.0)
    cb.record_failure(now=1.0)
    # third failure is far in the future — first two should be evicted
    cb.record_failure(now=100.0)
    assert cb.state == State.CLOSED


def test_transitions_to_half_open_after_recovery_timeout():
    cb = make_cb(failure_threshold=2, recovery_timeout=30.0)
    cb.record_failure(now=0.0)
    cb.record_failure(now=1.0)
    assert cb.state == State.OPEN
    # before timeout — still blocked
    assert cb.allow_restart(now=20.0) is False
    # after timeout — probe allowed
    assert cb.allow_restart(now=31.0) is True
    assert cb.state == State.HALF_OPEN


def test_success_in_half_open_resets_to_closed():
    cb = make_cb(failure_threshold=2, recovery_timeout=10.0)
    cb.record_failure(now=0.0)
    cb.record_failure(now=1.0)
    cb.allow_restart(now=15.0)  # move to HALF_OPEN
    cb.record_success()
    assert cb.state == State.CLOSED
    assert cb.allow_restart() is True


def test_failure_in_half_open_reopens():
    cb = make_cb(failure_threshold=2, recovery_timeout=10.0)
    cb.record_failure(now=0.0)
    cb.record_failure(now=1.0)
    cb.allow_restart(now=15.0)  # HALF_OPEN
    cb.record_failure(now=16.0)  # re-open
    assert cb.state == State.OPEN


def test_to_dict_returns_expected_keys():
    cb = make_cb()
    d = cb.to_dict()
    assert set(d.keys()) == {"state", "failure_threshold", "window", "recovery_timeout"}
    assert d["state"] == "closed"
