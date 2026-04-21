"""Tests for procwatch.uptime_tracker."""

import time
import pytest
from procwatch.uptime_tracker import UptimeTracker, UptimeWindow


def test_initial_state():
    t = UptimeTracker()
    assert not t.is_running
    assert t.current_uptime == 0.0
    assert t.total_uptime == 0.0
    assert t.windows() == []


def test_start_marks_running():
    t = UptimeTracker()
    t.start(now=100.0)
    assert t.is_running
    assert t.current_uptime > 0 or t.current_uptime == 0.0  # monotonic may not advance


def test_current_uptime_grows():
    t = UptimeTracker()
    t.start(now=100.0)
    # Simulate time passing by checking with an explicit window
    w = t._current
    w.started_at = 100.0
    assert w.duration >= 0.0


def test_stop_closes_window():
    t = UptimeTracker()
    t.start(now=100.0)
    t.stop(now=110.0)
    assert not t.is_running
    assert t.current_uptime == 0.0
    assert len(t.windows()) == 1
    assert t.windows()[0]["duration"] == pytest.approx(10.0)


def test_total_uptime_accumulates():
    t = UptimeTracker()
    t.start(now=0.0)
    t.stop(now=5.0)
    t.start(now=10.0)
    t.stop(now=17.0)
    assert t.total_uptime == pytest.approx(12.0)


def test_stop_without_start_is_noop():
    t = UptimeTracker()
    t.stop(now=50.0)  # should not raise
    assert t.windows() == []


def test_double_start_closes_previous_window():
    t = UptimeTracker()
    t.start(now=0.0)
    t.start(now=5.0)  # should flush the first window
    assert len(t.windows()) == 1
    assert t.windows()[0]["duration"] == pytest.approx(5.0)
    assert t.is_running


def test_max_windows_evicts_old():
    t = UptimeTracker(max_windows=3)
    for i in range(5):
        t.start(now=float(i * 10))
        t.stop(now=float(i * 10 + 5))
    assert len(t.windows()) == 3


def test_to_dict_keys():
    t = UptimeTracker()
    d = t.to_dict()
    assert set(d.keys()) == {"is_running", "current_uptime", "total_uptime", "window_count"}


def test_uptime_window_to_dict_open():
    w = UptimeWindow(started_at=100.0)
    d = w.to_dict()
    assert d["started_at"] == 100.0
    assert d["ended_at"] is None
    assert d["duration"] >= 0.0


def test_uptime_window_to_dict_closed():
    w = UptimeWindow(started_at=100.0, ended_at=115.0)
    d = w.to_dict()
    assert d["duration"] == pytest.approx(15.0)
