# Phase 25: Comprehensive API E2E Testing - Context

**Gathered:** 2026-03-16
**Status:** Ready for planning
**Source:** Auto-discuss (--auto mode with recommended defaults)

<domain>
## Phase Boundary

Test every API endpoint E2E with mock data — complete CRUD workflows for files, rows, TMs, projects, folders, gamedata, codex, worldmap, AI intelligence, search, QA, grammar, merge, export, offline storage, admin stats, auth, sessions, and capabilities. Expand mock fixtures to cover all StaticInfo paths and entity types. Validate that mock paths mirror real production StaticInfo structure. Create a reusable test suite that can run headless for hours.

</domain>

<decisions>
## Implementation Decisions

### Test Framework & Execution
- [auto] Python pytest for API tests (existing infrastructure: 170+ test files, conftest.py, helpers/)
- [auto] Bash test script `testing_toolkit/api_test_protocol.sh` for quick smoke tests (already built, 89/91 passing)
- [auto] Tests must run headless with no user interaction — designed for overnight autonomous execution
- [auto] Each test category in its own file under `tests/api/` directory
- [auto] Use existing `tests/conftest.py` patterns for auth fixtures and API client setup
- [auto] Test execution order: health → auth → projects → files → rows → TM → gamedata → codex → worldmap → AI → search → QA → merge → export → offline → admin → tools

### Mock Data Expansion
- [auto] Expand `tests/fixtures/mock_gamedata/StaticInfo/` to cover ALL entity types with realistic data
- [auto] Add missing StaticInfo subdirectories: questinfo/, sceneobjectdata/, sealdatainfo/
- [auto] Each mock XML must have at least 10 entities with Korean StrOrigin + English Str + br-tag examples
- [auto] Mock paths MUST mirror real production StaticInfo structure exactly (folder names, nesting depth, file naming convention: `{type}.staticinfo.xml`)
- [auto] Add mock localization files (`.loc.xml`) for every entity type in `stringtable/export__/System/`
- [auto] Add mock `languagedata_*.xml` for KOR/ENG/FRE/DEU/JPN in `stringtable/loc/`
- [auto] Create mock Excel files (`.xlsx`) with EU 14-column format for upload testing
- [auto] Create mock TXT/TSV files with tab-delimited format for upload testing

### API Coverage Strategy (275 endpoints, 12 subsystems)
- [auto] **Auth (14 endpoints):** Login, register, user CRUD, activate/deactivate, password change, JWT validation
- [auto] **Files (18 endpoints):** Upload XML/Excel/TXT, list, get, download, convert, copy, move, rename, delete, register-as-TM
- [auto] **Rows (5 endpoints):** List with pagination/search/filter, update target, check QA per-row, grammar per-row
- [auto] **Projects/Folders (12 endpoints):** Full CRUD, tree, cross-project move, platform assignment
- [auto] **TM (19 endpoints):** Upload, entries CRUD, search (pattern + exact + semantic), suggest, build indexes, sync, export, pretranslate
- [auto] **GameData (3 endpoints):** Browse with depth, detect columns (all entity types), save inline edit with br-tag preservation
- [auto] **Codex (4 endpoints):** Types, list per type, search, get entity — verify all entity types return data
- [auto] **WorldMap (1 endpoint):** Full data with nodes, routes, bounds — verify 14 nodes, 13 routes
- [auto] **AI Intelligence (11 endpoints):** AI suggestions status + generate, naming status + suggest + similar, context status + detect + get, mapdata status + configure
- [auto] **Search (9 endpoints):** Explorer, semantic, TM suggest, TM exact, TM pattern, QuickSearch, QuickSearch multiline, KR-Similar, Codex search
- [auto] **QA/Grammar (13 endpoints):** File-level QA (line/pattern/term), row-level QA, QA results, QA summary, resolve, grammar check, QuickSearch QA tools
- [auto] **Admin/Stats (44 endpoints):** Overview, daily/weekly/monthly, performance, errors, DB health, telemetry, rankings, server logs
- [auto] **Offline (22 endpoints):** Status, files, subscriptions, sync, push, local storage CRUD, trash
- [auto] **Merge (3 endpoints):** Translator merge (all 5 match modes), gamedev merge, file merge with original
- [auto] **Tools (7+ endpoints):** QuickSearch health + dictionaries + search, KR-Similar, XLSTransfer
- [auto] **Misc (announcements, logging, progress operations, updates)**

### Validation & Assertions
- [auto] Every test asserts: HTTP status code, response schema fields, content correctness
- [auto] Round-trip tests: upload → edit → download → verify edits preserved
- [auto] XML br-tag preservation: upload with `<br/>` → download → verify `<br/>` intact
- [auto] Korean text round-trip: upload Korean StrOrigin → download → verify Unicode preserved
- [auto] Gamedata path validation: browse paths must match `StaticInfo/{type}info/{filename}.staticinfo.xml` pattern
- [auto] Codex entity cross-references: character → knowledge → image/audio chain must resolve
- [auto] WorldMap node positions: verify x/z coordinates parse correctly from mock FactionInfo
- [auto] TM suggest similarity: verify scores are 0.0-1.0 range and sorted descending
- [auto] Search result ordering: verify results have similarity/score fields

### Skills to Invoke During Execution
- [auto] **test-master skill** — test strategy, mocking, coverage analysis for every plan
- [auto] **test-generator skill** — scaffold new test files from endpoint schemas
- [auto] **xml-localization skill** — validate br-tag handling, Unicode safety, lxml patterns in mock data
- [auto] **xlsx skill** — create mock Excel files with EU 14-column format
- [auto] **python-pro skill** — type-annotated Python, pytest fixtures, async patterns
- [auto] **modern-python skill** — uv, ruff validation on test files
- [auto] **fastapi-expert skill** — validate API endpoint schemas match Pydantic models
- [auto] **debugging-wizard skill** — investigate any test failures
- [auto] **playwright-pro skill** — for any frontend integration tests that verify API results
- [auto] **sql-expert skill** — verify DB state after API operations (row counts, data integrity)
- [auto] **security-reviewer skill** — validate auth endpoints, JWT handling, capability checks
- [auto] **api-designer skill** — verify REST conventions, response schemas, error handling

### Claude's Discretion
- Exact pytest fixture organization and conftest structure
- Test helper utility design
- Mock data generation scripts vs static XML files
- Parallelization strategy for test execution
- Retry logic for flaky network tests
- Test report format

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### API Structure
- `server/tools/ldm/router.py` — Main LDM router, imports all sub-routers
- `server/tools/ldm/routes/` — All route files (files.py, rows.py, tm_crud.py, tm_search.py, etc.)
- `server/tools/ldm/schemas/` — Pydantic response/request models (row.py, file.py, codex.py, qa.py)
- `server/tools/ldm/file_handlers/xml_handler.py` — XML upload parsing (LocStr format requirements)
- `server/tools/ldm/services/xml_parsing.py` — XML engine (STRINGID_ATTRS, STRORIGIN_ATTRS, STR_ATTRS, LOCSTR_TAGS)

### Existing Tests
- `tests/conftest.py` — Shared pytest fixtures
- `tests/integration/test_ldm_api.py` — Existing API integration tests
- `tests/integration/test_api_endpoints_detailed.py` — Detailed endpoint tests
- `tests/integration/test_mock_gamedata_pipeline.py` — Gamedata pipeline tests
- `tests/e2e/test_complete_user_flow.py` — Full user workflow simulation

### Mock Data
- `tests/fixtures/mock_gamedata/StaticInfo/` — Mock StaticInfo tree (current: 6 subdirs, 25 XML files)
- `tests/fixtures/mock_gamedata/stringtable/` — Mock localization files
- `tests/fixtures/sample_language_data.txt` — Sample TXT upload data (63 rows)
- `tests/fixtures/sample_dictionary.xlsx` — Sample Excel file

### API Test Script
- `testing_toolkit/api_test_protocol.sh` — Bash E2E smoke test (89 tests, 12 subsystems)

### Protocols
- `testing_toolkit/DEV_MODE_PROTOCOL.md` — DEV mode testing protocol
- `testing_toolkit/MASTER_TEST_PROTOCOL.md` — Full test protocol

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tests/conftest.py`: Shared fixtures (auth tokens, API client, test DB setup)
- `tests/helpers/`: Test utility functions
- `testing_toolkit/api_test_protocol.sh`: Bash smoke test covering 89 endpoints
- 170+ Python test files across unit/integration/e2e/security/stability/performance
- 66 Playwright spec files for frontend E2E
- `tests/fixtures/mock_gamedata/`: 44 XML files with realistic game data

### Established Patterns
- pytest with async support for API tests
- Playwright for frontend E2E (login helper, page navigation)
- Mock gamedata uses real StaticInfo structure (characterinfo, iteminfo, skillinfo, etc.)
- Fixtures use real Korean text with `<br/>` tags
- `LanguageData > LocStr` wrapper format for XML uploads (NOT `<LocStr>` as root)

### Integration Points
- Backend runs on localhost:8888 (DEV_MODE=true disables rate limiting)
- Auth: POST /api/auth/login → JWT token → Authorization: Bearer header
- All LDM endpoints under /api/ldm/ prefix
- Tools endpoints under /api/v2/ prefix (quicksearch, kr-similar, xlstransfer)
- Admin endpoints under /api/v2/admin/ prefix

</code_context>

<specifics>
## Specific Ideas

- Tests should be designed for overnight autonomous execution (5+ hours unattended)
- Mock data paths must exactly mirror production StaticInfo structure
- Every API endpoint must be hit at least once — no untested endpoints
- br-tag round-trip is critical — this is a known pain point
- Korean Unicode preservation is critical — test CJK characters, Jamo, special symbols
- GameData columns detection must work for ALL entity types (item, character, skill, gimmick, knowledge, region)
- Codex cross-reference chain: character → knowledge_key → KnowledgeInfo → image/audio must resolve end-to-end
- TM 5-tier cascade search should be tested: hash exact → FAISS whole → hash line → FAISS line → fallback

</specifics>

<deferred>
## Deferred Ideas

- Performance/load testing (k6, Artillery) — separate phase
- Frontend visual regression testing (screenshot comparison) — separate phase
- CI/CD pipeline integration (run tests on every push) — separate phase
- Production monitoring/alerting based on test results — separate phase

</deferred>

---

*Phase: 25-comprehensive-api-e2e-testing*
*Context gathered: 2026-03-16 via auto-discuss*
