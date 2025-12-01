"""
Mock Data for Tests

Sample data used across different test modules.
"""

from datetime import datetime, timedelta
import uuid


# Sample user data
SAMPLE_USER_DATA = {
    "basic": {
        "username": "test_user_basic",
        "email": "basic@test.com",
        "full_name": "Test User Basic",
        "department": "QA",
        "role": "user",
        "is_active": True,
    },
    "admin": {
        "username": "test_admin",
        "email": "admin@test.com",
        "full_name": "Test Admin",
        "department": "IT",
        "role": "admin",
        "is_active": True,
    },
    "inactive": {
        "username": "test_inactive",
        "email": "inactive@test.com",
        "full_name": "Test Inactive",
        "department": "QA",
        "role": "user",
        "is_active": False,
    },
}


# Sample session data
SAMPLE_SESSION_DATA = {
    "basic": {
        "machine_id": "test_machine_001",
        "ip_address": "192.168.1.100",
        "app_version": "2512010029",
        "is_active": True,
    },
    "expired": {
        "machine_id": "test_machine_002",
        "ip_address": "192.168.1.101",
        "app_version": "2511221939",
        "is_active": False,
    },
}


# Sample log entry data
SAMPLE_LOG_ENTRY_DATA = {
    "xlstransfer_success": {
        "tool_name": "XLSTransfer",
        "function_name": "transfer_data",
        "duration_seconds": 5.5,
        "status": "success",
        "file_info": {
            "input_file": "test.xlsx",
            "size_mb": 1.5,
            "rows": 1000,
        },
        "parameters": {
            "source_col": "A",
            "target_col": "B",
        },
    },
    "quicksearch_success": {
        "tool_name": "QuickSearch",
        "function_name": "search_dictionary",
        "duration_seconds": 0.5,
        "status": "success",
        "parameters": {
            "query": "hello",
            "language": "en",
        },
    },
    "kr_similar_success": {
        "tool_name": "KRSimilar",
        "function_name": "find_similar",
        "duration_seconds": 2.0,
        "status": "success",
        "parameters": {
            "query": "안녕하세요",
            "top_k": 5,
        },
    },
    "error_example": {
        "tool_name": "XLSTransfer",
        "function_name": "transfer_data",
        "duration_seconds": 0.1,
        "status": "error",
        "error_message": "File not found: test.xlsx",
    },
}


# Sample tool usage stats
SAMPLE_TOOL_STATS = {
    "xlstransfer": {
        "tool_name": "XLSTransfer",
        "total_uses": 150,
        "unique_users": 25,
        "total_duration_seconds": 750.0,
        "avg_duration_seconds": 5.0,
        "success_count": 145,
        "error_count": 5,
    },
    "quicksearch": {
        "tool_name": "QuickSearch",
        "total_uses": 500,
        "unique_users": 40,
        "total_duration_seconds": 250.0,
        "avg_duration_seconds": 0.5,
        "success_count": 498,
        "error_count": 2,
    },
}


# Sample API request payloads
SAMPLE_API_REQUESTS = {
    "login": {
        "username": "test_user",
        "password": "test_password",
    },
    "create_user": {
        "username": "new_user",
        "password": "secure_password_123",
        "email": "new@test.com",
        "full_name": "New User",
        "department": "Engineering",
    },
    "log_operation": {
        "tool_name": "XLSTransfer",
        "function_name": "transfer_data",
        "duration_seconds": 3.5,
        "status": "success",
        "file_info": {"size_mb": 2.0},
    },
}


# Sample file paths for testing
SAMPLE_FILE_PATHS = {
    "valid_xlsx": "tests/fixtures/sample_dictionary.xlsx",
    "valid_txt": "tests/fixtures/sample_language_data.txt",
    "quicksearch_data": "tests/fixtures/sample_quicksearch_data.txt",
    "translation_data": "tests/fixtures/sample_to_translate.txt",
}


def generate_unique_username(prefix: str = "test") -> str:
    """Generate a unique username for testing."""
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def generate_unique_email(prefix: str = "test") -> str:
    """Generate a unique email for testing."""
    return f"{prefix}_{uuid.uuid4().hex[:8]}@test.com"


def generate_session_id() -> str:
    """Generate a unique session ID."""
    return str(uuid.uuid4())


def generate_machine_id(prefix: str = "machine") -> str:
    """Generate a unique machine ID."""
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


def get_past_datetime(days: int = 1) -> datetime:
    """Get a datetime in the past."""
    return datetime.utcnow() - timedelta(days=days)


def get_future_datetime(days: int = 1) -> datetime:
    """Get a datetime in the future."""
    return datetime.utcnow() + timedelta(days=days)
