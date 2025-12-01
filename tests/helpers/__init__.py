"""
Test Helpers Module

Common utilities, fixtures, and test data generators for the test suite.
"""

from .db_helpers import (
    create_test_user,
    create_test_session,
    create_test_log_entry,
    cleanup_test_data,
)
from .api_helpers import (
    get_auth_headers,
    make_authenticated_request,
)
from .mock_data import (
    SAMPLE_USER_DATA,
    SAMPLE_SESSION_DATA,
    SAMPLE_LOG_ENTRY_DATA,
)

__all__ = [
    # DB helpers
    "create_test_user",
    "create_test_session",
    "create_test_log_entry",
    "cleanup_test_data",
    # API helpers
    "get_auth_headers",
    "make_authenticated_request",
    # Mock data
    "SAMPLE_USER_DATA",
    "SAMPLE_SESSION_DATA",
    "SAMPLE_LOG_ENTRY_DATA",
]
