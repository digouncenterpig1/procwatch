"""Manages ResourceMonitor instances across all supervised processes."""
from __future__ import annotations

from typing import Dict, List, Optional

from procwatch.resource_monitor import ResourceMonitor, ResourceSample


class ResourcePool:
    """Tracks one ResourceMonitor per named process."""

    def __init__(self) -> None:
        self._monitors: Dict[str, ResourceMonitor] = {}

    def register(self, name: str, pid: int) -> ResourceMonitor:
        """Create (or replace) a monitor for *name* with the given *pid*."""
        monitor = ResourceMonitor(pid=pid)
        self._monitors[name] = monitor
        return monitor

    def unregister(self, name: str) -> None:
        self._monitors.pop(name, None)

    def sample_all(self) -> Dict[str, Optional[ResourceSample]]:
        """Take a sample from every registered monitor."""
        return {name: mon.sample() for name, mon in self._monitors.items()}

    def get(self, name: str) -> Optional[ResourceMonitor]:
        return self._monitors.get(name)

    def names(self) -> List[str]:
        return list(self._monitors.keys())

    def summary(self) -> List[dict]:
        """Return to_dict for every tracked process, sorted by name."""
        return [
            {"name": name, **mon.to_dict()}
            for name, mon in sorted(self._monitors.items())
        ]
