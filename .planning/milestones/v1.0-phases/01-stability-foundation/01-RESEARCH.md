# Phase 1: Stability Foundation - Research

**Researched:** 2026-03-14
**Domain:** Python/FastAPI backend stability, SQLite/PostgreSQL parity testing, process lifecycle management
**Confidence:** HIGH

## Summary

Phase 1 targets proving the existing 3-mode database architecture (Online/PostgreSQL, Server-Local/SQLite ldm_*, Offline/SQLite offline_*) is correct and complete. The codebase already has a mature repository pattern with 9 abstract interfaces, 9 PostgreSQL implementations, 9 SQLite implementations, and a factory with 3-mode detection. The work is primarily **verification and hardening**, not new feature development.

The key technical challenges are: (1) building a pytest fixture infrastructure that can spin up real PostgreSQL and SQLite databases, initialize schemas, and run every repository method against all 3 modes with behavioral equivalence assertions; (2) validating schema consistency between `offline_schema.sql` and the SQLAlchemy models used for PostgreSQL/server-SQLite; (3) ensuring startup reliability with port cleanup, health checks, and clear error surfacing; (4) preventing zombie processes on all shutdown scenarios.

**Primary recommendation:** Build the parity test infrastructure first (conftest.py with mode-parametrized fixtures and game-realistic data factory), then systematically test each repository. The schema drift guard and startup/zombie tests are independent and can be developed in parallel.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Automated parity tests using pytest, parametrized by backend mode
- Test against **real PostgreSQL + real SQLite** -- no mocks (prior incident with mock/prod divergence)
- Test **all 9 repositories**, no exceptions: File, Row, TM, Folder, Project, Platform, QA, Trash, Capability
- Test **all 3 modes explicitly**: Online (PostgreSQL), Server-Local (SQLite ldm_* tables), Offline (SQLite offline_* tables)
- **Every interface method** gets a parity test (~50+ test cases x 3 modes)
- **Behavioral equivalence** assertions -- same inputs produce same business-meaningful outputs (ignore auto-increment IDs, timestamps, column ordering)
- **Fixture factory** with game-realistic data: Korean/English game strings, platforms -> projects -> folders -> files -> rows, TM entries, QA results
- CI + local: tests run on **every push to main** via Gitea CI, **hard gate** (failure = build failure)
- DB wiped and reinitialized **before each test** -- full isolation, no test interdependencies
- Tests live in `tests/stability/`
- **One test file per repo**: test_file_repo.py, test_tm_repo.py, test_row_repo.py, etc. (9 files)
- Naming convention: `test_{repo}_{method}[{mode}]`
- Shared fixtures in `tests/stability/conftest.py`: db_setup, game_data_factory, mode_parametrize
- Additional test files: test_startup.py, test_schema_drift.py, test_zombie.py
- **Fail fast** with clear, human-readable errors on any startup issue
- **Strict security validation** -- missing or weak crypto keys/API keys = server refuses to start
- Success criterion: **10 consecutive clean starts** in both DEV mode AND Electron production mode
- **Zero ERROR-level log lines** during startup
- **Pre-startup port cleanup** in both DEV and Electron modes
- **Automated post-shutdown check**: verify no python/node processes remain on ports 8888/5173
- Create **stop_all_servers.sh** script
- **Automated schema comparison test**: parse both offline_schema.sql and database_schema.sql, compare table structures
- Derive actual column diff from SQL files, then **validate against OFFLINE_ONLY_COLUMNS** allowlist
- **SQL dialect compatibility audit**: grep all .py files for raw SQL strings, flag PostgreSQL-only constructs
- **Assert SQLite PRAGMAs**: verify foreign_keys=ON, check_same_thread=false, journal_mode=WAL in tests
- **Rename "SQLite Fallback" to "Server-Local"** across the codebase
- Startup time thresholds: **<5s DEV mode**, **<10s Electron**
- DB connection must establish in **<1s**
- PostgreSQL **pre-installed on Gitea CI Windows runner**
- Stability tests run on **every push to main** -- **hard gate**

### Claude's Discretion
- Exact zombie process scenarios to test (force quit, second instance, crash) -- prioritize by codebase risk
- Fixture data content -- realistic game strings but Claude picks specific examples
- conftest.py internal structure
- stop_all_servers.sh implementation details

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| STAB-01 | Server starts reliably every time without errors or zombie processes | Startup test infrastructure (test_startup.py), port cleanup patterns, error surfacing via loguru, 10-start reliability test |
| STAB-02 | Offline mode (SQLite) delivers full feature parity with online mode | Parity test infrastructure parametrized by mode, all 9 repos tested against all 3 modes with behavioral equivalence |
| STAB-03 | DB Factory and Repository pattern implementations work correctly across all repository interfaces | Factory pattern already exists; parity tests exercise every interface method through the factory |
| STAB-04 | No Python zombie processes on startup, shutdown, or crash recovery | Pre-startup port cleanup, post-shutdown process verification, stop_all_servers.sh |
| STAB-05 | SQLite schema matches PostgreSQL schema for all operations (no divergence bugs) | Schema drift guard test (test_schema_drift.py), OFFLINE_ONLY_COLUMNS validation, SQL dialect audit |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | 8.x | Test framework | Already configured in pytest.ini, async support via pytest-asyncio |
| pytest-asyncio | 0.23+ | Async test support | All repositories are async (aiosqlite + asyncpg), configured with `asyncio_mode = auto` |
| aiosqlite | 0.20+ | Async SQLite access | Already used by all SQLite repositories |
| SQLAlchemy | 2.x | PostgreSQL ORM + schema init | Already used for engine creation, model definitions, schema upgrades |
| loguru | 0.7+ | Structured logging | Already the project standard, used everywhere |
| psutil | 5.x+ | Process management for zombie detection | Needed for port/PID checks in tests and stop script |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| sqlparse | 0.5+ | Parse SQL schema files for drift guard | Schema comparison test needs to parse CREATE TABLE statements |
| pytest-timeout | 2.x | Test timeout enforcement | Prevent hanging tests on DB connection issues |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| sqlparse for schema parsing | regex | sqlparse handles edge cases (multi-line, comments) that regex misses |
| psutil for process checks | lsof/taskkill shell commands | psutil is cross-platform, already available in Python stdlib path |

**Installation:**
```bash
pip install psutil sqlparse pytest-timeout
```

Note: pytest, pytest-asyncio, aiosqlite, SQLAlchemy, loguru are already installed.

## Architecture Patterns

### Recommended Test Structure
```
tests/
├── conftest.py                    # Existing root conftest (keep as-is)
└── stability/
    ├── __init__.py
    ├── conftest.py                # Stability-specific fixtures
    ├── test_startup.py            # STAB-01: 10-start reliability
    ├── test_schema_drift.py       # STAB-05: Schema parity
    ├── test_zombie.py             # STAB-04: Process lifecycle
    ├── test_platform_repo.py      # STAB-02/03: Platform parity
    ├── test_project_repo.py       # STAB-02/03: Project parity
    ├── test_folder_repo.py        # STAB-02/03: Folder parity
    ├── test_file_repo.py          # STAB-02/03: File parity
    ├── test_row_repo.py           # STAB-02/03: Row parity
    ├── test_tm_repo.py            # STAB-02/03: TM parity
    ├── test_qa_repo.py            # STAB-02/03: QA parity
    ├── test_trash_repo.py         # STAB-02/03: Trash parity
    └── test_capability_repo.py    # STAB-02/03: Capability parity
```

### Pattern 1: Mode-Parametrized Parity Testing
**What:** Every repository test is parametrized across all 3 modes
**When to use:** All 9 repository test files
**Example:**
```python
# tests/stability/conftest.py
import pytest
from enum import Enum

class DbMode(Enum):
    ONLINE = "online"           # PostgreSQL
    SERVER_LOCAL = "server_local"  # SQLite ldm_* tables
    OFFLINE = "offline"         # SQLite offline_* tables

@pytest.fixture(params=[DbMode.ONLINE, DbMode.SERVER_LOCAL, DbMode.OFFLINE], ids=str)
def db_mode(request):
    """Parametrize all tests across 3 database modes."""
    return request.param

@pytest.fixture
async def platform_repo(db_mode, clean_db):
    """Get the correct repository implementation for current mode."""
    if db_mode == DbMode.ONLINE:
        from server.repositories.postgresql.platform_repo import PostgreSQLPlatformRepository
        return PostgreSQLPlatformRepository(clean_db.async_session, test_user)
    elif db_mode == DbMode.SERVER_LOCAL:
        from server.repositories.sqlite.platform_repo import SQLitePlatformRepository
        from server.repositories.sqlite.base import SchemaMode
        return SQLitePlatformRepository(schema_mode=SchemaMode.SERVER)
    else:  # OFFLINE
        from server.repositories.sqlite.platform_repo import SQLitePlatformRepository
        from server.repositories.sqlite.base import SchemaMode
        return SQLitePlatformRepository(schema_mode=SchemaMode.OFFLINE)
```

### Pattern 2: Behavioral Equivalence Assertions
**What:** Compare results ignoring auto-increment IDs, timestamps, column ordering
**When to use:** Every parity test assertion
**Example:**
```python
def assert_equivalent(result_a, result_b, ignore_fields=None):
    """Assert two repository results are behaviorally equivalent."""
    ignore = {"id", "created_at", "updated_at", "downloaded_at", "sync_status"} | (ignore_fields or set())

    if isinstance(result_a, dict) and isinstance(result_b, dict):
        keys = set(result_a.keys()) | set(result_b.keys())
        for key in keys - ignore:
            assert result_a.get(key) == result_b.get(key), f"Mismatch on '{key}': {result_a.get(key)} != {result_b.get(key)}"
    elif isinstance(result_a, list) and isinstance(result_b, list):
        assert len(result_a) == len(result_b), f"Length mismatch: {len(result_a)} vs {len(result_b)}"
        for a, b in zip(result_a, result_b):
            assert_equivalent(a, b, ignore_fields)
```

### Pattern 3: Game-Realistic Fixture Factory
**What:** Factory that creates a full hierarchy: platform -> project -> folder -> files -> rows + TM + entries
**When to use:** Every repository test needs realistic data
**Example:**
```python
@pytest.fixture
async def game_data(platform_repo, project_repo, folder_repo, file_repo, row_repo):
    """Create a realistic game localization data hierarchy."""
    platform = await platform_repo.create(name="PC", owner_id=1)
    project = await project_repo.create(name="Dark Souls IV", platform_id=platform["id"], owner_id=1)
    folder = await folder_repo.create(name="UI", project_id=project["id"])
    file = await file_repo.create(
        name="menu_strings.xml", original_filename="menu_strings.xml",
        format="xml", project_id=project["id"], folder_id=folder["id"]
    )
    await row_repo.bulk_create(file["id"], [
        {"row_num": 1, "source": "새 게임", "target": "New Game", "string_id": "MENU_001"},
        {"row_num": 2, "source": "계속하기", "target": "Continue", "string_id": "MENU_002"},
        {"row_num": 3, "source": "설정", "target": "Settings", "string_id": "MENU_003"},
    ])
    return {"platform": platform, "project": project, "folder": folder, "file": file}
```

### Pattern 4: Clean Database Per Test
**What:** Wipe and reinitialize database before each test function
**When to use:** All stability tests
**Example:**
```python
@pytest.fixture(autouse=True)
async def clean_db(db_mode):
    """Wipe and reinitialize database for complete test isolation."""
    if db_mode == DbMode.ONLINE:
        # Drop and recreate all ldm_* tables in PostgreSQL
        engine = create_async_engine(POSTGRES_TEST_URL)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        yield engine
        await engine.dispose()
    else:
        # Create fresh temp SQLite file
        import tempfile
        db_path = tempfile.mktemp(suffix=".db")
        # Initialize with appropriate schema
        if db_mode == DbMode.OFFLINE:
            _execute_schema(db_path, "server/database/offline_schema.sql")
        else:
            _init_server_sqlite(db_path)
        yield db_path
        os.unlink(db_path)
```

### Anti-Patterns to Avoid
- **Shared database state between tests:** Each test MUST get a fresh database. The existing root conftest.py uses `session`-scoped admin token fixtures that connect to a live server -- stability tests must NOT depend on a running server
- **Mocking database backends:** User explicitly rejected mocks due to prior mock/production divergence incident. Use real PostgreSQL and real SQLite
- **Testing through HTTP/API layer:** Stability tests should call repository methods directly, not through FastAPI routes. This isolates the data layer from auth/routing concerns
- **Ignoring async context:** All repository methods are `async`. Tests must use `pytest-asyncio` with proper async fixtures

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SQL schema parsing | Custom regex parser | sqlparse library | CREATE TABLE statements have many edge cases (defaults, constraints, multi-line) |
| Process port checking | Shell-out to `lsof`/`netstat` | psutil.net_connections() | Cross-platform, no subprocess overhead, better error handling |
| Database schema comparison | Manual column-by-column comparison | Parse both schemas into normalized dicts, then set-diff | Reliable, maintainable, catches additions and removals |
| Async test infrastructure | Custom event loop management | pytest-asyncio's `asyncio_mode = auto` | Already configured in pytest.ini |

**Key insight:** The repository pattern is already fully built. The work is 90% test infrastructure and 10% fixing issues the tests reveal.

## Common Pitfalls

### Pitfall 1: SQLite vs PostgreSQL Boolean Handling
**What goes wrong:** SQLite stores booleans as 0/1, PostgreSQL uses TRUE/FALSE. Direct comparison fails.
**Why it happens:** SQLite lacks a native boolean type. The SQLite repos already handle this with `bool(platform.get("is_restricted"))` normalization, but tests must account for it.
**How to avoid:** Behavioral equivalence assertions should compare Python booleans after normalization, not raw database values.
**Warning signs:** Tests passing for PostgreSQL but failing for SQLite on boolean fields.

### Pitfall 2: Auto-Increment ID Differences
**What goes wrong:** PostgreSQL uses SERIAL (starts at 1, increments), SQLite repos use negative timestamp-based IDs for offline mode (`-int(time.time() * 1000) % 1000000000`).
**Why it happens:** Negative IDs are a design choice for offline entities to distinguish local vs server data.
**How to avoid:** Parity assertions MUST ignore `id` field. Only assert non-null and type correctness for IDs.
**Warning signs:** Tests that assert exact ID values.

### Pitfall 3: PostgreSQL-Specific SQL in Codebase
**What goes wrong:** Found `RETURNING` clause in `server/utils/progress_tracker.py`. If any PostgreSQL-specific SQL leaks into repository code, SQLite mode will break.
**Why it happens:** Developers use PostgreSQL features out of habit.
**How to avoid:** The schema drift test should include a SQL dialect audit that greps for `RETURNING`, `ILIKE`, `::type` casts, array operations, `NOW()` vs `datetime('now')`.
**Warning signs:** Good news: grep found ZERO PostgreSQL-specific SQL in the repository implementations. The `RETURNING` is only in the progress tracker (not a repository).

### Pitfall 4: Timestamp Format Inconsistency
**What goes wrong:** PostgreSQL returns `datetime` objects, SQLite returns ISO format strings. Direct comparison fails.
**Why it happens:** Different drivers return different types.
**How to avoid:** Parity assertions should ignore timestamp fields or normalize both to strings before comparison.
**Warning signs:** Tests failing with `datetime` vs `str` type mismatches.

### Pitfall 5: Server-Local Mode Schema Initialization
**What goes wrong:** Server-Local mode (SQLite with ldm_* tables) initializes via SQLAlchemy `Base.metadata.create_all()`, while Offline mode uses `offline_schema.sql`. The schemas might not match.
**Why it happens:** Two different initialization paths for two different SQLite modes.
**How to avoid:** The schema drift test should compare the table structure created by SQLAlchemy `create_all()` against the `offline_schema.sql` tables (ignoring the known OFFLINE_ONLY_COLUMNS).
**Warning signs:** Tests passing for Offline mode but failing for Server-Local, or vice versa.

### Pitfall 6: Orphaned Port on Test Failure
**What goes wrong:** If a startup test fails mid-way, port 8888 may be left occupied, causing subsequent test failures.
**Why it happens:** Test teardown not running on exceptions.
**How to avoid:** Use pytest fixtures with `yield` and cleanup in the teardown block. Also, clean up ports in the test setup phase.
**Warning signs:** "Address already in use" errors in CI after a failed test run.

### Pitfall 7: Capability Repository Asymmetry
**What goes wrong:** `SQLiteCapabilityRepository` is explicitly a stub (admin-only, no multi-user in SQLite). It won't have full parity.
**Why it happens:** By design -- capability management doesn't apply offline.
**How to avoid:** Document expected behavioral differences for CapabilityRepo. Parity tests for this repo should verify the stub returns sensible defaults (empty lists, no errors) rather than expecting identical behavior.
**Warning signs:** Tests expecting full capability management in SQLite modes.

### Pitfall 8: pytest.ini Coverage Requirements
**What goes wrong:** Current pytest.ini has `--cov-fail-under=80`. New stability tests may not immediately achieve 80% coverage.
**Why it happens:** Stability tests are in a new `tests/stability/` directory.
**How to avoid:** Either run stability tests with `pytest tests/stability/` (separate from coverage-gated runs) or adjust coverage config. The pytest.ini already excludes `tests/api`, `tests/cdp`, `tests/e2e` via `norecursedirs` -- stability tests won't be auto-excluded but coverage thresholds shouldn't block them.
**Warning signs:** CI failures from coverage threshold, not test failures.

## Code Examples

### Example: Schema Drift Guard Test
```python
# tests/stability/test_schema_drift.py
import sqlparse
import re
from pathlib import Path

def parse_create_tables(sql_content: str) -> dict:
    """Parse SQL file and extract table structures."""
    tables = {}
    statements = sqlparse.parse(sql_content)
    for stmt in statements:
        sql = str(stmt).strip()
        if sql.upper().startswith("CREATE TABLE"):
            match = re.search(r'CREATE TABLE\s+(?:IF NOT EXISTS\s+)?(\w+)', sql, re.IGNORECASE)
            if match:
                table_name = match.group(1)
                # Extract column definitions
                cols = extract_columns(sql)
                tables[table_name] = cols
    return tables

def test_offline_schema_covers_ldm_tables():
    """Verify offline_schema.sql has matching tables for all ldm_* tables."""
    from server.repositories.sqlite.base import TABLE_MAP, OFFLINE_ONLY_COLUMNS

    offline_sql = Path("server/database/offline_schema.sql").read_text()
    offline_tables = parse_create_tables(offline_sql)

    for base_name, (offline_name, server_name) in TABLE_MAP.items():
        assert offline_name in offline_tables, f"Missing table {offline_name} in offline_schema.sql"

def test_offline_only_columns_complete():
    """Verify OFFLINE_ONLY_COLUMNS matches reality."""
    from server.repositories.sqlite.base import OFFLINE_ONLY_COLUMNS

    offline_sql = Path("server/database/offline_schema.sql").read_text()
    offline_tables = parse_create_tables(offline_sql)

    # For each offline table, find columns that don't exist in server equivalent
    # Compare against OFFLINE_ONLY_COLUMNS allowlist
    # Flag any discrepancies
```

### Example: Startup Reliability Test
```python
# tests/stability/test_startup.py
import subprocess
import time
import requests

def test_dev_startup_10_times():
    """STAB-01: Server starts successfully 10 consecutive times."""
    for attempt in range(10):
        # Kill any existing process on port 8888
        _cleanup_port(8888)

        # Start server
        proc = subprocess.Popen(
            ["python3", "server/main.py"],
            env={**os.environ, "DEV_MODE": "true", "DATABASE_MODE": "sqlite"},
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        try:
            start = time.time()
            # Wait for health check
            for _ in range(50):  # 5 seconds max
                try:
                    r = requests.get("http://127.0.0.1:8888/health", timeout=0.5)
                    if r.ok:
                        elapsed = time.time() - start
                        assert elapsed < 5.0, f"Startup took {elapsed:.1f}s (>5s threshold)"
                        break
                except requests.ConnectionError:
                    time.sleep(0.1)
            else:
                pytest.fail(f"Server didn't start on attempt {attempt + 1}")

            # Verify zero ERROR log lines
            stderr_output = proc.stderr.read1(4096).decode() if proc.stderr else ""
            assert "ERROR" not in stderr_output, f"ERROR in startup logs: {stderr_output}"
        finally:
            proc.terminate()
            proc.wait(timeout=5)
            _cleanup_port(8888)
```

### Example: Zombie Process Test
```python
# tests/stability/test_zombie.py
import psutil
import signal

def test_no_zombies_after_sigterm():
    """STAB-04: No orphaned processes after SIGTERM."""
    proc = _start_server()
    pid = proc.pid

    # Record child PIDs
    parent = psutil.Process(pid)
    children_before = parent.children(recursive=True)

    # Send SIGTERM
    proc.terminate()
    proc.wait(timeout=10)

    # Verify all children are gone
    time.sleep(1)
    for child in children_before:
        assert not child.is_running(), f"Zombie child process {child.pid} still running"

    # Verify port is free
    assert not _port_in_use(8888), "Port 8888 still occupied after shutdown"

def test_no_zombies_after_kill():
    """STAB-04: No orphaned processes after force kill (SIGKILL)."""
    proc = _start_server()
    pid = proc.pid

    # Force kill
    proc.kill()
    proc.wait(timeout=5)

    time.sleep(2)
    # Port should be free (or freed by pre-startup cleanup)
    # This tests whether next startup handles the orphaned port
```

### Example: SQLite PRAGMA Verification
```python
def test_sqlite_pragmas(db_mode, clean_db):
    """STAB-05: SQLite PRAGMAs are correctly set."""
    if db_mode == DbMode.ONLINE:
        pytest.skip("PRAGMA test only applies to SQLite modes")

    import sqlite3
    conn = sqlite3.connect(clean_db)

    # Foreign keys must be ON
    result = conn.execute("PRAGMA foreign_keys").fetchone()
    assert result[0] == 1, "foreign_keys PRAGMA not enabled"

    conn.close()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| "SQLite Fallback" terminology | "Server-Local" (3 equal modes) | This phase | Codebase rename in factory.py, base.py, db_utils.py (27 occurrences across 3 files) |
| No parity testing | Parametrized parity tests (3 modes x all methods) | This phase | Catches divergence bugs before they ship |
| Manual startup verification | Automated 10-start reliability test | This phase | CI-enforced startup reliability |
| Hope-based zombie prevention | Pre-startup port cleanup + post-shutdown verification | This phase | Deterministic process lifecycle |

## Open Questions

1. **PostgreSQL Test Database**
   - What we know: Production uses `localizationtools` database. Tests need a separate database to avoid data contamination.
   - What's unclear: Whether to use a dedicated `localizationtools_test` database or create/drop per test.
   - Recommendation: Use `localizationtools_test` database. Create once in session setup, wipe tables per test. Faster than create/drop database cycles.

2. **Server-Local SQLite Schema Initialization**
   - What we know: Server-Local mode creates tables via SQLAlchemy `Base.metadata.create_all()`. Offline mode uses `offline_schema.sql`. These are two different code paths for the same table structure.
   - What's unclear: Whether `create_all()` produces exactly the same ldm_* table columns as what the PostgreSQL repos expect.
   - Recommendation: The schema drift test should verify this. If discrepancies exist, they're bugs to fix in this phase.

3. **CapabilityRepository Parity Scope**
   - What we know: SQLiteCapabilityRepository is explicitly a stub. The factory comment says "no multi-user" in SQLite modes.
   - What's unclear: What minimal behavior should the stub provide for parity tests?
   - Recommendation: Test that stub methods don't raise exceptions and return empty/default values. Don't expect functional parity for admin-only features.

4. **CI PostgreSQL on Windows Runner**
   - What we know: Decision says "PostgreSQL pre-installed on Gitea CI Windows runner."
   - What's unclear: Whether it's already installed or needs to be set up.
   - Recommendation: Verify with `pg_isready` in CI workflow. If not installed, the CI setup is a prerequisite task.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 0.23+ |
| Config file | `pytest.ini` (exists, needs stability marker added) |
| Quick run command | `pytest tests/stability/ -x -q --no-cov` |
| Full suite command | `pytest tests/stability/ -v --tb=short` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| STAB-01 | Server starts 10/10 times, <5s DEV, zero errors | integration | `pytest tests/stability/test_startup.py -x` | Wave 0 |
| STAB-02 | SQLite offline delivers parity with PostgreSQL | unit | `pytest tests/stability/test_*_repo.py -x --no-cov` | Wave 0 |
| STAB-03 | All 9 repo interfaces work across all modes | unit | `pytest tests/stability/test_*_repo.py -x --no-cov` | Wave 0 |
| STAB-04 | No zombie processes after any shutdown scenario | integration | `pytest tests/stability/test_zombie.py -x` | Wave 0 |
| STAB-05 | Schema parity between SQLite and PostgreSQL | unit | `pytest tests/stability/test_schema_drift.py -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/stability/ -x -q --no-cov`
- **Per wave merge:** `pytest tests/stability/ -v --tb=short`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/stability/__init__.py` -- package marker
- [ ] `tests/stability/conftest.py` -- mode parametrization, clean_db, game_data_factory, behavioral equivalence helpers
- [ ] `tests/stability/test_platform_repo.py` -- covers STAB-02, STAB-03
- [ ] `tests/stability/test_project_repo.py` -- covers STAB-02, STAB-03
- [ ] `tests/stability/test_folder_repo.py` -- covers STAB-02, STAB-03
- [ ] `tests/stability/test_file_repo.py` -- covers STAB-02, STAB-03
- [ ] `tests/stability/test_row_repo.py` -- covers STAB-02, STAB-03
- [ ] `tests/stability/test_tm_repo.py` -- covers STAB-02, STAB-03
- [ ] `tests/stability/test_qa_repo.py` -- covers STAB-02, STAB-03
- [ ] `tests/stability/test_trash_repo.py` -- covers STAB-02, STAB-03
- [ ] `tests/stability/test_capability_repo.py` -- covers STAB-02, STAB-03
- [ ] `tests/stability/test_startup.py` -- covers STAB-01
- [ ] `tests/stability/test_schema_drift.py` -- covers STAB-05
- [ ] `tests/stability/test_zombie.py` -- covers STAB-04
- [ ] `scripts/stop_all_servers.sh` -- covers STAB-04
- [ ] Install: `pip install psutil sqlparse pytest-timeout`
- [ ] Add `stability` marker to pytest.ini
- [ ] pytest.ini: ensure `tests/stability` is not in `norecursedirs`

## Existing Codebase Findings

### Terminology Rename Scope (Verified)
The term "sqlite_fallback" / "SQLite fallback" appears in exactly **3 files** (27 total occurrences):
- `server/database/db_utils.py` (2 occurrences)
- `server/repositories/factory.py` (23 occurrences -- function name `_is_sqlite_fallback()` and docstrings)
- `server/repositories/sqlite/base.py` (2 occurrences)

Rename to "server_local" / "Server-Local" is well-scoped.

### SQL Dialect Safety (Verified)
Grep for PostgreSQL-specific constructs (`RETURNING`, `ILIKE`, `::type` casts) in `server/repositories/` found **zero matches**. The only `RETURNING` in the codebase is in `server/utils/progress_tracker.py` (not a repository). Repository implementations are dialect-safe.

### Existing Test Infrastructure
- `pytest.ini` exists with comprehensive configuration
- `asyncio_mode = auto` already configured
- Root `tests/conftest.py` has session-scoped admin fixtures (for API tests, not relevant for stability)
- No existing stability/parity tests exist

### Repository Interface Method Count (Per Interface)
Counted from the interface files:

| Repository | Abstract Methods | Notes |
|------------|-----------------|-------|
| Platform | 10 | get, get_all, create, update, delete, get_with_project_count, set_restriction, assign_project, check_name_exists, search, etc. |
| Project | ~10 | Similar CRUD + platform assignment |
| Folder | ~8 | CRUD + tree operations |
| File | ~14 | CRUD + row operations + search + cross-project move/copy |
| Row | ~12 | CRUD + bulk ops + history + similarity search |
| TM | ~25 | CRUD + assignments + entries + bulk + indexes + search |
| QA | ~6 | CRUD + file-scoped queries |
| Trash | ~6 | CRUD + restore + auto-expire |
| Capability | ~4 | Stub in SQLite |

**Total: ~95 methods across 9 repositories, x3 modes = ~285 test cases minimum.**

### Key Architecture Details
- **SchemaMode enum** (`OFFLINE`/`SERVER`) drives table name resolution via `_table()` method
- **TABLE_MAP** maps base names to (offline_name, server_name) pairs
- **OFFLINE_ONLY_COLUMNS** frozenset tracks columns unique to offline schema (sync tracking)
- **PostgreSQL repos** take `(db: AsyncSession, current_user: dict)` -- need test session + user
- **SQLite repos** take `(schema_mode: SchemaMode)` -- simpler construction
- **RoutingRowRepository** wraps row repos for negative ID routing -- needs separate testing

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection: `server/repositories/interfaces/*.py` (9 files), `server/repositories/sqlite/*.py` (10 files), `server/repositories/postgresql/*.py` (10 files)
- Direct codebase inspection: `server/repositories/factory.py` (3-mode detection logic)
- Direct codebase inspection: `server/repositories/sqlite/base.py` (SchemaMode, TABLE_MAP, OFFLINE_ONLY_COLUMNS)
- Direct codebase inspection: `server/database/offline_schema.sql` (377 lines, full offline schema)
- Direct codebase inspection: `server/database/database_schema.sql` (560 lines, PostgreSQL schema)
- Direct codebase inspection: `server/database/db_setup.py` (auto-mode detection, schema upgrade)
- Direct codebase inspection: `server/main.py` (lifespan, security validation, startup flow)
- Direct codebase inspection: `server/config.py` (DATABASE_MODE, SECURITY_MODE, all settings)
- Direct codebase inspection: `locaNext/electron/main.js` (process spawn, kill, health poll)
- Direct codebase inspection: `locaNext/electron/health-check.js` (Python import validation)
- Direct codebase inspection: `pytest.ini` (existing test configuration)
- Direct codebase inspection: `tests/conftest.py` (existing fixtures)

### Secondary (MEDIUM confidence)
- Grep audit for PostgreSQL-specific SQL constructs across `server/` directory
- Grep count for "sqlite_fallback" terminology across `server/` directory

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already in use or well-known pytest ecosystem
- Architecture: HIGH -- directly read all 35+ repository files, schema files, startup code
- Pitfalls: HIGH -- derived from actual codebase patterns (boolean handling, ID generation, schema init paths)
- Test infrastructure: HIGH -- pytest.ini and root conftest.py directly inspected

**Research date:** 2026-03-14
**Valid until:** 2026-04-14 (stable codebase, patterns won't change)
