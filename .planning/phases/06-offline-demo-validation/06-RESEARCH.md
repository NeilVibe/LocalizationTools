# Phase 6: Offline Demo Validation - Research

**Researched:** 2026-03-14
**Domain:** Offline/Online mode parity validation, SQLite vs PostgreSQL, demo reliability
**Confidence:** HIGH

## Summary

Phase 6 is a VALIDATION phase, not a feature-building phase. LocaNext already has a mature offline/online architecture (3-mode detection via repository pattern, 9 repository interfaces, SchemaMode enum, factory-based dependency injection). All routes from Phases 2-5.1 already use the repository pattern for database operations. The core CRUD operations (file, row, TM, QA, folder, project, platform, trash) are abstracted behind interfaces that work identically across PostgreSQL, SQLite SERVER, and SQLite OFFLINE modes.

The key risk areas are: (1) Phase 5/5.1 services (MapDataService, GlossaryService, ContextService, CategoryMapper) that are in-memory singletons -- they don't use the DB at all, so they should work identically offline, but their configuration/initialization path needs validation; (2) Semantic search (FAISS indexes + Model2Vec) which is already local -- needs validation that index loading works in SQLite-only mode; (3) Known schema drift between offline and server-local schemas (5 table pairs have documented mismatches in KNOWN_SCHEMA_DRIFT); (4) Frontend mode selection and API client behavior when the server auto-detects SQLite mode.

**Primary recommendation:** Build an end-to-end test suite that exercises the full demo narrative (upload -> edit -> TM match -> search -> QA -> context -> export) in SQLite-only mode, verify mode switching transparency, and confirm no error/degraded paths exist.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| OFFL-01 | Offline mode demo flow works flawlessly (disconnect network, keep working) | Existing 3-mode architecture, factory pattern, auto-detect. Needs E2E validation of full demo narrative in SQLite mode. |
| OFFL-02 | All core operations (upload, edit, search, export) function identically offline | Repository pattern ensures DB parity. Phase 5/5.1 in-memory services (MapData, Glossary, Context) are DB-independent. Semantic search uses local FAISS. Needs systematic endpoint-by-endpoint validation. |
| OFFL-03 | Mode switching is transparent -- user doesn't need to know or configure anything | Launcher has [Start Offline] button and auto-detect. `_is_server_local()` checks `config.ACTIVE_DATABASE_TYPE`. Needs validation of auto-fallback behavior and frontend UX in offline path. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | 8.x | Backend validation tests | Already in use, stability tests exist |
| pytest-asyncio | auto mode | Async repo test support | Already configured in pytest.ini |
| Playwright | latest | Frontend E2E offline flow tests | Already used for all Phases 2-5 E2E tests |
| httpx | latest | API endpoint validation | Already used in api/ test directory |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| sqlparse | latest | Schema drift analysis | Already used in stability/test_schema_drift.py |

### Alternatives Considered
None -- this phase uses existing test infrastructure exclusively. No new libraries needed.

## Architecture Patterns

### Existing Architecture (DO NOT MODIFY)

The offline/online mode is already fully architected:

```
server/repositories/
  factory.py           # 3-mode detection: _is_offline_mode() + _is_server_local()
  interfaces/          # 9 ABC interfaces (TM, File, Row, Folder, Project, Platform, QA, Trash, Capability)
  postgresql/          # PostgreSQL implementations
  sqlite/              # SQLite implementations (SchemaMode.OFFLINE / SchemaMode.SERVER)
  routing/             # RoutingRowRepository (negative ID routing)

server/tools/ldm/
  routes/              # All routes use Depends(get_*_repository) -- never direct DB
  services/            # In-memory singletons (MapData, Glossary, Context, CategoryMapper)

server/database/
  offline.py           # SQLite offline database init
  offline_schema.sql   # Offline schema definition
  db_setup.py          # Sets config.ACTIVE_DATABASE_TYPE at startup
```

### Pattern: Repository Pattern (Already Implemented)

```python
# Routes inject repos via factory -- mode is transparent
@router.post("/files/{file_id}/check-qa")
async def check_file_qa(
    qa_repo: QAResultRepository = Depends(get_qa_repository),  # Auto-selects mode
    row_repo: RowRepository = Depends(get_row_repository),
    tm_repo: TMRepository = Depends(get_tm_repository),
):
    ...
```

### Pattern: In-Memory Services (Phase 5/5.1)

These services do NOT use the database -- they load data from file system:
- **MapDataService** -- loads staticinfo from Perforce branch/drive paths
- **GlossaryService** -- builds AC automaton from game data XML files
- **ContextService** -- combines Glossary + MapData for entity resolution
- **CategoryMapper** -- loads category rules from QACompiler patterns

**Implication for offline:** These services work identically in any mode since they never touch the database. The only dependency is file system paths (branch/drive), which are configured via `/mapdata/configure` endpoint.

### Pattern: Mode Detection (3-Mode)

```
Request comes in:
  1. Header has "Bearer OFFLINE_MODE_xxx" -> SQLite OFFLINE (offline_* tables)
  2. config.ACTIVE_DATABASE_TYPE == "sqlite" -> SQLite SERVER (ldm_* tables)
  3. Default -> PostgreSQL (ldm_* tables)
```

### Anti-Patterns to Avoid
- **Direct DB access in routes** -- all routes already use repository pattern, but validate no regressions
- **Assuming PostgreSQL-only features** -- schema drift guard test catches `RETURNING`, `ILIKE`, `::` casts
- **Hardcoded online assumptions** -- e.g., WebSocket features should gracefully degrade offline

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Mode parity testing | Custom comparison framework | Existing stability/conftest.py `assert_equivalent()` + `_make_repo()` | Already handles volatile field normalization, SQLite bool casting |
| Schema drift detection | Manual column comparison | Existing `test_schema_drift.py` KNOWN_SCHEMA_DRIFT tracking | Already catches new drift, documents known mismatches |
| API client mode switching | Custom mode interceptor | Existing `api/client.js` with `offlineMode` store | Frontend already handles token-based mode detection |
| Repo fixture creation | Per-test setup | Existing `game_data_factory` fixture | Creates full hierarchy (platform -> project -> folder -> file -> rows) |

## Common Pitfalls

### Pitfall 1: Schema Drift Between Offline and Server-Local
**What goes wrong:** Offline schema (offline_schema.sql) and server-local schema (SQLAlchemy models) have documented mismatches.
**Why it happens:** Two different init paths produce slightly different schemas.
**Known drift (from KNOWN_SCHEMA_DRIFT):**
- `files`: server has `created_by`, offline does not
- `rows`: offline has `created_at`, server does not
- `tms`: server has `line_pairs, whole_pairs, storage_path, indexed_at`, offline does not
- `tm_entries`: server has `created_at`, offline does not
- `qa_results`: server has `check_type`, offline does not (CRITICAL: QA may fail in OFFLINE mode)
**How to avoid:** Run existing schema drift tests. For QA, verify offline_qa_results DOES have check_type column (it does -- the KNOWN_SCHEMA_DRIFT may be stale since offline_schema.sql clearly defines it).
**Warning signs:** `sqlite3.OperationalError: no such column` errors in specific modes.

### Pitfall 2: In-Memory Services Not Initialized
**What goes wrong:** MapDataService/GlossaryService/ContextService return empty results or 503 because they haven't been configured.
**Why it happens:** These services require a `/mapdata/configure` call with valid branch/drive paths. In offline demo scenarios, the Perforce paths may not exist.
**How to avoid:** Validate that these services return graceful empty responses (not errors) when not configured. The services already have status endpoints and graceful degradation.
**Warning signs:** 500 errors from context or mapdata endpoints.

### Pitfall 3: FAISS Index Loading in SQLite Mode
**What goes wrong:** Semantic search returns "index not built" even though indexes exist.
**Why it happens:** TMIndexer saves indexes to filesystem paths that may depend on TM ID conventions. Negative IDs (offline) may create invalid paths.
**How to avoid:** Verify FAISS index loading works with SQLite-mode TM IDs. TMLoader already handles 3-mode source detection (negative ID -> OFFLINE, ACTIVE_DATABASE_TYPE == "sqlite" -> SERVER).
**Warning signs:** Semantic search returns empty results in SQLite mode but works in PostgreSQL mode.

### Pitfall 4: Frontend Mode Selection Doesn't Flow Through
**What goes wrong:** User clicks "Start Offline" in Launcher but API calls still try to reach PostgreSQL.
**Why it happens:** The `offlineMode` store flag may not properly set the `OFFLINE_MODE_` token prefix on all requests.
**How to avoid:** E2E test: click "Start Offline" in Launcher, then verify all subsequent API calls include the correct token.
**Warning signs:** 401 errors or PostgreSQL connection errors after choosing offline mode.

### Pitfall 5: WebSocket/Real-time Features Error in Offline
**What goes wrong:** WebSocket connection attempts throw errors when server is offline-only.
**Why it happens:** WebSocket is available only in online multi-user mode.
**How to avoid:** Verify WebSocket gracefully disconnects/disables in offline mode without error UI.
**Warning signs:** Console errors about WebSocket connection failures, error toasts in UI.

### Pitfall 6: Grammar Check (LanguageTool) Offline
**What goes wrong:** Grammar check fails because LanguageTool server is not available offline.
**Why it happens:** LanguageTool is a separate server that requires network.
**How to avoid:** This is already documented as "Grammar/Spelling: Online only". Verify it's either hidden or gracefully disabled in offline mode.
**Warning signs:** Grammar check button visible but throws errors in offline mode.

## Code Examples

### Existing Stability Test Pattern (Source: tests/stability/conftest.py)
```python
# Tests run parametrized across all 3 modes
@pytest.fixture(params=[DbMode.ONLINE, DbMode.SERVER_LOCAL, DbMode.OFFLINE], ids=str)
def db_mode(request) -> DbMode:
    return request.param

# Repository created for test mode
def _make_repo(db_mode, clean_db, repo_class, schema_mode):
    repo = repo_class(schema_mode=schema_mode)
    repo._db = _make_test_db(db_mode, clean_db)
    return repo
```

### Existing Factory Pattern (Source: server/repositories/factory.py)
```python
def get_tm_repository(request, db, current_user) -> TMRepository:
    if _is_offline_mode(request):
        return SQLiteTMRepository(schema_mode=SchemaMode.OFFLINE)
    elif _is_server_local():
        return SQLiteTMRepository(schema_mode=SchemaMode.SERVER)
    else:
        return PostgreSQLTMRepository(db, current_user)
```

### Mode Auto-Detection (Source: server/main.py)
```python
# At startup, db_setup.py sets config.ACTIVE_DATABASE_TYPE
# If PostgreSQL fails -> falls back to "sqlite" automatically
is_online = config.ACTIVE_DATABASE_TYPE == "postgresql"
```

### Graceful Service Degradation (Source: server/tools/ldm/routes/context.py)
```python
# Context service returns empty context (not errors) when not loaded
service = get_context_service()
result = service.resolve_context_for_row(string_id, source_text)
return EntityContextResponse(**result.to_dict())  # Empty entities if not configured
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Fallback pattern (try PG, catch, try SQLite) | Repository pattern with factory injection | P10 (completed) | All routes use Depends(), mode is transparent |
| Per-endpoint offline handling | Centralized 3-mode detection | ARCH-001 | Single _is_offline_mode() + _is_server_local() |
| No parity testing | Parametrized stability tests across 3 modes | Phase 1 (completed) | 9 repo interfaces x 2 SQLite modes tested |

**What already works:**
- All 9 repository interfaces have SQLite implementations
- Schema drift guard tests catch new mismatches
- Template DB caching for fast test execution
- Full game data hierarchy fixture (platform->project->folder->file->rows)
- Frontend Launcher with [Start Offline] / [Login] buttons
- API client handles OFFLINE_MODE_ token prefix

## Open Questions

1. **QA check_type in KNOWN_SCHEMA_DRIFT**
   - What we know: KNOWN_SCHEMA_DRIFT says qa_results server has `check_type` but offline doesn't. However, `offline_schema.sql` clearly defines `check_type TEXT NOT NULL` in `offline_qa_results`.
   - What's unclear: Is KNOWN_SCHEMA_DRIFT stale? This needs validation.
   - Recommendation: Run `test_schema_drift.py` to verify current state. If stale, clean up KNOWN_SCHEMA_DRIFT.

2. **Export Workflow in Offline Mode**
   - What we know: `/files/{id}/convert` is listed as offline-supported. Export workflow produces correct output files.
   - What's unclear: Whether the full export round-trip (XML with br-tags preservation) has been tested in SQLite-only mode.
   - Recommendation: Include export round-trip in the E2E validation test.

3. **TM Auto-Mirror in Offline Mode**
   - What we know: Auto-mirror uses folder-level scope. Decision says "auto-mirror failure is non-blocking (try/except with warning log)".
   - What's unclear: Whether auto-mirror creates TMs correctly when the only database is SQLite.
   - Recommendation: Test file upload -> verify TM mirror created in SQLite TM table.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio (auto mode) + Playwright |
| Config file | `pytest.ini` (root) + `locaNext/playwright.config.ts` |
| Quick run command | `pytest tests/stability/ -x -q` |
| Full suite command | `pytest tests/stability/ tests/unit/ldm/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| OFFL-01 | Full demo flow works offline | E2E (Playwright) | `cd locaNext && npx playwright test tests/offline-demo-flow.spec.ts` | No - Wave 0 |
| OFFL-01 | Server starts in SQLite mode | integration | `pytest tests/stability/test_startup.py -x` | Yes |
| OFFL-02 | Upload works in SQLite mode | E2E | `cd locaNext && npx playwright test tests/offline-upload.spec.ts` | No - Wave 0 |
| OFFL-02 | Edit+save works in SQLite mode | E2E | `cd locaNext && npx playwright test tests/offline-edit.spec.ts` | No - Wave 0 |
| OFFL-02 | Search works in SQLite mode | E2E | `cd locaNext && npx playwright test tests/offline-search.spec.ts` | No - Wave 0 |
| OFFL-02 | Export works in SQLite mode | E2E | `cd locaNext && npx playwright test tests/offline-export.spec.ts` | No - Wave 0 |
| OFFL-02 | QA checks work in SQLite mode | unit | `pytest tests/unit/ldm/test_routes_qa.py -x` | Yes |
| OFFL-02 | Context/MapData graceful in offline | unit | `pytest tests/unit/ldm/test_routes_context.py -x` | Yes |
| OFFL-02 | All repo operations parity | unit | `pytest tests/stability/test_*_repo.py -x` | Yes (9 files) |
| OFFL-03 | Mode auto-detection works | integration | `pytest tests/api/test_p3_offline_sync.py::TestOfflineStatus -x` | Yes |
| OFFL-03 | Launcher offline flow works | E2E | `cd locaNext && npx playwright test tests/offline-launcher.spec.ts` | No - Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/stability/ -x -q` (fast: <30s)
- **Per wave merge:** `pytest tests/stability/ tests/unit/ldm/ -v` + Playwright offline tests
- **Phase gate:** Full suite green + manual demo walkthrough

### Wave 0 Gaps
- [ ] `locaNext/tests/offline-demo-flow.spec.ts` -- full narrative E2E test (OFFL-01)
- [ ] Backend SQLite-mode integration test for full workflow (upload->edit->search->export)
- [ ] Verify KNOWN_SCHEMA_DRIFT is current (stale entries may cause false confidence)
- [ ] Test semantic search with SQLite-mode TM IDs
- [ ] Test WebSocket graceful degradation in offline mode

## Sources

### Primary (HIGH confidence)
- `server/repositories/factory.py` -- 3-mode detection, all 9 factory functions verified
- `server/database/offline_schema.sql` -- full offline schema with QA tables, sync metadata
- `docs/architecture/OFFLINE_ONLINE_MODE.md` -- comprehensive architecture doc
- `docs/architecture/ARCHITECTURE_SUMMARY.md` -- system overview with repository pattern
- `tests/stability/conftest.py` -- parity test infrastructure with fixtures
- `tests/stability/test_schema_drift.py` -- known drift documentation
- `server/tools/ldm/routes/` -- all route files verified to use Depends(get_*_repository)

### Secondary (MEDIUM confidence)
- Phase 5/5.1 services (mapdata, glossary, context) -- code review confirms they're DB-independent
- Frontend launcher store/component -- code review confirms mode selection flow

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all existing tools, no new dependencies
- Architecture: HIGH -- repository pattern fully implemented, documented, tested
- Pitfalls: HIGH -- schema drift tracked, known issues documented, services have graceful degradation
- Test gaps: MEDIUM -- existing parity tests cover repos, but full E2E offline flow untested

**Research date:** 2026-03-14
**Valid until:** Indefinite (architecture is stable, this is validation work)
