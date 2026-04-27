"""Supervisor mixin that applies PriorityConfig after each process start."""
from __future__ import annotations

import logging
from typing import Dict, Optional

from procwatch.supervisor import Supervisor
from procwatch.priority import PriorityConfig, apply, from_config

log = logging.getLogger(__name__)


class PrioritySupervisor(Supervisor):
    """Extends Supervisor to honour per-process priority settings."""

    def __init__(self, watch_config) -> None:  # type: ignore[override]
        super().__init__(watch_config)
        self._priority_cfgs: Dict[str, Optional[PriorityConfig]] = {}
        for pcfg in watch_config.processes:
            raw = getattr(pcfg, "priority", {}) or {}
            self._priority_cfgs[pcfg.name] = from_config(raw)

    # ------------------------------------------------------------------
    def _apply_priority(self, name: str) -> None:
        cfg = self._priority_cfgs.get(name)
        if cfg is None:
            return
        proc = self.processes.get(name)
        if proc is None:
            return
        pid = proc.pid
        if pid is None:
            log.debug("no pid yet for %s, skipping priority", name)
            return
        log.info("applying priority cfg to %s (pid=%d)", name, pid)
        apply(pid, cfg)

    # ------------------------------------------------------------------
    def start_all(self) -> None:
        super().start_all()
        for name in self.processes:
            self._apply_priority(name)

    def check_processes(self) -> None:
        """Restart dead processes then re-apply priority to any freshly started one."""
        before = {n: p.pid for n, p in self.processes.items()}
        super().check_processes()
        for name, proc in self.processes.items():
            if proc.pid and proc.pid != before.get(name):
                log.debug("%s was restarted, reapplying priority", name)
                self._apply_priority(name)
