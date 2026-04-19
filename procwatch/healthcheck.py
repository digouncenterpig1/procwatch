"""Optional health check support for managed processes."""

import socket
import subprocess
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class HealthCheck:
    """Configuration and logic for a single health check."""

    type: str  # 'tcp', 'http', 'exec'
    target: str  # host:port, url, or command
    interval: float = 10.0
    timeout: float = 5.0
    retries: int = 3

    def check(self) -> bool:
        """Run the health check and return True if healthy."""
        for _ in range(self.retries):
            if self._once():
                return True
            time.sleep(0.5)
        return False

    def _once(self) -> bool:
        if self.type == "tcp":
            return self._check_tcp()
        elif self.type == "exec":
            return self._check_exec()
        else:
            raise ValueError(f"Unsupported health check type: {self.type}")

    def _check_tcp(self) -> bool:
        host, _, port_str = self.target.rpartition(":")
        try:
            with socket.create_connection((host, int(port_str)), timeout=self.timeout):
                return True
        except OSError:
            return False

    def _check_exec(self) -> bool:
        try:
            result = subprocess.run(
                self.target,
                shell=True,
                timeout=self.timeout,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, OSError):
            return False


def from_config(cfg: dict) -> Optional[HealthCheck]:
    """Build a HealthCheck from a config dict, or None if not configured."""
    if not cfg:
        return None
    return HealthCheck(
        type=cfg["type"],
        target=cfg["target"],
        interval=cfg.get("interval", 10.0),
        timeout=cfg.get("timeout", 5.0),
        retries=cfg.get("retries", 3),
    )
