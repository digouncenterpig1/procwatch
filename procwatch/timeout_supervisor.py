"""Supervisor mixin that enforces per-process shutdown timeouts."""
from __future__ import annotations

import logging
import signal
from typing import Dict, List, Optional

from procwatch.supervisor import Supervisor
from procwatch.config import WatchConfig
from procwatch.timeout_policy import TimeoutPolicy, TimeoutTracker

log = logging.getLogger(__name__)


class TimeoutSupervisor(Supervisor):
    """Extends Supervisor with configurable graceful-shutdown timeouts."""

    def __init__(self, config: WatchConfig) -> None:
        super().__init__(config)
        self._tracker = TimeoutTracker()
        self._load_policies(config)

    # ------------------------------------------------------------------
    # setup
    # ------------------------------------------------------------------

    def _load_policies(self, config: WatchConfig) -> None:
        for pcfg in config.processes:
            raw = getattr(pcfg, "timeout", None) or {}
            policy = TimeoutPolicy.from_config(raw)
            if policy is not None:
                self._tracker.set_policy(pcfg.name, policy)
                log.debug(
                    "timeout policy for %s: graceful=%.1fs kill=%.1fs",
                    pcfg.name,
                    policy.graceful_timeout,
                    policy.kill_timeout,
                )

    # ------------------------------------------------------------------
    # shutdown
    # ------------------------------------------------------------------

    def stop_one(self, name: str) -> None:
        """Stop a single managed process, respecting its timeout policy."""
        proc = self._processes.get(name)
        if proc is None:
            log.warning("stop_one: unknown process %r", name)
            return

        policy = self._tracker.policy_for(name)
        log.info("stopping %s (graceful=%.1fs)", name, policy.graceful_timeout)

        try:
            proc.process.terminate()  # SIGTERM
        except ProcessLookupError:
            return  # already gone

        deadline = self._tracker.start_graceful(name)

        import time
        while not self._tracker.is_expired(name):
            if not proc.is_running():
                log.debug("%s exited cleanly within graceful window", name)
                self._tracker.clear(name)
                return
            time.sleep(0.1)

        # graceful timeout elapsed — force kill
        if proc.is_running():
            log.warning("%s did not stop in time; sending SIGKILL", name)
            try:
                proc.process.kill()
            except ProcessLookupError:
                pass

        self._tracker.clear(name)

    def stop_all(self) -> None:  # type: ignore[override]
        """Stop every managed process in reverse start order."""
        for name in list(self._processes):
            self.stop_one(name)

    # ------------------------------------------------------------------
    # introspection
    # ------------------------------------------------------------------

    def timeout_policies(self) -> Dict[str, TimeoutPolicy]:
        return self._tracker.all_policies()
