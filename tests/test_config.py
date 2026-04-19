"""Tests for config loading."""

import textwrap
import pytest
from pathlib import Path
from procwatch.config import load


TOML_BASIC = textwrap.dedent("""
    [[process]]
    name = "worker"
    command = ["python", "worker.py"]
    backoff_strategy = "linear"

    [process.backoff_options]
    initial = 2.0
    step = 1.0
    maximum = 30.0
""")

TOML_EMPTY = ""


def write_toml(tmp_path: Path, content: str) -> str:
    p = tmp_path / "procwatch.toml"
    p.write_text(content)
    return str(p)


def test_load_basic(tmp_path):
    path = write_toml(tmp_path, TOML_BASIC)
    cfg = load(path)
    assert len(cfg.processes) == 1
    p = cfg.processes[0]
    assert p.name == "worker"
    assert p.command == ["python", "worker.py"]
    assert p.backoff_strategy == "linear"
    assert p.backoff_options["step"] == 1.0


def test_load_defaults(tmp_path):
    toml = textwrap.dedent("""
        [[process]]
        name = "api"
        command = ["uvicorn", "app:app"]
    """)
    path = write_toml(tmp_path, toml)
    cfg = load(path)
    p = cfg.processes[0]
    assert p.backoff_strategy == "exponential"
    assert p.max_restarts == -1


def test_load_empty_raises(tmp_path):
    path = write_toml(tmp_path, TOML_EMPTY)
    with pytest.raises(ValueError, match="at least one"):
        load(path)
