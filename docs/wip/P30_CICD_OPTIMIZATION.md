# P30: CI/CD Pipeline Optimization

**Created:** 2025-12-15 | **Status:** PLANNING | **Priority:** Medium

---

## Goal

1. **Review all tests running in CI** - Find and remove redundant/duplicate tests from CI
2. **Add smoke test** - Verify installer actually works

---

## 1. Test Audit - Review All Tests IN CI

### What runs in CI (from build.yml line 350-351)

```bash
TEST_DIRS="tests/unit/ tests/integration/ tests/security/ tests/e2e/test_kr_similar_e2e.py tests/e2e/test_xlstransfer_e2e.py tests/e2e/test_quicksearch_e2e.py"
```

### Task: Review Each Test File

**For each test file that runs in CI:**
1. Read the test file
2. Note what it tests (which functions/endpoints/features)
3. Check if another test already covers the same thing
4. Decide: KEEP in CI or REMOVE from CI

### Criteria for REMOVE from CI

- **Duplicate:** Another test tests the exact same thing
- **Redundant:** Covered by a more comprehensive test
- **Slow + Low Value:** Takes long time, doesn't catch unique bugs

### Criteria for KEEP in CI

- **Unique coverage:** Tests something no other test covers
- **Critical path:** Tests core functionality that must work
- **Fast:** Runs quickly, no reason to remove

---

## 2. Test Files to Review

### `tests/unit/` (687 tests)

| File | What it tests | Duplicate of? | Decision |
|------|---------------|---------------|----------|
| | | | |

### `tests/integration/` (169 tests)

| File | What it tests | Duplicate of? | Decision |
|------|---------------|---------------|----------|
| | | | |

### `tests/security/` (~30 tests)

| File | What it tests | Duplicate of? | Decision |
|------|---------------|---------------|----------|
| | | | |

### `tests/e2e/` (3 files in CI)

| File | What it tests | Duplicate of? | Decision |
|------|---------------|---------------|----------|
| test_kr_similar_e2e.py | | | |
| test_xlstransfer_e2e.py | | | |
| test_quicksearch_e2e.py | | | |

---

## 3. Smoke Test

Add post-install verification to `build-windows` job:

```yaml
- name: Smoke Test - Install and Verify
  shell: pwsh
  run: |
    $installer = Get-ChildItem "installer_output\*Setup*.exe" | Select-Object -First 1

    # 1. Silent install
    Start-Process -FilePath $installer.FullName -Args '/S /D=C:\LocaNextTest' -Wait

    # 2. Check files exist
    $checks = @(
      'C:\LocaNextTest\LocaNext.exe',
      'C:\LocaNextTest\resources\server\main.py',
      'C:\LocaNextTest\resources\tools\python\python.exe'
    )
    foreach ($path in $checks) {
      if (!(Test-Path $path)) { exit 1 }
    }

    # 3. Launch and check health
    $process = Start-Process 'C:\LocaNextTest\LocaNext.exe' -PassThru
    for ($i = 0; $i -lt 30; $i++) {
      Start-Sleep -Seconds 2
      try {
        $r = Invoke-WebRequest -Uri 'http://localhost:8888/health' -TimeoutSec 5
        if ($r.StatusCode -eq 200) {
          Stop-Process -Id $process.Id -Force
          Write-Host "SMOKE TEST PASSED"
          exit 0
        }
      } catch { }
    }
    Stop-Process -Id $process.Id -Force
    exit 1
```

---

## 4. Final Results (After Review)

**Before:** 912 tests, 17 min

**After:** ? tests, ? min

**Removed from CI:**

| Test | Reason |
|------|--------|
| | |

---

## 5. Implementation

- [ ] Review `tests/unit/` - fill in table above
- [ ] Review `tests/integration/` - fill in table above
- [ ] Review `tests/security/` - fill in table above
- [ ] Review `tests/e2e/` - fill in table above
- [ ] Update `TEST_DIRS` or `DESELECTS` in build.yml
- [ ] Add smoke test to build.yml
- [ ] Test updated CI
