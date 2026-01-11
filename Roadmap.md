# LocaNext - Roadmap

> Strategic priorities and architecture. Fast-moving session info in [SESSION_CONTEXT.md](docs/wip/SESSION_CONTEXT.md).

---

## Component Status

| Component | Status |
|-----------|--------|
| LDM (Language Data Manager) | WORKS |
| XLS Transfer | WORKS |
| Quick Search | WORKS (KEEP - unique dictionary features) |
| KR Similar | WORKS (KEEP - unique FAISS similarity) |
| CI/CD (Gitea + GitHub) | WORKS |

---

## COMPLETED: UI Overhaul (Session 9) ✅

**Status:** COMPLETE | **Issues:** UI-094 to UI-097 + UI-087

All UI cleanup tasks completed:
- UI-087: Dropdown position → ✅ FIXED
- UI-094: Remove TM button → ✅ FIXED
- UI-095: Remove QA buttons → ✅ FIXED
- UI-096: Reference file picker → ✅ FIXED
- UI-097: Consolidate Settings → ✅ FIXED

---

## COMPLETED: EXPLORER Features (Sessions 21-24) ✅

**Status:** COMPLETE | **Build:** 448

Windows-style file management:
- EXPLORER-001: Ctrl+C/V/X clipboard → ✅ FIXED
- EXPLORER-002: Hierarchy validation → ✅ FIXED
- EXPLORER-003/006: Confirmation modals → ✅ FIXED
- EXPLORER-004: Explorer search like "Everything" → ✅ FIXED
- EXPLORER-005: Cross-project move → ✅ FIXED
- EXPLORER-007: Undo/Redo (Ctrl+Z/Y) → ✅ FIXED
- EXPLORER-008: Recycle Bin (soft delete) → ✅ FIXED
- EXPLORER-009: Privileged operations → ✅ FIXED (Session 24)

---

## COMPLETED: EXPLORER-009 Privileged Operations ✅

**Status:** COMPLETE (Session 24) | **Priority:** LOW (enterprise feature)

Implemented capability system:
- `delete_platform`: Required for platform deletion
- `delete_project`: Required for project deletion
- `cross_project_move`: Required for cross-project moves
- `empty_trash`: Required for emptying recycle bin

Admin endpoints at `/api/ldm/admin/capabilities/*` for grant management.
Admins always have all capabilities automatically.

---

## MAJOR FEATURE: TM Hierarchy System

**Status:** PLANNED | **Priority:** HIGH | **Doc:** `docs/wip/TM_HIERARCHY_PLAN.md`

### Core Concept

```
File Explorer (structure owner)     TM Explorer (READ-ONLY mirror)
├── Platform: PC                    ├── [Unassigned] ← TM-only
│   └── Project: Game1              ├── Platform: PC
│       └── Folder: French          │   └── Project: Game1
│           └── file.txt            │       └── Folder: French
│                                   │           └── french.tm [ACTIVE]
```

### Key Rules

1. **TM Explorer = READ-ONLY mirror** of File Explorer structure
2. **You NEVER create folders in TM Explorer** - only place/activate TMs
3. **Unassigned exists ONLY in TM Explorer** - safety net for orphaned TMs
4. **Hierarchical activation** - TM at folder level applies to all files in folder

### Implementation (5 Sprints)

1. Database: platforms table, tm_assignments
2. Backend: TM resolution logic (cascade inheritance)
3. ✅ **Frontend: TM Explorer GRID UI** - DONE (Session 37)
4. Frontend: File viewer TM indicator
5. Frontend: Platform management

### UI-108: COMPLETE ✅

TM page now uses Windows Explorer grid style:
- Grid rows with columns (Name, Entries, Status, Type)
- Breadcrumb navigation (Home > Platform > Project)
- Double-click to enter Platform/Project
- Right-click custom context menu
- Drag-drop TM reassignment
- Multi-select support

---

## MAJOR FEATURE: Offline/Online Sync System

**Status:** ✅ COMPLETE | **Priority:** HIGH | **Doc:** `docs/wip/OFFLINE_ONLINE_MODE.md`

Manual on-demand synchronization between Online (PostgreSQL) and Offline (SQLite) modes.

### Core Concept

```
┌─────────────────┐                     ┌─────────────────┐
│   ONLINE MODE   │  ◄── Manual Sync ──►│  OFFLINE MODE   │
│   PostgreSQL    │                     │     SQLite      │
│   (Central)     │                     │     (Local)     │
└─────────────────┘                     └─────────────────┘
        │                                       │
        └───────── Same UI, Different DB ───────┘
```

### Key Features

| Feature | Description |
|---------|-------------|
| **Mode Toggle** | Switch between Online/Offline in UI |
| **Sync to Offline** | Right-click file → download to SQLite |
| **Sync to Online** | Right-click file → upload to PostgreSQL |
| **Merge** | Combine changes from both directions |
| **Fully Offline** | Use LocaNext without any server connection |

### Implementation Phases

| Phase | Scope | Status |
|-------|-------|--------|
| Phase 1 | Mode toggle + basic file sync | PLANNED |
| Phase 2 | Folder sync with progress | PLANNED |
| Phase 3 | Smart merge + conflict resolution | PLANNED |
| Phase 4 | TM sync between modes | PLANNED |

### Use Cases

1. **Field Translator** - Download files, work offline, sync back
2. **Solo User** - Use offline-only, no server needed
3. **Team Collaboration** - Central server + individual offline work

See full specification: `docs/wip/OFFLINE_ONLINE_SYNC.md`

---

## CI/CD Build Modes

### Strategy (2025-12-23)

**DEV mode is DEAD.** Workers technology made full test suite so fast that we now run ALL 1000+ tests on every build. No more skipping tests.

| What Changed | Before | After |
|--------------|--------|-------|
| **Default mode** | DEV (skip tests) | QA (all tests) |
| **Test time** | "Too slow" | Fast (workers) |
| **Modes** | DEV, QA, TROUBLESHOOT | QA, QA FULL, TROUBLESHOOT |

### Build Modes

| Mode | Tests | Installer | Platform |
|------|-------|-----------|----------|
| `QA` | **ALL 1000+** | ~150MB | Both (default) |
| `QA FULL` | **ALL 1000+** | ~2GB+ | Gitea only |
| `TROUBLESHOOT` | Resume | Debug | Both |

### Platform Summary

| Platform | Default | Offline | Notes |
|----------|---------|---------|-------|
| **GitHub** | QA | N/A | LFS limits prevent offline bundle |
| **Gitea** | QA | QA FULL | Self-hosted, no limits |

### QA FULL Mode

**GITEA ONLY. Never GitHub.** Too complicated + LFS bandwidth limits.

For TRUE OFFLINE deployments:
- Bundles Qwen model (2.3GB)
- All Python deps pre-installed
- VC++ Redistributable included
- **Zero internet required on user PC**

### Implementation Status

| Mode | Status | Platform |
|------|--------|----------|
| `QA` | ✅ DONE | Both |
| `QA FULL` | ✅ DONE | Gitea only |
| `TROUBLESHOOT` | ✅ DONE | Both |

---

## Code Coverage (P36)

**Current:** 47% → **Target:** 70% | **Measured:** 2025-12-22

### LDM Routes Coverage (NEW MOCKED TESTS!)

| Route | Coverage | Status |
|-------|----------|--------|
| projects.py | **98%** | ✅ DONE |
| folders.py | **90%** | ✅ DONE |
| tm_entries.py | **74%** | ✅ GOOD |
| tm_crud.py | 46% | OK |
| tm_search.py | 46% | OK |

### Test Counts (Build 424)

| Stage | Tests |
|-------|-------|
| Unit Tests | 801 |
| Integration | 198 |
| E2E | 97 |
| API | 131 |
| Security | 86 |
| Fixtures | 74 |
| Performance | 12 |
| **Total** | **1,399** |

**What's done:** Core CRUD routes fully mocked (68-98% coverage)
**What's fine:** Complex routes tested via 145+ E2E tests

### CI Package Verification (Build 424)

Windows build cache now validates critical packages before reuse:
- `$requiredPackages`: fastapi, uvicorn, sqlalchemy, pandas, pydantic, huggingface_hub, **faiss, lxml, asyncpg**
- If ANY package directory missing → cache invalidated → fresh install
- `scripts/verify_requirements.py`: Verifies critical packages post-install

---

## Code Quality (P37)

**Status: COMPLETE** - No active monoliths in codebase

### What Was Done
- `api.py` (3156 lines) → **DELETED** (dead code after route migration)
- `tm_indexer.py` (2105 lines) → **SPLIT** into 4 modular files

### LDM Structure Now
```
server/tools/ldm/
├── router.py              # 68 lines - aggregates 44 endpoints
├── routes/                # 14 files - API endpoints
├── schemas/               # 10 files - Pydantic models
├── indexing/              # 5 files - FAISS/Vector (was tm_indexer.py)
└── tm_manager.py          # 1133 lines - well-organized (not monolith)
```

### Global Audit Results
All large files (>500 lines) are well-organized, not true monoliths.

---

## Endpoint Audit (2026-01-01)

**Status:** COMPLETE | **Tests:** 187 | **Endpoints:** 118 | **Runtime:** 20 seconds

Full API connectivity audit to prevent orphan endpoint bugs (like UI-084).

| Category | Endpoints | Tests |
|----------|-----------|-------|
| LDM (CAT Tool) | 56 | 80+ |
| Tools (XLS/QS/KR) | 7 | 7 |
| Admin/Stats | 29 | 29 |
| Core/Auth/Health | 26 | 50+ |

| Phase | Status | Result |
|-------|--------|--------|
| Backend Collection | ✅ DONE | 118 endpoints verified |
| Frontend Collection | ✅ DONE | 100+ API calls mapped |
| Cross-Reference | ✅ DONE | 2 orphan calls found & fixed |
| CI Tests | ✅ DONE | 132 tests in `tests/api/` |
| Documentation | ✅ DONE | `docs/wip/ENDPOINT_AUDIT.md` |

**Test Coverage:**
```
tests/api/test_all_endpoints.py      - 159 tests (comprehensive suite)
tests/api/test_endpoint_existence.py - 28 tests (critical paths)
Total: 187 tests in ~20 seconds
```

**CI Integration:** Gitea Stage 4 (API Tests) automatically runs all `tests/api/*.py`

**Why:** LDM.svelte was calling non-existent endpoints (UI-084). These tests catch orphan endpoints on every build.

---

## CI/CD

| Platform | Tests | Status |
|----------|-------|--------|
| **Gitea (Linux)** | 1,399 | ✅ Build 426 |
| **Gitea (Windows)** | Verified | ✅ Cache validation fixed |
| **GitHub** | 1,399 | ✅ Build 426 (macOS enabled) |
| **Endpoint Tests** | 28 | ✅ All passing |

### Session 13 Fixes (2026-01-01)

| Fix | Issue | Resolution |
|-----|-------|------------|
| gsudo for SW | Windows Runner offline | Added `gsudo` to `gitea_control.sh` |
| macOS build | `electron-builder.json` not found | Config in `package.json`, not separate file |
| pg_trgm | TM similarity search 500 error | Added extension to both CI workflows |

### Windows PATH Tests (CRITICAL)

**Why:** All tests run on Linux. Windows-specific path bugs slip through.

| Test Category | Description | Status |
|---------------|-------------|--------|
| Download Path | File downloads go to correct location | Pending |
| Upload Path | File uploads work from Windows paths | Pending |
| Model Path | Qwen/embeddings load from AppData | Pending |
| PKL Path | Index files save/load correctly | Pending |
| Embeddings Path | Vector indexes stored properly | Pending |
| Install Path | App installs to Program Files | Pending |
| Merge Path | Merged files export to correct location | Pending (P3) |

**Implementation:** Add to `build-windows` job in CI workflow.

### Build Strategy

| Platform | Default | Offline |
|----------|---------|---------|
| **GitHub** | QA (~150MB) | N/A (LFS limits) |
| **Gitea** | QA (~150MB) | QA FULL (~1.2GB) ✅ |

---

## Architecture: Embedding Engines

**Important:** Different tools use different engines for good reasons.

| Tool | Engine | Why |
|------|--------|-----|
| **LDM TM Search** | Model2Vec (default) / Qwen (opt-in) | Real-time needs speed |
| **LDM Standard Pretranslation** | Model2Vec / Qwen (user choice) | Follows user toggle |
| **KR Similar Pretranslation** | **Qwen ONLY** | Quality > speed |
| **XLS Transfer Pretranslation** | **Qwen ONLY** | Quality > speed |

### Model2Vec: `potion-multilingual-128M`

| Metric | Value |
|--------|-------|
| Languages | **101** (including Korean) |
| Speed | **29,269 sentences/sec** |
| Dimension | 256 |
| License | MIT |

> The Fast/Deep toggle affects LDM TM search AND standard pretranslation.
> KR Similar / XLS Transfer pretranslation ALWAYS use Qwen.

---

## LDM Absorption Status

**Goal:** LDM absorbs ALL features → Legacy apps become redundant → Single unified LocaNext

### Absorption Tracker

| Legacy App | Feature | LDM Status | Notes |
|------------|---------|------------|-------|
| **XLS Transfer** | Dictionary/TM creation | ✅ ABSORBED | TM Management |
| **XLS Transfer** | Pretranslation | ✅ ABSORBED | Works in LDM |
| **XLS Transfer** | Excel import/export | ✅ ABSORBED | File parsing |
| **Quick Search** | Glossary extraction | ✅ ABSORBED | Context menu |
| **Quick Search** | Line Check | ✅ ABSORBED | Auto-LQA P2 |
| **Quick Search** | Term Check | 🔄 P5 | LanguageTool |
| **Quick Search** | Pattern Check | ✅ ABSORBED | Auto-LQA P2 |
| **Quick Search** | Character Check | ✅ ABSORBED | Auto-LQA P2 |
| **KR Similar** | Similarity search | ✅ ABSORBED | TM search |
| **KR Similar** | Pretranslation | ✅ ABSORBED | Deep mode |
| **All** | Spelling/Grammar | 🔄 P2 | LanguageTool |

### Remaining Features (After P1/P2)

| Feature | Source | Priority |
|---------|--------|----------|
| Character Limit Extract | `characterlimit.py` | Future |
| XML → Excel | `tmxtransfer11.py` | Future |
| Excel → XML | `tmxtransfer11.py` | Future |
| Excel ↔ TMX | `tmxtransfer11.py` | Future |
| Merge File | New | Future |

### End State Vision

```
CURRENT (4 apps):
├── LDM ─────────── Main app (growing)
├── XLS Transfer ── Standalone
├── Quick Search ── Standalone
└── KR Similar ──── Standalone

AFTER P1/P2 (transition):
├── LocaNext LDM ── All features absorbed
└── Legacy Menu ─── Button to access old UIs (deprecation period)

FINAL (1 app):
└── LocaNext ────── Single unified app (legacy menu removed)
```

### Tech Debt: LDM Independence

LDM currently imports from legacy apps (violates Rule #0):

| File | Bad Import | Fix |
|------|------------|-----|
| `pretranslate.py` | `xlstransfer/`, `kr_similar/` | Move to `server/utils/` |
| `tm.py` | `kr_similar/` | Move to `server/utils/` |

**Status:** Will fix during P1 implementation

---

## Completed: DESIGN-001 Public Permissions (Session 18)

**Status:** COMPLETE | **Date:** 2026-01-03 | **Doc:** `docs/wip/PUBLIC_PERMISSIONS_SPEC.md`

Transformed LDM from "private by default" to "public by default with optional restrictions":

| Feature | Description |
|---------|-------------|
| **Public by Default** | All resources visible to all users |
| **Optional Restriction** | Admins can restrict platforms/projects |
| **Globally Unique Names** | No duplicate names anywhere |
| **Access Grants** | Admins assign users to restricted resources |

### Key Changes
- Added `is_restricted` column to LDMPlatform and LDMProject
- Created `LDMResourceAccess` table for access grants
- Created `server/tools/ldm/permissions.py` with helper functions
- Updated 13 route files (77+ locations)
- Added admin endpoints for restriction management

---

## Completed Milestones (P1-P5)

| Priority | Feature | Description | Status |
|----------|---------|-------------|--------|
| **P1** | Factorization | Move shared code to `server/utils/`, LDM independence | ✅ DONE |
| **P2** | Auto-LQA System | LIVE QA + per-file QA + QA Menu | ✅ DONE |
| **P3** | MERGE System | Right-click → Merge confirmed cells to main LanguageData | ✅ DONE |
| **P4** | File Conversions | Right-click → Convert (XML↔Excel, Excel→TMX, etc.) | ✅ DONE |
| **P5** | LanguageTool | Spelling/Grammar via central server | ✅ DONE |

### P1: Factorization (LDM Independence) ✅ COMPLETE
- Moved shared code to `server/utils/` (qa_helpers.py, code_patterns.py)
- LDM no longer imports from legacy apps
- 785 tests passed after migration

### P2: Auto-LQA System ✅ COMPLETE (2025-12-25)
- **Backend:** LDMQAResult model, 7 API endpoints, 17 unit tests
- **LIVE Mode:** "QA On/Off" toggle → auto-check on cell confirm
- **QA Menu:** Slide-out panel with summary cards + issue list
- **Features:** QA flags on cells, row filtering dropdown, Edit Modal QA panel
- **Checks:** Pattern (code), Character (symbol count), Line (inconsistency)

### P3: MERGE System ✅ COMPLETE (2025-12-26)
- **Backend:** `POST /api/ldm/files/{file_id}/merge` endpoint
- **Frontend:** Right-click → "Merge to LanguageData..." context menu
- **Logic:** Match by StringID + Source → EDIT (update target) or ADD (append new)
- **Formats:** TXT and XML supported (Excel has no StringID)
- **Result:** User downloads merged file, commits to SVN/Perforce manually
- **Future:** Perforce API integration to create changelist directly

### P4: File Conversions ✅ COMPLETE (2025-12-26)
- **Backend:** `GET /api/ldm/files/{file_id}/convert?format=xlsx|xml|txt|tmx`
- **Frontend:** Right-click → "Convert to..." submenu with format options
- **Supported:** TXT→Excel/XML/TMX, XML→Excel/TMX, Excel→XML/TMX
- **NOT supported:** XML/Excel→TXT (StringID loss)

### P5: LanguageTool ✅ COMPLETE (2025-12-26)
- **Server:** LanguageTool 6.6 on 172.28.150.120:8081 (systemd auto-start)
- **Backend:** `/api/ldm/grammar/status`, `/files/{id}/check-grammar`, `/rows/{id}/check-grammar`
- **Frontend:** Right-click → "Check Spelling/Grammar" context menu
- **Modal:** Loading spinner, summary stats, error list with suggestions
- **Performance:** ~43ms/row, 937MB RAM, minimal CPU
- **Languages:** 30+ supported (EN, DE, FR, ES, etc. - Korean NOT supported)

---

## Future Ideas (Backlog)

### Perforce API Integration
**Context:** Game company uses SVN and Perforce for version control.
- SVN: No API, manual commit after merge (nothing we can do)
- Perforce: Has API, could create changelist directly after merge

**Potential Flow:**
```
1. User merges confirmed cells to LanguageData (P3)
2. User clicks "Submit to Perforce"
3. LocaNext calls Perforce API
4. Changelist created automatically
5. User reviews and submits in P4V
```

**Status:** Future consideration after P3 (MERGE) is working

### Other Future Features
- Character Limit Extract (from `characterlimit.py`)
- Batch operations on multiple files

---

## Current Priorities

| Priority | Feature | WIP Doc | Status |
|----------|---------|---------|--------|
| **P10** | **DB Abstraction Layer** | [P10_DB_ABSTRACTION.md](docs/wip/P10_DB_ABSTRACTION.md) | ✅ **COMPLETE** |
| P9 | Launcher + Offline/Online | [LAUNCHER_PLAN.md](docs/wip/LAUNCHER_PLAN.md) | ✅ COMPLETE |
| P8 | Dashboard Overhaul | [DASHBOARD_OVERHAUL_PLAN.md](docs/wip/DASHBOARD_OVERHAUL_PLAN.md) | PLANNED |
| P7 | Endpoint Audit System | [ENDPOINT_PROTOCOL.md](testing_toolkit/ENDPOINT_PROTOCOL.md) | ✅ DONE |
| P5 | Advanced Search | [ADVANCED_SEARCH.md](docs/wip/ADVANCED_SEARCH.md) | ✅ DONE |
| P3 | Offline/Online Mode | [OFFLINE_ONLINE_MODE.md](docs/wip/OFFLINE_ONLINE_MODE.md) | ✅ COMPLETE |
| P2 | Font Settings Enhancement | [FONT_SETTINGS_ENHANCEMENT.md](docs/wip/FONT_SETTINGS_ENHANCEMENT.md) | ✅ DONE |
| P1 | QA UIUX Overhaul | [QA_UIUX_OVERHAUL.md](docs/wip/QA_UIUX_OVERHAUL.md) | ✅ DONE |

---

## P10: DB Abstraction Layer ✅ COMPLETE

**Status:** COMPLETE | **Doc:** [docs/wip/P10_DB_ABSTRACTION.md](docs/wip/P10_DB_ABSTRACTION.md)

Complete DB Abstraction Layer across entire backend using Repository Pattern.

### Why P10?

| Before | After |
|--------|-------|
| 1 route uses Repository (TM) | ALL routes use Repository |
| 6 routes use ugly fallback pattern | No fallback |
| 10+ routes use direct PostgreSQL | No direct DB in routes |
| Inconsistent offline | **True offline parity** |

### Implementation Phases

| Phase | Scope | Status |
|-------|-------|--------|
| Phase 1 | Documentation & Foundation | ✅ DONE |
| Phase 2 | Core Repositories (File, Row, Project) | ✅ DONE |
| Phase 3 | Hierarchy Repositories (Folder, Platform) | ✅ DONE |
| Phase 4 | Support Repositories (QA, Trash) | ✅ DONE |
| Phase 5 | Route Migration | ✅ DONE |
| Phase 5B | sync.py → SyncService | ✅ DONE |
| Phase 6 | Testing & Validation | ✅ DONE |

### Repositories Implemented

| Repository | Interface | PostgreSQL | SQLite | Routes |
|------------|-----------|------------|--------|--------|
| TMRepository | ✅ | ✅ | ✅ | tm_assignment.py |
| FileRepository | ✅ | ✅ | ✅ | files.py (15/15) |
| RowRepository | ✅ | ✅ | ✅ | rows.py (3/3) |
| ProjectRepository | ✅ | ✅ | ✅ | projects.py (9/9) |
| FolderRepository | ✅ | ✅ | ✅ | folders.py (8/8) |
| PlatformRepository | ✅ | ✅ | ✅ | platforms.py (10/10) |
| QAResultRepository | ✅ | ✅ | ✅ | qa.py (6/6) |
| TrashRepository | ✅ | ✅ | ✅ | trash.py (4/4) |
| **SyncService** | ✅ | ✅ | ✅ | sync.py (6 sync endpoints) |

### Remaining Tasks

- [x] ~~Test both modes (PostgreSQL + SQLite)~~ - **DONE** (Session 50) - PostgreSQL FULL PASS, SQLite Repository FULL PASS
- [x] ~~Dead Code Audit~~ - **DONE** (removed 700+ lines)
- [x] ~~Post-P10 Code Review (qa.py)~~ - **DONE** (migrated to RowRepository)
- [x] ~~Granular Audit~~ - **DONE** (logging prefixes, dead code, unused files/folders)
- [x] ~~Minor files migrated (search.py, pretranslate.py, tm_linking.py)~~ - **DONE**

### Bugs Fixed During Testing (Session 50)

| File | Issue |
|------|-------|
| folder_repo.py | Removed `updated_at` (LDMFolder lacks it) |
| row_repo.py | Removed `created_at` (LDMRow lacks it) |
| file_repo.py | Removed `memo` and `created_at` |
| trash.py | Removed `memo` in serialize |

### Key Decisions

- **Approach:** Stability - One repository at a time, full testing after each
- **sync.py:** Refactor to Service Layer BEFORE applying Repository Pattern

---

## P9: Launcher + Patch Updates + Mode Switching ✅ COMPLETE

**Status:** COMPLETE | **Build:** 453 | **Doc:** `docs/wip/LAUNCHER_PLAN.md`

Beautiful game-launcher style first screen with mode switching.

### P9-ARCH: TM + Offline Storage (Session 30)

TMs can now be assigned to Offline Storage:
- Offline Storage platform/project created in PostgreSQL for TM FK constraints
- SQLite files use `project_id = -1`
- TM Tree shows Offline Storage as first platform
- Full TM operations: Assign, Activate, Deactivate, Delete, Multi-select

### P9: Folder CRUD in Offline Storage (Session 31)

Full folder management in Offline Storage:
- Create folders with nested navigation
- Rename and delete folders
- API endpoints: POST/DELETE/PUT for folders
- 7 Playwright tests covering all operations

### What Was Built

| Component | File | Status |
|-----------|------|--------|
| Launcher Store | `src/lib/stores/launcher.js` | ✅ NEW |
| Launcher UI | `src/lib/components/Launcher.svelte` | ✅ NEW |
| Layout Integration | `src/routes/+layout.svelte` | ✅ MODIFIED |
| Mode Switching | `src/lib/components/sync/SyncStatusPanel.svelte` | ✅ MODIFIED |
| Tests | `tests/launcher.spec.js` | ✅ 8 TESTS |

### Launcher Features

```
┌─────────────────────────────────────┐
│              LocaNext               │  ← Gradient logo (Svelte 5)
│    Professional Localization        │
│           v25.1214.2330             │
│                                     │
│    ● Central Server Connected       │  ← Live status check
│                                     │
│   ╭─────────────╮ ╭─────────────╮   │
│   │Start Offline│ │   Login     │   │  ← Two entry paths
│   │ No account  │ │ Connect to  │   │
│   │   needed    │ │   server    │   │
│   ╰─────────────╯ ╰─────────────╯   │
│                                     │
├─────────────────────────────────────┤
│  UPDATE PANEL (when available)      │  ← Industry-style progress
│  ████████████░░░░░ 68% | 12/18 MB   │
└─────────────────────────────────────┘
```

### Mode Switching (Offline → Online)

1. Start Offline → Works without login (SQLite)
2. Open Sync Dashboard → "Switch to Online" button
3. Login form appears → Enter credentials
4. Connect → Switches to Online mode (PostgreSQL)
5. Full sync capabilities enabled

### Tech Stack

- **Svelte 5** runes (`$state`, `$derived`)
- **Electron 39** (latest)
- **Carbon Components** (IBM design system)
- **8 Playwright tests** passing

### What Works in Each Mode

| Feature | Offline | Online |
|---------|---------|--------|
| XLSTransfer | ✅ | ✅ |
| QuickSearch | ✅ | ✅ |
| KR Similar | ✅ | ✅ |
| LDM (local files) | ✅ | ✅ |
| LDM (shared projects) | ❌ | ✅ |
| Translation Memory (local) | ✅ | ✅ |
| Translation Memory (shared) | ❌ | ✅ |
| Qwen AI | ✅ | ✅ |
| Real-time Sync | ❌ | ✅ |

### P8: Dashboard Overhaul (9 Phases)

**Status:** PLANNED | **Doc:** `docs/wip/DASHBOARD_OVERHAUL_PLAN.md`

Comprehensive admin dashboard upgrade with translation/QA analytics.

**Key Decisions:**
- Keep `adminDashboard/` separate (web access valuable)
- Upgrade Svelte 4.2.8 → 5.0.0
- Client-side metrics calculation (server just stores)
- Metrics-only payloads (~100 bytes, no text duplication)

**Phases:**
| Phase | Task | Complexity |
|-------|------|------------|
| 1 | Svelte 5 Upgrade | MEDIUM |
| 2 | Capability Assignment UI | LOW |
| 3 | UI/UX Improvements (spacious, customizable) | MEDIUM |
| 4 | Database Changes (2 new tables) | LOW |
| 5 | Translation Activity Logging (client-side difflib) | MEDIUM |
| 6 | QA Usage Logging | LOW |
| 7 | Translation Stats Page | MEDIUM |
| 8 | QA Analytics Page | LOW |
| 9 | Custom Report Builder | HIGH |

**Database:**
- 2 NEW tables: `translation_activity`, `qa_usage_log`
- 4 NEW columns on `ldm_rows` for pretranslation tracking
- 6 EXISTING tables already handle sessions/login/tool usage
- Storage: ~62 MB/year for 100 users

**Architecture:**
```
Client (Electron)              Server (FastAPI)
├─ difflib word-level diff     ├─ Validate metrics
├─ Calculate similarity %      ├─ INSERT to database
├─ Count words changed         └─ ~1ms response
└─ Send metrics only (~100B)

Dashboard aggregates data only when admin views.
```

### P3: Offline/Online Mode ✅ COMPLETE

**Status:** COMPLETE (Build 447) | **Doc:** `docs/wip/OFFLINE_ONLINE_MODE.md`

**Key Features:**
- Auto-connect: Online if possible, auto-fallback to offline ✅
- Manual sync: Right-click → Download/Sync ✅
- Push changes: Local → Server sync ✅
- Last-write-wins: Automatic conflict resolution ✅
- Hierarchy sync: Platform → Project → Folder → File ✅
- TM sync: Translation Memory syncs with last-write-wins ✅
- Per-parent unique names: Auto-rename duplicates (_1, _2) ✅
- Beautiful UI: Sync Dashboard, Status icons ✅

**Phase Status:**
| Phase | Scope | Status |
|-------|-------|--------|
| Phase 1 | Foundation - Basic offline viewing/editing | ✅ DONE |
| Phase 2 | Change Tracking - Track all local changes | ✅ DONE |
| Phase 3 | Sync Engine - Push local changes to server | ✅ DONE |
| Phase 4 | Conflict Resolution | ✅ DONE (last-write-wins, automatic) |
| Phase 5 | File Path Selection | ✅ DONE (Offline Storage fallback) |
| Phase 6 | Polish & Edge Cases | ✅ DONE (Build 447) |

**All P3 Phases COMPLETE!**

### P5: Advanced Search ✅ COMPLETE (Session 16)

Fuzzy search with 4 modes:
- ⊃ Contains (default)
- = Exact match
- ≠ Excludes
- ≈ Similar (pg_trgm fuzzy, 0.3 threshold)

### P7: Endpoint Audit System ✅ COMPLETE
Full automated endpoint lifecycle management (2026-01-01):
- ✅ `scripts/endpoint_audit.py` - Comprehensive audit tool v2.0
- ✅ Coverage report (206 endpoints, 34% tested)
- ✅ Documentation quality check (100% have summaries)
- ✅ Security audit (8 intentional unprotected endpoints)
- ✅ Auto-generate test stubs (135 tests created)
- ✅ HTML dashboard (`docs/endpoint_audit_report.html`)
- ✅ CI/CD JSON output for pipelines
- ✅ Strict mode (fails if < 80% coverage)

### P1: QA UIUX Overhaul ✅ Phase 1 DONE
Fixed stability issues (2025-12-29):
- ✅ Cancel button with AbortController
- ✅ Escape key closes panel
- ✅ Empty state: "QA not run" vs "No issues found"

### P2: Font Settings Enhancement ✅ COMPLETE
Font customization now available:
- Font Family: System, Inter, Roboto, Noto Sans (CJK), Source Han (CJK), Consolas
- Text Contrast: Default, High Contrast, Soft

---

## Quick Navigation

| Need | Go To |
|------|-------|
| **Session state** | [SESSION_CONTEXT.md](docs/wip/SESSION_CONTEXT.md) |
| **Open bugs** | [ISSUES_TO_FIX.md](docs/wip/ISSUES_TO_FIX.md) |
| **CI/CD docs** | [docs/cicd/CI_CD_HUB.md](docs/cicd/CI_CD_HUB.md) |
| **CDP Testing** | [testing_toolkit/cdp/README.md](testing_toolkit/cdp/README.md) |
| **Enterprise** | [docs/enterprise/HUB.md](docs/enterprise/HUB.md) |

---

## Architecture

```
LocaNext.exe (User PC)           Central PostgreSQL
├─ Electron + Svelte 5       →   ├─ All text data
├─ Embedded Python Backend       ├─ Users, sessions
├─ FAISS indexes (local)         ├─ LDM rows, TM entries
├─ Model2Vec (~128MB)            └─ Logs
├─ Qwen (2.3GB, opt-in)
└─ File parsing (local)

ONLINE:  PostgreSQL (multi-user, WebSocket sync)
OFFLINE: SQLite (single-user, auto-fallback)
```

---

## Quick Commands

```bash
# Check servers
./scripts/check_servers.sh

# Check release/tag sync
./scripts/check_releases_status.sh

# Start backend
python3 server/main.py

# Desktop app
cd locaNext && npm run electron:dev

# Playground INSTALL (fresh install only - use UPDATE for existing app!)
# See CLAUDE.md "INSTALL vs UPDATE" section for when to use each
./scripts/playground_install.sh --launch --auto-login

# Trigger builds
echo "Build" >> GITEA_TRIGGER.txt && git add -A && git commit -m "Build" && git push origin main && git push gitea main
```

---

## Key URLs

| Service | URL |
|---------|-----|
| Backend API | http://localhost:8888 |
| Gitea | http://172.28.150.120:3000 |
| CDP | http://127.0.0.1:9222 |

---

## Future Vision: Analytics & AI Integration

> **Full details:** [docs/wip/ANALYTICS_AI_VISION.md](locaNext/docs/wip/ANALYTICS_AI_VISION.md)

### Long-Term Roadmap (Post-Core Stability)

| Phase | Feature | Description |
|-------|---------|-------------|
| **P6** | Preference Persistence | Save user settings (columns, fonts) locally + DB sync |
| **P7** | Analytics Foundation | Translation activity logging, time tracking, edit distance |
| **P8** | Productivity Dashboard | Words/day, translation type classification, trends |
| **P9** | AI Translation | API integration (OpenAI, Claude, DeepL), file/cell translation |
| **P10** | Intelligence | Smart suggestions, quality scoring, team analytics |

### Key Concepts

1. **Translation Type Classification**
   - TRUE Translation (user typed from scratch)
   - TM Match (confirmed as-is vs modified)
   - AI Translation (confirmed as-is vs modified)

2. **Productivity Metrics**
   - Average time to confirm (relative to word count)
   - Edit distance from pre-translation to final
   - Daily TRUE translations vs assisted translations

3. **AI Integration Points**
   - Right-click file → Translate with AI
   - Right-click cell → Translate this string
   - Keyboard shortcut for inline AI translation

---

*Strategic Roadmap | Updated 2026-01-12 | P10 DB Abstraction COMPLETE (Session 50)*
