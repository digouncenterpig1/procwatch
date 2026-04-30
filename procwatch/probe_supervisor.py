"""Supervisor mixin that runs readiness/liveness probes and acts on failures."""
from __future__ import annotations

import logging
from typing import Callable, Dict, Optional

from procwatch.probe import ProbeConfig, ProbeRunner
from procwatch.supervisor import Supervisor

log = logging.getLogger(__name__)


class ProbeSupervisor:
    """Wraps a Supervisor and periodically probes each process.

    Unhealthy processes are restarted according to the supervisor's normal
    restart logic (i.e., stop + let check_processes handle the restart).
    """

    def __init__(
        self,
        supervisor: Supervisor,
        probe_fn: Optional[Callable[[str, float], bool]] = None,
    ) -> None:
        self._sup = supervisor
        self._runner = ProbeRunner()
        # probe_fn(name, timeout) -> bool; defaults to always-healthy stub
        self._probe_fn: Callable[[str, float], bool] = probe_fn or (lambda _n, _t: True)
        self._configs: Dict[str, ProbeConfig] = {}

    # ------------------------------------------------------------------
    # configuration
    # ------------------------------------------------------------------

    def set_probe(self, name: str, config: ProbeConfig) -> None:
        self._configs[name] = config
        self._runner.register(name, config)

    def remove_probe(self, name: str) -> None:
        self._configs.pop(name, None)
        self._runner.unregister(name)

    # ------------------------------------------------------------------
    # delegation
    # ------------------------------------------------------------------

    def start_all(self) -> None:
        self._sup.start_all()

    def stop_all(self) -> None:
        self._sup.stop_all()

    # ------------------------------------------------------------------
    # probe tick — call this from your main loop
    # ------------------------------------------------------------------

    def tick(self) -> None:
        """Run probes for processes whose interval has elapsed."""
        for name, cfg in list(self._configs.items()):
            if not cfg.enabled:
                continue
            if not self._runner.due(name):
                continue
            proc = self._sup._procs.get(name)
            if proc is None or not proc.is_running():
                continue
            try:
                ok = self._probe_fn(name, cfg.timeout)
            except Exception as exc:  # noqa: BLE001
                log.warning("probe for %s raised: %s", name, exc)
                ok = False

            changed = self._runner.record(name, ok)
            if changed:
                if not self._runner.is_healthy(name):
                    log.warning("process %s marked unhealthy — stopping for restart", name)
                    proc.stop()
                else:
                    log.info("process %s recovered and is now healthy", name)

    def is_healthy(self, name: str) -> bool:
        return self._runner.is_healthy(name)

    def health_summary(self) -> Dict[str, bool]:
        return {name: self._runner.is_healthy(name) for name in self._configs}
