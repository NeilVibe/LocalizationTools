"""Tests for server.setup.state — setup wizard crash-recovery state file."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from server.setup.state import (
    STEP_NAMES,
    SetupState,
    get_first_incomplete_step,
    is_setup_complete,
    mark_step_done,
    mark_step_failed,
    read_state,
    write_state,
)


@pytest.fixture
def state_path(tmp_path: Path) -> Path:
    return tmp_path / "subdir" / "setup_state.json"


# --- read / write -----------------------------------------------------------


def test_read_state_returns_empty_when_no_file(state_path: Path) -> None:
    state = read_state(state_path)
    assert isinstance(state, SetupState)
    assert state.steps == {}
    assert state.config == {}


def test_write_and_read_state_roundtrip(state_path: Path) -> None:
    state = read_state(state_path)
    state.pg_major_version = 16
    state.config["pg_port"] = 5432
    write_state(state_path, state)

    loaded = read_state(state_path)
    assert loaded.pg_major_version == 16
    assert loaded.config["pg_port"] == 5432


def test_state_file_is_valid_json(state_path: Path) -> None:
    state = read_state(state_path)
    mark_step_done(state, "preflight_checks")
    write_state(state_path, state)

    raw = state_path.read_text(encoding="utf-8")
    parsed = json.loads(raw)
    assert "version" in parsed
    assert "steps" in parsed


# --- mark helpers ------------------------------------------------------------


def test_mark_step_done_and_failed(state_path: Path) -> None:
    state = read_state(state_path)

    mark_step_done(state, "preflight_checks")
    assert state.steps["preflight_checks"]["status"] == "done"
    assert "timestamp" in state.steps["preflight_checks"]

    mark_step_failed(state, "init_database", error="PG_INITDB_FAIL")
    assert state.steps["init_database"]["status"] == "failed"
    assert state.steps["init_database"]["error"] == "PG_INITDB_FAIL"


# --- get_first_incomplete_step -----------------------------------------------


def test_get_first_incomplete_step_all_done(state_path: Path) -> None:
    state = read_state(state_path)
    for step in STEP_NAMES:
        mark_step_done(state, step)
    assert get_first_incomplete_step(state) is None


def test_get_first_incomplete_step_partial(state_path: Path) -> None:
    state = read_state(state_path)
    mark_step_done(state, "preflight_checks")
    mark_step_done(state, "init_database")
    # configure_access not done yet
    assert get_first_incomplete_step(state) == "configure_access"


def test_get_first_incomplete_step_failed_step(state_path: Path) -> None:
    state = read_state(state_path)
    mark_step_done(state, "preflight_checks")
    mark_step_failed(state, "init_database", error="DISK_FULL")
    assert get_first_incomplete_step(state) == "init_database"


# --- is_setup_complete -------------------------------------------------------


def test_is_setup_complete(state_path: Path) -> None:
    state = read_state(state_path)
    assert is_setup_complete(state) is False

    for step in STEP_NAMES:
        mark_step_done(state, step)
    assert is_setup_complete(state) is True
