"""Tests for procwatch.logrotate."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from procwatch.logrotate import LogRotator, RotateConfig


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _make_rotator(tmp_path: Path, max_bytes: int = 100, backup_count: int = 3) -> LogRotator:
    log_file = tmp_path / "app.log"
    cfg = RotateConfig(max_bytes=max_bytes, backup_count=backup_count)
    return LogRotator(log_file, cfg)


# ---------------------------------------------------------------------------
# tests
# ---------------------------------------------------------------------------

def test_should_rotate_false_when_small(tmp_path):
    r = _make_rotator(tmp_path)
    r.path.write_bytes(b"tiny")
    assert r.should_rotate() is False


def test_should_rotate_true_when_large(tmp_path):
    r = _make_rotator(tmp_path, max_bytes=10)
    r.path.write_bytes(b"x" * 20)
    assert r.should_rotate() is True


def test_should_rotate_false_when_missing(tmp_path):
    r = _make_rotator(tmp_path)
    assert r.should_rotate() is False


def test_should_rotate_false_when_disabled(tmp_path):
    r = _make_rotator(tmp_path, max_bytes=1)
    r.cfg.enabled = False
    r.path.write_bytes(b"x" * 200)
    assert r.should_rotate() is False


def test_rotate_creates_backup(tmp_path):
    r = _make_rotator(tmp_path)
    r.path.write_bytes(b"original")
    r.rotate()
    assert not r.path.exists()
    assert Path(f"{r.path}.1").read_bytes() == b"original"


def test_rotate_shifts_existing_backups(tmp_path):
    r = _make_rotator(tmp_path, backup_count=3)
    r.path.write_bytes(b"new")
    Path(f"{r.path}.1").write_bytes(b"old1")
    Path(f"{r.path}.2").write_bytes(b"old2")
    r.rotate()
    assert Path(f"{r.path}.1").read_bytes() == b"new"
    assert Path(f"{r.path}.2").read_bytes() == b"old1"
    assert Path(f"{r.path}.3").read_bytes() == b"old2"


def test_rotate_drops_oldest_when_at_limit(tmp_path):
    r = _make_rotator(tmp_path, backup_count=2)
    r.path.write_bytes(b"new")
    Path(f"{r.path}.1").write_bytes(b"b1")
    Path(f"{r.path}.2").write_bytes(b"b2")
    r.rotate()
    assert not Path(f"{r.path}.3").exists()
    assert Path(f"{r.path}.2").read_bytes() == b"b1"


def test_maybe_rotate_returns_true_when_rotated(tmp_path):
    r = _make_rotator(tmp_path, max_bytes=5)
    r.path.write_bytes(b"x" * 10)
    assert r.maybe_rotate() is True


def test_maybe_rotate_returns_false_when_not_needed(tmp_path):
    r = _make_rotator(tmp_path, max_bytes=1000)
    r.path.write_bytes(b"small")
    assert r.maybe_rotate() is False


def test_open_log_creates_file(tmp_path):
    r = _make_rotator(tmp_path)
    with r.open_log() as fh:
        fh.write(b"hello")
    assert r.path.read_bytes() == b"hello"


def test_open_log_rotates_if_needed(tmp_path):
    r = _make_rotator(tmp_path, max_bytes=3)
    r.path.write_bytes(b"xxxx")  # exceeds max
    with r.open_log() as fh:
        fh.write(b"new")
    assert Path(f"{r.path}.1").exists()
