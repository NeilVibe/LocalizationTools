# LocaNext - Roadmap & Navigation Hub

**Build:** 295 ✅ | **Updated:** 2025-12-17 | **Status:** 98% Complete | **Open Issues:** 0

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
LocaNext v25.1216.1626 (Build 295 released)
├── Backend:     ✅ PostgreSQL + SQLite offline
├── Frontend:    ✅ Electron 39 + Svelte 5 + Vite 7
├── Tools:       ✅ XLSTransfer, QuickSearch, KR Similar, LDM
├── CI/CD:       ✅ ~273 tests in ~5min (PostgreSQL verified)
├── Offline:     ✅ Auto-fallback + indicator + Server Config UI
├── UI:          ✅ Compartmentalized modals (UI-001 to UI-004)
└── Installer:   ✅ NSIS fixed, release available
```

---

## Priority Queue

### NOW: P36 Unified Pretranslation System

**TM = single source of truth.** Three separate engines, user selects one.

| Phase | Description | Status |
|-------|-------------|--------|
| Phase 1 | E2E testing + validation | ✅ **COMPLETE** |
| Phase 2 | Backend + TM Merge | **NEXT** |
| Phase 3 | Pretranslation Modal UI | Pending |
| Phase 4 | Integration + testing | Pending |

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
| **UI-001 to UI-004** | 2025-12-16 | Compartmentalized modals, dark mode only |
| **BUG-012 Server Config** | 2025-12-16 | PostgreSQL config UI for online mode |
| Connectivity Tests | 2025-12-16 | 26 new tests for offline/online mode |
| P35 Svelte 5 Migration | 2025-12-16 | Fixed BUG-011 (connection issue) |
| CI Smoke Tests | 2025-12-16 | Svelte 5 + **PostgreSQL verification** |
| P33 Offline Mode | 2025-12-15 | SQLite fallback + auto-fallback |
| P28 NSIS Installer | 2025-12-14 | electron-builder NSIS |

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
│   ├── ISSUES_TO_FIX.md      # ← Bug tracker (0 open)
│   ├── POTENTIAL_ISSUES.md   # ← Future reference
│   ├── P36_PRETRANSLATION_STACK.md # ← Current work
│   └── P25_LDM_UX_OVERHAUL.md # ← 85% done
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
