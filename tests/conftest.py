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
from typing import Generator
import pandas as pd
import openpyxl

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


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
    monkeypatch.setattr("client.config.OFFLINE_MODE", True)
    monkeypatch.setattr("client.config.ENABLE_SERVER_LOGGING", False)
    monkeypatch.setattr("client.config.MOCK_SERVER", True)


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
    """Configure custom markers."""
    config.addinivalue_line(
        "markers", "requires_model: mark test as requiring ML model"
    )
    config.addinivalue_line(
        "markers", "requires_server: mark test as requiring running server"
    )


# ============================================
# Test Collection
# ============================================

def pytest_collection_modifyitems(config, items):
    """
    Modify test collection.
    Add markers automatically based on test location.
    """
    for item in items:
        # Auto-add markers based on path
        if "unit/client" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
            item.add_marker(pytest.mark.client)
        elif "unit/server" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
            item.add_marker(pytest.mark.server)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)


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
