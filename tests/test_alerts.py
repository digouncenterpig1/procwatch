"""Tests for procwatch.alerts."""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from procwatch.alerts import AlertConfig, Alerter, from_config


def make_alerter(**kwargs) -> Alerter:
    return Alerter(AlertConfig(**kwargs))


def test_log_handler_called_when_no_handlers(caplog):
    alerter = make_alerter()
    with caplog.at_level("WARNING"):
        alerter.crash("myapp", 1)
    assert "myapp" in caplog.text


def test_crash_suppressed_when_on_crash_false(caplog):
    alerter = make_alerter(on_crash=False)
    with caplog.at_level("WARNING"):
        alerter.crash("myapp", 1)
    assert "myapp" not in caplog.text


def test_throttle_suppressed_when_on_throttle_false(caplog):
    alerter = make_alerter(on_throttle=False)
    with caplog.at_level("WARNING"):
        alerter.throttle("myapp")
    assert "myapp" not in caplog.text


def test_exec_handler_invoked():
    alerter = make_alerter(exec="true")
    with patch("procwatch.alerts.subprocess.run") as mock_run:
        alerter.crash("worker", 2)
        mock_run.assert_called_once()
        _, kwargs = mock_run.call_args
        assert kwargs["env"]["PROCWATCH_PROCESS"] == "worker"
        assert "crashed" in kwargs["env"]["PROCWATCH_MESSAGE"]


def test_exec_handler_timeout_does_not_raise():
    alerter = make_alerter(exec="sleep 100")
    with patch("procwatch.alerts.subprocess.run", side_effect=subprocess.TimeoutExpired("sleep", 10)):
        # should not raise — handler swallows errors
        alerter.crash("worker", 1)


def test_smtp_handler_sends_email():
    alerter = make_alerter(smtp_host="localhost", smtp_to=["ops@example.com"])
    mock_smtp = MagicMock()
    with patch("procwatch.alerts.smtplib.SMTP", return_value=mock_smtp.__enter__.return_value):
        mock_smtp.__enter__.return_value = mock_smtp
        mock_smtp.__exit__.return_value = False
        with patch("procwatch.alerts.smtplib.SMTP") as smtp_cls:
            smtp_cls.return_value.__enter__.return_value = mock_smtp
            smtp_cls.return_value.__exit__.return_value = False
            alerter.throttle("worker")
            mock_smtp.send_message.assert_called_once()


def test_from_config_builds_alerter():
    raw = {"on_crash": True, "exec": "/usr/bin/notify", "smtp_to": []}
    alerter = from_config(raw)
    assert isinstance(alerter, Alerter)
    assert alerter.config.exec == "/usr/bin/notify"


def test_from_config_defaults():
    alerter = from_config({})
    assert alerter.config.on_crash is True
    assert alerter.config.smtp_port == 25
