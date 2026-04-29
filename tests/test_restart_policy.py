"""Tests for RestartPolicy and RestartPolicySupervisor."""
from __future__ import annotations

import pytest

from procwatch.restart_policy import RestartPolicy


# ---------------------------------------------------------------------------
# RestartPolicy unit tests
# ---------------------------------------------------------------------------

def test_default_mode_is_on_failure():
    p = RestartPolicy()
    assert p.mode == "on-failure"


def test_invalid_mode_raises():
    with pytest.raises(ValueError, match="Invalid restart mode"):
        RestartPolicy(mode="sometimes")


def test_negative_max_restarts_raises():
    with pytest.raises(ValueError, match="max_restarts"):
        RestartPolicy(max_restarts=-1)


def test_never_mode_never_restarts():
    p = RestartPolicy(mode="never")
    assert p.should_restart(exit_code=1, restart_count=0) is False
    assert p.should_restart(exit_code=0, restart_count=0) is False


def test_always_mode_restarts_on_clean_exit():
    p = RestartPolicy(mode="always")
    assert p.should_restart(exit_code=0, restart_count=0) is True


def test_on_failure_restarts_nonzero():
    p = RestartPolicy(mode="on-failure")
    assert p.should_restart(exit_code=1, restart_count=0) is True


def test_on_failure_skips_zero_exit():
    p = RestartPolicy(mode="on-failure")
    assert p.should_restart(exit_code=0, restart_count=0) is False


def test_max_restarts_caps_restarts():
    p = RestartPolicy(mode="always", max_restarts=3)
    assert p.should_restart(exit_code=0, restart_count=2) is True
    assert p.should_restart(exit_code=0, restart_count=3) is False


def test_allowed_exit_codes_suppresses_restart():
    p = RestartPolicy(mode="on-failure", allowed_exit_codes=[0, 2])
    assert p.should_restart(exit_code=2, restart_count=0) is False
    assert p.should_restart(exit_code=1, restart_count=0) is True


def test_from_config_returns_none_for_empty():
    assert RestartPolicy.from_config({}) is None
    assert RestartPolicy.from_config(None) is None


def test_from_config_builds_object():
    p = RestartPolicy.from_config({"mode": "always", "max_restarts": 5})
    assert p is not None
    assert p.mode == "always"
    assert p.max_restarts == 5


def test_to_dict_roundtrip():
    p = RestartPolicy(mode="on-failure", max_restarts=2, allowed_exit_codes=[0])
    d = p.to_dict()
    p2 = RestartPolicy(**d)
    assert p2.mode == p.mode
    assert p2.max_restarts == p.max_restarts
    assert p2.allowed_exit_codes == p.allowed_exit_codes
