# P30: CI/CD Pipeline Optimization

**Created:** 2025-12-15 | **Status:** PLANNING | **Priority:** Medium

---

## Overview

Optimize the CI/CD pipeline for faster feedback and better coverage. Current state:
- **Total build time:** ~22 minutes
- **Safety-checks job:** ~17 minutes (tests + security)
- **Build-windows job:** ~5 minutes
- **Test count:** 1226 test functions

---

## 1. Smoke Test (Installer Verification)

### Problem
Current pipeline builds the installer but never runs it. Path issues (like `resourcesPath` bug) slip through.

### Solution: Post-Install Smoke Test

Add to `build-windows` job after NSIS packaging:

```yaml
- name: Smoke Test - Install and Verify
  shell: pwsh
  run: |
    $installer = Get-ChildItem "installer_output\*Setup*.exe" | Select-Object -First 1

    # 1. Silent install
    Write-Host "Installing $($installer.Name)..."
    Start-Process -FilePath $installer.FullName -Args '/S /D=C:\LocaNextTest' -Wait

    # 2. Check files exist
    $checks = @(
      'C:\LocaNextTest\LocaNext.exe',
      'C:\LocaNextTest\resources\server\main.py',
      'C:\LocaNextTest\resources\tools\python\python.exe',
      'C:\LocaNextTest\resources\version.py'
    )
    foreach ($path in $checks) {
      if (!(Test-Path $path)) {
        Write-Error "SMOKE TEST FAILED: Missing $path"
        exit 1
      }
    }

    # 3. Launch app and wait for backend
    Write-Host "Launching LocaNext..."
    $process = Start-Process 'C:\LocaNextTest\LocaNext.exe' -PassThru

    # 4. Wait for backend health endpoint
    $maxRetries = 30
    $ready = $false
    for ($i = 0; $i -lt $maxRetries; $i++) {
      Start-Sleep -Seconds 2
      try {
        $response = Invoke-WebRequest -Uri 'http://localhost:8888/health' -UseBasicParsing -TimeoutSec 5
        if ($response.StatusCode -eq 200) {
          Write-Host "Backend is healthy!"
          $ready = $true
          break
        }
      } catch {
        Write-Host "Waiting for backend... ($i/$maxRetries)"
      }
    }

    # 5. Cleanup
    Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue

    if (!$ready) {
      Write-Error "SMOKE TEST FAILED: Backend never became healthy"
      exit 1
    }

    Write-Host "SMOKE TEST PASSED"
```

**Estimated time:** +2-3 minutes

### What This Catches
- Missing files after packaging
- Wrong path resolution in production mode
- Backend startup failures
- Python embedding issues

---

## 2. Current Test Structure

### Test Count by Directory

| Directory | Tests | In CI? | Notes |
|-----------|-------|--------|-------|
| `tests/unit/` | 687 | ✅ Yes | Fast, isolated |
| `tests/integration/` | 169 | ✅ Yes | DB + server tests |
| `tests/e2e/` | 116 | ✅ Partial | Only 3 files run |
| `tests/api/` | 121 | ❌ **NO** | Not in TEST_DIRS! |
| `tests/security/` | ~30 | ✅ Yes | Auth, CORS, JWT |
| `tests/archive/` | ~5 | ❌ No | Deprecated |
| **Total** | ~1226 | ~912 | |

### Finding: `tests/api/` Not Running!

The `tests/api/` directory (121 tests) is NOT included in the CI pipeline:

```bash
TEST_DIRS="tests/unit/ tests/integration/ tests/security/ tests/e2e/..."
# No tests/api/ !
```

**Options:**
1. Add `tests/api/` to CI → More coverage but longer runtime
2. Remove `tests/api/` → If redundant with integration tests
3. Merge into `tests/integration/` → Consolidate

**Action needed:** Review if `tests/api/` is redundant or missing from CI.

---

## 3. Potential Redundancies

### Files with `sleep()` (Slow Tests)

```
tests/api/test_api_full_system_integration.py
tests/api/test_api_tools_simulation.py
tests/api/test_api_websocket.py
tests/api/test_remote_logging.py
tests/integration/server_tests/test_auth_integration.py
```

These likely have artificial delays. Could be optimized with:
- Reduce sleep times
- Use async waiting instead of fixed sleeps
- Mock slow operations

### Deselected Tests (Known Slow)

Already deselected in CI:
```
--deselect=tests/integration/test_tm_real_model.py  # ML model loading
--deselect=tests/e2e/test_xlstransfer_e2e.py::*embedding*  # Embedding tests
```

These are correctly skipped - they require ML models.

### E2E Tests - Only 3 Files Run

```
tests/e2e/test_kr_similar_e2e.py
tests/e2e/test_xlstransfer_e2e.py
tests/e2e/test_quicksearch_e2e.py
```

**Not running:**
- `test_full_simulation.py`
- `test_production_workflows_e2e.py`
- `test_complete_user_flow.py`
- `test_real_workflows_e2e.py`
- `test_edge_cases_e2e.py`

**Question:** Are these deprecated or intentionally skipped?

---

## 4. Optimization Strategies

### Option A: Fast Mode (QUICK builds)

Add `Build LIGHT QUICK` trigger that runs only critical tests:

```yaml
# In check-build-trigger
if [[ "$TRIGGER_LINE" == *"QUICK"* ]]; then
  echo "quick_mode=true" >> $GITHUB_OUTPUT
fi

# In safety-checks
if: needs.check-build-trigger.outputs.quick_mode != 'true'
```

**Result:** Skip 17-min safety-checks for quick iteration.

### Option B: Parallel Test Jobs

Split tests across multiple jobs:

```yaml
test-unit:
  runs-on: ubuntu-latest
  # 687 unit tests (~5 min)

test-integration:
  runs-on: ubuntu-latest
  # 169 integration tests (~8 min)

test-security:
  runs-on: ubuntu-latest
  # 30 security tests (~2 min)
```

**Result:** 17 min → ~8 min (parallel)
**Cost:** More runner usage

### Option C: Test Duration Analysis

Run locally to identify slow tests:

```bash
python3 -m pytest tests/ --durations=50 2>&1 | tail -60
```

Then optimize or deselect the slowest ones.

### Option D: Remove Redundant Tests

If `tests/api/` duplicates `tests/integration/`, remove one.

---

## 5. Recommended Actions

### Phase 1: Quick Wins (Do Now)
- [ ] Add smoke test to build-windows job
- [ ] Review `tests/api/` - add to CI or delete if redundant
- [ ] Run `--durations=50` locally to find slow tests

### Phase 2: Optimization (Next Sprint)
- [ ] Add `QUICK` mode for fast iteration builds
- [ ] Consider parallel test jobs if runner resources available
- [ ] Clean up unused e2e tests or add them to CI

### Phase 3: Advanced (Future)
- [ ] Add Playwright/Spectron for full Electron UI tests
- [ ] Add visual regression tests for UI
- [ ] Add performance benchmarks

---

## 6. Implementation Checklist

- [ ] **Smoke Test**
  - [ ] Add silent install step
  - [ ] Add file verification
  - [ ] Add backend health check
  - [ ] Add cleanup step

- [ ] **Test Audit**
  - [ ] Run `--durations=50` analysis
  - [ ] Review `tests/api/` redundancy
  - [ ] Review skipped e2e tests
  - [ ] Document findings

- [ ] **Quick Mode**
  - [ ] Add `QUICK` trigger detection
  - [ ] Skip safety-checks on QUICK
  - [ ] Document usage in GITEA_TRIGGER.txt

---

## Current CI Timeline

```
check-build-trigger    [====]                              ~1 min
safety-checks          [========================]          ~17 min
                            └─ tests, security audit
build-windows               [========]                     ~5 min
                                 └─ npm, electron-builder
release                              [==]                  ~1 min
                                      └─ upload
───────────────────────────────────────────────────────────
Total                                                      ~22-24 min
```

## Target CI Timeline (with optimizations)

```
check-build-trigger    [====]                              ~1 min
safety-checks          [================]                  ~10 min (optimized)
                            └─ parallel tests, no redundancy
build-windows               [========]                     ~5 min
  └─ smoke-test                  [===]                     ~3 min (NEW)
release                              [==]                  ~1 min
───────────────────────────────────────────────────────────
Total                                                      ~18-20 min
```

---

*Related docs:*
- [SESSION_CONTEXT.md](SESSION_CONTEXT.md) - Current session status
- [docs/build/BUILD_AND_DISTRIBUTION.md](../build/BUILD_AND_DISTRIBUTION.md) - Build process
- [docs/cicd/RUNNER_SERVICE_SETUP.md](../cicd/RUNNER_SERVICE_SETUP.md) - Runner configuration
