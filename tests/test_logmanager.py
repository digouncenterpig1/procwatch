"""Tests for procwatch.logmanager."""

from __future__ import annotations

from pathlib import Path

import pytest

from procwatch.logmanager import LogManager
from procwatch.logrotate import RotateConfig


def _manager(tmp_path: Path, max_bytes: int = 10_000) -> LogManager:
    cfg = RotateConfig(max_bytes=max_bytes, backup_count=2)
    return LogManager(log_dir=tmp_path / "logs", rotate_cfg=cfg)


def test_get_handles_creates_files(tmp_path):
    mgr = _manager(tmp_path)
    out, err = mgr.get_handles("myapp")
    out.write(b"stdout data")
    err.write(b"stderr data")
    out.close()
    err.close()

    stdout_path, stderr_path = mgr.log_paths("myapp")
    assert stdout_path.read_bytes() == b"stdout data"
    assert stderr_path.read_bytes() == b"stderr data"


def test_get_handles_creates_subdirectory(tmp_path):
    mgr = _manager(tmp_path)
    out, err = mgr.get_handles("svc")
    out.close()
    err.close()
    assert (tmp_path / "logs" / "svc").is_dir()


def test_log_paths_returns_correct_paths(tmp_path):
    mgr = _manager(tmp_path)
    out_p, err_p = mgr.log_paths("worker")
    assert out_p.name == "stdout.log"
    assert err_p.name == "stderr.log"
    assert out_p.parent.name == "worker"


def test_rotate_all_empty_when_nothing_tracked(tmp_path):
    mgr = _manager(tmp_path)
    assert mgr.rotate_all() == {}


def test_rotate_all_rotates_oversized_logs(tmp_path):
    mgr = _manager(tmp_path, max_bytes=5)
    out, err = mgr.get_handles("app")
    out.close()
    err.close()

    # Manually bloat the log files
    stdout_path, stderr_path = mgr.log_paths("app")
    stdout_path.write_bytes(b"x" * 20)
    stderr_path.write_bytes(b"y" * 20)

    rotated = mgr.rotate_all()
    assert "app" in rotated
    assert len(rotated["app"]) == 2


def test_rotate_all_skips_small_logs(tmp_path):
    mgr = _manager(tmp_path, max_bytes=10_000)
    out, err = mgr.get_handles("app")
    out.write(b"tiny")
    err.write(b"tiny")
    out.close()
    err.close()

    rotated = mgr.rotate_all()
    assert rotated == {}


def test_multiple_processes_tracked_independently(tmp_path):
    mgr = _manager(tmp_path, max_bytes=5)
    for name in ("alpha", "beta"):
        o, e = mgr.get_handles(name)
        o.close()
        e.close()

    # Only bloat alpha
    p, _ = mgr.log_paths("alpha")
    p.write_bytes(b"x" * 100)

    rotated = mgr.rotate_all()
    assert "alpha" in rotated
    assert "beta" not in rotated
