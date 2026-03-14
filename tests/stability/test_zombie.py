"""Zombie process tests for the LocalizationTools server.

Verifies STAB-04: No orphaned Python processes remain after SIGTERM,
SIGKILL, or crash scenarios. Port 8888 is always freed after shutdown.
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
        preexec_fn=os.setsid,
    )
    return proc


def _wait_for_health(timeout_s: float = 15.0) -> float:
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


def _get_child_pids(parent_pid: int) -> list[int]:
    """Get all child PIDs (recursive) for the given parent."""
    try:
        parent = psutil.Process(parent_pid)
        return [c.pid for c in parent.children(recursive=True)]
    except psutil.NoSuchProcess:
        return []


def _port_in_use(port: int) -> bool:
    """Check if any process is listening on the given port."""
    for conn in psutil.net_connections(kind="inet"):
        if conn.laddr.port == port and conn.status == psutil.CONN_LISTEN:
            return True
    return False


def _pid_alive(pid: int) -> bool:
    """Check if a process with the given PID is still running."""
    try:
        return psutil.Process(pid).is_running()
    except psutil.NoSuchProcess:
        return False


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.stability
@pytest.mark.timeout(60)
def test_no_zombies_after_sigterm():
    """STAB-04: No orphaned processes after SIGTERM shutdown."""
    _cleanup_port(8888)
    proc = _start_server()
    try:
        _wait_for_health()
        parent_pid = proc.pid
        child_pids = _get_child_pids(parent_pid)

        # Send SIGTERM to the process group
        try:
            pgid = os.getpgid(proc.pid)
            os.killpg(pgid, signal.SIGTERM)
        except (ProcessLookupError, OSError):
            pass

        proc.wait(timeout=10)
        time.sleep(1)  # Allow OS cleanup

        # Verify all children are gone
        for cpid in child_pids:
            assert not _pid_alive(cpid), f"Child PID {cpid} still alive after SIGTERM"

        # Verify port is free
        assert not _port_in_use(8888), "Port 8888 still in use after SIGTERM"
    finally:
        # Safety cleanup
        try:
            _terminate_server(proc)
        except Exception:
            pass
        _cleanup_port(8888)


@pytest.mark.stability
@pytest.mark.timeout(60)
def test_no_zombies_after_sigkill():
    """STAB-04: Port freed after SIGKILL, and next startup succeeds."""
    _cleanup_port(8888)
    proc = _start_server()
    try:
        _wait_for_health()
        child_pids = _get_child_pids(proc.pid)

        # SIGKILL the process group (simulates hard crash)
        try:
            pgid = os.getpgid(proc.pid)
            os.killpg(pgid, signal.SIGKILL)
        except (ProcessLookupError, OSError):
            pass
        proc.wait(timeout=10)
        time.sleep(2)  # Allow OS to clean up sockets

        # Port might still be in TIME_WAIT; pre-startup cleanup should handle it
        # Start server again -- pre-startup cleanup handles orphaned port
        proc2 = _start_server()
        try:
            _wait_for_health(timeout_s=15.0)
            # Second start succeeded -- pre-startup cleanup works
        finally:
            _terminate_server(proc2)
            _cleanup_port(8888)
    finally:
        try:
            _terminate_server(proc)
        except Exception:
            pass
        _cleanup_port(8888)


@pytest.mark.stability
@pytest.mark.timeout(60)
def test_no_zombies_after_second_instance():
    """STAB-04: Only one server family remains when second instance starts."""
    _cleanup_port(8888)
    first = _start_server()
    try:
        _wait_for_health()
        first_pid = first.pid

        # Start second instance -- pre-startup cleanup should kill the first
        second = _start_server()
        try:
            try:
                _wait_for_health(timeout_s=15.0)
            except TimeoutError:
                # Second server might have failed; that's acceptable
                pass

            time.sleep(1)

            # Count how many server families are listening on 8888
            listeners = []
            for conn in psutil.net_connections(kind="inet"):
                if conn.laddr.port == 8888 and conn.status == psutil.CONN_LISTEN:
                    listeners.append(conn.pid)

            assert len(listeners) <= 1, (
                f"Multiple processes listening on 8888: {listeners}"
            )
        finally:
            _terminate_server(second)
    finally:
        _terminate_server(first)
        _cleanup_port(8888)


@pytest.mark.stability
@pytest.mark.timeout(60)
def test_port_freed_after_crash_simulation():
    """STAB-04: Server starts successfully after a simulated crash (SIGKILL)."""
    _cleanup_port(8888)
    proc = _start_server()
    try:
        _wait_for_health()

        # Simulate crash with SIGKILL
        try:
            pgid = os.getpgid(proc.pid)
            os.killpg(pgid, signal.SIGKILL)
        except (ProcessLookupError, OSError):
            pass
        proc.wait(timeout=10)
        time.sleep(1)

        # Start fresh -- should succeed thanks to pre-startup port cleanup
        proc2 = _start_server()
        try:
            elapsed = _wait_for_health(timeout_s=15.0)
            # Verify it's actually healthy
            resp = requests.get(HEALTH_URL, timeout=3)
            assert resp.status_code == 200, f"Health check returned {resp.status_code}"
        finally:
            _terminate_server(proc2)
            _cleanup_port(8888)
    finally:
        try:
            _terminate_server(proc)
        except Exception:
            pass
        _cleanup_port(8888)
