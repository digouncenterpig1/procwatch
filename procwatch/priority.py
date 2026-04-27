"""Process priority management — nice values and scheduling policies."""
from __future__ import annotations

import os
import logging
from dataclasses import dataclass, field
from typing import Optional

log = logging.getLogger(__name__)

VALID_POLICIES = {"other", "fifo", "rr", "batch", "idle"}


@dataclass
class PriorityConfig:
    nice: int = 0                          # -20 (highest) to 19 (lowest)
    ionice_class: int = 2                  # 1=RT, 2=best-effort, 3=idle
    ionice_level: int = 4                  # 0-7 within class
    policy: str = "other"                  # scheduling policy name

    def __post_init__(self) -> None:
        if not -20 <= self.nice <= 19:
            raise ValueError(f"nice must be -20..19, got {self.nice}")
        if self.policy not in VALID_POLICIES:
            raise ValueError(f"unknown policy {self.policy!r}")


def apply_nice(pid: int, nice: int) -> None:
    """Set the OS nice value for *pid*."""
    try:
        os.setpriority(os.PRIO_PROCESS, pid, nice)
        log.debug("set nice=%d for pid %d", nice, pid)
    except PermissionError:
        log.warning("no permission to set nice=%d for pid %d", nice, pid)
    except ProcessLookupError:
        log.warning("pid %d not found when applying nice", pid)


def apply_ionice(pid: int, ionice_class: int, ionice_level: int) -> None:
    """Best-effort ionice via /proc — silently skips on non-Linux."""
    try:
        import subprocess
        subprocess.run(
            ["ionice", "-c", str(ionice_class), "-n", str(ionice_level), "-p", str(pid)],
            check=False,
            capture_output=True,
        )
        log.debug("set ionice class=%d level=%d for pid %d", ionice_class, ionice_level, pid)
    except FileNotFoundError:
        log.debug("ionice binary not available, skipping")


def apply(pid: int, cfg: PriorityConfig) -> None:
    """Apply all priority settings in *cfg* to *pid*."""
    apply_nice(pid, cfg.nice)
    apply_ionice(pid, cfg.ionice_class, cfg.ionice_level)


def from_config(raw: dict) -> Optional[PriorityConfig]:
    """Build a PriorityConfig from a raw dict, or return None if empty."""
    if not raw:
        return None
    return PriorityConfig(
        nice=raw.get("nice", 0),
        ionice_class=raw.get("ionice_class", 2),
        ionice_level=raw.get("ionice_level", 4),
        policy=raw.get("policy", "other"),
    )
