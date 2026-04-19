"""Load and validate procwatch configuration from a TOML file."""

import tomllib
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProcessConfig:
    name: str
    command: list[str]
    backoff_strategy: str = "exponential"
    backoff_options: dict[str, Any] = field(default_factory=lambda: {"initial": 1.0})
    max_restarts: int = -1
    env: dict[str, str] = field(default_factory=dict)


@dataclass
class WatchConfig:
    processes: list[ProcessConfig]


def load(path: str) -> WatchConfig:
    with open(path, "rb") as f:
        data = tomllib.load(f)

    processes = []
    for entry in data.get("process", []):
        processes.append(
            ProcessConfig(
                name=entry["name"],
                command=entry["command"],
                backoff_strategy=entry.get("backoff_strategy", "exponential"),
                backoff_options=entry.get("backoff_options", {"initial": 1.0}),
                max_restarts=entry.get("max_restarts", -1),
                env=entry.get("env", {}),
            )
        )

    if not processes:
        raise ValueError("Config must define at least one [[process]] entry.")

    return WatchConfig(processes=processes)
