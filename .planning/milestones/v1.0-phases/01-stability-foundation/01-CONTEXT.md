# Phase 1: Stability Foundation - Context

**Gathered:** 2026-03-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Server starts reliably, DB layer works correctly across all 3 modes (Online/Server-Local/Offline), no zombie processes. This phase is about **proving correctness** — the architecture exists and is mature (9 repo interfaces, 35 files, 3-mode detection), but needs systematic verification that everything works identically across backends.

**Database is disposable** — wipe, rebuild, reinitialize freely. We're building for a demo, not preserving production data.

</domain>

<decisions>
## Implementation Decisions

### Verification Strategy
- Automated parity tests using pytest, parametrized by backend mode
- Test against **real PostgreSQL + real SQLite** — no mocks (prior incident with mock/prod divergence)
- Test **all 9 repositories**, no exceptions: File, Row, TM, Folder, Project, Platform, QA, Trash, Capability
- Test **all 3 modes explicitly**: Online (PostgreSQL), Server-Local (SQLite ldm_* tables), Offline (SQLite offline_* tables)
- **Every interface method** gets a parity test (~50+ test cases x 3 modes)
- **Behavioral equivalence** assertions — same inputs produce same business-meaningful outputs (ignore auto-increment IDs, timestamps, column ordering)
- **Fixture factory** with game-realistic data: Korean/English game strings, platforms -> projects -> folders -> files -> rows, TM entries, QA results
- CI + local: tests run on **every push to main** via Gitea CI, **hard gate** (failure = build failure)
- DB wiped and reinitialized **before each test** — full isolation, no test interdependencies

### Test Organization
- Tests live in `tests/stability/`
- **One test file per repo**: test_file_repo.py, test_tm_repo.py, test_row_repo.py, etc. (9 files)
- Naming convention: `test_{repo}_{method}[{mode}]` (e.g., `test_file_repo_create[online]`)
- Shared fixtures in `tests/stability/conftest.py`: db_setup, game_data_factory, mode_parametrize
- Additional test files: test_startup.py, test_schema_drift.py, test_zombie.py

### Startup Error Handling
- **Fail fast** with clear, human-readable errors on any startup issue (port occupied, DB unreachable, missing config)
- **Strict security validation** — missing or weak crypto keys/API keys = server refuses to start
- Success criterion: **10 consecutive clean starts** in both DEV mode AND Electron production mode
- **Zero ERROR-level log lines** during startup — warnings are allowed, errors are not
- Error surfacing: structured log block `[STARTUP FAILED] reason + suggested fix` + non-zero exit code in DEV; Electron shows error dialog in production
- Health check enhanced: current Python import checks + **DB connectivity check** (SQLite file accessible, PostgreSQL reachable if configured)

### Zombie Process Handling
- **Pre-startup port cleanup** in both DEV and Electron modes: check if port 8888 is occupied, kill stale process before spawning new backend
- **Automated post-shutdown check**: after each shutdown test, verify no python/node processes remain on ports 8888/5173
- Create **stop_all_servers.sh** script: mirror of start_all_servers.sh that kills backend (8888), Vite (5173), admin (5175) by port
- Zombie scenarios to test and harden: **Claude's Discretion** — prioritize force quit/Task Manager kill, second instance launch, crash during startup based on codebase analysis

### Schema Drift Guard
- **Automated schema comparison test**: parse both offline_schema.sql and database_schema.sql, compare table structures
- Derive actual column diff from SQL files, then **validate against OFFLINE_ONLY_COLUMNS** allowlist — catches both missing columns AND stale allowlist entries
- **SQL dialect compatibility audit**: grep all .py files for raw SQL strings, flag PostgreSQL-only constructs (RETURNING, ILIKE, ::type casts, array operations)
- **Assert SQLite PRAGMAs**: verify foreign_keys=ON, check_same_thread=false, journal_mode=WAL in tests
- All schema tests run in CI alongside parity tests — unified stability test suite

### Terminology Cleanup
- **Rename "SQLite Fallback" to "Server-Local"** across the codebase — all 3 modes are first-class, none is a "fallback"
- Three equal modes: Online (PostgreSQL), Server-Local (SQLite ldm_*), Offline (SQLite offline_*)

### Performance Baseline
- Startup time thresholds: **<5s DEV mode**, **<10s Electron** (icon click -> app usable). Measured in the 10-start reliability test
- DB connection must establish in **<1s**
- Individual repo operation speed: **tracked in parity tests** (logged) but no hard threshold in Phase 1. Data informs Phase 2 thresholds
- Electron demo startup: **under 10 seconds total** — executive attention span threshold

### CI Pipeline
- PostgreSQL **pre-installed on Gitea CI Windows runner**
- Stability tests run on **every push to main**
- **Hard gate**: test failure = build failure, blocks shipping

### Claude's Discretion
- Exact zombie process scenarios to test (force quit, second instance, crash) — prioritize by codebase risk
- Fixture data content — realistic game strings but Claude picks specific examples
- conftest.py internal structure
- stop_all_servers.sh implementation details

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- **9 Repository Interfaces** (`server/repositories/interfaces/`): Complete abstract definitions for all data operations
- **9 PostgreSQL Implementations** (`server/repositories/postgresql/`): Full async implementations with permission checks
- **9 SQLite Implementations** (`server/repositories/sqlite/`): Schema-aware with dual-table mapping (offline_*/ldm_*)
- **SQLite Base Class** (`server/repositories/sqlite/base.py`): SchemaMode enum, TABLE_MAP, lazy DB connection, `_table()` method for zero-duplication
- **RoutingRowRepository** (`server/repositories/routing/row_repo.py`): Negative ID routing for offline entities
- **DB Factory** (`server/repositories/factory.py`): 9 dependency injection functions with 3-mode detection
- **Health Check** (`locaNext/electron/health-check.js`): Python import validation with 15s timeout, auto-repair
- **Bootstrap Error Catcher** (`locaNext/electron/bootstrap.js`): Synchronous crash logging before any module loads
- **Start Script** (`scripts/start_all_servers.sh`): PostgreSQL + Backend + optional Vite startup
- **Check Script** (`scripts/check_servers.sh`): Server status + rate limit management
- **OFFLINE_ONLY_COLUMNS** (in SQLite base): Existing allowlist of sync-only columns

### Established Patterns
- **3-Mode Detection**: Authorization header (`Bearer OFFLINE_MODE_`) -> Offline, `config.ACTIVE_DATABASE_TYPE == "sqlite"` -> Server-Local, default -> Online
- **Process Lifecycle**: `detached: false` for backend spawn, triple cleanup hooks (window-closed, will-quit, before-quit), `taskkill /f /t` on Windows
- **Logging**: Loguru with file rotation (50MB), error logs, console output. Security audit log separate
- **Server Entry**: FastAPI app with lifespan manager (async startup/shutdown), Socket.IO wrapper, Uvicorn on 127.0.0.1:8888
- **DEV_MODE Flag**: Disables rate limiting, enables development features

### Integration Points
- **server/main.py:72-113**: Lifespan manager — startup/shutdown hooks where DB init and cleanup happen
- **server/config.py**: ACTIVE_DATABASE_TYPE, SECURITY_MODE, DEV_MODE — all relevant to stability testing
- **server/database/db_setup.py**: Auto-mode detection with socket timeout (3s), connection pooling config
- **server/database/offline.py**: OfflineDatabase singleton with well-known IDs (-1 platform, -1 project)
- **server/database/server_sqlite.py**: ServerSQLiteDatabase singleton
- **locaNext/electron/main.js:215-260**: Backend process spawning with health poll (30 retries x 1s)

</code_context>

<specifics>
## Specific Ideas

- "The DB right now can be refreshed and rebuilt on demand. We don't care. We need to get to the final product ready to be showcased as a demo for executives" — DB is fully disposable, wipe/reinitialize freely
- "It's not a fallback right? We have full abstraction so offline is technically not a fallback" — Rename "SQLite Fallback" terminology to "Server-Local" across codebase
- The 3 modes are equal peers through the same repository interfaces, not a degradation hierarchy

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-stability-foundation*
*Context gathered: 2026-03-14*
