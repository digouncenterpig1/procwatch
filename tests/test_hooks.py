"""Tests for procwatch.hooks."""
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from procwatch.hooks import HookConfig, HookRunner, from_config


def make_runner(on_start=None, on_stop=None, on_crash=None, timeout=5.0):
    cfg = HookConfig(on_start=on_start, on_stop=on_stop, on_crash=on_crash, timeout=timeout)
    return HookRunner(cfg, "myproc")


def _ok():
    return MagicMock(returncode=0, stderr="")


def _fail():
    return MagicMock(returncode=1, stderr="boom")


def test_on_start_runs_command():
    runner = make_runner(on_start="echo hi")
    with patch("subprocess.run", return_value=_ok()) as mock_run:
        runner.on_start()
    mock_run.assert_called_once()
    assert mock_run.call_args[0][0] == "echo hi"


def test_on_stop_skipped_when_none():
    runner = make_runner()
    with patch("subprocess.run") as mock_run:
        runner.on_stop()
    mock_run.assert_not_called()


def test_on_crash_runs_command():
    runner = make_runner(on_crash="notify.sh")
    with patch("subprocess.run", return_value=_ok()) as mock_run:
        runner.on_crash()
    mock_run.assert_called_once()


def test_nonzero_exit_logs_warning(caplog):
    import logging
    runner = make_runner(on_start="false")
    with patch("subprocess.run", return_value=_fail()):
        with caplog.at_level(logging.WARNING, logger="procwatch.hooks"):
            runner.on_start()
    assert any("exited 1" in r.message for r in caplog.records)


def test_timeout_logs_error(caplog):
    import logging
    runner = make_runner(on_start="sleep 100", timeout=0.001)
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("sleep", 0.001)):
        with caplog.at_level(logging.ERROR, logger="procwatch.hooks"):
            runner.on_start()
    assert any("timed out" in r.message for r in caplog.records)


def test_from_config_builds_runner():
    raw = {"on_start": "echo start", "on_crash": "alert.sh", "timeout": "3"}
    runner = from_config(raw, "svc")
    assert runner._cfg.on_start == "echo start"
    assert runner._cfg.on_crash == "alert.sh"
    assert runner._cfg.timeout == 3.0
    assert runner._cfg.on_stop is None


def test_from_config_defaults():
    runner = from_config({}, "svc")
    assert runner._cfg.on_start is None
    assert runner._cfg.timeout == 5.0
