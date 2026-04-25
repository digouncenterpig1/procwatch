"""Per-process CPU and memory usage sampling."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

try:
    import psutil
except ImportError:  # pragma: no cover
    psutil = None  # type: ignore


@dataclass
class ResourceSample:
    timestamp: float
    cpu_percent: float
    rss_bytes: int

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "cpu_percent": self.cpu_percent,
            "rss_bytes": self.rss_bytes,
        }


@dataclass
class ResourceMonitor:
    """Collects resource samples for a single PID."""

    pid: int
    _samples: List[ResourceSample] = field(default_factory=list, init=False)
    _proc: object = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        if psutil is not None:
            try:
                self._proc = psutil.Process(self.pid)
                # prime the CPU counter
                self._proc.cpu_percent(interval=None)
            except psutil.NoSuchProcess:
                self._proc = None

    def sample(self) -> Optional[ResourceSample]:
        """Take one sample; returns None if the process is gone or psutil unavailable."""
        if self._proc is None:
            return None
        try:
            cpu = self._proc.cpu_percent(interval=None)
            mem = self._proc.memory_info().rss
        except Exception:
            return None
        s = ResourceSample(timestamp=time.time(), cpu_percent=cpu, rss_bytes=mem)
        self._samples.append(s)
        return s

    def latest(self) -> Optional[ResourceSample]:
        return self._samples[-1] if self._samples else None

    def all_samples(self) -> List[ResourceSample]:
        return list(self._samples)

    def average_cpu(self) -> float:
        if not self._samples:
            return 0.0
        return sum(s.cpu_percent for s in self._samples) / len(self._samples)

    def peak_rss(self) -> int:
        if not self._samples:
            return 0
        return max(s.rss_bytes for s in self._samples)

    def to_dict(self) -> Dict:
        return {
            "pid": self.pid,
            "sample_count": len(self._samples),
            "average_cpu_percent": round(self.average_cpu(), 2),
            "peak_rss_bytes": self.peak_rss(),
            "latest": self.latest().to_dict() if self.latest() else None,
        }
