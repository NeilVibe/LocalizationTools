# P30: CI/CD Pipeline Optimization

**Created:** 2025-12-15 | **Status:** PLANNING | **Priority:** Medium

---

## Goal

Two objectives:
1. **Add smoke test** - Verify installer actually works
2. **Remove duplicate tests** - Clean up redundant tests that waste CI time

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

## 2. Test Audit - Remove Duplicates

### Current Test Count

| Directory | Tests | In CI? | Status |
|-----------|-------|--------|--------|
| `tests/unit/` | 687 | ✅ Yes | Review needed |
| `tests/integration/` | 169 | ✅ Yes | Review needed |
| `tests/e2e/` | 116 | ⚠️ Partial | Only 3 files run |
| `tests/api/` | 121 | ❌ NO | Not in CI at all |
| `tests/security/` | ~30 | ✅ Yes | Keep |
| `tests/archive/` | ~5 | ❌ No | Already deprecated |
| **Total** | ~1226 | ~912 | |

### Known Issues

#### Issue 1: `tests/api/` (121 tests) NOT in CI
```bash
# Current TEST_DIRS in build.yml:
TEST_DIRS="tests/unit/ tests/integration/ tests/security/ tests/e2e/..."
# No tests/api/ !
```

**Action:** Review each file in `tests/api/` - either add to CI or delete if redundant.

#### Issue 2: E2E - Only 3/8 Files Run

**Running:**
- `test_kr_similar_e2e.py`
- `test_xlstransfer_e2e.py`
- `test_quicksearch_e2e.py`

**NOT Running:**
- `test_full_simulation.py`
- `test_production_workflows_e2e.py`
- `test_complete_user_flow.py`
- `test_real_workflows_e2e.py`
- `test_edge_cases_e2e.py`

**Action:** Review each - add to CI or delete if redundant/deprecated.

---

## 3. Test Review Checklist

### Step 1: Identify Duplicates

Run locally to see test names:
```bash
# List all test functions
grep -r "def test_" tests/ --include="*.py" | sort > /tmp/all_tests.txt

# Find similar names
cat /tmp/all_tests.txt | awk -F'def ' '{print $2}' | sort | uniq -d
```

### Step 2: Review Each Directory

#### `tests/api/` (121 tests) - NOT IN CI
| File | Tests | Keep/Delete | Reason |
|------|-------|-------------|--------|
| `test_api_error_handling.py` | ? | TBD | |
| `test_api_full_system_integration.py` | ? | TBD | Has sleeps |
| `test_api_tools_simulation.py` | ? | TBD | Has sleeps |
| `test_api_websocket.py` | ? | TBD | Has sleeps |
| `test_remote_logging.py` | ? | TBD | Has sleeps |
| ... | | | |

#### `tests/e2e/` (5 files NOT running)
| File | Tests | Keep/Delete | Reason |
|------|-------|-------------|--------|
| `test_full_simulation.py` | ? | TBD | |
| `test_production_workflows_e2e.py` | ? | TBD | |
| `test_complete_user_flow.py` | ? | TBD | |
| `test_real_workflows_e2e.py` | ? | TBD | |
| `test_edge_cases_e2e.py` | ? | TBD | |

#### `tests/unit/` (687 tests)
Run duration analysis:
```bash
python3 -m pytest tests/unit/ --durations=20 --collect-only
```

#### `tests/integration/` (169 tests)
Check for overlap with `tests/api/`:
```bash
diff <(grep "def test_" tests/integration/*.py | sort) \
     <(grep "def test_" tests/api/*.py | sort)
```

---

## 4. Implementation Plan

### Phase 1: Add Smoke Test
- [ ] Add smoke test step to `.gitea/workflows/build.yml`
- [ ] Add smoke test step to `.github/workflows/build-electron.yml`
- [ ] Test on next build

### Phase 2: Test Audit
- [ ] Review `tests/api/` - decide keep or delete for each file
- [ ] Review skipped e2e tests - decide keep or delete
- [ ] Run `--durations=50` to find slow tests
- [ ] Remove confirmed duplicates
- [ ] Update TEST_DIRS if adding tests

### Phase 3: Verify
- [ ] Run full test suite locally
- [ ] Confirm CI passes
- [ ] Document what was removed and why

---

## 5. Files to Review

### `tests/api/` (121 tests - NOT in CI)
```
tests/api/test_api_error_handling.py
tests/api/test_api_full_system_integration.py
tests/api/test_api_tools_simulation.py
tests/api/test_api_websocket.py
tests/api/test_remote_logging.py
```

### `tests/e2e/` (5 files NOT running)
```
tests/e2e/test_full_simulation.py
tests/e2e/test_production_workflows_e2e.py
tests/e2e/test_complete_user_flow.py
tests/e2e/test_real_workflows_e2e.py
tests/e2e/test_edge_cases_e2e.py
```

---

## 6. Current vs Target

**Current:** 17 min safety-checks, no smoke test, unknown duplicates

**Target:**
- Smoke test added (+3 min on Windows build)
- Duplicate tests removed (-? min)
- All valuable tests running
- No wasted CI time on redundant tests

---

*Related docs:*
- [SESSION_CONTEXT.md](SESSION_CONTEXT.md) - Current session status
- [docs/cicd/RUNNER_SERVICE_SETUP.md](../cicd/RUNNER_SERVICE_SETUP.md) - Runner configuration
