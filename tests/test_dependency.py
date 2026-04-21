"""Tests for procwatch.dependency."""
import pytest

from procwatch.dependency import (
    CyclicDependencyError,
    DependencyGraph,
    _topo_sort,
    from_config,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

class _FakeCfg:
    def __init__(self, name, depends_on=None):
        self.name = name
        self.depends_on = depends_on or []


# ---------------------------------------------------------------------------
# DependencyGraph.add / dependencies_of
# ---------------------------------------------------------------------------

def test_add_registers_dependencies():
    g = DependencyGraph()
    g.add("web", ["db", "cache"])
    assert g.dependencies_of("web") == {"db", "cache"}


def test_no_dependencies_returns_empty_set():
    g = DependencyGraph()
    g.add("worker", [])
    assert g.dependencies_of("worker") == set()


def test_unknown_process_returns_empty_set():
    g = DependencyGraph()
    assert g.dependencies_of("ghost") == set()


# ---------------------------------------------------------------------------
# start_order
# ---------------------------------------------------------------------------

def test_start_order_independent_processes():
    g = DependencyGraph()
    g.add("a", [])
    g.add("b", [])
    order = g.start_order()
    assert set(order) == {"a", "b"}


def test_start_order_respects_dependency():
    g = DependencyGraph()
    g.add("db", [])
    g.add("web", ["db"])
    order = g.start_order()
    assert order.index("db") < order.index("web")


def test_start_order_chain():
    g = DependencyGraph()
    g.add("a", [])
    g.add("b", ["a"])
    g.add("c", ["b"])
    order = g.start_order()
    assert order.index("a") < order.index("b") < order.index("c")


# ---------------------------------------------------------------------------
# stop_order
# ---------------------------------------------------------------------------

def test_stop_order_is_reversed_start_order():
    g = DependencyGraph()
    g.add("db", [])
    g.add("web", ["db"])
    assert g.stop_order() == list(reversed(g.start_order()))


# ---------------------------------------------------------------------------
# cycle detection
# ---------------------------------------------------------------------------

def test_cycle_raises():
    g = DependencyGraph()
    g.add("a", ["b"])
    g.add("b", ["a"])
    with pytest.raises(CyclicDependencyError):
        g.start_order()


def test_self_loop_raises():
    g = DependencyGraph()
    g.add("a", ["a"])
    with pytest.raises(CyclicDependencyError):
        g.start_order()


# ---------------------------------------------------------------------------
# from_config
# ---------------------------------------------------------------------------

def test_from_config_builds_graph():
    cfgs = [
        _FakeCfg("db"),
        _FakeCfg("web", depends_on=["db"]),
    ]
    g = from_config(cfgs)
    order = g.start_order()
    assert order.index("db") < order.index("web")


def test_from_config_no_depends_on_attr():
    class _Bare:
        name = "solo"

    g = from_config([_Bare()])
    assert "solo" in g.start_order()
