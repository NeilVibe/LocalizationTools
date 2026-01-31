# Issues To Fix

**Last Updated:** 2026-01-31 (Session 60) | **Build:** 523 | **Open:** 2

---

## Quick Summary

| Status | Count |
|--------|-------|
| **OPEN** | 2 |
| **FIXED/CLOSED** | 158 |

---

## OPEN ISSUES

### LIMIT-001: Offline TM Search Suggestions Not Available ⚠️ LOW

- **Severity:** LOW (convenience feature)
- **Component:** `server/repositories/sqlite/tm_repo.py`

**Problem:** The `/tm/suggest` endpoint returns empty results for SQLite TMs because it uses PostgreSQL's `pg_trgm` extension.

**Impact:** Low - editor TM suggestions not available offline. Users can still work on translations manually.

**Future Fix:** Implement FAISS-based search for `/tm/suggest` endpoint.

---

### LIMIT-002: Offline TM Pretranslation Not Available ⚠️ MEDIUM

- **Severity:** MEDIUM (core feature missing)
- **Component:** `server/tools/ldm/pretranslate.py`, `server/tools/xlstransfer/embeddings.py`, `server/tools/kr_similar/embeddings.py`
- **Discovered:** Session 60 (6-agent code review)

**Problem:** All 3 pretranslation engines query PostgreSQL directly for TM data, bypassing the repository pattern.

| Engine | File Loading | TM Loading | Status |
|--------|--------------|------------|--------|
| `standard` | SQLite ✓ | PostgreSQL | FAILS offline |
| `xls_transfer` | SQLite ✓ | PostgreSQL | FAILS offline |
| `kr_similar` | SQLite ✓ | PostgreSQL | FAILS offline |

**Root Cause:**
```python
# pretranslate.py line 143 - queries PostgreSQL directly
tm = self.db.query(LDMTranslationMemory).filter(LDMTranslationMemory.id == tm_id).first()

# embeddings.py - EmbeddingsManager.load_tm() uses PostgreSQL
entries = db_session.query(LDMTMEntry).filter(LDMTMEntry.tm_id == tm_id).all()
```

**What WORKS offline:**
- TM registration (create, list, activate, delete)
- File upload, QA, row editing
- All TM management operations

**What DOESN'T work offline:**
- Pretranslation with any TM (all 3 engines fail)

**Workaround:** Use online mode for pretranslation, then work offline.

**Future Fix:** Refactor EmbeddingsManager and PretranslationEngine to use repository pattern for TM loading.

---

## RECENTLY FIXED (Session 60)

### BUG-042: Navigation Broken on Windows ✅ FIXED

- **Fixed:** Session 60
- **Problem:** `handleEnterFolder` was not async and didn't await folder load functions
- **Impact:** All folder navigation (platforms, projects, folders, trash) potentially broken on Windows
- **Fix:** Made `handleEnterFolder` async and added `await` to all 6 folder load calls

**File:** `locaNext/src/lib/components/pages/FilesPage.svelte:646-674`

---

### AIOSQLITE-001 to AIOSQLITE-011: Missing Await/Dict Conversions ✅ FIXED

- **Fixed:** Session 60
- **Problem:** aiosqlite migration left 11 bugs in Offline Storage code path
- **Files Fixed:**
  - `files.py` - 3 missing `await` statements
  - `pretranslate.py` - 3 sync→async bridges with `asyncio.run()`
  - `tm_repo.py` - 5 `sqlite3.Row` to `dict()` conversions

---

## CLOSED (Session 60 Verification)

### ARCH-001: Repository Layer Violations ✅ ALREADY FIXED

- **Verified:** Session 60 (6-agent parallel verification)
- **Finding:** No layer violations exist. Factory handles all mode detection at boundary.
- **Evidence:** grep found 0 instances of `ACTIVE_DATABASE_TYPE` in PostgreSQL repos

---

### TECH-DEBT-002: CLI Tools Use print() ✅ NOT A BUG

- **Verified:** Session 60
- **Finding:** Intentional design. CLI tools NEED stdout/stderr for:
  - Progress tracking (`print(..., file=sys.stderr)`)
  - JSON output for subprocess piping
- **Action:** Closed as "by design"

---

### IMPROVE-001: Unify First-Run Setup with Launcher ✅ NOT NEEDED

- **Verified:** Session 60
- **Finding:** Architecturally sound separation:
  - First-run setup: ONE-TIME environment init (pre-app)
  - Launcher: EVERY-TIME connection mode selection (in-app)
- **Action:** Closed as "working as designed"

---

### DOCS-001: Documentation Files Too Large ✅ FIXED

- **Verified:** Session 60
- **Finding:** `OFFLINE_ONLINE_MODE.md` reduced from 1660 → 150 lines (91% reduction)
- **Action:** Closed

---

### TECH-DEBT-001: SQLite Sync I/O ✅ MOSTLY FIXED

- **Fixed:** Sessions 59-60
- **What was done:**
  - AsyncSessionWrapper removed
  - aiosqlite migration complete
  - 11 additional bugs fixed in Session 60
- **Action:** Closed (monitor for any remaining edge cases)

---

## Historical Issues

See `docs/archive/history/ISSUES_ARCHIVE.md` for 150+ resolved issues from Sessions 1-59.
