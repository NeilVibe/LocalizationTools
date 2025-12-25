# Session Context - Claude Handoff Document

**Last Updated:** 2025-12-25 14:50 | **Build:** v25.1225.1450 | **CI:** Build 871 (WIP)

---

## CURRENT STATE: WINDOWS TESTS IN PROGRESS

| Status | Value |
|--------|-------|
| **Open Issues** | 0 |
| **Tests (Linux)** | 1,399 (7 stages, ~4 min) |
| **Tests (Windows)** | 62 tests written (CI integration WIP) |
| **Coverage** | 47% |
| **CI/CD** | ✅ Linux passing, Windows tests debugging |
| **QA FULL** | DONE (Gitea, 1.2GB) |

### Windows Tests Added (2025-12-25)

| Test File | Count | Categories |
|-----------|-------|------------|
| `test_windows_paths.py` | 15 | AppData, UserProfile, Downloads, Korean, Unicode |
| `test_windows_server.py` | 12 | Server, DB, socket, Python imports |
| `test_windows_encoding.py` | 14 | UTF-8, BOM, Korean filenames, JSON |
| `test_windows_excel.py` | 11 | openpyxl, Korean, large files |
| `test_windows_models.py` | 10 | PKL, FAISS, numpy, cache dirs |
| **TOTAL** | **62** | |

**Location:** `windows_tests/` (outside `tests/` to avoid conftest.py)

### CI Fix History (Builds 852-871)
- **852**: PowerShell `!` syntax error → removed special chars
- **855**: pip stderr as error → `$ErrorActionPreference = 'SilentlyContinue'`
- **858-864**: conftest.py imports failing → moved to `windows_tests/`
- **867**: `--noconftest` doesn't exist → removed invalid option
- **871**: Fixed path with `Join-Path` (current)

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

## WINDOWS PATH TESTS - ✅ IMPLEMENTED

**62 tests written, CI integration in progress.**

### Test Categories Covered

| Category | Tests | Status |
|----------|-------|--------|
| AppData/UserProfile/Downloads | 15 | ✅ Written |
| Server/DB/socket connectivity | 12 | ✅ Written |
| UTF-8/BOM/Korean encoding | 14 | ✅ Written |
| Excel/openpyxl operations | 11 | ✅ Written |
| Models/PKL/FAISS/numpy | 10 | ✅ Written |

### CI Integration Status

| Build | Issue | Fix |
|-------|-------|-----|
| 852-855 | PowerShell syntax | Fixed |
| 858-867 | conftest.py loading | Moved to `windows_tests/` |
| 871 | Path parsing | Using `Join-Path` |

### Key Windows Paths Tested
```
Install:     C:\Program Files\LocaNext\
AppData:     %APPDATA%\LocaNext\
Models:      %APPDATA%\LocaNext\models\
Indexes:     %APPDATA%\LocaNext\indexes\
Downloads:   %USERPROFILE%\Downloads\
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
