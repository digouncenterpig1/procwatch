"""Point-in-time snapshot of all supervised process states."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ProcessSnapshot:
    name: str
    pid: Optional[int]
    running: bool
    restart_count: int
    exit_code: Optional[int]
    uptime: float
    taken_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "pid": self.pid,
            "running": self.running,
            "restart_count": self.restart_count,
            "exit_code": self.exit_code,
            "uptime": round(self.uptime, 3),
            "taken_at": self.taken_at,
        }


@dataclass
class SupervisorSnapshot:
    processes: List[ProcessSnapshot] = field(default_factory=list)
    taken_at: float = field(default_factory=time.time)

    def by_name(self) -> Dict[str, ProcessSnapshot]:
        return {p.name: p for p in self.processes}

    def running_count(self) -> int:
        return sum(1 for p in self.processes if p.running)

    def to_dict(self) -> dict:
        return {
            "taken_at": self.taken_at,
            "running": self.running_count(),
            "total": len(self.processes),
            "processes": [p.to_dict() for p in self.processes],
        }


def take_snapshot(supervisor) -> SupervisorSnapshot:
    """Build a SupervisorSnapshot from a live Supervisor instance."""
    snaps = []
    for name, proc in supervisor.processes.items():
        metrics = supervisor.metrics.get(name)
        snaps.append(ProcessSnapshot(
            name=name,
            pid=proc.pid(),
            running=proc.is_running(),
            restart_count=metrics.restart_count if metrics else 0,
            exit_code=metrics.last_exit_code if metrics else None,
            uptime=metrics.current_uptime() if metrics else 0.0,
        ))
    return SupervisorSnapshot(processes=snaps)
