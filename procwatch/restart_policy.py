"""Restart policy: decide whether and how a process should be restarted."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


_VALID_MODES = {"always", "on-failure", "never"}


@dataclass
class RestartPolicy:
    """Controls when a managed process is eligible for restart."""

    mode: str = "on-failure"          # always | on-failure | never
    max_restarts: int = 0             # 0 = unlimited
    allowed_exit_codes: list[int] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.mode not in _VALID_MODES:
            raise ValueError(
                f"Invalid restart mode {self.mode!r}. "
                f"Choose from: {sorted(_VALID_MODES)}"
            )
        if self.max_restarts < 0:
            raise ValueError("max_restarts must be >= 0")

    # ------------------------------------------------------------------
    @classmethod
    def from_config(cls, cfg: dict) -> Optional["RestartPolicy"]:
        """Build from a raw config dict; return None when dict is empty."""
        if not cfg:
            return None
        return cls(
            mode=cfg.get("mode", "on-failure"),
            max_restarts=int(cfg.get("max_restarts", 0)),
            allowed_exit_codes=list(cfg.get("allowed_exit_codes", [])),
        )

    # ------------------------------------------------------------------
    def should_restart(self, exit_code: int, restart_count: int) -> bool:
        """Return True if the process should be restarted."""
        if self.mode == "never":
            return False
        if self.max_restarts and restart_count >= self.max_restarts:
            return False
        if self.mode == "always":
            return True
        # on-failure: restart unless exit code is in the allowed set
        if self.allowed_exit_codes and exit_code in self.allowed_exit_codes:
            return False
        return exit_code != 0

    def to_dict(self) -> dict:
        return {
            "mode": self.mode,
            "max_restarts": self.max_restarts,
            "allowed_exit_codes": list(self.allowed_exit_codes),
        }
