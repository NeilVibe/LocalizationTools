"""Tests for server.setup.runner — all step functions are mocked."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from server.setup import SetupConfig, StepResult
from server.setup.runner import STEP_FUNCTIONS, run_setup
from server.setup.state import STEP_NAMES, mark_step_done, read_state, write_state


@pytest.fixture
def config() -> SetupConfig:
    return SetupConfig(pg_bin_dir="/fake/bin", data_dir="/fake/data")


@pytest.fixture
def state_path(tmp_path: Path) -> Path:
    return tmp_path / "setup_state.json"


def _ok(step: str) -> StepResult:
    """Helper: return a successful StepResult."""
    return StepResult(step=step, status="done", message="ok")


def _fail(step: str, error_code: str = "ERR") -> StepResult:
    """Helper: return a failed StepResult."""
    return StepResult(step=step, status="failed", message="boom", error_code=error_code)


def _patch_all_steps(overrides: dict[str, MagicMock | StepResult] | None = None):
    """Context manager that patches all 7 step functions.

    *overrides* maps step name → MagicMock or StepResult.
    Un-overridden steps return ``_ok(name)``.
    """
    patches = {}
    mocks = {}
    for name in STEP_NAMES:
        target = f"server.setup.runner.STEP_FUNCTIONS"
        if overrides and name in overrides:
            val = overrides[name]
            if isinstance(val, MagicMock):
                mocks[name] = val
            else:
                m = MagicMock(return_value=val)
                mocks[name] = m
        else:
            mocks[name] = MagicMock(return_value=_ok(name))

    # We patch the dict itself
    patched_dict = {name: mocks[name] for name in STEP_NAMES}
    return patch.dict("server.setup.runner.STEP_FUNCTIONS", patched_dict), mocks


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@patch("server.setup.runner.detect_lan_ip", return_value="192.168.1.42")
def test_run_setup_calls_all_steps(_mock_ip, config, state_path):
    """All 7 steps succeed → result.success=True, all called once."""
    patcher, mocks = _patch_all_steps()
    with patcher:
        result = run_setup(config, state_path)

    assert result.success is True
    assert len(result.steps) == 7
    assert result.lan_ip == "192.168.1.42"
    assert result.failed_step is None
    for name in STEP_NAMES:
        mocks[name].assert_called_once_with(config)


@patch("server.setup.runner.detect_lan_ip", return_value="127.0.0.1")
def test_run_setup_stops_on_fatal_failure(_mock_ip, config, state_path):
    """Fatal step fails → abort immediately, only 1 step ran."""
    patcher, mocks = _patch_all_steps(
        overrides={"preflight_checks": _fail("preflight_checks", "MISSING_BINARIES")}
    )
    with patcher:
        result = run_setup(config, state_path)

    assert result.success is False
    assert result.failed_step == "preflight_checks"
    assert result.error_code == "MISSING_BINARIES"
    assert len(result.steps) == 1
    # Steps after preflight should NOT have been called
    mocks["init_database"].assert_not_called()
    mocks["create_account"].assert_not_called()


@patch("server.setup.runner.detect_lan_ip", return_value="192.168.1.42")
def test_run_setup_resumes_from_state(_mock_ip, config, state_path):
    """Steps 0-1 already done in state → they are NOT called again."""
    # Pre-populate state with first 2 steps done
    from server.setup.state import SetupState

    state = SetupState(started_at="2026-01-01T00:00:00+00:00")
    mark_step_done(state, "preflight_checks")
    mark_step_done(state, "init_database")
    write_state(state_path, state)

    patcher, mocks = _patch_all_steps()
    with patcher:
        result = run_setup(config, state_path)

    assert result.success is True
    # First two steps skipped (already done)
    mocks["preflight_checks"].assert_not_called()
    mocks["init_database"].assert_not_called()
    # Remaining 5 steps should run
    mocks["configure_access"].assert_called_once()
    mocks["start_database"].assert_called_once()
    mocks["create_account"].assert_called_once()
    mocks["create_database"].assert_called_once()
    mocks["generate_certificates"].assert_called_once()
    assert len(result.steps) == 5


@patch("server.setup.runner.detect_lan_ip", return_value="127.0.0.1")
def test_run_setup_retries_recoverable(_mock_ip, config, state_path):
    """Recoverable step fails once, succeeds on retry → called twice, success."""
    mock_create = MagicMock(
        side_effect=[_fail("create_account"), _ok("create_account")]
    )
    patcher, mocks = _patch_all_steps(overrides={"create_account": mock_create})
    with patcher:
        result = run_setup(config, state_path)

    assert result.success is True
    assert mock_create.call_count == 2


@patch("server.setup.runner.detect_lan_ip", return_value="192.168.1.42")
def test_run_setup_skips_optional_on_failure(_mock_ip, config, state_path):
    """Optional step (generate_certificates) fails → overall success still True."""
    patcher, mocks = _patch_all_steps(
        overrides={"generate_certificates": _fail("generate_certificates", "CERT_ERR")}
    )
    with patcher:
        result = run_setup(config, state_path)

    assert result.success is True
    assert result.failed_step is None
    # The failed step should still appear in results
    cert_results = [r for r in result.steps if r.step == "generate_certificates"]
    assert len(cert_results) == 1
    assert cert_results[0].status == "failed"


@patch("server.setup.runner.detect_lan_ip", return_value="192.168.1.42")
def test_run_setup_calls_progress_callback(_mock_ip, config, state_path):
    """on_progress callback is called once per step."""
    callback = MagicMock()
    patcher, mocks = _patch_all_steps()
    with patcher:
        result = run_setup(config, state_path, on_progress=callback)

    assert result.success is True
    assert callback.call_count == 7
    # Each call receives a StepResult
    for call_args in callback.call_args_list:
        arg = call_args[0][0]
        assert isinstance(arg, StepResult)
