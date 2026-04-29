"""CLI sub-command: procwatch retention prune / status."""
from __future__ import annotations

import argparse
import json
import logging
import time
from pathlib import Path

from procwatch.retention import RetentionPolicy
from procwatch.retention_manager import RetentionManager

log = logging.getLogger(__name__)


def _build_manager(args: argparse.Namespace) -> RetentionManager:
    policy = RetentionPolicy(
        max_age_seconds=args.max_age if args.max_age and args.max_age > 0 else None,
        max_entries=args.max_entries if args.max_entries and args.max_entries > 0 else None,
    )
    mgr = RetentionManager(default_policy=policy)
    for raw in args.files or []:
        p = Path(raw)
        mgr.register(p.name, p)
    return mgr


def cmd_prune(args: argparse.Namespace) -> None:
    mgr = _build_manager(args)
    if not mgr.registered_names():
        print("No files registered — pass paths via --files.")
        return
    results = mgr.prune_all(now=time.time())
    total = sum(results.values())
    for name, removed in results.items():
        print(f"  {name}: removed {removed} entries")
    print(f"Total pruned: {total}")


def cmd_status(args: argparse.Namespace) -> None:
    mgr = _build_manager(args)
    rows = []
    for name in mgr.registered_names():
        p = mgr._files[name]
        policy = mgr.policy_for(name)
        lines = len(p.read_text().splitlines()) if p.exists() else 0
        rows.append({"name": name, "entries": lines,
                     "max_age_seconds": policy.max_age_seconds,
                     "max_entries": policy.max_entries})
    if args.json:
        print(json.dumps(rows, indent=2))
    else:
        print(f"{'NAME':<20} {'ENTRIES':>8} {'MAX_AGE':>10} {'MAX_ENTRIES':>12}")
        for r in rows:
            print(f"{r['name']:<20} {r['entries']:>8} "
                  f"{str(r['max_age_seconds']):>10} {str(r['max_entries']):>12}")


def build_parser(parent: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = parent.add_parser("retention", help="manage log retention")
    p.add_argument("--files", nargs="+", metavar="PATH", help="JSONL files to manage")
    p.add_argument("--max-age", type=float, default=0, metavar="SECS")
    p.add_argument("--max-entries", type=int, default=0, metavar="N")
    sub = p.add_subparsers(dest="retention_cmd")

    prune_p = sub.add_parser("prune", help="apply retention and remove old entries")
    prune_p.set_defaults(func=cmd_prune)

    status_p = sub.add_parser("status", help="show current entry counts")
    status_p.add_argument("--json", action="store_true")
    status_p.set_defaults(func=cmd_status)
