"""Tests for procwatch.priority_supervisor."""
from __future__ import annotations

from unittest.mock import MagicMock, patch, call
import pytest

from procwatch.priority_supervisor import PrioritySupervisor
from procwatch.priority import PriorityConfig


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _pcfg(name="web", cmd="echo hi", priority=None):
    cfg = MagicMock()
    cfg.name = name
    cfg.command = cmd
    cfg.priority = priority or {}
    cfg.backoff = {"strategy": "constant", "base": 1}
    cfg.env = {}
    cfg.cwd = None
    return cfg


def _make_supervisor(priority_raw=None):
    watch = MagicMock()
    watch.processes = [_pcfg("web", priority=priority_raw or {})]
    with patch.object(PrioritySupervisor, "_make_process") as mk:
        fake_proc = MagicMock()
        fake_proc.pid = 1234
        fake_proc.is_running.return_value = True
        mk.return_value = fake_proc
        sup = PrioritySupervisor(watch)
        sup.processes = {"web": fake_proc}
    return sup


# ---------------------------------------------------------------------------
# tests
# ---------------------------------------------------------------------------

def test_from_config_called_for_each_process():
    """Priority configs are parsed during __init__."""
    raw = {"nice": -10, "policy": "batch"}
    sup = _make_supervisor(priority_raw=raw)
    cfg = sup._priority_cfgs.get("web")
    assert cfg is not None
    assert cfg.nice == -10


def test_no_priority_config_stores_none():
    sup = _make_supervisor(priority_raw={})
    assert sup._priority_cfgs["web"] is None


def test_apply_priority_calls_apply():
    raw = {"nice": 5}
    sup = _make_supervisor(priority_raw=raw)
    with patch("procwatch.priority_supervisor.apply") as mock_apply:
        sup._apply_priority("web")
        mock_apply.assert_called_once()
        _, cfg_arg = mock_apply.call_args[0]
        assert isinstance(cfg_arg, PriorityConfig)
        assert cfg_arg.nice == 5


def test_apply_priority_skips_unknown_process():
    sup = _make_supervisor(priority_raw={"nice": 1})
    with patch("procwatch.priority_supervisor.apply") as mock_apply:
        sup._apply_priority("nonexistent")
        mock_apply.assert_not_called()


def test_apply_priority_skips_when_no_pid():
    sup = _make_supervisor(priority_raw={"nice": 1})
    sup.processes["web"].pid = None
    with patch("procwatch.priority_supervisor.apply") as mock_apply:
        sup._apply_priority("web")
        mock_apply.assert_not_called()


def test_start_all_applies_priority():
    raw = {"nice": 2}
    sup = _make_supervisor(priority_raw=raw)
    with patch.object(sup.__class__.__bases__[0], "start_all"), \
         patch("procwatch.priority_supervisor.apply") as mock_apply:
        sup.start_all()
        mock_apply.assert_called_once()


def test_check_processes_reapplies_after_restart():
    raw = {"nice": 3}
    sup = _make_supervisor(priority_raw=raw)
    old_pid = sup.processes["web"].pid  # 1234
    with patch.object(sup.__class__.__bases__[0], "check_processes") as mock_check:
        def _restart_side_effect():
            sup.processes["web"].pid = 5678  # simulates restart
        mock_check.side_effect = _restart_side_effect
        with patch("procwatch.priority_supervisor.apply") as mock_apply:
            sup.check_processes()
            mock_apply.assert_called_once()
