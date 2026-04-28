"""Route processes to named groups via tag-based rules."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional


@dataclass
class TagRule:
    """A single routing rule: if a process has *all* required tags it joins the group."""

    group: str
    required_tags: List[str] = field(default_factory=list)

    def matches(self, tags: Iterable[str]) -> bool:
        tag_set = set(tags)
        return all(t in tag_set for t in self.required_tags)


@dataclass
class TagRouter:
    """Assign processes to groups based on their tags."""

    rules: List[TagRule] = field(default_factory=list)
    _groups: Dict[str, List[str]] = field(default_factory=dict, init=False, repr=False)

    def add_rule(self, group: str, required_tags: List[str]) -> None:
        self.rules.append(TagRule(group=group, required_tags=required_tags))

    def route(self, name: str, tags: Iterable[str]) -> List[str]:
        """Return the list of groups *name* belongs to given its tags."""
        assigned: List[str] = []
        for rule in self.rules:
            if rule.matches(tags):
                assigned.append(rule.group)
                self._groups.setdefault(rule.group, [])
                if name not in self._groups[rule.group]:
                    self._groups[rule.group].append(name)
        return assigned

    def group(self, name: str) -> List[str]:
        """Return all process names currently in *group*."""
        return list(self._groups.get(name, []))

    def groups_for(self, process_name: str) -> List[str]:
        """Return all group names that contain *process_name*."""
        return [g for g, members in self._groups.items() if process_name in members]

    def remove(self, process_name: str) -> None:
        """Remove a process from all groups (e.g. on stop)."""
        for members in self._groups.values():
            if process_name in members:
                members.remove(process_name)

    def all_groups(self) -> Dict[str, List[str]]:
        return {g: list(m) for g, m in self._groups.items()}
