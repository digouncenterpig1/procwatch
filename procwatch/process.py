"""Managed process wrapper with restart logic."""

import subprocess
import time
import logging
from typing import Iterator, Optional

logger = logging.getLogger(__name__)


class ManagedProcess:
    def __init__(
        self,
        name: str,
        command: list[str],
        backoff: Iterator[float],
        max_restarts: int = -1,
        env: Optional[dict] = None,
    ):
        self.name = name
        self.command = command
        self.backoff = backoff
        self.max_restarts = max_restarts
        self.env = env
        self.restarts = 0
        self._proc: Optional[subprocess.Popen] = None

    def start(self) -> None:
        logger.info("[%s] Starting: %s", self.name, " ".join(self.command))
        self._proc = subprocess.Popen(
            self.command,
            env=self.env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

    def is_running(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def wait(self) -> int:
        if self._proc is None:
            return -1
        return self._proc.wait()

    def stop(self) -> None:
        if self._proc and self.is_running():
            logger.info("[%s] Stopping process.", self.name)
            self._proc.terminate()
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._proc.kill()

    def run_forever(self) -> None:
        self.start()
        while True:
            exit_code = self.wait()
            logger.warning(
                "[%s] Exited with code %d (restarts=%d).",
                self.name, exit_code, self.restarts,
            )
            if self.max_restarts != -1 and self.restarts >= self.max_restarts:
                logger.error("[%s] Max restarts reached. Giving up.", self.name)
                break
            delay = next(self.backoff)
            logger.info("[%s] Restarting in %.1fs...", self.name, delay)
            time.sleep(delay)
            self.restarts += 1
            self.start()
