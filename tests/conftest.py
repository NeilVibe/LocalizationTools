"""
Test Configuration and Shared Fixtures

Provides reusable fixtures for all tests.
Keeps tests CLEAN and DRY (Don't Repeat Yourself).
"""

import pytest
import sys
from pathlib import Path
import tempfile
import shutil
from typing import Generator, Optional
import pandas as pd
import openpyxl
import requests
import time
import os

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Pre-import client_config module to ensure it's available for monkeypatch
# This fixes test isolation issues where module import order affects attribute access
import server.client_config.client_config  # noqa: E402, F401


# ============================================
# Admin User Management (Self-Healing)
# ============================================

# Constants for admin credentials
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"
BASE_URL = "http://localhost:8888"


def _server_is_running() -> bool:
    """Check if the server is running."""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=2)
        return response.ok
    except Exception:
        return False


def _try_admin_login() -> Optional[str]:
    """
    Try to login as admin.

    Returns:
        Access token if successful, None otherwise.
    """
    try:
        response = requests.post(
            f"{BASE_URL}/api/v2/auth/login",
            json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
            timeout=10
        )
        if response.status_code == 200:
            return response.json().get("access_token")
        return None
    except Exception:
        return None


def _ensure_admin_exists() -> bool:
    """
    Ensure admin user exists with correct password.

    This is the SELF-HEALING mechanism:
    - Directly accesses the database to fix admin user
    - Resets password if admin exists but password is wrong
    - Creates admin if it doesn't exist

    Returns:
        True if admin is now ready, False if failed.
    """
    try:
        from server.database.db_setup import setup_database
        from server.database.models import User
        from server.utils.auth import hash_password
        from server import config
        from datetime import datetime

        # Get database session
        engine, session_maker = setup_database(drop_existing=False)
        db = session_maker()

        try:
            # Check if admin exists
            admin = db.query(User).filter(User.username == ADMIN_USERNAME).first()

            if admin:
                # Admin exists - reset password to known value
                admin.password_hash = hash_password(ADMIN_PASSWORD)
                admin.is_active = True  # Ensure active
                db.commit()
                print(f"[conftest] Admin user password reset to {ADMIN_PASSWORD}")
                return True
            else:
                # Create admin user
                admin = User(
                    username=ADMIN_USERNAME,
                    password_hash=hash_password(ADMIN_PASSWORD),
                    email=config.DEFAULT_ADMIN_EMAIL,
                    full_name="System Administrator",
                    department="IT",
                    role="superadmin",
                    is_active=True,
                    created_at=datetime.utcnow()
                )
                db.add(admin)
                db.commit()
                print(f"[conftest] Admin user created: {ADMIN_USERNAME}")
                return True

        finally:
            db.close()

    except Exception as e:
        print(f"[conftest] Failed to ensure admin exists: {e}")
        return False


def get_admin_token_with_retry(max_retries: int = 3) -> str:
    """
    Get admin token with self-healing retry logic.

    This is the ROBUST fix for admin login failures:
    1. Try to login
    2. If login fails, ensure admin exists (fix credentials)
    3. Retry login

    Args:
        max_retries: Maximum number of retry attempts.

    Returns:
        Valid admin access token.

    Raises:
        RuntimeError: If unable to get admin token after all retries.
    """
    if not _server_is_running():
        raise RuntimeError("Server is not running at http://localhost:8888")

    for attempt in range(max_retries):
        # Try to login
        token = _try_admin_login()
        if token:
            return token

        # Login failed - try to fix admin user
        print(f"[conftest] Admin login failed (attempt {attempt + 1}/{max_retries}), ensuring admin exists...")

        if _ensure_admin_exists():
            # Wait a moment for database changes to propagate
            time.sleep(0.5)

            # Try login again
            token = _try_admin_login()
            if token:
                print(f"[conftest] Admin login succeeded after self-healing")
                return token

        # Wait before next retry
        time.sleep(1)

    raise RuntimeError(
        f"Failed to get admin token after {max_retries} attempts. "
        f"Check if server is running and database is accessible. "
        f"URL: {BASE_URL}, Username: {ADMIN_USERNAME}"
    )


@pytest.fixture(scope="session")
def admin_token_session() -> str:
    """
    Session-scoped admin token fixture.

    This token is obtained ONCE at the start of the test session
    using the self-healing mechanism. All tests in the session
    can share this token.

    Note: Use this for tests that don't modify admin credentials.
    """
    return get_admin_token_with_retry()


@pytest.fixture
def admin_token_fresh() -> str:
    """
    Fresh admin token fixture (function-scoped).

    Gets a NEW token for each test. Use this if:
    - Previous tests might have invalidated the token
    - You need to ensure a fresh authentication state
    """
    return get_admin_token_with_retry()


@pytest.fixture(scope="session")
def admin_headers_session(admin_token_session: str) -> dict:
    """Session-scoped authorization headers."""
    return {"Authorization": f"Bearer {admin_token_session}"}


@pytest.fixture
def admin_headers_fresh(admin_token_fresh: str) -> dict:
    """Fresh authorization headers (function-scoped)."""
    return {"Authorization": f"Bearer {admin_token_fresh}"}


@pytest.fixture(scope="session", autouse=True)
def ensure_admin_at_session_start():
    """
    Session-scoped autouse fixture that ensures admin user exists.

    This runs ONCE at the very start of the test session, BEFORE any tests.
    It ensures:
    1. Admin user exists in the database
    2. Admin password is set to 'admin123'
    3. Admin is active

    This protects ALL tests, even those that don't use the self-healing
    admin_token fixtures explicitly.
    """
    # Only run if server is up (don't fail if server isn't running for unit tests)
    if _server_is_running():
        # Try login first - if it works, admin is fine
        if not _try_admin_login():
            # Login failed, ensure admin exists
            print("[conftest] Session start: Admin login failed, ensuring admin exists...")
            _ensure_admin_exists()
            # Verify it works now
            if _try_admin_login():
                print("[conftest] Session start: Admin user is now ready")
            else:
                print("[conftest] Session start: WARNING - Admin still not working after fix attempt")
        else:
            print("[conftest] Session start: Admin user verified OK")

    yield

    # Session cleanup (optional)
    pass


# ============================================
# Temporary Directory Fixtures
# ============================================

@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """
    Create a temporary directory for tests.
    Automatically cleaned up after test.
    """
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    # Cleanup
    if temp_path.exists():
        shutil.rmtree(temp_path)


@pytest.fixture
def temp_file(temp_dir) -> Path:
    """Create a temporary file path."""
    return temp_dir / "test_file.txt"


# ============================================
# Excel File Fixtures
# ============================================

@pytest.fixture
def sample_excel_file(temp_dir) -> Path:
    """
    Create a sample Excel file with Korean and translation columns.

    Format:
    Column A: Korean text
    Column B: English translation
    10 rows of sample data
    """
    file_path = temp_dir / "sample.xlsx"

    # Sample data
    data = {
        "Korean": [
            "안녕하세요",
            "감사합니다",
            "미안합니다",
            "어디에 있습니까?",
            "도와주세요",
            "얼마예요?",
            "좋은 아침입니다",
            "안녕히 가세요",
            "네",
            "아니요"
        ],
        "English": [
            "Hello",
            "Thank you",
            "Sorry",
            "Where is it?",
            "Please help",
            "How much is it?",
            "Good morning",
            "Goodbye",
            "Yes",
            "No"
        ]
    }

    df = pd.DataFrame(data)
    df.to_excel(file_path, index=False)

    return file_path


@pytest.fixture
def large_excel_file(temp_dir) -> Path:
    """Create a larger Excel file for performance testing."""
    file_path = temp_dir / "large_sample.xlsx"

    # Generate 1000 rows
    data = {
        "Korean": [f"한국어 텍스트 {i}" for i in range(1000)],
        "English": [f"English text {i}" for i in range(1000)]
    }

    df = pd.DataFrame(data)
    df.to_excel(file_path, index=False)

    return file_path


@pytest.fixture
def multi_sheet_excel(temp_dir) -> Path:
    """Create an Excel file with multiple sheets."""
    file_path = temp_dir / "multi_sheet.xlsx"

    with pd.ExcelWriter(file_path) as writer:
        for i in range(3):
            data = {
                "Korean": [f"Sheet {i} - 한국어 {j}" for j in range(10)],
                "English": [f"Sheet {i} - English {j}" for j in range(10)]
            }
            df = pd.DataFrame(data)
            df.to_excel(writer, sheet_name=f"Sheet{i}", index=False)

    return file_path


# ============================================
# Mock Model Fixtures
# ============================================

@pytest.fixture
def mock_sentence_transformer():
    """
    Mock SentenceTransformer model for fast testing.
    Returns fixed-size embeddings without loading actual model.
    """
    class MockModel:
        """Mock model that generates fake embeddings."""

        def __init__(self):
            self.max_seq_length = 128
            self.embedding_dim = 384  # Same as real model

        def encode(self, texts, convert_to_tensor=False):
            """Generate fake embeddings."""
            import numpy as np

            if isinstance(texts, str):
                texts = [texts]

            # Return fixed random embeddings
            embeddings = np.random.rand(len(texts), self.embedding_dim).astype(np.float32)

            return embeddings

        def save(self, path):
            """Mock save (does nothing)."""
            pass

    return MockModel()


# ============================================
# Mock Server Fixtures
# ============================================

@pytest.fixture
def mock_server_url():
    """Return mock server URL for testing."""
    return "http://localhost:9999"


@pytest.fixture
def mock_api_response():
    """Return a mock successful API response."""
    return {
        "status": "success",
        "message": "Log received",
        "session_id": "test-session-123"
    }


# ============================================
# Database Fixtures
# ============================================

@pytest.fixture
def test_database_url(temp_dir):
    """Create a temporary SQLite database for testing."""
    db_path = temp_dir / "test.db"
    return f"sqlite:///{db_path}"


# ============================================
# Configuration Fixtures
# ============================================

@pytest.fixture
def mock_config(monkeypatch):
    """
    Mock client configuration for testing.
    Disables server logging to avoid network calls.
    """
    # Mock config values
    monkeypatch.setattr("server.client_config.client_config.OFFLINE_MODE", True)
    monkeypatch.setattr("server.client_config.client_config.ENABLE_SERVER_LOGGING", False)
    monkeypatch.setattr("server.client_config.client_config.MOCK_SERVER", True)


# ============================================
# Sample Data Fixtures
# ============================================

@pytest.fixture
def sample_korean_texts():
    """Return a list of sample Korean texts."""
    return [
        "안녕하세요",
        "감사합니다",
        "미안합니다",
        "어디에 있습니까?",
        "도와주세요"
    ]


@pytest.fixture
def sample_translation_dict():
    """Return a sample translation dictionary."""
    return {
        "안녕하세요": "Hello",
        "감사합니다": "Thank you",
        "미안합니다": "Sorry",
        "어디에 있습니까?": "Where is it?",
        "도와주세요": "Please help"
    }


# ============================================
# Logging Fixtures
# ============================================

@pytest.fixture
def capture_logs(caplog):
    """
    Capture log messages during tests.

    Usage:
        def test_something(capture_logs):
            logger.info("Test message")
            assert "Test message" in capture_logs.text
    """
    return caplog


# ============================================
# Cleanup Fixtures
# ============================================

@pytest.fixture(autouse=True)
def cleanup_temp_files():
    """
    Automatically clean up any temp files created during tests.
    Runs after every test.
    """
    yield
    # Cleanup logic here if needed


# ============================================
# Performance Fixtures
# ============================================

@pytest.fixture
def timer():
    """
    Simple timer fixture for performance tests.

    Usage:
        def test_performance(timer):
            with timer:
                # Code to measure
                pass
            assert timer.elapsed < 1.0  # Must complete in <1 second
    """
    import time

    class Timer:
        def __init__(self):
            self.start_time = None
            self.elapsed = None

        def __enter__(self):
            self.start_time = time.time()
            return self

        def __exit__(self, *args):
            self.elapsed = time.time() - self.start_time

    return Timer()


# ============================================
# Skip Markers
# ============================================

def pytest_configure(config):
    """Configure custom markers for optimal test organization."""
    # Test type markers
    config.addinivalue_line("markers", "unit: fast isolated unit tests")
    config.addinivalue_line("markers", "integration: component integration tests")
    config.addinivalue_line("markers", "e2e: end-to-end workflow tests")
    config.addinivalue_line("markers", "api: API endpoint tests")
    config.addinivalue_line("markers", "security: security validation tests")
    config.addinivalue_line("markers", "slow: long-running tests")
    config.addinivalue_line("markers", "performance: performance benchmark tests")

    # Component markers
    config.addinivalue_line("markers", "client: client-side tests")
    config.addinivalue_line("markers", "server: server-side tests")
    config.addinivalue_line("markers", "db: database tests")
    config.addinivalue_line("markers", "auth: authentication tests")
    config.addinivalue_line("markers", "tm: translation memory tests")

    # Feature markers
    config.addinivalue_line("markers", "feat001: FEAT-001 auto-add to TM tests")
    config.addinivalue_line("markers", "task002: TASK-002 silent tracking tests")

    # Requirement markers
    config.addinivalue_line("markers", "requires_model: requires ML model loaded")
    config.addinivalue_line("markers", "requires_server: requires running server")


# ============================================
# Test Collection
# ============================================

def pytest_collection_modifyitems(config, items):
    """
    Modify test collection.
    Add markers automatically based on test location.
    """
    for item in items:
        path_str = str(item.fspath)

        # ═══════════════════════════════════════════════════════════
        # AUTO-MARKERS BY DIRECTORY
        # ═══════════════════════════════════════════════════════════

        # Unit tests
        if "/unit/" in path_str:
            item.add_marker(pytest.mark.unit)
            if "unit/client" in path_str:
                item.add_marker(pytest.mark.client)
            elif "unit/server" in path_str:
                item.add_marker(pytest.mark.server)

        # Integration tests
        elif "/integration/" in path_str:
            item.add_marker(pytest.mark.integration)

        # E2E tests
        elif "/e2e/" in path_str:
            item.add_marker(pytest.mark.e2e)

        # API tests
        elif "/api/" in path_str:
            item.add_marker(pytest.mark.api)

        # Security tests
        elif "/security/" in path_str:
            item.add_marker(pytest.mark.security)

        # ═══════════════════════════════════════════════════════════
        # AUTO-MARKERS BY FILENAME
        # ═══════════════════════════════════════════════════════════

        # TM-related tests
        if "_tm_" in path_str or "test_tm" in path_str:
            item.add_marker(pytest.mark.tm)

        # Auth-related tests
        if "_auth" in path_str or "test_auth" in path_str:
            item.add_marker(pytest.mark.auth)

        # DB-related tests
        if "_db_" in path_str or "test_db" in path_str or "database" in path_str:
            item.add_marker(pytest.mark.db)

        # FEAT-001 tests
        if "feat001" in path_str.lower():
            item.add_marker(pytest.mark.feat001)


# ============================================
# Example Usage
# ============================================

# Tests can use these fixtures like this:
#
# def test_excel_processing(sample_excel_file):
#     df = pd.read_excel(sample_excel_file)
#     assert len(df) == 10
#
# def test_with_mock_model(mock_sentence_transformer):
#     embeddings = mock_sentence_transformer.encode(["test"])
#     assert embeddings.shape == (1, 384)
