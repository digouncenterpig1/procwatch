"""Graceful signal handling for the procwatch daemon."""

import logging
import signal
import threading
from typing import Callable, Optional

log = logging.getLogger(__name__)

_HANDLED = (signal.SIGTERM, signal.SIGINT, signal.SIGHUP)


class SignalHandler:
    """Installs OS signal handlers and routes them to registered callbacks."""

    def __init__(self) -> None:
        self._stop_cb: Optional[Callable[[], None]] = None
        self._reload_cb: Optional[Callable[[], None]] = None
        self._shutdown_event = threading.Event()

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def on_stop(self, cb: Callable[[], None]) -> None:
        """Register a callback invoked on SIGTERM / SIGINT."""
        self._stop_cb = cb

    def on_reload(self, cb: Callable[[], None]) -> None:
        """Register a callback invoked on SIGHUP (config reload)."""
        self._reload_cb = cb

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def install(self) -> None:
        """Attach this handler to the process signal table."""
        signal.signal(signal.SIGTERM, self._handle_stop)
        signal.signal(signal.SIGINT, self._handle_stop)
        signal.signal(signal.SIGHUP, self._handle_reload)
        log.debug("signal handlers installed (SIGTERM, SIGINT, SIGHUP)")

    def uninstall(self) -> None:
        """Restore default signal dispositions."""
        for sig in _HANDLED:
            signal.signal(sig, signal.SIG_DFL)
        log.debug("signal handlers restored to defaults")

    def wait_for_shutdown(self) -> None:
        """Block the calling thread until a stop signal is received."""
        self._shutdown_event.wait()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _handle_stop(self, signum: int, _frame) -> None:  # type: ignore[type-arg]
        name = signal.Signals(signum).name
        log.info("received %s — initiating shutdown", name)
        self._shutdown_event.set()
        if self._stop_cb is not None:
            self._stop_cb()

    def _handle_reload(self, signum: int, _frame) -> None:  # type: ignore[type-arg]
        log.info("received SIGHUP — reloading configuration")
        if self._reload_cb is not None:
            self._reload_cb()
