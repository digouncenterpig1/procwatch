"""Supervisor mixin that enforces resource quotas and kills violating processes."""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

from procwatch.quota import QuotaChecker, QuotaConfig, QuotaViolation
from procwatch.resource_monitor import ResourceMonitor
from procwatch.resource_pool import ResourcePool
from procwatch.supervisor import Supervisor

log = logging.getLogger(__name__)


class QuotaSupervisor:
    """Wraps a Supervisor and kills processes that breach their resource quota."""

    def __init__(self, supervisor: Supervisor, pool: ResourcePool) -> None:
        self._sv = supervisor
        self._pool = pool
        self._quotas: Dict[str, QuotaConfig] = {}
        self._checker = QuotaChecker()
        self._violations: List[QuotaViolation] = []

    # ------------------------------------------------------------------
    # configuration
    # ------------------------------------------------------------------

    def set_quota(self, name: str, quota: QuotaConfig) -> None:
        self._quotas[name] = quota

    def quota_for(self, name: str) -> Optional[QuotaConfig]:
        return self._quotas.get(name)

    # ------------------------------------------------------------------
    # delegation
    # ------------------------------------------------------------------

    def start_all(self) -> None:
        self._sv.start_all()

    def stop_all(self) -> None:
        self._sv.stop_all()

    # ------------------------------------------------------------------
    # quota enforcement
    # ------------------------------------------------------------------

    def check_quotas(self) -> List[QuotaViolation]:
        """Sample all monitored processes; kill and record any violators."""
        new_violations: List[QuotaViolation] = []

        for name, monitor in self._pool.monitors.items():
            quota = self._quotas.get(name)
            if quota is None:
                continue

            sample = monitor.sample()
            violation = self._checker.check(name, sample, quota)
            if violation is None:
                continue

            new_violations.append(violation)
            self._violations.append(violation)

            proc = self._sv._processes.get(name)
            if proc is not None and proc.is_running():
                log.error(
                    "quota_supervisor: killing %s due to %s violation",
                    name, violation.reason,
                )
                try:
                    proc._proc.kill()
                except Exception as exc:  # noqa: BLE001
                    log.debug("kill failed for %s: %s", name, exc)

        return new_violations

    @property
    def all_violations(self) -> List[QuotaViolation]:
        return list(self._violations)
