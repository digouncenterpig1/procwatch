"""RetentionManager wires RetentionPolicy to the run-log and event-log."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional

from procwatch.retention import RetentionPolicy, apply_policy, prune_jsonl_file

log = logging.getLogger(__name__)


@dataclass
class RetentionManager:
    """Applies retention policies to tracked JSONL log files."""
    default_policy: RetentionPolicy = field(default_factory=RetentionPolicy)
    _overrides: Dict[str, RetentionPolicy] = field(default_factory=dict, init=False)
    _files: Dict[str, Path] = field(default_factory=dict, init=False)

    def register(self, name: str, path: Path, policy: Optional[RetentionPolicy] = None) -> None:
        """Track *path* under *name* with an optional per-file policy override."""
        self._files[name] = path
        if policy is not None:
            self._overrides[name] = policy

    def policy_for(self, name: str) -> RetentionPolicy:
        return self._overrides.get(name, self.default_policy)

    def prune(self, name: str, now: Optional[float] = None) -> int:
        """Prune a single registered file; returns lines removed."""
        if name not in self._files:
            raise KeyError(f"unknown log name: {name!r}")
        path = self._files[name]
        policy = self.policy_for(name)
        removed = prune_jsonl_file(path, policy, now=now)
        if removed:
            log.debug("retention: pruned %d entries from %s", removed, path)
        return removed

    def prune_all(self, now: Optional[float] = None) -> Dict[str, int]:
        """Prune every registered file; returns {name: lines_removed}."""
        ts = now if now is not None else time.time()
        return {name: self.prune(name, now=ts) for name in list(self._files)}

    def registered_names(self) -> list:
        return list(self._files.keys())
