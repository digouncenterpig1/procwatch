"""Simple in-memory metrics collection for monitored processes."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class ProcessMetrics:
    name: str
    start_count: int = 0
    restart_count: int = 0
    last_started: Optional[datetime] = None
    last_stopped: Optional[datetime] = None
    last_exit_code: Optional[int] = None
    uptime_seconds: float = 0.0
    _start_time: Optional[datetime] = field(default=None, repr=False)

    def record_start(self) -> None:
        now = datetime.utcnow()
        self.start_count += 1
        if self.start_count > 1:
            self.restart_count += 1
        self.last_started = now
        self._start_time = now

    def record_stop(self, exit_code: Optional[int] = None) -> None:
        now = datetime.utcnow()
        self.last_stopped = now
        self.last_exit_code = exit_code
        if self._start_time is not None:
            self.uptime_seconds += (now - self._start_time).total_seconds()
            self._start_time = None

    def current_uptime(self) -> float:
        if self._start_time is None:
            return self.uptime_seconds
        return self.uptime_seconds + (datetime.utcnow() - self._start_time).total_seconds()

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "start_count": self.start_count,
            "restart_count": self.restart_count,
            "last_started": self.last_started.isoformat() if self.last_started else None,
            "last_stopped": self.last_stopped.isoformat() if self.last_stopped else None,
            "last_exit_code": self.last_exit_code,
            "uptime_seconds": self.current_uptime(),
        }


class MetricsRegistry:
    def __init__(self) -> None:
        self._metrics: Dict[str, ProcessMetrics] = {}

    def get(self, name: str) -> ProcessMetrics:
        if name not in self._metrics:
            self._metrics[name] = ProcessMetrics(name=name)
        return self._metrics[name]

    def all(self) -> List[ProcessMetrics]:
        return list(self._metrics.values())

    def summary(self) -> List[dict]:
        return [m.to_dict() for m in self._metrics.values()]
