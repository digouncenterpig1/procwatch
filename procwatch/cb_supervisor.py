"""Supervisor mixin that gates restarts through a per-process CircuitBreaker."""
from __future__ import annotations

import logging
from typing import Dict

from procwatch.circuit_breaker import CircuitBreaker
from procwatch.supervisor import Supervisor

log = logging.getLogger(__name__)


class CBSupervisor(Supervisor):
    """Extends :class:`Supervisor` with per-process circuit breakers.

    Each managed process gets its own :class:`CircuitBreaker`.  When the
    breaker is open ``check_processes`` skips the restart and logs a warning
    instead of spawning the child again.
    """

    def __init__(self, config, *, failure_threshold: int = 5,
                 window: float = 60.0, recovery_timeout: float = 30.0) -> None:
        super().__init__(config)
        self._cb_kwargs = dict(
            failure_threshold=failure_threshold,
            window=window,
            recovery_timeout=recovery_timeout,
        )
        self._breakers: Dict[str, CircuitBreaker] = {}

    def _breaker(self, name: str) -> CircuitBreaker:
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(**self._cb_kwargs)
        return self._breakers[name]

    def check_processes(self) -> None:  # type: ignore[override]
        """Restart dead processes unless their circuit breaker is open."""
        for name, proc in list(self._processes.items()):
            if proc.is_running():
                self._breaker(name).record_success()
                continue
            exit_code = proc.returncode()
            cb = self._breaker(name)
            cb.record_failure()
            if not cb.allow_restart():
                log.warning(
                    "circuit breaker OPEN for %s (state=%s) — skipping restart",
                    name, cb.state.value,
                )
                continue
            log.info("restarting process %s (exit_code=%s)", name, exit_code)
            new_proc = self._make_process(self._config_map[name])
            new_proc.start()
            self._processes[name] = new_proc

    def breaker_states(self) -> dict:
        """Return a snapshot of all breaker states keyed by process name."""
        return {name: cb.to_dict() for name, cb in self._breakers.items()}
