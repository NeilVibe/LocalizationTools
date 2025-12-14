# P30: CI/CD Pipeline Optimization

**Created:** 2025-12-15 | **Status:** PLANNING | **Priority:** Medium

---

## Goal

Two objectives:
1. **Add smoke test** - Verify installer actually works
2. **Curate CI test list** - Decide which tests should run in CI (not delete, just include/exclude)

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

## 2. CI Test Curation

**Goal:** Review each test directory and decide: IN CI or OUT of CI

Tests stay in the repo regardless - this is just about what runs in the pipeline.

### Current CI Configuration

```bash
# From .gitea/workflows/build.yml line 350-351
TEST_DIRS="tests/unit/ tests/integration/ tests/security/ tests/e2e/test_kr_similar_e2e.py tests/e2e/test_xlstransfer_e2e.py tests/e2e/test_quicksearch_e2e.py"

DESELECTS="--deselect=tests/integration/test_tm_real_model.py --deselect=tests/e2e/test_xlstransfer_e2e.py::TestXLSTransferEmbeddings::test_05_model_loads ..."
```

### Current Status

| Directory/File | Tests | In CI? | Decision |
|----------------|-------|--------|----------|
| **tests/unit/** | 687 | ✅ YES | TBD |
| **tests/integration/** | 169 | ✅ YES | TBD |
| **tests/security/** | ~30 | ✅ YES | TBD |
| **tests/e2e/test_kr_similar_e2e.py** | ? | ✅ YES | TBD |
| **tests/e2e/test_xlstransfer_e2e.py** | ? | ✅ YES | TBD |
| **tests/e2e/test_quicksearch_e2e.py** | ? | ✅ YES | TBD |
| **tests/e2e/test_full_simulation.py** | ? | ❌ NO | TBD |
| **tests/e2e/test_production_workflows_e2e.py** | ? | ❌ NO | TBD |
| **tests/e2e/test_complete_user_flow.py** | ? | ❌ NO | TBD |
| **tests/e2e/test_real_workflows_e2e.py** | ? | ❌ NO | TBD |
| **tests/e2e/test_edge_cases_e2e.py** | ? | ❌ NO | TBD |
| **tests/api/** | 121 | ❌ NO | TBD |
| **tests/archive/** | ~5 | ❌ NO | Keep out (deprecated) |

### Review Questions for Each

1. **Does this test add unique value?** Or is it covered by another test?
2. **Is it reliable?** Flaky tests waste CI time
3. **Is it fast enough?** Very slow tests might be better as manual/nightly
4. **Does it need special setup?** (ML models, external services, etc.)

---

## 3. Test Review Session

### To Review: `tests/api/` (121 tests - NOT in CI)

| File | Purpose | IN or OUT? | Reason |
|------|---------|------------|--------|
| `test_api_error_handling.py` | | | |
| `test_api_full_system_integration.py` | | | |
| `test_api_tools_simulation.py` | | | |
| `test_api_websocket.py` | | | |
| `test_remote_logging.py` | | | |

### To Review: `tests/e2e/` (5 files NOT in CI)

| File | Purpose | IN or OUT? | Reason |
|------|---------|------------|--------|
| `test_full_simulation.py` | | | |
| `test_production_workflows_e2e.py` | | | |
| `test_complete_user_flow.py` | | | |
| `test_real_workflows_e2e.py` | | | |
| `test_edge_cases_e2e.py` | | | |

### To Review: Currently IN CI (check for redundancy)

| Directory | Check for |
|-----------|-----------|
| `tests/unit/` | Duplicates, very slow tests |
| `tests/integration/` | Overlap with tests/api/ |
| `tests/security/` | Should all stay in |

---

## 4. Implementation Plan

### Phase 1: Add Smoke Test
- [ ] Add smoke test step to `.gitea/workflows/build.yml`
- [ ] Add smoke test step to `.github/workflows/build-electron.yml`
- [ ] Test on next build

### Phase 2: Test Review Session
- [ ] Review each file in `tests/api/` - decide IN or OUT
- [ ] Review each file in `tests/e2e/` not running - decide IN or OUT
- [ ] Check `tests/unit/` and `tests/integration/` for duplicates
- [ ] Update `TEST_DIRS` in build.yml based on decisions

### Phase 3: Verify
- [ ] Run updated CI
- [ ] Confirm all important tests still run
- [ ] Document final decisions

---

## 5. Final Configuration (After Review)

```bash
# Updated TEST_DIRS (to be filled after review)
TEST_DIRS="tests/unit/ tests/integration/ tests/security/ ..."

# Updated DESELECTS (to be filled after review)
DESELECTS="..."
```

---

*Related docs:*
- [SESSION_CONTEXT.md](SESSION_CONTEXT.md) - Current session status
- [docs/cicd/RUNNER_SERVICE_SETUP.md](../cicd/RUNNER_SERVICE_SETUP.md) - Runner configuration
