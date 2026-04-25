"""Pretty-print circuit breaker state from a CBSupervisor."""
from __future__ import annotations

import json
import sys
from typing import TextIO

from procwatch.cb_supervisor import CBSupervisor

_COLS = ("process", "state", "threshold", "window", "recovery_timeout")
_WIDTH = 20


def _fmt_row(*cells: str, width: int = _WIDTH) -> str:
    return "  ".join(str(c).ljust(width) for c in cells)


def print_table(sup: CBSupervisor, out: TextIO = sys.stdout) -> None:
    """Print a human-readable table of breaker states."""
    print(_fmt_row(*_COLS), file=out)
    print("-" * (_WIDTH * len(_COLS) + 2 * (len(_COLS) - 1)), file=out)
    for name, info in sorted(sup.breaker_states().items()):
        print(
            _fmt_row(
                name,
                info["state"],
                str(info["failure_threshold"]),
                str(info["window"]),
                str(info["recovery_timeout"]),
            ),
            file=out,
        )


def print_json(sup: CBSupervisor, out: TextIO = sys.stdout) -> None:
    """Dump breaker states as JSON."""
    json.dump(sup.breaker_states(), out, indent=2)
    print(file=out)


def report(sup: CBSupervisor, fmt: str = "table", out: TextIO = sys.stdout) -> None:
    """Dispatch to the requested formatter."""
    if fmt == "json":
        print_json(sup, out)
    else:
        print_table(sup, out)
