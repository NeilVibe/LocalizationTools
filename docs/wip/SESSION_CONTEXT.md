# Session Context - Last Working State

**Updated:** 2025-12-16 22:45 KST | **Build:** 283 ✅ ALL PASSED

---

## CURRENT STATUS: ALL GREEN - UNIFIED CI COMPLETE

Build 283 passed on both GitHub and Gitea with unified test configuration.
Both online (PostgreSQL) and offline (SQLite + auto-login) modes verified.

---

## Build 283 Results

| Platform | Database | Tests | Status |
|----------|----------|-------|--------|
| GitHub Linux | PostgreSQL | 255 | ✅ PASSED |
| Gitea Linux | PostgreSQL | 255 | ✅ PASSED |
| GitHub Windows | SQLite | Smoke | ✅ PASSED |
| Gitea Windows | SQLite | Smoke | ✅ PASSED |

---

## What Was Done This Session

### 1. CI Unification (Build 283)
- **Problem:** GitHub and Gitea had different test configs
- **Fix:** Both now run identical ~255 tests
- **Files:** `.gitea/workflows/build.yml`, `.github/workflows/build-electron.yml`

**Unified Test Suite:**
```
tests/unit/                          # All unit tests
tests/integration/                   # All integration tests
tests/security/                      # All security tests
tests/e2e/test_kr_similar_e2e.py     # KR Similar workflow
tests/e2e/test_xlstransfer_e2e.py    # XLSTransfer workflow
tests/e2e/test_quicksearch_e2e.py    # QuickSearch workflow
tests/e2e/test_full_simulation.py    # Full system simulation

DESELECTED (require 2GB model):
- test_tm_real_model.py
- 5 embedding-dependent tests in xlstransfer
```

### 2. Previous Session: P32 + P33 (Build 282)
- Smoke test IPv4/IPv6 fix (localhost → 127.0.0.1)
- 9/11 code review issues fixed in `server/tools/ldm/api.py`

---

## Priority Status

| Priority | Status | What |
|----------|--------|------|
| CI | ✅ DONE | Unified GitHub + Gitea (255 tests) |
| P33 | ✅ DONE | Offline Mode + Auto-Login |
| P32 | ✅ DONE | Code Review (9/11 fixed) |
| **P25** | 🔴 NEXT | LDM UX (85%) - TM matching, QA checks |

---

## Offline Auto-Login Flow (P33)

```
SQLite Mode Startup
       ↓
db_setup.py creates LOCAL admin user (server/database/db_setup.py:422-437)
       ↓
Frontend calls /health endpoint
       ↓
Backend returns auto_token (server/main.py:361-366)
       ↓
Frontend uses auto_token → NO LOGIN SCREEN
```

---

## CI/CD Quick Reference

### Both use same test suite now:
```bash
# GitHub
echo "Build LIGHT v$(date '+%y%m%d%H%M')" >> BUILD_TRIGGER.txt
git push origin main

# Gitea
echo "Build LIGHT v$(date '+%y%m%d%H%M')" >> GITEA_TRIGGER.txt
git push gitea main

# Check GitHub
gh run list --limit 3

# Check Gitea
curl -s "http://localhost:3000/neilvibe/LocaNext/actions/runs/283" | grep -oP '(success|failure)'
```

---

## Next Session Checklist

1. `./scripts/check_servers.sh`
2. Check [Roadmap.md](../../Roadmap.md) - P25 is next
3. **P25 (LDM UX)** tasks:
   - TM matching (Qwen + FAISS 5-tier)
   - QA checks (Word Check, Line Check)
   - Custom file pickers
4. See [P25_LDM_UX_OVERHAUL.md](P25_LDM_UX_OVERHAUL.md) for details

---

*For global priorities: [Roadmap.md](../../Roadmap.md)*
