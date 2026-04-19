"""Tests for procwatch.metrics."""

import time
from procwatch.metrics import MetricsRegistry, ProcessMetrics


def test_initial_state():
    m = ProcessMetrics(name="app")
    assert m.start_count == 0
    assert m.restart_count == 0
    assert m.last_started is None
    assert m.current_uptime() == 0.0


def test_record_start_increments_count():
    m = ProcessMetrics(name="app")
    m.record_start()
    assert m.start_count == 1
    assert m.restart_count == 0
    assert m.last_started is not None


def test_restart_count_increments_after_first():
    m = ProcessMetrics(name="app")
    m.record_start()
    m.record_stop(exit_code=0)
    m.record_start()
    assert m.start_count == 2
    assert m.restart_count == 1


def test_record_stop_captures_exit_code():
    m = ProcessMetrics(name="app")
    m.record_start()
    m.record_stop(exit_code=1)
    assert m.last_exit_code == 1
    assert m.last_stopped is not None


def test_uptime_accumulates():
    m = ProcessMetrics(name="app")
    m.record_start()
    time.sleep(0.05)
    m.record_stop()
    assert m.uptime_seconds >= 0.04


def test_current_uptime_while_running():
    m = ProcessMetrics(name="app")
    m.record_start()
    time.sleep(0.05)
    uptime = m.current_uptime()
    assert uptime >= 0.04


def test_registry_creates_on_first_get():
    reg = MetricsRegistry()
    m = reg.get("worker")
    assert m.name == "worker"
    assert reg.get("worker") is m  # same instance


def test_registry_summary():
    reg = MetricsRegistry()
    reg.get("a").record_start()
    reg.get("b").record_start()
    summary = reg.summary()
    names = {s["name"] for s in summary}
    assert names == {"a", "b"}
    for s in summary:
        assert "uptime_seconds" in s
        assert "restart_count" in s
