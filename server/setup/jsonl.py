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


def emit_boot_started(version: str, build_type: str = "unknown") -> None:
    """Emit when __main__ block begins execution."""
    emit_jsonl({
        "type": "boot_started",
        "version": version,
        "build_type": build_type,
    })


def emit_setup_substep(step: str, detail: str) -> None:
    """Emit a sub-step detail message for enriched progress display."""
    emit_jsonl({
        "type": "setup_substep",
        "step": step,
        "detail": detail,
    })


def emit_setup_error(
    step: str,
    error_code: str,
    error_detail: str,
    pg_log_tail: str = "",
    suggestion: str = "",
) -> None:
    """Emit a setup error with full diagnostic info."""
    emit_jsonl({
        "type": "setup_error",
        "step": step,
        "error_code": error_code,
        "error_detail": error_detail,
        "pg_log_tail": pg_log_tail,
        "suggestion": suggestion,
    })


# Error code to user-friendly suggestion mapping
SUGGESTIONS: dict[str, str] = {
    "PORT_CONFLICT": "Port 5432 is already in use. Close any other PostgreSQL instances.",
    "LOW_DISK": "Less than 500MB free disk space. Free up space and retry.",
    "MISSING_BINARIES": "PostgreSQL binaries not found. The installation may be corrupted.",
    "INITDB_TIMEOUT": "Database initialization timed out. Check antivirus is not blocking.",
    "INITDB_FAILED": "Database initialization failed. Check disk permissions.",
    "START_TIMEOUT": "PostgreSQL failed to start. Check resources/bin/postgresql/pg.log",
    "START_FAILED": "PostgreSQL failed to start. Check if port 5432 is available.",
    "CERT_GENERATION_FAILED": "TLS certificate generation failed. Check disk space.",
    "MISSING_CRYPTOGRAPHY": "Python cryptography package not installed.",
    "CREATE_USER_FAILED": "Could not create database user. Check PostgreSQL logs.",
    "CREATE_DB_FAILED": "Could not create database. Check PostgreSQL logs.",
    "TUNE_FAILED": "Performance tuning failed. PG will work with default settings.",
}


def get_suggestion(error_code: str) -> str:
    """Get a user-friendly suggestion for an error code."""
    return SUGGESTIONS.get(error_code, "Check the application logs for details.")
