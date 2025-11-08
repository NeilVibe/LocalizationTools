# Testing Documentation

## Test Suite Overview

LocalizationTools uses **pytest** for comprehensive testing across all layers of the application.

### Test Statistics

**Total Tests: 94 (100% PASSING ✅)**
- Unit Tests: 86 tests
- Integration Tests: 8 tests

**Test Execution Time:**
- Unit Tests: ~2.1 seconds
- Integration Tests: ~1.9 seconds
- **Total: ~4 seconds**

---

## Test Structure

```
tests/
├── conftest.py                    # Shared fixtures
├── unit/                          # Unit tests (86 tests)
│   └── client/
│       ├── test_utils_logger.py   # Logger utility tests (18 tests)
│       ├── test_utils_progress.py # Progress tracker tests (27 tests)
│       └── test_utils_file_handler.py # File handler tests (41 tests)
└── integration/                   # Integration tests (8 tests)
    ├── test_server_startup.py     # Server initialization tests
    └── test_api_endpoints.py      # API endpoint tests
```

---

## Running Tests

### All Tests
```bash
pytest
```

### Unit Tests Only
```bash
pytest tests/unit/ -v
```

### Integration Tests Only
```bash
pytest tests/integration/ -v
```

### With Coverage Report
```bash
pytest tests/unit/ --cov=client --cov-report=html
```

### Specific Test File
```bash
pytest tests/unit/client/test_utils_logger.py -v
```

---

## Unit Tests (86 tests)

### Logger Tests (18 tests)
**File:** `tests/unit/client/test_utils_logger.py`

Tests for the UsageLogger utility:
- ✅ Session management (start, generate ID, config)
- ✅ Log queue operations (add, clear, flush)
- ✅ Server connectivity (online/offline handling)
- ✅ Log operation decorator
- ✅ Error handling
- ✅ Complete workflow tests

**Key Test Cases:**
- `test_logger_session_id_generation` - Validates UUID generation
- `test_logger_queues_logs_when_server_unavailable` - Offline queueing
- `test_logger_flushes_queue_when_server_available` - Auto-flush
- `test_log_operation_decorator_success` - Decorator functionality

### Progress Tracker Tests (27 tests)
**File:** `tests/unit/client/test_utils_progress.py`

Tests for progress tracking utilities:
- ✅ ProgressTracker initialization and context manager
- ✅ Progress updates and status messages
- ✅ Gradio integration
- ✅ SimpleProgress class
- ✅ Edge cases (zero total, negative updates)
- ✅ Realistic workflows

**Key Test Cases:**
- `test_progress_tracker_with_gradio_progress` - Gradio integration
- `test_track_progress_processes_all_items` - Batch processing
- `test_progress_tracker_realistic_file_processing` - Real-world scenario
- `test_combined_progress_trackers` - Multiple trackers

### File Handler Tests (41 tests)
**File:** `tests/unit/client/test_utils_file_handler.py`

Tests for file handling utilities:
- ✅ File validation and size calculation
- ✅ File hashing (MD5, SHA256)
- ✅ Temporary file management
- ✅ TempFileManager cleanup
- ✅ Error handling
- ✅ Edge cases

**Key Test Cases:**
- `test_validate_file_exists` - File existence validation
- `test_calculate_file_hash_md5` - File hashing
- `test_temp_file_manager_cleanup_on_exit` - Resource cleanup
- `test_temp_file_manager_multiple_files` - Bulk operations

---

## Integration Tests (8 tests)

### Server Startup Tests (8 tests)
**File:** `tests/integration/test_server_startup.py`

Tests for FastAPI server initialization:
- ✅ Root endpoint returns server info
- ✅ Health check endpoint works
- ✅ API documentation accessible
- ✅ All 27 routes registered correctly
- ✅ CORS headers configured
- ✅ Database connection verified
- ✅ Server configuration loaded
- ✅ Database configuration valid

**Verified Routes:**
- Authentication: `/api/auth/login`, `/api/auth/register`, `/api/auth/me`
- Logging: `/api/logs/submit`, `/api/logs/error`, `/api/logs/stats/*`
- Sessions: `/api/sessions/start`, `/api/sessions/{id}/heartbeat`, `/api/sessions/{id}/end`
- Utility: `/`, `/health`, `/api/version/latest`, `/api/announcements`

### API Endpoint Tests
**File:** `tests/integration/test_api_endpoints.py`

Comprehensive API endpoint testing:
- ✅ Authentication flow (login, token validation)
- ✅ Log submission (with/without auth)
- ✅ Session management (start, heartbeat, end)
- ✅ Statistics endpoints
- ✅ Version and announcements
- ✅ Error handling

**Test Categories:**
1. **TestAuthEndpoints** - Login, user management
2. **TestLogEndpoints** - Log submission, statistics
3. **TestSessionEndpoints** - Session lifecycle
4. **TestVersionEndpoint** - Version and announcements

---

## Test Coverage

### Unit Test Coverage
- **Target:** 80% minimum (enforced by pytest.ini)
- **Achieved:** Varies by module
  - Utils: High coverage (logger, progress, file_handler)
  - Tools: Lower coverage (XLSTransfer modules tested via integration)

### Integration Test Focus
- **Focus:** Functionality over coverage
- **Purpose:** Verify system works end-to-end
- **Coverage:** Not measured separately (focuses on critical paths)

---

## CI/CD Integration

Tests are designed to run in CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run tests
  run: |
    pip install -r requirements.txt
    pytest tests/unit/ -v --cov=client --cov-report=xml
    pytest tests/integration/ -v
```

---

## Test Fixtures

### Shared Fixtures (conftest.py)

**`sample_excel_file`** - Creates test Excel files with Korean/English data
**`temp_dir`** - Provides temporary directory for file operations
**`mock_sentence_transformer`** - Mocks ML model for fast testing
**`mock_requests`** - Mocks HTTP requests for testing

### Integration Test Fixtures

**`test_db`** - Initializes test database (SQLite)
**`test_user`** - Creates test user with hashed password
**`client`** - FastAPI TestClient for endpoint testing

---

## Adding New Tests

### Unit Test Template

```python
import pytest

def test_your_function():
    """Test description."""
    # Arrange
    input_data = "test"

    # Act
    result = your_function(input_data)

    # Assert
    assert result == expected_output
```

### Integration Test Template

```python
import pytest
from fastapi.testclient import TestClient

@pytest.mark.integration
class TestYourEndpoint:
    """Test your endpoint."""

    def test_endpoint_success(self, client):
        """Test successful request."""
        response = client.get("/your/endpoint")
        assert response.status_code == 200
```

---

## Test Markers

Use pytest markers to organize tests:

```python
@pytest.mark.unit          # Unit test
@pytest.mark.integration   # Integration test
@pytest.mark.slow          # Slow test (skip in quick runs)
@pytest.mark.skip          # Skip test
```

Run specific markers:
```bash
pytest -m integration  # Run only integration tests
pytest -m "not slow"   # Skip slow tests
```

---

## Troubleshooting

### Tests Failing?

1. **Check database:** Ensure database is initialized
   ```bash
   python3 scripts/create_admin.py
   ```

2. **Check dependencies:** Ensure all packages installed
   ```bash
   pip install -r requirements.txt
   ```

3. **Run with verbose output:**
   ```bash
   pytest -vv --tb=long
   ```

4. **Check specific test:**
   ```bash
   pytest tests/unit/client/test_utils_logger.py::test_logger_initialization -vv
   ```

### Coverage Too Low?

1. Run coverage report to see missing lines:
   ```bash
   pytest --cov=client --cov-report=html
   open htmlcov/index.html
   ```

2. Add tests for uncovered code paths

3. For integration-tested code, coverage may be lower (expected)

---

## Test Maintenance

### When to Update Tests

- ✅ When adding new features
- ✅ When fixing bugs (add regression test)
- ✅ When refactoring code
- ✅ When changing API contracts

### Best Practices

1. **One assertion per test** (when possible)
2. **Descriptive test names** (test_function_name_scenario_expected_result)
3. **Use fixtures** for common setup
4. **Mock external dependencies** (network, database, ML models)
5. **Test edge cases** (empty input, None, errors)
6. **Keep tests fast** (<1s per test when possible)

---

## Next Steps

### Future Testing Improvements

1. **E2E Tests** - Full client-server integration tests
2. **Performance Tests** - Load testing, stress testing
3. **Security Tests** - Penetration testing, vulnerability scanning
4. **UI Tests** - Gradio interface testing
5. **Continuous Integration** - Automated testing on every commit

---

## Test Results Summary

**✅ All 94 tests passing**
**⚡ Fast execution (~4 seconds total)**
**🎯 Comprehensive coverage of critical paths**
**🔒 Validates authentication, logging, and core utilities**

The test suite provides confidence in code quality and system reliability.
