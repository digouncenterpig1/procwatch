"""Tests for procwatch.rollout."""
import pytest

from procwatch.rollout import RolloutConfig, RolloutResult, rollout


# ---------------------------------------------------------------------------
# RolloutConfig validation
# ---------------------------------------------------------------------------

def test_default_config_is_valid():
    cfg = RolloutConfig()
    assert cfg.batch_size == 1
    assert cfg.delay_seconds == 5.0
    assert cfg.max_failures == 1


def test_batch_size_zero_raises():
    with pytest.raises(ValueError, match="batch_size"):
        RolloutConfig(batch_size=0)


def test_negative_delay_raises():
    with pytest.raises(ValueError, match="delay_seconds"):
        RolloutConfig(delay_seconds=-1.0)


def test_negative_max_failures_raises():
    with pytest.raises(ValueError, match="max_failures"):
        RolloutConfig(max_failures=-1)


def test_from_config_returns_none_for_empty():
    assert RolloutConfig.from_config({}) is None


def test_from_config_builds_object():
    cfg = RolloutConfig.from_config({"batch_size": 3, "delay_seconds": 0.0, "max_failures": 2})
    assert cfg is not None
    assert cfg.batch_size == 3
    assert cfg.delay_seconds == 0.0


# ---------------------------------------------------------------------------
# rollout() logic
# ---------------------------------------------------------------------------

def _make_fns(healthy_names):
    restarted = []

    def restart(name):
        restarted.append(name)

    def is_healthy(name):
        return name in healthy_names

    return restart, is_healthy, restarted


def test_all_healthy_restarts_all():
    names = ["a", "b", "c"]
    restart, is_healthy, restarted = _make_fns(set(names))
    cfg = RolloutConfig(batch_size=2, delay_seconds=0.0, max_failures=0)
    result = rollout(names, restart, is_healthy, cfg)
    assert result.restarted == names
    assert result.failed == []
    assert not result.aborted


def test_failure_aborts_when_over_limit():
    names = ["a", "b", "c"]
    restart, is_healthy, _ = _make_fns(set())  # all unhealthy
    cfg = RolloutConfig(batch_size=1, delay_seconds=0.0, max_failures=1)
    result = rollout(names, restart, is_healthy, cfg)
    assert result.aborted
    # Stopped after exceeding max_failures=1, so at most 2 processed
    assert len(result.failed) <= 2


def test_result_to_dict():
    r = RolloutResult(restarted=["a"], failed=["b"], aborted=True)
    d = r.to_dict()
    assert d["restarted"] == ["a"]
    assert d["failed"] == ["b"]
    assert d["aborted"] is True


def test_exception_in_restart_counts_as_failure():
    def bad_restart(name):
        raise RuntimeError("boom")

    cfg = RolloutConfig(batch_size=1, delay_seconds=0.0, max_failures=0)
    result = rollout(["x"], bad_restart, lambda n: True, cfg)
    assert "x" in result.failed
    assert result.aborted
