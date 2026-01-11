# P22: Production Parity - SQLite Removal

**Priority:** P22 | **Status:** Phase 1 COMPLETE ✅ | **Created:** 2025-12-11

---

## Goal

**DEV = PRODUCTION** - Remove all SQLite code from LocaNext core.

```
BEFORE:
├── Config: PostgreSQL ✅
├── Runtime: PostgreSQL ✅
├── Code: SQLite fallbacks everywhere ❌ (dead code)
└── Tests: May test SQLite paths ❓

AFTER (ACHIEVED):
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

## Phase 1: Server Code Cleanup (11 files) ✅ COMPLETE

### 1.1 Core Database Files ✅

- [x] **server/config.py** - Verified PostgreSQL only
- [x] **server/database/db_setup.py** - Complete rewrite, PostgreSQL only
- [x] **server/database/db_utils.py** - Removed all SQLite fallbacks
- [x] **server/database/models.py** - Updated docstring
- [x] **server/database/__init__.py** - Updated comment

### 1.2 API Files ✅

- [x] **server/api/admin_db_stats.py**
  - Removed `_get_sqlite_stats()` function
  - Changed SQLite branch to return error
  - Health check returns "critical" for non-PostgreSQL

- [x] **server/api/stats.py**
  - Replaced `func.strftime()` with PostgreSQL `func.to_char()`
  - Removed SQLite date handling comments
  - Rewrote `/database` endpoint to use PostgreSQL system tables

- [x] **server/api/base_tool_api.py**
  - Removed `check_same_thread` conditionals (2 locations)

- [x] **server/utils/dependencies.py**
  - Removed SQLite async URL handling
  - Removed `use_postgres` parameter usage

### 1.3 Tool Files ✅

- [x] **server/tools/xlstransfer/progress_tracker.py**
  - Removed `check_same_thread` conditional

### 1.4 Migration Files ✅

- [x] **server/database/migrations/add_user_profile_fields.py**
  - Removed SQLite-specific ALTER TABLE handling
  - PostgreSQL syntax only

### 1.5 Backup Files ✅

- [x] **server/api/xlstransfer_async.py.backup** - DELETED
- [x] **server/data/localizationtools.db.backup_20251203_221120** - DELETED

### 1.6 Additional Fixes ✅

- [x] Added `is_postgresql()` stub that always returns True (for compatibility)
- [x] Updated test `test_sqlite_returns_false` → `test_always_returns_true`

### Verification ✅

```bash
# All 595 unit tests pass
python3 -m pytest tests/unit/ -v  # 595 passed

# SQLite references remaining (comments only):
grep -r "sqlite" server/
# server/database/db_setup.py:5:PostgreSQL only - no SQLite support.
# server/config.py:129:# Database type - PostgreSQL is REQUIRED (no SQLite)
```

---

## Phase 2: Test Cleanup (PENDING)

- [ ] **tests/conftest.py** - Review for SQLite references
- [ ] **tests/unit/test_db_utils.py** - Already updated
- [ ] **tests/unit/test_dependencies_module.py** - Already updated
- [ ] Other test files as needed

---

## Phase 3: Documentation Cleanup (PENDING)

- [ ] Update docs to reflect PostgreSQL-only architecture
- [ ] Remove SQLite troubleshooting sections
- [ ] Update installation guides

---

## Summary

| Phase | Status | Files Changed |
|-------|--------|---------------|
| Phase 1 | ✅ COMPLETE | 12 files |
| Phase 2 | 📋 PENDING | ~5 test files |
| Phase 3 | 📋 PENDING | ~8 doc files |

---

## Architecture (Current)

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

*Updated: 2025-12-11 - Phase 1 Complete*
