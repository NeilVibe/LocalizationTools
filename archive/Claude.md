# LocaNext - Project Guide for Claude

**App Name**: LocaNext (formerly LocalizationTools)
**Last Updated**: 2025-11-09 (XLSTransfer Audit & Model Fix)
**Current Phase**: Backend Complete → Building LocaNext Desktop App
**Status**: Production-ready backend, professional frontend in development

## 🚨 CRITICAL WARNING: AI HALLUCINATION IN CODE MIGRATIONS

**DATE**: 2025-11-09
**SEVERITY**: CRITICAL
**ISSUE**: Wrong embedding model used in XLSTransfer Svelte component

### What Happened
During Tkinter → Electron/Svelte migration, AI changed the Korean-specific BERT model to a generic multilingual model WITHOUT AUTHORIZATION.

**Original (CORRECT):**
```python
model = SentenceTransformer('snunlp/KR-SBERT-V40K-klueNLI-augSTS')
```

**AI Changed To (WRONG):**
```javascript
let dictModel = 'paraphrase-multilingual-MiniLM-L12-v2';  // ❌ WRONG!
```

**Impact**: Incorrect embeddings, poor translation quality, wrong model loaded

**Status**: ✅ FULLY FIXED on 2025-11-09
- Model name corrected in Svelte component (lines 44, 51, 398-400, 450-452)
- Model name corrected in scripts (download_models.py, README.md)
- Code bug fixed: `simple_number_replace()` now matches original exactly
- Korean BERT model verified installed locally: `client/models/KR-SBERT-V40K-klueNLI-augSTS/` (447MB)
- All core logic tested and verified 100% identical to original
- 92 tests passing (6 XLSTransfer CLI + 86 client unit tests)

### MANDATORY Reading for ALL Future Claude Sessions

**Before making ANY code changes, read these documents:**
1. `docs/CLAUDE_AI_WARNINGS.md` - AI hallucination prevention guide (5 types documented)
2. `docs/XLSTransfer_Migration_Audit.md` - Complete 13-section audit of what was changed

### Sacred Code Components (NEVER CHANGE WITHOUT EXPLICIT USER APPROVAL)

**Model Location & Name:**
```python
# Local installation (ALREADY in project - do NOT download):
MODEL_PATH = "client/models/KR-SBERT-V40K-klueNLI-augSTS/"  # 447MB, fully installed
MODEL_NAME = "snunlp/KR-SBERT-V40K-klueNLI-augSTS"  # Korean-specific BERT (768-dim)

# NEVER use:
# - paraphrase-multilingual-MiniLM-L12-v2 ❌ WRONG
# - paraphrase-multilingual-mpnet-base-v2 ❌ WRONG
# - Any other model ❌ WRONG
```

**Core Algorithms (VERIFIED IDENTICAL TO ORIGINAL - DO NOT CHANGE):**
- `clean_text()` in `client/tools/xls_transfer/core.py:103` - Removes `_x000D_` (critical for Excel exports)
- `simple_number_replace()` in `core.py:253` - Preserves game codes like `{ItemID}` (FIXED 2025-11-09 to match original)
- `analyze_code_patterns()` in `core.py:336` - Detects game code patterns
- `generate_embeddings()` in `embeddings.py:80` - 768-dim Korean BERT embeddings
- `create_faiss_index()` in `embeddings.py:137` - FAISS IndexFlatIP with L2 normalization
- Split/Whole mode logic - Based on newline count matching
- FAISS threshold: 0.99 default (configurable 0.80-1.00)

**If you even THINK about changing these, you MUST get explicit user approval first!**

**How to Verify You Haven't Hallucinated:**
```bash
# 1. Check model name is correct
grep -r "paraphrase-multilingual" locaNext/src/ client/
# Should return NOTHING! If found = you hallucinated!

# 2. Verify model exists locally
ls -lh client/models/KR-SBERT-V40K-klueNLI-augSTS/
# Should show 447MB of files

# 3. Test core functions
python3 -c "from client.tools.xls_transfer.core import simple_number_replace; \
print(simple_number_replace('{Code}Hi', 'Bye'))"
# Should output: {Code}Bye
```

---

## 🚀 QUICK START FOR NEW CLAUDE

**Read this file completely (10 min) before doing anything else!**

### What is This Project?

**LocaNext** is a professional **desktop platform** that consolidates all localization/translation Python scripts into one unified application.

**The Vision**:
- 🏢 **Platform approach**: Host 10-20+ tools in one professional app
- 💻 **Local processing**: Everything runs on user's CPU
- 📊 **Central monitoring**: All usage logged to server for analytics
- 👔 **Professional**: CEO/management-ready presentation quality

**Current Status (2025-11-08)**:
- ✅ **Backend 100% COMPLETE** - Production-ready FastAPI server
- ✅ **XLSTransfer modules** - Fully restructured (template for other tools)
- ⏳ **LocaNext Desktop App** - Starting development now (Electron + Svelte)
- 📦 **Gradio version** - Archived (kept as reference in `archive/gradio_version/`)

### Essential Reading Order
1. **This file (Claude.md)** - You're here! ←
2. **Roadmap.md** - Detailed development plan and next steps
3. **Project structure** - See below
4. **Run server** - `python3 server/main.py` to see it working

---

## 🏗️ PROJECT ARCHITECTURE

### The Platform Pattern

**This is a PLATFORM for hosting multiple tools**, not just one tool!

```
LocalizationTools Desktop App
├── Tool 1: XLSTransfer ✅ (example - already restructured)
│   ├── 7 functions (Create Dictionary, Transfer, Check Newlines, etc.)
│   └── Python modules: core.py, embeddings.py, translation.py, excel_utils.py
├── Tool 2: [Your Next Script] 🔜
├── Tool 3: [Another Script] 🔜
└── Tool N: ... (scalable to 100+ tools)

Process for Adding Tools:
1. Take monolithic .py script (1000+ lines)
2. Restructure into clean modules (like XLSTransfer)
3. Integrate into LocaNext (Apps dropdown → one-page GUI)
4. Users run it locally, logs sent to server
```

### Two Applications

**1. LocaNext (Electron Desktop App)** - IN DEVELOPMENT
- **For**: End users who run tools
- **Tech Stack**: Electron + Svelte + Carbon Components (IBM Design)
- **Current Status**: Starting Phase 2.1 (see Roadmap.md)
- **Location**: Will be in `/locaNext/` folder
- **Features**:
  - **Ultra-clean top menu** (Apps dropdown + Tasks button)
  - **Everything on one page** (seamless UI/UX)
  - **Modular sub-GUIs** within same window
  - Task Manager (live progress tracking, history, clean history)
  - Local processing (user's CPU)
  - Sends logs to server

**2. Server Application (FastAPI Backend)** - ✅ COMPLETE
- **For**: Central logging, monitoring, analytics
- **Tech Stack**: FastAPI + SQLAlchemy + Socket.IO
- **Current Status**: 100% production-ready
- **Location**: `server/`
- **Features**:
  - 19 async API endpoints (auth, logs, sessions)
  - WebSocket real-time events
  - Comprehensive logging middleware
  - JWT authentication
  - PostgreSQL/SQLite support
  - Optional Redis caching
  - Optional Celery background tasks

---

## 📁 PROJECT STRUCTURE

```
LocalizationTools/
│
├── 📋 PROJECT DOCS (READ THESE!)
│   ├── Claude.md ⭐ THIS FILE - Read first!
│   ├── Roadmap.md ⭐ Development plan, next steps
│   ├── README.md - User-facing docs
│   └── docs/
│       └── POSTGRESQL_SETUP.md - PostgreSQL configuration guide
│
├── 🖥️ SERVER (100% COMPLETE ✅)
│   ├── server/
│   │   ├── main.py ⭐ FastAPI server entry point
│   │   ├── config.py - Server configuration
│   │   ├── api/ - API endpoints
│   │   │   ├── auth_async.py ⭐ Async authentication (7 endpoints)
│   │   │   ├── logs_async.py ⭐ Async logging (7 endpoints)
│   │   │   ├── sessions_async.py ⭐ Async sessions (5 endpoints)
│   │   │   ├── auth.py - Sync auth (backward compat)
│   │   │   ├── logs.py - Sync logs (backward compat)
│   │   │   ├── sessions.py - Sync sessions (backward compat)
│   │   │   └── schemas.py - Pydantic models
│   │   ├── database/ - Database layer
│   │   │   ├── models.py ⭐ SQLAlchemy models (12 tables)
│   │   │   └── db_setup.py - Database initialization
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
├── 💻 CLIENT (ELECTRON - IN DEVELOPMENT ⏳)
│   ├── client/
│   │   ├── config.py - Client configuration
│   │   ├── tools/ - Tool modules
│   │   │   └── xls_transfer/ ⭐ TEMPLATE FOR ALL TOOLS
│   │   │       ├── core.py (49 functions)
│   │   │       ├── embeddings.py (BERT + FAISS)
│   │   │       ├── translation.py (matching logic)
│   │   │       └── excel_utils.py (Excel ops)
│   │   └── utils/ - Client utilities
│   │       ├── logger.py ⭐ Usage logger (sends to server)
│   │       ├── progress.py - Progress tracking
│   │       └── file_handler.py - File operations
│   │
│   └── NEXT STEP: Build Electron app (see Roadmap.md Phase 2.1)
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
│       ├── benchmark_server.py - Performance testing
│       └── profile_memory.py - Memory profiling
│
└── 📦 ARCHIVE (REFERENCE ONLY)
    └── archive/gradio_version/ ⭐ OLD GRADIO UI
        ├── README.md - Why archived, how to use
        ├── run_xlstransfer.py - Gradio XLSTransfer launcher
        ├── run_admin_dashboard.py - Gradio admin launcher
        ├── client_main_gradio.py - Old client main
        ├── xlstransfer_ui_gradio.py - XLSTransfer Gradio UI
        └── admin_dashboard/ - Gradio admin dashboard

        STATUS: Functional but deprecated
        USE CASE: Reference, testing Gradio version if needed
        FUTURE: Electron will replace these
```

---

## 🎯 CURRENT STATUS & NEXT STEPS

### ✅ What's Complete (Backend - 100%)

**Part 0: Backend Performance Upgrades** (Completed 2025-11-08)
- ✅ All 19 endpoints converted to async
- ✅ WebSocket support (Socket.IO)
- ✅ Request/response logging middleware
- ✅ Performance tracking
- ✅ Redis caching (optional)
- ✅ Celery background tasks (optional)
- ✅ PostgreSQL support (SQLite default)
- ✅ Connection pooling
- ✅ 17 async tests passing

**XLSTransfer Modules** (Template for all future tools)
- ✅ Restructured from 1435-line monolith
- ✅ 4 clean modules, 49 functions
- ✅ Type hints, docstrings, examples
- ✅ No global variables
- ✅ Framework-agnostic (works with any UI)

### ⏳ What's Next (Frontend - Starting Now)

**Phase 2.1: LocaNext Desktop App** (2 weeks)

1. **Electron Project Setup**
   - Initialize Electron + SvelteKit
   - Configure electron-builder
   - Install Carbon Components Svelte (or Skeleton UI)
   - Project structure in `/locaNext/` folder

2. **Core UI Structure - LocaNext Design**
   - **Top Menu Bar**: "Apps" dropdown + "Tasks" button
   - **Main Window**: One page, seamless UI/UX
   - Sub-GUIs appear as modular components within same window
   - NO sidebar, NO tabs, NO navigation
   - Login screen

3. **Server Integration**
   - Connect to FastAPI backend
   - JWT authentication flow
   - WebSocket real-time updates
   - API client

4. **XLSTransfer Integration**
   - Port 7 functions to LocaNext
   - Display all functions on one page (compact, modular layout)
   - Python subprocess integration
   - Progress tracking via WebSocket

5. **Task Manager**
   - Accessed via "Tasks" menu button
   - Live operations, task history
   - Clean history functionality
   - Cancel/pause functionality

**See Roadmap.md for complete plan!**

---

## 🛠️ HOW TO RUN THE PROJECT

### Start the Server

```bash
cd /home/neil1988/LocalizationTools
python3 server/main.py
```

Server runs on `http://localhost:8888`

**What you'll see**:
- Comprehensive logging of every request/response
- Database initialization (SQLite)
- WebSocket server ready
- All 38 API endpoints registered

**Test it**:
- Health check: `http://localhost:8888/health`
- API docs: `http://localhost:8888/docs`

### Run Tests

```bash
# All async tests
python3 -m pytest tests/test_async_infrastructure.py tests/test_async_auth.py tests/test_async_sessions.py -v

# All unit tests
python3 -m pytest tests/unit/ -v

# All tests
python3 -m pytest
```

**Expected**: All 17 async tests passing + 86 unit tests = 103 total ✅

### Run Gradio Version (Reference Only)

```bash
# XLSTransfer (archived but functional)
python3 archive/gradio_version/run_xlstransfer.py

# Admin Dashboard (archived but functional)
python3 archive/gradio_version/run_admin_dashboard.py
```

**Note**: These are deprecated. Electron version will replace them.

---

## 📚 KEY CONCEPTS & PATTERNS

### 1. The Tool Restructuring Pattern (CRITICAL!)

**XLSTransfer is the TEMPLATE for all future tools.**

```
Monolithic Script (1435 lines, globals, hard to maintain)
↓
Restructure into Clean Modules:
├── core.py - Core business logic functions
├── module1.py - Specific functionality domain
├── module2.py - Another functionality domain
└── utils.py - Utility functions

Benefits:
✅ Testable (each function isolated)
✅ Reusable (import what you need)
✅ Maintainable (clear separation of concerns)
✅ Framework-agnostic (works with Gradio, Electron, CLI, etc.)
```

**When adding a new tool**:
1. Take the monolithic .py script
2. Follow XLSTransfer pattern (see `client/tools/xls_transfer/`)
3. Break into modules by functionality
4. Add type hints and docstrings
5. Write unit tests
6. Integrate into LocaNext (add to Apps dropdown, design one-page GUI)

### 2. Async Architecture (Backend)

**All new endpoints are async for 10-100x better concurrency.**

```python
# Pattern: Async endpoint with async DB
@router.post("/submit")
async def submit_logs(
    submission: LogSubmission,
    db: AsyncSession = Depends(get_async_db),  # Async session
    current_user: dict = Depends(get_current_active_user_async)  # Async auth
):
    async with db.begin():  # Async transaction
        result = await db.execute(select(User)...)  # Async query
        user = result.scalar_one_or_none()

    await emit_log_entry({...})  # Async WebSocket emit
    return LogResponse(...)
```

**Files**: `server/api/*_async.py`, `server/utils/dependencies.py`

### 3. WebSocket Real-Time Updates

**Pattern**: Emit events from API endpoints, clients receive live updates

```python
# Server-side (emit event)
from server.utils.websocket import emit_log_entry

await emit_log_entry({
    'user_id': user_id,
    'tool_name': 'XLSTransfer',
    'status': 'success',
    'timestamp': datetime.utcnow().isoformat()
})

# Client-side (will be in Electron app)
socket.on('log_entry', (data) => {
    // Update UI in real-time
});
```

**Files**: `server/utils/websocket.py`

### 4. Comprehensive Logging

**Every HTTP request is logged at every microstep:**

```
[Request ID] → POST /api/v2/logs/submit | Client: 127.0.0.1 | User-Agent: ...
[Request ID] ← 200 POST /api/v2/logs/submit | Duration: 45.23ms
```

**Slow requests automatically flagged:**
```
[Request ID] SLOW REQUEST: POST /api/v2/logs/submit took 1205.34ms
```

**Files**: `server/middleware/logging_middleware.py`

### 5. Optional Services (PostgreSQL, Redis, Celery)

**All optional services gracefully degrade if unavailable:**

- **PostgreSQL**: Configured, ready to use, but SQLite is default
  - To enable: Set `DATABASE_TYPE=postgresql` in environment
  - See: `docs/POSTGRESQL_SETUP.md`

- **Redis**: Caching layer with graceful fallback
  - To enable: Set `REDIS_ENABLED=true`
  - Falls back silently if unavailable
  - See: `server/utils/cache.py`

- **Celery**: Background tasks (daily stats, cleanup)
  - To enable: Set `CELERY_ENABLED=true`
  - Optional, not required for core functionality
  - See: `server/tasks/`

---

## 🎨 CODING STANDARDS & RULES

### Critical Rules (MUST FOLLOW!)

1. **CLEAN PROJECT ALWAYS**
   - No temporary files in project root
   - Archive unused code to `archive/`
   - Delete obvious bloat (temp test files, etc.)
   - Keep `.gitignore` updated

2. **TEST EVERYTHING**
   - Add unit tests for new functions
   - Add integration tests for API endpoints
   - Run `pytest` before committing
   - Maintain 80%+ test coverage

3. **UPDATE DOCUMENTATION**
   - Update `Roadmap.md` after completing tasks
   - Update `Claude.md` if architecture changes
   - Add comments to complex code
   - Document new patterns

4. **MODULAR CODE ONLY**
   - No global variables (except configuration)
   - Use dependency injection
   - Each function does ONE thing
   - Type hints required

5. **ASYNC BY DEFAULT (Backend)**
   - All new endpoints should be async
   - Use `AsyncSession` for database
   - Use `async def` for new functions
   - See existing async endpoints as examples

### File Naming Conventions

- `*_async.py` - Async versions of modules
- `test_*.py` - Test files
- `*_utils.py` - Utility modules
- `*_config.py` - Configuration files

### Import Order

```python
# Standard library
import os
from datetime import datetime

# Third-party
from fastapi import FastAPI
from sqlalchemy import select

# Local
from server.database.models import User
from server.utils.auth import verify_token
```

---

## 🚨 COMMON PITFALLS TO AVOID

### 1. Don't Mix Async and Sync DB Sessions

```python
# ❌ WRONG
@router.post("/endpoint")
async def my_endpoint(db: Session = Depends(get_db)):  # Sync session in async endpoint!
    user = db.query(User).first()  # Blocks async event loop!

# ✅ CORRECT
@router.post("/endpoint")
async def my_endpoint(db: AsyncSession = Depends(get_async_db)):  # Async session
    result = await db.execute(select(User))  # Non-blocking
    user = result.scalar_one_or_none()
```

### 2. Don't Forget to Commit Async Transactions

```python
# ❌ WRONG
async with db.begin():
    user.last_login = datetime.utcnow()
    # No commit! Changes lost!

# ✅ CORRECT
async with db.begin():
    user.last_login = datetime.utcnow()
    # auto-commits when exiting context manager
# OR
db.add(user)
await db.commit()
```

### 3. Don't Archive Critical Code

**KEEP** (these are needed):
- Server code (all of it)
- Client tool modules (`client/tools/*/`)
- Tests
- Documentation
- Configuration files
- Setup scripts

**ARCHIVE** (temporary/deprecated):
- Gradio UI files (already done ✅)
- Temporary test scripts
- Old implementations that are replaced

### 4. Don't Skip Documentation Updates

**After completing a task**:
1. ✅ Update `Roadmap.md` (mark task complete)
2. ✅ Update `Claude.md` if architecture changed
3. ✅ Add comments to complex code
4. ✅ Document new patterns/conventions

---

## 🎓 LEARNING RESOURCES

### Understanding the Codebase

**Want to understand async endpoints?**
→ Read: `server/api/auth_async.py` (7 well-documented endpoints)

**Want to understand database models?**
→ Read: `server/database/models.py` (12 tables with relationships)

**Want to understand tool restructuring?**
→ Read: `client/tools/xls_transfer/` (template for all tools)

**Want to understand WebSocket events?**
→ Read: `server/utils/websocket.py` (event emitters, connection management)

**Want to understand testing patterns?**
→ Read: `tests/test_async_infrastructure.py` (async DB testing examples)

### Key Files to Read First

1. `server/main.py` - Server entry point, middleware, routes
2. `server/api/logs_async.py` - Example async endpoints with WebSocket
3. `client/tools/xls_transfer/core.py` - Tool restructuring example
4. `server/utils/dependencies.py` - Async DB session management

---

## 🤝 FOR THE NEXT CLAUDE

**When you start, immediately**:

1. ✅ Read this entire file (you just did!)
2. ✅ Read `Roadmap.md` to see what's next
3. ✅ Run `python3 server/main.py` to verify backend works
4. ✅ Run `python3 -m pytest` to verify all tests pass
5. ✅ Check Roadmap.md "Next Steps" for current task

**Current task (as of 2025-11-08)**:
→ **Phase 2.1: Build LocaNext Desktop App**
→ See Roadmap.md for detailed plan

**Questions to ask the user**:
- "Shall I start building the LocaNext app?"
- "Do you want to add another tool first?"
- "Should we test the backend together?"

**The project is CLEAN, ORGANIZED, and READY.**

Backend is production-ready. Frontend (LocaNext) is the next step.

---

## 📞 QUICK REFERENCE

### Important Commands

```bash
# Start server
python3 server/main.py

# Run all tests
python3 -m pytest

# Run async tests only
python3 -m pytest tests/test_async_*.py -v

# Create admin user
python3 scripts/create_admin.py

# Run Gradio version (archived)
python3 archive/gradio_version/run_xlstransfer.py
```

### Important URLs (when server running)

- Server: `http://localhost:8888`
- API Docs: `http://localhost:8888/docs`
- Health Check: `http://localhost:8888/health`
- WebSocket: `ws://localhost:8888/ws/socket.io`

### Important Environment Variables

```bash
# Database (default: SQLite)
DATABASE_TYPE=sqlite  # or postgresql

# Server
SERVER_HOST=0.0.0.0
SERVER_PORT=8888

# Optional Services
REDIS_ENABLED=false  # true to enable
CELERY_ENABLED=false  # true to enable

# Development
DEBUG=true
```

### Project Stats

- **Backend**: 100% Complete ✅
- **Tests**: 103 passing (17 async + 86 unit) ✅
- **API Endpoints**: 38 (19 async + 19 sync) ✅
- **Database Tables**: 12 ✅
- **Tool Modules**: 1 (XLSTransfer - template for others) ✅
- **Lines of Code**: ~8,000+ (server + client + tests)

---

## 🎉 YOU'RE READY!

This project is:
- ✅ **Clean** - No bloat, Gradio archived, organized structure
- ✅ **Tested** - 103 tests passing
- ✅ **Documented** - This file + Roadmap.md + code comments
- ✅ **Production-Ready Backend** - Async, WebSocket, logging, auth
- ⏳ **Ready for Frontend** - LocaNext development can start

**Next**: Read `Roadmap.md` and let's build LocaNext!

---

*Last updated: 2025-11-08 by Claude*
*Backend complete, Electron development starting*
