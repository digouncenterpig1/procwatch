"""Environment variable handling for managed processes.

Supports loading per-process env vars from the config, inheriting from
the parent environment, and optionally loading from a .env file.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Optional


def _parse_dotenv(path: Path) -> Dict[str, str]:
    """Parse a simple .env file into a dict.

    Supports:
      - KEY=VALUE
      - KEY="VALUE" or KEY='VALUE' (quotes stripped)
      - Lines starting with # are comments
      - Blank lines are ignored
    """
    result: Dict[str, str] = {}
    for lineno, raw in enumerate(path.read_text().splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(
                f"{path}:{lineno}: invalid syntax (missing '='): {raw!r}"
            )
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        # Strip matching surrounding quotes
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]
        if not key:
            raise ValueError(f"{path}:{lineno}: empty key: {raw!r}")
        result[key] = value
    return result


def build_env(
    *,
    extra: Optional[Dict[str, str]] = None,
    dotenv_path: Optional[str] = None,
    inherit: bool = True,
) -> Dict[str, str]:
    """Build an environment dict for a child process.

    Resolution order (later entries win):
      1. Parent environment (if inherit=True)
      2. Variables loaded from dotenv_path (if provided)
      3. Explicit key/value pairs from extra

    Args:
        extra: Explicit env vars defined in the process config.
        dotenv_path: Optional path to a .env file to load.
        inherit: Whether to start from the current process environment.

    Returns:
        A dict suitable for passing to subprocess as ``env``.
    """
    env: Dict[str, str] = {}

    if inherit:
        env.update(os.environ)

    if dotenv_path is not None:
        p = Path(dotenv_path)
        if p.exists():
            env.update(_parse_dotenv(p))
        else:
            # Non-fatal: log a warning rather than crashing the daemon
            import logging
            logging.getLogger(__name__).warning(
                "dotenv file not found, skipping: %s", dotenv_path
            )

    if extra:
        env.update(extra)

    return env
