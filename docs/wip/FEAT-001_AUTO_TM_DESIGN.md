# FEAT-001: Auto-Add to TM on Cell Confirm (FULL Implementation)

**Status:** READY TO IMPLEMENT | **Priority:** CRITICAL | **Created:** 2025-12-21

---

## Problem Statement

When user confirms a cell (Ctrl+S → status='reviewed'), it should auto-add the source/target pair to the project's linked TM. Currently it only saves to DB and does NOT update the TM.

---

## GOOD NEWS: Smart FAISS Already Exists!

We already have intelligent FAISS/embedding sync:

| Operation | Method | Speed |
|-----------|--------|-------|
| **INSERT only** | `_incremental_sync()` → `FAISSManager.incremental_add()` | ~30-50ms |
| **UPDATE/DELETE** | Smart rebuild (cache unchanged, embed only changed) | ~2-10s |

**Key Code:**
- `server/tools/ldm/tm_indexer.py:1568` - `_incremental_sync()`
- `server/tools/shared/faiss_manager.py:216` - `FAISSManager.incremental_add()`

So when we INSERT a new TM entry on confirm, the background sync will use the SUPER FAST incremental path!

---

## Architecture: FULL Database-Backed Implementation

### Target Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     TARGET ARCHITECTURE                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. ADMIN: Link TM to Project                                   │
│  ┌─────────────────────────────────────────────────────────────┐
│  │ POST /api/ldm/projects/{id}/link-tm                         │
│  │   { tm_id: 5, priority: 0 }                                 │
│  │                                                             │
│  │ Creates LDMActiveTM record:                                 │
│  │   tm_id=5, project_id=10, priority=0                        │
│  └─────────────────────────────────────────────────────────────┘
│                                                                 │
│  2. USER: Edit cell and confirm (Ctrl+S)                        │
│  ┌─────────────────────────────────────────────────────────────┐
│  │ PUT /api/ldm/rows/{id}                                      │
│  │   { target: "Hello", status: "reviewed" }                   │
│  └─────────────────────────────────────────────────────────────┘
│                              │                                  │
│                              ▼                                  │
│  3. BACKEND: update_row() auto-adds to TM                       │
│  ┌─────────────────────────────────────────────────────────────┐
│  │ a) Save row to LDMRow                          ✅ EXISTS    │
│  │ b) Create edit history                         ✅ EXISTS    │
│  │ c) WebSocket broadcast                         ✅ EXISTS    │
│  │ d) If status='reviewed':                       🆕 NEW       │
│  │    - Get file's project_id                                  │
│  │    - Query LDMActiveTM for linked TM                        │
│  │    - Call tm_manager.add_entry()                            │
│  │    - Trigger _auto_sync_tm_indexes()                        │
│  └─────────────────────────────────────────────────────────────┘
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Database: LDMActiveTM (Already Exists!)

```python
# server/database/models.py:853-888
class LDMActiveTM(Base):
    __tablename__ = "ldm_active_tms"

    id = Column(Integer, primary_key=True)
    tm_id = Column(Integer, ForeignKey("ldm_translation_memories.id"))
    project_id = Column(Integer, ForeignKey("ldm_projects.id"))  # Link to project
    file_id = Column(Integer, ForeignKey("ldm_files.id"))        # OR link to file
    priority = Column(Integer, default=0)                         # Lower = higher priority
    activated_by = Column(Integer, ForeignKey("users.user_id"))
    activated_at = Column(DateTime, default=datetime.utcnow)
```

**Table exists but is NEVER USED!** We just need to add the APIs.

---

## Implementation Plan

### Phase 1: Backend - New API Endpoints

**File:** `server/tools/ldm/api.py`

#### 1.1 Link TM to Project

```python
@router.post("/projects/{project_id}/link-tm")
async def link_tm_to_project(
    project_id: int,
    tm_id: int,
    priority: int = 0,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Link a TM to a project. All confirmed cells in this project
    will auto-add to this TM.
    """
    # Verify project ownership
    # Verify TM ownership
    # Check if link already exists
    # Create LDMActiveTM record
    # Return success
```

#### 1.2 Unlink TM from Project

```python
@router.delete("/projects/{project_id}/link-tm/{tm_id}")
async def unlink_tm_from_project(
    project_id: int,
    tm_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """Remove TM link from project."""
    # Delete LDMActiveTM record
```

#### 1.3 Get Linked TMs for Project

```python
@router.get("/projects/{project_id}/linked-tms")
async def get_linked_tms(
    project_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """Get all TMs linked to a project, ordered by priority."""
    # Query LDMActiveTM WHERE project_id = X
    # Join with LDMTranslationMemory for TM details
    # Return list with tm_id, name, priority, status
```

---

### Phase 2: Backend - Update Row Logic

**File:** `server/tools/ldm/api.py` - `update_row()` function (line 728-798)

#### 2.1 Add Helper Function

```python
async def _get_project_linked_tm(db: AsyncSession, project_id: int, user_id: int) -> Optional[int]:
    """
    Get the highest-priority linked TM for a project.
    Returns tm_id or None if no TM linked.
    """
    result = await db.execute(
        select(LDMActiveTM.tm_id)
        .join(LDMTranslationMemory, LDMActiveTM.tm_id == LDMTranslationMemory.id)
        .where(
            LDMActiveTM.project_id == project_id,
            LDMTranslationMemory.owner_id == user_id  # User must own TM
        )
        .order_by(LDMActiveTM.priority)
        .limit(1)
    )
    row = result.scalar_one_or_none()
    return row
```

#### 2.2 Update update_row() Function

Add after line 778 (after `await db.commit()`):

```python
# FEAT-001: Auto-add to linked TM if status is 'reviewed'
if row.status == "reviewed" and row.source and row.target:
    try:
        # Get project's linked TM
        project_id = row.file.project_id
        linked_tm_id = await _get_project_linked_tm(db, project_id, current_user["user_id"])

        if linked_tm_id:
            # Add entry to TM in background thread
            def _add_to_tm():
                sync_db = next(get_db())
                try:
                    from server.tools.ldm.tm_manager import TMManager
                    tm_manager = TMManager(sync_db)
                    return tm_manager.add_entry(linked_tm_id, row.source, row.target)
                finally:
                    sync_db.close()

            result = await asyncio.to_thread(_add_to_tm)

            if result:
                # Trigger index rebuild in background
                background_tasks.add_task(
                    _auto_sync_tm_indexes,
                    linked_tm_id,
                    current_user["user_id"]
                )
                logger.info(f"FEAT-001: Auto-added to TM {linked_tm_id}: row_id={row_id}")
    except Exception as e:
        # Don't fail the row update, just log warning
        logger.warning(f"FEAT-001: Auto-add to TM failed: {e}")
```

#### 2.3 Add BackgroundTasks Dependency

Update function signature:

```python
async def update_row(
    row_id: int,
    update: RowUpdate,
    background_tasks: BackgroundTasks,  # ADD THIS
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
```

---

### Phase 3: Frontend - Project TM Link UI

**File:** `locaNext/src/lib/components/ldm/FileExplorer.svelte` (or new component)

#### 3.1 Add TM Link Dropdown in Project Header

```svelte
<!-- In project item, add a TM link button/dropdown -->
<div class="project-tm-link">
  <select bind:value={linkedTmId} on:change={() => linkTmToProject(project.id, linkedTmId)}>
    <option value={null}>No TM linked</option>
    {#each tms as tm}
      <option value={tm.id}>{tm.name}</option>
    {/each}
  </select>
</div>
```

#### 3.2 API Functions

```javascript
async function linkTmToProject(projectId, tmId) {
  await fetch(`${API_BASE}/api/ldm/projects/${projectId}/link-tm`, {
    method: 'POST',
    headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
    body: JSON.stringify({ tm_id: tmId, priority: 0 })
  });
}

async function getLinkedTms(projectId) {
  const response = await fetch(`${API_BASE}/api/ldm/projects/${projectId}/linked-tms`, {
    headers: getAuthHeaders()
  });
  return await response.json();
}
```

---

### Phase 4: Frontend - Remove Local Storage Approach

**Files to update:**
- `locaNext/src/lib/stores/preferences.js` - Remove `activeTmId` (or keep for backwards compat)
- `locaNext/src/lib/components/ldm/TMManager.svelte` - Update toggle to use API
- `locaNext/src/lib/components/ldm/VirtualGrid.svelte` - Get linked TM from project, not preferences

---

## Implementation Order

### Step 1: Backend APIs (No UI changes needed for testing)

| Task | File | Lines |
|------|------|-------|
| 1.1 | Add `link_tm_to_project` endpoint | api.py |
| 1.2 | Add `unlink_tm_from_project` endpoint | api.py |
| 1.3 | Add `get_linked_tms` endpoint | api.py |
| 1.4 | Add `_get_project_linked_tm` helper | api.py |
| 1.5 | Update `update_row` with auto-add logic | api.py:728-798 |
| 1.6 | Add `BackgroundTasks` to `update_row` | api.py |

### Step 2: Test Backend with curl

```bash
# Link TM to project
curl -X POST "http://localhost:8888/api/ldm/projects/1/link-tm" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"tm_id": 1, "priority": 0}'

# Get linked TMs
curl "http://localhost:8888/api/ldm/projects/1/linked-tms" \
  -H "Authorization: Bearer $TOKEN"

# Update row (should auto-add to TM)
curl -X PUT "http://localhost:8888/api/ldm/rows/1" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"target": "Hello", "status": "reviewed"}'

# Check TM entries increased
curl "http://localhost:8888/api/ldm/tm/1" \
  -H "Authorization: Bearer $TOKEN"
```

### Step 3: Frontend UI

| Task | File |
|------|------|
| 3.1 | Add TM link dropdown to project | FileExplorer.svelte |
| 3.2 | Load linked TM on project expand | FileExplorer.svelte |
| 3.3 | Show linked TM indicator | FileExplorer.svelte |

### Step 4: Tests

| Test | Type |
|------|------|
| `test_link_tm_to_project` | Unit |
| `test_unlink_tm_from_project` | Unit |
| `test_get_linked_tms` | Unit |
| `test_update_row_auto_adds_to_tm` | Integration |
| `test_update_row_no_linked_tm` | Integration |
| `test_confirm_cell_adds_to_tm_e2e` | E2E |

---

## Summary: Files to Modify

| File | Changes |
|------|---------|
| `server/tools/ldm/api.py` | +3 endpoints, +1 helper, update `update_row` |
| `locaNext/src/lib/components/ldm/FileExplorer.svelte` | Add TM link UI |
| `tests/integration/test_tm_auto_add.py` | NEW: Test file |

---

## Success Criteria

1. ✅ User can link TM to project via UI
2. ✅ Linked TM shows indicator on project
3. ✅ Ctrl+S (confirm) auto-adds to linked TM
4. ✅ TM index auto-rebuilds after add
5. ✅ Works for all users in project (not per-device)
6. ✅ No TM linked = no auto-add (silent)

---

---

## Complete Data Flow: Millisecond by Millisecond

```
USER PRESSES Ctrl+S (Confirm cell)
         │
         │ [0ms] Frontend: editStatus = 'reviewed', call saveEdit()
         │ [1ms] Frontend: fetch('PUT /api/ldm/rows/123', {target, status})
         │
         ▼ ════════════════════════════════════════════════════════════
         │           CENTRAL SERVER (PostgreSQL)
         ▼ ════════════════════════════════════════════════════════════
         │
         │ [2ms]  Parse request, authenticate user
         │
         │ [3ms]  SELECT * FROM ldm_rows WHERE id=123
         │        (load row with file/project relationships)
         │
         │ [4ms]  Verify user owns project
         │
         │ [5ms]  UPDATE ldm_rows SET
         │          target = 'Hello',
         │          status = 'reviewed',
         │          updated_by = user_id,
         │          updated_at = NOW()
         │
         │ [6ms]  INSERT INTO ldm_edit_history
         │          (row_id, old_target, new_target, old_status, new_status)
         │
         │ [7ms]  COMMIT (row saved to central DB)
         │
         │ [8ms]  WebSocket.broadcast({cell_update})
         │        → All other users see change instantly
         │
         │ ══════════════ 🆕 FEAT-001 NEW CODE ══════════════
         │
         │ [9ms]  IF status == 'reviewed' AND source AND target:
         │          │
         │          ▼
         │ [10ms]   SELECT tm_id FROM ldm_active_tms
         │          WHERE project_id = row.file.project_id
         │          ORDER BY priority LIMIT 1
         │          │
         │          ▼
         │ [11ms]   IF linked_tm_id:
         │            │
         │            ▼
         │ [12ms]     INSERT INTO ldm_tm_entries
         │              (tm_id, source_text, target_text, source_hash)
         │            │
         │            ▼
         │ [13ms]     COMMIT (TM entry saved to central DB)
         │            │
         │            ▼
         │ [14ms]     BackgroundTasks.add(_auto_sync_tm_indexes)
         │
         │ ══════════════════════════════════════════════════
         │
         │ [15ms]   Return HTTP 200 {row_data, tm_updated: true}
         │
         ▼ ════════════════════════════════════════════════════════════
         │           USER SEES RESPONSE (~15ms total)
         ▼ ════════════════════════════════════════════════════════════
         │
         │ [16ms]   Frontend updates local grid
         │ [17ms]   Close edit modal, show success
         │
         ▼ ════════════════════════════════════════════════════════════
         │           BACKGROUND (User doesn't wait)
         ▼ ════════════════════════════════════════════════════════════
         │
         │ [20ms]    _auto_sync_tm_indexes() starts
         │
         │ [25ms]    TMSyncManager.sync():
         │             ├── compute_diff() → finds 1 INSERT
         │             ├── can_incremental = TRUE ✅
         │             │
         │             └── _incremental_sync():
         │                   │
         │ [30ms]             ├── Load existing FAISS index
         │ [35ms]             ├── Model2Vec.encode([new_text]) ← SUPER FAST
         │ [40ms]             ├── FAISSManager.incremental_add()
         │ [45ms]             └── Save updated index + mapping
         │
         │ [50ms]    UPDATE ldm_translation_memories
         │             SET status = 'ready', updated_at = NOW()
         │
         │ [55ms]    COMMIT (TM index ready)
         │
         ▼ ════════════════════════════════════════════════════════════
                    DONE! TM is updated and searchable
         ════════════════════════════════════════════════════════════
```

---

## What Already Works ✅

| Component | Status | Speed |
|-----------|--------|-------|
| Row UPDATE to central DB | ✅ WORKS | ~5ms |
| Edit history INSERT | ✅ WORKS | ~2ms |
| WebSocket broadcast | ✅ WORKS | ~1ms |
| TM entry INSERT | ✅ EXISTS (just not called) | ~3ms |
| Smart FAISS incremental add | ✅ EXISTS | ~30ms |
| Model2Vec embeddings | ✅ DEFAULT (79x faster) | ~5ms |
| Background task system | ✅ EXISTS | async |

---

## What We Need to Add 🆕

| Task | Location | Lines of Code |
|------|----------|---------------|
| **1. Link TM to Project API** | `api.py` | ~30 lines |
| **2. Unlink TM API** | `api.py` | ~15 lines |
| **3. Get Linked TMs API** | `api.py` | ~20 lines |
| **4. Helper: _get_project_linked_tm()** | `api.py` | ~15 lines |
| **5. Update update_row() with TM logic** | `api.py:778` | ~25 lines |
| **6. Frontend: TM link dropdown** | `FileExplorer.svelte` | ~50 lines |
| **TOTAL** | | **~155 lines** |

---

## File Stats (Optional Enhancement)

For memoQ-style file progress (50 translated, 30 reviewed):

```python
# GET /files/{id}/stats - Compute on demand
@router.get("/files/{file_id}/stats")
async def get_file_stats(file_id: int, db: AsyncSession):
    result = await db.execute("""
        SELECT status, COUNT(*) as count
        FROM ldm_rows
        WHERE file_id = :file_id
        GROUP BY status
    """, {"file_id": file_id})

    stats = {row.status: row.count for row in result}
    total = sum(stats.values())

    return {
        "total": total,
        "pending": stats.get("pending", 0),
        "translated": stats.get("translated", 0),
        "reviewed": stats.get("reviewed", 0),
        "progress_translated": round(stats.get("translated", 0) / total * 100) if total else 0,
        "progress_reviewed": round(stats.get("reviewed", 0) / total * 100) if total else 0
    }
```

---

## Implementation Checklist

### Phase 1: Backend APIs
- [ ] 1.1 Add `POST /projects/{id}/link-tm` endpoint
- [ ] 1.2 Add `DELETE /projects/{id}/link-tm/{tm_id}` endpoint
- [ ] 1.3 Add `GET /projects/{id}/linked-tms` endpoint
- [ ] 1.4 Add `_get_project_linked_tm()` helper function
- [ ] 1.5 Update `update_row()` with auto-add logic
- [ ] 1.6 Add `BackgroundTasks` dependency to `update_row`

### Phase 2: Test Backend
- [ ] 2.1 Test link TM to project via curl
- [ ] 2.2 Test confirm cell → verify TM entry added
- [ ] 2.3 Test TM index rebuilt (check FAISS file timestamp)

### Phase 3: Frontend UI
- [ ] 3.1 Add TM link dropdown to project header
- [ ] 3.2 Load linked TM on project expand
- [ ] 3.3 Show linked TM indicator badge

### Phase 4: Optional - File Stats
- [ ] 4.1 Add `GET /files/{id}/stats` endpoint
- [ ] 4.2 Show progress bar in file list

### Phase 5: Tests
- [ ] 5.1 Unit test: link/unlink TM
- [ ] 5.2 Integration test: confirm → TM add
- [ ] 5.3 E2E test: full workflow

---

*FEAT-001 Full Implementation Plan | Created 2025-12-21*
