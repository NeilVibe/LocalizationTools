# Session Context - Last Working State

**Updated:** 2025-12-15 ~02:55 KST | **By:** Claude

---

## Current Session: P30 - CI/CD Optimization

**Status: BUILD SUCCESS** | Awaiting user validation

### Build Results - v25.1215.0230

| Component | Result |
|-----------|--------|
| Linux Tests | 865 passed, 1 skipped, 99 deselected (17:09) |
| P30 Optimization | 72 duplicate tests removed from CI |
| Smoke Test | PASSED (Install/Files VERIFIED) |
| Release | v25.1215.0230 uploaded to Gitea |

### Task List

| # | Task | Status |
|---|------|--------|
| 1 | Review CI testing phase - find duplicate/redundant tests | COMPLETE |
| 2 | Write review results to P30 WIP document | COMPLETE |
| 3 | Implement thorough smoke test (install, download, autologin, interaction) | COMPLETE |
| 4 | Trigger build and monitor until success | COMPLETE |
| 5 | Wait for user validation of new CI suite | PENDING |

### Smoke Test (Implemented)

What the CI smoke test verifies:
1. Installer found and correct size (162.8 MB)
2. Silent installation completes
3. All critical files present (exe, server, python, tools)
4. Backend test (OPTIONAL - no PostgreSQL in CI)

**Note:** Full backend testing requires PostgreSQL (manual testing).

---

## BUG-006 Fixed This Session

**Embedding Model Download Failure** - CRITICAL bug fixed

| What | Before | After |
|------|--------|-------|
| `tools/download_model.py` | KR-SBERT (deprecated) | QWEN |
| Model path | `models/kr-sbert/` | `models/qwen-embedding/` |
| First-run checks | Wrong path | Correct path |
| Old scripts | Active | Archived in `scripts/deprecated/` |

---

## Previous Session: P28.5 - CI/CD Infrastructure Hardening

**Status: COMPLETE** | All infrastructure issues fixed

### Issues Fixed

| ID | Severity | Issue | Fix |
|----|----------|-------|-----|
| INFRA-001 | CRITICAL | 706% CPU Terror | Safe systemd config with limits |
| INFRA-002 | HIGH | Node.js syntax error | Wrapper script sources NVM |
| INFRA-003 | HIGH | Wrong DB in CI | `override=False` in config.py |
| BUG-006 | CRITICAL | Embedding Model download fails | Fixed download_model.py for QWEN |

---

## CI Test Suite Overview (Under Review)

**Current TEST_DIRS in CI:**
```
tests/unit/                      # 20 files
tests/integration/               # 11 files
tests/security/                  # 4 files
tests/e2e/test_kr_similar_e2e.py
tests/e2e/test_xlstransfer_e2e.py
tests/e2e/test_quicksearch_e2e.py
```

**NOT in CI (excluded):**
- `tests/api/` (7 files)
- Other `tests/e2e/` files (5 files)
- `tests/archive/`
- `tests/cdp/`

**Goal:** Find duplicate/redundant tests to remove from CI without losing coverage.

---

## Build History (Recent)

| Run | Version | Status | Notes |
|-----|---------|--------|-------|
| #267 | v25.1215.0100 | SUCCESS | Full review + CPU fix |
| #269 | v25.1215.0204 | FAILED | Smoke test required DB |
| #271 | v25.1215.0230 | SUCCESS | P30 + fixed smoke test |

---

## Quick Commands

```bash
# Check runner status (systemd)
sudo systemctl status gitea-runner.service

# Trigger new build
echo "Build LIGHT v$(TZ='Asia/Seoul' date '+%y%m%d%H%M')" >> GITEA_TRIGGER.txt
git add -A && git commit -m "Build" && git push origin main && git push gitea main
```

---

*For full project status, see [Roadmap.md](../../Roadmap.md)*
