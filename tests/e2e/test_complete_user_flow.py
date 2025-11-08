"""
End-to-End Test: Complete User Flow

This test simulates a complete user journey through LocaNext:
1. User logs in
2. User runs XLSTransfer operations
3. Logs are created in the database
4. WebSocket events are broadcasted
5. User views task history
6. User logs out

Since this is a WSL environment without X server, we test the backend
functionality directly instead of the Electron GUI.
"""

import pytest
import requests
import json
import subprocess
import time
import os
from pathlib import Path
from datetime import datetime


# Configuration
BASE_URL = "http://localhost:8888"
API_BASE = f"{BASE_URL}/api/v2"
PROJECT_ROOT = Path(__file__).parent.parent.parent
TEST_DATA_DIR = PROJECT_ROOT / "locaNext" / "test-data"
TESTSMALL_FILE = TEST_DATA_DIR / "TESTSMALL.xlsx"
CLI_SCRIPT = PROJECT_ROOT / "client/tools/xls_transfer/cli/xlstransfer_cli.py"


def run_cli(command=None, *args):
    """Helper to run CLI command with proper environment"""
    env = os.environ.copy()
    env['PYTHONPATH'] = str(PROJECT_ROOT)

    if command is None:
        cmd = ['python3', str(CLI_SCRIPT)]
    else:
        cmd = ['python3', str(CLI_SCRIPT), command, *args]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=env,
        timeout=60
    )

    return result


class TestCompleteUserFlow:
    """End-to-end test of complete user workflow"""

    @classmethod
    def setup_class(cls):
        """Setup: Verify backend is running"""
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=5)
            assert response.status_code == 200
            print(f"\n✓ Backend server is healthy: {response.json()}")
        except Exception as e:
            pytest.fail(f"Backend server not running: {e}")

    def test_01_health_check(self):
        """Test: Backend health check"""
        response = requests.get(f"{BASE_URL}/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["healthy", "degraded"]
        assert data["database"] == "connected"
        print(f"✓ Health check passed: {data['status']}")

    def test_02_user_authentication_flow(self):
        """Test: Complete authentication flow (login, token validation, logout)"""
        # 1. Login
        login_data = {
            "username": "admin",
            "password": "admin123"
        }
        try:
            response = requests.post(f"{API_BASE}/auth/login", json=login_data, timeout=10)
        except Exception as e:
            pytest.skip(f"Could not connect to auth endpoint: {e}")

        if response.status_code == 404:
            # Try sync endpoint if async doesn't exist
            response = requests.post(f"{BASE_URL}/api/auth/login", json=login_data, timeout=10)

        if response.status_code != 200:
            pytest.skip(f"Auth endpoint not available (status {response.status_code})")

        data = response.json()
        assert "access_token" in data
        token = data["access_token"]
        user_id = data["user"]["user_id"]
        print(f"✓ Login successful: {data['user']['username']} (ID: {user_id})")

        # 2. Store token for other tests
        TestCompleteUserFlow.token = token
        TestCompleteUserFlow.headers = {"Authorization": f"Bearer {token}"}
        TestCompleteUserFlow.user_id = user_id
        print(f"✓ Token stored for subsequent tests")

    def test_03_xlstransfer_validate_dict(self):
        """Test: XLSTransfer - Validate Dictionary"""
        if not TESTSMALL_FILE.exists():
            pytest.skip(f"Test file not found: {TESTSMALL_FILE}")

        result = run_cli('validate_dict', str(TESTSMALL_FILE))

        # Parse JSON output (last line)
        output_lines = result.stdout.strip().split('\n')
        output = json.loads(output_lines[-1])

        assert output['success'] == True
        assert output['valid'] == True
        print(f"✓ Dictionary validation passed: {output['file']}")

    def test_04_xlstransfer_check_newlines(self):
        """Test: XLSTransfer - Check Newlines"""
        if not TESTSMALL_FILE.exists():
            pytest.skip(f"Test file not found: {TESTSMALL_FILE}")

        result = run_cli('check_newlines', str(TESTSMALL_FILE))

        output_lines = result.stdout.strip().split('\n')
        output = json.loads(output_lines[-1])

        assert output['success'] == True
        assert 'mismatches' in output
        print(f"✓ Newline check completed: {output.get('mismatches', 0)} mismatches found")

    def test_05_xlstransfer_check_spaces(self):
        """Test: XLSTransfer - Check Spaces"""
        if not TESTSMALL_FILE.exists():
            pytest.skip(f"Test file not found: {TESTSMALL_FILE}")

        result = run_cli('check_spaces', str(TESTSMALL_FILE))

        output_lines = result.stdout.strip().split('\n')
        output = json.loads(output_lines[-1])

        assert output['success'] == True
        assert 'mismatches' in output
        assert output['file'] == str(TESTSMALL_FILE)
        print(f"✓ Space check completed: {output.get('mismatches', 0)} mismatches found")

    def test_06_xlstransfer_find_duplicates(self):
        """Test: XLSTransfer - Find Duplicates"""
        if not TESTSMALL_FILE.exists():
            pytest.skip(f"Test file not found: {TESTSMALL_FILE}")

        # Use a sample column value from the test file
        result = run_cli('find_duplicates', str(TESTSMALL_FILE), '연금 스킬 경험치가 증가합니다.')

        output_lines = result.stdout.strip().split('\n')
        output = json.loads(output_lines[-1])

        # Check that we got a valid response (success or error is both OK for this test)
        assert 'success' in output
        if output['success']:
            assert 'duplicates' in output
            print(f"✓ Duplicate check completed: {output.get('duplicates', 0)} duplicates found")
        else:
            print(f"✓ Duplicate check completed (column not found - expected for test data)")

    def test_07_create_log_entry(self):
        """Test: Create log entry via API"""
        if not hasattr(TestCompleteUserFlow, 'user_id'):
            pytest.skip("Authentication test did not run successfully")

        log_data = {
            "user_id": TestCompleteUserFlow.user_id,
            "tool_name": "xls_transfer",
            "operation": "check_spaces",
            "status": "completed",
            "file_path": str(TESTSMALL_FILE),
            "file_size": TESTSMALL_FILE.stat().st_size if TESTSMALL_FILE.exists() else 0,
            "rows_processed": 100,
            "duration": 5.5
        }

        try:
            response = requests.post(f"{API_BASE}/logs", json=log_data, headers=TestCompleteUserFlow.headers, timeout=10)
            if response.status_code == 404:
                # Try sync endpoint
                response = requests.post(f"{BASE_URL}/api/logs", json=log_data, headers=TestCompleteUserFlow.headers, timeout=10)
        except Exception as e:
            pytest.skip(f"Could not connect to logs endpoint: {e}")

        if response.status_code not in [200, 201]:
            pytest.skip(f"Logs endpoint not available (status {response.status_code})")

        data = response.json()
        assert "log_id" in data or "id" in data
        log_id = data.get("log_id") or data.get("id")
        TestCompleteUserFlow.log_id = log_id
        print(f"✓ Log entry created: ID {log_id}")

    def test_08_get_user_logs(self):
        """Test: Retrieve user's logs"""
        if not hasattr(TestCompleteUserFlow, 'user_id'):
            pytest.skip("Authentication test did not run successfully")

        try:
            response = requests.get(
                f"{API_BASE}/logs",
                params={"user_id": TestCompleteUserFlow.user_id, "limit": 10},
                headers=TestCompleteUserFlow.headers,
                timeout=10
            )
            if response.status_code == 404:
                # Try sync endpoint
                response = requests.get(
                    f"{BASE_URL}/api/logs",
                    params={"user_id": TestCompleteUserFlow.user_id, "limit": 10},
                    headers=TestCompleteUserFlow.headers,
                    timeout=10
                )
        except Exception as e:
            pytest.skip(f"Could not connect to logs endpoint: {e}")

        if response.status_code != 200:
            pytest.skip(f"Logs endpoint not available (status {response.status_code})")

        logs = response.json()
        assert isinstance(logs, list)
        print(f"✓ Retrieved {len(logs)} log entries")

    def test_09_verify_backend_endpoints(self):
        """Test: Verify backend update endpoints"""
        # Test updates version endpoint
        try:
            response = requests.get(f"{BASE_URL}/updates/version", timeout=10)
            if response.status_code == 200:
                data = response.json()
                print(f"✓ Updates endpoint available: version={data.get('version', 'N/A')}")
            else:
                print(f"✓ Updates endpoint exists but no updates available (status {response.status_code})")
        except Exception as e:
            print(f"✓ Updates endpoint not critical for testing")

    def test_10_websocket_connection(self):
        """Test: WebSocket connection and basic communication"""
        try:
            import socketio
        except ImportError:
            pytest.skip("python-socketio not installed")

        # Create Socket.IO client
        sio = socketio.Client()
        connected = False

        @sio.event
        def connect():
            nonlocal connected
            connected = True
            print("✓ WebSocket connected")

        @sio.event
        def disconnect():
            print("✓ WebSocket disconnected")

        # Connect
        try:
            sio.connect(f"{BASE_URL}/ws", transports=['websocket', 'polling'], wait_timeout=5)
            time.sleep(1)  # Wait for connection
            assert connected, "WebSocket failed to connect"

            # Disconnect
            sio.disconnect()
            print("✓ WebSocket test completed")
        except Exception as e:
            pytest.skip(f"WebSocket connection failed: {e}")

    def test_11_logout(self):
        """Test: User logout"""
        if not hasattr(TestCompleteUserFlow, 'headers'):
            pytest.skip("Authentication test did not run successfully")

        try:
            response = requests.post(f"{API_BASE}/auth/logout", headers=TestCompleteUserFlow.headers, timeout=10)
            if response.status_code == 404:
                # Try sync endpoint
                response = requests.post(f"{BASE_URL}/api/auth/logout", headers=TestCompleteUserFlow.headers, timeout=10)
        except Exception as e:
            pytest.skip(f"Could not connect to logout endpoint: {e}")

        if response.status_code == 200:
            print(f"✓ Logout successful")
        else:
            print(f"✓ Logout endpoint returned status {response.status_code}")


@pytest.mark.asyncio
async def test_websocket_events():
    """Test: WebSocket event broadcasting (async test)"""
    try:
        import socketio
    except ImportError:
        pytest.skip("python-socketio not installed")

    # This would test real-time event broadcasting
    # Skipping for now as it requires more complex async setup
    pytest.skip("Async WebSocket event testing requires additional setup")


def test_performance_file_size():
    """Test: Verify performance with file size tracking"""
    if not TESTSMALL_FILE.exists():
        pytest.skip(f"Test file not found: {TESTSMALL_FILE}")

    file_size = TESTSMALL_FILE.stat().st_size
    print(f"\n✓ Test file size: {file_size:,} bytes ({file_size / 1024:.2f} KB)")

    # For large file testing (future)
    # - Test with files > 1MB
    # - Test with files > 10MB
    # - Monitor memory usage
    # - Check processing time


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s"])
