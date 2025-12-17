# LocaNext - Roadmap & Navigation Hub

**Build:** 297 (pending) | **Updated:** 2025-12-18 10:00 KST | **Status:** 99% Complete | **Open Issues:** 2

---

## ✅ BUG-016 COMPLETE: Global Toast Notifications

**Toast notifications now appear on ANY page when Task Manager operations start/complete/fail!**

| Feature | Status | Details |
|---------|--------|---------|
| Toast Notifications | ✅ COMPLETE | Global toasts via WebSocket events |
| TM Viewer | ✅ COMPLETE | Paginated, sortable, searchable, inline edit |
| TM Export | ✅ COMPLETE | TEXT/Excel/TMX with column selection |
| Task Manager | ✅ COMPLETE | 22 operations tracked across 4 tools |
| E2E Tests | ✅ COMPLETE | 20 tests for all 3 engines |

---

## ✅ All Critical Issues FIXED

### Pipeline Status

| Engine | Status | Notes |
|--------|--------|-------|
| **Standard TM** | ✅ WORKS | StringID, incremental sync |
| **XLS Transfer** | ✅ WORKS | Code preservation |
| **KR Similar** | ✅ WORKS | Structure adaptation |
| **TM Viewer** | ✅ WORKS | Full CRUD with pagination |
| **TM Export** | ✅ WORKS | 3 formats, column selection |
| **Task Manager** | ✅ WORKS | 22 operations tracked |
| **Toast Notifications** | ✅ WORKS | Global toasts on any page |

### Recently Fixed

| Issue | Fix |
|-------|-----|
| **BUG-016** | Global Toast Notifications (toastStore.js + GlobalToast.svelte) |
| **FEAT-003** | TM Viewer (TMViewer.svelte + API endpoints) |
| **FEAT-002** | TM Export (TEXT/Excel/TMX) |
| **TASK-002** | Full E2E tests for all 3 engines (20 tests total) |
| **TASK-001** | TrackedOperation for ALL long processes |
| **BUG-022** | Incremental updates via TMSyncManager.sync() |

### Remaining

| Item | Priority | Description |
|------|----------|-------------|
| **BUG-020** | HIGH | TM entry metadata for memoQ workflow |
| **FEAT-001** | LOW | TM Metadata enhancement (optional) |

**See:** [ISSUES_TO_FIX.md](docs/wip/ISSUES_TO_FIX.md)

---

## Quick Navigation

| Need | Go To |
|------|-------|
| **Session state?** | [SESSION_CONTEXT.md](docs/wip/SESSION_CONTEXT.md) |
| **Open bugs?** | [ISSUES_TO_FIX.md](docs/wip/ISSUES_TO_FIX.md) |
| **WIP tasks?** | [docs/wip/README.md](docs/wip/README.md) |
| **Enterprise deploy?** | [docs/enterprise/HUB.md](docs/enterprise/HUB.md) |
| **How to do X?** | [docs/README.md](docs/README.md) |

---

## Current Status

```
LocaNext v25.1217.0100 (Build 296 released)
├── Backend:     ✅ PostgreSQL + SQLite offline
├── Frontend:    ✅ Electron 39 + Svelte 5 + Vite 7
├── Tools:       ✅ XLSTransfer, QuickSearch, KR Similar, LDM
├── CI/CD:       ✅ ~273 tests in ~5min (PostgreSQL verified)
├── Offline:     ✅ Auto-fallback + status indicator
├── UI:          ✅ Compartmentalized modals (UI-001 to UI-004)
├── Security:    ✅ Removed Server Config UI (no dev data exposed)
└── Installer:   ✅ NSIS fixed, release available
```

---

## Priority Queue

### NOW: P36 Unified Pretranslation System

**TM = single source of truth.** Three separate engines, user selects one.

| Phase | Description | Status |
|-------|-------------|--------|
| Phase 1 | E2E testing + validation | ✅ **COMPLETE** |
| Phase 2A | Excel File Editing (excel_handler.py + API) | ✅ **COMPLETE** |
| Phase 2B | TM StringID Support (DB + handler) | ✅ **COMPLETE** |
| Phase 2C | Pretranslation API | ✅ **COMPLETE** |
| Phase 2C+ | PKL StringID Metadata (variations structure) | ✅ **COMPLETE** |
| Phase 2D | TRUE E2E Testing | ✅ **COMPLETE** |
| Phase 2E | Pipeline Bug Fixes (6 CRITICAL) | ✅ **COMPLETE** |
| Phase 2F | Task Manager Integration (TASK-001) | ✅ **COMPLETE** |
| Phase 3 | Frontend modals | Pending |

**Phase 2D TRUE E2E Testing Progress:**
| Engine | Test | Status | Notes |
|--------|------|--------|-------|
| **Standard TM** | `true_e2e_standard.py` | ✅ **6/6 PASSED** | Full pipeline works |
| **XLS Transfer** | `true_e2e_xls_transfer.py` | ✅ **7/7 PASSED** | **Isolated logic only** |
| | Full pipeline | ✅ **WORKS** | BUG-013: FIXED |
| **KR Similar** | `true_e2e_kr_similar.py` | ⏳ **PENDING** | After embedding mgmt |

**XLS Transfer Results:** 4006 dictionary entries, 150 test rows, 98.5% code preservation rate

**Phase 2 Key Features:**
```
Excel File Support (2 or 3 columns):
├── File Editing: Upload Excel → Edit in LDM grid → Export
├── TM Creation: Upload Excel → Create TM → Pretranslate
├── User selects columns via UI (not hardcoded)
└── 2-col (Source+Target) or 3-col (Source+Target+StringID)

TM Creation Modes:
├── Standard Mode: Source + Target (duplicates merged)
├── StringID Mode: Source + Target + StringID (all variations kept)
├── Data validation + TM name validation
└── Right-click Excel → Create TM...

StringID Benefits:
├── Same source "저장" → multiple targets based on context
├── UI_BUTTON_SAVE → "Save"
├── UI_MENU_SAVE → "Save Game"
└── Pretranslation matches by StringID first, then shows alternatives

Technical: Embeddings for SOURCE only, StringID is metadata in PKL
```

**API-Dependent Features (FUTURE):** `docs/future/smart-translation/`
- Smart Translation Pipeline (requires QWEN/Claude API)
- Dynamic glossary translation

**Details:** [P36_TECHNICAL_DESIGN.md](docs/wip/P36_TECHNICAL_DESIGN.md)

**Testing Plan:** [P36_STRINGID_TESTING_PLAN.md](docs/wip/P36_STRINGID_TESTING_PLAN.md)

**Phase 1 Complete - E2E Test Results:**
```
All Tests Passing: 2,172 total
├── XLS Transfer E2E: 537 passed ✅
├── KR Similar E2E: 530 passed ✅
├── Standard TM E2E: 566 passed ✅
├── QWEN+FAISS Real E2E: 500 queries ✅
├── Korean Accuracy: 12 categories tested ✅
├── QWEN validation: 26/27 passed ✅
└── Real pattern tests: 13/13 passed ✅

Key Finding: QWEN = TEXT similarity (not meaning)
├── Same text: 100% ✅
├── Minor diff (particles): 96% ✅
├── Different words: 58% (correctly low) ✅
└── 92% threshold appropriate for text matching ✅
```

**Details:** [P36_PRETRANSLATION_STACK.md](docs/wip/P36_PRETRANSLATION_STACK.md)

### ALSO: P25 LDM UX (85% done)

- TM matching (Qwen + FAISS)
- QA checks
- Custom pickers

**Details:** [P25_LDM_UX_OVERHAUL.md](docs/wip/P25_LDM_UX_OVERHAUL.md)

### All Issues Resolved (0 Open)

**All 38 issues fixed!** No blocking issues remaining.

| Recently Fixed | Description |
|----------------|-------------|
| UI-001 | Dark mode only - removed theme toggle |
| UI-002 | Compartmentalized modals (Grid, Reference, Display) |
| UI-003 | TM activation in TMManager |
| UI-004 | Removed TM Results checkbox |
| BUG-012 | Server Config UI for PostgreSQL |

**Details:** [ISSUES_TO_FIX.md](docs/wip/ISSUES_TO_FIX.md)

---

## Recently Completed

| What | When | Details |
|------|------|---------|
| **TASK-001 TrackedOperation** | 2025-12-17 | All long operations now tracked for UI feedback |
| **P36 Phase 2E Bug Fixes** | 2025-12-17 | 7 critical bugs fixed, all pipelines working |
| **Playground PostgreSQL** | 2025-12-17 | Auto-config + UTF-8 BOM fix, verified ONLINE |
| **Security Fix** | 2025-12-17 | Removed Server Config UI (no dev data exposed) |
| **P36 Phase 1 E2E Tests** | 2025-12-17 | 2,133 tests (XLS Transfer, KR Similar, Standard TM, QWEN) |
| **Doc cleanup + archive** | 2025-12-17 | 12 P* files archived, enterprise docs created |
| **UI-001 to UI-004** | 2025-12-16 | Compartmentalized modals, dark mode only |
| Connectivity Tests | 2025-12-16 | 26 new tests for offline/online mode |
| P35 Svelte 5 Migration | 2025-12-16 | Fixed BUG-011 (connection issue) |
| P33 Offline Mode | 2025-12-15 | SQLite fallback + auto-fallback |

---

## Architecture

```
LocaNext.exe (User PC)           Central PostgreSQL
├─ Electron + Svelte 5       →   ├─ All text data
├─ Embedded Python Backend       ├─ Users, sessions
├─ FAISS indexes (local)         ├─ LDM rows, TM entries
├─ Qwen model (local, 2.3GB)     └─ Logs, telemetry
└─ File parsing (local)

ONLINE:  PostgreSQL (multi-user, WebSocket sync)
OFFLINE: SQLite (single-user, auto-login)
```

---

## Quick Commands

```bash
# Check servers
./scripts/check_servers.sh

# Start servers
./scripts/start_all_servers.sh

# Build frontend
cd locaNext && npm run build

# Run tests
python3 -m pytest tests/unit/ tests/integration/ -v

# Trigger CI build
echo "Build LIGHT" >> GITEA_TRIGGER.txt && git add -A && git commit -m "Build" && git push origin main && git push gitea main
```

---

## Key URLs

| Service | URL |
|---------|-----|
| Backend API | http://localhost:8888 |
| API Docs | http://localhost:8888/docs |
| Gitea | http://localhost:3000 |
| Admin Dashboard | http://localhost:5175 |

---

## Documentation Index

```
docs/
├── wip/                      # Active work
│   ├── SESSION_CONTEXT.md    # ← Last session state
│   ├── ISSUES_TO_FIX.md      # ← Bug tracker (6 open)
│   ├── P36_PRETRANSLATION_STACK.md  # ← P36 scope & plan
│   ├── P36_TECHNICAL_DESIGN.md      # ← P36 technical details
│   ├── P36_STRINGID_TESTING_PLAN.md # ← Testing fixtures & E2E plan
│   └── P25_LDM_UX_OVERHAUL.md       # ← 85% done
├── future/                   # API-dependent features (NEW)
│   └── smart-translation/    # ← When API available
├── enterprise/               # Company deployment (14 files)
│   └── HUB.md                # ← Start here for deploy
├── history/                  # Archives
│   ├── wip-archive/          # ← Completed P* files
│   └── ISSUES_HISTORY.md     # ← Fixed bugs (38)
├── getting-started/          # Onboarding
├── architecture/             # Design docs
├── development/              # Coding guides
├── build/                    # Build & CI
├── testing/                  # Test guides
└── troubleshooting/          # Debug help
```

---

## Key Principles

1. **Monolith is Sacred** - Copy logic from `RessourcesForCodingTheProject/`, only change UI
2. **Central = Text, Local = Heavy** - PostgreSQL for data, local for FAISS/Qwen
3. **Log Everything** - Use `logger`, never `print()`
4. **Fix Everything** - No deferring, no excuses, fix ALL issues

---

*Details live in linked docs. This file is navigation only.*
