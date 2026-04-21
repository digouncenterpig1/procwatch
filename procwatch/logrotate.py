"""Log rotation support for managed process stdout/stderr streams."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)


@dataclass
class RotateConfig:
    max_bytes: int = 10 * 1024 * 1024  # 10 MB
    backup_count: int = 3
    enabled: bool = True


class LogRotator:
    """Rotates a log file when it exceeds *max_bytes*.

    Keeps up to *backup_count* numbered backups (.1, .2, …).
    """

    def __init__(self, path: Path, cfg: RotateConfig) -> None:
        self.path = path
        self.cfg = cfg

    # ------------------------------------------------------------------
    def should_rotate(self) -> bool:
        if not self.cfg.enabled:
            return False
        try:
            return self.path.stat().st_size >= self.cfg.max_bytes
        except FileNotFoundError:
            return False

    def rotate(self) -> None:
        """Perform the rotation synchronously."""
        if not self.path.exists():
            return

        # Remove oldest backup if at limit
        oldest = Path(f"{self.path}.{self.cfg.backup_count}")
        if oldest.exists():
            oldest.unlink()
            log.debug("logrotate: removed %s", oldest)

        # Shift existing backups up by one
        for n in range(self.cfg.backup_count - 1, 0, -1):
            src = Path(f"{self.path}.{n}")
            dst = Path(f"{self.path}.{n + 1}")
            if src.exists():
                src.rename(dst)
                log.debug("logrotate: %s -> %s", src, dst)

        # Move current log to .1
        self.path.rename(Path(f"{self.path}.1"))
        log.info("logrotate: rotated %s", self.path)

    def maybe_rotate(self) -> bool:
        """Rotate if needed; return True if rotation happened."""
        if self.should_rotate():
            self.rotate()
            return True
        return False

    def open_log(self, mode: str = "ab") -> "os.PathLike":
        """Open (and possibly rotate) the log file, returning a file object."""
        self.maybe_rotate()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        return open(self.path, mode)  # noqa: WPS515
