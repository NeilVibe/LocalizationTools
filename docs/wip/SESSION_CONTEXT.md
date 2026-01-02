# Session Context

> Last Updated: 2026-01-02 (Session 14 - Auto-Updater Fix)

---

## Current State

**Build:** 436 (v26.102.1001)
**Status:** Auto-updater fully working with Gitea

---

## SESSION 14 UPDATES (2026-01-02)

### Auto-Updater Fixes

| Issue | Root Cause | Fix | Status |
|-------|------------|-----|--------|
| AU-001 Semver leading zeros | `%m%d` format | Changed to `%-m%d` (no leading zero) | ✅ FIXED |
| AU-002 Missing latest tag | No `latest` release for electron-updater | Added step to create `latest` release | ✅ FIXED |
| AU-003 YAML heredoc | PowerShell heredoc broke YAML | Use ConvertTo-Json | ✅ FIXED |
| AU-004 JSON escaping | curl JSON encoding issues | Write to file, use @file | ✅ FIXED |
| AU-005 UTF-8 BOM | PowerShell Out-File adds BOM | Use `[System.IO.File]::WriteAllText()` | ✅ FIXED |
| AU-006 Stupid regex | Parsed version.py when CI had variable | Use `${{ needs.job.outputs.version }}` directly | ✅ FIXED |
| AU-007 Wrong provider | package.json had `github` provider | Changed to `generic` with Gitea URL | ✅ FIXED |

### Files Modified (Session 14)

| File | Change |
|------|--------|
| `locaNext/package.json` | Changed publish provider from `github` to `generic` with Gitea URL |
| `.gitea/workflows/build.yml` | Fixed latest.yml generation, removed regex, use CI version directly |
| `docs/development/CODING_STANDARDS.md` | Added rule 5: "STUPID vs ELEGANT" |
| `CLAUDE.md` | Added rule 14: "STUPID vs ELEGANT" |
| `docs/cicd/TROUBLESHOOTING.md` | Added Gitea API Token + Auto-Updater System sections |
| `docs/cicd/CI_CD_HUB.md` | Added "Release System: 2-Tag Methodology" section |

### Files Created (Session 14)

| File | Purpose |
|------|---------|
| `scripts/release_manager.sh` | Release management (list, cleanup, mock-update, restore) |
| `testing_toolkit/cdp/check_update.js` | Test auto-update connectivity |
| `testing_toolkit/cdp/auto_update_test.js` | Full auto-update debug test |

### Key Learnings (Session 14)

| CS | Issue | Solution |
|----|-------|----------|
| CS-022 | STUPID vs ELEGANT | Don't fix broken complexity - DELETE it. Ask "is this the RIGHT solution?" |
| CS-023 | Auto-updater provider | electron-updater `generic` provider requires URL to directory with `latest.yml` |
| CS-024 | Gitea token location | Stored in `~/.bashrc` as `GITEA_TOKEN` |
| CS-025 | 2-Tag release system | Each build needs versioned (`v26.102.1001`) + `latest` tag for auto-updater fixed URL |

### Cleanup Done (Session 14)

- Deleted 8 old releases (all had broken GitHub auto-updater)
- Only 2 releases remain: `latest` + `v26.102.1001`
- Verified auto-update with mock v99.999.9999 test

### Auto-Update Test Proof

```
Server: v99.999.9999 (mock) vs Installed: v26.102.1001

Result:
├── Connected to Gitea ✓
├── Detected newer version ✓
├── Downloaded 624MB installer ✓
└── Created pending/update-info.json ✓
```

---

## SESSION 13 UPDATES (2026-01-01)

### CI/CD Fixes (Session 13)

| Issue | Root Cause | Fix | Status |
|-------|------------|-----|--------|
| Windows Runner offline | SW lacked admin rights for Windows services | Added `gsudo` to `gitea_control.sh` lines 143, 197-198, 309 | ✅ FIXED |
| GitHub macOS build fail | `--config electron-builder.json` file doesn't exist | Changed to `npx electron-builder --mac --publish never` | ✅ FIXED |
| TM tests failing (500) | `similarity()` requires pg_trgm extension | Added `CREATE EXTENSION pg_trgm` to both CI workflows | ✅ FIXED |

### Files Modified (Session 13)

| File | Change |
|------|--------|
| `scripts/gitea_control.sh` | Added gsudo for Windows service Start/Stop commands |
| `.github/workflows/build-electron.yml` | Fixed macOS build + added pg_trgm extension |
| `.gitea/workflows/build.yml` | Added pg_trgm extension step |

### Key Learnings (Session 13)

| CS | Issue | Solution |
|----|-------|----------|
| CS-019 | SW can't start Windows services | Use gsudo: `$POWERSHELL -Command "gsudo Start-Service..."` |
| CS-020 | electron-builder config | Config lives in `package.json` under "build" key, not separate file |
| CS-021 | TM similarity search | Requires `pg_trgm` PostgreSQL extension in CI database |

### Build Status (Session 13)

| Platform | Build | Status | Notes |
|----------|-------|--------|-------|
| Gitea | 426 | RUNNING | Has all fixes (gsudo, pg_trgm) |
| GitHub | 426 | RUNNING | Missing pg_trgm fix (pushed after trigger) |
| GitHub | 427 | PENDING | Will trigger after 426 fails |

---

## SESSION 12 UPDATES (2026-01-01)

### Bug Fixes (Session 12)

| Bug | Issue | Fix | Status |
|-----|-------|-----|--------|
| CTRL+S not adding to TM | Event destructuring wrong: expected `{row}` but got `{rowId, source, target}` | Fixed destructuring in `GridPage.svelte:152` | ✅ FIXED |
| Double event handler | LDM.svelte still had old `linkedTM` handler | Removed `on:confirmTranslation` from LDM.svelte | ✅ FIXED |
| TM indicator unclear | User wanted "TM ACTIVE:" prefix | Added label prefix in GridPage toolbar | ✅ FIXED |
| Ugly dropdown | Files/TM dropdown looked bad | Replaced with clean segmented tabs | ✅ FIXED |

### UI Changes (Session 12)

| Component | Change |
|-----------|--------|
| TM Indicator | Now shows "TM ACTIVE: [name] (scope: scope_name)" |
| LDM Navigation | Changed from dropdown to clean segmented tabs |
| TM info width | Increased max-width from 350px to 400px |
| **Settings/User Menu** | **UNIFIED** - Single dropdown with user profile, preferences, about, logout |
| **Header Dropdowns** | Replaced ugly Carbon side-panels with compact custom dropdowns |
| **Files/TM Tabs** | Always visible - works from anywhere (Task Manager, other apps) |

### Pending Issues (Session 12)

| Issue | Description | Priority |
|-------|-------------|----------|
| Fast/Deep model selector | No UI to choose TM model type | Medium |
| Threading lag | Heavy processing blocks UI responsiveness | High |

---

## SESSION 11 UPDATES (2026-01-01)

### TM Hierarchy System - COMPLETE

| Sprint | Feature | Status |
|--------|---------|--------|
| Sprint 1 | Database schema (platforms, tm_assignments) | ✅ DONE |
| Sprint 2 | Backend TM resolution (cascade inheritance) | ✅ DONE |
| Sprint 3 | TM Explorer UI (tree view) | ✅ DONE |
| Sprint 4 | File Viewer TM indicator | ✅ DONE |
| Sprint 5 | Platform Management UI | ✅ DONE |

### Key Learnings (CS-017, CS-018)

| CS | Issue | Solution |
|----|-------|----------|
| CS-017 | Bash `$()` gets mangled | Use heredoc `python3 << 'EOF'` + separate commands |
| CS-018 | TM "active" but no scope | Check if assignment has NULL platform_id/project_id/folder_id |

---

## TM System Current State

### FAISS Implementation

| Setting | Value | Notes |
|---------|-------|-------|
| Index Type | HNSW | State-of-the-art nearest neighbor |
| HNSW_M | 32 | Connections per layer |
| efConstruction | 400 | Build accuracy |
| efSearch | 500 | Search accuracy |
| Auto-sync | ✅ ENABLED | Background task on add/update/delete |

### Sync Behavior

| Operation | Sync Type | Speed |
|-----------|-----------|-------|
| ADD entry | Incremental | Fast (vectors appended) |
| UPDATE entry | Full rebuild | Slower |
| DELETE entry | Full rebuild | Slower |

### Auto-Add Flow (CTRL+S Confirm)

```
1. User presses CTRL+S in VirtualGrid
2. VirtualGrid.confirmInlineEdit() dispatches {rowId, source, target}
3. GridPage.handleConfirmTranslation() receives event
4. If activeTMs.length > 0:
   - POST to /api/ldm/tm/{tm_id}/entries (FormData)
   - Backend auto-syncs via _auto_sync_tm_indexes()
   - Entry embedded + added to FAISS incrementally
```

---

## Key Files

### TM Hierarchy

| File | Purpose |
|------|---------|
| `server/tools/ldm/routes/tm_assignment.py` | TM assignment & activation |
| `server/tools/ldm/routes/tm_entries.py` | TM entry CRUD with auto-sync |
| `server/tools/ldm/indexing/sync_manager.py` | PKL/FAISS sync logic |
| `server/tools/shared/faiss_manager.py` | Centralized FAISS operations |

### Frontend

| File | Purpose |
|------|---------|
| `src/lib/components/pages/GridPage.svelte` | File viewer with TM indicator + auto-add |
| `src/lib/components/ldm/VirtualGrid.svelte` | Grid with TM matching |
| `src/routes/+layout.svelte` | App layout with LDM tabs |

---

## Next Steps

1. **FULL CODE REVIEW** - Review Cycle 2 (PRIORITY)
2. Add Fast/Deep model selector in TM menu
3. Fix threading/responsiveness during heavy processing

---

## Code Review Cycle 2 (2026-01-01)

**Issue File:** `docs/code-review/ISSUES_20260101.md`
**Protocol:** `docs/code-review/CODE_REVIEW_PROTOCOL.md`
**Last Review:** 2025-12-12 to 2025-12-13 (~2.5 weeks ago)

### Review Progress

| Session | Module | Status |
|---------|--------|--------|
| Quick Scan | Automated scans | PENDING |
| 1 | Database & Models | PENDING |
| 2 | Utils & Core | PENDING |
| 3 | Auth & Security | PENDING |
| 4 | LDM Backend | PENDING |
| 5 | XLSTransfer | PENDING |
| 6 | QuickSearch | PENDING |
| 7 | KR Similar | PENDING |
| 8 | API Layer | PENDING |
| 9 | Frontend - Core | PENDING |
| 10 | Frontend - LDM | PENDING |
| 11 | Admin Dashboard | PENDING |
| 12 | Scripts & Config | PENDING |
| 13 | CI/CD Workflows | PENDING |
| 13B | CI/CD Infrastructure | PENDING |
| 14 | Tests | PENDING |
| 15 | Electron/Desktop | PENDING |
| 16 | Installer | PENDING |

### Key Rules (REMEMBER!)

1. **REVIEW ALL FIRST, FIX LATER** - Document issues, don't fix during review
2. **FIX EVERYTHING. NO EXCUSES. NO DEFER.**
3. One issue file for entire review cycle
4. Pass 2 = Full re-review after fixes

---

## Quick Commands

```bash
# DEV servers
./scripts/start_all_servers.sh --with-vite

# Check TM assignment in DB
python3 << 'EOF'
import sys
sys.path.insert(0, '/home/neil1988/LocalizationTools/server')
from sqlalchemy import create_engine, text
from config import DATABASE_URL
engine = create_engine(DATABASE_URL)
with engine.connect() as conn:
    result = conn.execute(text("SELECT * FROM ldm_tm_assignments WHERE is_active = true"))
    for r in result.fetchall():
        print(r)
EOF

# Test TM hierarchy
node testing_toolkit/dev_tests/test_clean_hierarchy.mjs
```

---

*Session 12 - UI polish + Confirm-to-TM fix*
