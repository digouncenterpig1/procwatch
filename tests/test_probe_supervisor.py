"""Tests for procwatch.probe_supervisor."""
from unittest.mock import MagicMock, patch

import pytest

from procwatch.probe import ProbeConfig
from procwatch.probe_supervisor import ProbeSupervisor


def _fake_proc(running: bool = True) -> MagicMock:
    p = MagicMock()
    p.is_running.return_value = running
    return p


def _make_ps(probe_fn=None) -> tuple[ProbeSupervisor, MagicMock]:
    sup = MagicMock()
    sup._procs = {}
    ps = ProbeSupervisor(sup, probe_fn=probe_fn)
    return ps, sup


def test_start_all_delegates():
    ps, sup = _make_ps()
    ps.start_all()
    sup.start_all.assert_called_once()


def test_stop_all_delegates():
    ps, sup = _make_ps()
    ps.stop_all()
    sup.stop_all.assert_called_once()


def test_tick_skips_when_not_due(monkeypatch):
    ps, sup = _make_ps(probe_fn=lambda n, t: True)
    ps.set_probe("svc", ProbeConfig(interval=9999))
    sup._procs["svc"] = _fake_proc()
    ps.tick()  # should not probe — interval not elapsed
    assert ps.is_healthy("svc") is True


def test_tick_healthy_probe_keeps_healthy(monkeypatch):
    import procwatch.probe as probe_mod
    import time
    t = [time.monotonic()]
    monkeypatch.setattr(probe_mod.time, "monotonic", lambda: t[0])

    ps, sup = _make_ps(probe_fn=lambda n, timeout: True)
    ps.set_probe("svc", ProbeConfig(interval=1))
    sup._procs["svc"] = _fake_proc()

    t[0] += 2  # advance past interval
    ps.tick()
    assert ps.is_healthy("svc") is True


def test_tick_failing_probe_stops_process(monkeypatch):
    import procwatch.probe as probe_mod
    import time
    t = [time.monotonic()]
    monkeypatch.setattr(probe_mod.time, "monotonic", lambda: t[0])

    proc = _fake_proc()
    ps, sup = _make_ps(probe_fn=lambda n, timeout: False)
    ps.set_probe("svc", ProbeConfig(interval=1, failure_threshold=1))
    sup._procs["svc"] = proc

    t[0] += 2
    ps.tick()
    proc.stop.assert_called_once()
    assert ps.is_healthy("svc") is False


def test_tick_exception_in_probe_treated_as_failure(monkeypatch):
    import procwatch.probe as probe_mod
    import time
    t = [time.monotonic()]
    monkeypatch.setattr(probe_mod.time, "monotonic", lambda: t[0])

    def boom(n, timeout):
        raise RuntimeError("network error")

    proc = _fake_proc()
    ps, sup = _make_ps(probe_fn=boom)
    ps.set_probe("svc", ProbeConfig(interval=1, failure_threshold=1))
    sup._procs["svc"] = proc

    t[0] += 2
    ps.tick()  # must not raise
    proc.stop.assert_called_once()


def test_health_summary_returns_all_registered():
    ps, _ = _make_ps()
    ps.set_probe("a", ProbeConfig())
    ps.set_probe("b", ProbeConfig())
    summary = ps.health_summary()
    assert set(summary.keys()) == {"a", "b"}
    assert all(v is True for v in summary.values())


def test_remove_probe_clears_entry():
    ps, _ = _make_ps()
    ps.set_probe("svc", ProbeConfig())
    ps.remove_probe("svc")
    assert "svc" not in ps.health_summary()
