"""Per-process resource quota enforcement."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

log = logging.getLogger(__name__)


@dataclass
class QuotaConfig:
    max_cpu_percent: Optional[float] = None   # e.g. 80.0 means 80 %
    max_mem_mb: Optional[float] = None        # resident set size in MiB

    def __post_init__(self) -> None:
        if self.max_cpu_percent is not None and not (0 < self.max_cpu_percent <= 100):
            raise ValueError("max_cpu_percent must be in (0, 100]")
        if self.max_mem_mb is not None and self.max_mem_mb <= 0:
            raise ValueError("max_mem_mb must be positive")

    @classmethod
    def from_config(cls, cfg: dict) -> Optional["QuotaConfig"]:
        if not cfg:
            return None
        return cls(
            max_cpu_percent=cfg.get("max_cpu_percent"),
            max_mem_mb=cfg.get("max_mem_mb"),
        )


@dataclass
class QuotaViolation:
    process_name: str
    reason: str
    cpu_percent: Optional[float] = None
    mem_mb: Optional[float] = None

    def to_dict(self) -> dict:
        return {
            "process_name": self.process_name,
            "reason": self.reason,
            "cpu_percent": self.cpu_percent,
            "mem_mb": self.mem_mb,
        }


class QuotaChecker:
    """Check a ResourceSample against a QuotaConfig and report violations."""

    def check(self, name: str, sample, quota: QuotaConfig) -> Optional[QuotaViolation]:
        """Return a QuotaViolation if *sample* exceeds *quota*, else None."""
        if sample is None:
            return None

        if quota.max_cpu_percent is not None:
            if sample.cpu_percent is not None and sample.cpu_percent > quota.max_cpu_percent:
                log.warning(
                    "quota: %s cpu %.1f%% > limit %.1f%%",
                    name, sample.cpu_percent, quota.max_cpu_percent,
                )
                return QuotaViolation(
                    process_name=name,
                    reason="cpu",
                    cpu_percent=sample.cpu_percent,
                )

        if quota.max_mem_mb is not None:
            mem_mb = (sample.mem_rss or 0) / (1024 * 1024)
            if mem_mb > quota.max_mem_mb:
                log.warning(
                    "quota: %s mem %.1f MiB > limit %.1f MiB",
                    name, mem_mb, quota.max_mem_mb,
                )
                return QuotaViolation(
                    process_name=name,
                    reason="mem",
                    mem_mb=mem_mb,
                )

        return None
