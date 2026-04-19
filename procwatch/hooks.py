"""Lifecycle hooks — run shell commands on process events."""
from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass, field
from typing import Optional

log = logging.getLogger(__name__)


@dataclass
class HookConfig:
    on_start: Optional[str] = None
    on_stop: Optional[str] = None
    on_crash: Optional[str] = None
    timeout: float = 5.0


class HookRunner:
    def __init__(self, config: HookConfig, process_name: str) -> None:
        self._cfg = config
        self._name = process_name

    def _run(self, cmd: str, event: str) -> None:
        log.debug("[%s] running %s hook: %s", self._name, event, cmd)
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                timeout=self._cfg.timeout,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                log.warning(
                    "[%s] %s hook exited %d: %s",
                    self._name,
                    event,
                    result.returncode,
                    result.stderr.strip(),
                )
        except subprocess.TimeoutExpired:
            log.error("[%s] %s hook timed out after %ss", self._name, event, self._cfg.timeout)
        except Exception as exc:  # pragma: no cover
            log.error("[%s] %s hook error: %s", self._name, event, exc)

    def on_start(self) -> None:
        if self._cfg.on_start:
            self._run(self._cfg.on_start, "start")

    def on_stop(self) -> None:
        if self._cfg.on_stop:
            self._run(self._cfg.on_stop, "stop")

    def on_crash(self) -> None:
        if self._cfg.on_crash:
            self._run(self._cfg.on_crash, "crash")


def from_config(raw: dict, process_name: str) -> HookRunner:
    cfg = HookConfig(
        on_start=raw.get("on_start"),
        on_stop=raw.get("on_stop"),
        on_crash=raw.get("on_crash"),
        timeout=float(raw.get("timeout", 5.0)),
    )
    return HookRunner(cfg, process_name)
