"""Process namespace support for grouping and isolating managed processes.

Allows processes to be organized into named namespaces, enabling
scoped operations like start/stop/status for a subset of processes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, Iterator, List, Optional

DEFAULT_NAMESPACE = "default"


@dataclass
class Namespace:
    """A named group of process names."""

    name: str
    process_names: List[str] = field(default_factory=list)

    def add(self, process_name: str) -> None:
        """Register a process under this namespace."""
        if process_name not in self.process_names:
            self.process_names.append(process_name)

    def remove(self, process_name: str) -> None:
        """Remove a process from this namespace (no-op if absent)."""
        try:
            self.process_names.remove(process_name)
        except ValueError:
            pass

    def __contains__(self, process_name: str) -> bool:
        return process_name in self.process_names

    def __iter__(self) -> Iterator[str]:
        return iter(self.process_names)

    def __len__(self) -> int:
        return len(self.process_names)


class NamespaceRegistry:
    """Registry that maps process names to their namespace.

    Each process belongs to exactly one namespace.  Processes that are
    not explicitly assigned land in the DEFAULT_NAMESPACE.
    """

    def __init__(self) -> None:
        self._namespaces: Dict[str, Namespace] = {}
        # Reverse index: process_name -> namespace_name
        self._index: Dict[str, str] = {}

    # ------------------------------------------------------------------
    # Mutation helpers
    # ------------------------------------------------------------------

    def register(self, process_name: str, namespace: str = DEFAULT_NAMESPACE) -> None:
        """Assign *process_name* to *namespace*, moving it if necessary."""
        current = self._index.get(process_name)
        if current and current != namespace:
            # Remove from old namespace before reassigning
            self._namespaces[current].remove(process_name)

        ns = self._namespaces.setdefault(namespace, Namespace(namespace))
        ns.add(process_name)
        self._index[process_name] = namespace

    def unregister(self, process_name: str) -> None:
        """Remove *process_name* from the registry entirely."""
        ns_name = self._index.pop(process_name, None)
        if ns_name and ns_name in self._namespaces:
            self._namespaces[ns_name].remove(process_name)

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def namespace_of(self, process_name: str) -> Optional[str]:
        """Return the namespace name for *process_name*, or None."""
        return self._index.get(process_name)

    def get(self, namespace: str) -> Optional[Namespace]:
        """Return the :class:`Namespace` object, or None if unknown."""
        return self._namespaces.get(namespace)

    def processes_in(self, namespace: str) -> List[str]:
        """Return a list of process names belonging to *namespace*."""
        ns = self._namespaces.get(namespace)
        return list(ns) if ns else []

    def all_namespaces(self) -> List[str]:
        """Return sorted list of all known namespace names."""
        return sorted(self._namespaces.keys())

    def filter_names(self, names: Iterable[str], namespace: str) -> List[str]:
        """Return only those *names* that belong to *namespace*."""
        members = set(self.processes_in(namespace))
        return [n for n in names if n in members]

    def __repr__(self) -> str:  # pragma: no cover
        parts = ", ".join(
            f"{ns}={list(obj)}" for ns, obj in self._namespaces.items()
        )
        return f"NamespaceRegistry({parts})"
