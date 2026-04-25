"""Tests for procwatch.cb_supervisor."""
from unittest.mock import MagicMock, patch

import pytest

from procwatch.cb_supervisor import CBSupervisor
from procwatch.circuit_breaker import State
from procwatch.config import ProcessConfig, WatchConfig


def _pcfg(name: str) -> ProcessConfig:
    return ProcessConfig(name=name, command=f"echo {name}")


def _make_supervisor(**cb_kw) -> CBSupervisor:
    cfg = WatchConfig(processes=[_pcfg("alpha"), _pcfg("beta")])
    return CBSupervisor(cfg, **cb_kw)


def _fake_proc(running: bool, returncode: int = 0) -> MagicMock:
    p = MagicMock()
    p.is_running.return_value = running
    p.returncode.return_value = returncode
    return p


def test_running_process_records_success():
    sup = _make_supervisor(failure_threshold=3)
    sup._processes["alpha"] = _fake_proc(running=True)
    sup._config_map = {"alpha": _pcfg("alpha")}
    sup.check_processes()
    assert sup._breaker("alpha").state == State.CLOSED


def test_dead_process_is_restarted_when_breaker_closed():
    sup = _make_supervisor(failure_threshold=5)
    dead = _fake_proc(running=False, returncode=1)
    sup._processes["alpha"] = dead
    sup._config_map = {"alpha": _pcfg("alpha")}

    new_proc = _fake_proc(running=True)
    with patch.object(sup, "_make_process", return_value=new_proc) as mk:
        sup.check_processes()
        mk.assert_called_once()
    assert sup._processes["alpha"] is new_proc


def test_restart_suppressed_when_breaker_open():
    sup = _make_supervisor(failure_threshold=2, window=60.0, recovery_timeout=999.0)
    sup._processes["alpha"] = _fake_proc(running=False, returncode=1)
    sup._config_map = {"alpha": _pcfg("alpha")}

    # trip the breaker manually
    cb = sup._breaker("alpha")
    cb.record_failure(now=0.0)
    cb.record_failure(now=1.0)
    assert cb.state == State.OPEN

    original = sup._processes["alpha"]
    with patch.object(sup, "_make_process") as mk:
        sup.check_processes()
        mk.assert_not_called()
    # process reference unchanged
    assert sup._processes["alpha"] is original


def test_breaker_states_returns_dict():
    sup = _make_supervisor()
    sup._breaker("alpha")  # touch to create
    states = sup.breaker_states()
    assert "alpha" in states
    assert states["alpha"]["state"] == "closed"


def test_each_process_gets_independent_breaker():
    sup = _make_supervisor(failure_threshold=2)
    # trip alpha's breaker
    cb_a = sup._breaker("alpha")
    cb_a.record_failure(now=0.0)
    cb_a.record_failure(now=1.0)
    # beta should still be closed
    assert sup._breaker("beta").state == State.CLOSED
    assert sup._breaker("alpha").state == State.OPEN
