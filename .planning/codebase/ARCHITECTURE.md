# Architecture

**Analysis Date:** 2026-03-14

## Pattern Overview

**Overall:** Offline-first, dual-database abstraction layer with Svelte 5 frontend

**Key Characteristics:**
- **3-mode detection**: PostgreSQL (online), SQLite fallback (server), SQLite offline mode (client)
- **Repository abstraction**: Same interfaces, different database implementations (no code duplication)
- **Optimistic UI**: Frontend updates instantly, server syncs in background
- **Full offline parity**: Every online feature works offline except network-dependent ones

---

## Layers

**Backend API Layer:**
- Purpose: HTTP/WebSocket endpoints for all tools and LDM features
- Location: `server/api/`
- Contains: FastAPI routers, tool endpoints, authentication, logging
- Depends on: Repository layer, database models, config
- Used by: Frontend (Svelte), external clients via HTTP

**Repository Layer (Data Access Abstraction):**
- Purpose: Abstract database access - routes never touch databases directly
- Location: `server/repositories/`
- Contains: Two implementations (PostgreSQL, SQLite) with shared interfaces
- Depends on: SQLAlchemy, database connections
- Used by: API routes (via factory dependency injection), business logic

**Database Models:**
- Purpose: SQLAlchemy ORM models shared across both database types
- Location: `server/database/models.py`
- Contains: User, Session, LogEntry, ActiveOperation, and 80+ entity models
- Depends on: SQLAlchemy
- Used by: Repository implementations

**Frontend (Svelte 5):**
- Purpose: Desktop app UI built with SvelteKit, Carbon Components
- Location: `locaNext/src/`
- Contains: Pages, components, stores, API client
- Depends on: API client, stores, utilities
- Used by: Electron wrapper (Windows executable)

**Configuration & Utilities:**
- Purpose: Centralized config, logging, caching, WebSocket, security
- Location: `server/config.py`, `server/utils/`, `server/middleware/`
- Contains: Environment loading, database initialization, IP filtering, CORS
- Used by: Main app, all routes

---

## Data Flow

**Online (PostgreSQL) Flow:**

1. Client (Electron app) sends HTTP request with `Bearer {jwt_token}`
2. API route receives request → `Depends(get_current_active_user_async)`
3. Factory `get_tm_repository()` detects: online mode, PostgreSQL available → returns `PostgreSQLTMRepository`
4. Route calls repo method (e.g., `get_translation_memory()`)
5. Repo queries PostgreSQL (permissions baked in)
6. Response returned to client with `updatedAt` timestamp
7. Client updates UI optimistically, then syncs with server

**Offline (SQLite) Flow:**

1. Client sends HTTP request with `Bearer OFFLINE_MODE_{session_id}`
2. API detects offline mode header in factory → returns `SQLiteRepository(schema_mode=OFFLINE)`
3. Route calls repo method → queries SQLite `offline_*` tables
4. Client works entirely local, no server communication
5. When server available again, client syncs changes via WebSocket

**SQLite Fallback (Server in fallback mode):**

1. Server detects PostgreSQL unavailable
2. Factory checks `config.ACTIVE_DATABASE_TYPE == "sqlite"`
3. Returns `SQLiteRepository(schema_mode=SERVER)` → queries `ldm_*` tables
4. Server operates on local SQLite with same schema as PostgreSQL
5. When PostgreSQL restored, server migrates data automatically

---

## Key Abstractions

**Repository Interface Pattern:**
- Purpose: Define contract that all database implementations must follow
- Examples: `FileRepository`, `TMRepository`, `RowRepository`, `ProjectRepository`
- Pattern: Abstract base class in `server/repositories/interfaces/`, two implementations
- Location: `server/repositories/interfaces/`, `server/repositories/postgresql/`, `server/repositories/sqlite/`

**Mode Detection:**
- Purpose: Automatically select correct repository based on request context
- Examples: Offline header check, PostgreSQL availability check
- Pattern: Factory functions `_is_offline_mode()`, `_is_sqlite_fallback()` in `server/repositories/factory.py`
- Handles: 3 distinct modes seamlessly

**API Router Pattern:**
- Purpose: Reduce code duplication across multiple tool endpoints
- Examples: `BaseToolAPI` provides common patterns for all tools
- Pattern: Tool APIs inherit from `BaseToolAPI`, define tool-specific logic
- Location: `server/api/base_tool_api.py` (base), `server/api/xlstransfer_async.py`, `server/api/quicksearch_async.py`, etc.

**Svelte 5 Runes:**
- Purpose: State management without external libraries
- Examples: `$state()` for mutable state, `$derived()` for computed values, `$effect()` for side effects
- Pattern: Used throughout components; `$state` for local UI state, centralized stores for app state
- Location: `locaNext/src/lib/components/` (component local state), `locaNext/src/lib/stores/` (global state)

**Store Pattern:**
- Purpose: Centralized, reactive app state (authentication, navigation, sync)
- Examples: `app.js` (currentApp, isAuthenticated), `ldm.js` (file tree), `sync.js` (sync status)
- Pattern: Svelte writable stores with initialization and subscription functions
- Location: `locaNext/src/lib/stores/`

---

## Entry Points

**Backend Server:**
- Location: `server/main.py`
- Triggers: `python3 server/main.py` or Electron embedded Python
- Responsibilities: FastAPI app initialization, database setup, middleware registration, router registration, WebSocket wrapping

**Frontend:**
- Location: `locaNext/src/routes/+page.svelte` (main UI)
- Triggers: Electron loads `http://localhost:5173` (dev) or `file://` (build)
- Responsibilities: Login, app switching, page routing, global state management

**API Routes (v2 endpoints):**
- Location: `server/api/`
- Examples: `/api/v2/auth/login`, `/api/v2/ldm/files`, `/api/v2/xlstransfer/process`
- Pattern: FastAPI routers included in main app via `app.include_router(router)`

---

## Error Handling

**Strategy:** Layered error handling with context-specific responses

**Patterns:**

- **Backend HTTP Errors**: FastAPI `HTTPException` with status codes + JSON detail
  - 401 → Unauthorized (token invalid/missing)
  - 403 → Forbidden (permission denied, baked into repository)
  - 404 → Not found (resource doesn't exist)
  - 500 → Server error (logged to `server/data/logs/`)

- **Database Errors**: Caught in repository layer, wrapped as `HTTPException`
  - Constraint violations → 400 Bad Request
  - Connection errors → 503 Service Unavailable

- **Frontend Error Handling**: Global error boundary + toast notifications
  - API errors → caught in `client.js`, display toast
  - Network errors → retry logic with exponential backoff
  - Sync conflicts → user prompted to resolve (keep local vs. server version)

- **WebSocket Errors**: Try-catch in `websocket.js`, automatic reconnect
  - Connection lost → queues operations locally until reconnected
  - Invalid message → logged, connection continues

---

## Cross-Cutting Concerns

**Logging:** Loguru-based with file rotation and archival
- Backend: `server/data/logs/` with separate error log
- Frontend: Browser console + remote logging via `/logs/submit` endpoint
- Location: `server/utils/logger.js` (frontend), `loguru` integration (backend)

**Validation:** Input validation at route level + database constraints
- Pydantic models for request validation (`server/api/schemas.py`)
- SQLAlchemy column constraints (NOT NULL, UNIQUE, FK, CHECK)
- Frontend validation in components before sending to API

**Authentication:** JWT tokens + offline mode detection
- Backend: `server/api/auth_async.py` handles login/token generation
- Frontend: Token stored in localStorage, included in all requests
- Offline: Special token format `OFFLINE_MODE_{session_id}` for offline mode detection
- Refreshing: Token auto-refreshed on `401` response

**Authorization:** Permission checks baked into repository implementations
- PostgreSQL repo enforces permissions via SQL
- SQLite offline repo: all operations allowed (single-user local storage)
- Location: `server/repositories/postgresql/` (each repo has permission logic)

**Caching:** Redis optional (if available), falls back to in-memory
- Location: `server/utils/cache.py`
- Used for: Session tokens, API responses, FAISS indexes
- Pattern: Cache-aside (check cache first, load from DB if missed)

**WebSocket:** Real-time sync and presence tracking
- Location: `server/utils/websocket.py` (backend), `locaNext/src/lib/api/websocket.js` (frontend)
- Events: `operation_start`, `progress_update`, `operation_complete`, `sync_update`
- Fallback: HTTP polling if WebSocket unavailable

---

*Architecture analysis: 2026-03-14*
