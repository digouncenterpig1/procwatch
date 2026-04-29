"""Tests for AuditSupervisor."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from procwatch.audit import AuditLog
from procwatch.audit_supervisor import AuditSupervisor
from procwatch.config import ProcessConfig, WatchConfig


def _pcfg(name: str) -> ProcessConfig:
    return ProcessConfig(name=name, command=f"echo {name}")


def _make_supervisor(tmp_path: Path, *names: str) -> tuple[AuditSupervisor, AuditLog]:
    cfg = WatchConfig(processes=[_pcfg(n) for n in names])
    log = AuditLog(tmp_path / "audit.jsonl")
    sup = AuditSupervisor(cfg, audit_log=log, actor="test")
    return sup, log


def _fake_proc(running: bool) -> MagicMock:
    p = MagicMock()
    p.is_running.return_value = running
    return p


# ── start_all ──────────────────────────────────────────────────────────────

def test_start_all_records_start_entries(tmp_path: Path):
    sup, log = _make_supervisor(tmp_path, "web", "worker")
    with patch.object(sup, "_make_process", return_value=_fake_proc(True)):
        with patch("procwatch.supervisor.Supervisor.start_all"):
            sup._processes = {"web": _fake_proc(True), "worker": _fake_proc(True)}
            sup.start_all()
    entries = log.read_all()
    actions = {e.action for e in entries}
    assert "start" in actions


# ── stop_all ───────────────────────────────────────────────────────────────

def test_stop_all_records_stop_entries(tmp_path: Path):
    sup, log = _make_supervisor(tmp_path, "api")
    sup._processes = {"api": _fake_proc(True)}
    with patch("procwatch.supervisor.Supervisor.stop_all"):
        sup.stop_all()
    entries = log.read_all()
    assert any(e.action == "stop" and e.process == "api" for e in entries)


# ── check_processes ────────────────────────────────────────────────────────

def test_restart_emits_audit_entry(tmp_path: Path):
    sup, log = _make_supervisor(tmp_path, "db")
    dead = _fake_proc(False)
    alive = _fake_proc(True)
    sup._processes = {"db": dead}

    def _flip_to_alive():
        sup._processes["db"] = alive

    with patch("procwatch.supervisor.Supervisor.check_processes", side_effect=_flip_to_alive):
        sup.check_processes()

    entries = log.read_all()
    assert any(e.action == "restart" and e.process == "db" for e in entries)


def test_no_restart_entry_when_process_stays_alive(tmp_path: Path):
    sup, log = _make_supervisor(tmp_path, "cache")
    proc = _fake_proc(True)
    sup._processes = {"cache": proc}

    with patch("procwatch.supervisor.Supervisor.check_processes"):
        sup.check_processes()

    entries = log.read_all()
    assert not any(e.action == "restart" for e in entries)


def test_actor_stored_in_entries(tmp_path: Path):
    sup, log = _make_supervisor(tmp_path, "web")
    sup._processes = {"web": _fake_proc(True)}
    with patch("procwatch.supervisor.Supervisor.stop_all"):
        sup.stop_all()
    entries = log.read_all()
    assert all(e.actor == "test" for e in entries)
