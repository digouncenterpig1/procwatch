"""Tests for procwatch.healthcheck."""

import socket
import threading
from unittest.mock import patch

import pytest

from procwatch.healthcheck import HealthCheck, from_config


def test_exec_healthy():
    hc = HealthCheck(type="exec", target="true", retries=1)
    assert hc.check() is True


def test_exec_unhealthy():
    hc = HealthCheck(type="exec", target="false", retries=1)
    assert hc.check() is False


def test_exec_timeout():
    hc = HealthCheck(type="exec", target="sleep 10", timeout=0.1, retries=1)
    assert hc.check() is False


def test_tcp_healthy():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", 0))
    port = server.getsockname()[1]
    server.listen(1)

    def _accept():
        try:
            conn, _ = server.accept()
            conn.close()
        except OSError:
            pass

    t = threading.Thread(target=_accept, daemon=True)
    t.start()

    hc = HealthCheck(type="tcp", target=f"127.0.0.1:{port}", retries=1)
    assert hc.check() is True
    server.close()


def test_tcp_unhealthy():
    hc = HealthCheck(type="tcp", target="127.0.0.1:1", timeout=0.5, retries=1)
    assert hc.check() is False


def test_unsupported_type():
    hc = HealthCheck(type="http", target="http://localhost", retries=1)
    with pytest.raises(ValueError, match="Unsupported"):
        hc.check()


def test_from_config_none():
    assert from_config({}) is None
    assert from_config(None) is None


def test_from_config_builds_healthcheck():
    cfg = {"type": "exec", "target": "true", "interval": 5.0, "retries": 2}
    hc = from_config(cfg)
    assert hc is not None
    assert hc.type == "exec"
    assert hc.interval == 5.0
    assert hc.retries == 2
