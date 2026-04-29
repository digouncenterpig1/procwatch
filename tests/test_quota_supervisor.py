"""Tests for QuotaSupervisor."""
from unittest.mock import MagicMock, patch

import pytest

from procwatch.quota import QuotaConfig
from procwatch.quota_supervisor import QuotaSupervisor


def _fake_monitor(cpu=10.0, mem_rss=32 * 1024 * 1024):
    sample = MagicMock()
    sample.cpu_percent = cpu
    sample.mem_rss = mem_rss
    monitor = MagicMock()
    monitor.sample.return_value = sample
    return monitor


def _make_qs(monitors=None):
    supervisor = MagicMock()
    supervisor._processes = {}
    pool = MagicMock()
    pool.monitors = monitors or {}
    return QuotaSupervisor(supervisor, pool)


def test_set_and_get_quota():
    qs = _make_qs()
    q = QuotaConfig(max_cpu_percent=50.0)
    qs.set_quota("svc", q)
    assert qs.quota_for("svc") is q


def test_no_quota_no_violation():
    qs = _make_qs(monitors={"svc": _fake_monitor(cpu=99.0)})
    violations = qs.check_quotas()
    assert violations == []


def test_within_quota_no_violation():
    qs = _make_qs(monitors={"svc": _fake_monitor(cpu=30.0)})
    qs.set_quota("svc", QuotaConfig(max_cpu_percent=80.0))
    assert qs.check_quotas() == []


def test_cpu_breach_kills_process():
    fake_proc = MagicMock()
    fake_proc.is_running.return_value = True

    qs = _make_qs(monitors={"svc": _fake_monitor(cpu=95.0)})
    qs._sv._processes["svc"] = fake_proc
    qs.set_quota("svc", QuotaConfig(max_cpu_percent=50.0))

    violations = qs.check_quotas()
    assert len(violations) == 1
    assert violations[0].reason == "cpu"
    fake_proc._proc.kill.assert_called_once()


def test_mem_breach_kills_process():
    fake_proc = MagicMock()
    fake_proc.is_running.return_value = True

    qs = _make_qs(monitors={"svc": _fake_monitor(mem_rss=512 * 1024 * 1024)})
    qs._sv._processes["svc"] = fake_proc
    qs.set_quota("svc", QuotaConfig(max_mem_mb=128.0))

    violations = qs.check_quotas()
    assert len(violations) == 1
    assert violations[0].reason == "mem"


def test_kill_exception_does_not_propagate():
    fake_proc = MagicMock()
    fake_proc.is_running.return_value = True
    fake_proc._proc.kill.side_effect = OSError("no such process")

    qs = _make_qs(monitors={"svc": _fake_monitor(cpu=99.0)})
    qs._sv._processes["svc"] = fake_proc
    qs.set_quota("svc", QuotaConfig(max_cpu_percent=50.0))

    violations = qs.check_quotas()  # must not raise
    assert len(violations) == 1


def test_all_violations_accumulates():
    fake_proc = MagicMock()
    fake_proc.is_running.return_value = True

    qs = _make_qs(monitors={"svc": _fake_monitor(cpu=99.0)})
    qs._sv._processes["svc"] = fake_proc
    qs.set_quota("svc", QuotaConfig(max_cpu_percent=50.0))

    qs.check_quotas()
    qs.check_quotas()
    assert len(qs.all_violations) == 2
