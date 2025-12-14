# P30: CI/CD Pipeline Optimization

**Created:** 2025-12-15 | **Status:** PLANNING | **Priority:** Medium

---

## Goal

1. **Review the 912 tests IN CI** - Find and remove redundant/duplicate tests
2. **Add smoke test** - Verify installer actually works

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

---

## 2. Test Audit - Review 912 Tests IN CI

### Current CI Configuration

```bash
# From .gitea/workflows/build.yml line 350-351
TEST_DIRS="tests/unit/ tests/integration/ tests/security/ tests/e2e/test_kr_similar_e2e.py tests/e2e/test_xlstransfer_e2e.py tests/e2e/test_quicksearch_e2e.py"
```

### Tests Currently IN CI

| Directory | Tests | Time? | Review Status |
|-----------|-------|-------|---------------|
| `tests/unit/` | 687 | ? | TODO |
| `tests/integration/` | 169 | ? | TODO |
| `tests/security/` | ~30 | ? | TODO |
| `tests/e2e/test_kr_similar_e2e.py` | ? | ? | TODO |
| `tests/e2e/test_xlstransfer_e2e.py` | ? | ? | TODO |
| `tests/e2e/test_quicksearch_e2e.py` | ? | ? | TODO |
| **Total** | ~912 | 17 min | |

### Review Questions

For each test file/directory:
1. **Is it redundant?** Same thing tested elsewhere?
2. **Is it a duplicate?** Nearly identical test exists?
3. **Is it slow?** Takes too long for the value it adds?
4. **Is it unique?** Tests something nothing else tests?

### Tests NOT in CI (excluded for a reason)

These are already excluded - probably duplicates or require special setup:
- `tests/api/` (121 tests) - likely duplicates of integration tests
- `tests/e2e/` other files - likely covered by the 3 files that run
- `tests/archive/` - deprecated

---

## 3. Review Session Plan

### Step 1: Get test durations
```bash
python3 -m pytest tests/unit/ tests/integration/ tests/security/ --durations=50 -v 2>&1 | tail -100
```

### Step 2: Review each directory

#### `tests/unit/` (687 tests)
| File | Tests | Keep in CI? | Reason |
|------|-------|-------------|--------|
| TODO | | | |

#### `tests/integration/` (169 tests)
| File | Tests | Keep in CI? | Reason |
|------|-------|-------------|--------|
| TODO | | | |

#### `tests/security/` (~30 tests)
| File | Tests | Keep in CI? | Reason |
|------|-------|-------------|--------|
| TODO | | | |

#### `tests/e2e/` (3 files in CI)
| File | Tests | Keep in CI? | Reason |
|------|-------|-------------|--------|
| TODO | | | |

---

## 4. Implementation Plan

### Phase 1: Add Smoke Test
- [ ] Add smoke test step to `.gitea/workflows/build.yml`
- [ ] Add smoke test step to `.github/workflows/build-electron.yml`

### Phase 2: Test Audit
- [ ] Run `--durations=50` to identify slow tests
- [ ] Review `tests/unit/` for redundancy
- [ ] Review `tests/integration/` for redundancy
- [ ] Review `tests/security/` for redundancy
- [ ] Review e2e tests for redundancy
- [ ] Update `TEST_DIRS` or `DESELECTS` based on findings

### Phase 3: Verify
- [ ] Run updated CI
- [ ] Confirm coverage is still good
- [ ] Document what was removed and why

---

## 5. Final Results (After Review)

**Before:** 912 tests, 17 min

**After:** ? tests, ? min

**Removed from CI:**
| Test | Reason |
|------|--------|
| TBD | |

---

*Related docs:*
- [SESSION_CONTEXT.md](SESSION_CONTEXT.md) - Current session status
