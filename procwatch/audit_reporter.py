"""Pretty-print or export the audit log."""
from __future__ import annotations

import json
import sys
from typing import List, Optional

from procwatch.audit import AuditEntry, AuditLog

_COLS = ("timestamp", "action", "process", "actor", "detail")
_WIDTHS = (27, 8, 20, 12, 30)


def _fmt_row(e: AuditEntry) -> str:
    cells = [
        str(e.timestamp)[:26],
        e.action,
        e.process,
        e.actor,
        e.detail or "",
    ]
    return "  ".join(c.ljust(w) for c, w in zip(cells, _WIDTHS))


def print_table(entries: List[AuditEntry], file=sys.stdout) -> None:
    header = "  ".join(c.upper().ljust(w) for c, w in zip(_COLS, _WIDTHS))
    sep = "  ".join("-" * w for w in _WIDTHS)
    print(header, file=file)
    print(sep, file=file)
    for e in entries:
        print(_fmt_row(e), file=file)


def print_json(entries: List[AuditEntry], file=sys.stdout) -> None:
    print(json.dumps([e.to_dict() for e in entries], indent=2), file=file)


def print_csv(entries: List[AuditEntry], file=sys.stdout) -> None:
    print(",".join(_COLS), file=file)
    for e in entries:
        row = [str(e.timestamp), e.action, e.process, e.actor, e.detail or ""]
        print(",".join(f'"{v}"' for v in row), file=file)


def report(log: AuditLog, fmt: str = "table",
           tail: Optional[int] = None, file=sys.stdout) -> None:
    entries = log.tail(tail) if tail else log.read_all()
    if fmt == "json":
        print_json(entries, file=file)
    elif fmt == "csv":
        print_csv(entries, file=file)
    else:
        print_table(entries, file=file)
