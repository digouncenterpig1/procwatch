"""Tests for procwatch.rollout_supervisor."""
from unittest.mock import MagicMock, patch

import pytest

from procwatch.rollout import RolloutConfig
from procwatch.rollout_supervisor import RolloutSupervisor


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _fake_proc(running: bool = True):
    p = MagicMock()
    p.is_running.return_value = running
    return p


def _make_rs(proc_names, running=True):
    sup = MagicMock()
    procs = {name: _fake_proc(running) for name in proc_names}
    sup.processes = procs
    sup._configs = {name: MagicMock() for name in proc_names}
    sup._make_process.side_effect = lambda cfg: _fake_proc(running)
    return RolloutSupervisor(sup, RolloutConfig(batch_size=2, delay_seconds=0.0, max_failures=1))


# ---------------------------------------------------------------------------
# config management
# ---------------------------------------------------------------------------

def test_default_config_returned_for_unknown_process():
    rs = _make_rs(["a"])
    cfg = rs.config_for("unknown")
    assert isinstance(cfg, RolloutConfig)


def test_set_rollout_config_overrides_default():
    rs = _make_rs(["a"])
    custom = RolloutConfig(batch_size=5, delay_seconds=0.0)
    rs.set_rollout_config("a", custom)
    assert rs.config_for("a").batch_size == 5


# ---------------------------------------------------------------------------
# rolling_restart
# ---------------------------------------------------------------------------

def test_rolling_restart_empty_returns_empty_result():
    rs = _make_rs([])
    result = rs.rolling_restart([])
    assert result.restarted == []
    assert not result.aborted


def test_rolling_restart_all_healthy():
    rs = _make_rs(["web", "worker"])
    result = rs.rolling_restart(["web", "worker"])
    assert set(result.restarted) == {"web", "worker"}
    assert not result.aborted


def test_rolling_restart_defaults_to_all_processes():
    rs = _make_rs(["a", "b"])
    result = rs.rolling_restart()
    assert len(result.restarted) + len(result.failed) == 2


def test_rolling_restart_aborts_on_too_many_failures():
    rs = _make_rs(["a", "b", "c"], running=False)
    # max_failures=0 so first failure aborts
    rs._default = RolloutConfig(batch_size=1, delay_seconds=0.0, max_failures=0)
    result = rs.rolling_restart(["a", "b", "c"])
    assert result.aborted


# ---------------------------------------------------------------------------
# delegation
# ---------------------------------------------------------------------------

def test_start_all_delegates():
    rs = _make_rs(["a"])
    rs.start_all()
    rs._sup.start_all.assert_called_once()


def test_stop_all_delegates():
    rs = _make_rs(["a"])
    rs.stop_all()
    rs._sup.stop_all.assert_called_once()
