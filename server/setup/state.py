"""Setup wizard state file for crash recovery.

Persists progress as JSON so a failed/interrupted setup can resume
from the last successful step.
"""
from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

STEP_NAMES: list[str] = [
    "preflight_checks",
    "init_database",
    "configure_access",
    "generate_certificates",
    "start_database",
    "create_account",
    "create_database",
]


@dataclass
class SetupState:
    """In-memory representation of the setup state file."""
    version: int = 1
    pg_major_version: int | None = None
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    started_at: str | None = None
    completed_at: str | None = None
    steps: dict[str, Any] = field(default_factory=dict)
    config: dict[str, Any] = field(default_factory=dict)


def read_state(path: Path) -> SetupState:
    """Read state from *path*, returning an empty state if the file is missing."""
    if not path.exists():
        return SetupState()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return SetupState(
            version=data.get("version", 1),
            pg_major_version=data.get("pg_major_version"),
            run_id=data.get("run_id", uuid.uuid4().hex[:12]),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            steps=data.get("steps", {}),
            config=data.get("config", {}),
        )
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Corrupt state file %s, starting fresh: %s", path, exc)
        return SetupState()


def write_state(path: Path, state: SetupState) -> None:
    """Persist *state* to *path*, creating parent directories as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "version": state.version,
        "pg_major_version": state.pg_major_version,
        "run_id": state.run_id,
        "started_at": state.started_at,
        "completed_at": state.completed_at,
        "steps": state.steps,
        "config": state.config,
    }
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def mark_step_done(state: SetupState, step: str) -> None:
    """Record *step* as successfully completed."""
    state.steps[step] = {"status": "done", "timestamp": _utc_now()}


def mark_step_failed(state: SetupState, step: str, error: str = "") -> None:
    """Record *step* as failed with an optional error description."""
    state.steps[step] = {
        "status": "failed",
        "error": error,
        "timestamp": _utc_now(),
    }


def get_first_incomplete_step(state: SetupState) -> str | None:
    """Return the first step that is not 'done', or None if all are complete."""
    for step in STEP_NAMES:
        info = state.steps.get(step, {})
        if info.get("status") != "done":
            return step
    return None


def is_setup_complete(state: SetupState) -> bool:
    """Return True if every step has status 'done'."""
    return get_first_incomplete_step(state) is None
