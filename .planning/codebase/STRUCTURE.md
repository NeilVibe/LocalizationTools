# Codebase Structure

**Analysis Date:** 2026-03-14

## Directory Layout

```
LocalizationTools/
├── server/                      # Backend (FastAPI)
│   ├── main.py                  # FastAPI app entry point
│   ├── config.py                # Configuration, paths, env vars
│   ├── api/                      # API routes and endpoints
│   ├── repositories/             # Database abstraction layer
│   ├── database/                 # SQLAlchemy models and migrations
│   ├── utils/                    # Utilities (logger, cache, websocket, dependencies)
│   ├── middleware/               # Request/response middleware (logging, IP filtering)
│   ├── client_config/            # Client-side config delivery endpoints
│   └── data/                     # Runtime data (logs, cache, TM indexes, backups)
│
├── locaNext/                    # Frontend (Svelte 5 + SvelteKit)
│   ├── src/
│   │   ├── routes/              # SvelteKit pages (+page.svelte, +layout.svelte)
│   │   ├── lib/
│   │   │   ├── api/             # API client and WebSocket
│   │   │   ├── components/      # Reusable Svelte components
│   │   │   ├── stores/          # Global state (Svelte stores)
│   │   │   └── utils/           # Frontend utilities
│   │   ├── app.css              # Global styles
│   │   └── app.html             # HTML entry point
│   ├── svelte.config.js         # SvelteKit configuration
│   ├── vite.config.js           # Vite build configuration
│   └── package.json             # NPM dependencies
│
├── scripts/                     # Utility scripts
│   ├── check_servers.sh         # Check running servers
│   ├── start_all_servers.sh     # Start all backend+frontend
│   ├── playground_install.sh    # Fresh Windows build installation
│   ├── db_manager.sh            # Database management CLI
│   └── gitea_control.sh         # Gitea CI/CD control
│
├── tests/                       # Test suite
│   ├── test_api.py              # API endpoint tests
│   ├── test_repositories.py     # Repository layer tests
│   └── ...
│
├── testing_toolkit/             # Testing utilities
│   ├── DEV_MODE_PROTOCOL.md     # Development testing guide
│   ├── MASTER_TEST_PROTOCOL.md  # Build and test procedures
│   └── cdp/                     # Chrome DevTools Protocol tests
│
├── docs/                        # Documentation
│   ├── INDEX.md                 # Documentation hub
│   ├── architecture/            # Architecture docs
│   ├── protocols/               # Development protocols (GDP, PRXR)
│   ├── reference/               # Reference guides
│   └── history/                 # Historical decisions
│
├── RessourcesForCodingTheProject/  # Reference scripts library
│   └── NewScripts/              # Mini-projects and standalone tools
│
├── .planning/                   # GSD planning documents
│   └── codebase/                # Codebase analysis (ARCHITECTURE.md, STRUCTURE.md, etc.)
│
├── installer/                   # Windows installer builder
├── landing-page/                # Marketing landing page (index.html)
├── logs/                        # Log archives
├── models/                      # ML models (Qwen, FAISS indexes)
└── CLAUDE.md                    # Project instructions (CRITICAL)
```

---

## Directory Purposes

**server/**
- Purpose: Central backend server handling all business logic, data, and API endpoints
- Contains: FastAPI app, database abstraction, repositories, utilities, configuration
- Key files: `main.py` (entry point), `config.py` (all settings)

**server/api/**
- Purpose: HTTP route definitions for all features
- Contains: Tool endpoints (XLSTransfer, QuickSearch, KR Similar), authentication, logging, admin endpoints
- Key files: `auth_async.py` (login/tokens), `base_tool_api.py` (base class for tools)
- Naming: `{tool}_async.py` for each tool, `{topic}_async.py` for features

**server/repositories/**
- Purpose: Database abstraction - routes never touch databases directly
- Contains: Two implementations (PostgreSQL and SQLite) with shared interface contracts
- Key files: `factory.py` (mode detection and repository selection), `interfaces/` (base contracts)
- Pattern: `postgresql/` and `sqlite/` directories mirror each other exactly

**server/repositories/interfaces/**
- Purpose: Define repository contracts (abstract base classes)
- Contains: `file_repository.py`, `tm_repository.py`, `row_repository.py`, `project_repository.py`, etc.
- Key: Routes import these interfaces, not implementations

**server/repositories/postgresql/**
- Purpose: PostgreSQL implementations of all repositories
- Contains: One file per repository interface with full SQL implementation
- Used: In online mode, falls back to SQLite if PostgreSQL unavailable

**server/repositories/sqlite/**
- Purpose: SQLite implementations of all repositories
- Contains: Same file names as PostgreSQL, SQL adapted for SQLite
- Features: Base class `base.py` with common SQLite patterns
- Used: In offline mode (`schema_mode=OFFLINE` → offline_* tables) or server fallback

**server/database/**
- Purpose: Database models and schema management
- Contains: SQLAlchemy ORM models, Alembic migrations
- Key files: `models.py` (80+ entity models), `migrations/` (schema versions)

**server/utils/**
- Purpose: Shared utilities (not business logic)
- Contains: Logger setup, cache (Redis), WebSocket manager, dependency injection, database initialization
- Key files: `dependencies.py` (Depends() functions), `websocket.py` (real-time sync)

**server/middleware/**
- Purpose: FastAPI middleware for cross-cutting concerns
- Contains: Request logging, performance monitoring, IP filtering, CORS
- Key files: `__init__.py` (RequestLoggingMiddleware, PerformanceLoggingMiddleware), `ip_filter.py`

**locaNext/src/**
- Purpose: Frontend UI source code
- Contains: Svelte 5 components, pages, global state, API client

**locaNext/src/routes/**
- Purpose: SvelteKit file-based routing
- Contains: `+page.svelte` (main page), `+layout.svelte` (app wrapper), `+error.svelte` (error page)
- Key: SvelteKit automatically creates routes from file structure

**locaNext/src/lib/api/**
- Purpose: API communication layer
- Contains: `client.js` (HTTP requests, auth token handling), `websocket.js` (WebSocket real-time)
- Pattern: Singleton instance `api` exported from `client.js`, used in all components

**locaNext/src/lib/components/**
- Purpose: Reusable Svelte components organized by feature
- Contains: Global components (Login, Launcher, TaskManager), app components (LDM, XLSTransfer), page components
- Subdirectories: `ldm/` (Translation Memory UI), `apps/` (tool UIs), `admin/` (admin features), `pages/` (page-level), `common/` (utilities)

**locaNext/src/lib/stores/**
- Purpose: Global reactive state (Svelte stores)
- Contains: `app.js` (auth, current app), `ldm.js` (file tree state), `sync.js` (sync status), `navigation.js` (page routing)
- Pattern: Writable stores with initialization on mount

**locaNext/src/lib/utils/**
- Purpose: Frontend utilities
- Contains: Logger, remote logging, formatters, validators

---

## Key File Locations

**Entry Points:**
- Backend: `server/main.py` - FastAPI app initialization and startup
- Frontend: `locaNext/src/routes/+layout.svelte` - App shell and global state setup

**Configuration:**
- Backend config: `server/config.py` - All environment settings, paths, security
- Frontend config: `locaNext/svelte.config.js` - SvelteKit and build settings
- Env file: `.env` (not in repo) - Runtime environment variables

**Core Logic:**
- API routes: `server/api/*.py` - Business logic endpoints
- Repositories: `server/repositories/*/` - Data access layer
- Components: `locaNext/src/lib/components/` - UI logic

**Testing:**
- Unit tests: `tests/test_*.py` - API and repository tests
- Dev testing: `testing_toolkit/DEV_MODE_PROTOCOL.md` - How to test locally
- Integration: `testing_toolkit/MASTER_TEST_PROTOCOL.md` - Full build/test cycle

**Database:**
- Models: `server/database/models.py` - All ORM models (User, Session, LogEntry, etc.)
- Migrations: `server/database/migrations/` - Alembic schema version control
- Runtime data: `server/data/` - Logs, backups, FAISS indexes, TM data

---

## Naming Conventions

**Files:**
- Backend Python: `{feature}_async.py` for async routes, `{feature}.py` for utilities
- Frontend Components: `{Feature}.svelte` (PascalCase)
- Frontend Stores: `{feature}.js` (camelCase)
- Tests: `test_{module}.py` (snake_case, pytest convention)

**Directories:**
- Backend: `{module}_name/` (snake_case)
- Frontend components: `{Feature}/` (PascalCase) or by feature area
- Utilities: `utils/` (singular in backend, plural used elsewhere)

**Functions/Methods:**
- Backend: `async_function_name()` (snake_case) or `snake_case_method()`
- Frontend: `functionName()` (camelCase)
- Svelte stores: `storeName` (camelCase), export as `writable()` or custom

**Variables/Constants:**
- Backend: `CONSTANT_NAME` (UPPERCASE), `variable_name` (snake_case)
- Frontend: `const variableName` (camelCase), `$state(value)` for Svelte 5 runes
- Store subscriptions: `const unsubscribe = store.subscribe()` (explicit cleanup)

**Database Tables:**
- Online (PostgreSQL): `ldm_{entity}` (e.g., `ldm_users`, `ldm_files`, `ldm_translation_memories`)
- Offline (SQLite): `offline_{entity}` (e.g., `offline_files`, `offline_translation_memories`)
- Server fallback (SQLite): `ldm_{entity}` (same as PostgreSQL)

---

## Where to Add New Code

**New Feature (Backend API):**
- API route: `server/api/{feature}_async.py` (FastAPI router)
- Repository interface: `server/repositories/interfaces/{feature}_repository.py` (abstract class)
- PostgreSQL impl: `server/repositories/postgresql/{feature}_repo.py`
- SQLite impl: `server/repositories/sqlite/{feature}_repo.py`
- Database model: Add to `server/database/models.py`
- Register route: Include in `server/main.py` via `app.include_router(router)`

**New Component (Frontend):**
- Implementation: `locaNext/src/lib/components/{Feature}.svelte` or `locaNext/src/lib/components/{area}/{Feature}.svelte`
- If using global state: Add store to `locaNext/src/lib/stores/{feature}.js`
- If tool-specific: Place in `locaNext/src/lib/components/apps/{ToolName}.svelte`

**New Utility Function:**
- Backend: `server/utils/{feature}.py`
- Frontend: `locaNext/src/lib/utils/{feature}.js`

**New Tool (XLSTransfer, QuickSearch, etc.):**
- API: Create `server/api/{tool}_async.py` inheriting from `BaseToolAPI`
- Register: Include in `server/main.py`
- Frontend: Create `locaNext/src/lib/components/apps/{ToolName}.svelte`
- Launch entry: Add to apps list in `locaNext/src/routes/+layout.svelte`

---

## Special Directories

**server/data/**
- Purpose: Runtime data, not source code
- Generated: Yes (created at startup)
- Committed: No (except template structure)
- Contents: Logs, cache, FAISS indexes, TM embeddings, backups, KR similarity dictionaries

**server/database/migrations/**
- Purpose: Alembic schema versioning
- Generated: No (manually created with `alembic revision --autogenerate`)
- Committed: Yes (track all schema changes)
- Contents: Python files per migration with up/down logic

**locaNext/.svelte-kit/**
- Purpose: SvelteKit generated client code and output
- Generated: Yes (by SvelteKit during build)
- Committed: No
- Contents: Compiled components, node resolution, server output

**locaNext/static/**
- Purpose: Static assets (images, fonts, etc.)
- Generated: No (hand-created)
- Committed: Yes
- Served as: `/` prefix in Electron app

**tests/**
- Purpose: Test suite
- Generated: No (manually written)
- Committed: Yes
- Run with: `pytest tests/` or specific test file

**.planning/codebase/**
- Purpose: GSD (Goal/Specification/Design) planning documents
- Generated: Yes (by GSD mapper)
- Committed: No (planning/ephemeral)
- Contents: ARCHITECTURE.md, STRUCTURE.md, CONVENTIONS.md, TESTING.md, CONCERNS.md

---

*Structure analysis: 2026-03-14*
