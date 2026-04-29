"""Tests for procwatch.retention."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

import pytest

from procwatch.retention import (
    RetentionPolicy,
    apply_policy,
    prune_by_age,
    prune_by_count,
    prune_jsonl_file,
)


@dataclass
class _E:
    timestamp: float
    name: str


NOW = 1_000_000.0


def test_policy_rejects_zero_age():
    with pytest.raises(ValueError):
        RetentionPolicy(max_age_seconds=0)


def test_policy_rejects_zero_entries():
    with pytest.raises(ValueError):
        RetentionPolicy(max_entries=0)


def test_prune_by_age_keeps_recent():
    entries = [_E(NOW - 10, "a"), _E(NOW - 5, "b"), _E(NOW - 1, "c")]
    policy = RetentionPolicy(max_age_seconds=6)
    result = prune_by_age(entries, policy, now=NOW)
    assert [e.name for e in result] == ["b", "c"]


def test_prune_by_age_no_limit_keeps_all():
    entries = [_E(0, "old"), _E(NOW, "new")]
    policy = RetentionPolicy()
    assert prune_by_age(entries, policy, now=NOW) == entries


def test_prune_by_count_keeps_last_n():
    entries = [_E(float(i), str(i)) for i in range(10)]
    policy = RetentionPolicy(max_entries=3)
    result = prune_by_count(entries, policy)
    assert [e.name for e in result] == ["7", "8", "9"]


def test_apply_policy_combines_both():
    entries = [_E(NOW - 100, "old"), _E(NOW - 2, "a"), _E(NOW - 1, "b"), _E(NOW, "c")]
    policy = RetentionPolicy(max_age_seconds=10, max_entries=2)
    result = apply_policy(entries, policy, now=NOW)
    assert [e.name for e in result] == ["b", "c"]


def test_prune_jsonl_file_removes_old(tmp_path):
    p = tmp_path / "run.jsonl"
    lines = [
        {"timestamp": NOW - 200, "msg": "old"},
        {"timestamp": NOW - 5, "msg": "recent"},
        {"timestamp": NOW - 1, "msg": "newest"},
    ]
    p.write_text("".join(json.dumps(l) + "\n" for l in lines))
    removed = prune_jsonl_file(p, RetentionPolicy(max_age_seconds=10), now=NOW)
    assert removed == 1
    remaining = [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
    assert len(remaining) == 2
    assert remaining[0]["msg"] == "recent"


def test_prune_jsonl_missing_file_returns_zero(tmp_path):
    p = tmp_path / "nope.jsonl"
    assert prune_jsonl_file(p, RetentionPolicy(max_age_seconds=60)) == 0


def test_from_config_builds_policy():
    p = RetentionPolicy.from_config({"max_age_seconds": 3600, "max_entries": 100})
    assert p.max_age_seconds == 3600
    assert p.max_entries == 100
