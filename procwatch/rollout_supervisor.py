"""Supervisor mixin that performs staged rollouts when reloading config."""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

from procwatch.rollout import RolloutConfig, RolloutResult, rollout
from procwatch.supervisor import Supervisor

log = logging.getLogger(__name__)


class RolloutSupervisor:
    """Wraps a Supervisor and adds staged-rollout restart capability."""

    def __init__(self, supervisor: Supervisor, default_config: Optional[RolloutConfig] = None) -> None:
        self._sup = supervisor
        self._default = default_config or RolloutConfig()
        self._configs: Dict[str, RolloutConfig] = {}

    def set_rollout_config(self, name: str, config: RolloutConfig) -> None:
        self._configs[name] = config

    def config_for(self, name: str) -> RolloutConfig:
        return self._configs.get(name, self._default)

    def rolling_restart(self, names: Optional[List[str]] = None) -> RolloutResult:
        """Restart the given processes (or all) using their rollout configs."""
        if names is None:
            names = list(self._sup.processes.keys())

        if not names:
            return RolloutResult()

        # Use the config of the first named process for batch/delay settings.
        cfg = self.config_for(names[0])

        def _restart(name: str) -> None:
            proc = self._sup.processes.get(name)
            if proc is not None:
                proc.stop()
            self._sup.processes[name] = self._sup._make_process(self._sup._configs[name])
            self._sup.processes[name].start()
            log.info("rollout: restarted %s", name)

        def _healthy(name: str) -> bool:
            proc = self._sup.processes.get(name)
            return proc is not None and proc.is_running()

        result = rollout(names, _restart, _healthy, cfg)
        if result.aborted:
            log.warning("rollout aborted after %d failure(s): %s", len(result.failed), result.failed)
        return result

    # Delegate common supervisor methods.
    def start_all(self) -> None:
        self._sup.start_all()

    def stop_all(self) -> None:
        self._sup.stop_all()

    def check_processes(self) -> None:
        self._sup.check_processes()
