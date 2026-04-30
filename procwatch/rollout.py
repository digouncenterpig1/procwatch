"""Staged rollout support: restart processes in batches with a delay between each."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class RolloutConfig:
    batch_size: int = 1
    delay_seconds: float = 5.0
    max_failures: int = 1

    def __post_init__(self) -> None:
        if self.batch_size < 1:
            raise ValueError("batch_size must be >= 1")
        if self.delay_seconds < 0:
            raise ValueError("delay_seconds must be >= 0")
        if self.max_failures < 0:
            raise ValueError("max_failures must be >= 0")

    @classmethod
    def from_config(cls, data: dict) -> Optional["RolloutConfig"]:
        if not data:
            return None
        return cls(
            batch_size=int(data.get("batch_size", 1)),
            delay_seconds=float(data.get("delay_seconds", 5.0)),
            max_failures=int(data.get("max_failures", 1)),
        )


@dataclass
class RolloutResult:
    restarted: List[str] = field(default_factory=list)
    failed: List[str] = field(default_factory=list)
    aborted: bool = False

    def to_dict(self) -> dict:
        return {
            "restarted": self.restarted,
            "failed": self.failed,
            "aborted": self.aborted,
        }


def rollout(names: List[str], restart_fn, is_healthy_fn, config: RolloutConfig) -> RolloutResult:
    """Restart *names* in batches, aborting if too many failures accumulate."""
    result = RolloutResult()
    failures = 0
    batches = [names[i:i + config.batch_size] for i in range(0, len(names), config.batch_size)]

    for idx, batch in enumerate(batches):
        for name in batch:
            try:
                restart_fn(name)
                if is_healthy_fn(name):
                    result.restarted.append(name)
                else:
                    result.failed.append(name)
                    failures += 1
            except Exception:
                result.failed.append(name)
                failures += 1

            if failures > config.max_failures:
                result.aborted = True
                return result

        if idx < len(batches) - 1:
            time.sleep(config.delay_seconds)

    return result
