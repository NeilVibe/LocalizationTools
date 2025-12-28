# Offline/Online Mode Feature

**Priority:** P3 | **Status:** PLANNING | **Created:** 2025-12-28

---

## Feature Overview

Allow users to work offline when central server is unavailable, with automatic sync and merge when reconnecting.

**Use Cases:**
- Network outage but need to continue working
- Travel/no internet scenarios
- Server maintenance windows
- Performance improvement (local-first)

---

## Current Architecture

```
ONLINE MODE (Current Default):
┌─────────────┐         ┌─────────────┐
│  LocaNext   │  ───►   │  PostgreSQL │
│  (Client)   │  ◄───   │  (Central)  │
└─────────────┘         └─────────────┘

OFFLINE MODE (Exists but limited):
┌─────────────┐
│  LocaNext   │  ───►  SQLite (local)
│  (Client)   │
└─────────────┘
```

---

## Proposed Architecture

```
HYBRID MODE:
┌─────────────┐         ┌─────────────┐
│  LocaNext   │  ⟺     │  PostgreSQL │
│  + SQLite   │  sync   │  (Central)  │
└─────────────┘         └─────────────┘
     │
     └── Local changes queue
```

---

## Feature Requirements

### 1. Mode Detection

```javascript
// Auto-detect server availability
async function checkServerStatus() {
  try {
    const response = await fetch('/api/health', { timeout: 5000 });
    return response.ok ? 'online' : 'offline';
  } catch {
    return 'offline';
  }
}
```

**UI Indicator:**
- Green dot = Online (synced)
- Yellow dot = Online (pending sync)
- Red dot = Offline mode

### 2. Local Change Tracking

All edits while offline are stored in a queue:

```javascript
const changeQueue = {
  file_id: 123,
  row_num: 45,
  field: 'target',
  old_value: 'original text',
  new_value: 'edited text',
  timestamp: '2025-12-28T10:30:00Z',
  sync_status: 'pending'
};
```

### 3. Auto-Merge on Reconnect

When server becomes available:

```
1. Fetch server version of file
2. Compare local changes with server state
3. Apply merge rules (see below)
4. Report conflicts to user
```

---

## Merge Rules

### Rule 1: "Reviewed" Status is Sacred

**If row is marked "Reviewed" on server:**
- Local changes CANNOT overwrite
- User gets conflict notification
- Must manually resolve

```javascript
if (serverRow.status === 'reviewed' && localRow.modified) {
  conflicts.push({
    type: 'reviewed_conflict',
    row: localRow.row_num,
    server_value: serverRow.target,
    local_value: localRow.target,
    message: 'This row was reviewed on server. Manual resolution required.'
  });
}
```

### Rule 2: Same File Merge (Add/Edit)

For same file, same row:

| Server State | Local Change | Result |
|--------------|--------------|--------|
| Unchanged | Edited | Apply local |
| Edited | Edited | CONFLICT |
| Deleted | Edited | CONFLICT |
| Unchanged | Deleted | Apply local |

### Rule 3: New Files

Local files not on server:
- Upload as new file
- OR merge into existing file (user choice)

### Rule 4: Edit-Only Merge

Option to merge only edits (no new rows):

```javascript
const mergeOptions = {
  mode: 'edit_only', // vs 'full' (add + edit)
  overwrite_unreviewed: true,
  skip_reviewed: true
};
```

---

## Conflict Resolution UI

When conflicts exist, show modal:

```
┌─────────────────────────────────────────┐
│  Sync Conflicts (3 items)               │
├─────────────────────────────────────────┤
│  Row 45: "hello" vs "안녕하세요"        │
│  [Keep Server] [Keep Local] [Manual]    │
│                                         │
│  Row 102: (Row deleted on server)       │
│  [Restore] [Accept Deletion]            │
│                                         │
│  Row 200: (Reviewed on server)          │
│  [Keep Server] [Request Re-review]      │
├─────────────────────────────────────────┤
│  [Resolve All: Keep Server]             │
│  [Resolve All: Keep Local]              │
│  [Cancel Sync]                          │
└─────────────────────────────────────────┘
```

---

## Implementation Phases

### Phase 1: Foundation (P3)

1. Add SQLite change tracking table
2. Implement change queue system
3. Add online/offline status indicator
4. Basic auto-reconnect logic

### Phase 2: Sync Engine (P3)

1. Build diff algorithm for rows
2. Implement merge rules
3. Create conflict detection
4. Add sync API endpoints

### Phase 3: UI/UX (P3)

1. Conflict resolution modal
2. Sync progress indicator
3. Manual sync button
4. Offline mode banner

### Phase 4: Advanced (Future)

1. Merge file A → file B (cross-file)
2. Batch conflict resolution
3. Sync history/audit log
4. WebSocket real-time sync

---

## Database Schema Changes

### New Table: `local_changes`

```sql
CREATE TABLE local_changes (
  id INTEGER PRIMARY KEY,
  file_id INTEGER,
  row_num INTEGER,
  field TEXT,           -- 'source', 'target', 'status', etc.
  old_value TEXT,
  new_value TEXT,
  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
  sync_status TEXT DEFAULT 'pending',  -- pending, synced, conflict
  conflict_resolution TEXT,  -- null, 'keep_local', 'keep_server'
  UNIQUE(file_id, row_num, field, timestamp)
);
```

### New Table: `sync_log`

```sql
CREATE TABLE sync_log (
  id INTEGER PRIMARY KEY,
  sync_timestamp DATETIME,
  files_synced INTEGER,
  rows_updated INTEGER,
  conflicts_found INTEGER,
  conflicts_resolved INTEGER,
  status TEXT  -- 'success', 'partial', 'failed'
);
```

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/sync/status` | GET | Check if server is reachable |
| `/api/sync/diff` | POST | Get diff between local and server |
| `/api/sync/push` | POST | Push local changes to server |
| `/api/sync/pull` | GET | Pull server changes to local |
| `/api/sync/resolve` | POST | Submit conflict resolutions |

---

## Technical Considerations

### 1. Data Integrity
- Use transactions for all sync operations
- Checksum verification for transferred data
- Rollback capability if sync fails

### 2. Performance
- Batch sync operations (not row-by-row)
- Compress data for transfer
- Background sync (non-blocking)

### 3. Edge Cases
- Partial sync (network drops mid-sync)
- Multiple clients editing same row
- Server schema changes during offline period

---

## Success Criteria

- [ ] Can work offline when server unavailable
- [ ] Changes persist locally
- [ ] Auto-sync when server returns
- [ ] Conflicts clearly shown
- [ ] Reviewed rows protected
- [ ] Merge options available (full vs edit-only)

---

*Complex feature - Plan thoroughly before implementing*
