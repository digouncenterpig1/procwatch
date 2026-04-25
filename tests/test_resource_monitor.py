"""Tests for resource_monitor and resource_pool."""
from __future__ import annotations

import os
import time
from unittest.mock import MagicMock, patch

import pytest

from procwatch.resource_monitor import ResourceMonitor, ResourceSample
from procwatch.resource_pool import ResourcePool


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_proc(cpu: float = 10.0, rss: int = 1024 * 1024):
    proc = MagicMock()
    proc.cpu_percent.return_value = cpu
    mem = MagicMock()
    mem.rss = rss
    proc.memory_info.return_value = mem
    return proc


# ---------------------------------------------------------------------------
# ResourceSample
# ---------------------------------------------------------------------------

def test_sample_to_dict():
    s = ResourceSample(timestamp=1.0, cpu_percent=5.5, rss_bytes=2048)
    d = s.to_dict()
    assert d["cpu_percent"] == 5.5
    assert d["rss_bytes"] == 2048
    assert d["timestamp"] == 1.0


# ---------------------------------------------------------------------------
# ResourceMonitor
# ---------------------------------------------------------------------------

def test_sample_returns_none_when_proc_none():
    mon = ResourceMonitor(pid=99999999)
    mon._proc = None
    assert mon.sample() is None


def test_sample_appends_and_returns():
    mon = ResourceMonitor.__new__(ResourceMonitor)
    mon.pid = 1
    mon._samples = []
    mon._proc = _mock_proc(cpu=20.0, rss=512)
    s = mon.sample()
    assert s is not None
    assert s.cpu_percent == 20.0
    assert s.rss_bytes == 512
    assert len(mon.all_samples()) == 1


def test_latest_none_when_no_samples():
    mon = ResourceMonitor.__new__(ResourceMonitor)
    mon.pid = 1
    mon._samples = []
    mon._proc = None
    assert mon.latest() is None


def test_average_cpu_and_peak_rss():
    mon = ResourceMonitor.__new__(ResourceMonitor)
    mon.pid = 1
    mon._samples = []
    mon._proc = _mock_proc()
    mon._samples = [
        ResourceSample(timestamp=1.0, cpu_percent=10.0, rss_bytes=100),
        ResourceSample(timestamp=2.0, cpu_percent=20.0, rss_bytes=200),
    ]
    assert mon.average_cpu() == 15.0
    assert mon.peak_rss() == 200


def test_to_dict_structure():
    mon = ResourceMonitor.__new__(ResourceMonitor)
    mon.pid = 42
    mon._samples = [ResourceSample(timestamp=0.0, cpu_percent=5.0, rss_bytes=1000)]
    mon._proc = None
    d = mon.to_dict()
    assert d["pid"] == 42
    assert d["sample_count"] == 1
    assert "average_cpu_percent" in d
    assert "peak_rss_bytes" in d


# ---------------------------------------------------------------------------
# ResourcePool
# ---------------------------------------------------------------------------

def test_register_and_get():
    pool = ResourcePool()
    with patch("procwatch.resource_monitor.psutil") as mock_psutil:
        mock_psutil.Process.return_value = _mock_proc()
        mon = pool.register("web", pid=1)
    assert pool.get("web") is mon


def test_unregister_removes_monitor():
    pool = ResourcePool()
    pool._monitors["db"] = MagicMock()
    pool.unregister("db")
    assert pool.get("db") is None


def test_sample_all_calls_each_monitor():
    pool = ResourcePool()
    m1, m2 = MagicMock(), MagicMock()
    m1.sample.return_value = ResourceSample(0.0, 1.0, 100)
    m2.sample.return_value = None
    pool._monitors = {"a": m1, "b": m2}
    result = pool.sample_all()
    assert result["a"] is not None
    assert result["b"] is None


def test_summary_sorted_by_name():
    pool = ResourcePool()
    for name in ("zebra", "alpha", "middle"):
        mon = MagicMock()
        mon.to_dict.return_value = {"pid": 1, "sample_count": 0,
                                    "average_cpu_percent": 0.0,
                                    "peak_rss_bytes": 0, "latest": None}
        pool._monitors[name] = mon
    names = [row["name"] for row in pool.summary()]
    assert names == sorted(names)
