"""Manages per-process log file handles with optional rotation."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, IO, Optional

from procwatch.logrotate import LogRotator, RotateConfig

log = logging.getLogger(__name__)

_DEFAULT_LOG_DIR = Path("logs")


class LogManager:
    """Opens and tracks stdout/stderr file handles for managed processes.

    Rotation is attempted each time :meth:`get_handles` is called so that
    long-running processes naturally rotate without external cron jobs.
    """

    def __init__(
        self,
        log_dir: Path = _DEFAULT_LOG_DIR,
        rotate_cfg: Optional[RotateConfig] = None,
    ) -> None:
        self.log_dir = log_dir
        self.rotate_cfg = rotate_cfg or RotateConfig()
        self._rotators: Dict[str, tuple[LogRotator, LogRotator]] = {}

    # ------------------------------------------------------------------
    def _rotator(self, path: Path) -> LogRotator:
        return LogRotator(path, self.rotate_cfg)

    def get_handles(self, name: str) -> tuple[IO[bytes], IO[bytes]]:
        """Return (stdout_fh, stderr_fh) for *name*, rotating if needed."""
        stdout_path = self.log_dir / name / "stdout.log"
        stderr_path = self.log_dir / name / "stderr.log"

        stdout_r = self._rotator(stdout_path)
        stderr_r = self._rotator(stderr_path)

        self._rotators[name] = (stdout_r, stderr_r)

        stdout_fh = stdout_r.open_log()
        stderr_fh = stderr_r.open_log()
        return stdout_fh, stderr_fh

    def rotate_all(self) -> Dict[str, list[str]]:
        """Trigger rotation check for every tracked process.

        Returns a dict mapping process name -> list of rotated paths.
        """
        rotated: Dict[str, list[str]] = {}
        for name, (sr, er) in self._rotators.items():
            done = []
            if sr.maybe_rotate():
                done.append(str(sr.path))
            if er.maybe_rotate():
                done.append(str(er.path))
            if done:
                rotated[name] = done
        return rotated

    def log_paths(self, name: str) -> tuple[Path, Path]:
        """Return the (stdout, stderr) Path objects for *name*."""
        return (
            self.log_dir / name / "stdout.log",
            self.log_dir / name / "stderr.log",
        )
