"""Tests for procwatch.pidfile."""

import os
import pytest
from pathlib import Path

from procwatch.pidfile import PidFile, PidFileError


def test_acquire_writes_current_pid(tmp_path):
    p = tmp_path / "proc.pid"
    pf = PidFile(p)
    pf.acquire()
    assert p.exists()
    assert int(p.read_text().strip()) == os.getpid()
    pf.release()


def test_release_removes_file(tmp_path):
    p = tmp_path / "proc.pid"
    pf = PidFile(p)
    pf.acquire()
    pf.release()
    assert not p.exists()


def test_context_manager(tmp_path):
    p = tmp_path / "proc.pid"
    with PidFile(p):
        assert p.exists()
    assert not p.exists()


def test_stale_pid_file_is_overwritten(tmp_path):
    p = tmp_path / "proc.pid"
    # Write a PID that almost certainly doesn't exist
    p.write_text("9999999\n")
    pf = PidFile(p)
    pf.acquire()  # should not raise
    assert int(p.read_text().strip()) == os.getpid()
    pf.release()


def test_active_pid_raises(tmp_path):
    p = tmp_path / "proc.pid"
    # Write our own PID as if another instance acquired it
    p.write_text(str(os.getpid()) + "\n")
    pf = PidFile(p)
    # Trick: _pid is None so release won't clean up; but acquire should raise
    with pytest.raises(PidFileError, match="already running"):
        pf.acquire()
    p.unlink()  # cleanup


def test_read_pid_returns_none_when_missing(tmp_path):
    p = tmp_path / "no.pid"
    pf = PidFile(p)
    assert pf.read_pid() is None


def test_read_pid_returns_value(tmp_path):
    p = tmp_path / "proc.pid"
    p.write_text("1234\n")
    pf = PidFile(p)
    assert pf.read_pid() == 1234


def test_creates_parent_directories(tmp_path):
    p = tmp_path / "run" / "sub" / "proc.pid"
    with PidFile(p):
        assert p.exists()
