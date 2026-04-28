"""Supervisor mixin that uses TagRouter to expose group-level operations."""
from __future__ import annotations

from typing import Dict, List, Optional

from procwatch.supervisor import Supervisor
from procwatch.tag_router import TagRouter


class TagSupervisor:
    """Wraps a Supervisor and provides group-aware start/stop/query."""

    def __init__(self, supervisor: Supervisor, router: Optional[TagRouter] = None) -> None:
        self._sv = supervisor
        self._router = router or TagRouter()
        self._tags: Dict[str, List[str]] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register_tags(self, process_name: str, tags: List[str]) -> List[str]:
        """Store tags for *process_name* and route it into groups."""
        self._tags[process_name] = list(tags)
        return self._router.route(process_name, tags)

    def add_rule(self, group: str, required_tags: List[str]) -> None:
        self._router.add_rule(group, required_tags)

    # ------------------------------------------------------------------
    # Group queries
    # ------------------------------------------------------------------

    def group(self, name: str) -> List[str]:
        """Return process names in *group*."""
        return self._router.group(name)

    def groups_for(self, process_name: str) -> List[str]:
        return self._router.groups_for(process_name)

    def all_groups(self) -> Dict[str, List[str]]:
        return self._router.all_groups()

    # ------------------------------------------------------------------
    # Group-level lifecycle
    # ------------------------------------------------------------------

    def stop_group(self, group: str) -> List[str]:
        """Stop every process in *group*; return names that were stopped."""
        stopped: List[str] = []
        for name in self._router.group(group):
            proc = self._sv._processes.get(name)
            if proc and proc.is_running():
                proc.stop()
                stopped.append(name)
        return stopped

    def running_in_group(self, group: str) -> List[str]:
        return [
            name
            for name in self._router.group(group)
            if (p := self._sv._processes.get(name)) and p.is_running()
        ]
