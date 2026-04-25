"""Report processes grouped or filtered by labels."""
from __future__ import annotations

import json
from typing import Dict, Iterable, List

from procwatch.label_filter import LabelFilter, label_names


def _group_by(processes: Iterable, key: str) -> Dict[str, List]:
    """Group *processes* by the value of label *key*."""
    groups: Dict[str, List] = {}
    for p in processes:
        value = getattr(p, "labels", {}).get(key, "<none>")
        groups.setdefault(value, []).append(p)
    return groups


def print_label_table(processes: Iterable, selector: str = "") -> None:
    """Print a simple table of processes, optionally filtered by *selector*."""
    from procwatch.label_filter import parse_selector

    procs = list(processes)
    if selector:
        procs = LabelFilter(parse_selector(selector)).filter(procs)

    all_keys = sorted(label_names(procs))
    name_w = max((len(getattr(p, "name", "")) for p in procs), default=4)
    name_w = max(name_w, 4)

    header_parts = [f"{'NAME':<{name_w}}"] + [k.upper() for k in all_keys]
    print("  ".join(header_parts))
    print("-" * (name_w + sum(len(k) + 2 for k in all_keys)))

    for p in procs:
        labels = getattr(p, "labels", {})
        row = [f"{getattr(p, 'name', '?'):<{name_w}}"] + [
            f"{labels.get(k, '-'):<{len(k)}}" for k in all_keys
        ]
        print("  ".join(row))


def print_label_json(processes: Iterable, selector: str = "") -> None:
    """Dump process label data as JSON."""
    from procwatch.label_filter import parse_selector

    procs = list(processes)
    if selector:
        procs = LabelFilter(parse_selector(selector)).filter(procs)

    out = [
        {"name": getattr(p, "name", "?"), "labels": getattr(p, "labels", {})}
        for p in procs
    ]
    print(json.dumps(out, indent=2))


def report(processes: Iterable, fmt: str = "table", selector: str = "") -> None:
    """Entry-point: dispatch to the appropriate formatter."""
    if fmt == "json":
        print_label_json(processes, selector)
    else:
        print_label_table(processes, selector)
