"""Dependency-aware start/stop helpers for the Supervisor.

This module wraps a Supervisor and a DependencyGraph to provide ordered
start_all / stop_all that respect declared process dependencies.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from procwatch.dependency import DependencyGraph, from_config

if TYPE_CHECKING:
    from procwatch.supervisor import Supervisor

log = logging.getLogger(__name__)


class DepSupervisor:
    """Thin wrapper around Supervisor that honours dependency order."""

    def __init__(self, supervisor: "Supervisor") -> None:
        self._sv = supervisor
        self._graph: DependencyGraph = from_config(
            list(self._sv._configs.values())
            if hasattr(self._sv, "_configs")
            else []
        )

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    def start_all(self) -> None:
        """Start processes in dependency-safe order."""
        try:
            order = self._graph.start_order()
        except Exception as exc:  # CyclicDependencyError or similar
            log.error("Cannot determine start order: %s", exc)
            raise

        processes = self._sv._processes  # type: ignore[attr-defined]
        for name in order:
            proc = processes.get(name)
            if proc is None:
                continue
            log.debug("dep_supervisor: starting %s", name)
            proc.start()

    def stop_all(self) -> None:
        """Stop processes in reverse dependency order."""
        try:
            order = self._graph.stop_order()
        except Exception as exc:
            log.error("Cannot determine stop order: %s", exc)
            raise

        processes = self._sv._processes  # type: ignore[attr-defined]
        for name in order:
            proc = processes.get(name)
            if proc is None:
                continue
            log.debug("dep_supervisor: stopping %s", name)
            proc.stop()

    def start_order(self):
        """Expose the computed start order (useful for tests / CLI)."""
        return self._graph.start_order()

    def stop_order(self):
        """Expose the computed stop order."""
        return self._graph.stop_order()
