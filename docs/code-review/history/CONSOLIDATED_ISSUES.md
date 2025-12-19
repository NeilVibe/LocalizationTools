# Consolidated Issues - Fix Plan

**Created:** 2025-12-12 | **Status:** Phase 2 Complete | **Total Open:** 31

---

## Overview

31 open issues from 12 Deep Review sessions, grouped by type for efficient batch fixing.

| Group | Issues | Priority | Est. Effort |
|-------|--------|----------|-------------|
| **A. Hardcoded URLs** | 4 | MEDIUM | Quick |
| **B. Database/SQL** | 6 | MEDIUM | Medium |
| **C. Async/Sync Mixing** | 5 | MEDIUM | Medium |
| **D. Auth Refactor** | 5 | MEDIUM | Medium |
| **E. Code Bugs** | 8 | MEDIUM | Quick |
| **F. Performance** | 2 | MEDIUM | Later |
| **G. DEV_MODE Feature** | 1 | MEDIUM | Medium |

---

## Group A: Hardcoded URLs (4 issues)

**Single fix:** Create centralized config, update all files.

| Issue | File | Line |
|-------|------|------|
| DR10-001 | `locaNext/src/lib/components/ldm/VirtualGrid.svelte` | 20 |
| DR10-002 | `locaNext/src/lib/components/ldm/DataGrid.svelte` | 25 |
| DR11-001 | `adminDashboard/src/lib/api/client.js` | 6 |
| DR8-001 | `server/api/stats.py` (13 endpoints) | Various |

**Fix Plan:**
1. VirtualGrid/DataGrid: Import `serverUrl` from stores
2. Admin client: Use environment variable `VITE_API_URL`
3. Stats endpoints: Implement DEV_MODE flag (Group G) to handle properly

---

## Group B: Database/SQL Issues (6 issues)

**Batch fix:** Single migration + code update.

| Issue | File | Problem |
|-------|------|---------|
| DR1-001 | `db_setup.py:154` | get_table_counts() incomplete |
| DR1-002 | `db_utils.py:637` | chunked_query() no ORDER BY |
| DR1-003 | `db_utils.py:676` | upsert_batch() return incorrect |
| DR1-004 | `models.py:899` | LDMTrash.item_data → JSONB |
| DR1-005 | `models.py` (9 cols) | JSON → JSONB migration |
| DR3-004 | `auth.py:176` | list_users no ORDER BY |

**Fix Plan:**
1. Create Alembic migration for JSON→JSONB (DR1-004, DR1-005)
2. Fix chunked_query default ORDER BY (DR1-002)
3. Fix list_users ORDER BY (DR3-004)
4. Fix upsert_batch return value (DR1-003)
5. Make get_table_counts dynamic (DR1-001)

**Migration SQL:**
```sql
-- All in one migration
ALTER TABLE ldm_trash ALTER COLUMN item_data TYPE JSONB USING item_data::JSONB;
ALTER TABLE log_entries ALTER COLUMN extra_data TYPE JSONB USING extra_data::JSONB;
-- ... (9 columns total)
```

---

## Group C: Async/Sync Mixing (5 issues)

**Theme:** Sync operations blocking async event loop.

| Issue | File | Problem |
|-------|------|---------|
| DR2-001 | `dependencies.py:76` | Async pool hardcoded |
| DR2-002 | `dependencies.py:114` | Auto-commit in get_async_db |
| DR2-004 | `websocket.py:62` | Deprecated asyncio call |
| DR4-001 | `ldm/api.py:867` | Sync session in async endpoint |
| DR4-002 | `ldm/api.py:969,1003,1028` | Repeated sync pattern |

**Fix Plan:**
1. Use config values for async pool (DR2-001)
2. Document auto-commit behavior (DR2-002)
3. Replace deprecated `asyncio.get_event_loop().time()` (DR2-004)
4. Create async TMManager methods (DR4-001, DR4-002)

---

## Group D: Auth Refactor (5 issues)

**Theme:** Sync vs async auth, security hardening.

| Issue | File | Problem |
|-------|------|---------|
| DR3-002 | `auth.py` vs `auth_async.py` | Duplicate endpoints |
| DR3-003 | `auth.py` | Sync missing audit logging |
| DR3-005 | Both auth files | No rate limiting |
| DR3-006 | `auth_async.py:422,496` | Hardcoded role validation |

**Fix Plan:**
1. Deprecate sync auth.py (add warning, redirect to async)
2. Add rate limiting via slowapi or audit_logger
3. Create VALID_ROLES constant in models.py
4. Keep audit logging in async version only

---

## Group E: Code Bugs (8 issues)

**Quick fixes:** Individual file edits.

| Issue | File | Problem | Fix |
|-------|------|---------|-----|
| DR2-003 | `cache.py:159` | MD5 unclear | Add comment |
| DR2-005 | `progress_tracker.py:292` | str() instead of json.dumps() | Change to json.dumps() |
| DR4-004 | `tm.py:132` | TODO stub returns [] | Implement or remove |
| DR5-001 | `xlstransfer/core.py:80` | Single-letter columns only | Fix algorithm |
| DR5-002 | `embeddings.py:56` | Model save no try/except | Add error handling |
| DR5-003 | `xlstransfer/core.py:22` | Duplicate clean_text | Use text_utils |
| DR6-001 | `parser.py:35` | Missing import re | Add import |
| DR6-002 | `qa_tools.py:107` | lxml not guarded | Add HAS_LXML check |
| DR7-001 | `kr_similar/embeddings.py:401` | Bare except | Use Exception |

**Fix Plan:** Fix each individually, one commit per file or logical group.

---

## Group F: Performance (2 issues)

**Defer:** Not blocking, optimize later.

| Issue | File | Problem |
|-------|------|---------|
| DR4-003 | `ldm/api.py:781` | TM suggest O(n) loop |
| DR4-005 | `backup_service.py:251` | Full backup loads all to memory |

**Fix Plan:** Defer to TM phase - need FAISS integration (DR4-003) and streaming backup (DR4-005).

---

## Group G: DEV_MODE Feature (1 issue)

**New feature:** Secure localhost-only auto-auth.

| Issue | File | Description |
|-------|------|-------------|
| DR3-009 | config.py, dependencies.py, auth_async.py | Claude autonomous testing |

**Fix Plan:**
1. Add `DEV_MODE` env var in config.py (default: false)
2. Add `is_localhost()` check in dependencies.py
3. Create `get_current_user_dev_mode()` dependency
4. Apply to all endpoints via dependency override
5. Log warning on startup if DEV_MODE enabled
6. Block if PRODUCTION=true

**This also fixes DR8-001** (13 endpoints with auth disabled in stats.py).

---

## Phase 3: Fix Sprint Order

| Week | Group | Issues | Notes |
|------|-------|--------|-------|
| 1 | **A** | 4 | Hardcoded URLs (quick) |
| 1 | **E** | 8 | Code bugs (quick) |
| 2 | **B** | 6 | Database migration |
| 2 | **D** | 5 | Auth refactor |
| 3 | **C** | 5 | Async/sync cleanup |
| 3 | **G** | 1 | DEV_MODE feature |
| Later | **F** | 2 | Performance (defer) |

---

## Commit Strategy

```
# Week 1 commits
fix(frontend): use serverUrl store instead of hardcoded URLs
fix(db): chunked_query and list_users ORDER BY
fix(utils): json.dumps for progress tracker, add comment for MD5
fix(xlstransfer): multi-letter column support, use text_utils
fix(quicksearch): add import re, guard lxml usage
fix(kr_similar): use Exception instead of bare except

# Week 2 commits
feat(db): migrate JSON columns to JSONB
refactor(auth): deprecate sync auth, add rate limiting

# Week 3 commits
refactor(ldm): async TMManager methods
feat(auth): DEV_MODE for localhost auto-auth
```

---

## When Complete

1. All 31 issues marked `[x]` in ISSUES_20251212.md
2. Run full test suite (595+ tests)
3. Verify no regressions
4. Move ISSUES_20251212.md to `history/`
5. Create new issue list for next cycle

---

*Phase 2 Consolidation Complete - 2025-12-12*
