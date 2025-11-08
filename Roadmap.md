# LocalizationTools - Development Roadmap

**Last Updated**: 2025-01-08
**Current Phase**: Phase 1 - Foundation & MVP → **MAJOR ARCHITECTURAL PIVOT TO ELECTRON**
**Overall Progress**: 60% Backend Complete → **Frontend needs complete rebuild with Electron**

---

## ⚠️ **MAJOR CHANGE - ARCHITECTURAL PIVOT** ⚠️

**Decision Date**: 2025-01-08
**Reason**: Gradio is not professional enough for management presentations

### Why the Change?

**Gradio Limitations**:
- ❌ Not visually impressive for CEOs/management
- ❌ Tab-based UI doesn't scale (can't have 100 tabs for 100 functions)
- ❌ Limited UI/UX customization
- ❌ No compact, centralized layout
- ❌ No sub-windows, modals, nested GUI structure
- ❌ Not suitable for professional product presentation

**New Direction: Electron Desktop App**:
- ✅ Professional, native-looking desktop application
- ✅ Inspired by successful WebTranslator project
- ✅ Compact, centralized UI with sub-windows and modals
- ✅ Real-time updates via WebSocket (1-second polling)
- ✅ Beautiful, management-ready presentation
- ✅ Scalable UI for many functions without tabs
- ✅ Click on users to see their live processes
- ✅ Comprehensive logging console with live updates

### New Tech Stack

**Frontend (Electron App)**:
```
Desktop Application
├── Electron (v36.4.0+)
├── Svelte + SvelteKit + TypeScript - Lightweight, fast, easy to maintain
├── Carbon Components Svelte - Professional IBM Design System
│   OR Skeleton UI - Modern Tailwind-based components
├── Chart.js or Apache ECharts - Data visualization
├── Socket.io-client - Real-time WebSocket communication
└── electron-builder - Cross-platform builds (Windows/Mac/Linux)
```

**Backend (Keep existing)**:
```
FastAPI Server (Already built ✓)
├── SQLAlchemy ORM (SQLite/PostgreSQL) ✓
├── FastAPI endpoints (27 routes) ✓
├── WebSocket support (for live updates) - TO ADD
├── JWT authentication ✓
└── Logging system ✓
```

**Frontend Framework Decision**:

**CHOSEN: Svelte + SvelteKit + Carbon Components**

**Why Svelte over React?**
1. ✅ **Lighter**: 3KB vs React's 145KB (React + React-DOM)
2. ✅ **Simpler**: No hooks complexity (useState, useEffect, etc.)
3. ✅ **Faster**: Compiles to vanilla JS, no virtual DOM overhead
4. ✅ **Cleaner Code**: Less boilerplate, more readable
5. ✅ **Built-in Animations**: No need for heavy libraries
6. ✅ **Better Performance**: Smaller bundle, faster load times
7. ✅ **Professional**: Used in Obsidian (popular Electron app)
8. ✅ **Easier to Maintain**: Simpler syntax, less code to manage

**Comparison**:
```
React:  const [count, setCount] = useState(0);
        useEffect(() => {...}, [count]);

Svelte: let count = 0;
        $: console.log(count);  // Auto-reactive!
```

**UI Component Library**: Carbon Components Svelte (IBM Design System)
- Professional, enterprise-ready
- Similar aesthetics to Ant Design
- Dark mode built-in
- Comprehensive components (tables, modals, forms, charts)

---

## 🎯 Current Status

### ✅ Completed
- **1.1 Project Setup** (Day 1) ✓
  - Project structure created (120+ files)
  - Database schema designed (13 tables)
  - Documentation complete (Claude.md, README.md, STATS_DASHBOARD_SPEC.md)
  - Git repository initialized and pushed to GitHub
  - Configuration files created (client/server)
  - Setup scripts created (download_models.py, setup_environment.py)

- **1.3 Implement Local Processing & Logging** (Day 2) ✓
  - ✓ Logger utility complete (sends logs to server)
  - ✓ Progress tracking utility complete
  - ✓ File handling utilities complete
  - ✓ All utilities fully tested (86 unit tests, 100% passing)

- **Testing Framework** (Day 2) ✓
  - ✓ pytest configuration with coverage requirements (80% minimum)
  - ✓ Comprehensive test documentation (tests/README.md)
  - ✓ Shared fixtures and test utilities (tests/conftest.py)
  - ✓ Unit tests for all utility modules (86 tests):
    - test_utils_logger.py (18 tests - session management, logging, queueing)
    - test_utils_progress.py (27 tests - progress tracking, Gradio integration)
    - test_utils_file_handler.py (41 tests - file operations, validation, temp files)
  - ✓ All tests passing successfully
  - ✓ Test structure organized (unit/integration/e2e directories)

- **XLSTransfer Refactoring** (Day 2-3) ✓
  - ✓ Extracted 1435-line monolithic script into 4 clean modules
  - ✓ core.py (15 functions): Text processing, column conversion, code patterns
  - ✓ embeddings.py (13 functions): Model loading, embedding generation, FAISS
  - ✓ translation.py (10 functions + class): Matching logic, statistics
  - ✓ excel_utils.py (11 functions): Excel file operations
  - ✓ Total: 49 functions with type hints, docstrings, examples
  - ✓ No global variables, clean modular architecture
  - ✓ Logging integration with loguru
  - ✓ Ready for Gradio UI implementation

- **1.2 Build XLSTransfer Gradio Interface** (Day 3-4) ✓
  - ✓ Created utility modules (logger, progress, file_handler)
  - ✓ Refactored XLSTransfer into clean modules
  - ✓ Built complete Gradio UI (ui.py, 730+ lines)
  - ✓ 7 tabs with all major functions implemented:
    - Create Dictionary (build translation dictionaries from Excel)
    - Load Dictionary (load existing dictionaries)
    - Transfer to Excel (AI-powered translation transfer)
    - Check Newlines (find newline mismatches)
    - Combine Excel (merge multiple Excel files)
    - Newline Auto Adapt (auto-fix newline mismatches)
    - Simple Transfer (basic translation mode)
  - ✓ Full integration with refactored modules
  - ✓ Logging for all operations
  - ✓ Progress tracking with Gradio.Progress
  - ✓ Standalone launcher (run_xlstransfer.py)

- **1.4 Database Setup** (Day 4) ✓
  - ✓ SQLAlchemy models created (12 tables matching schema)
  - ✓ Database setup script (supports SQLite + PostgreSQL)
  - ✓ Connection testing and table creation verified
  - ✓ Helper functions for session management
  - ✓ Clean exports in database/__init__.py
  - ✓ Tested successfully - all 12 tables created

- **1.5 Central Logging Server** (Day 5) ✓
  - ✓ FastAPI server with complete API architecture
  - ✓ Authentication endpoints (login, register, user management)
  - ✓ Log submission endpoints (batch logs, error reports)
  - ✓ Session management endpoints (start, heartbeat, end)
  - ✓ Server utilities (auth, dependencies, JWT tokens)
  - ✓ Pydantic schemas for all requests/responses
  - ✓ 27 API routes registered and tested
  - ✓ Health check endpoint with database verification
  - ✓ CORS middleware configured
  - ✓ Complete logging infrastructure

- **1.6 Admin Dashboard** (Day 6) ✓
  - ✓ Gradio admin interface created (5 tabs)
  - ✓ Overview tab: Real-time statistics, KPIs, dashboard overview
  - ✓ Logs tab: Recent activity logs with filtering
  - ✓ Users tab: User management and statistics
  - ✓ Errors tab: Error log viewing and monitoring
  - ✓ Settings tab: Server configuration display
  - ✓ Standalone launcher (run_admin_dashboard.py)
  - ✓ Complete data visualization with pandas DataFrames
  - ✓ Refresh buttons for live data updates

- **1.7 Admin User & Authentication** (Day 7) ✓
  - ✓ Admin initialization script (scripts/create_admin.py)
  - ✓ Default admin user created (username: admin, role: superadmin)
  - ✓ Initial app version record created
  - ✓ Login test script (scripts/test_admin_login.py)
  - ✓ Password verification tested (bcrypt)
  - ✓ JWT token creation and verification tested
  - ✓ Complete authentication flow verified
  - ✓ Admin setup documentation (ADMIN_SETUP.md)
  - ✓ All tests passing (100%)

## 🎉 MVP CORE COMPLETE!

**What's Working:**
- ✅ XLSTransfer tool with full Gradio UI (7 functions)
- ✅ Database layer (12 tables, SQLite active, PostgreSQL support ready)
- ✅ FastAPI logging server (27 API routes)
- ✅ Admin dashboard (5 tabs with real-time stats)
- ✅ User authentication (JWT, bcrypt)
- ✅ Admin user initialized and tested
- ✅ 86 unit tests (100% passing)
- ✅ Clean, organized codebase

- **1.8 Integration Testing** (Day 8) ✓
  - ✓ Server startup tests (8 tests - all routes verified)
  - ✓ API endpoint integration tests (comprehensive coverage)
  - ✓ Authentication flow tested (login, tokens, permissions)
  - ✓ Log submission tested (with/without auth)
  - ✓ Session management tested (start, heartbeat, end)
  - ✓ Complete testing documentation (TESTING.md)
  - ✓ Claude.md updated with comprehensive navigation guide
  - ✓ **Total: 94 tests (100% PASSING ✅)**
  - ✓ **Execution time: ~4 seconds**

## 🎊 MILESTONE: MVP FULLY TESTED & DOCUMENTED!

**Current State:**
- ✅ 94 tests passing (86 unit + 8 integration)
- ✅ Comprehensive documentation for future developers
- ✅ Clean, organized codebase (0 temp files)
- ✅ Complete navigation guide in Claude.md
- ✅ All core features working and verified
- ✅ Admin authentication tested and working
- ✅ Database layer tested and operational
- ✅ Server API fully functional (27 routes)

- **1.9 Performance Optimization** (Day 9) ✓
  - ✓ Created performance benchmarking tool (scripts/benchmark_server.py)
  - ✓ Created memory profiling tool (scripts/profile_memory.py)
  - ✓ Ran memory profiler: Database operations ~27 MB (excellent!)
  - ✓ Created comprehensive performance documentation (PERFORMANCE.md)
  - ✓ Documented optimization strategies and performance targets
  - ✓ Performance baseline established for future monitoring

## 🚀 MILESTONE: MVP OPTIMIZED & BENCHMARKED!

**Performance Metrics:**
- ✅ Database memory usage: ~27 MB (lightweight footprint)
- ✅ Benchmarking tools ready for ongoing monitoring
- ✅ Performance targets documented (<50ms health check)
- ✅ Optimization strategies in place (connection pooling, query optimization)
- ✅ Future optimization roadmap (caching, async processing)

- **1.10 End-to-End Testing** (Day 10) ✓
  - ✓ Created comprehensive E2E test suite (8 tests)
  - ✓ Database initialization and workflow verification
  - ✓ User authentication and session lifecycle testing
  - ✓ Log submission and statistics calculation testing
  - ✓ Error tracking and performance metrics verification
  - ✓ Server integration tests (3 tests with live server)
  - ✓ Fixed integration test assertions
  - ✓ All 117 tests PASSING with live server (0 skipped, 0 failed!)

## 🎊 MILESTONE: MVP FULLY TESTED & VERIFIED!

**Test Suite Status:**
- ✅ **117 tests PASSING** (100% pass rate!)
- ✅ Unit tests: 86 (client utilities)
- ✅ Integration tests: 20 (server + API)
- ✅ E2E tests: 8 (full workflow)
- ✅ Server integration: 3 (with live server)
- ✅ Execution time: ~80 seconds
- ✅ Complete stack verification (database → API → server)
- ✅ All authentication flows tested
- ✅ All database operations verified
- ✅ Error handling tested
- ✅ Performance metrics validated

## 🎯 READY FOR USER TESTING!

**You can now test the complete system!**

**Quick Start - 3 Terminals:**
```bash
# Terminal 1: Start the logging server (port 8888)
python3 server/main.py

# Terminal 2: Open the Admin Dashboard (port 8885)
python3 run_admin_dashboard.py

# Terminal 3: Use the XLSTransfer tool (port 7860)
python3 run_xlstransfer.py
```

**What to expect:**
1. ✅ **XLSTransfer Tool** - Opens at http://localhost:7860
   - Use any function (Create Dictionary, Transfer, etc.)
   - Processing happens on YOUR local CPU
   - Logs sent to server automatically

2. ✅ **Admin Dashboard** - Opens at http://localhost:8885
   - See beautiful statistics in real-time
   - 5 tabs: Overview, Logs, Users, Errors, Settings
   - Click "Refresh Data" to see updates
   - All stats nicely organized and presented!

3. ✅ **Logging Server** - Runs on port 8888
   - Receives logs from tools
   - Stores in database
   - Provides API for dashboard

**See TESTING_GUIDE.md for complete testing instructions!**

### ⏳ In Progress
- User testing and feedback
- Model download fixed (Korean SBERT now working locally)

### 📋 Next Up - Phase 1.11: Build Electron Desktop Application

**COMPLETE FRONTEND REBUILD - Professional Desktop App**

---

## **Part 0: Backend Performance & Real-Time Enhancements** ⚡

**CRITICAL: Upgrade backend for production-grade performance**

**Time**: 2-3 days (do this FIRST before frontend!)

### **What's Wrong with Current Backend:**
- ❌ All endpoints are **synchronous** (blocking) - should be async
- ❌ No WebSocket support - can't push real-time updates
- ❌ SQLite in use - PostgreSQL ready but not configured
- ❌ No background task queue - heavy stats calculated on request
- ❌ No caching - stats recalculated every time
- ❌ No connection pooling - inefficient database access

---

### **Backend Improvements to Make:**

#### **1. Convert ALL Endpoints to Async** (6 hours)
**Current (BAD - Blocking)**:
```python
@router.post("/logs")
def submit_logs(data: LogBatchCreate, db: Session = Depends(get_db)):
    # Blocking database call - holds up other requests!
    for entry in data.logs:
        db_log = LogEntry(**entry.dict())
        db.add(db_log)
    db.commit()
    return {"status": "success"}
```

**Fixed (GOOD - Non-blocking)**:
```python
@router.post("/logs")
async def submit_logs(data: LogBatchCreate, db: AsyncSession = Depends(get_async_db)):
    # Non-blocking - handles 1000s of requests concurrently!
    async with db.begin():
        for entry in data.logs:
            db_log = LogEntry(**entry.dict())
            db.add(db_log)
        await db.commit()
    return {"status": "success"}
```

**Files to Update**:
- [ ] `server/api/logs.py` - All log endpoints (7 endpoints)
- [ ] `server/api/sessions.py` - All session endpoints (5 endpoints)
- [ ] `server/api/auth.py` - All auth endpoints (7 endpoints)
- [ ] `server/utils/dependencies.py` - Add `get_async_db` dependency

**Benefits**:
- ✅ 10-100x more concurrent requests
- ✅ Non-blocking I/O - server stays responsive
- ✅ Proper use of FastAPI's async capabilities

---

#### **2. Add WebSocket Support with python-socketio** (1 day)
**Install**:
```bash
pip install python-socketio python-socketio[asyncio]
```

**Implementation**:
```python
# server/websocket.py
import socketio
from fastapi import FastAPI

# Create Socket.IO server
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*',
    logger=True,
    engineio_logger=True
)

# Wrap with ASGI
sio_app = socketio.ASGIApp(sio)

@sio.event
async def connect(sid, environ):
    print(f"Client {sid} connected")
    await sio.emit('welcome', {'message': 'Connected to server'}, to=sid)

@sio.event
async def disconnect(sid):
    print(f"Client {sid} disconnected")

# Broadcast functions (called from API endpoints)
async def broadcast_operation_started(user_id, operation_data):
    await sio.emit('operation_started', operation_data, room='admin')

async def broadcast_operation_progress(user_id, progress_data):
    await sio.emit('operation_progress', progress_data, room=f'user_{user_id}')

async def broadcast_operation_completed(user_id, result_data):
    await sio.emit('operation_completed', result_data, room='admin')
    await sio.emit('operation_completed', result_data, room=f'user_{user_id}')

# Mount to FastAPI app
# In server/main.py:
app.mount('/ws', sio_app)
```

**Usage in Log Endpoint**:
```python
from server.websocket import broadcast_operation_started, broadcast_operation_progress

@router.post("/logs")
async def submit_logs(data: LogBatchCreate, db: AsyncSession = Depends(get_async_db)):
    # Broadcast to connected clients
    await broadcast_operation_started(data.user_id, {
        'user': data.username,
        'tool': data.tool_name,
        'function': data.function_name
    })

    # Process logs...

    await broadcast_operation_completed(data.user_id, result)
    return {"status": "success"}
```

**Benefits**:
- ✅ Real-time updates to all connected clients
- ✅ Rooms for targeted broadcasts (per-user, admin-only)
- ✅ Bidirectional communication
- ✅ Automatic reconnection handling

---

#### **3. Switch to PostgreSQL with Connection Pooling** (4 hours)
**Install**:
```bash
pip install asyncpg  # Async PostgreSQL driver
```

**Configuration** (`server/config.py`):
```python
# Database settings
DATABASE_TYPE = os.getenv("DATABASE_TYPE", "postgresql")  # Change default!

# PostgreSQL connection pool settings
POSTGRES_POOL_SIZE = int(os.getenv("POSTGRES_POOL_SIZE", "20"))
POSTGRES_MAX_OVERFLOW = int(os.getenv("POSTGRES_MAX_OVERFLOW", "10"))
POSTGRES_POOL_TIMEOUT = int(os.getenv("POSTGRES_POOL_TIMEOUT", "30"))
POSTGRES_POOL_RECYCLE = int(os.getenv("POSTGRES_POOL_RECYCLE", "3600"))
```

**Database Setup** (`server/database/db_setup.py`):
```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# Create async engine with connection pooling
async_engine = create_async_engine(
    DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    pool_size=POSTGRES_POOL_SIZE,
    max_overflow=POSTGRES_MAX_OVERFLOW,
    pool_timeout=POSTGRES_POOL_TIMEOUT,
    pool_recycle=POSTGRES_POOL_RECYCLE,
    echo=False,  # Set to True for debugging
    future=True
)

# Create async session maker
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_async_db():
    """Async database dependency for FastAPI."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
```

**Benefits**:
- ✅ **Connection pooling** - Reuse connections (10-50x faster)
- ✅ **Async queries** - Non-blocking database access
- ✅ **Production-ready** - Handles 100+ concurrent users
- ✅ **Auto-reconnect** - Handles network issues gracefully

---

#### **4. Add Redis Caching for Stats** (4 hours)
**Install**:
```bash
pip install redis aioredis
```

**Setup** (`server/utils/cache.py`):
```python
import aioredis
import json
from datetime import timedelta

# Redis connection
redis = None

async def init_redis():
    global redis
    redis = await aioredis.from_url(
        "redis://localhost:6379",
        encoding="utf-8",
        decode_responses=True
    )

async def cache_get(key: str):
    """Get cached value."""
    if not redis:
        return None
    value = await redis.get(key)
    return json.loads(value) if value else None

async def cache_set(key: str, value: any, expire: int = 300):
    """Set cached value with expiration (default 5 min)."""
    if redis:
        await redis.setex(key, expire, json.dumps(value))

async def cache_delete(key: str):
    """Delete cached value."""
    if redis:
        await redis.delete(key)
```

**Usage**:
```python
from server.utils.cache import cache_get, cache_set

@router.get("/stats/overview")
async def get_stats_overview(db: AsyncSession = Depends(get_async_db)):
    # Try cache first
    cached = await cache_get("stats:overview")
    if cached:
        return cached

    # Calculate stats (expensive query)
    stats = await calculate_overview_stats(db)

    # Cache for 5 minutes
    await cache_set("stats:overview", stats, expire=300)

    return stats
```

**What to Cache**:
- ✅ Overview stats (refresh every 5 min)
- ✅ Tool usage stats (refresh every 10 min)
- ✅ User lists (refresh when user added/removed)
- ✅ Recent logs (refresh every 30 sec)

**Benefits**:
- ✅ **100x faster** stats queries (from cache, not DB)
- ✅ Reduces database load
- ✅ Dashboard stays snappy even with 1000s of logs

---

#### **5. Add Celery for Background Tasks** (1 day)
**Install**:
```bash
pip install celery redis
```

**Setup** (`server/tasks/celery_app.py`):
```python
from celery import Celery

celery_app = Celery(
    'localizationtools',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/0'
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)
```

**Background Tasks** (`server/tasks/stats_tasks.py`):
```python
from server.tasks.celery_app import celery_app
from server.database.db_setup import AsyncSessionLocal
from server.utils.cache import cache_set

@celery_app.task
async def calculate_daily_stats():
    """Calculate daily stats in background (runs every hour)."""
    async with AsyncSessionLocal() as db:
        # Calculate expensive stats
        daily_stats = await compute_daily_aggregates(db)

        # Update cache
        await cache_set("stats:daily", daily_stats, expire=3600)

        # Store in materialized view
        await update_daily_stats_view(db, daily_stats)

@celery_app.task
async def cleanup_old_logs():
    """Delete logs older than 90 days (runs daily)."""
    async with AsyncSessionLocal() as db:
        await db.execute(
            "DELETE FROM log_entries WHERE timestamp < NOW() - INTERVAL '90 days'"
        )
        await db.commit()
```

**Schedule Tasks** (`server/tasks/celerybeat_schedule.py`):
```python
from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    'calculate-daily-stats': {
        'task': 'server.tasks.stats_tasks.calculate_daily_stats',
        'schedule': crontab(minute=0),  # Every hour
    },
    'cleanup-old-logs': {
        'task': 'server.tasks.stats_tasks.cleanup_old_logs',
        'schedule': crontab(hour=2, minute=0),  # 2 AM daily
    },
}
```

**Run Celery Worker**:
```bash
# Terminal 1: Start Celery worker
celery -A server.tasks.celery_app worker --loglevel=info

# Terminal 2: Start Celery beat (scheduler)
celery -A server.tasks.celery_app beat --loglevel=info
```

**Benefits**:
- ✅ Heavy stats calculated in background (doesn't block API)
- ✅ Scheduled maintenance tasks (cleanup, aggregations)
- ✅ Can retry failed tasks automatically
- ✅ Scales horizontally (add more workers)

---

### **Summary: Backend Performance Improvements**

| Feature | Before | After | Benefit |
|---------|--------|-------|---------|
| **Endpoints** | Sync (blocking) | Async (non-blocking) | 10-100x concurrency |
| **WebSocket** | ❌ None | ✅ python-socketio | Real-time updates |
| **Database** | SQLite | PostgreSQL + pooling | Production-ready |
| **Caching** | ❌ None | ✅ Redis | 100x faster stats |
| **Background Tasks** | ❌ None | ✅ Celery | Offload heavy work |
| **Response Time** | 500-2000ms | 10-50ms (cached) | 40x faster! |

**Estimated Time**: 2-3 days

**Priority**: **DO THIS FIRST** before frontend - backend must be solid!

---

## **Part A: Electron App Setup & Structure**

### 1. Initialize Electron Project
**Time**: 1 day

- [ ] **Project Structure** (Inspired by WebTranslator):
  ```
  LocalizationTools/
  ├── desktop-app/              # NEW Electron application
  │   ├── src/
  │   │   ├── main/             # Electron main process
  │   │   │   └── main.ts       # App entry, window management
  │   │   ├── preload/          # Security layer (IPC)
  │   │   │   └── preload.ts    # Expose safe APIs to renderer
  │   │   └── renderer/         # Frontend (React)
  │   │       ├── App.tsx       # Main app component
  │   │       ├── components/   # Reusable UI components
  │   │       ├── pages/        # Main pages (not tabs!)
  │   │       ├── services/     # API client, WebSocket
  │   │       └── types/        # TypeScript types
  │   ├── assets/               # Icons, images
  │   ├── build/                # Compiled output
  │   ├── package.json
  │   ├── tsconfig.json
  │   └── webpack.config.js
  ├── server/                   # KEEP existing FastAPI server
  └── client/                   # KEEP Python client utilities
  ```

- [ ] **Dependencies** (package.json):
  ```json
  {
    "devDependencies": {
      "electron": "^36.4.0",
      "electron-builder": "^26.0.12",
      "@sveltejs/kit": "^2.0.0",
      "@sveltejs/adapter-static": "^3.0.0",
      "svelte": "^4.2.0",
      "svelte-check": "^4.0.0",
      "typescript": "^5.8.3",
      "vite": "^5.0.0",
      "svelte-preprocess": "^6.0.0",
      "@types/node": "^24.0.1"
    },
    "dependencies": {
      "carbon-components-svelte": "^0.85.0",
      "carbon-icons-svelte": "^12.0.0",
      "chart.js": "^4.4.0",
      "socket.io-client": "^4.8.1",
      "axios": "^1.10.0",
      "dayjs": "^1.11.13"
    }
  }
  ```

  **Note**: Using Vite instead of Webpack (faster, better for Svelte)

- [ ] **Build Scripts**:
  - `npm run dev` - Development with hot reload
  - `npm run build` - Production build
  - `npm run build:win` - Windows installer
  - `npm run build:mac` - macOS app
  - `npm run build:linux` - Linux AppImage

---

## **Part B: Modern UI/UX Design - Compact & Centralized**

### 2. Main Window Layout (NO TABS!)
**Time**: 2 days

**Single-Page Dashboard with Regions**:
```
┌─────────────────────────────────────────────────────────────────┐
│ Header: Logo | Tools Menu | Admin Menu | User Avatar | Settings│
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ LEFT SIDEBAR (20%)           │ MAIN CONTENT AREA (60%)         │
│ ─────────────────────────    │ ──────────────────────────────  │
│ 📊 Dashboard                 │                                 │
│ 🔧 Tools                     │  [Dynamic content based on      │
│   └─ XLSTransfer            │   selection - shows function    │
│   └─ Tool2 (future)         │   forms, results, etc.]         │
│   └─ Tool3                  │                                 │
│ 👥 Users (Admin)             │                                 │
│ 📝 Logs (Admin)              │                                 │
│ 📈 Analytics (Admin)         │                                 │
│ ⚙️  Settings                 │                                 │
│                              │                                 │
│                              │                                 │
├──────────────────────────────┼─────────────────────────────────┤
│ BOTTOM STATUS BAR: Server Status | Active Operations | CPU/RAM │
└─────────────────────────────────────────────────────────────────┘
```

**Key Features**:
- ✅ **Compact**: Everything visible in one screen
- ✅ **Hierarchical**: Tools → Functions (expandable tree)
- ✅ **No Tabs**: Sidebar navigation instead
- ✅ **Context-aware**: Main area changes based on selection
- ✅ **Sub-windows**: Modals for detailed views
- ✅ **Live Status**: Bottom bar shows real-time info

---

### 3. Professional Visual Design
**Time**: 1 day

Using **Carbon Components Svelte**:
- [ ] **Color Scheme**: Professional blues/grays (IBM Carbon theme)
- [ ] **Typography**: IBM Plex Sans (clean, corporate-friendly)
- [ ] **Cards**: Tile components with subtle shadows
- [ ] **Icons**: carbon-icons-svelte (comprehensive icon set)
- [ ] **Spacing**: Consistent 8px grid system (Carbon Design)
- [ ] **Animations**: Built-in Svelte transitions (fade, slide, fly)

**Dashboard Summary Cards** (Top of main area):
```svelte
<script lang="ts">
  import { Tile, Grid, Row, Column } from 'carbon-components-svelte';
  import { Rocket, CheckmarkFilled } from 'carbon-icons-svelte';

  let totalOps = 127;
  let successRate = 98.5;
  let activeUsers = 12;
  let avgDuration = 8.3;
</script>

<Grid>
  <Row>
    <Column lg={4} md={4} sm={4}>
      <Tile>
        <div class="stat-card">
          <Rocket size={32} class="stat-icon" />
          <h4>Total Operations Today</h4>
          <p class="stat-value">{totalOps}</p>
        </div>
      </Tile>
    </Column>

    <Column lg={4} md={4} sm={4}>
      <Tile>
        <div class="stat-card">
          <CheckmarkFilled size={32} class="stat-icon success" />
          <h4>Success Rate</h4>
          <p class="stat-value success">{successRate.toFixed(1)}%</p>
        </div>
      </Tile>
    </Column>

    <!-- More cards... -->
  </Row>
</Grid>

<style>
  .stat-card {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .stat-value {
    font-size: 2rem;
    font-weight: bold;
    color: #161616;
  }

  .stat-value.success {
    color: #24a148;
  }
</style>
```

---

### 4. XLSTransfer UI (Compact, Modal-Based)
**Time**: 2 days

**Main Page**: Simple function list with quick actions
```svelte
<script lang="ts">
  import { Tile, Button, StructuredList } from 'carbon-components-svelte';
  import { DocumentAdd, TranslateAI, Checkmark } from 'carbon-icons-svelte';

  const functions = [
    {
      name: 'Create Dictionary',
      description: 'Build translation dictionaries from Excel files',
      icon: DocumentAdd,
      action: 'create_dictionary'
    },
    {
      name: 'Transfer to Excel',
      description: 'AI-powered translation transfer',
      icon: TranslateAI,
      action: 'transfer_to_excel'
    },
    // ... more functions
  ];

  let selectedFunction = null;

  function openModal(func) {
    selectedFunction = func;
  }
</script>

<Tile>
  <h3>XLSTransfer Functions</h3>
  <StructuredList>
    {#each functions as func}
      <StructuredList.Row>
        <StructuredList.Cell>
          <div class="function-item">
            <svelte:component this={func.icon} size={24} />
            <div>
              <h4>{func.name}</h4>
              <p>{func.description}</p>
            </div>
          </div>
        </StructuredList.Cell>
        <StructuredList.Cell>
          <Button kind="primary" on:click={() => openModal(func)}>
            Execute
          </Button>
        </StructuredList.Cell>
      </StructuredList.Row>
    {/each}
  </StructuredList>
</Tile>
```

**Function Execution**: Opens modal with form
```svelte
<script lang="ts">
  import { Modal, FileUploader, RadioButtonGroup, RadioButton, ProgressBar, Button } from 'carbon-components-svelte';

  let isCreateDictOpen = false;
  let isProcessing = false;
  let progress = 0;
  let mode = 'whole';
  let files = [];

  async function handleCreateDict() {
    isProcessing = true;
    // Processing logic with progress updates
    for (let i = 0; i <= 100; i += 10) {
      progress = i;
      await new Promise(r => setTimeout(r, 200));
    }
    isProcessing = false;
  }
</script>

<Modal
  bind:open={isCreateDictOpen}
  modalHeading="Create Dictionary"
  primaryButtonText="Process"
  secondaryButtonText="Cancel"
  on:click:button--primary={handleCreateDict}
  size="lg"
>
  <FileUploader
    labelTitle="Upload Excel files"
    labelDescription="Select one or more Excel files"
    bind:files
    multiple
  />

  <RadioButtonGroup legendText="Processing Mode" bind:selected={mode}>
    <RadioButton value="split" labelText="Split Mode" />
    <RadioButton value="whole" labelText="Whole Mode" />
  </RadioButtonGroup>

  {#if isProcessing}
    <ProgressBar value={progress} helperText="Processing files..." />
  {/if}
</Modal>
```

---

## **Part C: Real-Time Features & Live Monitoring**

### 5. WebSocket Integration (1-second Updates)
**Time**: 2 days

**Backend: Add WebSocket Support**
- [ ] Install `python-socketio` for FastAPI
- [ ] Create WebSocket endpoint: `ws://localhost:8888/ws`
- [ ] Broadcast events:
  - `operation_started` - When user starts operation
  - `operation_progress` - Progress updates (% complete, current stage)
  - `operation_completed` - Final results
  - `user_connected` - User joins
  - `user_disconnected` - User leaves
  - `error_occurred` - Errors in real-time

**Frontend: Socket.io Client (Svelte)**
```svelte
<script lang="ts">
  import { onMount } from 'svelte';
  import { ToastNotification } from 'carbon-components-svelte';
  import io from 'socket.io-client';

  let socket;
  let progress = 0;
  let currentStage = '';
  let showNotification = false;
  let notificationData = {};

  onMount(() => {
    socket = io('http://localhost:8888');

    socket.on('operation_progress', (data) => {
      // Update progress bar in real-time (reactive!)
      progress = data.percent;
      currentStage = data.stage;
    });

    socket.on('operation_completed', (data) => {
      // Show completion notification
      showNotification = true;
      notificationData = {
        title: 'Operation Complete!',
        subtitle: `Processed ${data.rows} rows in ${data.duration}s`,
        kind: 'success'
      };
    });

    return () => socket.disconnect();
  });
</script>

{#if showNotification}
  <ToastNotification
    title={notificationData.title}
    subtitle={notificationData.subtitle}
    kind={notificationData.kind}
    on:close={() => showNotification = false}
  />
{/if}
```

**Note**: Svelte's reactivity means no `setState` needed - just assign values!

---

### 6. Live Logs Console (Admin)
**Time**: 1 day

**Features**:
- [ ] **Auto-scrolling log viewer** (updates every 1 second via WebSocket)
- [ ] **Filter controls**: By user, tool, function, status
- [ ] **Search**: Real-time text search in logs
- [ ] **Expandable rows**: Click to see full details

```tsx
<Card title="Live Logs" extra={<Switch>Auto-scroll</Switch>}>
  <Space style={{ marginBottom: 16 }}>
    <Select placeholder="User" onChange={setUserFilter} />
    <Select placeholder="Tool" onChange={setToolFilter} />
    <Select placeholder="Status" onChange={setStatusFilter} />
    <Input.Search placeholder="Search..." onSearch={setSearchText} />
  </Space>

  <Table
    dataSource={logs}
    columns={logColumns}
    expandable={{
      expandedRowRender: (record) => (
        <Descriptions bordered size="small">
          <Descriptions.Item label="Files">{record.files}</Descriptions.Item>
          <Descriptions.Item label="Memory">{record.memory} MB</Descriptions.Item>
          <Descriptions.Item label="Stages">{record.stages}</Descriptions.Item>
          {record.error && (
            <Descriptions.Item label="Error" span={3}>
              <pre>{record.error_stack}</pre>
            </Descriptions.Item>
          )}
        </Descriptions>
      )
    }}
    pagination={{ pageSize: 50 }}
  />
</Card>
```

---

### 7. User Process Monitoring (Click to View)
**Time**: 1 day

**User List with Live Status**:
```tsx
<Card title="Active Users">
  <List
    dataSource={activeUsers}
    renderItem={user => (
      <List.Item
        onClick={() => showUserDetails(user)}
        style={{ cursor: 'pointer' }}
      >
        <List.Item.Meta
          avatar={
            <Badge dot status={user.isActive ? 'success' : 'default'}>
              <Avatar>{user.name[0]}</Avatar>
            </Badge>
          }
          title={user.name}
          description={`${user.currentOps} active operations`}
        />
      </List.Item>
    )}
  />
</Card>
```

**User Details Modal** (opens on click):
```tsx
<Modal title={`${user.name} - Live Processes`} width={1000}>
  <Tabs>
    <TabPane tab="Active Operations" key="active">
      <Timeline>
        {user.operations.map(op => (
          <Timeline.Item color={op.status === 'running' ? 'blue' : 'green'}>
            <Card size="small">
              <Space direction="vertical" style={{ width: '100%' }}>
                <Text strong>{op.function}</Text>
                <Progress percent={op.progress} status={op.status} />
                <Text type="secondary">
                  Stage: {op.currentStage} | Memory: {op.memory} MB
                </Text>
              </Space>
            </Card>
          </Timeline.Item>
        ))}
      </Timeline>
    </TabPane>
    <TabPane tab="Recent History" key="history">
      {/* Show last 20 operations */}
    </TabPane>
    <TabPane tab="Statistics" key="stats">
      {/* User-specific stats */}
    </TabPane>
  </Tabs>
</Modal>
```

---

## **Part D: Enhanced Logging & Statistics**

### 8. Comprehensive Logging (Backend Enhancement)
**Time**: 2 days

**Update LogEntry model to include**:
- [ ] File details (names, sizes, input/output)
- [ ] Processing metrics (rows, embeddings, mode, threshold)
- [ ] Performance data (memory peak/avg, CPU %, stage durations)
- [ ] Full error details (stack traces, suggested fixes)

**See updated logging format in Phase 1.3 section**

---

### 9. Analytics Dashboard with Charts
**Time**: 2 days

**Using Chart.js with Svelte**:
```svelte
<script lang="ts">
  import { onMount } from 'svelte';
  import { Line, Pie, Bar, Doughnut } from 'svelte-chartjs';
  import {
    Chart as ChartJS,
    Title,
    Tooltip,
    Legend,
    LineElement,
    ArcElement,
    BarElement,
    CategoryScale,
    LinearScale,
    PointElement
  } from 'chart.js';

  ChartJS.register(
    Title, Tooltip, Legend,
    LineElement, ArcElement, BarElement,
    CategoryScale, LinearScale, PointElement
  );

  // Usage Trends (Last 7/30 days)
  const usageTrendData = {
    labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
    datasets: [{
      label: 'XLSTransfer',
      data: [12, 19, 15, 25, 22, 18, 20],
      borderColor: 'rgb(75, 192, 192)',
      tension: 0.4
    }]
  };

  // Tool Distribution (Pie Chart)
  const toolDistData = {
    labels: ['XLSTransfer', 'Tool2', 'Tool3'],
    datasets: [{
      data: [65, 25, 10],
      backgroundColor: [
        'rgb(54, 162, 235)',
        'rgb(255, 99, 132)',
        'rgb(255, 205, 86)'
      ]
    }]
  };

  // Hourly Usage (Bar Chart)
  const hourlyData = {
    labels: ['0h', '4h', '8h', '12h', '16h', '20h'],
    datasets: [{
      label: 'Operations',
      data: [5, 10, 45, 80, 60, 20],
      backgroundColor: 'rgba(54, 162, 235, 0.6)'
    }]
  };
</script>

<div class="charts-grid">
  <div class="chart-container">
    <h4>Usage Trends</h4>
    <Line data={usageTrendData} options={{responsive: true}} />
  </div>

  <div class="chart-container">
    <h4>Tool Distribution</h4>
    <Doughnut data={toolDistData} options={{responsive: true}} />
  </div>

  <div class="chart-container">
    <h4>Hourly Usage</h4>
    <Bar data={hourlyData} options={{responsive: true}} />
  </div>
</div>

<style>
  .charts-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
    gap: 2rem;
    padding: 1rem;
  }

  .chart-container {
    background: white;
    padding: 1.5rem;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  }
</style>
```

**Alternative**: Use **Carbon Charts** (IBM's chart library for Svelte)
```svelte
<script>
  import { LineChart, PieChart, BarChart } from '@carbon/charts-svelte';
  // Native Carbon integration - matches UI perfectly!
</script>
```

---

### 10. Comparison Views & Reports
**Time**: 1 day

**Time Period Comparison**:
```tsx
<Card title="This Week vs Last Week">
  <Row gutter={16}>
    <Col span={12}>
      <Statistic
        title="This Week"
        value={thisWeekOps}
        prefix={<ArrowUpOutlined />}
        valueStyle={{ color: '#3f8600' }}
      />
    </Col>
    <Col span={12}>
      <Statistic
        title="Last Week"
        value={lastWeekOps}
        suffix={`(${percentChange}%)`}
      />
    </Col>
  </Row>
  <Divider />
  <Column data={comparisonData} xField="week" yField="count" />
</Card>
```

---

## **Summary: Phase 1.11 Timeline**

**Total Estimated Time**: 17 days (3.5 weeks)

| Part | Task | Days | Priority |
|------|------|------|----------|
| **0** | **Backend Performance Upgrades** | **3** | **🔥 DO FIRST!** |
| 0.1 | Convert all endpoints to async | 0.5 | Critical |
| 0.2 | Add WebSocket support (python-socketio) | 1 | Critical |
| 0.3 | Switch to PostgreSQL + connection pooling | 0.5 | Critical |
| 0.4 | Add Redis caching | 0.5 | Important |
| 0.5 | Add Celery background tasks | 0.5 | Important |
| **A** | **Electron Setup** | **1** | After Part 0 |
| A1 | Electron project setup & structure | 1 | - |
| **B** | **UI/UX Design** | **5** | - |
| B2 | Main window layout (sidebar + content) | 2 | - |
| B3 | Professional visual design (Carbon) | 1 | - |
| B4 | XLSTransfer UI (modal-based) | 2 | - |
| **C** | **Real-Time Features** | **4** | - |
| C5 | Frontend WebSocket integration | 1 | - |
| C6 | Live logs console | 1 | - |
| C7 | User process monitoring | 1 | - |
| C8 | Real-time notifications | 1 | - |
| **D** | **Analytics & Stats** | **4** | - |
| D9 | Enhanced logging (comprehensive metadata) | 1 | - |
| D10 | Analytics dashboard (charts) | 2 | - |
| D11 | Comparison views & reports | 1 | - |

**Deliverables**:
- ✅ **Production-grade backend** (async, PostgreSQL, Redis, Celery)
- ✅ **Real-time WebSocket** communication (bi-directional)
- ✅ **Professional Electron desktop app** (Svelte + Carbon)
- ✅ **Compact, centralized UI** (no tabs, sidebar navigation)
- ✅ **Live updates every 1 second** (WebSocket push)
- ✅ **Live user/process monitoring** (click users to see operations)
- ✅ **Comprehensive logging** (files, sizes, performance, stages)
- ✅ **Beautiful analytics** (interactive charts, comparisons)
- ✅ **Management-ready presentation** (CEO-quality)

### 📋 Phase 1.12: Package and Deploy MVP
- After user testing feedback
- Documentation & Final Polish

---

## Project Phases Overview

```
Phase 1: Foundation & MVP (Week 1-2)
├── Set up project structure
├── Build basic Gradio interface for XLSTransfer
├── Implement central logging server
└── Create basic admin dashboard

Phase 2: Multi-Tool Integration (Week 3-4)
├── Add 3-5 additional tools
├── Enhance UI/UX
├── Improve logging and analytics
└── Add user settings

Phase 3: Polish & Features (Week 5-6)
├── User authentication
├── Auto-update system
├── Advanced analytics
└── Performance optimization

Phase 4: Production Ready (Week 7-8)
├── Full tool suite
├── Comprehensive testing
├── Documentation
└── Deployment
```

---

## Phase 1: Foundation & MVP (Week 1-2)

### Milestone: Single Tool Working with Analytics

### 1.1 Project Setup ✅ COMPLETED

**Tasks**:
- [x] Initialize Git repository
- [x] Create project folder structure (client/, server/, scripts/, tests/, ARCHIVE/)
- [x] Create all __init__.py files for Python packages
- [x] Set up .gitignore for clean repository
- [x] Create comprehensive requirements.txt
- [x] Create configuration files (client/config.py, server/config.py)
- [x] Create skeleton main.py files (client and server)
- [x] Create README.md with professional overview
- [x] Push to GitHub (https://github.com/NeilVibe/LocalizationTools)
- [ ] Set up virtual environment (NEXT STEP)
- [ ] Install core dependencies from requirements.txt (NEXT STEP)
- [ ] Download and cache Korean BERT model locally (NEXT STEP)

**File Structure**:
```
LocalizationTools/
├── client/                 # Gradio app (user-side)
│   ├── app.py             # Main Gradio app
│   ├── tools/             # Individual tool modules
│   │   ├── xls_transfer.py
│   │   └── __init__.py
│   ├── utils/             # Shared utilities
│   │   ├── logger.py      # Logging to server
│   │   └── config.py
│   └── models/            # ML models directory
│       └── KRTransformer/
├── server/                # Central server
│   ├── main.py           # FastAPI app
│   ├── database.py       # DB models
│   ├── api/              # API endpoints
│   │   └── logs.py
│   └── admin/            # Admin dashboard
│       └── dashboard.py
├── requirements.txt
├── build_client.py       # PyInstaller script
└── README.md
```

**Status**: ✅ COMPLETED (Day 1)
**Actual Time**: 1 day

**What We Built**:
- Complete project structure with 120+ files
- Professional documentation (Claude.md, README.md, STATS_DASHBOARD_SPEC.md)
- Database schema with 13 tables (PostgreSQL)
- Clean code policy and ARCHIVE structure
- Configuration systems for client and server
- Git repository pushed to GitHub

---

### 1.2 Build XLSTransfer Gradio Interface ⏳ IN PROGRESS

**Tasks**:
- [ ] Convert XLSTransfer0225.py to Gradio components
- [ ] Create tabbed interface for different functions:
  - Create Dictionary
  - Load Dictionary
  - Transfer to Excel
  - Transfer to Close
  - Check Newlines
  - Combine Excel Files
  - Newline Auto Adapt
  - Simple Excel Transfer
- [ ] Implement file upload/download
- [ ] Add progress indicators
- [ ] Handle errors gracefully with user-friendly messages

**Key Components**:
```python
import gradio as gr

with gr.Blocks() as app:
    with gr.Tab("Create Dictionary"):
        # File upload
        # Column selection
        # Process button
        # Progress bar

    with gr.Tab("Transfer to Excel"):
        # File upload
        # Settings
        # Process button

    # ... other tabs
```

**Estimated Time**: 3 days

---

### 1.3 Implement Local Processing & Logging

**Tasks**:
- [ ] Refactor XLSTransfer functions to work with Gradio callbacks
- [ ] Load Korean BERT model on app startup
- [ ] Implement progress callbacks
- [ ] Create logging utility that sends to server
- [ ] Add error handling and user feedback

**Logging Format** (Enhanced for Phase 1.11):
```python
{
    # Basic info
    "user_id": "anonymous_123",
    "session_id": "uuid-here",
    "tool": "XLSTransfer",
    "function": "create_dictionary",
    "timestamp_start": "2025-01-08T10:30:00",
    "timestamp_end": "2025-01-08T10:30:45",
    "duration_seconds": 45.2,
    "status": "success",  # or "error"
    "error_message": null,

    # File details
    "files": {
        "input_files": ["translations_v1.xlsx", "translations_v2.xlsx"],
        "output_files": ["SplitExcelDictionary.pkl", "SplitExcelEmbeddings.npy"],
        "temp_files": ["temp_merged.xlsx"],
        "input_size_mb": 2.5,
        "output_size_mb": 3.2
    },

    # Processing details
    "processing": {
        "rows_total": 5000,
        "rows_processed": 4850,
        "rows_skipped": 150,
        "unique_texts": 4850,
        "embeddings_generated": 4850,
        "embedding_dimensions": 768,
        "mode": "whole",  # or "split"
        "faiss_threshold": 0.99
    },

    # Performance metrics
    "performance": {
        "memory_peak_mb": 450,
        "memory_avg_mb": 320,
        "cpu_avg_percent": 85.5,
        "stage_durations": {
            "loading": 2.1,
            "embedding": 8.3,
            "indexing": 1.5,
            "saving": 2.8
        }
    },

    # Function-specific metadata (varies by function)
    "metadata": {
        "dictionary_type": "split",
        "model_name": "snunlp/KR-SBERT-V40K-klueNLI-augSTS",
        "batch_size": 100
    }
}
```

**Note**: See Phase 1.11 for comprehensive logging enhancements

**Estimated Time**: 2 days

---

### 1.4 Set Up Database

**CURRENT STATUS: Using SQLite for MVP Testing**

**Tasks**:
- [x] Design PostgreSQL schema (see `database_schema.sql`)
- [x] Create SQLite version for local testing ✅ ACTIVE
- [x] Run schema creation scripts (SQLAlchemy auto-create)
- [x] Create database connection utilities
- [x] Test database connections
- [x] Set up SQLAlchemy ORM models
- [ ] **PostgreSQL Setup (Future - Production Only)**
  - PostgreSQL 14.19 installed but not configured
  - Will be needed for production deployment
  - Code is ready (supports both databases)

**Current Database**:
- **Type:** SQLite
- **File:** `/server/data/localizationtools.db` (196 KB)
- **Status:** Working perfectly for testing
- **Switch to PostgreSQL:** Set `DATABASE_TYPE=postgresql` env variable

**Database Setup**:
```bash
# Current setup (SQLite - working)
DATABASE_TYPE=sqlite  # Default

# Future production (PostgreSQL)
DATABASE_TYPE=postgresql
# Then run: python scripts/setup_database.py --db postgresql
```

**Schema includes**:
- 12 tables covering all aspects (users, logs, stats, errors, etc.)
- SQLAlchemy ORM models
- Optimized for both SQLite and PostgreSQL
- Automatic table creation on startup

**Why SQLite for MVP**:
- ✅ No setup required
- ✅ Perfect for testing/development
- ✅ Single file, easy backup
- ✅ Sufficient for initial testing

**When to switch to PostgreSQL**:
- Production deployment
- Multiple concurrent users (20+)
- Need for advanced features
- Better performance at scale

See `database_schema.sql` for complete PostgreSQL schema.

**Time Spent**: 2 days (Complete for MVP)

---

### 1.5 Build Central Logging Server

**Tasks**:
- [ ] Set up FastAPI project structure
- [ ] Implement database models with SQLAlchemy
- [ ] Create authentication endpoints (login, register)
- [ ] Implement POST /api/logs endpoint
- [ ] Add user session management
- [ ] Create API for querying logs
- [ ] Add API key authentication for client apps
- [ ] Test all endpoints

**API Endpoints**:
- `POST /api/auth/login` - User authentication
- `POST /api/auth/register` - User registration (admin only)
- `POST /api/logs` - Receive log entry from client
- `POST /api/sessions/start` - Start new session
- `POST /api/sessions/end` - End session
- `GET /api/stats/overview` - Get aggregated statistics
- `GET /api/stats/tools` - Tool usage statistics
- `GET /api/stats/users` - User activity data
- `GET /api/version/latest` - Check for updates
- `GET /api/announcements` - Get active announcements

**Authentication**:
- bcrypt password hashing
- JWT tokens for session management
- API keys for client-server communication

**Estimated Time**: 3 days

---

### 1.6 Create Comprehensive Admin Dashboard

**CRITICAL**: Dashboard must be CLEAN, DETAILED, and BEAUTIFUL to impress management.

**Tasks**:
- [ ] Build Gradio dashboard interface with professional design
- [ ] Implement real-time metrics (auto-refresh every 30s)
- [ ] Create comprehensive charts with Plotly (interactive)
- [ ] Add date range filtering (daily/weekly/monthly/custom)
- [ ] Implement all analytics views (see STATS_DASHBOARD_SPEC.md)

**Dashboard Sections** (See STATS_DASHBOARD_SPEC.md for full details):

1. **Overview / Home Page**:
   - Real-time active users count (🟢 live)
   - Today's operations total
   - Overall success rate percentage
   - Average processing duration

2. **Usage Analytics**:
   - **Daily Usage**: Line chart (last 30 days)
   - **Weekly Aggregation**: Table with week-by-week breakdown
   - **Monthly Aggregation**: Bar chart with monthly comparison
   - Shows: operations count, unique users, success rate, avg duration

3. **Tool Popularity**:
   - **Most Used Tools**: Horizontal bar chart with percentages
   - **Function-Level Breakdown**: Expandable tables per tool
   - Shows: usage count, % of total, avg duration, success rate

4. **Performance Metrics**:
   - **Fastest Functions**: Top 10 table (sorted by speed)
   - **Slowest Functions**: Bottom 10 table
   - **Performance Over Time**: Line chart showing duration trends
   - Min/max/average duration for each function

5. **Connection Analytics**:
   - **Daily Connections**: Bar chart of daily active users
   - **Weekly Connections**: Table with retention rates
   - **Monthly Active Users (MAU)**: Line chart with growth trend
   - Total sessions, operations per user

6. **User Leaderboard**:
   - Top 20 most active users (current month)
   - Shows: operations count, time spent, active days, top tool
   - Sortable and filterable

7. **Error Tracking**:
   - **Error Rate Over Time**: Line chart (percentage)
   - **Most Common Errors**: Table with error types, frequencies
   - Affected users count, most common tool per error

8. **Export Reports**:
   - PDF: Executive summary with key charts
   - Excel: Detailed data tables
   - PowerPoint: Management presentation
   - CSV: Raw data for custom analysis
   - Report types: Daily, Weekly, Monthly, Custom Range, User-Specific

**Visual Design**:
- **Color coded**: Green (success), Red (error), Blue (info)
- **Interactive charts**: Hover tooltips, click to drill down
- **Responsive layout**: Works on desktop, tablet, mobile
- **Auto-refresh**: Real-time metrics update automatically
- **Clean UI**: Professional, easy to read, impressive

**Database Queries**:
- All optimized queries documented in STATS_DASHBOARD_SPEC.md
- Use pre-computed views for fast loading
- Implement caching for expensive queries

**Estimated Time**: 5 days (comprehensive dashboard is critical!)

---

### 1.7 Testing & MVP Release

**Tasks**:
- [ ] Test XLSTransfer all functions in Gradio
- [ ] Verify logging works correctly
- [ ] Test admin dashboard
- [ ] Create test data
- [ ] Fix bugs
- [ ] Document basic usage

**Deliverable**:
- Working Gradio app with XLSTransfer
- Central server receiving logs
- Basic admin dashboard showing statistics

**Estimated Time**: 2 days

**Total Phase 1 Time**: 18 days (3.5 weeks)

---

## Phase 2: Multi-Tool Integration (Week 3-4)

### Milestone: 5+ Tools Available with Enhanced UI

### 2.1 Select & Prioritize Additional Tools

**Tasks**:
- [ ] Review all existing scripts in MAIN/SECONDARY folders
- [ ] Select 4-5 most impactful tools based on:
  - Frequency of use
  - Processing complexity
  - User requests
  - Business value

**Recommended Tools to Add**:
1. **TFMFULL0116.py** - TFM full processing
2. **QS0305.py** - Quick Search functionality
3. **KRSIMILAR0124.py** - Korean similarity checker
4. **stackKR.py** - Stack Korean files
5. **removeduplicate.py** - Remove duplicates

**Estimated Time**: 1 day

---

### 2.2 Convert Tools to Gradio Modules

**Tasks**:
For each tool:
- [ ] Analyze script functionality
- [ ] Refactor into modular functions
- [ ] Create Gradio interface
- [ ] Add to main app as new tab
- [ ] Implement logging for each function
- [ ] Add progress tracking
- [ ] Test thoroughly

**Template for Each Tool**:
```python
# tools/tool_name.py

def process_function(input_file, settings):
    # Original logic here
    # Add progress callbacks
    # Return results
    pass

def create_gradio_interface():
    with gr.Tab("Tool Name"):
        # UI components
        # Buttons
        # File uploads
        pass
    return interface
```

**Estimated Time**: 2 days per tool = 10 days

---

### 2.3 Enhance UI/UX

**Tasks**:
- [ ] Add app branding (logo, colors, theme)
- [ ] Implement dark mode toggle
- [ ] Add tooltips and help text
- [ ] Create better progress indicators
- [ ] Add sound notifications on completion
- [ ] Improve error messages
- [ ] Add keyboard shortcuts

**Estimated Time**: 2 days

---

### 2.4 Improve Analytics

**Tasks**:
- [ ] Track individual function usage within tools
- [ ] Add performance metrics (CPU, memory)
- [ ] Track error rates
- [ ] Add user feedback mechanism
- [ ] Enhance dashboard with new metrics

**New Metrics**:
- Function-level usage
- Average file sizes processed
- Success/error rates
- Performance trends over time
- User retention rates

**Estimated Time**: 2 days

**Total Phase 2 Time**: 15 days (3 weeks)

---

## Phase 3: Polish & Advanced Features (Week 5-6)

### Milestone: Production-Quality Application

### 3.1 User Authentication System

**Tasks**:
- [ ] Add login screen to Gradio app
- [ ] Implement user registration
- [ ] Create authentication API endpoints
- [ ] Store user credentials securely (hashed)
- [ ] Add "Remember Me" functionality
- [ ] Allow anonymous mode (optional login)

**Benefits**:
- Accurate user tracking
- Personalized settings
- User-specific analytics

**Estimated Time**: 3 days

---

### 3.2 Auto-Update System

**Tasks**:
- [ ] Implement version checking
- [ ] Create update server endpoint
- [ ] Add update notification in app
- [ ] Build auto-download mechanism
- [ ] Create update installer/patcher
- [ ] Test update process

**Update Flow**:
1. App checks version on startup
2. If new version available, show notification
3. User clicks "Update"
4. Download only changed files
5. Apply update and restart

**Estimated Time**: 4 days

---

### 3.3 Advanced Analytics Dashboard

**Tasks**:
- [ ] Add advanced charts (heatmaps, trends)
- [ ] Create exportable reports (PDF, Excel)
- [ ] Add custom date range filtering
- [ ] Implement user comparison views
- [ ] Add tool efficiency metrics
- [ ] Create monthly summary reports

**Dashboard Features**:
- Daily/Weekly/Monthly views
- Tool usage heatmap by hour/day
- User leaderboard (most active)
- Performance benchmarks
- Export to PowerPoint for presentations

**Estimated Time**: 3 days

---

### 3.4 Settings & Preferences

**Tasks**:
- [ ] Add user settings panel
- [ ] Allow theme customization
- [ ] Add default file locations
- [ ] Create tool-specific presets
- [ ] Add notification preferences
- [ ] Implement settings sync (server-side)

**Estimated Time**: 2 days

**Total Phase 3 Time**: 12 days (2.5 weeks)

---

## Phase 4: Production Ready (Week 7-8)

### Milestone: Full Deployment

### 4.1 Complete Tool Suite

**Tasks**:
- [ ] Add remaining tools (aim for 10+ total)
- [ ] Ensure all tools are fully integrated
- [ ] Standardize UI across all tools
- [ ] Complete all logging implementations

**Estimated Time**: 5 days

---

### 4.2 Packaging & Distribution

**Tasks**:
- [ ] Configure PyInstaller for optimal build
- [ ] Bundle ML models efficiently
- [ ] Minimize executable size where possible
- [ ] Create installer (NSIS or similar)
- [ ] Set up auto-update infrastructure
- [ ] Create uninstaller

**Build Configuration**:
```python
# build_client.py
import PyInstaller.__main__

PyInstaller.__main__.run([
    'client/app.py',
    '--name=LocalizationTools',
    '--onefile',
    '--windowed',
    '--add-data=models:models',
    '--icon=icon.ico',
    '--hidden-import=gradio',
    '--hidden-import=sentence_transformers',
    # ... other imports
])
```

**Estimated Time**: 3 days

---

### 4.3 Testing & QA

**Tasks**:
- [ ] Unit tests for all tool functions
- [ ] Integration tests for logging
- [ ] UI/UX testing
- [ ] Performance testing (large files)
- [ ] Cross-platform testing (if applicable)
- [ ] Beta testing with real users
- [ ] Bug fixing

**Test Cases**:
- All tool functions work correctly
- Logging captures all events
- Dashboard displays accurate data
- Updates work smoothly
- Error handling is robust
- Performance is acceptable

**Estimated Time**: 4 days

---

### 4.4 Documentation

**Tasks**:
- [ ] User manual (how to use each tool)
- [ ] Video tutorials (optional)
- [ ] Admin guide (dashboard usage)
- [ ] Developer docs (for maintenance)
- [ ] API documentation
- [ ] Troubleshooting guide

**Estimated Time**: 2 days

---

### 4.5 Deployment

**Tasks**:
- [ ] Deploy central server to production
- [ ] Set up SSL certificates
- [ ] Configure domain (your.company.com)
- [ ] Set up database backups
- [ ] Create monitoring/alerting
- [ ] Release client application
- [ ] Announce to users

**Infrastructure**:
- Server: AWS/DigitalOcean/Azure
- Database: PostgreSQL (production)
- Domain: SSL-secured
- Backup: Daily automated backups

**Estimated Time**: 2 days

**Total Phase 4 Time**: 16 days (3 weeks)

---

## Total Timeline: 9-10 Weeks

```
Week 1-3:  Phase 1 - MVP with XLSTransfer + Database setup
Week 4-6:  Phase 2 - Multi-tool integration
Week 7-8:  Phase 3 - Polish & advanced features
Week 9-10: Phase 4 - Production ready
```

---

## Technology Stack Summary

### Client Application
| Technology | Purpose | Version |
|------------|---------|---------|
| Python | Runtime | 3.10+ |
| Gradio | UI Framework | 4.x |
| PyInstaller | Executable builder | 6.x |
| sentence-transformers | ML models | Latest |
| FAISS | Vector search | Latest |
| pandas | Data processing | Latest |
| openpyxl | Excel manipulation | Latest |
| requests | HTTP client | Latest |

### Server
| Technology | Purpose | Version |
|------------|---------|---------|
| Python | Runtime | 3.10+ |
| FastAPI | Web framework | 0.100+ |
| SQLAlchemy | ORM | 2.x |
| PostgreSQL | Database (prod) | 15+ |
| SQLite | Database (dev) | 3.x |
| uvicorn | ASGI server | Latest |
| Gradio | Admin dashboard | 4.x |

---

## Risk Management

### Potential Challenges & Solutions

**Challenge 1**: Large executable size (1GB+)
- **Solution**: Optimize PyInstaller configuration, use lazy model loading

**Challenge 2**: Slow first-time startup (model loading)
- **Solution**: Add splash screen, cache models, show progress

**Challenge 3**: Users behind firewall (logging fails)
- **Solution**: Queue logs locally, retry with exponential backoff, offline mode

**Challenge 4**: Server downtime affects client
- **Solution**: Client works fully offline, logs queue until server available

**Challenge 5**: Update distribution bandwidth
- **Solution**: Delta updates only, CDN for downloads

---

## Success Criteria

The project is successful when:

- [ ] 80%+ of target users have installed the app
- [ ] Daily active usage of at least 50%
- [ ] All tools report usage correctly
- [ ] Admin dashboard shows accurate real-time data
- [ ] Updates deploy smoothly without user friction
- [ ] Management sees clear value in usage reports
- [ ] Users prefer unified app over individual tools

---

## Development Guidelines

### 🧹 Clean Code Policy (CRITICAL!)

**STRICT RULE**: Keep the project CLEAN at all times. This is NON-NEGOTIABLE.

**Why Cleanliness Matters**:
- Professional presentation to management
- Easy maintenance and debugging
- Quick onboarding for new developers
- Scalable codebase as project grows
- **Demonstrates attention to detail**

**ARCHIVE Folder Usage**:
- Create `ARCHIVE/` folder for ALL temporary/experimental code
- After solving issues with test scripts → Move to `ARCHIVE/test_scripts/`
- Old code versions during refactoring → Move to `ARCHIVE/old_code/`
- Experiments that don't work out → Move to `ARCHIVE/experiments/`
- Debug scripts once resolved → Move to `ARCHIVE/test_scripts/`

**Never leave clutter**:
- No orphaned test files in main directories
- No `temp.py`, `test123.py`, `debug_something.py` in working folders
- Every file has a purpose or gets archived

**Resources**:
- `RessourcesForCodingTheProject/` contains all original scripts and test data
- Reference this for validation and testing
- Don't modify - use as read-only reference

**Important Documentation**:
- `Claude.md` - Complete project documentation with clean code policy
- `STATS_DASHBOARD_SPEC.md` - Comprehensive analytics dashboard specification
- `database_schema.sql` - Complete PostgreSQL schema with all tables

### Update System Details

**Version Management**:
- All versions tracked in `app_versions` table
- Mark new versions as `is_latest=TRUE`
- Optional updates: `is_mandatory=FALSE`
- Force updates: `is_mandatory=TRUE` (critical fixes)

**Update Flow**:
1. User opens app
2. App calls `GET /api/version/latest`
3. Server responds with version info
4. App shows update notification
5. User clicks "Update Now"
6. Auto-download and install
7. Logged in `update_history` table

**Push Announcements**:
- Use `announcements` table to notify users
- Show banners in app for maintenance, news, tips
- Target specific users or all users
- Set display timeframes

## Next Immediate Steps

### ✅ Completed (Day 1)
1. ✅ Design PostgreSQL schema with all tables (13 tables, complete with views)
2. ✅ Update documentation (Claude.md, Roadmap.md, STATS_DASHBOARD_SPEC.md)
3. ✅ Define clean code policy (documented in Claude.md)
4. ✅ Set up project structure with ARCHIVE folder (120+ files)
5. ✅ Create configuration files (client/config.py, server/config.py)
6. ✅ Create skeleton applications (client/main.py, server/main.py)
7. ✅ Set up requirements.txt with all dependencies
8. ✅ Initialize Git and push to GitHub

### 🎯 Next Steps (Day 2 - Starting Now!)

**Environment Setup**:
1. **Set up virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Download Korean BERT model**
   ```bash
   python scripts/download_models.py  # We need to create this script
   ```

**Development Work**:
4. **Build basic Gradio interface** (Day 2-3)
5. **Set up SQLite database for testing** (Day 3)
6. **Implement XLSTransfer Create Dictionary function** (Day 4-5)
7. **Set up central server with authentication** (Day 5-6)
8. **Connect client logging to server** (Day 7)
9. **Build comprehensive admin dashboard** (Day 8-12)
10. **Continue with remaining XLSTransfer functions** (Day 13-15)

### 📅 Timeline
- **Week 1**: Setup ✅, Environment, Basic Gradio Interface, Database
- **Week 2**: XLSTransfer implementation, Server setup, Logging
- **Week 3**: Admin dashboard, Testing, MVP release

Let's continue building! 🚀
