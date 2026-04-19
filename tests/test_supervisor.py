"""Tests for the Supervisor class."""

import pytest
from unittest.mock import MagicMock, patch, call

from procwatch.supervisor import Supervisor
from procwatch.config import WatchConfig, ProcessConfig


def make_config(**kwargs):
    defaults = dict(
        name="worker",
        command="echo hello",
        backoff="constant",
        backoff_base=1.0,
        backoff_max=30.0,
        max_restarts=3,
    )
    defaults.update(kwargs)
    proc_cfg = ProcessConfig(**defaults)
    return WatchConfig(processes=[proc_cfg])


def make_supervisor(config=None):
    if config is None:
        config = make_config()
    sup = Supervisor(config)
    return sup


def test_start_all_starts_processes():
    sup = make_supervisor()
    mock_proc = MagicMock()
    with patch.object(sup, "_make_process", return_value=mock_proc):
        sup.start_all()
    mock_proc.start.assert_called_once()
    assert "worker" in sup._processes


def test_stop_all_stops_processes():
    sup = make_supervisor()
    mock_proc = MagicMock()
    sup._processes["worker"] = mock_proc
    sup.stop_all()
    mock_proc.stop.assert_called_once()


def test_check_processes_restarts_dead_process():
    sup = make_supervisor(make_config(backoff_base=0.0, max_restarts=5))
    dead_proc = MagicMock()
    dead_proc.is_running.return_value = False
    new_proc = MagicMock()
    sup._processes["worker"] = dead_proc
    sup._restart_counts["worker"] = 0
    with patch.object(sup, "_make_process", return_value=new_proc), \
         patch("time.sleep"):
        sup._check_processes()
    new_proc.start.assert_called_once()
    assert sup._restart_counts["worker"] == 1


def test_check_processes_gives_up_after_max_restarts():
    sup = make_supervisor(make_config(max_restarts=2))
    dead_proc = MagicMock()
    dead_proc.is_running.return_value = False
    sup._processes["worker"] = dead_proc
    sup._restart_counts["worker"] = 2
    with patch.object(sup, "_make_process") as mock_make:
        sup._check_processes()
    mock_make.assert_not_called()
