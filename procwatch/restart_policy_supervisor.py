"""Supervisor mixin that gates restarts through RestartPolicy."""
from __future__ import annotations

from typing import Dict, Optional

from procwatch.config import WatchConfig
from procwatch.metrics import ProcessMetrics
from procwatch.restart_policy import RestartPolicy
from procwatch.supervisor import Supervisor


class RestartPolicySupervisor(Supervisor):
    """Extends Supervisor to honour per-process RestartPolicy rules."""

    def __init__(self, config: WatchConfig) -> None:
        super().__init__(config)
        self._policies: Dict[str, Optional[RestartPolicy]] = {}
        self._metrics: Dict[str, ProcessMetrics] = {}
        self._load_policies()

    # ------------------------------------------------------------------
    def _load_policies(self) -> None:
        for pcfg in self.config.processes:
            raw = getattr(pcfg, "restart_policy", {}) or {}
            self._policies[pcfg.name] = RestartPolicy.from_config(raw)
            self._metrics[pcfg.name] = ProcessMetrics(pcfg.name)

    # ------------------------------------------------------------------
    def check_processes(self) -> None:
        """Override: only restart when the policy permits it."""
        for name, proc in list(self.processes.items()):
            if proc.is_running():
                continue

            exit_code = proc.returncode() if hasattr(proc, "returncode") else 1
            metrics = self._metrics.get(name)
            restart_count = metrics.restart_count if metrics else 0
            policy = self._policies.get(name)

            if policy is None or policy.should_restart(exit_code, restart_count):
                proc.start()
                if metrics:
                    metrics.record_start()

    # ------------------------------------------------------------------
    def policy_for(self, name: str) -> Optional[RestartPolicy]:
        return self._policies.get(name)

    def policy_states(self) -> dict:
        return {
            name: (p.to_dict() if p else None)
            for name, p in self._policies.items()
        }
