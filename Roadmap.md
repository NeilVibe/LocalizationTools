# LocaNext - Development Roadmap

**Version**: 2512120100 | **Updated**: 2025-12-12 | **Status**: Production Ready

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

| Priority | Name | Status | WIP Doc |
|----------|------|--------|---------|
| **P25** | LDM UX Overhaul | 📋 NEW | [P25_LDM_UX_OVERHAUL.md](docs/wip/P25_LDM_UX_OVERHAUL.md) |
| **P24** | Server Status Dashboard | 📋 Pending | [P24_STATUS_DASHBOARD.md](docs/wip/P24_STATUS_DASHBOARD.md) |
| **P17** | LDM LanguageData Manager | 67% | [P17_LDM_TASKS.md](docs/wip/P17_LDM_TASKS.md) |
| **P22** | SQLite Removal | Phase 1 ✅ | [P22_PRODUCTION_PARITY.md](docs/wip/P22_PRODUCTION_PARITY.md) |
| **P23** | Data Flow (Production) | 📋 Later | [P23_DATA_FLOW_ARCHITECTURE.md](docs/wip/P23_DATA_FLOW_ARCHITECTURE.md) |
| **P21** | Database Powerhouse | ✅ Complete | [P21_DATABASE_POWERHOUSE.md](docs/wip/P21_DATABASE_POWERHOUSE.md) |
| **ISSUES** | Bug Fixes | 1 Open | [ISSUES_TO_FIX.md](docs/wip/ISSUES_TO_FIX.md) |

---

## Active Development

### P25: LDM UX Overhaul (NEW - Major)

Comprehensive UX improvements based on user feedback.

**Bugs Fixed (Phase 1):**
- ✅ Target lock blocking editing (BUG-002)
- ✅ Upload tooltip z-index (BUG-003)
- ✅ Search bar icon requirement (BUG-004)
- ✅ Go to row removed (BUG-001)

**Grid Simplification (Phase 2 - DONE):**
- ✅ Status column REMOVED → Using cell colors instead
  - Teal left border = translated
  - Blue left border = reviewed
  - Green left border = approved/confirmed
- Default: Source + Target columns only
- Optional columns via Preferences: Index, String ID, Reference, TM, QA

**New Features:**
- **Preferences Menu** - Toggle columns, configure QA/TM/Reference
- **Edit Workflow** - Ctrl+S=Confirm, Ctrl+T=Translate only
- **Merge Function** - Merge confirmed strings back to original file
- **Reference Column** - Load reference from project/local file
- **TM Integration** - Upload TM, show in Tasks, TM Results column
- **Live QA** - Spell, grammar, glossary term, inconsistency checks
- **Auto-Glossary** - Generate glossary during TM upload

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

### Known Issues (1 Open)

| ID | Status | Description |
|----|--------|-------------|
| ~~BUG-001~~ | ✅ Fixed | ~~Go to row removed~~ |
| ~~BUG-002~~ | ✅ Fixed | ~~Target lock blocking editing~~ |
| ~~BUG-003~~ | ✅ Fixed | ~~Upload tooltip z-index~~ |
| ~~BUG-004~~ | ✅ Fixed | ~~Search bar requires icon click~~ |
| ISSUE-011 | 📋 Open | Missing TM upload UI (backend ready) |

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

### P25 Phase 1+2: Bug Fixes + Grid UX ✅ (2025-12-12)
- BUG-001, BUG-002, BUG-003, BUG-004 all fixed
- Light/Dark theme toggle
- Font size/weight settings
- CDP test suite (Normal + Detailed)
- Status column REMOVED → Cell colors show status
- Go to Row button REMOVED

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
