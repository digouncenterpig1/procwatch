"""Tests for procwatch.priority."""
from __future__ import annotations

import os
import pytest
from unittest.mock import patch, MagicMock

from procwatch.priority import (
    PriorityConfig,
    apply_nice,
    apply_ionice,
    apply,
    from_config,
)


# ---------------------------------------------------------------------------
# PriorityConfig validation
# ---------------------------------------------------------------------------

def test_default_config_is_valid():
    cfg = PriorityConfig()
    assert cfg.nice == 0
    assert cfg.policy == "other"


def test_nice_out_of_range_raises():
    with pytest.raises(ValueError, match="nice"):
        PriorityConfig(nice=20)


def test_invalid_policy_raises():
    with pytest.raises(ValueError, match="policy"):
        PriorityConfig(policy="unknown")


def test_from_config_returns_none_for_empty():
    assert from_config({}) is None
    assert from_config(None) is None  # type: ignore[arg-type]


def test_from_config_builds_object():
    cfg = from_config({"nice": -5, "ionice_class": 1, "ionice_level": 2, "policy": "rr"})
    assert cfg is not None
    assert cfg.nice == -5
    assert cfg.policy == "rr"


# ---------------------------------------------------------------------------
# apply_nice
# ---------------------------------------------------------------------------

def test_apply_nice_calls_setpriority():
    with patch.object(os, "setpriority") as mock_sp:
        apply_nice(1234, 5)
        mock_sp.assert_called_once_with(os.PRIO_PROCESS, 1234, 5)


def test_apply_nice_permission_error_does_not_raise():
    with patch.object(os, "setpriority", side_effect=PermissionError):
        apply_nice(1, 0)  # should log warning, not raise


def test_apply_nice_process_not_found_does_not_raise():
    with patch.object(os, "setpriority", side_effect=ProcessLookupError):
        apply_nice(99999, 0)


# ---------------------------------------------------------------------------
# apply_ionice
# ---------------------------------------------------------------------------

def test_apply_ionice_calls_subprocess(tmp_path):
    import subprocess
    with patch.object(subprocess, "run") as mock_run:
        apply_ionice(42, 2, 4)
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "ionice" in args
        assert "42" in args


def test_apply_ionice_missing_binary_does_not_raise():
    import subprocess
    with patch.object(subprocess, "run", side_effect=FileNotFoundError):
        apply_ionice(1, 2, 4)  # should not raise


# ---------------------------------------------------------------------------
# apply (combined)
# ---------------------------------------------------------------------------

def test_apply_calls_both_helpers():
    cfg = PriorityConfig(nice=3, ionice_class=3, ionice_level=0)
    with patch("procwatch.priority.apply_nice") as mn, \
         patch("procwatch.priority.apply_ionice") as mi:
        apply(999, cfg)
        mn.assert_called_once_with(999, 3)
        mi.assert_called_once_with(999, 3, 0)


def test_apply_skips_ionice_when_not_configured():
    """apply() should not call apply_ionice when ionice_class is not set."""
    cfg = PriorityConfig(nice=-2)
    with patch("procwatch.priority.apply_nice") as mn, \
         patch("procwatch.priority.apply_ionice") as mi:
        apply(123, cfg)
        mn.assert_called_once_with(123, -2)
        mi.assert_not_called()
