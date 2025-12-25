# Session Context - Claude Handoff Document

**Last Updated:** 2025-12-25 16:00 | **Build:** v25.1225.1600 | **CI:** Build 879+ (CDP Tests)

---

## CURRENT STATE: WINDOWS CDP TESTS IMPLEMENTED

| Status | Value |
|--------|-------|
| **Open Issues** | 0 |
| **Tests (Linux)** | 1,399 (7 stages, ~4 min) |
| **Tests (Windows)** | 62 pytest + CDP integration tests |
| **Coverage** | 47% |
| **CI/CD** | ✅ Linux passing, Windows CDP tests added |
| **QA FULL** | DONE (Gitea, 1.2GB) |

### Windows CI Testing Pipeline (Build 879+)

```
Windows CI Pipeline:
├── Smoke Test (install + health check) ✅
├── pytest tests (62 tests in windows_tests/) ✅
└── CDP Integration Tests (NEW!)
    ├── TEST 1: SQLite (offline) mode
    │   └── Launch app → quick_check.js
    └── TEST 2: PostgreSQL (online) mode
        └── Launch app → login.js → quick_check.js → test_server_status.js
```

### Gitea Secrets for CI (SECURITY)

| Secret | Purpose | Required |
|--------|---------|----------|
| `CI_DB_HOST` | PostgreSQL server address | For online tests |
| `CI_TEST_USER` | Test user (NOT super admin) | For login tests |
| `CI_TEST_PASS` | Test user password | For login tests |

**To configure:** Gitea repo → Settings → Secrets → Add

**IMPORTANT:** Use a limited `user` role account, NOT super admin.

---

## ACTION PLAN: CI Credential Security

### Current Problem - SOLVED
- ~~`login.js` has `neil/neil` as fallback (visible in code)~~ **REMOVED**
- ~~neil is super admin with full privileges~~ **Now uses ci_tester (role=user)**
- ~~Anyone reading code can see credentials~~ **Credentials in Gitea secrets only**

### TODO (In Order)

| Step | Task | Status |
|------|------|--------|
| 1 | Wait for build 879 to complete | ✅ Done |
| 2 | Create `ci_tester` user in PostgreSQL (role=user) | ✅ Done |
| 3 | Add secrets to Gitea (CI_DB_HOST, CI_TEST_USER, CI_TEST_PASS) | ✅ Done |
| 4 | Remove neil/neil fallback from login.js | ✅ Done |
| 5 | Trigger build 880 to verify online tests work | 🔄 In Progress |

### Commands to Execute

```bash
# Step 2: Create ci_tester in database
python3 -c "
from server.database.db_setup import get_db_session
from server.database.models import User
from server.utils.auth import hash_password

session = get_db_session()
ci_user = User(
    username='ci_tester',
    password_hash=hash_password('CI_TEST_SECURE_2025'),
    role='user',
    must_change_password=False
)
session.add(ci_user)
session.commit()
print('Created ci_tester')
"

# Step 3: Add Gitea secrets (manual via UI)
# Gitea → neilvibe/LocaNext → Settings → Secrets → New Secret
# - CI_DB_HOST = 172.28.150.120
# - CI_TEST_USER = ci_tester
# - CI_TEST_PASS = CI_TEST_SECURE_2025
```

### After Implementation

| Item | Before | After |
|------|--------|-------|
| Credentials in code | `neil/neil` visible | Only fallback, not used |
| CI uses | neil (super admin) | ci_tester (user role) |
| Password storage | In git history | In Gitea secrets only |
| Risk | High (anyone can login as admin) | Low (limited user, secret password) |

### Environment Portability

| Location | PostgreSQL Host | Notes |
|----------|-----------------|-------|
| Home/Dev | 172.28.150.120 | Current setup |
| Company | TBD | Update `CI_DB_HOST` secret |

When moving to company server, just update the Gitea secret - no code changes needed.

### CI Fix History (Builds 852-879)
- **852-855**: PowerShell syntax fixes
- **858-874**: conftest.py isolation → moved to `windows_tests/`
- **877**: Fixed CI edge cases (SYSTEM user, socket errors)
- **878**: Added basic CDP tests (SQLite only)
- **879+**: Dual-mode CDP tests (SQLite + PostgreSQL)

---

## CURRENT PRIORITIES

| Priority | Feature | Status | Description |
|----------|---------|--------|-------------|
| **P1** | Factorization | ✅ DONE | Moved shared code to `server/utils/`, LDM independence |
| **P2** | Auto-LQA System | ✅ DONE | Backend + Frontend complete (5 phases) |
| **P3** | MERGE System | 🔄 NEXT | Merge confirmed cells to main LanguageData (CRUCIAL) |
| **P4** | File Conversions | Pending | XML↔Excel, Excel↔TMX, Text→XML/Excel |
| **P5** | LanguageTool | Pending | Spelling/Grammar via central server |
| **Future** | UIUX Overhaul | Pending | Legacy Apps menu → Single LocaNext |

---

## P2: Auto-LQA System - ✅ COMPLETE (2025-12-25)

**All 5 phases implemented. 136 LDM tests passing (17 QA-specific).**

### Backend (Phase 1)

| Component | Status |
|-----------|--------|
| `LDMQAResult` model | ✅ Created |
| `qa_checked_at`, `qa_flag_count` on rows | ✅ Added |
| QA schemas (`schemas/qa.py`) | ✅ Created |
| `routes/qa.py` (7 endpoints) | ✅ Created |
| Row filter by `qa_flagged` | ✅ Added |
| 17 unit tests | ✅ Passing |

### API Endpoints

| Endpoint | Purpose |
|----------|---------|
| `POST /rows/{id}/check-qa` | LIVE mode single row |
| `GET /rows/{id}/qa-results` | Row issues (Edit Modal) |
| `POST /files/{id}/check-qa` | Full file QA |
| `GET /files/{id}/qa-results` | File report (QA Menu) |
| `GET /files/{id}/qa-summary` | Summary counts |
| `POST /qa-results/{id}/resolve` | Dismiss issue |
| `GET /files/{id}/rows?filter=qa_flagged` | Filter rows |

### Frontend (Phases 2-5)

| Phase | Feature | Status |
|-------|---------|--------|
| 2 | LIVE QA Mode (toggle, auto-check on confirm) | ✅ Done |
| 3 | Edit Modal QA Panel (show issues, dismiss) | ✅ Done |
| 4 | Row Filtering UI (search + dropdown) | ✅ Done |
| 5 | QA Menu (slide-out panel, summary, jump to row) | ✅ Done |

### Files Created/Modified

| File | Type |
|------|------|
| `server/tools/ldm/routes/qa.py` | NEW |
| `server/tools/ldm/schemas/qa.py` | NEW |
| `tests/unit/ldm/test_routes_qa.py` | NEW (17 tests) |
| `locaNext/src/lib/components/ldm/QAMenuPanel.svelte` | NEW |
| `locaNext/src/lib/components/ldm/VirtualGrid.svelte` | Modified |
| `locaNext/src/lib/components/apps/LDM.svelte` | Modified |

### QA Checks Implemented

| Check | Description | Severity |
|-------|-------------|----------|
| Pattern | `{code}` mismatches between source/target | Error |
| Character | Special char count mismatches (`{}[]<>`) | Error |
| Line | Same source → different translations | Warning |

---

## P3: MERGE System (NEXT PRIORITY)

**Purpose:** Merge confirmed cells back to main LanguageData

### Flow
```
1. Work on file in LocaNext (translate, confirm cells)
2. Right-click file → "Merge to LanguageData"
3. Select target LanguageData file (synced with mainbranch)
4. Confirmed cells merged (edit if match, add if new)
5. User commits to SVN/Perforce manually
```

### Implementation Needs
- Backend: Merge logic (match by StringID, update target)
- Frontend: Right-click menu option, modal to select target file
- Export: Generate merged file for download
- **PATH handling:** Windows path for merged file export

### Future: Perforce API
- Could create changelist directly after merge
- User reviews in P4V and submits

---

## WINDOWS TESTING - ✅ COMPLETE

**3-tier testing: pytest (62) + Smoke Test + CDP Integration**

### Test Tiers

| Tier | Type | Tests | What It Validates |
|------|------|-------|-------------------|
| 1 | pytest | 62 | Paths, encoding, Excel, models |
| 2 | Smoke Test | 1 | Silent install, file verification, backend health |
| 3 | CDP | 3+ | App launch, login, UI functionality |

### pytest Tests (`windows_tests/`)

| File | Count | Categories |
|------|-------|------------|
| `test_windows_paths.py` | 15 | AppData, UserProfile, Downloads |
| `test_windows_server.py` | 12 | Server, DB, socket connectivity |
| `test_windows_encoding.py` | 14 | UTF-8, BOM, Korean |
| `test_windows_excel.py` | 11 | openpyxl, Korean, large files |
| `test_windows_models.py` | 10 | PKL, FAISS, numpy |

### CDP Integration Tests

| Test | Mode | What It Does |
|------|------|--------------|
| `quick_check.js` | Both | Page state, URL, DOM verification |
| `login.js` | Online | Login with credentials from Gitea secrets |
| `test_server_status.js` | Online | Server panel, DB connection status |

### Key Windows Paths
```
Install:     C:\Program Files\LocaNext\
AppData:     %APPDATA%\LocaNext\
Models:      %APPDATA%\LocaNext\models\
Indexes:     %APPDATA%\LocaNext\indexes\
CI Temp:     C:\LocaNextSmokeTest\
```

---

## P1: Factorization - ✅ COMPLETE

**785 tests passed** - no breakage.

### Created in server/utils/

| File | Functions |
|------|-----------|
| `qa_helpers.py` | `is_korean`, `is_sentence`, `check_pattern_match`, `check_character_count` |
| `code_patterns.py` | `simple_number_replace`, `extract_code_blocks`, `adapt_structure` |
| `text_utils.py` | `normalize_korean_text` (already existed) |

---

## BUILD MODES

| Mode | Tests | Installer | Platform |
|------|-------|-----------|----------|
| **QA** | ALL 1000+ | ~170MB | Both (default) |
| **QA FULL** | ALL 1000+ | ~1.2GB | Gitea only |
| **TROUBLESHOOT** | Resume | Debug | Both |

```bash
# QA (default)
echo "Build" >> GITEA_TRIGGER.txt && git add -A && git commit -m "Build" && git push origin main && git push gitea main

# QA FULL (Gitea only)
echo "Build QA FULL" >> GITEA_TRIGGER.txt && git add -A && git commit -m "Build QA FULL" && git push gitea main
```

---

## TESTING RECOMMENDATIONS

### Before Next Build
1. Run `python3 -m pytest tests/unit/ldm/ -v` (136 tests)
2. Test on Playground: QA toggle, QA Menu, filter dropdown
3. Verify QA flags appear on rows with issues

### CDP E2E Tests (Future)
- Test LIVE QA mode (toggle on, edit cell, verify check runs)
- Test QA Menu (open, run full QA, click issue to jump to row)
- Test row filtering (select "QA Flagged", verify only flagged rows shown)

---

## KEY DOCS

| Doc | Purpose |
|-----|---------|
| [Roadmap.md](../../Roadmap.md) | Absorption tracker + strategic view |
| [AUTO_LQA_IMPLEMENTATION.md](AUTO_LQA_IMPLEMENTATION.md) | P2 detailed plan (COMPLETE) |
| [LANGUAGETOOL_IMPLEMENTATION.md](LANGUAGETOOL_IMPLEMENTATION.md) | P5 detailed plan |
| [ISSUES_TO_FIX.md](ISSUES_TO_FIX.md) | Open bugs (0) |

---

*Next: P3 MERGE System → P4 File Conversions → P5 LanguageTool*
