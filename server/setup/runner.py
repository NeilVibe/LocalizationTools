"""Sequential setup runner with state tracking, resume, and progress callbacks."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from server.setup import SetupConfig, SetupResult, StepResult
from server.setup.network import detect_lan_ip
from server.setup.state import (
    STEP_NAMES,
    SetupState,
    mark_step_done,
    mark_step_failed,
    read_state,
    write_state,
)
from server.setup.steps import (
    step_configure_access,
    step_create_account,
    step_create_database,
    step_generate_certificates,
    step_init_database,
    step_preflight_checks,
    step_start_database,
    step_tune_performance,
)

from loguru import logger

# ---------------------------------------------------------------------------
# Step registry
# ---------------------------------------------------------------------------

STEP_FUNCTIONS: dict[str, Callable[[SetupConfig], StepResult]] = {
    "preflight_checks": step_preflight_checks,
    "init_database": step_init_database,
    "configure_access": step_configure_access,
    "generate_certificates": step_generate_certificates,
    "start_database": step_start_database,
    "tune_performance": step_tune_performance,
    "create_account": step_create_account,
    "create_database": step_create_database,
}

# Step classification - determines behavior on failure
FATAL_STEPS: set[str] = {
    "preflight_checks",
    "init_database",
    "configure_access",
    "generate_certificates",
    "start_database",
}
RECOVERABLE_STEPS: set[str] = {"create_account", "create_database"}
OPTIONAL_STEPS: set[str] = {"tune_performance"}

_MAX_RETRIES = 1  # auto-retry count for recoverable steps


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def run_setup(
    config: SetupConfig,
    state_path: Path,
    on_progress: Callable[[StepResult], None] | None = None,
) -> SetupResult:
    """Run setup steps sequentially with state tracking and resume.

    1. Read state file (supports resume after crash).
    2. Initialise ``run_id`` / ``started_at`` if this is a fresh run.
    3. For each step in :data:`STEP_NAMES`:
       a. **Skip** if already marked *done* in state.
       b. Execute the step function with *config*.
       c. If the step fails and is **recoverable**, auto-retry once.
       d. Persist state to disk after every step.
       e. Fire *on_progress* callback (if provided).
       f. If failed and **fatal** → stop immediately, return failure.
       g. If failed and **optional** → mark done, continue.
    4. When all steps complete: set ``completed_at``, return success
       with the detected LAN IP.
    """
    logger.info("=" * 60)
    logger.info("SETUP WIZARD START")
    logger.info("=" * 60)
    logger.info("  pg_bin_dir: {}", config.pg_bin_dir)
    logger.info("  data_dir:   {}", config.data_dir)
    logger.info("  pg_port:    {}", config.pg_port)
    logger.info("  state_path: {}", state_path)

    state = read_state(state_path)

    # Initialise run metadata on first invocation
    if state.started_at is None:
        state.run_id = uuid.uuid4().hex[:12]
        state.started_at = datetime.now(timezone.utc).isoformat()
        write_state(state_path, state)

    results: list[StepResult] = []

    for step_name in STEP_NAMES:
        # ----- resume: skip already-done steps -----
        step_info = state.steps.get(step_name, {})
        if step_info.get("status") == "done":
            logger.info("Skipping already-done step: {}", step_name)
            continue

        step_fn = STEP_FUNCTIONS[step_name]
        step_index = STEP_NAMES.index(step_name)
        logger.info("[SETUP {}/{}] Running: {}", step_index + 1, len(STEP_NAMES), step_name)
        result = _run_step_with_retry(step_name, step_fn, config)
        logger.info("[SETUP {}/{}] {} → {} ({}ms) {}",
                     step_index + 1, len(STEP_NAMES), step_name,
                     result.status, result.duration_ms, result.message)

        # ----- persist state -----
        if result.status in ("done", "skipped"):
            mark_step_done(state, step_name)
        else:
            # Failed - handle based on classification
            if step_name in OPTIONAL_STEPS:
                # Optional steps don't block - mark done and continue
                logger.warning(
                    "Optional step '{}' failed, continuing: {}",
                    step_name,
                    result.message,
                )
                mark_step_done(state, step_name)
            else:
                mark_step_failed(state, step_name, result.message)

        write_state(state_path, state)
        results.append(result)

        if on_progress is not None:
            on_progress(result)

        # ----- fatal failure: abort -----
        if result.status == "failed" and step_name in FATAL_STEPS:
            logger.error("Fatal step '{}' failed - aborting setup", step_name)
            return SetupResult(
                success=False,
                steps=results,
                failed_step=step_name,
                error_code=result.error_code,
                error_detail=result.error_detail or result.message,
            )

        # ----- recoverable failure (after retry exhausted) -----
        if result.status == "failed" and step_name in RECOVERABLE_STEPS:
            logger.error(
                "Recoverable step '{}' failed after retry - aborting setup",
                step_name,
            )
            return SetupResult(
                success=False,
                steps=results,
                failed_step=step_name,
                error_code=result.error_code,
                error_detail=result.error_detail or result.message,
            )

    # ----- all steps done -----
    state.completed_at = datetime.now(timezone.utc).isoformat()
    write_state(state_path, state)

    lan_ip: str | None = None
    try:
        lan_ip = detect_lan_ip()
    except Exception as exc:
        logger.warning("LAN IP detection failed: {}", exc)

    logger.info("=" * 60)
    logger.info("SETUP WIZARD COMPLETE - LAN IP: {}", lan_ip)
    logger.info("=" * 60)
    return SetupResult(success=True, steps=results, lan_ip=lan_ip)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _run_step_with_retry(
    step_name: str,
    step_fn: Callable[[SetupConfig], StepResult],
    config: SetupConfig,
) -> StepResult:
    """Execute *step_fn*; auto-retry once if the step is recoverable."""
    result = step_fn(config)

    if result.status != "failed":
        return result

    if step_name not in RECOVERABLE_STEPS:
        return result

    # Auto-retry recoverable steps
    for attempt in range(1, _MAX_RETRIES + 1):
        logger.info(
            "Retrying recoverable step '{}' (attempt {}/{})",
            step_name,
            attempt,
            _MAX_RETRIES,
        )
        result = step_fn(config)
        if result.status != "failed":
            return result

    return result
