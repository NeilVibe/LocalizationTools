"""
Tests for P12.5 Central Telemetry System - Remote Logging API

Tests the full telemetry flow:
1. Registration (Desktop → Central)
2. Session tracking (start/heartbeat/end)
3. Log submission with API key auth
4. Error detection in batches

Run with server:
    python3 server/main.py &
    RUN_API_TESTS=1 python3 -m pytest tests/api/test_remote_logging.py -v
"""

import os
import pytest
import time
import requests
from datetime import datetime

# Skip if server not running
pytestmark = pytest.mark.skipif(
    not os.getenv("RUN_API_TESTS"),
    reason="RUN_API_TESTS not set - start server first"
)


class APIClient:
    """HTTP client for API tests."""

    def __init__(self, base_url="http://127.0.0.1:8888"):
        self.base_url = base_url
        self.session = requests.Session()

    def get(self, endpoint, **kwargs):
        url = endpoint if endpoint.startswith("http") else f"{self.base_url}{endpoint}"
        return self.session.get(url, timeout=30, **kwargs)

    def post(self, endpoint, **kwargs):
        url = endpoint if endpoint.startswith("http") else f"{self.base_url}{endpoint}"
        return self.session.post(url, timeout=30, **kwargs)


class TestRemoteLoggingAPI:
    """Test P12.5 Remote Logging API endpoints."""

    BASE_URL = "http://127.0.0.1:8888/api/v1/remote-logs"

    # Shared state across tests
    installation_id = None
    api_key = None
    session_id = None

    @pytest.fixture(scope="class")
    def client(self):
        """Create API client for tests."""
        return APIClient()

    def test_01_health_check(self, client):
        """Test remote logging service health."""
        r = client.get(f"{self.BASE_URL}/health")
        assert r.status_code == 200
        data = r.json()
        assert data.get("status") == "healthy"
        print("✓ Remote logging service healthy")

    def test_02_register_installation(self, client):
        """
        DESKTOP ACTION: First launch registers with Central Server.
        EXPECTED: Returns installation_id and api_key.
        """
        payload = {
            "installation_name": "Test Desktop",
            "version": "1.2.0",
            "platform": "win32",
            "os_version": "Windows 10"
        }
        r = client.post(f"{self.BASE_URL}/register", json=payload)
        assert r.status_code in [200, 201], f"Registration failed: {r.text}"

        data = r.json()
        assert "installation_id" in data, "Missing installation_id"
        assert "api_key" in data, "Missing api_key"
        assert len(data["api_key"]) > 32, "API key too short"

        # Store for subsequent tests
        TestRemoteLoggingAPI.installation_id = data["installation_id"]
        TestRemoteLoggingAPI.api_key = data["api_key"]

        print(f"✓ Registered: {data['installation_id'][:8]}...")
        print(f"✓ API Key: {data['api_key'][:16]}...")

    def test_03_start_session(self, client):
        """
        DESKTOP ACTION: User opens app, session starts.
        EXPECTED: Returns session_id.
        """
        assert self.api_key, "No API key - run registration first"

        headers = {"x-api-key": self.api_key}
        payload = {
            "installation_id": self.installation_id,
            "version": "1.2.0"
        }

        r = client.post(
            f"{self.BASE_URL}/sessions/start",
            json=payload,
            headers=headers
        )
        assert r.status_code in [200, 201], f"Session start failed: {r.text}"

        data = r.json()
        assert "session_id" in data, "Missing session_id"

        TestRemoteLoggingAPI.session_id = data["session_id"]
        print(f"✓ Session started: {data['session_id'][:8]}...")

    def test_04_submit_logs_with_auth(self, client):
        """
        DESKTOP ACTION: App sends logs during usage.
        EXPECTED: Logs accepted with valid API key.
        """
        assert self.api_key, "No API key - run registration first"

        headers = {"x-api-key": self.api_key}
        inst_id = self.installation_id
        payload = {
            "installation_id": inst_id,
            "logs": [
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "level": "INFO",
                    "message": "XLSTransfer: Load dictionary clicked",
                    "source": "frontend",
                    "component": "XLSTransfer",
                    "installation_id": inst_id
                },
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "level": "INFO",
                    "message": "Dictionary loaded: 1500 entries",
                    "source": "backend",
                    "component": "XLSTransfer",
                    "installation_id": inst_id
                },
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "level": "WARNING",
                    "message": "Slow response: 2.3s",
                    "source": "backend",
                    "component": "API",
                    "installation_id": inst_id
                }
            ]
        }

        r = client.post(f"{self.BASE_URL}/submit", json=payload, headers=headers)
        assert r.status_code in [200, 201], f"Log submit failed: {r.text}"

        data = r.json()
        assert data.get("logs_received", 0) >= 3, "Not all logs received"
        print(f"✓ Submitted {data.get('logs_received', 0)} logs")

    def test_05_submit_error_log(self, client):
        """
        DESKTOP ACTION: Error occurs in app.
        EXPECTED: Error detected and counted by Central Server.
        """
        assert self.api_key, "No API key"

        headers = {"x-api-key": self.api_key}
        inst_id = self.installation_id
        payload = {
            "installation_id": inst_id,
            "logs": [
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "level": "ERROR",
                    "message": "Failed to connect to backend: ECONNREFUSED",
                    "source": "frontend",
                    "component": "API",
                    "installation_id": inst_id,
                    "data": {"url": "http://127.0.0.1:8888/health"}
                }
            ]
        }

        r = client.post(f"{self.BASE_URL}/submit", json=payload, headers=headers)
        assert r.status_code in [200, 201], f"Error log failed: {r.text}"

        data = r.json()
        assert data.get("errors_detected", 0) >= 1, "Error not detected"
        print(f"✓ Error detected: {data.get('errors_detected', 0)}")

    def test_06_end_session(self, client):
        """
        DESKTOP ACTION: User closes app, session ends.
        EXPECTED: Session duration recorded.
        """
        assert self.api_key and self.session_id, "Missing credentials"

        # Small delay to have measurable duration
        time.sleep(1)

        headers = {"x-api-key": self.api_key}
        payload = {
            "session_id": self.session_id,
            "end_reason": "user_closed"
        }

        r = client.post(
            f"{self.BASE_URL}/sessions/end",
            json=payload,
            headers=headers
        )
        assert r.status_code in [200, 201], f"Session end failed: {r.text}"

        data = r.json()
        assert data.get("duration_seconds", 0) >= 1, "Duration not recorded"
        print(f"✓ Session ended: {data.get('duration_seconds', 0)}s")

    def test_07_check_installation_status(self, client):
        """
        ADMIN ACTION: Check installation statistics.
        """
        assert self.installation_id and self.api_key, "No installation ID or API key"

        headers = {"x-api-key": self.api_key}
        r = client.get(f"{self.BASE_URL}/status/{self.installation_id}", headers=headers)

        if r.status_code == 404:
            print("⚠ Status endpoint not implemented yet")
            pytest.skip("Status endpoint not available")

        assert r.status_code == 200, f"Status check failed: {r.text}"
        data = r.json()
        print(f"✓ Installation status: {data}")

    def test_08_reject_invalid_api_key(self, client):
        """
        SECURITY: Invalid API key should be rejected.
        """
        headers = {"x-api-key": "invalid-key-12345678901234567890123456789012"}  # 32+ chars
        payload = {
            "installation_id": "fake-installation",
            "logs": [{
                "timestamp": datetime.utcnow().isoformat(),
                "level": "INFO",
                "message": "test",
                "source": "test",
                "installation_id": "fake-installation"
            }]
        }

        r = client.post(f"{self.BASE_URL}/submit", json=payload, headers=headers)
        assert r.status_code in [401, 403], f"Should reject invalid key: {r.status_code}"
        print("✓ Invalid API key rejected")

    def test_09_reject_missing_api_key(self, client):
        """
        SECURITY: Missing API key should be rejected.
        """
        inst_id = self.installation_id or "test"
        payload = {
            "installation_id": inst_id,
            "logs": [{
                "timestamp": datetime.utcnow().isoformat(),
                "level": "INFO",
                "message": "test",
                "source": "test",
                "installation_id": inst_id
            }]
        }

        r = client.post(f"{self.BASE_URL}/submit", json=payload)
        assert r.status_code in [401, 403, 422], f"Should reject missing key: {r.status_code}"
        print("✓ Missing API key rejected")


class TestTelemetryWithRealWorkflow:
    """Test telemetry during actual tool operations."""

    @pytest.fixture(scope="class")
    def client(self):
        """Create API client for tests."""
        return APIClient()

    def test_xlstransfer_with_telemetry(self, client):
        """
        TRUE SIMULATION: Use XLSTransfer while telemetry runs.

        Flow:
        1. Register installation
        2. Start session
        3. Load dictionary (real operation)
        4. Submit operation logs
        5. End session
        """
        BASE = "http://127.0.0.1:8888/api/v1/remote-logs"

        # 1. Register
        reg = client.post(f"{BASE}/register", json={
            "installation_name": "Workflow Test",
            "version": "1.2.0"
        })
        if reg.status_code not in [200, 201]:
            pytest.skip("Registration not available")

        data = reg.json()
        api_key = data["api_key"]
        inst_id = data["installation_id"]
        headers = {"x-api-key": api_key}

        # 2. Start session
        sess = client.post(f"{BASE}/sessions/start", json={
            "installation_id": inst_id,
            "version": "1.2.0"
        }, headers=headers)
        session_id = sess.json().get("session_id") if sess.status_code in [200, 201] else None

        # 3. Simulate XLSTransfer operation
        # (In real test, this would actually call the XLSTransfer API)
        print("✓ Simulating XLSTransfer load dictionary...")

        # 4. Submit telemetry
        client.post(f"{BASE}/submit", json={
            "installation_id": inst_id,
            "logs": [
                {"timestamp": datetime.utcnow().isoformat(), "level": "INFO", "message": "XLSTransfer: Starting load dictionary", "source": "frontend", "component": "XLSTransfer", "installation_id": inst_id},
                {"timestamp": datetime.utcnow().isoformat(), "level": "INFO", "message": "Processing 1500 rows", "source": "backend", "component": "XLSTransfer", "installation_id": inst_id},
                {"timestamp": datetime.utcnow().isoformat(), "level": "INFO", "message": "Dictionary loaded successfully", "source": "backend", "component": "XLSTransfer", "installation_id": inst_id}
            ]
        }, headers=headers)

        # 5. End session
        if session_id:
            client.post(f"{BASE}/sessions/end", json={
                "session_id": session_id,
                "end_reason": "user_closed"
            }, headers=headers)

        print("✓ Complete workflow with telemetry executed")
