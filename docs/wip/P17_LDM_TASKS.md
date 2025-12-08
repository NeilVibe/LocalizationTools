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
Phase 2: File Explorer      [X] 16/16 tasks  ✅ COMPLETE
Phase 3: Real-time Sync     [X] 20/20 tasks  ✅ COMPLETE
Phase 4: Virtual Scroll     [ ] 0/8 tasks
Phase 5: CAT Features       [ ] 0/10 tasks
Phase 6: Polish             [ ] 0/8 tasks
─────────────────────────────────────────
TOTAL                       [▓▓▓▓▓▓] 48/74 tasks (65%)
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

- [x] **2.1.1** `POST /api/ldm/projects` - Create project *(built in Phase 1)*
- [x] **2.1.2** `GET /api/ldm/projects` - List user's projects *(built in Phase 1)*
- [x] **2.1.3** `POST /api/ldm/folders` - Create folder in project *(built in Phase 1)*
- [x] **2.1.4** `GET /api/ldm/projects/{id}/tree` - Get folder tree *(built in Phase 1)*
- [x] **2.1.5** `DELETE /api/ldm/folders/{id}` - Delete folder *(built in Phase 1)*

### 2.2 Backend: File Upload
```
Location: server/tools/ldm/api.py, file_handlers/
```

- [x] **2.2.1** Create `file_handlers/` directory *(done in Phase 1)*
- [x] **2.2.2** Create `txt_handler.py` (parse TXT, index 5=source, 6=target)
- [x] **2.2.3** Create `xml_handler.py` (parse LocStr, StrOrigin=source, Str=target)
- [x] **2.2.4** `POST /api/ldm/files/upload` - Upload file, parse, store rows in DB
- [x] **2.2.5** `GET /api/ldm/files/{id}` - Get file metadata *(built in Phase 1)*

### 2.3 Frontend: File Explorer
```
Location: locaNext/src/lib/components/ldm/
```

- [x] **2.3.1** Create `lib/components/ldm/` directory
- [x] **2.3.2** Create `FileExplorer.svelte` (tree view)
- [x] **2.3.3** Implement project/folder display
- [x] **2.3.4** Implement "New Project" button
- [x] **2.3.5** Implement "New Folder" button
- [x] **2.3.6** Implement file upload (modal + FileUploader)

### 2.4 Frontend: Basic Grid
```
Location: locaNext/src/lib/components/ldm/
```

- [x] **2.4.1** Create `DataGrid.svelte` (basic table)
- [x] **2.4.2** Implement columns: # | StringID | Source (KR) | Target | Status
- [x] **2.4.3** Paginated rows API connection
- [x] **2.4.4** Connect grid to API, display real data
- [x] **2.4.5** Style: Source column grey (read-only), Target column editable

**Phase 2 Completion Checklist:**
- [x] Can create project
- [x] Can create folders
- [x] Can upload TXT file
- [x] Can upload XML file
- [x] Grid shows parsed data
- [x] Pagination works

---

## Phase 3: Editing + Real-time Sync

### 3.1 Backend: Row Update API ✅
```
Location: server/tools/ldm/api.py (already built in Phase 1)
```

- [x] **3.1.1** `PUT /api/ldm/rows/{id}` - Update target text *(done in Phase 1)*
- [x] **3.1.2** Validate: only target field editable *(source is READ-ONLY)*
- [x] **3.1.3** Update status to "translated" when target set *(auto-update logic)*

### 3.2 Backend: WebSocket ✅
```
Location: server/tools/ldm/websocket.py
```

- [x] **3.2.1** Create `websocket.py` *(full implementation with Socket.IO)*
- [x] **3.2.2** Implement room management *(ldm_join_file, ldm_leave_file)*
- [x] **3.2.3** Implement `cell_update` broadcast *(broadcast_cell_update)*
- [x] **3.2.4** Implement `presence` broadcast *(broadcast_file_presence, ldm_get_presence)*
- [x] **3.2.5** Implement row locking *(ldm_lock_row, ldm_unlock_row, is_row_locked)*
- [x] **3.2.6** Register WebSocket route in main.py *(uses existing /ws/socket.io)*

### 3.3 Frontend: Edit Modal ✅
```
Location: locaNext/src/lib/components/ldm/DataGrid.svelte (built-in modal)
```

- [x] **3.3.1** Edit modal built into DataGrid.svelte *(no separate file needed)*
- [x] **3.3.2** Display StringID (read-only) *(in modal form)*
- [x] **3.3.3** Display Source/StrOrigin (read-only, grey) *(source-preview class)*
- [x] **3.3.4** Display Target/Str (editable textarea) *(TextArea component)*
- [x] **3.3.5** Save button → API call *(saveEdit function)*
- [x] **3.3.6** Double-click target cell → open modal *(openEditModal)*

### 3.4 Frontend: Real-time Updates ✅
```
Location: locaNext/src/lib/stores/ldm.js + components
```

- [x] **3.4.1** Create `ldm.js` store *(with full WebSocket support)*
- [x] **3.4.2** WebSocket connection management *(joinFile, leaveFile, lockRow, unlockRow)*
- [x] **3.4.3** Receive `cell_update` → update grid row *(onCellUpdate, handleCellUpdates)*
- [x] **3.4.4** Create `PresenceBar.svelte` *(shows avatars, viewer count)*
- [x] **3.4.5** Show lock indicator on rows being edited *(Locked icon, tooltip)*

**Phase 3 Completion Checklist:**
- [x] Can edit target text via modal
- [x] Changes saved to database
- [x] Changes broadcast to other users
- [x] See who's online (PresenceBar)
- [x] See lock on rows being edited

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
  "current_phase": 4,
  "current_task": "4.1.1",
  "next_task": "4.1.2",
  "blockers": [],
  "notes": "Phase 3 COMPLETE! Ready for Phase 4: Virtual Scrolling for large files."
}
```

---

## Session Log

| Date | Tasks Completed | Notes |
|------|-----------------|-------|
| 2025-12-08 | Planning complete | Created task list, ready to start |
| 2025-12-08 | Phase 1 COMPLETE (12/12) | Backend models, API, frontend component all done |
| 2025-12-08 | Phase 2 COMPLETE (16/16) | File handlers, upload, FileExplorer, DataGrid |
| 2025-12-08 | Phase 3 COMPLETE (20/20) | WebSocket, real-time sync, presence, row locking |

---

*This file is a working document. Update as tasks complete.*
