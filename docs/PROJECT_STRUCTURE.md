# Project Structure

**Complete File Tree** | **Module Organization** | **Architecture Overview**

---

## 📁 COMPLETE PROJECT TREE

```
LocalizationTools/
│
├── 📋 PROJECT DOCS (READ THESE!)
│   ├── CLAUDE.md ⭐ MASTER NAVIGATION HUB - Start here!
│   ├── Roadmap.md ⭐ Development plan, next steps
│   ├── README.md - User-facing documentation
│   └── docs/ - Detailed documentation (see below)
│
├── 🖥️ SERVER (100% COMPLETE ✅)
│   ├── server/
│   │   ├── main.py ⭐ FastAPI server entry point
│   │   ├── config.py - Server configuration
│   │   ├── api/ - API endpoints
│   │   │   ├── auth_async.py ⭐ Async authentication (7 endpoints)
│   │   │   ├── logs_async.py ⭐ Async logging (7 endpoints)
│   │   │   ├── sessions_async.py ⭐ Async sessions (5 endpoints)
│   │   │   ├── xlstransfer_async.py ⭐ XLSTransfer API endpoints
│   │   │   ├── auth.py - Sync auth (backward compat)
│   │   │   ├── logs.py - Sync logs (backward compat)
│   │   │   ├── sessions.py - Sync sessions (backward compat)
│   │   │   └── schemas.py - Pydantic models
│   │   ├── database/ - Database layer
│   │   │   ├── models.py ⭐ SQLAlchemy models (13 tables)
│   │   │   └── db_setup.py - Database initialization
│   │   ├── data/ ⭐ ALL USER DATA (unified location)
│   │   │   ├── localizationtools.db - SQLite database
│   │   │   ├── logs/ - All server logs
│   │   │   ├── backups/ - Database backups
│   │   │   ├── cache/ - Client cache & temp files
│   │   │   ├── outputs/ - All tool outputs
│   │   │   │   ├── xlstransfer/{date}/ - XLSTransfer outputs
│   │   │   │   ├── quicksearch/{date}/ - QuickSearch outputs
│   │   │   │   └── kr_similar/{date}/ - KR Similar outputs
│   │   │   ├── kr_similar_dictionaries/ - KR Similar dictionaries
│   │   │   ├── quicksearch_dictionaries/ - QuickSearch dictionaries
│   │   │   └── xlstransfer_dictionaries/ - XLSTransfer embeddings
│   │   ├── utils/ - Server utilities
│   │   │   ├── auth.py ⭐ JWT, password hashing
│   │   │   ├── dependencies.py ⭐ Async DB sessions
│   │   │   ├── websocket.py ⭐ Socket.IO real-time events
│   │   │   └── cache.py ⭐ Redis caching (optional)
│   │   ├── middleware/ - Request/response logging
│   │   │   └── logging_middleware.py ⭐ Comprehensive logging
│   │   └── tasks/ - Background jobs (Celery)
│   │       ├── celery_app.py - Celery configuration
│   │       └── background_tasks.py - Scheduled tasks
│   │
│   └── BACKEND STATUS:
│       ✅ Async architecture (10-100x concurrency)
│       ✅ WebSocket real-time updates
│       ✅ Comprehensive request/response logging
│       ✅ Performance tracking
│       ✅ PostgreSQL-ready (SQLite default)
│       ✅ Connection pooling (20+10 overflow)
│       ✅ 17 async tests passing
│
│   │   ├── tools/ ⭐ ALL TOOL BACKENDS (unified)
│   │   │   ├── xlstransfer/ ⭐ TEMPLATE FOR ALL TOOLS
│   │   │   │   ├── core.py (49 functions)
│   │   │   │   ├── embeddings.py (BERT + FAISS)
│   │   │   │   ├── translation.py (matching logic)
│   │   │   │   ├── excel_utils.py (Excel ops)
│   │   │   │   ├── process_operation.py - 5 operations
│   │   │   │   └── cli/ - Command-line interface
│   │   │   ├── quicksearch/ - Dictionary search
│   │   │   └── kr_similar/ - Korean semantic similarity
│   │   ├── config/ - Server configuration
│   │   │   └── client_config.py - Client app settings
│   │   └── STATUS: ✅ COMPLETE - All tool backends unified
│
├── 🖥️ LOCANEXT (ELECTRON DESKTOP APP - COMPLETE ✅)
│   └── locaNext/
│       ├── electron/ - Electron main process
│       │   ├── main.js ⭐ Main process (IPC, file dialogs)
│       │   └── preload.js - Preload script (expose APIs)
│       ├── src/ - Svelte frontend
│       │   ├── routes/
│       │   │   └── +page.svelte - Main app page
│       │   └── lib/
│       │       ├── components/
│       │       │   ├── apps/
│       │       │   │   └── XLSTransfer.svelte ⭐ (17KB - exact replica)
│       │       │   ├── TopBar.svelte - Top menu bar
│       │       │   └── TaskManager.svelte - Task manager sidebar
│       │       └── api/
│       │           ├── client.js - API client
│       │           └── websocket.js - WebSocket service
│       ├── package.json - Electron app dependencies
│       └── STATUS: ✅ COMPLETE - Fully functional desktop app
│
├── 📊 ADMIN DASHBOARD (SVELTEKIT WEB APP - 85% COMPLETE ⏳)
│   └── adminDashboard/
│       ├── src/routes/
│       │   ├── +page.svelte - Dashboard Home
│       │   ├── users/+page.svelte - User Management
│       │   ├── users/[userId]/+page.svelte - User Detail
│       │   ├── activity/+page.svelte - Live Activity Feed
│       │   ├── stats/+page.svelte - Statistics
│       │   └── logs/+page.svelte - Logs Viewer
│       └── src/lib/
│           ├── api/client.js - API client
│           └── api/websocket.js - WebSocket service
│
├── 🧪 TESTS (COMPREHENSIVE ✅)
│   └── tests/
│       ├── test_async_infrastructure.py ⭐ (7 tests - async DB)
│       ├── test_async_auth.py (6 tests - async auth)
│       ├── test_async_sessions.py (4 tests - async sessions)
│       ├── test_utils_logger.py (18 tests - logging)
│       ├── test_utils_progress.py (27 tests - progress)
│       ├── test_utils_file_handler.py (41 tests - files)
│       └── e2e/ - End-to-end tests
│
├── 🛠️ SCRIPTS (SETUP & UTILITIES)
│   └── scripts/
│       ├── create_admin.py ⭐ Create admin user
│       ├── download_models.py - Download AI models
│       ├── setup_environment.py - Environment setup
│       ├── test_admin_login.py - Test authentication
│       ├── check_version_unified.py ⭐ Version consistency check
│       ├── benchmark_server.py - Performance testing
│       └── profile_memory.py - Memory profiling
│
├── 📦 ARCHIVE (REFERENCE ONLY)
│   └── archive/gradio_version/ ⭐ OLD GRADIO UI
│       ├── README.md - Why archived, how to use
│       ├── run_xlstransfer.py - Gradio XLSTransfer launcher
│       ├── run_admin_dashboard.py - Gradio admin launcher
│       ├── client_main_gradio.py - Old client main
│       ├── xlstransfer_ui_gradio.py - XLSTransfer Gradio UI
│       └── admin_dashboard/ - Gradio admin dashboard
│
└── 📚 DOCS (DOCUMENTATION)
    └── docs/
        ├── Core Guides
        │   ├── BUILD_AND_DISTRIBUTION.md ⭐ Build system, versioning
        │   ├── DEPLOYMENT_ARCHITECTURE.md ⭐ Hybrid model explanation
        │   ├── XLSTRANSFER_GUIDE.md ⭐ XLSTransfer complete guide
        │   ├── PROJECT_STRUCTURE.md ⭐ This file
        │   ├── QUICK_START_GUIDE.md ⭐ How to run everything
        │   └── CODING_STANDARDS.md ⭐ Rules, patterns, conventions
        │
        ├── Architecture
        │   ├── BACKEND_PRINCIPLES.md - "Backend is Flawless" principle
        │   ├── PLATFORM_PATTERN.md - Multi-tool platform approach
        │   └── ASYNC_PATTERNS.md - Async architecture patterns
        │
        ├── Development Guides
        │   ├── ADD_NEW_APP_GUIDE.md - Adding new tools
        │   ├── TESTING_GUIDE.md - Testing procedures
        │   ├── LOGGING_PROTOCOL.md - Logging requirements
        │   └── MONITORING_COMPLETE_GUIDE.md - Monitoring system
        │
        ├── Deployment & Operations
        │   ├── DEPLOYMENT.md - Production deployment
        │   ├── ENTERPRISE_DEPLOYMENT.md - Enterprise-scale
        │   ├── POSTGRESQL_SETUP.md - PostgreSQL configuration
        │   └── SECURITY_AND_LOGGING.md - Security practices
        │
        ├── Build & Release
        │   ├── BUILD_TROUBLESHOOTING.md - Debugging builds
        │   ├── BUILD_CHECKLIST.md - Pre-release checklist
        │   └── PACKAGING_GUIDE.md - Electron packaging
        │
        └── Reference
            ├── CLAUDE_AI_WARNINGS.md - AI hallucination prevention
            ├── XLSTransfer_Migration_Audit.md - Migration audit
            ├── BEST_PRACTICES.md - Best practices
            ├── PERFORMANCE.md - Performance optimization
            └── QUICK_TEST_COMMANDS.md - Testing commands
```

---

## 🏛️ ARCHITECTURE OVERVIEW

### The Platform Pattern

**This is a PLATFORM for hosting multiple tools**, not just one tool!

```
LocalizationTools Desktop App
├── Tool 1: XLSTransfer ✅ (COMPLETE - exact replica of original)
│   ├── 10 functions (Create dictionary, Load dictionary, Transfer to Close, etc.)
│   └── Python modules: core.py, embeddings.py, translation.py, excel_utils.py
│   └── Backend scripts: get_sheets.py, load_dictionary.py, process_operation.py, etc.
├── Tool 2: [Your Next Script] 🔜
├── Tool 3: [Another Script] 🔜
└── Tool N: ... (scalable to 100+ tools)
```

### Process for Adding Tools:
1. Take monolithic .py script (1000+ lines)
2. Restructure into clean modules (like XLSTransfer)
3. Integrate into LocaNext (Apps dropdown → one-page GUI)
4. Users run it locally, logs sent to server

---

## 📊 PROJECT STATS (Updated 2025-12-02)

- **Overall Progress**: 96% Complete ✅
- **Backend**: 100% Complete ✅
- **LocaNext Desktop App**: 100% Complete ✅
- **Admin Dashboard**: 85% Complete ⏳
- **Tests**: 450 passing (49% coverage) ✅
- **API Endpoints**: 47+ (async + sync) ✅
- **Database Tables**: 13 ✅
- **Tool Modules**: 3 (XLSTransfer, QuickSearch, KR Similar) ✅
- **Lines of Code**: ~18,000+ (server + client + locaNext + adminDashboard + tests)
- **Data Structure**: Unified under `server/data/` ✅

---

## 📚 Related Documentation

- **CLAUDE.md** - Master navigation hub (start here!)
- **PLATFORM_PATTERN.md** - Platform architecture explanation
- **ADD_NEW_APP_GUIDE.md** - Adding new tools to the platform
