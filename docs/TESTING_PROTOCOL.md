# TESTING_PROTOCOL.md - Full Autonomous Testing Guide

**Version:** 2511302345
**Purpose:** Complete protocol for running FULL tests with server, API, and all components operational

---

## Overview

This document describes the **AUTONOMOUS TESTING PROTOCOL** - a step-by-step process to run comprehensive tests that verify ALL functionality, including API endpoints that require a running server.

**Key Principle:** Don't treat "requires running server" as a blocker. Start the server yourself!

---

## Quick Reference

### One-Liner Full Test (Copy-Paste Ready)

```bash
# Create admin, start server, run ALL tests
python3 scripts/create_admin.py && \
python3 server/main.py &
sleep 5 && \
RUN_API_TESTS=1 python3 -m pytest -v
```

### Verify Everything Works

```bash
# Check all 3 apps are operational
TOKEN=$(curl -s -X POST http://localhost:8888/api/v2/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8888/api/v2/xlstransfer/health
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8888/api/v2/quicksearch/health
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8888/api/v2/kr-similar/health
```

---

## Full Testing Protocol

### Step 1: Setup Admin Credentials

```bash
python3 scripts/create_admin.py
```

**Expected Output:**
```
✓ Admin user created: admin (ID: X)
Username: admin
Password: admin123
```

**Default Credentials:**
- Username: `admin`
- Password: `admin123`
- Role: `superadmin`

---

### Step 2: Start the Server

```bash
# Start in background
python3 server/main.py &
sleep 5

# Verify server is running
curl -s http://localhost:8888/health | python3 -m json.tool
```

**Expected Response:**
```json
{
    "status": "healthy",
    "database": "connected",
    "version": "1.0.0"
}
```

---

### Step 3: Verify All Apps Are Operational

```bash
# Get JWT token
TOKEN=$(curl -s -X POST http://localhost:8888/api/v2/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Test each app
echo "=== XLSTransfer ===" && curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8888/api/v2/xlstransfer/health
echo "=== QuickSearch ===" && curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8888/api/v2/quicksearch/health
echo "=== KR Similar ===" && curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8888/api/v2/kr-similar/health
```

**Expected Responses:**
```json
{"status":"ok","modules_loaded":{"core":true,"embeddings":true,"translation":true}}
{"status":"ok","modules_loaded":{"dictionary_manager":true,"searcher":true}}
{"status":"ok","modules_loaded":{"embeddings_manager":true,"searcher":true},"models_available":true}
```

---

### Step 4: Run Full Test Suite

```bash
# Run ALL tests including API tests
RUN_API_TESTS=1 python3 -m pytest -v

# Or run specific test categories
RUN_API_TESTS=1 python3 -m pytest tests/test_kr_similar.py tests/e2e/test_kr_similar_e2e.py -v
```

---

### Step 5: Cleanup

```bash
# Kill server when done
pkill -f "python3 server/main.py"
```

---

## Test Organization

### Folder Structure

```
tests/
├── archive/                   # Deprecated tests (don't delete, archive!)
│   └── README.md
├── e2e/                       # End-to-end tests (full pipeline with real data)
│   ├── test_complete_user_flow.py
│   ├── test_full_workflow.py
│   └── test_kr_similar_e2e.py    # KR Similar E2E (15 tests)
├── fixtures/                  # Shared test data
│   ├── __init__.py
│   └── sample_language_data.txt  # Mock language data (20 rows)
├── integration/               # API integration tests
│   ├── test_api_endpoints.py
│   └── test_server_startup.py
├── unit/                      # Fast unit tests
│   ├── client/
│   └── test_server/
├── test_kr_similar.py         # KR Similar unit tests (15 tests)
├── test_quicksearch_phase4.py
├── test_xlstransfer_cli.py
└── conftest.py
```

### When to Use Each Folder

| Folder | Purpose | Server Required? |
|--------|---------|------------------|
| `unit/` | Test single functions in isolation | No |
| `integration/` | Test API endpoints | Sometimes |
| `e2e/` | Test full pipelines with real data | Usually |
| `fixtures/` | Shared test data | N/A |
| `archive/` | Old/deprecated tests | N/A |

---

## Creating Comprehensive Tests

### Template: New App E2E Test

```python
"""
End-to-End Tests for [APP_NAME] (App #X)

Full integration tests that:
1. Create a TEST dictionary from fixture data
2. Load the dictionary
3. Test all main functions
4. Verify API endpoints
"""

import pytest
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Fixtures are in tests/fixtures/ (shared by all tests)
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"

# Test dictionary type (use "TEST" to avoid overwriting real data)
TEST_DICT_TYPE = "TEST"


class TestAppNameE2E:
    """End-to-end tests for [APP_NAME]."""

    @pytest.fixture(scope="class")
    def setup_test_environment(self):
        """Setup test environment."""
        # Add TEST to allowed types if needed
        yield
        # Cleanup after tests

    @pytest.fixture(scope="class")
    def fixture_file(self):
        """Get path to fixture data file."""
        fixture_path = FIXTURES_DIR / "sample_data.txt"
        assert fixture_path.exists(), f"Fixture file not found: {fixture_path}"
        return str(fixture_path)

    def test_01_module_loads(self):
        """Test that modules load successfully."""
        # Import and verify
        pass

    def test_02_process_data(self, fixture_file):
        """Test processing fixture data."""
        # Load and process
        pass

    def test_03_api_endpoint(self):
        """Test API endpoint (requires server)."""
        # Only runs if RUN_API_TESTS=1
        pass


class TestAppNameAPI:
    """API tests (require running server)."""

    @pytest.mark.skipif(
        not os.environ.get("RUN_API_TESTS"),
        reason="API tests require running server (set RUN_API_TESTS=1)"
    )
    def test_api_health(self):
        """Test health endpoint."""
        import requests
        # Login and test
        pass
```

### Test Naming Convention

```
test_XX_descriptive_name
     │
     └── Number for ordering (01, 02, 03...)

Examples:
- test_01_model_loads_successfully
- test_02_encode_texts
- test_03_create_dictionary
- test_04_load_dictionary
- test_05_similarity_search
```

### Fixture Data Guidelines

1. **Location:** Always in `tests/fixtures/`
2. **Format:** Match real data structure exactly
3. **Size:** 10-50 rows (enough to test, fast to run)
4. **Naming:** `sample_[type]_data.[ext]`

Example fixture (`sample_language_data.txt`):
```
39	7924197	1001	0	1	{ChangeScene(Main_001)}안녕하세요.	{ChangeScene(Main_001)}Hello.	None	NPC Dialog
```

---

## Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `RUN_API_TESTS` | Enable API tests that require server | `0` (disabled) |
| `TEST_DATABASE_URL` | Override database for testing | Uses main DB |

---

## Test Coverage Goals

| Component | Target | Minimum |
|-----------|--------|---------|
| Core modules | 90%+ | 80% |
| API endpoints | 85%+ | 70% |
| E2E flows | 80%+ | 60% |

---

## Troubleshooting

### "Login failed" in API tests

**Problem:** Admin credentials not found

**Solution:**
```bash
python3 scripts/create_admin.py
```

### "Connection refused" in API tests

**Problem:** Server not running

**Solution:**
```bash
python3 server/main.py &
sleep 5
```

### Tests pass locally but fail in CI

**Problem:** CI doesn't have server running

**Solution:** Skip API tests in CI or add server startup to CI workflow

---

## CI/CD Integration

### GitHub Actions Example

```yaml
- name: Setup admin
  run: python3 scripts/create_admin.py

- name: Start server
  run: |
    python3 server/main.py &
    sleep 5

- name: Run full tests
  run: RUN_API_TESTS=1 python3 -m pytest -v
```

---

## Best Practices

### DO

- **Run server before API tests** - Don't skip them
- **Use fixtures from `tests/fixtures/`** - Shared data
- **Archive old tests** - Don't delete, move to `archive/`
- **Number tests for ordering** - `test_01_`, `test_02_`
- **Use TEST dict type** - Don't overwrite real data
- **Clean up after tests** - Remove temp files/dicts

### DON'T

- **Treat "requires server" as blocker** - Start it!
- **Skip API tests by default** - They're important
- **Hardcode credentials** - Use fixtures/config
- **Leave orphan test data** - Always cleanup
- **Delete old tests** - Archive them

---

## Summary

**The key insight:** Nothing blocks autonomous testing. If a test needs:
- Server → Start it: `python3 server/main.py &`
- Admin → Create it: `python3 scripts/create_admin.py`
- Data → Use fixtures: `tests/fixtures/`

**Full test command:**
```bash
python3 scripts/create_admin.py && python3 server/main.py & sleep 5 && RUN_API_TESTS=1 python3 -m pytest -v
```

---

*Last updated: 2025-11-30*
*Protocol version: 1.0*
