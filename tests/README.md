# Testing Framework - LocalizationTools

**Comprehensive, organized testing for ALL components**

---

## 🎯 Testing Philosophy

**We test EVERYTHING:**
- ✅ Every function, every feature
- ✅ Backend code (server, API, database)
- ✅ Frontend code (client, UI, tools)
- ✅ Network communication (client-server)
- ✅ File operations (upload, download, processing)
- ✅ Logging and statistics
- ✅ Error handling and edge cases
- ✅ Performance and robustness

**No bloat allowed. CLEAN, organized tests.**

---

## 📁 Test Structure (CLEAN Organization)

```
tests/
├── README.md                    # This file
├── conftest.py                  # Shared fixtures and config
│
├── unit/                        # Unit tests (fast, isolated)
│   ├── client/
│   │   ├── test_utils_logger.py
│   │   ├── test_utils_progress.py
│   │   ├── test_utils_file_handler.py
│   │   ├── test_xls_transfer_core.py
│   │   ├── test_xls_transfer_embeddings.py
│   │   ├── test_xls_transfer_translation.py
│   │   └── test_xls_transfer_excel_utils.py
│   └── server/
│       ├── test_api_logs.py
│       ├── test_api_auth.py
│       ├── test_api_stats.py
│       ├── test_database_models.py
│       └── test_database_crud.py
│
├── integration/                 # Integration tests (multiple components)
│   ├── client/
│   │   ├── test_xls_transfer_workflow.py
│   │   ├── test_logging_integration.py
│   │   └── test_ui_integration.py
│   └── server/
│       ├── test_api_endpoints.py
│       ├── test_database_operations.py
│       └── test_stats_aggregation.py
│
├── e2e/                         # End-to-end tests (full workflows)
│   ├── client/
│   │   └── test_full_tool_workflow.py
│   └── server/
│       └── test_full_server_workflow.py
│
├── fixtures/                    # Test data and fixtures
│   ├── sample_excel_files/
│   ├── sample_models/
│   └── sample_configs/
│
└── helpers/                     # Test utilities
    ├── mock_server.py
    ├── test_data_generators.py
    └── assertions.py
```

---

## 🏃 Running Tests

### **Run All Tests**
```bash
pytest
```

### **Run by Type**
```bash
# Unit tests only (fast)
pytest -m unit

# Integration tests
pytest -m integration

# End-to-end tests
pytest -m e2e

# Client tests only
pytest -m client

# Server tests only
pytest -m server

# Database tests
pytest -m database

# Network tests
pytest -m network
```

### **Run by Component**
```bash
# All client tests
pytest tests/unit/client/

# All server tests
pytest tests/unit/server/

# Specific module
pytest tests/unit/client/test_utils_logger.py

# Specific test
pytest tests/unit/client/test_utils_logger.py::test_log_operation
```

### **Run with Coverage**
```bash
# Generate coverage report
pytest --cov=client --cov=server --cov-report=html

# View coverage report
open htmlcov/index.html  # or xdg-open on Linux
```

### **Run in Watch Mode** (for development)
```bash
# Install pytest-watch
pip install pytest-watch

# Auto-run tests on file changes
ptw
```

---

## ✅ Test Requirements

### **Every Test Must Have:**
1. **Clear docstring** - What it tests and why
2. **Descriptive name** - `test_function_does_what_when_condition`
3. **Arrange-Act-Assert** pattern
4. **Proper markers** - @pytest.mark.unit, etc.
5. **Clean fixtures** - Use conftest.py
6. **No hardcoded paths** - Use fixtures and Path()
7. **Cleanup** - Remove temp files after test

### **Example of CLEAN Test:**
```python
import pytest
from pathlib import Path

@pytest.mark.unit
@pytest.mark.client
def test_file_handler_validates_existing_file(tmp_path):
    """
    Test that file_handler correctly validates an existing file.

    Given: A temporary file exists
    When: validate_file_exists() is called
    Then: Returns (True, "") indicating success
    """
    # Arrange
    test_file = tmp_path / "test.xlsx"
    test_file.write_text("test content")

    # Act
    from server.utils.client.file_handler import validate_file_exists
    is_valid, error = validate_file_exists(str(test_file), ['.xlsx'])

    # Assert
    assert is_valid is True
    assert error == ""
```

---

## 🧪 Test Coverage Goals

**Minimum Coverage**: 80% (enforced by pytest.ini)
**Target Coverage**: 90%+

### **Coverage by Component:**
- **Utilities**: 95%+ (critical reusable code)
- **Tools (XLSTransfer, etc.)**: 90%+
- **Server API**: 90%+
- **Database**: 90%+
- **UI**: 70%+ (harder to test, but still important)

---

## 🔍 What We Test

### **1. Unit Tests** (Fast, Isolated)

**Client Utils:**
- ✅ Logger sends correct data format
- ✅ Logger queues when server unavailable
- ✅ Progress tracker updates correctly
- ✅ File handler validates files properly
- ✅ File handler creates safe filenames
- ✅ File handler manages temp files

**XLSTransfer:**
- ✅ Text cleaning removes unwanted characters
- ✅ Column conversion works correctly
- ✅ Code pattern detection finds all codes
- ✅ Embedding generation produces correct shapes
- ✅ FAISS index creation works
- ✅ Translation matching returns correct results
- ✅ Excel reading handles all formats

**Server:**
- ✅ API endpoints validate input
- ✅ Database models have correct fields
- ✅ CRUD operations work correctly
- ✅ Authentication validates credentials
- ✅ Stats aggregation calculates correctly

### **2. Integration Tests** (Multiple Components)

**Client:**
- ✅ Logger + Progress work together
- ✅ File upload → Processing → Download workflow
- ✅ XLSTransfer full dictionary creation
- ✅ XLSTransfer full translation workflow
- ✅ UI updates when processing completes

**Server:**
- ✅ API → Database → Response flow
- ✅ Log entry → Stats aggregation → Dashboard
- ✅ Authentication → Session → Logging
- ✅ Multiple concurrent users

### **3. End-to-End Tests** (Full Workflows)

**Complete User Flows:**
- ✅ User logs in → Uses tool → Sees stats
- ✅ Upload file → Process → Download result
- ✅ Create dictionary → Load → Translate
- ✅ Admin views dashboard → Exports report

**Network Tests:**
- ✅ Client connects to server
- ✅ Logs sent successfully
- ✅ Server returns correct responses
- ✅ Handles network errors gracefully

**Database Tests:**
- ✅ Tables created correctly
- ✅ Data persists across connections
- ✅ Queries return correct results
- ✅ Aggregation views work

---

## 🛠️ Test Utilities

### **Fixtures** (in conftest.py)

```python
@pytest.fixture
def sample_excel_file(tmp_path):
    """Create a sample Excel file for testing."""
    # Implementation

@pytest.fixture
def mock_server():
    """Mock server for client tests."""
    # Implementation

@pytest.fixture
def test_database():
    """Temporary test database."""
    # Implementation
```

### **Mock Objects**

```python
# Mock Korean BERT model (fast for testing)
@pytest.fixture
def mock_model():
    class MockModel:
        def encode(self, texts):
            return [[0.1] * 384 for _ in texts]
    return MockModel()
```

### **Test Data Generators**

```python
# Generate realistic test data
def generate_excel_with_translations(rows=100):
    # Creates Excel with KR and translation columns
    pass
```

---

## 📊 Test Reporting

### **After Running Tests:**

**Terminal Output:**
```
tests/unit/client/test_utils_logger.py::test_log_operation PASSED     [ 10%]
tests/unit/client/test_utils_progress.py::test_update PASSED           [ 20%]
...
==================== 50 passed in 2.34s ====================

Coverage: 87%
Missing lines: client/utils/logger.py (45-47, 102)
```

**HTML Coverage Report:**
- Open `htmlcov/index.html` in browser
- See line-by-line coverage
- Identify untested code

### **CI/CD Integration** (Future)

```yaml
# .github/workflows/test.yml
- name: Run tests
  run: pytest

- name: Upload coverage
  run: codecov
```

---

## 🧹 Keeping Tests CLEAN

**DO:**
- ✅ Use descriptive test names
- ✅ One assertion per test (when possible)
- ✅ Use fixtures for common setup
- ✅ Clean up temp files
- ✅ Mark tests appropriately
- ✅ Document complex tests
- ✅ Keep tests fast (use mocks)

**DON'T:**
- ❌ Hardcode file paths
- ❌ Rely on external services (mock them)
- ❌ Leave temp files behind
- ❌ Write slow tests without @pytest.mark.slow
- ❌ Test implementation details (test behavior)
- ❌ Duplicate test code (use fixtures)
- ❌ Commit failing tests

---

## 🔄 Test-Driven Development (TDD)

**For New Features:**

1. **Write test first** (it will fail)
2. **Write minimal code** to pass
3. **Refactor** while keeping tests green
4. **Repeat**

**Example:**
```python
# 1. Write test (fails)
def test_new_feature():
    result = new_feature(input)
    assert result == expected

# 2. Implement feature (test passes)
def new_feature(input):
    return expected

# 3. Refactor (tests still pass)
def new_feature(input):
    # Cleaner implementation
    return expected
```

---

## 📈 Test Metrics

**We Track:**
- ✅ Test count (goal: 200+ tests)
- ✅ Coverage percentage (goal: 90%+)
- ✅ Test execution time (goal: <30s for unit tests)
- ✅ Flaky tests (goal: 0)
- ✅ Test maintenance (tests updated with code)

---

## 🚀 Continuous Testing

**During Development:**
```bash
# Terminal 1: Watch mode
ptw

# Terminal 2: Code changes
# Tests auto-run on save
```

**Before Commit:**
```bash
# Run all tests
pytest

# Check coverage
pytest --cov

# Fix any failures
```

**In CI/CD:**
- All tests run automatically
- Coverage report generated
- Failures block merge

---

## 📝 Test Documentation

**Each test file has:**
- Module docstring explaining what's tested
- Individual test docstrings
- Comments for complex assertions
- Examples of expected behavior

---

**COMPREHENSIVE TESTING = ROBUST CODE** ✅

**No bloat. CLEAN, organized, thorough.**
