"""Process dependency ordering — ensures processes start/stop in correct order."""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Dict, List, Set


class CyclicDependencyError(Exception):
    """Raised when a dependency cycle is detected."""


@dataclass
class DependencyGraph:
    """Directed graph of process dependencies."""

    _deps: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))

    def add(self, name: str, depends_on: List[str]) -> None:
        """Register that *name* depends on each entry in *depends_on*."""
        for dep in depends_on:
            self._deps[name].add(dep)
        # Ensure every node exists even if it has no deps
        if name not in self._deps:
            self._deps[name] = set()

    def start_order(self) -> List[str]:
        """Return process names in dependency-safe start order (topological sort).

        Raises CyclicDependencyError if a cycle exists.
        """
        return _topo_sort(self._deps)

    def stop_order(self) -> List[str]:
        """Return process names in reverse start order (safe shutdown)."""
        return list(reversed(self.start_order()))

    def dependencies_of(self, name: str) -> Set[str]:
        """Return direct dependencies for *name*."""
        return set(self._deps.get(name, set()))


def _topo_sort(deps: Dict[str, Set[str]]) -> List[str]:
    """Kahn's algorithm — raises CyclicDependencyError on cycle."""
    in_degree: Dict[str, int] = {n: 0 for n in deps}
    reverse: Dict[str, List[str]] = defaultdict(list)

    for node, predecessors in deps.items():
        for pred in predecessors:
            if pred not in in_degree:
                in_degree[pred] = 0
            reverse[pred].append(node)
            in_degree[node] = in_degree.get(node, 0)

    # Recount properly
    in_degree = {n: 0 for n in deps}
    for node, predecessors in deps.items():
        for pred in predecessors:
            in_degree[node] += 1

    queue: deque[str] = deque(n for n, d in in_degree.items() if d == 0)
    order: List[str] = []

    while queue:
        node = queue.popleft()
        order.append(node)
        for dependent in reverse[node]:
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                queue.append(dependent)

    if len(order) != len(in_degree):
        raise CyclicDependencyError(
            "Cycle detected among processes: "
            + str(set(in_degree) - set(order))
        )
    return order


def from_config(process_configs) -> DependencyGraph:
    """Build a DependencyGraph from a list of ProcessConfig objects."""
    graph = DependencyGraph()
    for cfg in process_configs:
        depends_on = getattr(cfg, "depends_on", []) or []
        graph.add(cfg.name, depends_on)
    return graph
