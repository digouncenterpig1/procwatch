"""Tests for procwatch.runlog."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from procwatch.runlog import RunEntry, RunLog


@pytest.fixture()
def log_path(tmp_path: Path) -> Path:
    return tmp_path / "runs" / "run.jsonl"


@pytest.fixture()
def runlog(log_path: Path) -> RunLog:
    return RunLog(log_path)


def test_record_creates_file(runlog: RunLog, log_path: Path) -> None:
    runlog.record("web", "start", pid=123)
    assert log_path.exists()


def test_record_appends_jsonl(runlog: RunLog, log_path: Path) -> None:
    runlog.record("web", "start", pid=1)
    runlog.record("web", "stop", pid=1, exit_code=0)
    lines = log_path.read_text().strip().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["event"] == "start"
    assert json.loads(lines[1])["event"] == "stop"


def test_read_returns_entries(runlog: RunLog) -> None:
    runlog.record("db", "start", pid=42)
    entries = runlog.read()
    assert len(entries) == 1
    assert entries[0].process == "db"
    assert entries[0].event == "start"
    assert entries[0].pid == 42


def test_read_missing_file_returns_empty(log_path: Path) -> None:
    rl = RunLog(log_path)
    assert rl.read() == []


def test_iter_for_filters_by_process(runlog: RunLog) -> None:
    runlog.record("web", "start")
    runlog.record("db", "start")
    runlog.record("web", "stop")
    results = list(runlog.iter_for("web"))
    assert len(results) == 2
    assert all(e.process == "web" for e in results)


def test_exit_code_preserved(runlog: RunLog) -> None:
    runlog.record("worker", "crash", exit_code=1)
    entry = runlog.read()[0]
    assert entry.exit_code == 1


def test_timestamp_is_recent(runlog: RunLog) -> None:
    before = time.time()
    runlog.record("web", "start")
    after = time.time()
    entry = runlog.read()[0]
    assert before <= entry.timestamp <= after


def test_max_lines_rotation(log_path: Path) -> None:
    rl = RunLog(log_path, max_lines=5)
    for i in range(10):
        rl.record("svc", "start", pid=i)
    lines = log_path.read_text().strip().splitlines()
    assert len(lines) == 5
    # newest entries kept — last pid should be 9
    last = json.loads(lines[-1])
    assert last["pid"] == 9


def test_run_entry_round_trip() -> None:
    entry = RunEntry(process="x", event="start", timestamp=1.0, pid=5, exit_code=None)
    restored = RunEntry.from_dict(entry.to_dict())
    assert restored.process == entry.process
    assert restored.pid == entry.pid
    assert restored.exit_code is None


def test_extra_fields_preserved(runlog: RunLog) -> None:
    runlog.record("api", "restart", extra={"reason": "oom"})
    entry = runlog.read()[0]
    assert entry.extra.get("reason") == "oom"
