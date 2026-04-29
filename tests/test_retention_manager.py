"""Tests for procwatch.retention_manager."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from procwatch.retention import RetentionPolicy
from procwatch.retention_manager import RetentionManager

NOW = 1_000_000.0


def _write_jsonl(path: Path, entries: list) -> None:
    path.write_text("".join(json.dumps(e) + "\n" for e in entries))


def _read_jsonl(path: Path) -> list:
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def test_register_and_policy_for_default(tmp_path):
    mgr = RetentionManager(default_policy=RetentionPolicy(max_entries=5))
    p = tmp_path / "a.jsonl"
    p.touch()
    mgr.register("a", p)
    assert mgr.policy_for("a").max_entries == 5


def test_register_with_override(tmp_path):
    mgr = RetentionManager(default_policy=RetentionPolicy(max_entries=5))
    p = tmp_path / "b.jsonl"
    p.touch()
    override = RetentionPolicy(max_entries=2)
    mgr.register("b", p, policy=override)
    assert mgr.policy_for("b").max_entries == 2


def test_prune_unknown_name_raises(tmp_path):
    mgr = RetentionManager()
    with pytest.raises(KeyError):
        mgr.prune("ghost")


def test_prune_removes_old_entries(tmp_path):
    mgr = RetentionManager(default_policy=RetentionPolicy(max_age_seconds=10))
    p = tmp_path / "events.jsonl"
    _write_jsonl(p, [
        {"timestamp": NOW - 100, "msg": "stale"},
        {"timestamp": NOW - 3, "msg": "fresh"},
    ])
    mgr.register("events", p)
    removed = mgr.prune("events", now=NOW)
    assert removed == 1
    assert _read_jsonl(p)[0]["msg"] == "fresh"


def test_prune_all_returns_dict(tmp_path):
    mgr = RetentionManager(default_policy=RetentionPolicy(max_age_seconds=10))
    for name in ("x", "y"):
        p = tmp_path / f"{name}.jsonl"
        _write_jsonl(p, [{"timestamp": NOW - 50, "v": name}])
        mgr.register(name, p)
    result = mgr.prune_all(now=NOW)
    assert set(result.keys()) == {"x", "y"}
    assert result["x"] == 1
    assert result["y"] == 1


def test_registered_names(tmp_path):
    mgr = RetentionManager()
    for n in ("alpha", "beta", "gamma"):
        p = tmp_path / f"{n}.jsonl"
        p.touch()
        mgr.register(n, p)
    assert sorted(mgr.registered_names()) == ["alpha", "beta", "gamma"]


def test_prune_missing_file_returns_zero(tmp_path):
    mgr = RetentionManager(default_policy=RetentionPolicy(max_age_seconds=60))
    p = tmp_path / "missing.jsonl"  # intentionally not created
    mgr.register("missing", p)
    assert mgr.prune("missing", now=NOW) == 0
