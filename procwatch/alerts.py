"""Simple alert system for procwatch — emit notifications when processes crash or throttle."""

from __future__ import annotations

import logging
import smtplib
import subprocess
from dataclasses import dataclass, field
from email.message import EmailMessage
from typing import Callable, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AlertConfig:
    on_crash: bool = True
    on_throttle: bool = True
    exec: Optional[str] = None  # shell command, receives env vars
    smtp_host: Optional[str] = None
    smtp_port: int = 25
    smtp_to: List[str] = field(default_factory=list)
    smtp_from: str = "procwatch@localhost"


class Alerter:
    def __init__(self, config: AlertConfig) -> None:
        self.config = config
        self._handlers: List[Callable[[str, str], None]] = []
        if config.exec:
            self._handlers.append(self._exec_handler)
        if config.smtp_host and config.smtp_to:
            self._handlers.append(self._smtp_handler)
        if not self._handlers:
            self._handlers.append(self._log_handler)

    def crash(self, name: str, exit_code: int) -> None:
        if self.config.on_crash:
            self._dispatch(name, f"Process '{name}' crashed with exit code {exit_code}")

    def throttle(self, name: str) -> None:
        if self.config.on_throttle:
            self._dispatch(name, f"Process '{name}' is throttled — too many restarts")

    def _dispatch(self, name: str, message: str) -> None:
        for handler in self._handlers:
            try:
                handler(name, message)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Alert handler failed: %s", exc)

    def _log_handler(self, name: str, message: str) -> None:
        logger.warning("[alert] %s", message)

    def _exec_handler(self, name: str, message: str) -> None:
        assert self.config.exec
        subprocess.run(
            self.config.exec,
            shell=True,
            env={"PROCWATCH_PROCESS": name, "PROCWATCH_MESSAGE": message},
            timeout=10,
        )

    def _smtp_handler(self, name: str, message: str) -> None:
        msg = EmailMessage()
        msg["Subject"] = f"[procwatch] {message}"
        msg["From"] = self.config.smtp_from
        msg["To"] = ", ".join(self.config.smtp_to)
        msg.set_content(message)
        with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port) as s:
            s.send_message(msg)


def from_config(raw: dict) -> Alerter:
    cfg = AlertConfig(
        on_crash=raw.get("on_crash", True),
        on_throttle=raw.get("on_throttle", True),
        exec=raw.get("exec"),
        smtp_host=raw.get("smtp_host"),
        smtp_port=raw.get("smtp_port", 25),
        smtp_to=raw.get("smtp_to", []),
        smtp_from=raw.get("smtp_from", "procwatch@localhost"),
    )
    return Alerter(cfg)
