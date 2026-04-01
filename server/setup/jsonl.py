"""JSONL stdout emitter for the setup wizard.

Every function writes a single JSON object + newline to stdout and flushes
immediately so Electron's line-buffered reader gets each message in real time.
"""
from __future__ import annotations

import json
import sys

from server.setup import StepResult
from server.setup.state import STEP_NAMES


def emit_jsonl(msg: dict) -> None:
    """Write a JSON object as a single line to stdout and flush."""
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()


def emit_setup_started(run_id: str) -> None:
    """Emit the setup_started event with total step count."""
    emit_jsonl({
        "type": "setup_started",
        "run_id": run_id,
        "total_steps": len(STEP_NAMES),
        "protocol_version": 1,
    })


def emit_setup_step(result: StepResult, run_id: str) -> None:
    """Emit progress for a single setup step."""
    index = STEP_NAMES.index(result.step) if result.step in STEP_NAMES else -1
    msg: dict = {
        "type": "setup_step",
        "run_id": run_id,
        "step": result.step,
        "index": index,
        "total": len(STEP_NAMES),
        "status": result.status,
        "duration_ms": result.duration_ms,
        "message": result.message,
    }
    if result.error_code:
        msg["error_code"] = result.error_code
    if result.error_detail:
        msg["error_detail"] = result.error_detail
    emit_jsonl(msg)


def emit_setup_complete(
    success: bool,
    run_id: str,
    lan_ip: str | None = None,
    failed_step: str | None = None,
    error_code: str | None = None,
    error_detail: str | None = None,
) -> None:
    """Emit the final setup_complete event."""
    msg: dict = {"type": "setup_complete", "run_id": run_id, "success": success}
    if success and lan_ip:
        msg["lan_ip"] = lan_ip
    if not success:
        if failed_step:
            msg["failed_step"] = failed_step
        if error_code:
            msg["error_code"] = error_code
        if error_detail:
            msg["error_detail"] = error_detail
    emit_jsonl(msg)


def emit_pg_starting() -> None:
    """Emit when PG is about to start on a subsequent (non-first) launch."""
    emit_jsonl({"type": "pg_starting"})


def emit_pg_ready() -> None:
    """Emit when PG is confirmed running."""
    emit_jsonl({"type": "pg_ready"})


def emit_server_ready(port: int) -> None:
    """Emit when the FastAPI server is ready to accept connections."""
    emit_jsonl({"type": "server_ready", "port": port})
