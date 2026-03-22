# Phase 60: Integration Testing - Research

**Researched:** 2026-03-23
**Domain:** End-to-end verification of merge pipeline (backend API + UI + QuickTranslate adapter)
**Confidence:** HIGH

## Summary

Phase 60 is a verification phase, not a feature-building phase. All 26 v6.0 requirements (MOCK-01 through UI-09) are marked complete across phases 56-59. The goal is to confirm the full pipeline works end-to-end: mock data setup, path configuration, merge preview (dry-run), merge execution with SSE streaming, and output verification -- across single-language and multi-language scenarios with all 3 match types.

The project has an established pytest infrastructure with conftest.py fixtures, marker system, and directory conventions. For API-level integration tests, the existing pattern uses `requests` against a running server (`localhost:8888`). For UI-level testing, Playwright scripts exist in `testing_toolkit/scripts/` using the Vite dev server at `localhost:5173`. Phase 60 testing should use both layers: (1) pytest-based API integration tests for the merge endpoints, and (2) manual or Playwright-based UI walkthrough for the modal flow.

**Primary recommendation:** Write pytest integration tests calling the merge API endpoints directly (preview + execute SSE), using the mock data from `setup_mock_data.py` and real test files from the test123 directory. Verify SSE stream parsing, match type results, and multi-language breakdown. UI verification via Playwright screenshots confirms the modal state machine works visually.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MOCK-01 | CLI script creates mock platform with 3 projects | Verify via `setup_mock_data.py --confirm-wipe` execution |
| MOCK-02 | Auto-detect language from project name | Verify language badges in UI via Playwright |
| MOCK-03 | project_MULTI has language-suffixed subfolders | Verify multi-language scan endpoint response |
| MOCK-04 | test123 languagedata files loadable as LOC data | Verify path validation endpoint with test123 path |
| SET-01 | LOC PATH configurable in Settings | Verify via projectSettings store + API validation |
| SET-02 | EXPORT PATH configurable in Settings | Same as SET-01 |
| SET-03 | Path validation (exists + contains languagedata) | Test `/api/settings/validate-path` endpoint |
| XFER-01 | Adapter imports QT modules via sys.path | Verify `init_quicktranslate()` succeeds |
| XFER-02 | StringID Only match type works | Test via `/api/merge/preview` with `match_mode=stringid_only` |
| XFER-03 | StringID+StrOrigin match type works | Test via `/api/merge/preview` with `match_mode=strict` |
| XFER-04 | StrOrigin+FileName 2PASS works | Test via `/api/merge/preview` with `match_mode=strorigin_filename` |
| XFER-05 | 8-step postprocess runs after merge | Verify postprocess markers in execute result |
| XFER-06 | Transfer scope (all vs untranslated) | Test both `only_untranslated=true/false` |
| XFER-07 | Multi-language folder merge | Test via `/api/merge/preview` with `multi_language=true` |
| API-01 | Preview returns dry-run summary | Validate response schema (files, entries, matches) |
| API-02 | Execute streams SSE progress | Parse SSE events, verify progress/log/complete events |
| API-03 | Summary report on completion | Verify `complete` SSE event contains counts |
| API-04 | Multi-language preview breakdown | Verify `per_language` dict in preview response |
| UI-01 | Merge button in toolbar | Playwright screenshot verification |
| UI-02 | Right-click context menu entry | Playwright screenshot verification |
| UI-03 | 4-phase modal (configure/preview/execute/done) | Playwright walkthrough with screenshots |
| UI-04 | Category filter toggle for StringID mode | Playwright screenshot in StringID mode |
| UI-05 | Dry-run preview panel | Playwright screenshot after preview |
| UI-06 | Progress display during execution | Playwright screenshot during/after execute |
| UI-07 | Summary report on completion | Playwright screenshot of done phase |
| UI-08 | Language badge in modal header | Playwright screenshot verification |
| UI-09 | Multi-language mode shows detected languages | Playwright screenshot of multi-lang preview |
</phase_requirements>

## Standard Stack

### Core (Testing)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | 7.x+ | Test framework | Already in project conftest.py |
| requests | 2.x | HTTP client for API tests | Already used in conftest.py |
| httpx | 0.27+ | Async HTTP + SSE stream parsing | Better SSE support than requests |
| Playwright | 1.x | UI screenshot verification | Already installed in testing_toolkit/cdp/ |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| sse-starlette | (installed) | Server-side SSE | Already in server deps |
| sseclient-py | 1.8+ | Client-side SSE parsing for tests | Parsing execute endpoint responses |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| httpx for SSE | Raw requests + manual parsing | httpx has built-in streaming; manual parsing works too but more code |
| sseclient-py | Manual line-by-line parsing | sseclient handles reconnect/retry fields automatically |
| Playwright for UI | Manual browser testing | Playwright gives reproducible screenshots as evidence |

## Architecture Patterns

### Test File Structure
```
tests/
  integration/
    test_merge_pipeline.py     # Plan 01: E2E single + multi-language
    test_merge_match_types.py  # Plan 02: All 3 match types with real data
```

### Pattern 1: API Integration Test with Running Server
**What:** Tests hit the actual FastAPI server endpoints, not TestClient mocks
**When to use:** When verifying the full stack including QuickTranslate imports
**Example:**
```python
# Existing project pattern from tests/conftest.py
import requests

BASE_URL = "http://localhost:8888"

def test_merge_preview():
    token = get_admin_token_with_retry()
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.post(f"{BASE_URL}/api/merge/preview", json={
        "source_path": "/path/to/corrections",
        "target_path": "/path/to/loc",
        "export_path": "/path/to/export",
        "match_mode": "strict",
    }, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total_matched" in data
```

### Pattern 2: SSE Stream Parsing for Execute Endpoint
**What:** POST to execute endpoint, read SSE event stream, collect events
**When to use:** Verifying SSE progress streaming works end-to-end
**Example:**
```python
import requests

def test_merge_execute_sse():
    resp = requests.post(
        f"{BASE_URL}/api/merge/execute",
        json={...},
        headers=headers,
        stream=True,
    )
    assert resp.status_code == 200

    events = []
    for line in resp.iter_lines(decode_unicode=True):
        if line.startswith("event:"):
            event_type = line.split(":", 1)[1].strip()
        elif line.startswith("data:"):
            data = line.split(":", 1)[1].strip()
            events.append({"event": event_type, "data": data})

    # Must have at least one progress event and one complete event
    event_types = [e["event"] for e in events]
    assert "complete" in event_types
```

### Pattern 3: Mock Data Setup as Test Fixture
**What:** Run `setup_mock_data.py --confirm-wipe` before tests, configure paths
**When to use:** Test precondition setup
**Example:**
```python
import subprocess

@pytest.fixture(scope="module")
def mock_data_ready():
    """Ensure mock DB is populated before tests."""
    result = subprocess.run(
        ["python3", "scripts/setup_mock_data.py", "--confirm-wipe"],
        capture_output=True, text=True, cwd=PROJECT_ROOT
    )
    assert result.returncode == 0
```

### Anti-Patterns to Avoid
- **Mocking QuickTranslate internals:** The point of integration testing is to verify the REAL QT modules load and execute. Do NOT mock transfer_folder_to_folder.
- **Testing without server running:** These are integration tests. They require `DEV_MODE=true python3 server/main.py` running.
- **Ignoring WSL path translation:** Test paths must account for `translate_wsl_path()` -- use Linux paths in DEV_MODE.
- **Hardcoding test123 Windows paths:** Use `/mnt/c/Users/MYCOM/Desktop/oldoldVold/test123/` (WSL-translated).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SSE parsing | Custom line parser | requests stream=True + simple line parser | SSE format is trivial (event:/data: lines) |
| Test data setup | Manual SQL inserts | `setup_mock_data.py --confirm-wipe` | Script already handles FK ordering and admin user |
| Path translation | Manual /mnt/c conversion | `translate_wsl_path()` in server/api/settings.py | Already handles DEV_MODE detection |

## Common Pitfalls

### Pitfall 1: Server Not Running
**What goes wrong:** Tests fail with ConnectionRefusedError
**Why it happens:** Integration tests require a live server
**How to avoid:** Add `@pytest.mark.requires_server` marker, check health endpoint in fixture
**Warning signs:** `ConnectionError` in test output

### Pitfall 2: Stale QT Module Cache
**What goes wrong:** Config shim has wrong paths from previous test run
**Why it happens:** `_qt_modules` is module-level cache, persists across requests
**How to avoid:** Call `reconfigure_paths()` with correct paths before each test scenario
**Warning signs:** Merge results reference wrong languagedata files

### Pitfall 3: test123 Files Not Available
**What goes wrong:** Tests fail because test123 path doesn't exist
**Why it happens:** test123 lives on Windows desktop, may not be accessible from WSL
**How to avoid:** Use fixture that checks path existence, skip test if unavailable
**Warning signs:** `FileNotFoundError` or `valid: false` from path validation

### Pitfall 4: SSE Stream Not Closing
**What goes wrong:** Test hangs waiting for more SSE events
**Why it happens:** The complete/error event terminates the stream, but if never received, iter_lines blocks
**How to avoid:** Set a timeout on the requests call (e.g., `timeout=60`)
**Warning signs:** Test hangs indefinitely

### Pitfall 5: Concurrent Merge Guard
**What goes wrong:** Second test gets 409 Conflict
**Why it happens:** `_merge_in_progress` global flag prevents concurrent merges
**How to avoid:** Run execute tests sequentially (not in parallel), wait for complete event before next test
**Warning signs:** `409` status code, "A merge is already in progress"

### Pitfall 6: Auth Token Needed for Merge Endpoints
**What goes wrong:** 401/403 responses
**Why it happens:** Merge endpoints may require authentication
**How to avoid:** Use `get_admin_token_with_retry()` from conftest.py
**Warning signs:** Check if merge router has auth dependencies

## Code Examples

### Complete Preview Test
```python
import pytest
import requests

BASE_URL = "http://localhost:8888"
TEST123_PATH = "/mnt/c/Users/MYCOM/Desktop/oldoldVold/test123"

@pytest.mark.requires_server
@pytest.mark.integration
def test_preview_strict_match(admin_headers_session):
    """Test dry-run preview with strict (StringID+StrOrigin) match mode."""
    resp = requests.post(
        f"{BASE_URL}/api/merge/preview",
        json={
            "source_path": TEST123_PATH,
            "target_path": TEST123_PATH,  # same dir for test
            "export_path": TEST123_PATH,
            "match_mode": "strict",
            "only_untranslated": False,
            "multi_language": False,
        },
        headers=admin_headers_session,
        timeout=30,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "total_matched" in data
    assert "errors" in data
```

### Complete SSE Execute Test
```python
@pytest.mark.requires_server
@pytest.mark.integration
def test_execute_streams_progress(admin_headers_session):
    """Test that execute endpoint streams SSE progress events."""
    resp = requests.post(
        f"{BASE_URL}/api/merge/execute",
        json={
            "source_path": TEST123_PATH,
            "target_path": "/tmp/merge_test_target",
            "export_path": TEST123_PATH,
            "match_mode": "strict",
        },
        headers=admin_headers_session,
        stream=True,
        timeout=120,
    )
    assert resp.status_code == 200

    events = []
    current_event = "message"
    for line in resp.iter_lines(decode_unicode=True):
        if not line:
            continue
        if line.startswith("event:"):
            current_event = line[6:].strip()
        elif line.startswith("data:"):
            events.append({"event": current_event, "data": line[5:].strip()})
            if current_event in ("complete", "error"):
                break

    event_types = [e["event"] for e in events]
    assert "complete" in event_types or "error" in event_types
```

### Multi-Language Preview Test
```python
@pytest.mark.requires_server
@pytest.mark.integration
def test_multi_language_preview(admin_headers_session):
    """Test multi-language preview returns per-language breakdown."""
    resp = requests.post(
        f"{BASE_URL}/api/merge/preview",
        json={
            "source_path": "/path/to/multi_source",
            "target_path": "/path/to/loc",
            "export_path": "/path/to/export",
            "match_mode": "strict",
            "multi_language": True,
        },
        headers=admin_headers_session,
        timeout=30,
    )
    assert resp.status_code == 200
    data = resp.json()
    # Multi-language response should have scan and per_language
    assert "scan" in data or "per_language" in data
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| EventSource for SSE | fetch + ReadableStream (POST) | Phase 59 | Execute endpoint is POST, not GET -- EventSource only supports GET |
| Separate single/multi endpoints | Single endpoint with `multi_language` flag | Phase 58 | Simpler API surface |
| Manual path entry in modal | Auto-fill from project settings | Phase 56-59 | Paths come from localStorage via `getProjectSettings()` |

## Open Questions

1. **Auth requirement on merge endpoints**
   - What we know: The merge API router is mounted at app level (`app.include_router(merge_api.router)`) and also within LDM router. Need to verify if auth middleware applies.
   - What's unclear: Whether `/api/merge/preview` and `/api/merge/execute` require Bearer token
   - Recommendation: Test both with and without auth headers; use admin token from conftest

2. **test123 data suitability for all 3 match types**
   - What we know: test123 contains `languagedata_fr PC *.txt` files -- these are languagedata format files
   - What's unclear: Whether these files have the right attributes (StringID, StrOrigin, FileName) for all 3 match modes
   - Recommendation: Plan 02 should create minimal synthetic XML test fixtures if test123 doesn't cover all modes

3. **Merge target safety for tests**
   - What we know: Execute (non-dry-run) writes to the target folder
   - What's unclear: Need to use a temp copy of target files so tests don't destroy real data
   - Recommendation: Copy test files to `/tmp/merge_test_*` before each execute test, clean up after

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 7.x |
| Config file | tests/conftest.py (exists) |
| Quick run command | `python3 -m pytest tests/integration/test_merge_pipeline.py -x -v` |
| Full suite command | `python3 -m pytest tests/integration/test_merge_*.py -v` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SC-60-1 | Full merge workflow succeeds with project_FRE | integration | `pytest tests/integration/test_merge_pipeline.py::test_full_single_language_workflow -x` | Wave 0 |
| SC-60-2 | Multi-language merge processes FRE+ENG subfolders | integration | `pytest tests/integration/test_merge_pipeline.py::test_multi_language_workflow -x` | Wave 0 |
| SC-60-3 | All 3 match types produce correct output | integration | `pytest tests/integration/test_merge_match_types.py -x` | Wave 0 |
| SC-60-4 | SSE events stream correctly (no drops, 100%) | integration | `pytest tests/integration/test_merge_pipeline.py::test_sse_streaming -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `python3 -m pytest tests/integration/test_merge_pipeline.py -x -v --timeout=120`
- **Per wave merge:** `python3 -m pytest tests/integration/test_merge_*.py -v --timeout=120`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/integration/test_merge_pipeline.py` -- covers SC-60-1, SC-60-2, SC-60-4
- [ ] `tests/integration/test_merge_match_types.py` -- covers SC-60-3
- [ ] Test data fixtures: synthetic XML files for controlled match type testing

## Sources

### Primary (HIGH confidence)
- Direct code inspection: `server/api/merge.py` -- merge endpoints, request/response models
- Direct code inspection: `server/services/transfer_adapter.py` -- adapter, match modes, multi-language
- Direct code inspection: `server/services/transfer_config_shim.py` -- config injection
- Direct code inspection: `scripts/setup_mock_data.py` -- mock data script
- Direct code inspection: `locaNext/src/lib/components/ldm/MergeModal.svelte` -- modal component
- Direct code inspection: `tests/conftest.py` -- existing test infrastructure

### Secondary (MEDIUM confidence)
- test123 file listing (`/mnt/c/Users/MYCOM/Desktop/oldoldVold/test123/`) -- confirmed via `ls`
- QuickTranslate core modules listing -- confirmed via filesystem inspection

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - existing pytest infrastructure fully inspected
- Architecture: HIGH - all implementation files read and understood
- Pitfalls: HIGH - identified from direct code analysis (global merge guard, module cache, path translation)

**Research date:** 2026-03-23
**Valid until:** 2026-04-23 (stable -- verification phase, no external dependencies)
