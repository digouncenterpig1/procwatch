"""Tests for TagRouter and TagSupervisor."""
from unittest.mock import MagicMock

import pytest

from procwatch.tag_router import TagRule, TagRouter
from procwatch.tag_supervisor import TagSupervisor


# ---------------------------------------------------------------------------
# TagRule
# ---------------------------------------------------------------------------

def test_rule_matches_when_all_tags_present():
    rule = TagRule(group="web", required_tags=["http", "public"])
    assert rule.matches(["http", "public", "extra"]) is True


def test_rule_does_not_match_when_tag_missing():
    rule = TagRule(group="web", required_tags=["http", "public"])
    assert rule.matches(["http"]) is False


def test_rule_with_no_required_tags_always_matches():
    rule = TagRule(group="all")
    assert rule.matches([]) is True
    assert rule.matches(["anything"]) is True


# ---------------------------------------------------------------------------
# TagRouter
# ---------------------------------------------------------------------------

def test_route_assigns_to_matching_group():
    r = TagRouter()
    r.add_rule("web", ["http"])
    groups = r.route("nginx", ["http", "public"])
    assert "web" in groups


def test_route_skips_non_matching_group():
    r = TagRouter()
    r.add_rule("db", ["postgres"])
    groups = r.route("nginx", ["http"])
    assert "db" not in groups


def test_route_assigns_multiple_groups():
    r = TagRouter()
    r.add_rule("web", ["http"])
    r.add_rule("public", ["public"])
    groups = r.route("nginx", ["http", "public"])
    assert set(groups) == {"web", "public"}


def test_group_returns_members():
    r = TagRouter()
    r.add_rule("web", ["http"])
    r.route("nginx", ["http"])
    r.route("caddy", ["http"])
    assert set(r.group("web")) == {"nginx", "caddy"}


def test_remove_drops_from_all_groups():
    r = TagRouter()
    r.add_rule("web", ["http"])
    r.add_rule("public", ["public"])
    r.route("nginx", ["http", "public"])
    r.remove("nginx")
    assert "nginx" not in r.group("web")
    assert "nginx" not in r.group("public")


def test_groups_for_returns_correct_groups():
    r = TagRouter()
    r.add_rule("web", ["http"])
    r.add_rule("all", [])
    r.route("nginx", ["http"])
    assert set(r.groups_for("nginx")) == {"web", "all"}


# ---------------------------------------------------------------------------
# TagSupervisor
# ---------------------------------------------------------------------------

def _make_tag_supervisor():
    sv = MagicMock()
    sv._processes = {}
    ts = TagSupervisor(sv)
    ts.add_rule("web", ["http"])
    return ts, sv


def test_register_tags_routes_process():
    ts, _ = _make_tag_supervisor()
    groups = ts.register_tags("nginx", ["http"])
    assert "web" in groups


def test_stop_group_stops_running_processes():
    ts, sv = _make_tag_supervisor()
    proc = MagicMock()
    proc.is_running.return_value = True
    sv._processes["nginx"] = proc
    ts.register_tags("nginx", ["http"])
    stopped = ts.stop_group("web")
    assert "nginx" in stopped
    proc.stop.assert_called_once()


def test_stop_group_skips_already_stopped():
    ts, sv = _make_tag_supervisor()
    proc = MagicMock()
    proc.is_running.return_value = False
    sv._processes["nginx"] = proc
    ts.register_tags("nginx", ["http"])
    stopped = ts.stop_group("web")
    assert stopped == []


def test_running_in_group_filters_correctly():
    ts, sv = _make_tag_supervisor()
    p1 = MagicMock()
    p1.is_running.return_value = True
    p2 = MagicMock()
    p2.is_running.return_value = False
    sv._processes["nginx"] = p1
    sv._processes["caddy"] = p2
    ts.register_tags("nginx", ["http"])
    ts.register_tags("caddy", ["http"])
    running = ts.running_in_group("web")
    assert running == ["nginx"]
