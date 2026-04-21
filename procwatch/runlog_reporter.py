"""CLI-friendly reporting helpers for RunLog data."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from typing import Optional

from procwatch.runlog import RunLog


def _fmt_ts(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def summary(runlog: RunLog, process: Optional[str] = None) -> dict:
    """Return per-process event counts and last-seen timestamp."""
    entries = runlog.read()
    if process:
        entries = [e for e in entries if e.process == process]

    stats: dict[str, dict] = defaultdict(lambda: {"starts": 0, "stops": 0, "crashes": 0, "restarts": 0, "last_seen": None})
    for e in entries:
        s = stats[e.process]
        key = e.event if e.event in ("starts", "stops", "crashes", "restarts") else e.event + "s"
        if key in s:
            s[key] += 1
        if s["last_seen"] is None or e.timestamp > s["last_seen"]:
            s["last_seen"] = e.timestamp

    return dict(stats)


def print_table(runlog: RunLog, process: Optional[str] = None, limit: int = 20) -> None:
    entries = runlog.read()
    if process:
        entries = [e for e in entries if e.process == process]
    entries = entries[-limit:]

    header = f"{'TIME':<22} {'PROCESS':<16} {'EVENT':<10} {'PID':<8} {'EXIT':>4}"
    print(header)
    print("-" * len(header))
    for e in entries:
        pid_s = str(e.pid) if e.pid is not None else "-"
        exit_s = str(e.exit_code) if e.exit_code is not None else "-"
        print(f"{_fmt_ts(e.timestamp):<22} {e.process:<16} {e.event:<10} {pid_s:<8} {exit_s:>4}")


def print_json(runlog: RunLog, process: Optional[str] = None, limit: int = 20) -> None:
    entries = runlog.read()
    if process:
        entries = [e for e in entries if e.process == process]
    entries = entries[-limit:]
    print(json.dumps([e.to_dict() for e in entries], indent=2))


def print_summary(runlog: RunLog, process: Optional[str] = None) -> None:
    data = summary(runlog, process)
    header = f"{'PROCESS':<20} {'STARTS':>7} {'STOPS':>7} {'CRASHES':>8} {'RESTARTS':>9} {'LAST SEEN':<22}"
    print(header)
    print("-" * len(header))
    for name, s in sorted(data.items()):
        last = _fmt_ts(s["last_seen"]) if s["last_seen"] else "-"
        print(f"{name:<20} {s['starts']:>7} {s['stops']:>7} {s['crashes']:>8} {s['restarts']:>9} {last:<22}")
