# Session Context

> Last Updated: 2026-01-05 (Session 28 - Schema Fixes + TM/Pretranslate Offline)

---

## STABLE CHECKPOINT

**Post-Session 28:** Build 444+ | **Date:** 2026-01-05

All file/row endpoints now work with both PostgreSQL AND SQLite (Offline Storage).
All schemas have Optional datetime fields for SQLite compatibility.

---

## Current State

**Build:** 444 | **Open Issues:** 0
**Tests:** All offline endpoints verified working
**Status:** Unified Offline/Online Backend COMPLETE!

---

## SESSION 28 COMPLETE ✅

### Schema DateTime Fixes ✅ DONE

All response schemas now use `Optional[datetime] = None` for SQLite compatibility:

| Schema | Fields Fixed |
|--------|--------------|
| `ProjectResponse` | created_at, updated_at |
| `FolderResponse` | created_at |
| `FileResponse` | created_at, updated_at |
| `RowResponse` | updated_at |
| `QAIssue` | created_at |
| `TMResponse` | created_at (already Optional) |

### Additional Endpoints Fixed ✅ DONE

| Endpoint | Fix |
|----------|-----|
| `GET /projects` | Includes "Offline Storage" virtual project (id=0) |
| `GET /tm` | Includes SQLite TMs from offline.py |
| `POST /pretranslate` | Full SQLite fallback with RowLike objects |

### TM in Offline Mode

- TMs created from local files go to PostgreSQL (hybrid approach)
- TM list includes both PostgreSQL and SQLite TMs
- SQLite TMs stored in `offline_tms` table

---

## SESSION 27 COMPLETE ✅

### Offline/Online Unified Endpoints ✅ DONE

**Every file/row endpoint now works with both databases:**

| Endpoint | PostgreSQL | SQLite | Status |
|----------|------------|--------|--------|
| `GET /files/{id}` | ✅ | ✅ | UNIFIED |
| `GET /files/{id}/rows` | ✅ | ✅ | UNIFIED |
| `PUT /rows/{id}` | ✅ | ✅ | FIXED |
| `DELETE /files/{id}` | ✅ | ✅ | UNIFIED |
| `PATCH /files/{id}/rename` | ✅ | ✅ | UNIFIED |
| `GET /files/{id}/download` | ✅ | ✅ | UNIFIED |
| `GET /files/{id}/convert` | ✅ | ✅ | FIXED |
| `GET /files/{id}/extract-glossary` | ✅ | ✅ | UNIFIED |
| `POST /files/{id}/merge` | ✅ | ✅ | UNIFIED |
| `POST /files/{id}/register-as-tm` | ✅ | ✅ | UNIFIED |
| `POST /files/{id}/check-qa` | ✅ | ✅ | UNIFIED |
| `POST /rows/{id}/check-qa` | ✅ | ✅ | UNIFIED |
| `POST /files/{id}/check-grammar` | ✅ | ✅ | UNIFIED |
| `POST /rows/{id}/check-grammar` | ✅ | ✅ | UNIFIED |
| `GET /files/{id}/active-tms` | ✅ | Empty | UNIFIED |
| `POST /pretranslate` | ✅ | ✅ | UNIFIED |
| `GET /search` | ✅ | ✅ | Includes local files |
| `POST /files/upload?storage=local` | N/A | ✅ | Imports to Offline Storage |

**PostgreSQL-Only Operations (by design):**
- `PATCH /files/{id}/move` → Returns 400 for local files
- `PATCH /files/{id}/move-cross-project` → Returns 400 for local files
- `POST /files/{id}/copy` → Returns 400 for local files

### Architecture Pattern

```
ONE endpoint → Try PostgreSQL → Fall back to SQLite if not found
```

**NO DUPLICATE CODE!** Each endpoint uses this pattern:
```python
result = await db.execute(select(LDMFile).where(LDMFile.id == file_id))
file = result.scalar_one_or_none()

if not file:
    # Fallback to SQLite
    offline_db = get_offline_db()
    return offline_db.get_local_file(file_id)
```

### Bugs Fixed

| Bug | Root Cause | Fix |
|-----|------------|-----|
| `PUT /rows/{id}` 500 error | Response didn't match RowResponse schema | Return full row data after update |
| `GET /files/{id}/convert` 500 error | `extra_data` was JSON string, not dict | Parse JSON from SQLite |

### Documentation Created

| Doc | Purpose |
|-----|---------|
| `docs/OFFLINE_ONLINE_ARCHITECTURE.md` | Technical implementation guide |
| Updated `docs/wip/OFFLINE_ONLINE_MODE.md` | P9 Launcher permissions |

---

## File Scenarios (MEMORIZE)

| Scenario | sync_status | Permissions |
|----------|-------------|-------------|
| **Local File** (Offline Storage) | `'local'` | FULL CONTROL - move, rename, delete |
| **Synced File** (from server) | `'synced'` | READ STRUCTURE - edit content only |
| **Orphaned File** (server path deleted) | `'orphaned'` | READ ONLY - needs reassignment |

---

## PRIORITIES (Updated)

| Priority | Feature | Status |
|----------|---------|--------|
| **P9** | **Offline/Online Mode** | ✅ BACKEND COMPLETE |
| P8 | Dashboard Overhaul | PLANNED |

### Next Steps for P9

1. ✅ Unified endpoints (done)
2. ⬜ Frontend Offline Storage UI improvements
3. ⬜ Sync flow implementation (push changes to server)
4. ⬜ SQLite TM storage (for true offline TM support)

---

## KEY FILES (Session 27)

| File | Changes |
|------|---------|
| `server/tools/ldm/routes/files.py` | 10+ endpoints with SQLite fallback |
| `server/tools/ldm/routes/rows.py` | Fixed row update response |
| `server/tools/ldm/routes/qa.py` | QA endpoints with fallback |
| `server/tools/ldm/routes/grammar.py` | Grammar endpoints with fallback |
| `server/tools/ldm/routes/pretranslate.py` | Pre-translate with fallback |
| `server/tools/ldm/routes/tm_assignment.py` | Active TMs returns empty for local |
| `server/tools/ldm/routes/search.py` | Searches SQLite local files |
| `server/database/offline.py` | Added `get_row()` method |
| `docs/OFFLINE_ONLINE_ARCHITECTURE.md` | NEW - Technical docs |

---

## ARCHITECTURE

```
LocaNext.exe (User PC)           Central PostgreSQL
├─ Electron + Svelte 5       →   ├─ All text data
├─ Embedded Python Backend       ├─ Users, sessions
├─ SQLite (offline storage)  ←   ├─ LDM rows, TM entries
├─ FAISS indexes (local)         └─ Logs
└─ Qwen model (optional)

UNIFIED PATTERN:
Endpoint → PostgreSQL first → SQLite fallback → Same response format

PERMISSIONS:
Offline Storage:     FULL CONTROL (create, move, delete)
Downloaded files:    READ CONTENT (edit rows only)
```

---

## QUICK COMMANDS

```bash
# DEV servers
./scripts/start_all_servers.sh --with-vite

# Check servers
./scripts/check_servers.sh

# Test offline endpoints
python3 -c "import requests; ..." # See test script in session

# Build trigger
echo "Build NNN" >> GITEA_TRIGGER.txt && git add -A && git commit -m "Build NNN: Description" && git push origin main && git push gitea main
```

---

*Session 27 | Build 444 | Offline/Online Unified Endpoints COMPLETE*
