"""Supervisor mixin that writes an audit entry for every lifecycle event."""
from __future__ import annotations

from typing import Optional

from procwatch.audit import AuditLog
from procwatch.supervisor import Supervisor


class AuditSupervisor(Supervisor):
    """Wraps Supervisor and emits audit entries on start / stop / restart."""

    def __init__(self, config, audit_log: AuditLog, actor: str = "supervisor") -> None:
        super().__init__(config)
        self._audit = audit_log
        self._actor = actor

    # ------------------------------------------------------------------
    def start_all(self) -> None:
        super().start_all()
        for name in self._processes:
            self._audit.record("start", name, actor=self._actor)

    def stop_all(self) -> None:
        for name in list(self._processes):
            self._audit.record("stop", name, actor=self._actor)
        super().stop_all()

    def check_processes(self) -> None:
        """Restart dead processes and emit an audit entry for each restart."""
        before = {
            name: proc.is_running()
            for name, proc in self._processes.items()
        }
        super().check_processes()
        after = {
            name: proc.is_running()
            for name, proc in self._processes.items()
        }
        for name in self._processes:
            was_dead = not before.get(name, True)
            is_live = after.get(name, False)
            if was_dead and is_live:
                self._audit.record(
                    "restart", name, actor="supervisor",
                    detail="process was dead; restarted",
                )
