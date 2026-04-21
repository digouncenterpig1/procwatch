"""Tests for procwatch.watchdog."""

import threading
import time

import pytest

from procwatch.watchdog import Watchdog


def test_no_callback_before_deadline():
    fired = []
    wd = Watchdog(interval=0.05)
    wd.register("svc", deadline=10.0, callback=lambda n: fired.append(n))
    wd.start()
    time.sleep(0.15)
    wd.stop()
    assert fired == []


def test_callback_fires_after_deadline():
    fired = []
    event = threading.Event()

    def cb(name):
        fired.append(name)
        event.set()

    wd = Watchdog(interval=0.05)
    wd.register("svc", deadline=0.1, callback=cb)
    wd.start()
    assert event.wait(timeout=1.0), "callback never fired"
    wd.stop()
    assert "svc" in fired


def test_heartbeat_resets_timer():
    fired = []
    wd = Watchdog(interval=0.05)
    wd.register("svc", deadline=0.15, callback=lambda n: fired.append(n))
    wd.start()
    # keep sending heartbeats so deadline never expires
    for _ in range(6):
        time.sleep(0.05)
        wd.heartbeat("svc")
    wd.stop()
    assert fired == []


def test_callback_fires_only_once_per_timeout():
    fired = []
    wd = Watchdog(interval=0.05)
    wd.register("svc", deadline=0.1, callback=lambda n: fired.append(n))
    wd.start()
    time.sleep(0.5)
    wd.stop()
    assert fired.count("svc") == 1


def test_heartbeat_after_fire_allows_second_trigger():
    fired = []
    event = threading.Event()

    def cb(name):
        fired.append(name)
        event.set()

    wd = Watchdog(interval=0.05)
    wd.register("svc", deadline=0.1, callback=cb)
    wd.start()
    assert event.wait(timeout=1.0)
    # reset by sending a heartbeat
    event.clear()
    wd.heartbeat("svc")
    assert event.wait(timeout=1.0), "second callback never fired"
    wd.stop()
    assert fired.count("svc") >= 2


def test_unregister_stops_monitoring():
    fired = []
    wd = Watchdog(interval=0.05)
    wd.register("svc", deadline=0.1, callback=lambda n: fired.append(n))
    wd.unregister("svc")
    wd.start()
    time.sleep(0.4)
    wd.stop()
    assert fired == []


def test_multiple_processes_independent():
    fired = []
    event = threading.Event()

    def cb(name):
        fired.append(name)
        event.set()

    wd = Watchdog(interval=0.05)
    wd.register("fast", deadline=0.1, callback=cb)
    wd.register("slow", deadline=10.0, callback=cb)
    wd.start()
    assert event.wait(timeout=1.0)
    wd.stop()
    assert "fast" in fired
    assert "slow" not in fired
