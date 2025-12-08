# P17: LocaNext LDM - Detailed Task List

**Started:** 2025-12-08
**Status:** IN PROGRESS
**Last Updated:** 2025-12-08

> This is the granular task breakdown for P17. Update checkboxes as tasks complete.
> Main roadmap: [Roadmap.md](../../Roadmap.md)

---

## Progress Overview

```
Phase 1: Foundation         [X] 12/12 tasks  ✅ COMPLETE
Phase 2: File Explorer      [ ] 0/10 tasks
Phase 3: Real-time Sync     [ ] 0/12 tasks
Phase 4: Virtual Scroll     [ ] 0/8 tasks
Phase 5: CAT Features       [ ] 0/10 tasks
Phase 6: Polish             [ ] 0/8 tasks
─────────────────────────────────────────
TOTAL                       [▓] 12/60 tasks (20%)
```

---

## Phase 1: Foundation (Database + Basic API)

### 1.1 Backend: Database Models
```
Location: server/database/models.py (added to existing models file)
```

- [x] **1.1.1** Create `server/tools/ldm/` directory
- [x] **1.1.2** Create `__init__.py`
- [x] **1.1.3** Create models with SQLAlchemy (in server/database/models.py):
  - [x] `LDMProject` (id, name, owner_id, created_at, updated_at)
  - [x] `LDMFolder` (id, project_id, parent_id, name, created_at)
  - [x] `LDMFile` (id, folder_id, name, format, row_count, created_at)
  - [x] `LDMRow` (id, file_id, row_num, string_id, source, target, status, updated_by, updated_at)
  - [x] `LDMEditHistory` (version tracking for rollback)
  - [x] `LDMActiveSession` (presence tracking and row locking)
- [x] **1.1.4** Tables auto-created via Base.metadata.create_all()
- [x] **1.1.5** Verified models import correctly

### 1.2 Backend: Basic API
```
Location: server/tools/ldm/api.py
```

- [x] **1.2.1** Create `api.py` with FastAPI router
- [x] **1.2.2** Implement `GET /api/ldm/health` (test endpoint)
- [x] **1.2.3** Register LDM router in `server/main.py`
- [x] **1.2.4** API verified: imports correctly, router prefix `/api/ldm`

### 1.3 Frontend: Basic Route
```
Location: locaNext/src/lib/components/apps/LDM.svelte
```

- [x] **1.3.1** Created `LDM.svelte` component (using existing app pattern)
- [x] **1.3.2** Component shows health status and feature roadmap
- [x] **1.3.3** Added "LDM" to apps array in `+layout.svelte`
- [x] **1.3.4** Added LDM rendering in `+page.svelte`

**Phase 1 Completion Checklist:**
- [x] Database tables created (auto via Base.metadata.create_all)
- [x] API endpoint responds (verified import)
- [x] Frontend tab visible (added to apps menu)
- [x] Module imports correctly

---

## Phase 2: File Explorer + Basic Grid

### 2.1 Backend: Projects/Folders API
```
Location: server/tools/ldm/api.py
```

- [ ] **2.1.1** `POST /api/ldm/projects` - Create project
- [ ] **2.1.2** `GET /api/ldm/projects` - List user's projects
- [ ] **2.1.3** `POST /api/ldm/folders` - Create folder in project
- [ ] **2.1.4** `GET /api/ldm/projects/{id}/tree` - Get folder tree
- [ ] **2.1.5** `DELETE /api/ldm/folders/{id}` - Delete folder

### 2.2 Backend: File Upload
```
Location: server/tools/ldm/api.py, file_handlers/
```

- [ ] **2.2.1** Create `file_handlers/` directory
- [ ] **2.2.2** Create `txt_handler.py` (parse TXT, index 5=source, 6=target)
- [ ] **2.2.3** Create `xml_handler.py` (parse LocStr, StrOrigin=source, Str=target)
- [ ] **2.2.4** `POST /api/ldm/files/upload` - Upload file, parse, store rows in DB
- [ ] **2.2.5** `GET /api/ldm/files/{id}` - Get file metadata

### 2.3 Frontend: File Explorer
```
Location: locaNext/src/lib/components/ldm/
```

- [ ] **2.3.1** Create `lib/components/ldm/` directory
- [ ] **2.3.2** Create `FileExplorer.svelte` (tree view)
- [ ] **2.3.3** Implement project/folder display
- [ ] **2.3.4** Implement "New Project" button
- [ ] **2.3.5** Implement "New Folder" (right-click menu)
- [ ] **2.3.6** Implement file upload (drag & drop + button)

### 2.4 Frontend: Basic Grid
```
Location: locaNext/src/lib/components/ldm/
```

- [ ] **2.4.1** Create `DataGrid.svelte` (basic table)
- [ ] **2.4.2** Implement columns: # | StringID | Source (KR) | Target | Status
- [ ] **2.4.3** `GET /api/ldm/files/{id}/rows?page=1&limit=50` - Paginated rows
- [ ] **2.4.4** Connect grid to API, display real data
- [ ] **2.4.5** Style: Source column grey (read-only), Target column white

**Phase 2 Completion Checklist:**
- [ ] Can create project
- [ ] Can create folders
- [ ] Can upload TXT file
- [ ] Can upload XML file
- [ ] Grid shows parsed data
- [ ] Pagination works

---

## Phase 3: Editing + Real-time Sync

### 3.1 Backend: Row Update API
```
Location: server/tools/ldm/api.py
```

- [ ] **3.1.1** `PUT /api/ldm/rows/{id}` - Update target text
- [ ] **3.1.2** Validate: only target field editable
- [ ] **3.1.3** Update status to "translated" when target set

### 3.2 Backend: WebSocket
```
Location: server/tools/ldm/websocket.py
```

- [ ] **3.2.1** Create `websocket.py`
- [ ] **3.2.2** Implement room management (users join/leave file rooms)
- [ ] **3.2.3** Implement `cell_update` broadcast
- [ ] **3.2.4** Implement `presence` broadcast (who's online)
- [ ] **3.2.5** Implement row locking (when modal open)
- [ ] **3.2.6** Register WebSocket route `/ws/ldm/{file_id}` in main.py

### 3.3 Frontend: Edit Modal
```
Location: locaNext/src/lib/components/ldm/
```

- [ ] **3.3.1** Create `EditModal.svelte`
- [ ] **3.3.2** Display StringID (read-only)
- [ ] **3.3.3** Display Source/StrOrigin (read-only, grey)
- [ ] **3.3.4** Display Target/Str (editable textarea)
- [ ] **3.3.5** Save button → API call
- [ ] **3.3.6** Double-click target cell → open modal

### 3.4 Frontend: Real-time Updates
```
Location: locaNext/src/lib/stores/
```

- [ ] **3.4.1** Create `ldm.js` store
- [ ] **3.4.2** WebSocket connection management
- [ ] **3.4.3** Receive `cell_update` → update grid row
- [ ] **3.4.4** Create `PresenceBar.svelte` (who's online)
- [ ] **3.4.5** Show lock indicator on rows being edited

**Phase 3 Completion Checklist:**
- [ ] Can edit target text via modal
- [ ] Changes saved to database
- [ ] Changes broadcast to other users
- [ ] See who's online
- [ ] See lock on rows being edited

---

## Phase 4: Virtual Scrolling (1M Rows)

### 4.1 Backend: Optimized Queries
```
Location: server/tools/ldm/api.py
```

- [ ] **4.1.1** Add database indexes (file_id, row_num)
- [ ] **4.1.2** Add PostgreSQL trigram index for search
- [ ] **4.1.3** Implement `GET /api/ldm/files/{id}/rows?search=text`
- [ ] **4.1.4** Optimize pagination with keyset pagination (if needed)

### 4.2 Frontend: Virtual Grid
```
Location: locaNext/src/lib/components/ldm/
```

- [ ] **4.2.1** Upgrade `DataGrid.svelte` to `VirtualGrid.svelte`
- [ ] **4.2.2** Implement virtual scrolling (render only visible ~50 rows)
- [ ] **4.2.3** Implement infinite scroll OR pagination controls
- [ ] **4.2.4** Implement "Go to row N" navigation
- [ ] **4.2.5** Implement search bar (server-side search)
- [ ] **4.2.6** Test with 100K+ rows

**Phase 4 Completion Checklist:**
- [ ] Smooth scrolling with 100K rows
- [ ] Search returns results in <500ms
- [ ] "Go to row" works instantly
- [ ] Memory usage stays low

---

## Phase 5: CAT Features

### 5.1 Backend: Translation Memory
```
Location: server/tools/ldm/tm.py
```

- [ ] **5.1.1** Create `tm.py` (reuse KR Similar fuzzy matching)
- [ ] **5.1.2** `GET /api/ldm/tm/suggest?source=text` - Get TM suggestions
- [ ] **5.1.3** Implement similarity threshold (e.g., 70%+)

### 5.2 Backend: Glossary
```
Location: server/tools/ldm/glossary.py
```

- [ ] **5.2.1** Create `glossary.py` (reuse QA Tools)
- [ ] **5.2.2** `GET /api/ldm/glossary/check?text=...` - Check glossary terms

### 5.3 Frontend: CAT Panels
```
Location: locaNext/src/lib/components/ldm/
```

- [ ] **5.3.1** Create `TMPanel.svelte` (shows suggestions in modal)
- [ ] **5.3.2** Create `GlossaryPanel.svelte` (shows term matches)
- [ ] **5.3.3** Integrate panels into EditModal
- [ ] **5.3.4** Implement keyboard shortcuts (Ctrl+Enter, Tab)
- [ ] **5.3.5** Implement status workflow UI (Draft/Review/Approved)

**Phase 5 Completion Checklist:**
- [ ] TM suggestions appear when editing
- [ ] Glossary terms highlighted
- [ ] Keyboard shortcuts work
- [ ] Status workflow visible

---

## Phase 6: Polish & Scale

- [ ] **6.1** Version history (track all changes)
- [ ] **6.2** Rollback feature
- [ ] **6.3** TMX export
- [ ] **6.4** XLIFF export
- [ ] **6.5** Project permissions (owner, editor, viewer)
- [ ] **6.6** Performance tuning for 50+ concurrent users
- [ ] **6.7** Offline mode (read-only cache)
- [ ] **6.8** Final testing & documentation

---

## Current Focus

```json
{
  "current_phase": 2,
  "current_task": "2.1.1",
  "next_task": "2.1.2",
  "blockers": [],
  "notes": "Phase 1 COMPLETE - Ready for Phase 2: File Explorer"
}
```

---

## Session Log

| Date | Tasks Completed | Notes |
|------|-----------------|-------|
| 2025-12-08 | Planning complete | Created task list, ready to start |
| 2025-12-08 | Phase 1 COMPLETE (12/12) | Backend models, API, frontend component all done |

---

*This file is a working document. Update as tasks complete.*
