"""CLI reporter: prints a formatted metrics table to stdout."""

import sys
from typing import TextIO

from procwatch.metrics import MetricsRegistry


_HEADER = (
    f"{'NAME':<20} {'STARTS':>7} {'RESTARTS':>9} "
    f"{'EXIT':>5} {'UPTIME(s)':>10}"
)
_SEP = "-" * len(_HEADER)


def _fmt_row(d: dict) -> str:
    name = d["name"][:19]
    starts = d["start_count"]
    restarts = d["restart_count"]
    exit_code = d["last_exit_code"] if d["last_exit_code"] is not None else "-"
    uptime = f"{d['uptime_seconds']:.1f}"
    return f"{name:<20} {starts:>7} {restarts:>9} {exit_code!s:>5} {uptime:>10}"


def print_table(registry: MetricsRegistry, out: TextIO = sys.stdout) -> None:
    """Print a summary table of all process metrics."""
    rows = registry.summary()
    if not rows:
        out.write("No processes tracked yet.\n")
        return
    out.write(_HEADER + "\n")
    out.write(_SEP + "\n")
    for row in sorted(rows, key=lambda r: r["name"]):
        out.write(_fmt_row(row) + "\n")


def print_json(registry: MetricsRegistry, out: TextIO = sys.stdout) -> None:
    """Print metrics as JSON."""
    import json
    out.write(json.dumps(registry.summary(), indent=2) + "\n")


def report(registry: MetricsRegistry, fmt: str = "table", out: TextIO = sys.stdout) -> None:
    """Dispatch to the right formatter."""
    if fmt == "json":
        print_json(registry, out)
    else:
        print_table(registry, out)
