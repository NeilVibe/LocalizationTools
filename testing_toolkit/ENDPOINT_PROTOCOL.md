# Endpoint Protocol

> **MASTER GUIDE** for API endpoint lifecycle: Discovery → Registry → Testing → Audit → CI/CD

**Last Updated:** 2026-01-01 | **Endpoints:** 206 | **Tests:** 159+

---

## Quick Commands

```bash
# FULL AUDIT (coverage + docs + security)
python3 scripts/endpoint_audit.py

# Coverage report only
python3 scripts/endpoint_audit.py --coverage

# Documentation quality check
python3 scripts/endpoint_audit.py --docs

# Security audit (unprotected endpoints)
python3 scripts/endpoint_audit.py --security

# Generate HTML dashboard
python3 scripts/endpoint_audit.py --html
# → docs/endpoint_audit_report.html

# Auto-generate test stubs for missing endpoints
python3 scripts/endpoint_audit.py --generate-stubs
# → tests/api/test_generated_stubs.py

# JSON output for CI/CD pipelines
python3 scripts/endpoint_audit.py --json

# Strict mode (exit 1 if coverage < 80%)
python3 scripts/endpoint_audit.py --strict

# Run all endpoint tests
python3 -m pytest tests/api/test_all_endpoints.py -v
```

---

## 1. Endpoint Discovery

### How to Find All Endpoints

```bash
# Method 1: Grep for FastAPI decorators
grep -rn "@router\.\(get\|post\|put\|delete\|patch\)" server/ --include="*.py"

# Method 2: Use OpenAPI spec (runtime)
curl http://localhost:8888/openapi.json | jq '.paths | keys[]'

# Method 3: Automated script (recommended)
python3 scripts/endpoint_audit.py --discover
```

### Endpoint Categories

| Category | Path Prefix | Description |
|----------|-------------|-------------|
| Auth | `/api/v1/auth/*` | Login, logout, token refresh |
| Users | `/api/v1/users/*` | User management |
| LDM Projects | `/api/v1/ldm/projects/*` | Project CRUD |
| LDM Folders | `/api/v1/ldm/folders/*` | Folder operations |
| LDM Files | `/api/v1/ldm/files/*` | File upload/download |
| LDM Rows | `/api/v1/ldm/rows/*` | Row CRUD, search |
| LDM TM | `/api/v1/ldm/tm/*` | Translation Memory |
| LDM Settings | `/api/v1/ldm/settings/*` | User preferences |
| Tools | `/api/v1/tools/*` | XLSTransfer, QuickSearch |
| System | `/health`, `/api/v1/system/*` | Health, telemetry |

---

## 2. Endpoint Registry

### Registry Location

```
docs/ENDPOINT_REGISTRY.md  ← Auto-generated, DO NOT edit manually
```

### Registry Format

```markdown
| # | Method | Path | Auth | Tested | Test File |
|---|--------|------|------|--------|-----------|
| 1 | GET | /health | No | ✅ | test_all_endpoints.py:15 |
| 2 | POST | /api/v1/auth/login | No | ✅ | test_all_endpoints.py:23 |
| 3 | GET | /api/v1/users/me | Yes | ✅ | test_all_endpoints.py:45 |
```

### Updating Registry

```bash
# Regenerate after adding new endpoints
python3 scripts/endpoint_audit.py --registry > docs/ENDPOINT_REGISTRY.md
git add docs/ENDPOINT_REGISTRY.md
git commit -m "Update endpoint registry"
```

---

## 3. Test Requirements

### Every Endpoint MUST Have

| Test Type | Required | Description |
|-----------|----------|-------------|
| Happy path | ✅ YES | Valid request returns expected response |
| Auth check | ✅ YES | Unauthenticated request returns 401 (if protected) |
| Validation | ✅ YES | Invalid input returns 422 with clear error |
| Not found | ⚠️ If applicable | Missing resource returns 404 |
| Permission | ⚠️ If applicable | Unauthorized access returns 403 |

### Test File Structure

```
tests/api/
├── test_all_endpoints.py      ← Master test file (159 tests)
├── test_auth.py               ← Auth-specific edge cases
├── test_ldm_projects.py       ← LDM project edge cases
├── test_ldm_files.py          ← File upload/download edge cases
└── conftest.py                ← Shared fixtures
```

### Adding Tests for New Endpoint

```python
# In test_all_endpoints.py

# 1. Add to the appropriate section
class TestLDMProjects:

    # 2. Use descriptive test name
    def test_create_project_success(self, client, auth_headers):
        """POST /api/v1/ldm/projects - create new project"""
        response = client.post(
            "/api/v1/ldm/projects",
            json={"name": "Test Project"},
            headers=auth_headers
        )
        assert response.status_code == 201
        assert "id" in response.json()

    # 3. Add validation test
    def test_create_project_invalid_name(self, client, auth_headers):
        """POST /api/v1/ldm/projects - reject empty name"""
        response = client.post(
            "/api/v1/ldm/projects",
            json={"name": ""},
            headers=auth_headers
        )
        assert response.status_code == 422

    # 4. Add auth test
    def test_create_project_no_auth(self, client):
        """POST /api/v1/ldm/projects - require authentication"""
        response = client.post(
            "/api/v1/ldm/projects",
            json={"name": "Test"}
        )
        assert response.status_code == 401
```

---

## 4. Audit Process

### Weekly Audit Checklist

```bash
# 1. Regenerate endpoint list from code
python3 scripts/endpoint_audit.py --discover > /tmp/endpoints_code.txt

# 2. Get endpoints from OpenAPI
curl -s http://localhost:8888/openapi.json | jq -r '.paths | keys[]' | sort > /tmp/endpoints_api.txt

# 3. Compare (should match)
diff /tmp/endpoints_code.txt /tmp/endpoints_api.txt

# 4. Check test coverage
python3 scripts/endpoint_audit.py --audit
```

### Audit Output Example

```
ENDPOINT AUDIT REPORT
=====================
Total endpoints: 118
Tested: 118 (100%)
Untested: 0

COVERAGE BY CATEGORY:
- Auth: 5/5 (100%)
- LDM Projects: 12/12 (100%)
- LDM Folders: 8/8 (100%)
- LDM Files: 15/15 (100%)
- LDM Rows: 20/20 (100%)
- LDM TM: 20/20 (100%)
...
```

### When Audit Fails

1. **New endpoint found without test:**
   ```bash
   # Add test immediately
   # Update test_all_endpoints.py
   # Re-run audit
   ```

2. **Endpoint removed but test exists:**
   ```bash
   # Remove obsolete test
   # Update registry
   ```

3. **Endpoint changed signature:**
   ```bash
   # Update test to match new signature
   # Verify all edge cases still covered
   ```

---

## 5. CI/CD Integration

### Pipeline Stages

```yaml
# .gitea/workflows/build.yaml

jobs:
  test:
    steps:
      # Stage 1: Unit tests
      - name: Run unit tests
        run: python3 -m pytest tests/unit/ -v

      # Stage 2: Endpoint tests (CRITICAL)
      - name: Run endpoint tests
        run: python3 -m pytest tests/api/test_all_endpoints.py -v --tb=short

      # Stage 3: Audit (fail if untested endpoints)
      - name: Endpoint audit
        run: |
          python3 scripts/endpoint_audit.py --audit --strict
          # --strict = fail if any endpoint untested
```

### Required CI Checks

| Check | Blocking | Description |
|-------|----------|-------------|
| Endpoint tests pass | ✅ YES | All 159 tests must pass |
| No untested endpoints | ✅ YES | Audit must show 100% coverage |
| No breaking changes | ✅ YES | Existing endpoints maintain compatibility |
| OpenAPI spec valid | ⚠️ Warning | Spec should be parseable |

### Pre-commit Hook

```bash
# .git/hooks/pre-push (optional)
#!/bin/bash

echo "Running endpoint audit..."
python3 scripts/endpoint_audit.py --audit --strict || {
    echo "ERROR: Untested endpoints found!"
    echo "Add tests before pushing."
    exit 1
}
```

---

## 6. Adding New Endpoints

### Developer Checklist

When adding a new endpoint:

- [ ] **1. Implement endpoint** in `server/api/` or `server/tools/`
- [ ] **2. Add OpenAPI docs** (summary, description, responses)
- [ ] **3. Write tests** in `tests/api/test_all_endpoints.py`
  - [ ] Happy path test
  - [ ] Auth test (if protected)
  - [ ] Validation test
- [ ] **4. Run audit** to verify coverage
- [ ] **5. Update registry** if needed
- [ ] **6. Run full test suite** before commit

### Example: Adding New Endpoint

```python
# 1. server/api/ldm/exports.py
@router.post("/exports/batch", summary="Export multiple files")
async def batch_export(
    request: BatchExportRequest,
    current_user: User = Depends(get_current_user)
) -> BatchExportResponse:
    """Export multiple files as a ZIP archive."""
    ...

# 2. tests/api/test_all_endpoints.py
class TestLDMExports:
    def test_batch_export_success(self, client, auth_headers):
        """POST /api/v1/ldm/exports/batch - export multiple files"""
        response = client.post(
            "/api/v1/ldm/exports/batch",
            json={"file_ids": [1, 2, 3]},
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"

    def test_batch_export_no_auth(self, client):
        """POST /api/v1/ldm/exports/batch - require auth"""
        response = client.post("/api/v1/ldm/exports/batch", json={})
        assert response.status_code == 401

    def test_batch_export_empty_list(self, client, auth_headers):
        """POST /api/v1/ldm/exports/batch - reject empty list"""
        response = client.post(
            "/api/v1/ldm/exports/batch",
            json={"file_ids": []},
            headers=auth_headers
        )
        assert response.status_code == 422
```

---

## 7. Versioning

### Current Version

```
/api/v1/*  ← All current endpoints
```

### Versioning Rules

| Rule | Description |
|------|-------------|
| No breaking changes in v1 | Add fields, don't remove |
| Deprecate before remove | Mark deprecated, remove in v2 |
| New features in v1 | Unless incompatible |
| Major overhaul = v2 | New version for breaking changes |

### Deprecation Process

```python
# 1. Mark as deprecated in code
@router.get("/old-endpoint", deprecated=True)
async def old_endpoint():
    """DEPRECATED: Use /new-endpoint instead."""
    ...

# 2. Add warning header
response.headers["X-Deprecated"] = "Use /api/v1/new-endpoint"

# 3. Log usage
logger.warning(f"Deprecated endpoint called: /old-endpoint by {user.id}")

# 4. Remove after 2 major versions
```

---

## 8. Documentation

### OpenAPI Requirements

Every endpoint MUST have:

```python
@router.post(
    "/example",
    summary="Short description (required)",        # ✅ Required
    description="Longer explanation if needed",    # Optional
    response_model=ExampleResponse,                # ✅ Required
    responses={                                    # ✅ Required
        200: {"description": "Success"},
        401: {"description": "Not authenticated"},
        422: {"description": "Validation error"},
    },
    tags=["category"],                             # ✅ Required
)
```

### Viewing Docs

```
http://localhost:8888/docs      ← Swagger UI
http://localhost:8888/redoc     ← ReDoc
http://localhost:8888/openapi.json  ← Raw spec
```

---

## 9. Monitoring & Alerts

### What to Monitor

| Metric | Alert Threshold | Action |
|--------|-----------------|--------|
| Response time | > 500ms | Investigate slow endpoint |
| Error rate | > 1% | Check logs, fix bug |
| 401 rate | > 10% | Possible auth issue |
| 404 rate | > 5% | Client using wrong paths |

### Logging Requirements

```python
# Every endpoint should log:
logger.info(f"[{request_id}] {method} {path} - {status_code} in {duration}ms")

# Errors should include context:
logger.error(f"[{request_id}] Failed to process: {error}", exc_info=True)
```

---

## 10. Quick Reference

### File Locations

```
server/api/                    ← API route definitions
server/tools/ldm/routes/       ← LDM-specific routes
tests/api/test_all_endpoints.py ← Master test file
scripts/endpoint_audit.py      ← Audit script (TODO: create)
docs/ENDPOINT_REGISTRY.md      ← Auto-generated registry
```

### Commands Cheat Sheet

```bash
# Test all endpoints
pytest tests/api/test_all_endpoints.py -v

# Test specific category
pytest tests/api/test_all_endpoints.py -k "LDM" -v

# Test single endpoint
pytest tests/api/test_all_endpoints.py -k "test_create_project" -v

# Generate coverage report
pytest tests/api/ --cov=server --cov-report=html

# View OpenAPI spec
curl http://localhost:8888/openapi.json | jq '.paths | keys | length'
```

---

## Appendix: Current Stats

| Metric | Value |
|--------|-------|
| Total endpoints | 118 |
| Total tests | 159 |
| Coverage | 100% |
| Categories | 10 |
| Avg tests per endpoint | 1.35 |

**Last audit:** 2026-01-01
**Next audit:** Weekly (automated in CI)

---

*Protocol version 1.0 - Created 2026-01-01*
