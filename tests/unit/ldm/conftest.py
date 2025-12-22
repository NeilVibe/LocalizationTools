"""
LDM Unit Test Fixtures

Provides TestClient and mock database for LDM route tests.
These tests run WITHOUT a server - fast unit tests.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from server.main import app


@pytest.fixture
def client():
    """FastAPI TestClient - no server needed."""
    return TestClient(app)


@pytest.fixture
def mock_db():
    """Mock database session."""
    db = MagicMock(spec=Session)
    return db


@pytest.fixture
def auth_headers():
    """Mock auth headers for protected endpoints."""
    return {"Authorization": "Bearer test-token"}


@pytest.fixture
def mock_user():
    """Mock authenticated user."""
    return {
        "id": 1,
        "username": "testuser",
        "email": "test@example.com",
        "is_admin": False
    }


@pytest.fixture
def mock_admin():
    """Mock admin user."""
    return {
        "id": 1,
        "username": "admin",
        "email": "admin@example.com",
        "is_admin": True
    }


@pytest.fixture
def sample_project():
    """Sample project data."""
    return {
        "id": 1,
        "name": "Test Project",
        "description": "A test project",
        "source_lang": "ko",
        "target_lang": "en",
        "owner_id": 1,
        "created_at": "2025-01-01T00:00:00"
    }


@pytest.fixture
def sample_folder():
    """Sample folder data."""
    return {
        "id": 1,
        "name": "Test Folder",
        "project_id": 1,
        "parent_id": None
    }


@pytest.fixture
def sample_tm():
    """Sample TM data."""
    return {
        "id": 1,
        "name": "Test TM",
        "description": "A test TM",
        "source_lang": "ko",
        "target_lang": "en",
        "entry_count": 100,
        "status": "ready",
        "owner_id": 1
    }


@pytest.fixture
def sample_tm_entry():
    """Sample TM entry data."""
    return {
        "id": 1,
        "tm_id": 1,
        "source_text": "안녕하세요",
        "target_text": "Hello",
        "string_id": "STR_001",
        "is_confirmed": False
    }
