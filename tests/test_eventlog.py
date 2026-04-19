"""Tests for procwatch.eventlog."""
import time

import pytest

from procwatch.eventlog import Event, EventLog, get_default, reset_default


def test_record_adds_event():
    log = EventLog()
    ev = log.record("web", "start")
    assert len(log) == 1
    assert ev.name == "web"
    assert ev.kind == "start"


def test_all_returns_list():
    log = EventLog()
    log.record("web", "start")
    log.record("worker", "crash")
    events = log.all()
    assert len(events) == 2
    assert isinstance(events, list)


def test_for_process_filters():
    log = EventLog()
    log.record("web", "start")
    log.record("worker", "crash")
    log.record("web", "stop")
    assert len(log.for_process("web")) == 2
    assert len(log.for_process("worker")) == 1


def test_since_filters_by_timestamp():
    log = EventLog()
    ev1 = log.record("web", "start")
    ev1.ts = 1000.0
    ev2 = log.record("web", "crash")
    ev2.ts = 2000.0
    result = log.since(1500.0)
    assert len(result) == 1
    assert result[0].kind == "crash"


def test_maxlen_evicts_old_events():
    log = EventLog(maxlen=3)
    for i in range(5):
        log.record("svc", "start")
    assert len(log) == 3


def test_clear_empties_log():
    log = EventLog()
    log.record("web", "start")
    log.clear()
    assert len(log) == 0


def test_event_to_dict():
    ev = Event(name="web", kind="crash", ts=999.0, detail="exit 1")
    d = ev.to_dict()
    assert d == {"name": "web", "kind": "crash", "ts": 999.0, "detail": "exit 1"}


def test_default_log_shared():
    reset_default()
    log = get_default()
    log.record("x", "start")
    assert len(get_default()) == 1


def test_reset_default_clears():
    get_default().record("x", "start")
    reset_default()
    assert len(get_default()) == 0


def test_iter_yields_events():
    log = EventLog()
    log.record("a", "start")
    log.record("b", "stop")
    kinds = [e.kind for e in log]
    assert kinds == ["start", "stop"]
