"""Tests for procwatch.signal_handler."""

import signal
import threading
import time

import pytest

from procwatch.signal_handler import SignalHandler


@pytest.fixture(autouse=True)
def restore_signals():
    """Always restore default signal handlers after each test."""
    yield
    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(sig, signal.SIG_DFL)


def test_install_and_uninstall_do_not_raise():
    h = SignalHandler()
    h.install()
    h.uninstall()


def test_stop_callback_called_on_sigterm():
    called = []
    h = SignalHandler()
    h.on_stop(lambda: called.append("stop"))
    h.install()

    signal.raise_signal(signal.SIGTERM)

    assert called == ["stop"]


def test_stop_callback_called_on_sigint():
    called = []
    h = SignalHandler()
    h.on_stop(lambda: called.append("int"))
    h.install()

    signal.raise_signal(signal.SIGINT)

    assert called == ["int"]


def test_reload_callback_called_on_sighup():
    called = []
    h = SignalHandler()
    h.on_reload(lambda: called.append("reload"))
    h.install()

    signal.raise_signal(signal.SIGHUP)

    assert called == ["reload"]


def test_no_callback_registered_does_not_raise():
    h = SignalHandler()
    h.install()
    # Neither on_stop nor on_reload registered — should be safe.
    signal.raise_signal(signal.SIGHUP)
    signal.raise_signal(signal.SIGTERM)


def test_shutdown_event_set_after_sigterm():
    h = SignalHandler()
    h.install()

    signal.raise_signal(signal.SIGTERM)

    assert h._shutdown_event.is_set()


def test_wait_for_shutdown_unblocks():
    h = SignalHandler()
    h.install()

    result = []

    def _waiter():
        h.wait_for_shutdown()
        result.append("done")

    t = threading.Thread(target=_waiter, daemon=True)
    t.start()
    time.sleep(0.05)
    signal.raise_signal(signal.SIGTERM)
    t.join(timeout=1.0)

    assert result == ["done"]
