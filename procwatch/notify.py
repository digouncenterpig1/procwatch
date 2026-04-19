"""Glue between Supervisor events and the Alerter."""

from __future__ import annotations

import logging
from typing import Optional

from procwatch.alerts import AlertConfig, Alerter

logger = logging.getLogger(__name__)

_alerter: Optional[Alerter] = None


def configure(raw: dict) -> None:
    """Initialise the module-level alerter from raw config dict."""
    global _alerter
    cfg = AlertConfig(
        on_crash=raw.get("on_crash", True),
        on_throttle=raw.get("on_throttle", True),
        exec=raw.get("exec"),
        smtp_host=raw.get("smtp_host"),
        smtp_port=raw.get("smtp_port", 25),
        smtp_to=raw.get("smtp_to", []),
        smtp_from=raw.get("smtp_from", "procwatch@localhost"),
    )
    _alerter = Alerter(cfg)
    logger.debug("Alerter configured: exec=%s smtp=%s", cfg.exec, cfg.smtp_host)


def notify_crash(name: str, exit_code: int) -> None:
    """Call from Supervisor when a managed process exits unexpectedly."""
    if _alerter is None:
        logger.debug("notify_crash called but no alerter configured")
        return
    _alerter.crash(name, exit_code)


def notify_throttle(name: str) -> None:
    """Call from Supervisor when restart throttle kicks in."""
    if _alerter is None:
        logger.debug("notify_throttle called but no alerter configured")
        return
    _alerter.throttle(name)


def reset() -> None:
    """Clear the module-level alerter (useful in tests)."""
    global _alerter
    _alerter = None
