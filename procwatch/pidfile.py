"""PID file management for procwatch daemon."""

from __future__ import annotations

import os
import errno
from pathlib import Path


class PidFileError(Exception):
    pass


class PidFile:
    """Write and manage a PID file for the running daemon."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._pid: int | None = None

    def acquire(self) -> None:
        """Write current PID to file. Raises if stale/active PID exists."""
        if self.path.exists():
            existing = self._read()
            if existing is not None and _pid_alive(existing):
                raise PidFileError(
                    f"Process already running with PID {existing} ({self.path})"
                )
            # stale file — remove it
            self.path.unlink(missing_ok=True)

        self._pid = os.getpid()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(str(self._pid) + "\n")

    def release(self) -> None:
        """Remove the PID file if we own it."""
        if self._pid is not None and self._pid == os.getpid():
            self.path.unlink(missing_ok=True)
            self._pid = None

    def read_pid(self) -> int | None:
        """Return the PID stored in the file, or None."""
        return self._read()

    def _read(self) -> int | None:
        try:
            text = self.path.read_text().strip()
            return int(text) if text else None
        except (OSError, ValueError):
            return None

    def __enter__(self) -> "PidFile":
        self.acquire()
        return self

    def __exit__(self, *_) -> None:
        self.release()


def _pid_alive(pid: int) -> bool:
    """Return True if a process with *pid* is running."""
    try:
        os.kill(pid, 0)
        return True
    except OSError as exc:
        return exc.errno != errno.ESRCH
