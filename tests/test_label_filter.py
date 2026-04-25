"""Tests for procwatch.label_filter."""
from __future__ import annotations

import pytest
from dataclasses import dataclass, field
from typing import Dict

from procwatch.label_filter import LabelFilter, label_names, parse_selector


@dataclass
class _FakeProc:
    name: str
    labels: Dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# parse_selector
# ---------------------------------------------------------------------------

def test_parse_selector_single_pair():
    assert parse_selector("env=prod") == {"env": "prod"}


def test_parse_selector_multiple_pairs():
    result = parse_selector("env=prod,team=backend")
    assert result == {"env": "prod", "team": "backend"}


def test_parse_selector_empty_string_returns_empty():
    assert parse_selector("") == {}
    assert parse_selector("   ") == {}


def test_parse_selector_missing_equals_raises():
    with pytest.raises(ValueError, match="Invalid label selector token"):
        parse_selector("env")


def test_parse_selector_empty_key_raises():
    with pytest.raises(ValueError, match="Empty key"):
        parse_selector("=value")


# ---------------------------------------------------------------------------
# LabelFilter.matches
# ---------------------------------------------------------------------------

def test_empty_selector_matches_anything():
    f = LabelFilter()
    assert f.matches({}) is True
    assert f.matches({"env": "prod"}) is True


def test_exact_match():
    f = LabelFilter({"env": "prod"})
    assert f.matches({"env": "prod"}) is True


def test_subset_match():
    f = LabelFilter({"env": "prod"})
    assert f.matches({"env": "prod", "team": "backend"}) is True


def test_wrong_value_does_not_match():
    f = LabelFilter({"env": "prod"})
    assert f.matches({"env": "staging"}) is False


def test_missing_key_does_not_match():
    f = LabelFilter({"env": "prod"})
    assert f.matches({"team": "backend"}) is False


# ---------------------------------------------------------------------------
# LabelFilter.filter
# ---------------------------------------------------------------------------

def test_filter_returns_matching_subset():
    procs = [
        _FakeProc("a", {"env": "prod"}),
        _FakeProc("b", {"env": "staging"}),
        _FakeProc("c", {"env": "prod", "team": "backend"}),
    ]
    result = LabelFilter({"env": "prod"}).filter(procs)
    assert [p.name for p in result] == ["a", "c"]


def test_filter_empty_selector_returns_all():
    procs = [_FakeProc("a"), _FakeProc("b")]
    assert LabelFilter().filter(procs) == procs


def test_filter_no_matches_returns_empty():
    procs = [_FakeProc("a", {"env": "staging"})]
    assert LabelFilter({"env": "prod"}).filter(procs) == []


# ---------------------------------------------------------------------------
# label_names
# ---------------------------------------------------------------------------

def test_label_names_collects_all_keys():
    procs = [
        _FakeProc("a", {"env": "prod"}),
        _FakeProc("b", {"team": "backend"}),
    ]
    assert label_names(procs) == {"env", "team"}


def test_label_names_empty_returns_empty_set():
    assert label_names([]) == set()
