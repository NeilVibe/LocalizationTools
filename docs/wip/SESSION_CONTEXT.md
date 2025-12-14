# Session Context - Last Working State

**Updated:** 2025-12-15 ~11:30 KST | **By:** Claude

---

## Current Session: P30 - CI/CD Optimization

**Status: IN PROGRESS** | Reviewing CI test suite for optimization

### Current Task List

| # | Task | Status |
|---|------|--------|
| 1 | Review CI testing phase - find duplicate/redundant tests | IN PROGRESS |
| 2 | Write review results to P30 WIP document | PENDING |
| 3 | Implement thorough smoke test (install, download, autologin, interaction) | PENDING |
| 4 | Trigger build and monitor until success | PENDING |
| 5 | Wait for user validation of new CI suite | PENDING |

### Smoke Test Requirements (When Implemented)

The smoke test must verify:
1. Installation completes successfully (silent install)
2. All dependencies download correctly (including Embedding Model)
3. App launches and backend starts
4. Admin autologin succeeds
5. Main page loads and is responsive
6. Basic interaction works (click buttons, verify responses)
7. **ANY warning or error = FAIL with detailed log**

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
| #263 | v25.1214.2235 | SUCCESS | First good NSIS build |
| #267 | v25.1215.0100 | SUCCESS | Full review + CPU fix |
| NEXT | TBD | PENDING | After CI optimization |

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
