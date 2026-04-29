"""Log and run-history retention policy: prune old entries by age or count."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class RetentionPolicy:
    """Defines how long / how many records to keep."""
    max_age_seconds: Optional[float] = None   # None → no age limit
    max_entries: Optional[int] = None         # None → no count limit

    def __post_init__(self) -> None:
        if self.max_age_seconds is not None and self.max_age_seconds <= 0:
            raise ValueError("max_age_seconds must be positive")
        if self.max_entries is not None and self.max_entries <= 0:
            raise ValueError("max_entries must be positive")

    @classmethod
    def from_config(cls, cfg: dict) -> "RetentionPolicy":
        return cls(
            max_age_seconds=cfg.get("max_age_seconds"),
            max_entries=cfg.get("max_entries"),
        )


def prune_by_age(entries: list, policy: RetentionPolicy, now: Optional[float] = None) -> list:
    """Return entries whose *timestamp* field is within the age window."""
    if policy.max_age_seconds is None:
        return list(entries)
    cutoff = (now if now is not None else time.time()) - policy.max_age_seconds
    return [e for e in entries if getattr(e, "timestamp", 0) >= cutoff]


def prune_by_count(entries: list, policy: RetentionPolicy) -> list:
    """Return at most *max_entries* most-recent entries (assumes chronological order)."""
    if policy.max_entries is None:
        return list(entries)
    return entries[-policy.max_entries:]


def apply_policy(entries: list, policy: RetentionPolicy, now: Optional[float] = None) -> list:
    """Apply age pruning then count pruning."""
    result = prune_by_age(entries, policy, now=now)
    result = prune_by_count(result, policy)
    return result


def prune_jsonl_file(path: Path, policy: RetentionPolicy, now: Optional[float] = None) -> int:
    """Rewrite a .jsonl file applying retention; returns number of lines removed."""
    import json

    if not path.exists():
        return 0

    raw = path.read_text().splitlines()
    parsed = []
    for line in raw:
        line = line.strip()
        if not line:
            continue
        try:
            parsed.append(json.loads(line))
        except json.JSONDecodeError:
            pass

    kept = []
    ts_now = now if now is not None else time.time()
    if policy.max_age_seconds is not None:
        cutoff = ts_now - policy.max_age_seconds
        parsed = [d for d in parsed if d.get("timestamp", 0) >= cutoff]
    if policy.max_entries is not None:
        parsed = parsed[-policy.max_entries:]

    removed = len(raw) - len(parsed)
    path.write_text("".join(json.dumps(d) + "\n" for d in parsed))
    return removed
