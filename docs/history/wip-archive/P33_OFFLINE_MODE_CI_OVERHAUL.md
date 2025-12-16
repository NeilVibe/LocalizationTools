# P33: Offline Mode + CI Testing Overhaul

**Status:** ✅ COMPLETE (100%)
**Priority:** Done
**Created:** 2025-12-13 | **Updated:** 2025-12-16 06:00 KST

---

## Progress

| Phase | Status | Description |
|-------|--------|-------------|
| Phase 1 | ✅ DONE | Database abstraction - SQLite backend |
| Phase 2 | ✅ DONE | Auto-detection (PostgreSQL → SQLite fallback) |
| Phase 3 | ✅ DONE | Tabbed sidebar (Files/TM) |
| Phase 4 | ✅ DONE | UI feedback (Online/Offline badges) |
| Phase 5 | ✅ DONE | Go Online button + Upload to Server modal |
| Phase 6 | ✅ DONE | CI overhaul (1536 → 272 real tests) |
| Phase 7 | ✅ DONE | Offline auto-login (LOCAL user + auto_token) |
| Phase 8 | ✅ DONE | Smoke test fix (IPv4/IPv6 localhost issue) |

---

## What Was Built

### 1. SQLite Offline Mode

```python
# server/config.py
DATABASE_MODE = "auto"  # auto | postgresql | sqlite

# server/database/db_setup.py
setup_database()  # Auto-detects, creates engine
# PostgreSQL reachable? → Use PostgreSQL
# Not reachable? → Fall back to SQLite

# server/database/models.py
FlexibleJSON  # JSONB on PostgreSQL, JSON on SQLite
```

**Key Files:**
- `server/database/db_setup.py` - `setup_database()` with auto-fallback
- `server/database/db_utils.py` - `is_sqlite()`, SQLite-specific fallbacks
- `server/config.py` - `DATABASE_MODE`, `set_active_database()`

### 2. Online/Offline UI

```
┌─────────────────────────────────────────────────────────┐
│ LanguageData Manager  🟢 Online  [TM Manager] [Settings]│
│                       🔘 Offline [Go Online]            │
├─────────────────────────────────────────────────────────┤
```

**Endpoints:**
- `GET /api/status` - Returns connection_mode, database_type, can_sync
- `POST /api/go-online` - Checks PostgreSQL reachability

### 3. Upload to Server

```
Right-click file (when offline)
    ↓
"Upload to Central Server..."
    ↓
┌─────────────────────────────────────────┐
│        Upload to Central Server          │
├─────────────────────────────────────────┤
│  File: myfile.txt                        │
│                                          │
│  Choose destination:                     │
│  [📁 Project Alpha        ]              │
│  [📁 Project Beta    ← ✓  ]              │
│                                          │
│  Safety Checks:                          │
│  ✓ File format supported                 │
│  ✓ File name valid                       │
│  ✓ Destination selected                  │
│                                          │
│         [Cancel]  [Upload]               │
└─────────────────────────────────────────┘
```

**Key Files:**
- `FileExplorer.svelte` - `connectionMode` prop, Upload modal
- `LDM.svelte` - Connection status state, Go Online handler

### 4. CI Pipeline

**Before:** 1536 tests, 229 mocks, slow, misses real bugs
**After:** 272 real tests, no mocks, fast, catches actual issues

```yaml
# .gitea/workflows/build.yml
TEST_DIRS="tests/integration/test_api_true_simulation.py tests/security/ tests/e2e/..."
```

---

## Architecture

```
ONLINE MODE                          OFFLINE MODE
┌─────────────────────────┐         ┌─────────────────────────┐
│ PostgreSQL (central)    │         │ SQLite (local)          │
│ • Multi-user            │         │ • Single-user           │
│ • WebSocket sync        │         │ • Local only            │
│ • Shared data           │         │ • CI testing            │
└─────────────────────────┘         └─────────────────────────┘
         ↑                                    ↑
         │     User clicks [Go Online]        │
         └────────── can switch ──────────────┘

Right-click → "Upload to Central Server" → Destination → Safety Check → Upload
```

---

## Test Suite (272 Real Tests)

| Category | Count | What |
|----------|-------|------|
| API Integration | ~50 | TestClient, real endpoints |
| Security | ~90 | JWT, CORS, IP filter, auth |
| E2E Tools | ~80 | KR Similar, QuickSearch workflows |
| DB Utils | ~30 | is_sqlite(), fallbacks |
| Core | ~22 | TM search, algorithms |

**Key:** All tests use real API calls (TestClient or requests), no mocks.

---

## TM Processing Workflow (Fully Verified 2025-12-16)

| Feature | Status | Evidence |
|---------|--------|----------|
| Unique paths per TM | ✅ | `server/data/ldm_tm/{tm_id}/` |
| Correct embeddings | ✅ | Qwen + FAISS HNSW (normalized) |
| Multiple TMs simultaneous | ✅ | `buildingIndexes = Set()` per TM |
| Task Manager tracking | ✅ | `TrackedOperation` + 4-stage progress |
| Warning dialog | ✅ | `confirmBuildIndexes()` modal added |

### TM Storage (per TM)
```
server/data/ldm_tm/{tm_id}/
├── metadata.json
├── hash/whole_lookup.pkl, line_lookup.pkl
├── embeddings/whole.npy, whole_mapping.pkl, line.npy, line_mapping.pkl
└── faiss/whole.index, line.index
```

### Key Code Locations
- `TMManager.svelte:350-374` - Warning modal
- `TMManager.svelte:182-195` - `confirmBuildIndexes()`
- `tm_indexer.py:173-175` - Path: `get_tm_path(tm_id)`
- `tm_indexer.py:405-474` - Embedding generation
- `api.py:1086-1164` - TrackedOperation

---

## What's Left

**Nothing - P33 is complete!**

Remaining items moved to future priorities:
- Upload to Server sync (file re-upload works, DB sync is future enhancement)
- Full E2E CDP tests (manual validation in Playground)

---

## Future Enhancement: Upload to Server DB Sync

**Current Status:** File re-upload works (binary upload). DB row sync is a future enhancement.

**What would be needed:**
```
POST /api/ldm/sync-to-central
- Input: file_id (SQLite), destination_project_id
- Reads ldm_files + ldm_rows from SQLite
- Creates records in PostgreSQL
- Returns new file_id
```

**Priority:** Low - users can work offline and re-upload files when online.

---

## Quick Reference

```bash
# Test SQLite mode
DATABASE_MODE=sqlite python3 server/main.py

# Test auto-fallback (PostgreSQL down)
POSTGRES_PORT=9999 DATABASE_MODE=auto python3 server/main.py

# Run streamlined tests
python3 -m pytest tests/integration/test_api_true_simulation.py tests/security/ -v

# Build frontend
cd locaNext && npm run build
```

---

## Files Modified

**Backend:**
- `server/config.py` - DATABASE_MODE, ACTIVE_DATABASE_TYPE
- `server/database/models.py` - FlexibleJSON
- `server/database/db_setup.py` - setup_database()
- `server/database/db_utils.py` - is_sqlite(), fallbacks
- `server/utils/dependencies.py` - Uses setup_database()
- `server/main.py` - /api/status, /api/go-online

**Frontend:**
- `LDM.svelte` - Connection badge, Go Online button
- `FileExplorer.svelte` - Tabs, Upload to Server modal

**CI:**
- `.gitea/workflows/build.yml` - Streamlined TEST_DIRS

---

*P33 100% complete. Offline mode fully working.*
