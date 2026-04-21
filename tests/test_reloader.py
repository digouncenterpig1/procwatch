"""Tests for procwatch.reloader."""

import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from procwatch.config import ProcessConfig, WatchConfig
from procwatch.reloader import Reloader


def _pcfg(name: str) -> ProcessConfig:
    return ProcessConfig(name=name, command=f"echo {name}")


def _make_supervisor(names: list[str]):
    """Build a minimal mock Supervisor with the given process names."""
    sup = MagicMock()
    sup._processes = {n: MagicMock() for n in names}
    sup._make_process = lambda pcfg: MagicMock()
    sup.config = WatchConfig(processes=[_pcfg(n) for n in names])
    return sup


def test_reload_stops_removed_process(tmp_path):
    cfg_file = tmp_path / "watch.toml"
    cfg_file.write_text(textwrap.dedent("""\
        [[process]]
        name = "alpha"
        command = "echo alpha"
    """))

    sup = _make_supervisor(["alpha", "beta"])
    beta_proc = sup._processes["beta"]

    reloader = Reloader(cfg_file, sup)
    reloader.reload()

    beta_proc.stop.assert_called_once()
    assert "beta" not in sup._processes


def test_reload_starts_new_process(tmp_path):
    cfg_file = tmp_path / "watch.toml"
    cfg_file.write_text(textwrap.dedent("""\
        [[process]]
        name = "alpha"
        command = "echo alpha"
        [[process]]
        name = "gamma"
        command = "echo gamma"
    """))

    sup = _make_supervisor(["alpha"])
    new_proc = MagicMock()
    sup._make_process = MagicMock(return_value=new_proc)

    reloader = Reloader(cfg_file, sup)
    reloader.reload()

    new_proc.start.assert_called_once()
    assert "gamma" in sup._processes


def test_reload_bad_config_keeps_existing(tmp_path, caplog):
    cfg_file = tmp_path / "watch.toml"
    cfg_file.write_text("this is not valid toml [")  # invalid

    sup = _make_supervisor(["alpha"])
    alpha_proc = sup._processes["alpha"]

    reloader = Reloader(cfg_file, sup)
    reloader.reload()

    # Existing process must be untouched
    alpha_proc.stop.assert_not_called()
    assert "alpha" in sup._processes


def test_reload_updates_supervisor_config(tmp_path):
    cfg_file = tmp_path / "watch.toml"
    cfg_file.write_text(textwrap.dedent("""\
        [[process]]
        name = "alpha"
        command = "echo alpha"
    """))

    sup = _make_supervisor(["alpha"])
    reloader = Reloader(cfg_file, sup)
    reloader.reload()

    assert sup.config is not None
    assert any(p.name == "alpha" for p in sup.config.processes)
