# LocaNext - Development Roadmap

**Version**: 2512122200 | **Updated**: 2025-12-12 | **Status**: Production Ready

> **Full History**: [docs/history/ROADMAP_ARCHIVE.md](docs/history/ROADMAP_ARCHIVE.md)
> **Detailed Tasks**: [docs/wip/README.md](docs/wip/README.md) (WIP Hub)
> **Session Context**: [docs/wip/SESSION_CONTEXT.md](docs/wip/SESSION_CONTEXT.md)

---

## Current Status

```
LocaNext v2512111745
├── Backend:     ✅ 55+ API endpoints, async, WebSocket
├── Frontend:    ✅ Electron + Svelte (LocaNext Desktop)
├── Tools:       ✅ XLSTransfer, QuickSearch, KR Similar + LDM 67%
├── Tests:       ✅ 912 total (595 unit pass, no mocks)
├── Security:    ✅ 86 tests (IP filter, CORS, JWT, audit)
├── CI/CD:       ✅ GitHub Actions + Gitea (FULLY WORKING!)
├── Database:    ✅ PostgreSQL + PgBouncer (NO SQLite!)
└── Distribution: ✅ Auto-update enabled
```

---

## Priority Status Overview

| # | Priority | Name | Status | Doc |
|---|----------|------|--------|-----|
| **1** | **CODE REVIEW** | Deep Review (12 sessions) | 🔨 Session 1 | [docs/code-review/](docs/code-review/) |
| 2 | P25 | LDM UX Overhaul | 🔨 70% | [P25_LDM_UX_OVERHAUL.md](docs/wip/P25_LDM_UX_OVERHAUL.md) |
| 3 | P24 | Server Status Dashboard | 📋 Pending | [P24_STATUS_DASHBOARD.md](docs/wip/P24_STATUS_DASHBOARD.md) |
| 4 | P17 | LDM LanguageData Manager | 67% | [P17_LDM_TASKS.md](docs/wip/P17_LDM_TASKS.md) |
| - | P22 | SQLite Removal | ✅ Phase 1 | [P22_PRODUCTION_PARITY.md](docs/wip/P22_PRODUCTION_PARITY.md) |
| - | P21 | Database Powerhouse | ✅ Complete | [P21_DATABASE_POWERHOUSE.md](docs/wip/P21_DATABASE_POWERHOUSE.md) |
| - | ISSUES | Bug Fixes | 2 Open | [ISSUES_TO_FIX.md](docs/wip/ISSUES_TO_FIX.md) |

---

## Active Development

### CODE REVIEW: Deep Review (Priority #1)

Full codebase review - 12 sessions in dependency order.

**Protocol:** [docs/code-review/CODE_REVIEW_PROTOCOL.md](docs/code-review/CODE_REVIEW_PROTOCOL.md)

| Session | Module | Status |
|---------|--------|--------|
| 1 | Database & Models | 🔨 Next |
| 2 | Utils & Core | 📋 |
| 3 | Auth & Security | 📋 |
| 4 | LDM Backend | 📋 |
| 5 | XLSTransfer | 📋 |
| 6 | QuickSearch | 📋 |
| 7 | KR Similar | 📋 |
| 8 | API Layer | 📋 |
| 9 | Frontend Core | 📋 |
| 10 | Frontend LDM | 📋 |
| 11 | Admin Dashboard | 📋 |
| 12 | Scripts & Config | 📋 |

**Quick Scan Week 1:** ✅ Complete (9 issues found, 4 fixed, Pass 2 clean)

---

### P25: LDM UX Overhaul (70% Complete)

Comprehensive UX improvements based on user feedback.

**Phase 1: Bug Fixes ✅**
- ✅ Target lock blocking editing (BUG-002)
- ✅ Upload tooltip z-index (BUG-003)
- ✅ Search bar icon requirement (BUG-004)
- ✅ Go to row removed (BUG-001)

**Phase 2: Grid Simplification ✅**
- ✅ Status column REMOVED → Using cell colors instead
- ✅ Default: Source + Target columns only
- ✅ Cell colors: teal=translated, blue=reviewed, green=approved

**Phase 3: Edit Modal Redesign ✅**
- ✅ BIG modal (85% width/height)
- ✅ Two-column layout: Source/Target left, TM panel right
- ✅ Shortcut bar at top (Ctrl+S, Ctrl+T, Tab, Esc)
- ✅ Keyboard shortcuts working (Ctrl+S=Confirm, Ctrl+T=Translate)

**Phase 4: Preferences Menu ✅**
- ✅ Column toggles: Index Number, String ID
- ✅ Settings persist in localStorage
- ✅ Grid updates dynamically
- Reference/TM/QA toggles ready (disabled until features built)

**Phase 5: Download/Export ✅** (NEW)
- ✅ Download endpoint + frontend menu
- ✅ Status filters (all, translated, reviewed)
- ✅ TXT/XML/Excel export
- ✅ Format verification test (exact match with original)

**Remaining Phases:**
- Phase 6: Right-Click Context Menu - download, QA, upload as TM
- Phase 7: Tasks Panel - background task progress (TM processing, QA)
- Phase 8: Reference Column - show reference from another file
- Phase 9: TM Integration - upload TM, TM Results column
- Phase 10: Live QA System - spell, grammar, glossary checks

**Details:** [P25_LDM_UX_OVERHAUL.md](docs/wip/P25_LDM_UX_OVERHAUL.md)

---

### P24: Server Status Dashboard

Real-time health monitoring for Central Server.

**LocaNext App (Simple):**
- Connection status: green/orange/red
- Basic server health

**Admin Dashboard (Detailed):**
- API Server status + response time
- Database: connections, load, query time
- WebSocket: active connections
- System: CPU, memory, disk
- Active users count

**Details:** [P24_STATUS_DASHBOARD.md](docs/wip/P24_STATUS_DASHBOARD.md)

---

### P17: LDM LanguageData Manager (67%)

Professional CAT tool with 5-tier cascade TM search.

**What's Done:**
- ✅ Virtual scroll grid (1M+ rows)
- ✅ File Explorer (projects, folders)
- ✅ Real-time WebSocket sync
- ✅ Phase 7.1-7.3: TM Database + TMManager + TMIndexer

**What's Next (Pick One):**

| Task | Priority | Notes |
|------|----------|-------|
| **TM Upload UI** | HIGH | ISSUE-011 - Backend ready, need frontend |
| **TM Search API** | HIGH | Phase 7.4 - `tm_search.py` |
| **Custom Excel picker** | HIGH | Column selection (not just A/B) |
| **Custom XML picker** | HIGH | Attribute selection |

**Details:** [P17_LDM_TASKS.md](docs/wip/P17_LDM_TASKS.md)

---

### P22: SQLite Removal (Phase 1 ✅)

**Completed (2025-12-11):**
- ✅ 12 server files cleaned
- ✅ 595 unit tests pass
- ✅ PostgreSQL-only architecture

---

### P23: Data Flow Architecture (LATER)

**For Production Deployment** - Not needed during development.

Currently localhost:8888 is hardcoded, which is FINE for dev/testing.

**Connection Flow (Simplified):**
```
1. Admin sets Central Server IP (once, in build or config)
2. User launches app → connects to Central Server
3. Server checks client IP against whitelist (already built!)
4. If authorized → connect, show green status
```

**What's LEFT to build:**
- Connection Status Panel (green/orange/red indicators)
- IP whitelist already exists in `server/middleware/`

**Details:** [P23_DATA_FLOW_ARCHITECTURE.md](docs/wip/P23_DATA_FLOW_ARCHITECTURE.md)

---

### Known Issues (2 Open)

| ID | Status | Description |
|----|--------|-------------|
| ~~BUG-001~~ | ✅ Fixed | ~~Go to row removed~~ |
| ~~BUG-002~~ | ✅ Fixed | ~~Target lock blocking editing~~ |
| ~~BUG-003~~ | ✅ Fixed | ~~Upload tooltip z-index~~ |
| ~~BUG-004~~ | ✅ Fixed | ~~Search bar requires icon click~~ |
| ISSUE-011 | 📋 Open | Missing TM upload UI (backend ready) |
| ISSUE-013 | 📋 Open | WebSocket locking events (workaround applied) |

**Details:** [ISSUES_TO_FIX.md](docs/wip/ISSUES_TO_FIX.md)

---

## Architecture

```
┌─────────────────────────────────────────┐
│         Development (localhost)          │
├─────────────────────────────────────────┤
│  LocaNext Desktop                       │
│       ↓                                 │
│  FastAPI Backend (localhost:8888)       │
│       ↓                                 │
│  PostgreSQL (localhost:5432)            │
│       ↓                                 │
│  Local Indexes (FAISS, embeddings)      │
└─────────────────────────────────────────┘

Central = PostgreSQL (text data)
Local = Heavy processing (FAISS, ML - rebuildable)
```

---

## Recently Completed

### P25 Phases 1-5: Core UX + Download ✅ (2025-12-12)
- BUG-001, BUG-002, BUG-003, BUG-004 all fixed
- Light/Dark theme toggle + Font settings
- Status column → Cell colors, Go to Row removed
- **Edit Modal Redesign** - BIG modal, TM panel, shortcuts
- **Preferences Menu** - Column toggles (Index, StringID)
- **Download/Export** - TXT/XML/Excel with format verification
- CDP test suite (Normal + Detailed + Format verification)

### P22 Phase 1: SQLite Removal ✅ (2025-12-11)
- 12 server files cleaned
- 595 unit tests pass

### P21: Database Powerhouse ✅ (2025-12-10)
- PgBouncer 1.16 - 1000 connections
- COPY TEXT - 31K entries/sec

### P20: Embedding Model Migration ✅ (2025-12-09)
- Qwen3-Embedding-0.6B (Apache 2.0)

---

## Quick Commands

```bash
# Start servers
python3 server/main.py
cd locaNext && npm run electron:dev

# Testing
python3 -m pytest tests/unit/ -v  # 595 tests

# Check session context
cat docs/wip/SESSION_CONTEXT.md
```

---

## Key Principles

1. **Monolith is Sacred** - Copy logic exactly, only change UI
2. **PostgreSQL Only** - No SQLite in LocaNext core
3. **Central = Text, Local = Heavy** - Data architecture
4. **Log Everything** - Use `logger`, never `print()`
5. **localhost OK for dev** - Server URL config is for production

---

*For session context, see [docs/wip/SESSION_CONTEXT.md](docs/wip/SESSION_CONTEXT.md)*
