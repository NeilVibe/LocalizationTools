# P22: Production Parity - SQLite Removal

**Priority:** P22 | **Status:** Not Started | **Created:** 2025-12-11

---

## Goal

**DEV = PRODUCTION** - Remove all SQLite code from LocaNext core.

```
BEFORE (Current):
├── Config: PostgreSQL ✅
├── Runtime: PostgreSQL ✅
├── Code: SQLite fallbacks everywhere ❌ (dead code)
└── Tests: May test SQLite paths ❓

AFTER (Target):
├── Config: PostgreSQL ONLY ✅
├── Runtime: PostgreSQL ONLY ✅
├── Code: No SQLite references ✅
└── Tests: PostgreSQL ONLY ✅
```

**What KEEPS SQLite:**
- Gitea internal database (separate system)
- Autonomous testing scripts (if needed for temp storage)
- NOT LocaNext server/tools/frontend

---

## Phase 1: Server Code Cleanup (11 files)

### 1.1 Core Database Files

- [ ] **server/config.py** (1 reference)
  - Remove any SQLITE_DATABASE_URL if present
  - Verify DATABASE_URL = POSTGRES only
  - Update comments

- [ ] **server/database/db_setup.py** (12 references)
  - Remove `set_sqlite_pragma()` function
  - Remove SQLite URL generation
  - Remove `check_same_thread` conditionals
  - Remove SQLite engine creation path
  - Update docstrings (remove "SQLite" mentions)

- [ ] **server/database/db_utils.py** (15 references)
  - Remove `_bulk_copy_sqlite_fallback()` function
  - Remove `_upsert_batch_sqlite()` function
  - Remove `_fallback_like_search()` SQLite path
  - Remove dialect checks for SQLite
  - Update docstrings

- [ ] **server/database/models.py** (1 reference)
  - Update docstring: Remove "Supports both SQLite (dev) and PostgreSQL (prod)"
  - Change to: "PostgreSQL ORM models"

- [ ] **server/database/__init__.py** (1 reference)
  - Remove SQLite comment reference

### 1.2 API Files

- [ ] **server/api/admin_db_stats.py** (8 references)
  - Remove `_get_sqlite_stats()` function
  - Remove SQLite dialect check
  - Remove SQLite health warning
  - Update to PostgreSQL-only stats

- [ ] **server/api/stats.py** (12 references)
  - Remove `import sqlite3`
  - Remove SQLite version check
  - Remove `sqlite_master` queries
  - Remove SQLite date handling differences

- [ ] **server/api/base_tool_api.py** (2 references)
  - Remove `check_same_thread` conditional

- [ ] **server/utils/dependencies.py** (3 references)
  - Remove `sqlite+aiosqlite` URL conversion
  - Remove SQLite async pool comments

### 1.3 Tool Files

- [ ] **server/tools/xlstransfer/progress_tracker.py** (1 reference)
  - Remove `check_same_thread` conditional

### 1.4 Migration Files

- [ ] **server/database/migrations/add_user_profile_fields.py** (4 references)
  - Remove SQLite-specific ALTER TABLE handling
  - Use PostgreSQL syntax only

### 1.5 Backup Files

- [ ] **server/api/xlstransfer_async.py.backup** (4 references)
  - DELETE this file (it's a backup, not needed)

---

## Phase 2: Test Cleanup (9 files)

- [ ] **tests/conftest.py**
  - Remove SQLite test database setup if present
  - Ensure all fixtures use PostgreSQL

- [ ] **tests/unit/test_db_utils.py**
  - Remove SQLite fallback tests
  - Update to test PostgreSQL paths only

- [ ] **tests/unit/test_server/test_models.py**
  - Remove SQLite references

- [ ] **tests/unit/test_dependencies_module.py**
  - Remove SQLite async URL tests

- [ ] **tests/e2e/test_edge_cases_e2e.py**
  - Remove SQLite edge case tests

- [ ] **tests/integration/server_tests/test_logging_integration.py**
  - Remove SQLite references

- [ ] **tests/integration/server_tests/test_auth_integration.py**
  - Remove SQLite references

- [ ] **tests/integration/server_tests/test_server_startup.py**
  - Remove SQLite startup tests

- [ ] **tests/archive/test_full_workflow.py**
  - Review/delete if SQLite-dependent

---

## Phase 3: Documentation Cleanup (8 files)

### 3.1 Active Docs (Need Updates)

- [ ] **docs/deployment/GITEA_SETUP.md**
  - Clarify: Gitea uses SQLite (its own DB, not LocaNext)
  - Add note: LocaNext = PostgreSQL only

- [ ] **docs/company-setup/INSTALLATION.md**
  - Remove any SQLite installation steps
  - PostgreSQL-only instructions

- [ ] **docs/development/CODING_STANDARDS.md**
  - Remove SQLite coding patterns
  - Add: "No SQLite in LocaNext core"

### 3.2 History/Archive (Keep as-is, just note)

- [ ] **docs/history/P13_GITEA_CACHE_PLAN.md** - Historical, OK
- [ ] **docs/history/ROADMAP_ARCHIVE.md** - Historical, OK

### 3.3 Deprecated (Review/Delete)

- [ ] **docs/deprecated/QUICK_TEST_COMMANDS_OLD.md** - Delete if SQLite-focused
- [ ] **docs/deprecated/COMPLETE_WORKFLOW.md** - Update or delete
- [ ] **docs/deprecated/logs_error_summary.md** - Review

---

## Phase 4: Troubleshooting & Testing Docs

- [ ] **docs/troubleshooting/*.md** - Remove SQLite troubleshooting
- [ ] **docs/testing/*.md** - Update: Tests require PostgreSQL
- [ ] **docs/testing/PYTEST_GUIDE.md** - PostgreSQL setup required
- [ ] **docs/testing/QUICK_COMMANDS.md** - PostgreSQL commands only

---

## Phase 5: Verification

- [ ] Run full test suite against PostgreSQL
- [ ] Verify no SQLite imports remain: `grep -r "sqlite" server/`
- [ ] Verify no SQLite in tests: `grep -r "sqlite" tests/`
- [ ] Test fresh install with PostgreSQL only
- [ ] Verify CI/CD builds work

---

## Summary

| Phase | Files | Tasks |
|-------|-------|-------|
| Phase 1 | 11 server files | Remove SQLite code |
| Phase 2 | 9 test files | Update tests |
| Phase 3 | 8 doc files | Update docs |
| Phase 4 | ~5 doc files | Troubleshooting/Testing |
| Phase 5 | - | Verification |
| **Total** | **~33 files** | **Full cleanup** |

---

## Architecture After Cleanup

```
LocaNext Architecture (PostgreSQL ONLY)
═══════════════════════════════════════

┌─────────────────────────────────────────────────────────────┐
│                      LocaNext Desktop                        │
│                    (Electron + Svelte)                       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI Backend                          │
│                    (server/main.py)                          │
│                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ SQLAlchemy  │  │   asyncpg   │  │    psycopg2         │  │
│  │   2.x ORM   │  │  (async)    │  │    (sync)           │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      PgBouncer                               │
│                   (Port 6433)                                │
│              1000 connections pooled                         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     PostgreSQL 16                            │
│                    (Port 5432)                               │
│                                                              │
│  • 17 tables                                                 │
│  • COPY TEXT: 31K entries/sec                                │
│  • FTS: <10ms                                                │
│  • GIN indexes for similarity                                │
└─────────────────────────────────────────────────────────────┘

NO SQLITE IN THIS STACK (except Gitea's internal DB)
```

---

## Notes

- **Gitea SQLite**: Gitea uses its own SQLite database. This is SEPARATE from LocaNext and is fine.
- **Test Scripts**: Autonomous testing (CDP, Playwright) can use SQLite for temp storage if needed - this is outside LocaNext core.
- **Dev = Prod**: After this cleanup, development and production use identical database code.

---

*Created: 2025-12-11*
*Target: Full PostgreSQL parity*
