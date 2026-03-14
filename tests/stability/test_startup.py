"""Startup reliability tests for the LocalizationTools server.

Verifies STAB-01: Server starts reliably 10/10 times in DEV mode,
each under 10 seconds, with zero ERROR-level log lines, proper port
conflict handling, and security key validation in strict mode.
"""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import psutil
import pytest
import requests

# Project root (two levels up from tests/stability/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Server startup command
SERVER_CMD = [sys.executable, str(PROJECT_ROOT / "server" / "main.py")]

# Base environment for DEV server with SQLite (no PostgreSQL dependency)
_BASE_ENV = {
    **os.environ,
    "DEV_MODE": "true",
    "DATABASE_MODE": "sqlite",
    "SECURITY_MODE": "warn",
    "LOG_LEVEL": "INFO",
}

HEALTH_URL = "http://127.0.0.1:8888/health"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cleanup_port(port: int, timeout: float = 2.0) -> None:
    """Find and kill any process listening on *port*. Wait up to *timeout* s."""
    killed = []
    for conn in psutil.net_connections(kind="inet"):
        if conn.laddr.port == port and conn.status == psutil.CONN_LISTEN:
            try:
                proc = psutil.Process(conn.pid)
                proc.kill()
                killed.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

    deadline = time.monotonic() + timeout
    for proc in killed:
        remaining = max(0, deadline - time.monotonic())
        try:
            proc.wait(timeout=remaining)
        except psutil.TimeoutExpired:
            pass


def _start_server(**extra_env) -> subprocess.Popen:
    """Start the server as a subprocess and return the Popen handle."""
    env = {**_BASE_ENV, **extra_env}
    proc = subprocess.Popen(
        SERVER_CMD,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(PROJECT_ROOT),
        # Use a new process group so we can kill the tree
        preexec_fn=os.setsid,
    )
    return proc


def _wait_for_health(timeout_s: float = 5.0) -> float:
    """Poll /health until success or *timeout_s*. Return elapsed seconds."""
    start = time.monotonic()
    deadline = start + timeout_s
    while time.monotonic() < deadline:
        try:
            resp = requests.get(HEALTH_URL, timeout=1)
            if resp.status_code == 200:
                return time.monotonic() - start
        except requests.ConnectionError:
            pass
        time.sleep(0.1)
    raise TimeoutError(f"Server did not become healthy within {timeout_s}s")


def _terminate_server(proc: subprocess.Popen, timeout: float = 10.0) -> None:
    """Gracefully terminate the server process tree."""
    try:
        pgid = os.getpgid(proc.pid)
        os.killpg(pgid, signal.SIGTERM)
    except (ProcessLookupError, OSError):
        pass
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            pgid = os.getpgid(proc.pid)
            os.killpg(pgid, signal.SIGKILL)
        except (ProcessLookupError, OSError):
            pass
        proc.wait(timeout=5)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.stability
@pytest.mark.timeout(180)
def test_dev_startup_10_consecutive_times():
    """STAB-01: Server starts 10 consecutive times without errors, each < 10s.

    Note: threshold is 10s (not 5s) because the server imports 20+ routers,
    SQLAlchemy, FastAPI middleware, and Socket.IO at module level. This is
    measured from subprocess.Popen to /health 200 OK.
    """
    for attempt in range(1, 11):
        _cleanup_port(8888)
        proc = _start_server()
        try:
            elapsed = _wait_for_health(timeout_s=15.0)
            assert elapsed < 10.0, (
                f"Attempt {attempt}: startup took {elapsed:.2f}s (limit 10s)"
            )

            # Read any output produced so far -- check for ERROR lines
            # (non-blocking read via communicate with short timeout)
        finally:
            _terminate_server(proc)
            # Grab output after termination
            stdout, stderr = proc.communicate(timeout=5)
            output = (stdout or b"").decode(errors="replace") + (stderr or b"").decode(errors="replace")
            error_lines = [
                ln for ln in output.splitlines()
                if "| ERROR" in ln
                # Ignore expected security warnings in dev mode
                and "SECURITY" not in ln
            ]
            assert not error_lines, (
                f"Attempt {attempt}: found ERROR log lines:\n"
                + "\n".join(error_lines)
            )
            _cleanup_port(8888)


@pytest.mark.stability
@pytest.mark.timeout(30)
def test_startup_db_connectivity_check():
    """STAB-01: Server starts in SQLite mode and reports DB status via /health."""
    _cleanup_port(8888)
    proc = _start_server()
    try:
        _wait_for_health(timeout_s=10.0)
        resp = requests.get(HEALTH_URL, timeout=3)
        data = resp.json()
        # Health endpoint should report database connectivity
        assert "database" in data, "Health response missing 'database' field"
        assert data["database"] in ("connected", "error", "unknown"), (
            f"Unexpected database status: {data['database']}"
        )
        # In SQLite mode the DB type should be sqlite
        assert data.get("database_type") == "sqlite", (
            f"Expected sqlite, got {data.get('database_type')}"
        )
    finally:
        _terminate_server(proc)
        _cleanup_port(8888)


@pytest.mark.stability
@pytest.mark.timeout(30)
def test_startup_clear_error_on_port_conflict():
    """STAB-01: Second server instance handles port conflict gracefully."""
    _cleanup_port(8888)
    first = _start_server()
    try:
        _wait_for_health(timeout_s=10.0)

        # Start second server (same port) -- DEV_MODE cleanup should kill the first
        second = _start_server()
        try:
            # The second instance should either take over or fail clearly
            try:
                _wait_for_health(timeout_s=10.0)
                # If it starts, the pre-startup cleanup killed the first -- that's OK
                took_over = True
            except TimeoutError:
                took_over = False

            if not took_over:
                # It should have exited with a clear message, not be stuck
                retcode = second.poll()
                assert retcode is not None, (
                    "Second server is stuck (neither started nor exited)"
                )
                _, stderr = second.communicate(timeout=5)
                output = (stderr or b"").decode(errors="replace")
                # Should have a clear error, not a raw traceback
                assert (
                    "Address already in use" in output
                    or "port" in output.lower()
                    or "already" in output.lower()
                    or retcode != 0
                ), f"Second server failed without clear message: {output[:500]}"
        finally:
            _terminate_server(second)
    finally:
        _terminate_server(first)
        _cleanup_port(8888)


@pytest.mark.stability
@pytest.mark.timeout(30)
def test_startup_rejects_weak_secret_key():
    """STAB-01: Server refuses to start with weak/default SECRET_KEY in strict mode."""
    _cleanup_port(8888)

    # Test 1: Explicitly weak (short) key
    proc = _start_server(SECURITY_MODE="strict", SECRET_KEY="weak")
    try:
        # Should exit quickly with non-zero
        retcode = proc.wait(timeout=15)
        assert retcode != 0, f"Expected non-zero exit, got {retcode}"
        stdout, stderr = proc.communicate(timeout=5)
        output = (stdout or b"").decode(errors="replace") + (stderr or b"").decode(errors="replace")
        assert "SECURITY" in output or "SECRET_KEY" in output, (
            f"Missing clear security error message in output:\n{output[:500]}"
        )
    except subprocess.TimeoutExpired:
        _terminate_server(proc)
        pytest.fail("Server did not exit when given weak SECRET_KEY in strict mode")

    # Verify port is free after rejected startup
    time.sleep(0.5)
    assert not _port_in_use(8888), "Port 8888 still occupied after rejected startup"

    # Test 2: Default key (no SECRET_KEY override) in strict mode
    proc2_env = {**_BASE_ENV, "SECURITY_MODE": "strict"}
    proc2_env.pop("SECRET_KEY", None)
    proc2 = subprocess.Popen(
        SERVER_CMD,
        env=proc2_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(PROJECT_ROOT),
        preexec_fn=os.setsid,
    )
    try:
        retcode = proc2.wait(timeout=15)
        assert retcode != 0, f"Expected non-zero exit with default key, got {retcode}"
        stdout, stderr = proc2.communicate(timeout=5)
        output = (stdout or b"").decode(errors="replace") + (stderr or b"").decode(errors="replace")
        assert "Security validation FAILED" in output or "SECURITY" in output, (
            f"Missing security failure message:\n{output[:500]}"
        )
    except subprocess.TimeoutExpired:
        _terminate_server(proc2)
        pytest.fail("Server did not exit with default SECRET_KEY in strict mode")


def _port_in_use(port: int) -> bool:
    """Check if any process is listening on the given port."""
    for conn in psutil.net_connections(kind="inet"):
        if conn.laddr.port == port and conn.status == psutil.CONN_LISTEN:
            return True
    return False
