# LDM (LanguageData Manager) - SubTree Documentation

**Created:** 2025-12-08
**Status:** 70% Complete (Phase 4 in progress)
**Task Tracking:** [docs/wip/P17_LDM_TASKS.md](../wip/P17_LDM_TASKS.md)

---

## Overview

LDM is a **CAT tool** (Computer-Assisted Translation) for editing localization data. Think of it as a specialized spreadsheet for translation files that supports:

- **Multi-format support**: TXT (tab-separated) and XML (LocStr format)
- **Real-time collaboration**: WebSocket-based live updates
- **Row locking**: Prevents edit conflicts
- **Presence tracking**: See who's viewing the same file
- **Virtual scrolling**: Handle 1M+ rows efficiently

---

## File Structure

```
server/tools/ldm/
├── __init__.py              # Module init
├── api.py                   # FastAPI router (55+ endpoints)
├── websocket.py             # Socket.IO handlers for real-time
└── file_handlers/
    ├── __init__.py
    ├── txt_handler.py       # Parse TXT/TSV files
    └── xml_handler.py       # Parse XML LocStr files

locaNext/src/lib/
├── components/
│   ├── apps/
│   │   └── LDM.svelte       # Main LDM app component (+ TEST MODE)
│   └── ldm/
│       ├── FileExplorer.svelte  # Project/folder tree
│       ├── DataGrid.svelte      # Rows table with edit modal
│       └── PresenceBar.svelte   # Shows online viewers
└── stores/
    └── ldm.js               # Svelte store for WebSocket state

server/database/models.py    # LDM* models (6 tables)
```

---

## Database Models

```
LDMProject    → Projects (name, owner_id)
LDMFolder     → Folders within projects
LDMFile       → Files (TXT/XML) with row count
LDMRow        → Individual strings (source, target, status)
LDMEditHistory → Version tracking for rollback
LDMActiveSession → Presence & row locking
```

### Key Indexes (for 1M row performance)

```sql
idx_ldm_row_file_rownum    (file_id, row_num)   -- Pagination
idx_ldm_row_file_stringid  (file_id, string_id) -- Search
idx_ldm_row_status         (status)             -- Filtering
```

---

## File Formats

### TXT Format (Tab-Separated)

```
col0  col1  col2  col3  col4  SOURCE(Korean)  TARGET(Translation)
0     390   0     0     1     연금술 스킬...    Augmente l'EXP...
```

- Columns 0-4: StringID components
- Column 5: Korean source (READ-ONLY)
- Column 6: Target translation (EDITABLE)
- Reference: `sampleofLanguageData.txt`

### XML Format (LocStr)

```xml
<LocStr StringId="ITEM_001"
        StrOrigin="빛의 검"         <!-- Korean SOURCE -->
        Str="Sword of Light"       <!-- English TARGET -->
/>
```

- `StrOrigin`: Korean source (READ-ONLY)
- `Str`: Target translation (EDITABLE)
- Reference: `sample_localization.xml`

---

## API Endpoints

### Projects
- `GET /api/ldm/projects` - List user's projects
- `POST /api/ldm/projects` - Create project
- `GET /api/ldm/projects/{id}/tree` - Get folder tree

### Files
- `POST /api/ldm/files/upload` - Upload TXT/XML file
- `GET /api/ldm/files/{id}/rows?page=1&limit=50&search=text&status=pending`

### Rows
- `PUT /api/ldm/rows/{id}` - Update target text (broadcasts via WebSocket)

### WebSocket Events
- `ldm_join_file` - Join a file room
- `ldm_leave_file` - Leave a file room
- `ldm_lock_row` - Request edit lock
- `ldm_unlock_row` - Release edit lock
- `ldm_cell_update` - Real-time cell change broadcast
- `ldm_presence_update` - Who's online update

---

## TEST MODE (Autonomous Testing)

LDM has a built-in TEST MODE for CDP-based testing:

```javascript
// Browser console or via CDP
window.ldmTest.createProject()  // Create test project
window.ldmTest.uploadFile()     // Upload embedded TXT
window.ldmTest.uploadXml()      // Upload embedded XML
window.ldmTest.editRow()        // Edit first row
window.ldmTest.fullSequence()   // Run all tests
window.ldmTest.getStatus()      // Check state
```

### Run via testing_toolkit:
```bash
cd /home/neil1988/LocalizationTools/testing_toolkit
node scripts/run_test.js ldm.fullSequence
```

---

## Development Status

| Phase | Status | Tasks |
|-------|--------|-------|
| Phase 1: Foundation | ✅ COMPLETE | Database, API, basic UI |
| Phase 2: File Explorer | ✅ COMPLETE | Projects, folders, upload |
| Phase 3: Real-time Sync | ✅ COMPLETE | WebSocket, presence, locking |
| Phase 4: Virtual Scroll | 🔄 IN PROGRESS | Backend done, frontend pending |
| Phase 5: CAT Features | ⏳ PLANNED | TM, Glossary, keyboard shortcuts |
| Phase 6: Polish | ⏳ PLANNED | Export, permissions, offline |

---

## Quick Commands

```bash
# Start server
python3 server/main.py

# Test LDM API
curl http://localhost:8888/api/ldm/health

# Login and create project
TOKEN=$(curl -s -X POST http://localhost:8888/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl -X POST http://localhost:8888/api/ldm/projects \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Project"}'
```

---

## Related Documents

- [P17_LDM_TASKS.md](../wip/P17_LDM_TASKS.md) - Detailed task tracking
- [Roadmap.md](../../Roadmap.md) - Project roadmap (P17 section)
- [QuickSearch parser.py](../../server/tools/quicksearch/parser.py) - Similar TXT/XML parsing

---

*Last updated: 2025-12-08*
