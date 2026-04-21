"""Supervisor mixin that integrates Watchdog with managed processes."""

from __future__ import annotations

import logging
from typing import Dict, Optional

from procwatch.supervisor import Supervisor
from procwatch.watchdog import Watchdog
from procwatch.config import WatchConfig

logger = logging.getLogger(__name__)

_DEFAULT_DEADLINE = 30.0  # seconds


class WatchdogSupervisor(Supervisor):
    """Supervisor that restarts processes that stop sending heartbeats."""

    def __init__(self, config: WatchConfig, watchdog_interval: float = 1.0) -> None:
        super().__init__(config)
        self._watchdog = Watchdog(interval=watchdog_interval)
        self._deadlines: Dict[str, float] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def heartbeat(self, name: str) -> None:
        """Signal that *name* is still alive; resets its watchdog timer."""
        self._watchdog.heartbeat(name)

    def set_deadline(self, name: str, deadline: float) -> None:
        """Override the watchdog deadline for a specific process."""
        self._deadlines[name] = deadline
        if name in self._processes:
            self._watchdog.register(name, deadline, self._on_timeout)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start_all(self) -> None:
        super().start_all()
        for name in self._processes:
            deadline = self._deadlines.get(name, _DEFAULT_DEADLINE)
            self._watchdog.register(name, deadline, self._on_timeout)
        self._watchdog.start()
        logger.debug("watchdog started for %d process(es)", len(self._processes))

    def stop_all(self) -> None:
        self._watchdog.stop()
        super().stop_all()
        logger.debug("watchdog stopped")

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _on_timeout(self, name: str) -> None:
        logger.warning("watchdog timeout for '%s' — restarting", name)
        proc = self._processes.get(name)
        if proc is None:
            return
        try:
            proc.stop()
        except Exception:  # noqa: BLE001
            pass
        proc.start()
        # reset heartbeat so the timer starts fresh after restart
        self._watchdog.heartbeat(name)
