# Code Review: LDM API

**Date:** 2025-12-15 | **Reviewer:** Claude | **File:** `server/tools/ldm/api.py`

**Trigger:** CDP testing revealed API response format inconsistency

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 2 |
| HIGH | 3 |
| MEDIUM | 4 |
| LOW | 2 |

---

## CRITICAL Issues

### CR-001: Inconsistent API Response Formats

**Location:** Multiple endpoints
**Impact:** Client code breaks, debugging nightmare

**Current State:**
| Endpoint | Returns | Format |
|----------|---------|--------|
| `GET /projects` | `List[ProjectResponse]` | Plain array `[...]` |
| `GET /folders` | `List[FolderResponse]` | Plain array `[...]` |
| `GET /files` | `List[FileResponse]` | Plain array `[...]` |
| `GET /files/{id}/rows` | `PaginatedRows` | **Wrapped** `{"rows": [...]}` |
| `GET /tm` | `List[TMResponse]` | Plain array `[...]` |
| `GET /tm/{id}/search` | dict | **Wrapped** `{"results": [...]}` |
| `GET /tm/suggest` | dict | **Wrapped** `{"suggestions": [...]}` |

**Problem:**
- `/files/{id}/rows` returns `{"rows": [...], "total": ..., "page": ...}`
- But `/projects`, `/folders`, `/files` return plain arrays
- Client code doing `data[0]` fails on rows endpoint

**Fix Options:**
1. **Standardize ALL list endpoints to use wrappers** (recommended for pagination support)
2. **Add plain array endpoint for rows** (`/files/{id}/rows/all`)
3. **Document clearly** which format each endpoint uses

**Recommended Fix:**
```python
# Option 1: Wrapper for all list endpoints
class PaginatedProjects(BaseModel):
    projects: List[ProjectResponse]
    total: int
    page: int = 1
    limit: int = 50

# OR Option 2: Add non-paginated endpoint
@router.get("/files/{file_id}/rows/all", response_model=List[RowResponse])
async def list_all_rows(...):  # Returns plain array
```

---

### CR-002: SQL Injection Pattern in TM Suggest

**Location:** Lines 766-771
**Impact:** Potential SQL injection

```python
# DANGEROUS - f-string into SQL
if file_id:
    conditions.append(f"r.file_id = {file_id}")  # Line 768
elif project_id:
    conditions.append(f"f.project_id = {project_id}")  # Line 770
if exclude_row_id:
    conditions.append(f"r.id != {exclude_row_id}")  # Line 771
```

**Why It's Risky:**
- Even though FastAPI validates these as `int`, the pattern is dangerous
- Copy-paste to string fields would be catastrophic
- Code review might miss this if query params change

**Fix:**
```python
# Use parameterized queries
conditions = ["r.target IS NOT NULL", "r.target != ''"]
params = {'search_text': source.strip(), 'threshold': threshold, 'max_results': max_results}

if file_id:
    conditions.append("r.file_id = :file_id")
    params['file_id'] = file_id
elif project_id:
    conditions.append("f.project_id = :project_id")
    params['project_id'] = project_id
if exclude_row_id:
    conditions.append("r.id != :exclude_row_id")
    params['exclude_row_id'] = exclude_row_id
```

---

## HIGH Issues

### CR-003: Deprecated asyncio.get_event_loop()

**Location:** Lines 869, 1076, 1157, 1304
**Impact:** Deprecation warning in Python 3.10+, may fail in 3.12+

```python
# Current (deprecated)
loop = asyncio.get_event_loop()
result = await loop.run_in_executor(None, _upload_tm)
```

**Fix:**
```python
# Correct approach
result = await asyncio.to_thread(_upload_tm)

# Or if you need the loop:
loop = asyncio.get_running_loop()
result = await loop.run_in_executor(None, _upload_tm)
```

---

### CR-004: Missing Response Models

**Location:** Multiple endpoints
**Impact:** No OpenAPI schema, client codegen fails

| Endpoint | Issue |
|----------|-------|
| `GET /projects/{id}/tree` | Returns dict, no model |
| `DELETE /projects/{id}` | Returns dict, no model |
| `DELETE /folders/{id}` | Returns dict, no model |
| `DELETE /tm/{id}` | Returns dict, no model |
| `GET /tm/suggest` | Returns dict, no model |
| `GET /tm/{id}/search/exact` | Returns dict, no model |
| `GET /tm/{id}/search` | Returns dict, no model |

**Fix:** Add Pydantic response models for all endpoints.

---

### CR-005: Sync DB Sessions in Async Handlers

**Location:** Lines 852-867, 1067-1074, 1129-1153, 1270-1301
**Impact:** Connection pool exhaustion under load

```python
def _upload_tm():
    sync_db = next(get_db())  # Takes connection from pool
    try:
        # Long operation...
    finally:
        sync_db.close()  # Returns to pool

loop = asyncio.get_event_loop()
result = await loop.run_in_executor(None, _upload_tm)
```

**Problem:**
- Each executor call holds a sync DB connection
- Under concurrent load, pool can exhaust
- `next(get_db())` is meant for request scope, not manual use

**Fix:**
- Use dedicated sync connection pool for background tasks
- Or refactor TMManager to be async

---

## MEDIUM Issues

### CR-006: No Threshold Validation

**Location:** Line 726
**Impact:** Invalid values could cause unexpected behavior

```python
threshold: float = 0.70  # No validation
```

**Fix:**
```python
threshold: float = Query(0.70, ge=0.0, le=1.0)
```

---

### CR-007: Error Messages Leak Internal Details

**Location:** Lines 809-811, 874, 1162, 1313

```python
except Exception as e:
    logger.error(f"TM suggest failed: {e}")
    raise HTTPException(status_code=500, detail=f"TM search failed: {str(e)}")
```

**Problem:** `str(e)` may contain internal paths, query details, etc.

**Fix:**
```python
except Exception as e:
    logger.error(f"TM suggest failed: {e}", exc_info=True)
    raise HTTPException(status_code=500, detail="TM search failed. Check server logs.")
```

---

### CR-008: WebSocket Broadcast Silently Fails

**Location:** Lines 623-636

```python
try:
    from server.tools.ldm.websocket import broadcast_cell_update
    await broadcast_cell_update(...)
except Exception as e:
    logger.warning(f"Failed to broadcast cell update: {e}")
```

**Issue:** Import inside function + silently swallowed error

**Fix:**
- Move import to top of file
- Consider whether broadcast failure should affect response

---

### CR-009: Tree Building is O(n*m)

**Location:** Lines 679-702

```python
def build_tree(parent_id=None):
    tree = []
    for folder in folders:  # O(n) for each level
        if folder.parent_id == parent_id:
            tree.append({...})
    for file in files:  # O(m) for each level
        ...
```

**Impact:** With 1000 folders nested 10 deep = 10,000 iterations

**Fix:** Build lookup dict first:
```python
folder_by_parent = defaultdict(list)
for folder in folders:
    folder_by_parent[folder.parent_id].append(folder)
```

---

## LOW Issues

### CR-010: Hardcoded Source Language

**Location:** Lines 1281, 472-473

```python
source_lang="ko",  # Hardcoded
target_language=None  # Set later based on project settings (comment lies)
```

---

### CR-011: Magic Numbers

**Location:** Lines 504-505

```python
page: int = Query(1, ge=1),
limit: int = Query(50, ge=1, le=200),  # Why 200?
```

Should be constants with documentation.

---

## Action Items

| Priority | Issue | Effort | Fix |
|----------|-------|--------|-----|
| P0 | CR-001 | Medium | Standardize response formats |
| P0 | CR-002 | Low | Parameterize SQL |
| P1 | CR-003 | Low | Replace deprecated asyncio calls |
| P1 | CR-004 | Medium | Add response models |
| P1 | CR-005 | High | Refactor sync DB usage |
| P2 | CR-006 | Low | Add validation |
| P2 | CR-007 | Low | Sanitize error messages |
| P2 | CR-008 | Low | Move import, improve logging |
| P2 | CR-009 | Low | Optimize tree building |
| P3 | CR-010 | Low | Make configurable |
| P3 | CR-011 | Low | Extract constants |

---

## Root Cause of CDP Test Failure

**Issue:** CR-001 (Inconsistent Response Formats)

The CDP test was calling `/api/ldm/files/1/rows` and doing:
```javascript
const rows = await resp.json();
rows[0].id  // undefined!
```

But the endpoint returns:
```json
{"rows": [...], "total": 10, "page": 1, "limit": 50, "total_pages": 1}
```

Should have been:
```javascript
const data = await resp.json();
data.rows[0].id  // correct
```

**Prevention:** OpenAPI/TypeScript client codegen would catch this.

---

## CI Testing Gap Analysis

### Why Did 865 Tests Miss These Issues?

**The Problem:** We have 865 tests passing, but NONE caught:
- Inconsistent API response formats
- SQL injection patterns
- Deprecated asyncio usage
- Missing response models

### Test Coverage Analysis

| Directory | In CI? | Test Files | Purpose |
|-----------|--------|------------|---------|
| `tests/unit/` | YES | 20 | Unit tests (heavy mocking) |
| `tests/integration/` | YES | 11 | Integration tests |
| `tests/security/` | YES | 4 | Security tests |
| `tests/e2e/` | PARTIAL | 3 of 8 | E2E tests |
| `tests/api/` | **NO** | 7 | **API tests - EXCLUDED!** |
| `tests/cdp/` | **NO** | 1 | **CDP tests - EXCLUDED!** |

### Critical Gaps

#### GAP-001: API Tests Not in CI

```yaml
# From .gitea/workflows/build.yml
TEST_DIRS="tests/unit/ tests/integration/ tests/security/ ..."
# Missing: tests/api/ tests/cdp/
```

**Impact:** 8 test files with actual API endpoint tests are never run!

**Irony:** `tests/cdp/test_download_format.py` line 94:
```python
rows = response.json()["rows"]  # Test KNOWS about wrapper!
```
This test would have caught CR-001, but it's not in CI.

---

#### GAP-002: Unit Tests Mock Too Much

```bash
$ grep -r "mock\|Mock\|patch" tests/unit/ | wc -l
229  # 229 mock usages!
```

**Problem:** Unit tests mock the database, HTTP client, etc. They test internal logic but never verify actual API contracts.

---

#### GAP-003: No Schema/Contract Tests

```bash
$ grep -r "pydantic\|schema\|openapi" tests/ -l
# No files testing API response schemas!
```

**Missing:**
- No tests that validate response matches Pydantic model
- No OpenAPI schema validation tests
- No contract testing (consumer-driven contracts)

---

#### GAP-004: No SQL Pattern Scanning

Security tests exist but don't scan for:
- f-string SQL patterns
- Raw SQL usage
- Unparameterized queries

---

#### GAP-005: No Deprecation Checks

No tests or linting for:
- `asyncio.get_event_loop()` deprecation
- Other Python version compatibility issues

---

### Test Suite Metrics

| Metric | Value | Issue |
|--------|-------|-------|
| Total test functions | 1,226 | |
| Total test files | 63 | |
| Files in CI | 42 (67%) | 33% excluded! |
| LDM API endpoint tests | ~7 lines | Almost zero |
| Mock usage in unit tests | 229 | Over-mocking |
| Schema validation tests | 0 | No contract tests |

---

### Recommended CI Overhaul

#### Phase 1: Include Missing Tests (Immediate)

```yaml
# build.yml change
TEST_DIRS="tests/unit/ tests/integration/ tests/security/ tests/api/ tests/cdp/ tests/e2e/"
```

#### Phase 2: Add Contract Tests

```python
# tests/contract/test_api_schemas.py
from fastapi.testclient import TestClient
from pydantic import ValidationError

def test_rows_endpoint_returns_paginated_response():
    """Verify /files/{id}/rows returns PaginatedRows schema"""
    response = client.get("/api/ldm/files/1/rows", headers=auth)

    # Must have these fields (not just status 200)
    assert "rows" in response.json()
    assert "total" in response.json()
    assert "page" in response.json()

    # Validate against Pydantic model
    PaginatedRows(**response.json())  # Raises if invalid
```

#### Phase 3: Add Security Scanning

```yaml
# Add to CI
- name: Security scan
  run: |
    # Check for SQL injection patterns
    ! grep -rn 'f".*{.*}.*SELECT\|f".*{.*}.*WHERE\|f".*{.*}.*INSERT' server/

    # Check for deprecated patterns
    ! grep -rn 'get_event_loop()' server/
```

#### Phase 4: Reduce Mock Dependency

**Current:**
```python
@patch('server.database.get_db')
@patch('server.tools.ldm.api.get_current_user')
def test_something(mock_user, mock_db):
    # Tests nothing real
```

**Better:**
```python
def test_something(test_client, test_db):
    # Use real TestClient with test database
    response = test_client.get("/api/ldm/projects")
    assert response.status_code == 200
    assert isinstance(response.json(), list)  # Verify actual format!
```

---

### Summary: Why Tests Failed to Catch Issues

| Issue | Why Missed | Fix |
|-------|-----------|-----|
| CR-001 (Response format) | API tests excluded from CI | Include `tests/api/` |
| CR-002 (SQL injection) | No security pattern scanning | Add grep checks |
| CR-003 (Deprecated asyncio) | No deprecation linting | Add pylint checks |
| CR-004 (Missing models) | No schema validation tests | Add contract tests |
| CR-005 (Sync DB) | Unit tests mock DB | Use real test DB |

**Root Cause:** Test suite optimized for speed (mocking) over correctness (integration).
