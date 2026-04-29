"""Reporting helpers for quota violations."""
from __future__ import annotations

import json
from typing import List

from procwatch.quota import QuotaViolation


_HEADERS = ("process", "reason", "cpu_%", "mem_mib")


def _fmt_row(v: QuotaViolation) -> tuple:
    cpu = f"{v.cpu_percent:.1f}" if v.cpu_percent is not None else "-"
    mem = f"{v.mem_mb:.1f}" if v.mem_mb is not None else "-"
    return (v.process_name, v.reason, cpu, mem)


def print_table(violations: List[QuotaViolation]) -> None:
    if not violations:
        print("No quota violations recorded.")
        return
    rows = [_fmt_row(v) for v in violations]
    widths = [max(len(h), max(len(r[i]) for r in rows)) for i, h in enumerate(_HEADERS)]
    fmt = "  ".join(f"{{:<{w}}}" for w in widths)
    print(fmt.format(*_HEADERS))
    print("  ".join("-" * w for w in widths))
    for row in rows:
        print(fmt.format(*row))


def print_json(violations: List[QuotaViolation]) -> None:
    print(json.dumps([v.to_dict() for v in violations], indent=2))


def report(violations: List[QuotaViolation], fmt: str = "table") -> None:
    if fmt == "json":
        print_json(violations)
    else:
        print_table(violations)
