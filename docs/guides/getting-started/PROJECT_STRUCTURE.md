# Project Structure

**Complete File Tree** | **Module Organization** | **Architecture Overview**

---

## COMPLETE PROJECT TREE

```
LocalizationTools/
│
├── PROJECT DOCS (READ THESE!)
│   ├── CLAUDE.md ⭐ MASTER NAVIGATION HUB - Start here!
│   ├── Roadmap.md ⭐ Development plan, next steps
│   ├── README.md - User-facing documentation
│   └── docs/ - Detailed documentation (see below)
│
├── SERVER (100% COMPLETE)
│   ├── server/
│   │   ├── main.py ⭐ FastAPI server entry point
│   │   ├── config.py - Server configuration
│   │   ├── api/ - API endpoints
│   │   │   ├── auth_async.py ⭐ Async authentication
│   │   │   ├── logs_async.py ⭐ Async logging
│   │   │   ├── sessions_async.py ⭐ Async sessions
│   │   │   ├── admin_telemetry.py - Telemetry dashboard
│   │   │   └── schemas.py - Pydantic models
│   │   ├── database/ - Database layer
│   │   │   ├── models.py ⭐ SQLAlchemy models (17 tables)
│   │   │   ├── db_setup.py - Database initialization
│   │   │   └── db_utils.py - COPY TEXT bulk inserts
│   │   ├── data/ ⭐ LOCAL COMPUTED FILES (heavy stuff)
│   │   │   ├── ldm_tm/ - TM indexes (FAISS, hash, embeddings)
│   │   │   ├── logs/ - Server logs
│   │   │   ├── cache/ - Temp files
│   │   │   └── outputs/ - Tool outputs
│   │   ├── tools/ ⭐ ALL TOOL BACKENDS
│   │   │   ├── xlstransfer/ - Excel transfer tool
│   │   │   ├── quicksearch/ - Dictionary search
│   │   │   ├── kr_similar/ - Korean similarity
│   │   │   └── ldm/ ⭐ Language Data Manager
│   │   │       ├── api.py - LDM API endpoints
│   │   │       ├── tm_manager.py - TM CRUD
│   │   │       ├── tm_indexer.py - FAISS index builder
│   │   │       └── file_handlers/ - TXT/XML parsers
│   │   ├── utils/ - Server utilities
│   │   │   ├── auth.py ⭐ JWT, password hashing
│   │   │   ├── dependencies.py ⭐ Async DB sessions
│   │   │   └── websocket.py ⭐ Real-time sync
│   │   └── middleware/ - Request/response logging
│   │
│   └── BACKEND STATUS:
│       ✅ PostgreSQL (ALL text data)
│       ✅ PgBouncer (1000 connections)
│       ✅ Async architecture
│       ✅ WebSocket real-time sync
│       ✅ 63+ API endpoints
│
├── LOCANEXT (ELECTRON DESKTOP APP - COMPLETE)
│   └── locaNext/
│       ├── electron/ - Electron main process
│       │   ├── main.js ⭐ Main process
│       │   ├── preload.js - Preload script
│       │   ├── telemetry.js - Sends logs to central server
│       │   └── health-check.js - Auto-repair system
│       ├── src/ - Svelte frontend
│       │   ├── routes/
│       │   │   └── +page.svelte - Main app page
│       │   └── lib/
│       │       └── components/
│       │           └── apps/
│       │               ├── XLSTransfer.svelte
│       │               ├── QuickSearch.svelte
│       │               ├── KRSimilar.svelte
│       │               └── LDM.svelte ⭐ Language Data Manager
│       └── STATUS: ✅ COMPLETE
│
├── ADMIN DASHBOARD (COMPLETE)
│   └── adminDashboard/
│       ├── src/routes/
│       │   ├── +page.svelte - Dashboard Home
│       │   ├── users/ - User Management
│       │   ├── stats/ - Statistics
│       │   ├── logs/ - Logs Viewer
│       │   └── telemetry/ - Telemetry dashboard
│       └── STATUS: ✅ COMPLETE
│
├── TESTS (912 PASSING)
│   └── tests/
│       ├── unit/ - Unit tests
│       ├── integration/ - Integration tests
│       ├── e2e/ - End-to-end tests
│       └── security/ - Security tests (86)
│
├── SCRIPTS (UTILITIES)
│   └── scripts/
│       ├── create_admin.py ⭐ Create admin user
│       ├── check_version_unified.py ⭐ Version check
│       ├── benchmark_copy.py - DB performance test
│       └── generate_postgresql_config.py - DB tuning
│
└── DOCS (DOCUMENTATION)
    └── docs/
        ├── getting-started/ - Onboarding guides
        ├── INDEX.md - Navigation hub
        ├── architecture/ - System design (6 docs)
        ├── protocols/ - Claude protocols (GDP)
        ├── current/ - Active work
        │   ├── SESSION_CONTEXT.md - Session state
        │   └── ISSUES_TO_FIX.md - Bug tracker
        ├── reference/ - Stable reference docs
        │   ├── cicd/ - CI/CD pipeline
        │   ├── enterprise/ - Deployment
        │   └── security/ - Security docs
        ├── guides/ - User guides
        └── archive/ - Old docs (kept for reference)
```

---

## ARCHITECTURE OVERVIEW

### Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│ USER'S PC (LocaNext.exe)                                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ LOCAL STORAGE (server/data/):                               │
│ ├─ ldm_tm/{tm_id}/ - FAISS indexes, embeddings, hash        │
│ ├─ outputs/ - Tool outputs                                  │
│ └─ cache/ - Temp files                                      │
│                                                             │
│ LOCAL PROCESSING:                                           │
│ ├─ File parsing                                             │
│ ├─ FAISS index building                                     │
│ ├─ Embedding generation                                     │
│ └─ Model inference                                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                        │
                        │ TEXT DATA (PostgreSQL)
                        │ Real-time sync (WebSocket)
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ CENTRAL POSTGRESQL                                          │
├─────────────────────────────────────────────────────────────┤
│ ├─ LDM: projects, folders, files, rows (ALL text)           │
│ ├─ TM: translation_memories, tm_entries                     │
│ ├─ Users, sessions, auth                                    │
│ ├─ Logs, telemetry                                          │
│ └─ PgBouncer: 1000 connections                              │
└─────────────────────────────────────────────────────────────┘
```

### What Goes Where

| Data Type | Location | Why |
|-----------|----------|-----|
| LDM rows (source/target) | PostgreSQL | Shared, synced |
| TM entries | PostgreSQL | Shared across users |
| Projects, files metadata | PostgreSQL | Shared |
| Users, sessions | PostgreSQL | Centralized |
| Logs, telemetry | PostgreSQL | Admin monitoring |
| FAISS indexes | Local disk | Heavy, rebuildable |
| Embeddings | Local disk | Heavy, rebuildable |
| ML models | Local disk | Large, downloaded once |

---

## THE PLATFORM PATTERN

**This is a PLATFORM for hosting multiple tools**, not just one tool!

```
LocaNext Desktop App
├── Tool 1: XLSTransfer ✅
├── Tool 2: QuickSearch ✅
├── Tool 3: KR Similar ✅
├── Tool 4: LDM (Language Data Manager) 🔄 67%
└── Tool N: ... (scalable to 100+ tools)
```

### Process for Adding Tools:
1. Take monolithic .py script
2. Restructure into clean modules under `server/tools/`
3. Create Svelte component under `locaNext/src/lib/components/apps/`
4. Add API endpoints
5. All text data → PostgreSQL, heavy computation → local

---

## PROJECT STATS (Updated 2025-12-11)

- **Backend**: 100% Complete
- **LocaNext Desktop App**: 100% Complete
- **Admin Dashboard**: 100% Complete
- **LDM Tool**: 67% Complete (Phase 7)
- **Tests**: 912 passing
- **API Endpoints**: 63+
- **Database Tables**: 17
- **Tools**: 4 (XLSTransfer, QuickSearch, KR Similar, LDM)

---

## Related Documentation

- **CLAUDE.md** - Master navigation hub
- **DEPLOYMENT_ARCHITECTURE.md** - Full architecture
- **ADD_NEW_APP_GUIDE.md** - Adding new tools
