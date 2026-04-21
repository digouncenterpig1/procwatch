"""Hot-reload support: re-read config on SIGHUP and reconcile running processes."""

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from procwatch.config import WatchConfig, load

if TYPE_CHECKING:
    from procwatch.supervisor import Supervisor

log = logging.getLogger(__name__)


class Reloader:
    """Reloads WatchConfig from disk and reconciles it against a live Supervisor."""

    def __init__(self, config_path: str | Path, supervisor: "Supervisor") -> None:
        self._path = Path(config_path)
        self._supervisor = supervisor

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def reload(self) -> None:
        """Read config from disk and apply changes to the running supervisor."""
        log.info("reloading config from %s", self._path)
        try:
            new_cfg = load(str(self._path))
        except Exception as exc:  # noqa: BLE001
            log.error("config reload failed — keeping current config: %s", exc)
            return

        self._reconcile(new_cfg)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _reconcile(self, new_cfg: WatchConfig) -> None:
        supervisor = self._supervisor
        old_names = set(supervisor._processes.keys())
        new_names = {p.name for p in new_cfg.processes}

        # Stop processes removed from config
        for name in old_names - new_names:
            log.info("reloader: stopping removed process '%s'", name)
            proc = supervisor._processes.pop(name)
            proc.stop()

        # Add processes that are new
        for pcfg in new_cfg.processes:
            if pcfg.name not in old_names:
                log.info("reloader: starting new process '%s'", pcfg.name)
                managed = supervisor._make_process(pcfg)
                supervisor._processes[pcfg.name] = managed
                managed.start()

        # Update supervisor-level config
        supervisor.config = new_cfg
        log.info("reloader: reconciliation complete (kept=%d, added=%d, removed=%d)",
                 len(old_names & new_names),
                 len(new_names - old_names),
                 len(old_names - new_names))
