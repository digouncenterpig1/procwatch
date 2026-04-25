"""Label-based filtering for managed processes."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Set


@dataclass
class LabelFilter:
    """Match processes against a set of label key/value pairs.

    A process matches when *all* selector labels are present in its
    own label map with equal values (subset match).
    """

    selector: Dict[str, str] = field(default_factory=dict)

    def matches(self, labels: Dict[str, str]) -> bool:
        """Return True if *labels* satisfies every entry in selector."""
        return all(labels.get(k) == v for k, v in self.selector.items())

    def filter(self, processes: Iterable) -> List:
        """Return the subset of *processes* whose .labels satisfy the selector.

        Each item in *processes* must expose a ``labels`` attribute that is a
        ``Dict[str, str]``.
        """
        return [p for p in processes if self.matches(getattr(p, "labels", {}))]


def parse_selector(raw: str) -> Dict[str, str]:
    """Parse a comma-separated ``key=value`` selector string.

    Example::

        parse_selector("env=prod,team=backend")
        # -> {'env': 'prod', 'team': 'backend'}

    Raises ``ValueError`` for malformed pairs.
    """
    if not raw.strip():
        return {}
    result: Dict[str, str] = {}
    for part in raw.split(","):
        part = part.strip()
        if "=" not in part:
            raise ValueError(f"Invalid label selector token: {part!r}")
        k, _, v = part.partition("=")
        k, v = k.strip(), v.strip()
        if not k:
            raise ValueError(f"Empty key in label selector token: {part!r}")
        result[k] = v
    return result


def label_names(processes: Iterable) -> Set[str]:
    """Collect every label key present across *processes*."""
    keys: Set[str] = set()
    for p in processes:
        keys.update(getattr(p, "labels", {}).keys())
    return keys
