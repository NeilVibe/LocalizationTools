"""
Windows Tests Conftest

Minimal conftest for Windows tests - no dependencies required.
This file prevents pytest from loading the main tests/conftest.py
which requires SQLAlchemy and other backend dependencies.
"""

import pytest
import sys

# Ensure we don't inherit from parent conftest
# by defining our own minimal fixtures

@pytest.fixture(scope="session")
def windows_test_session():
    """Marker for Windows test session."""
    return True


def pytest_configure(config):
    """Configure pytest for Windows tests."""
    # Register custom markers
    config.addinivalue_line(
        "markers", "windows: mark test as Windows-only"
    )


def pytest_collection_modifyitems(config, items):
    """Skip tests not on Windows."""
    import platform
    if platform.system() != "Windows":
        skip_windows = pytest.mark.skip(reason="Windows-only tests")
        for item in items:
            item.add_marker(skip_windows)
