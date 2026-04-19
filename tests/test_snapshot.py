"""Tests for snapshot + watcher."""
from __future__ import annotations

import time
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from procwatch.snapshot import ProcessSnapshot, SupervisorSnapshot, take_snapshot
from procwatch.watcher import SnapshotWatcher


def _fake_metrics(restart_count=2, exit_code=1, uptime=10.0):
    m = MagicMock()
    m.restart_count = restart_count
    m.last_exit_code = exit_code
    m.current_uptime.return_value = uptime
    return m


def _fake_supervisor(names=("web", "worker")):
    sup = MagicMock()
    sup.processes = {}
    sup.metrics = {}
    for name in names:
        proc = MagicMock()
        proc.pid.return_value = 1234
        proc.is_running.return_value = True
        sup.processes[name] = proc
        sup.metrics[name] = _fake_metrics()
    return sup


def test_take_snapshot_returns_all_processes():
    sup = _fake_supervisor(["a", "b", "c"])
    snap = take_snapshot(sup)
    assert len(snap.processes) == 3
    assert {p.name for p in snap.processes} == {"a", "b", "c"}


def test_process_snapshot_to_dict():
    ps = ProcessSnapshot(name="web", pid=42, running=True, restart_count=3,
                         exit_code=0, uptime=5.5)
    d = ps.to_dict()
    assert d["name"] == "web"
    assert d["pid"] == 42
    assert d["running"] is True
    assert d["restart_count"] == 3


def test_supervisor_snapshot_running_count():
    snaps = [
        ProcessSnapshot("a", 1, True, 0, None, 1.0),
        ProcessSnapshot("b", 2, False, 1, 1, 0.0),
        ProcessSnapshot("c", 3, True, 0, None, 2.0),
    ]
    ss = SupervisorSnapshot(processes=snaps)
    assert ss.running_count() == 2


def test_supervisor_snapshot_by_name():
    snaps = [ProcessSnapshot("x", 9, True, 0, None, 0.0)]
    ss = SupervisorSnapshot(processes=snaps)
    assert "x" in ss.by_name()


def test_watcher_collects_snapshots():
    sup = _fake_supervisor(["svc"])
    watcher = SnapshotWatcher(sup, interval=0.05)
    watcher.start()
    time.sleep(0.2)
    watcher.stop()
    assert len(watcher.history) >= 2


def test_watcher_callback_invoked():
    sup = _fake_supervisor(["svc"])
    received = []
    watcher = SnapshotWatcher(sup, interval=0.05)
    watcher.add_callback(received.append)
    watcher.start()
    time.sleep(0.15)
    watcher.stop()
    assert len(received) >= 1
    assert isinstance(received[0], SupervisorSnapshot)


def test_watcher_history_capped():
    sup = _fake_supervisor(["svc"])
    watcher = SnapshotWatcher(sup, interval=0.01)
    watcher._history_limit = 5
    watcher.start()
    time.sleep(0.15)
    watcher.stop()
    assert len(watcher.history) <= 5
