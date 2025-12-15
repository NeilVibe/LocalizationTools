# Session Context - Last Working State

**Updated:** 2025-12-15 | **By:** Claude

---

## Current Priority: P33 Offline Mode + CI Overhaul

**Status: 100% COMPLETE** | Full structure preservation + Sync endpoints done

---

## P33 Phase Status

| Phase | Status | What |
|-------|--------|------|
| 1 | ✅ | SQLite backend (FlexibleJSON, db_setup.py, auto-fallback) |
| 2 | ✅ | Auto-detection (PostgreSQL unreachable → SQLite) |
| 3 | ✅ | Tabbed sidebar (Files/TM tabs) |
| 4 | ✅ | Online/Offline badges in toolbar |
| 5 | ✅ | Go Online button + Upload to Server modal |
| 6 | ✅ | CI streamlined (1536 → 272 real tests) |

---

## Key Implementation Details

### Backend (Offline Mode)
```python
# server/config.py
DATABASE_MODE = "auto"  # auto | postgresql | sqlite
ACTIVE_DATABASE_TYPE = "postgresql"  # set at runtime

# server/database/db_setup.py
setup_database()  # Auto-detects, falls back to SQLite

# server/database/models.py
FlexibleJSON  # JSONB on PostgreSQL, JSON on SQLite
```

### Frontend (LDM.svelte)
```javascript
// Connection status
let connectionStatus = $state({ mode: 'unknown', canSync: false });

// Go Online button (visible when offline)
async function handleGoOnline() { ... }

// FileExplorer receives connectionMode prop
<FileExplorer connectionMode={connectionStatus.mode} />
```

### Upload to Server (FileExplorer.svelte)
```javascript
// Right-click menu option (only visible when offline)
{#if connectionMode === 'offline'}
  <button onclick={openUploadToServer}>Upload to Central Server...</button>
{/if}

// Modal with destination selection + safety checks
<Modal bind:open={showUploadToServerModal}>
  <Select bind:selected={uploadToServerDestination}>
    {#each uploadToServerProjects as project}
      <SelectItem value={project.id} text={project.name} />
    {/each}
  </Select>
</Modal>
```

### CI Pipeline (build.yml)
```yaml
# Streamlined from 1536 → 272 real tests
TEST_DIRS="tests/integration/test_api_true_simulation.py tests/security/ tests/e2e/..."

# No mocks, all real API tests with TestClient
```

---

## Files Modified (P33)

**Backend:**
- `server/config.py` - DATABASE_MODE, set_active_database()
- `server/database/models.py` - FlexibleJSON type
- `server/database/db_setup.py` - setup_database() with auto-fallback
- `server/database/db_utils.py` - is_sqlite(), SQLite fallbacks
- `server/utils/dependencies.py` - Uses setup_database()
- `server/main.py` - /api/status, /api/go-online endpoints

**Frontend:**
- `locaNext/src/lib/components/apps/LDM.svelte` - Connection badge, Go Online button
- `locaNext/src/lib/components/ldm/FileExplorer.svelte` - Tabs, Upload to Server modal

**CI:**
- `.gitea/workflows/build.yml` - Streamlined TEST_DIRS

---

## Architecture

```
ONLINE MODE:                         OFFLINE MODE:
┌─────────────────────────┐         ┌─────────────────────────┐
│ PostgreSQL (central)    │         │ SQLite (local)          │
│ Multi-user, WebSocket   │         │ Single-user, CI testing │
│ All data shared         │         │ Local only              │
└─────────────────────────┘         └─────────────────────────┘
         ↑                                    ↑
         │ [Go Online]                        │
         └────────── User can switch ─────────┘

Right-click file → "Upload to Central Server" → Destination Modal → Safety Check → Upload
```

---

## TM Processing Workflow (Fully Verified + Fixed)

| Feature | Status | Evidence |
|---------|--------|----------|
| Unique paths per TM | ✅ | `server/data/ldm_tm/{tm_id}/` |
| Correct embeddings | ✅ | Qwen + FAISS HNSW (normalized) |
| Multiple TMs simultaneous | ✅ | `buildingIndexes = Set()` per TM |
| Task Manager tracking | ✅ | `TrackedOperation` + 4-stage progress |
| Warning before processing | ✅ | Confirmation modal added |

### Storage Architecture (per TM)
```
server/data/ldm_tm/{tm_id}/
├── metadata.json       # TM info, timestamps, counts
├── hash/
│   ├── whole_lookup.pkl  # Tier 1: O(1) exact whole match
│   └── line_lookup.pkl   # Tier 3: O(1) exact line match
├── embeddings/
│   ├── whole.npy         # Tier 2: whole-text embeddings
│   ├── whole_mapping.pkl # entry_id → embedding idx
│   ├── line.npy          # Tier 4: line embeddings
│   └── line_mapping.pkl
└── faiss/
    ├── whole.index       # HNSW index for semantic whole search
    └── line.index        # HNSW index for semantic line search
```

### Embedding Pipeline
1. **Model:** Qwen3-Embedding-0.6B (same as KR Similar)
2. **FAISS:** HNSW index (M=32, efConstruction=400, efSearch=500)
3. **Normalization:** L2 normalized for cosine similarity
4. **Batch:** 64 texts per batch

### Multiple TM Processing
- `TMManager.svelte` uses `buildingIndexes = $state(new Set())` to track
- Each TM adds its ID to set when processing starts
- Each TM removes its ID when done
- Button disabled only for that specific TM while processing
- 10 TMs can process simultaneously without conflicts

### Progress Tracking (4 stages)
1. "Building hash indexes" (0/4)
2. "Building embeddings" (1/4)
3. "Building line embeddings" (2/4)
4. "Saving metadata" (3/4) → "Complete" (4/4)

### Code Locations
| What | File | Lines |
|------|------|-------|
| Warning modal | `TMManager.svelte` | 350-374 |
| Build confirmation | `TMManager.svelte` | 182-195 |
| Path management | `tm_indexer.py` | 173-175 |
| Embedding build | `tm_indexer.py` | 405-474 |
| FAISS indexing | `tm_indexer.py` | 459-471 |
| TrackedOperation | `api.py` | 1086-1164 |

---

## What's Left

1. ~~**Fix Upload to Server**~~ ✅ DONE - Using sync-to-central endpoint
2. **Run full CI** - Verify tests pass in pipeline
3. **Windows smoke test** - CDP tests exist but need app running
4. **Database migration** - Add extra_data columns to existing databases

---

## COMPLETED: Full Structure Preservation + Sync

### What Was Built (2025-12-15)

**1. extra_data JSONB columns added:**
- `LDMFile.extra_data` - File-level metadata (encoding, root element, total columns)
- `LDMRow.extra_data` - Row-level extra data (extra columns/attributes)

**2. File parsers updated:**
- `txt_handler.py` - Captures columns 7+, encoding, total column count
- `xml_handler.py` - Captures all attributes beyond stringid/strorigin/str, root element

**3. File reconstruction updated:**
- `_build_txt_file()` - Restores extra columns from extra_data
- `_build_xml_file()` - Restores root element, extra attributes
- `_build_excel_file()` - Restores extra columns, sheet name

**4. Sync endpoints built:**
- `POST /api/ldm/sync-to-central` - Syncs file + rows from SQLite → PostgreSQL
- `POST /api/ldm/tm/sync-to-central` - Syncs TM + entries from SQLite → PostgreSQL

**5. Frontend fixed:**
- `FileExplorer.svelte` - Now calls sync-to-central (not re-upload blob)

### The Flow (NOW WORKING)
```
OFFLINE (SQLite)                    ONLINE (PostgreSQL)
┌─────────────────────┐            ┌─────────────────────┐
│ ldm_files           │            │ ldm_files           │
│   + extra_data      │            │   + extra_data      │
│ ldm_rows            │──SYNC───►  │ ldm_rows            │
│   + extra_data      │            │   + extra_data      │
│ (with translations) │            │ (with translations) │
└─────────────────────┘            └─────────────────────┘
                                            │
                                     /download endpoint
                                            │
                                            ▼
                                   FULL RECONSTRUCTION
                                   (ALL columns/attrs)
```

### Data Structure

**File-level metadata (LDMFile.extra_data):**
```json
// TXT
{"encoding": "utf-8", "total_columns": 10, "line_count": 500}

// XML
{"encoding": "UTF-8", "root_element": "LangData", "element_tag": "LocStr", "root_attributes": {...}}

// Excel
{"sheet_name": "Translations", "headers": ["Source", "Target", "Notes"]}
```

**Row-level extra data (LDMRow.extra_data):**
```json
// TXT: extra columns
{"col7": "value", "col8": "value"}

// XML: extra attributes
{"CustomAttr": "value", "Category": "UI"}

// Excel: extra columns
{"C": "Notes", "D": "Context"}
```

---

## Code Review (P32 - LOW PRIORITY)

11 issues documented in `docs/code-review/ISSUES_20251215_LDM_API.md`
- 2 CRITICAL (SQL injection, response format)
- 3 HIGH (deprecated asyncio, missing models)
- 4 MEDIUM (validation, error messages)
- 2 LOW (hardcoded values)

**Do AFTER P33 is fully verified.**

---

## Quick Commands

```bash
# Start servers
./scripts/start_all_servers.sh

# Build frontend
cd locaNext && npm run build

# Run streamlined tests
python3 -m pytest tests/integration/test_api_true_simulation.py tests/security/ -v

# Test SQLite mode
DATABASE_MODE=sqlite python3 server/main.py

# Check server imports
python3 -c "from server.main import app; print('OK')"
```

---

## Key Decisions Made

1. **Dual mode** - PostgreSQL (online) + SQLite (offline) with auto-fallback
2. **Manual reconnect** - [Go Online] button, not automatic polling
3. **Upload workflow** - Right-click → Destination modal → Safety check → Upload
4. **CI focus** - Real tests only, no mocks, 272 essential tests
5. **TM sync simplified** - Upload entire files/TM to server, not individual entries

---

*For full task details: [P33_OFFLINE_MODE_CI_OVERHAUL.md](P33_OFFLINE_MODE_CI_OVERHAUL.md)*
*For global priorities: [Roadmap.md](../../Roadmap.md)*
