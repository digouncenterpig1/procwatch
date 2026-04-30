"""CLI reporter for probe health status."""
from __future__ import annotations

import json
from typing import Dict

from procwatch.probe import ProbeRunner, ProbeState

_COL_W = (20, 10, 8, 8, 14)


def _fmt_row(*cols: str) -> str:
    return "  ".join(str(c).ljust(w) for c, w in zip(cols, _COL_W))


def _state_to_dict(name: str, state: ProbeState) -> dict:
    return {
        "name": name,
        "healthy": state.healthy,
        "consecutive_successes": state.consecutive_successes,
        "consecutive_failures": state.consecutive_failures,
        "last_result": state.last_result,
    }


def print_table(runner: ProbeRunner, names: list[str]) -> None:
    header = _fmt_row("PROCESS", "HEALTHY", "OK_RUN", "FAIL", "LAST")
    print(header)
    print("-" * len(header))
    for name in names:
        state = runner.state_for(name)
        if state is None:
            continue
        last = "pass" if state.last_result else ("fail" if state.last_result is False else "n/a")
        print(
            _fmt_row(
                name,
                "yes" if state.healthy else "no",
                str(state.consecutive_successes),
                str(state.consecutive_failures),
                last,
            )
        )


def print_json(runner: ProbeRunner, names: list[str]) -> None:
    rows = []
    for name in names:
        state = runner.state_for(name)
        if state is not None:
            rows.append(_state_to_dict(name, state))
    print(json.dumps(rows, indent=2))


def report(runner: ProbeRunner, names: list[str], fmt: str = "table") -> None:
    if fmt == "json":
        print_json(runner, names)
    else:
        print_table(runner, names)
