"""Supervisor: watches managed processes and restarts them with backoff."""

import time
import logging
from typing import Dict

from procwatch.config import WatchConfig, ProcessConfig
from procwatch.process import ManagedProcess
from procwatch import backoff

logger = logging.getLogger(__name__)


class Supervisor:
    def __init__(self, config: WatchConfig):
        self.config = config
        self._processes: Dict[str, ManagedProcess] = {}
        self._restart_counts: Dict[str, int] = {}

    def _make_process(self, cfg: ProcessConfig) -> ManagedProcess:
        return ManagedProcess(cfg)

    def start_all(self):
        for cfg in self.config.processes:
            logger.info("Starting process: %s", cfg.name)
            proc = self._make_process(cfg)
            proc.start()
            self._processes[cfg.name] = proc
            self._restart_counts[cfg.name] = 0

    def stop_all(self):
        for name, proc in self._processes.items():
            logger.info("Stopping process: %s", name)
            proc.stop()

    def run_forever(self):
        self.start_all()
        try:
            while True:
                self._check_processes()
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Interrupted, stopping all processes.")
            self.stop_all()

    def _check_processes(self):
        for cfg in self.config.processes:
            name = cfg.name
            proc = self._processes.get(name)
            if proc is None or not proc.is_running():
                restarts = self._restart_counts[name]
                if cfg.max_restarts is not None and restarts >= cfg.max_restarts:
                    logger.warning("Process %s reached max restarts (%d), giving up.", name, cfg.max_restarts)
                    continue
                delay_gen = backoff.from_config(cfg)
                delay = next(x for i, x in enumerate(delay_gen) if i == restarts)
                logger.info("Restarting %s in %.1fs (attempt %d)", name, delay, restarts + 1)
                time.sleep(delay)
                new_proc = self._make_process(cfg)
                new_proc.start()
                self._processes[name] = new_proc
                self._restart_counts[name] = restarts + 1
