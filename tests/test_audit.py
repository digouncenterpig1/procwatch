"""Tests for procwatch.audit and procwatch.audit_reporter."""
from __future__ import annotations

import json
from io import StringIO
from pathlib import Path

import pytest

from procwatch.audit import AuditEntry, AuditLog
from procwatch.audit_reporter import report


@pytest.fixture()
def log_path(tmp_path: Path) -> Path:
    return tmp_path / "audit.jsonl"


@pytest.fixture()
def audit(log_path: Path) -> AuditLog:
    return AuditLog(log_path)


# ── AuditEntry ─────────────────────────────────────────────────────────────

def test_entry_to_dict_contains_required_keys():
    e = AuditEntry(action="start", process="web", actor="operator")
    d = e.to_dict()
    assert {"action", "process", "actor", "timestamp", "detail"} == set(d.keys())


def test_entry_roundtrip():
    e = AuditEntry(action="stop", process="worker", actor="supervisor", detail="exit 1")
    assert AuditEntry.from_dict(e.to_dict()) == e


# ── AuditLog.record ────────────────────────────────────────────────────────

def test_record_creates_file(audit: AuditLog, log_path: Path):
    audit.record("start", "web")
    assert log_path.exists()


def test_record_appends_jsonl(audit: AuditLog, log_path: Path):
    audit.record("start", "web")
    audit.record("stop", "web", detail="exit 0")
    lines = log_path.read_text().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["action"] == "start"
    assert json.loads(lines[1])["detail"] == "exit 0"


def test_read_all_returns_entries(audit: AuditLog):
    audit.record("reload", "api", actor="signal")
    entries = audit.read_all()
    assert len(entries) == 1
    assert entries[0].actor == "signal"


def test_tail_returns_last_n(audit: AuditLog):
    for i in range(10):
        audit.record("start", f"proc{i}")
    t = audit.tail(3)
    assert len(t) == 3
    assert t[-1].process == "proc9"


def test_maxlen_evicts_old_entries(log_path: Path):
    log = AuditLog(log_path, maxlen=5)
    for i in range(8):
        log.record("start", f"p{i}")
    assert len(log.tail(100)) == 5


def test_read_all_missing_file(audit: AuditLog):
    assert audit.read_all() == []


# ── audit_reporter ─────────────────────────────────────────────────────────

def test_report_table(audit: AuditLog):
    audit.record("start", "web", actor="operator")
    buf = StringIO()
    report(audit, fmt="table", file=buf)
    out = buf.getvalue()
    assert "start" in out and "web" in out


def test_report_json(audit: AuditLog):
    audit.record("kill", "db", detail="oom")
    buf = StringIO()
    report(audit, fmt="json", file=buf)
    data = json.loads(buf.getvalue())
    assert data[0]["action"] == "kill"


def test_report_csv(audit: AuditLog):
    audit.record("stop", "cache")
    buf = StringIO()
    report(audit, fmt="csv", file=buf)
    lines = buf.getvalue().strip().splitlines()
    assert lines[0].startswith("timestamp")
    assert "stop" in lines[1]


def test_report_tail_limits_output(audit: AuditLog):
    for i in range(10):
        audit.record("start", f"p{i}")
    buf = StringIO()
    report(audit, fmt="json", tail=3, file=buf)
    data = json.loads(buf.getvalue())
    assert len(data) == 3
