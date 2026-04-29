"""Tests for QuotaConfig and QuotaChecker."""
import pytest
from unittest.mock import MagicMock

from procwatch.quota import QuotaChecker, QuotaConfig, QuotaViolation


# ---------------------------------------------------------------------------
# QuotaConfig
# ---------------------------------------------------------------------------

def test_default_config_has_no_limits():
    q = QuotaConfig()
    assert q.max_cpu_percent is None
    assert q.max_mem_mb is None


def test_invalid_cpu_raises():
    with pytest.raises(ValueError):
        QuotaConfig(max_cpu_percent=0)


def test_invalid_cpu_over_100_raises():
    with pytest.raises(ValueError):
        QuotaConfig(max_cpu_percent=101)


def test_invalid_mem_raises():
    with pytest.raises(ValueError):
        QuotaConfig(max_mem_mb=-1)


def test_from_config_returns_none_for_empty():
    assert QuotaConfig.from_config({}) is None


def test_from_config_builds_object():
    q = QuotaConfig.from_config({"max_cpu_percent": 50.0, "max_mem_mb": 256.0})
    assert q is not None
    assert q.max_cpu_percent == 50.0
    assert q.max_mem_mb == 256.0


# ---------------------------------------------------------------------------
# QuotaChecker
# ---------------------------------------------------------------------------

def _sample(cpu=10.0, mem_rss=64 * 1024 * 1024):
    s = MagicMock()
    s.cpu_percent = cpu
    s.mem_rss = mem_rss
    return s


def test_no_violation_within_limits():
    checker = QuotaChecker()
    quota = QuotaConfig(max_cpu_percent=80.0, max_mem_mb=256.0)
    assert checker.check("svc", _sample(cpu=50.0, mem_rss=128 * 1024 * 1024), quota) is None


def test_cpu_violation_detected():
    checker = QuotaChecker()
    quota = QuotaConfig(max_cpu_percent=50.0)
    v = checker.check("svc", _sample(cpu=75.0), quota)
    assert v is not None
    assert v.reason == "cpu"
    assert v.process_name == "svc"


def test_mem_violation_detected():
    checker = QuotaChecker()
    quota = QuotaConfig(max_mem_mb=64.0)
    v = checker.check("svc", _sample(mem_rss=128 * 1024 * 1024), quota)
    assert v is not None
    assert v.reason == "mem"


def test_none_sample_returns_none():
    checker = QuotaChecker()
    quota = QuotaConfig(max_cpu_percent=50.0)
    assert checker.check("svc", None, quota) is None


def test_violation_to_dict():
    v = QuotaViolation(process_name="svc", reason="cpu", cpu_percent=90.0)
    d = v.to_dict()
    assert d["process_name"] == "svc"
    assert d["reason"] == "cpu"
    assert d["cpu_percent"] == 90.0
