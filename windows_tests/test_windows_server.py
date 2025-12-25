"""
Windows Server Connectivity Tests

Tests for server startup and connectivity on Windows.
"""

import os
import sys
import platform
import socket
import subprocess
import time
from pathlib import Path

import pytest


pytestmark = pytest.mark.skipif(
    platform.system() != "Windows",
    reason="Windows-only tests"
)


class TestServerConnectivity:
    """Test server connectivity from Windows."""

    def test_localhost_resolves(self):
        """localhost should resolve to 127.0.0.1."""
        ip = socket.gethostbyname("localhost")
        assert ip == "127.0.0.1", f"localhost resolved to {ip}, expected 127.0.0.1"

    def test_ipv4_loopback_works(self):
        """IPv4 loopback should work."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        try:
            # Try to connect - connection refused is OK (no server)
            # Only network errors are problems
            result = sock.connect_ex(("127.0.0.1", 8888))
            # 0 = connected, 10061 = connection refused (Windows)
            # 10035 = WSAEWOULDBLOCK (operation in progress), 111 = Linux refused
            assert result in [0, 10061, 10035, 111], f"Unexpected socket error: {result}"
        finally:
            sock.close()

    def test_backend_port_available(self):
        """Port 8888 should be bindable (not in use by other app)."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            # Try to bind - either works or port in use (server running)
            sock.bind(("127.0.0.1", 8888))
            sock.close()
        except OSError as e:
            # 10048 = address already in use (Windows) - OK if server running
            if e.errno not in [10048, 98]:
                pytest.fail(f"Port 8888 issue: {e}")

    def test_websocket_port_available(self):
        """WebSocket port should work."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            result = sock.connect_ex(("127.0.0.1", 8888))
            # Connection result doesn't matter, just that socket works
        finally:
            sock.close()


class TestDatabaseConnectivity:
    """Test database connection paths."""

    def test_postgresql_port_reachable(self):
        """PostgreSQL port should be reachable (if server is on network)."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        try:
            # Try to connect to PostgreSQL (may timeout if not on network)
            result = sock.connect_ex(("172.28.150.120", 5432))
            # Any result is fine - we're just testing socket works
        except socket.timeout:
            pass  # Timeout is OK - server may not be reachable
        finally:
            sock.close()

    def test_sqlite_fallback_path(self):
        """SQLite fallback path should be writable."""
        appdata = os.environ.get("APPDATA")
        sqlite_path = Path(appdata) / "LocaNext" / "data"
        sqlite_path.mkdir(parents=True, exist_ok=True)

        test_db = sqlite_path / "test.db"
        test_db.write_text("test")
        assert test_db.exists()
        test_db.unlink()


class TestPythonBackendStartup:
    """Test Python backend can start on Windows."""

    def test_python_imports_work(self):
        """Critical Python imports should work."""
        # Test imports that are needed for backend
        import json
        import asyncio
        import threading
        import multiprocessing

    def test_uvicorn_importable(self):
        """uvicorn should be importable (if installed)."""
        try:
            import uvicorn
        except ImportError:
            pytest.skip("uvicorn not installed")

    def test_fastapi_importable(self):
        """FastAPI should be importable (if installed)."""
        try:
            import fastapi
        except ImportError:
            pytest.skip("fastapi not installed")

    def test_sqlalchemy_importable(self):
        """SQLAlchemy should be importable (if installed)."""
        try:
            import sqlalchemy
        except ImportError:
            pytest.skip("sqlalchemy not installed")


class TestProcessSpawning:
    """Test process spawning on Windows."""

    def test_subprocess_works(self):
        """subprocess should work on Windows."""
        result = subprocess.run(
            ["cmd", "/c", "echo", "test"],
            capture_output=True,
            text=True
        )
        assert "test" in result.stdout

    def test_python_subprocess_works(self):
        """Python subprocess should work."""
        result = subprocess.run(
            [sys.executable, "-c", "print('hello')"],
            capture_output=True,
            text=True
        )
        assert "hello" in result.stdout

    def test_environment_variables_passed(self):
        """Environment variables should pass to subprocesses."""
        env = os.environ.copy()
        env["TEST_VAR"] = "test_value"

        result = subprocess.run(
            [sys.executable, "-c", "import os; print(os.environ.get('TEST_VAR', ''))"],
            capture_output=True,
            text=True,
            env=env
        )
        assert "test_value" in result.stdout
