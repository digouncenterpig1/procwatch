"""Tests for procwatch.statefile."""

import json
import time
from pathlib import Path

import pytest

from procwatch.statefile import ProcessState, StateFile


@pytest.fixture()
def state_path(tmp_path: Path) -> Path:
    return tmp_path / "procwatch.state"


def make_state(name="web", restart_count=3, exit_code=1, started_at=None):
    return ProcessState(
        name=name,
        restart_count=restart_count,
        last_exit_code=exit_code,
        last_started_at=started_at or time.time(),
    )


def test_save_and_load_roundtrip(state_path):
    sf = StateFile(state_path)
    states = [make_state("web", 2, 0), make_state("worker", 5, 1)]
    sf.save(states)
    loaded = sf.load()
    assert set(loaded.keys()) == {"web", "worker"}
    assert loaded["web"].restart_count == 2
    assert loaded["worker"].last_exit_code == 1


def test_load_missing_file_returns_empty(state_path):
    sf = StateFile(state_path)
    assert sf.load() == {}


def test_save_creates_file(state_path):
    sf = StateFile(state_path)
    sf.save([make_state()])
    assert state_path.exists()


def test_remove_deletes_file(state_path):
    sf = StateFile(state_path)
    sf.save([make_state()])
    sf.remove()
    assert not state_path.exists()


def test_remove_missing_file_is_noop(state_path):
    sf = StateFile(state_path)
    sf.remove()  # should not raise


def test_corrupt_file_returns_empty(state_path):
    state_path.write_text("not json at all")
    sf = StateFile(state_path)
    assert sf.load() == {}


def test_saved_at_timestamp_present(state_path):
    sf = StateFile(state_path)
    sf.save([make_state()])
    data = json.loads(state_path.read_text())
    assert "saved_at" in data
    assert data["saved_at"] <= time.time()


def test_process_state_from_dict_defaults():
    ps = ProcessState.from_dict({"name": "svc"})
    assert ps.restart_count == 0
    assert ps.last_exit_code is None
    assert ps.last_started_at is None


def test_save_is_atomic_on_success(state_path):
    sf = StateFile(state_path)
    sf.save([make_state("a", 1, 0)])
    # overwrite with new data
    sf.save([make_state("a", 7, 0)])
    loaded = sf.load()
    assert loaded["a"].restart_count == 7
    # tmp file should not linger
    assert not state_path.with_suffix(".tmp").exists()
