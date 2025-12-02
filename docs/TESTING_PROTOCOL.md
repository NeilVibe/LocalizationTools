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
│   ├── test_kr_similar_e2e.py        # KR Similar: 18 tests (embeddings, search, etc.)
│   ├── test_xlstransfer_e2e.py       # XLSTransfer: 9 tests (dictionary, translation)
│   ├── test_quicksearch_e2e.py       # QuickSearch: 11 tests (search, dictionary)
│   ├── test_complete_user_flow.py    # 9 tests (cross-app workflows)
│   ├── test_edge_cases_e2e.py        # 24 tests (edge cases, special chars)
│   ├── test_real_workflows_e2e.py    # 14 tests (true simulation workflows)
│   └── test_production_workflows_e2e.py  # 18 tests (full production simulations)
├── fixtures/                  # Shared test data (CRITICAL!)
│   ├── __init__.py                   # Pattern documentation & helpers
│   ├── sample_language_data.txt      # KR Similar fixture (23 rows, comprehensive)
│   ├── sample_quicksearch_data.txt   # QuickSearch fixture (36 rows)
│   ├── sample_dictionary.xlsx        # XLSTransfer fixture (Excel format)
│   └── sample_to_translate.txt       # Translation input fixture (production format)
├── integration/               # API integration tests
│   ├── test_api_endpoints.py
│   └── test_server_startup.py
├── unit/                      # Fast unit tests
│   ├── client/               # Client utilities
│   │   ├── test_utils_logger.py
│   │   ├── test_utils_progress.py
│   │   └── test_utils_file_handler.py
│   └── test_server/
│       └── test_websocket.py     # WebSocket tests (13 tests)
├── test_async_auth.py         # Auth tests (6 async tests)
├── test_dashboard_api.py      # Admin Dashboard (20 tests, 16 endpoints)
├── test_kr_similar.py         # KR Similar unit tests
├── test_quicksearch_phase4.py
├── test_xlstransfer_cli.py
└── conftest.py
```

### Test Coverage Summary (2025-12-02)

| Category | Tests | Coverage |
|----------|-------|----------|
| **App E2E Tests** | | |
| - KR Similar | 27 (18 unit + 9 API) | All 9 endpoints |
| - XLSTransfer | 17 (9 unit + 8 API) | All 8 endpoints |
| - QuickSearch | 19 (11 unit + 8 API) | All 8 endpoints |
| **API User Simulation Tests** | | |
| - Tools Simulation | 26 | Full user workflows |
| - Admin Simulation | 15 | User/session/log management |
| - Error Handling | 25 | Auth, validation, recovery |
| - WebSocket/Polling | 10 | Real-time, reconnection |
| **Infrastructure** | | |
| - Admin Dashboard | 20 | 16/16 endpoints |
| - Authentication | 6 | JWT, roles, activation |
| - WebSocket | 13 | Events, rooms, real-time |
| - Client Utils | 86 | Logger, progress, file handler |
| **Total** | **450** | 49% code coverage |

### API User Simulation Test Files (NEW - 2025-12-02)

| File | Tests | Description |
|------|-------|-------------|
| `tests/api/test_api_tools_simulation.py` | 26 | Simulates real user workflows for all 3 tools |
| `tests/api/test_api_admin_simulation.py` | 15 | Simulates admin operations: users, sessions, logs |
| `tests/api/test_api_error_handling.py` | 25 | Auth errors, validation, edge cases, recovery |
| `tests/api/test_api_websocket.py` | 10 | WebSocket connection, messaging, HTTP polling |
| **Total API Simulation** | **76** | TRUE PRODUCTION SIMULATION |

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

## Test Data Design Philosophy

> **Key Insight:** Test data should be SIMPLE but COMPREHENSIVE. It must cover all real-world patterns, not just basic cases.

### The Problem We Solved

Early test fixtures were "too simple" - they had correct structure (columns, tabs) but missed critical patterns from real production data:

| Pattern | Real Data Has | Simple Test Data Had |
|---------|---------------|---------------------|
| Multiple tag blocks per cell | 3-5 `{ChangeScene}{AudioVoice}` blocks | 1 block only |
| Complex voice IDs | `NPC_VCE_NEW_8513_2_11_Iksun` | `NPC_001` |
| Multiple `\n` in one cell | 5+ newlines | 1-2 newlines |
| Non-English translations | French, German, etc. | English only |
| Empty trailing columns | `\t\t` at end | `None\tCategory` |
| Korean dialect variations | `있잖아요?`, `싶어유!` | Standard Korean |

**Result:** Tests passed but production code could still fail on real data!

### Design Principles

#### 1. Structure Must Match Exactly
```
# Real production format (tab-separated):
COL0	COL1	COL2	COL3	COL4	KOREAN_TEXT	TRANSLATION	NOTES	CATEGORY

# Test fixture MUST have same columns, same separators
39	7924197	1001	0	1	{Tag}Korean	{Tag}English	None	Dialog
```

#### 2. Cover ALL Tag Patterns
Real data has these patterns that MUST be in test fixtures:

```python
# Pattern 1: Multiple tags at start
"{ChangeScene(X)}{AudioVoice(Y)}Text here"

# Pattern 2: Tags mid-text (after newline)
"First line\n{ChangeScene(X)}{AudioVoice(Y)}Second line"

# Pattern 3: Multiple tag+text blocks in ONE cell
"{Tag1}Line1\n{Tag2}Line2\n{Tag3}Line3"

# Pattern 4: Nested/complex tag names
"{AudioVoice(NPC_VCE_NEW_8513_2_11_Iksun)}"

# Pattern 5: HTML-like tags
"<color=red>Warning</color>"

# Pattern 6: Scale/formatting tags
"{Scale(1.2)}Big text{/Scale}"
```

#### 3. Cover Edge Cases in Content
```python
# Korean with punctuation variations
"안녕하세요!"      # Exclamation
"뭐라고요?"       # Question
"그렇군요..."     # Ellipsis

# Dialect markers
"있잖아유?"       # Regional dialect
"했슈?"          # Informal speech

# Special characters in text
"▶ 선택하세요"    # Bullet points
"【경고】"        # Brackets

# Mixed content
"HP: 100 / MP: 50"  # Numbers and colons
```

#### 4. Keep It Simple, Not Simplistic
- Simple = Easy to read and understand
- Simplistic = Missing important patterns

```python
# WRONG (simplistic):
"Hello"  # Too basic, misses all patterns

# RIGHT (simple but comprehensive):
"{ChangeScene(Main_001)}{AudioVoice(NPC_001)}안녕하세요.\n{AudioVoice(NPC_002)}반갑습니다!"
# Covers: multiple tags, newline, Korean text, punctuation
```

### Real Data Reference

Production data comes from `RessourcesForCodingTheProject/datausedfortesting/langsampleallweneed.txt`.

**Key characteristics:**
- Tab-separated (not comma, not space)
- 7+ columns per row
- Korean source with French/English translations
- Complex inline tags for scenes and voice
- Multi-line content within single cells (using `\n`)
- Voice asset naming: `NPC_VCE_NEW_[ID]_[SEQ]_[Name]`
- Scene naming: `MorningMain_XX_XXX`, `MorningLand_NPC_XXXXX`

### Comprehensive Test Pattern Checklist

When creating/updating fixtures, verify these patterns are covered:

- [ ] **Basic single tag**: `{Tag}Text`
- [ ] **Multiple tags start**: `{Tag1}{Tag2}Text`
- [ ] **Tags after newline**: `Text\n{Tag}More text`
- [ ] **Multiple blocks per cell**: `{T1}L1\n{T2}L2\n{T3}L3`
- [ ] **Complex tag names**: `{AudioVoice(NPC_VCE_NEW_8504_26_10_Name)}`
- [ ] **Scene references**: `{ChangeScene(MorningMain_04_137)}`
- [ ] **Empty columns**: Row ends with `\t\t` or `\tNone\t`
- [ ] **Korean punctuation**: `!`, `?`, `...`, `~`
- [ ] **Special characters**: `▶`, `【】`, `<color>`, `{Scale}`
- [ ] **Numbers in text**: `HP: 100`, `레벨 5`
- [ ] **Long text (100+ chars)**: Test truncation handling

### Future Claude Sessions: Remember This

When working on tests:
1. **Don't assume simple = correct** - Check against real data patterns
2. **Compare with `langsampleallweneed.txt`** - The source of truth
3. **Run pattern checklist above** - Before marking fixtures "complete"
4. **Update this doc** - When you discover new patterns

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

## Security Changes Verification Protocol ⚠️ IMPORTANT

**CRITICAL**: After adding ANY security features (IP filter, CORS, JWT, etc.), ALWAYS verify existing functionality still works!

Security middleware can accidentally break:
- API endpoints (403 errors)
- Inter-service communication (CORS blocks)
- Authentication flows (JWT issues)
- WebSocket connections

### Post-Security Change Checklist

Run this EVERY TIME after security changes:

```bash
# Step 1: Run ALL security tests (must pass 100%)
python -m pytest tests/security/ -v --override-ini="addopts="
# Expected: 86+ tests passed

# Step 2: Run app functionality tests (must pass 100%)
python -m pytest tests/test_kr_similar.py tests/test_quicksearch_phase4.py -v --override-ini="addopts="
# Expected: All passed

# Step 3: Verify security modules load without errors
python3 -c "
from server import config
from server.middleware.ip_filter import IPFilterMiddleware
from server.utils.audit_logger import log_login_success
print('✓ All security modules load correctly')
"

# Step 4: Start server and verify health
python3 server/main.py &
sleep 5
curl -s http://localhost:8888/health | python3 -m json.tool
# Expected: {"status": "healthy", ...}

# Step 5: Verify API endpoints work
curl -s http://localhost:8888/api/v2/kr-similar/health
curl -s http://localhost:8888/api/v2/quicksearch/health
curl -s http://localhost:8888/api/v2/xlstransfer/health
# Expected: All return {"status": "ok"}

# Step 6: Kill test server
pkill -f "python3 server/main.py"
```

### Security Test Summary (Updated 2025-12-02)

| Test File | Tests | What It Verifies |
|-----------|-------|------------------|
| `test_cors_config.py` | 11 | CORS origin restrictions |
| `test_ip_filter.py` | 24 | IP range filtering |
| `test_jwt_security.py` | 22 | SECRET_KEY validation, security modes |
| `test_audit_logging.py` | 29 | Login/block event logging |
| **Total Security Tests** | **86** | Full security coverage |

### E2E Test Summary (Updated 2025-12-02)

| Test File | Tests | What It Verifies |
|-----------|-------|------------------|
| `test_kr_similar_e2e.py` | 18 | BERT embeddings, similarity search |
| `test_quicksearch_e2e.py` | 11 | Dictionary search, Korean data |
| `test_xlstransfer_e2e.py` | 9 | Excel translation pipeline |
| `test_edge_cases_e2e.py` | 23 | Empty/unicode/special chars |
| `test_complete_user_flow.py` | 9 | Cross-app workflows |
| `test_real_workflows_e2e.py` | 14 | Production patterns |
| `test_production_workflows_e2e.py` | 18 | Full pipelines |
| **Total E2E Tests** | **102** | All pass ✅ |

### API User Simulation Tests (Updated 2025-12-02)

| Test File | Tests | What It Simulates |
|-----------|-------|-------------------|
| `test_api_auth_integration.py` | 11 | Login, JWT, session management |
| `test_api_tools_simulation.py` | 26 | **REAL USER workflows via API** |
| **Total API Tests** | **37** | All pass ✅ |

**API Simulation Coverage:**
- ✅ KR Similar: health → list → create → load → search → edge cases
- ✅ QuickSearch: health → list → create → load → search modes
- ✅ XLSTransfer: health → list → create → translate
- ✅ Cross-tool: session persistence, activity tracking

### If Tests Fail After Security Changes

1. **403 Forbidden errors** → Check IP filter config, CORS origins
2. **401 Unauthorized** → Check JWT SECRET_KEY, token expiry
3. **Connection refused** → Check server binding (0.0.0.0 vs 127.0.0.1)
4. **CORS blocked** → Add origin to CORS_ORIGINS whitelist

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

**After security changes:**
```bash
python -m pytest tests/security/ tests/test_kr_similar.py tests/test_quicksearch_phase4.py -v --override-ini="addopts="
```

---

*Last updated: 2025-12-02*
*Protocol version: 2.3 (added API user simulation tests)*
*Total tests: 450 | E2E: 102 | API Simulation: 37 | Security: 86*
