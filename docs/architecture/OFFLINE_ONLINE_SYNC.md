# Offline/Online Synchronization System

> **Created:** 2026-01-01 | **Status:** Planning | **Priority:** High

---

## Overview

A manual on-demand synchronization system between Online (PostgreSQL) and Offline (SQLite) modes. Users can work fully offline or online, and sync specific files/folders between modes when needed.

---

## Core Concept

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        LOCANEXT SYNC ARCHITECTURE                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   ┌─────────────────┐                     ┌─────────────────┐          │
│   │   ONLINE MODE   │  ◄── Manual Sync ──►│  OFFLINE MODE   │          │
│   │   PostgreSQL    │                     │     SQLite      │          │
│   │   (Central)     │                     │     (Local)     │          │
│   └─────────────────┘                     └─────────────────┘          │
│          │                                        │                     │
│          │     Same UI (File Explorer/TM)        │                     │
│          │     Different Data Source             │                     │
│          │                                        │                     │
│   ┌──────┴────────────────────────────────────────┴──────┐             │
│   │                   USER INTERFACE                      │             │
│   │  • Mode Toggle: [Online] ◄──► [Offline]              │             │
│   │  • Right-click: Sync to Offline / Sync to Online     │             │
│   │  • Merge: Combine changes from both directions       │             │
│   └──────────────────────────────────────────────────────┘             │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Use Cases

### 1. Field Translator (Primary Use Case)
- Download files to work offline during travel
- Work without internet connection
- Sync completed work back to central server when online

### 2. Solo User (Offline Only)
- Use LocaNext purely offline with SQLite
- No need for central server
- All data stays local

### 3. Team Collaboration
- Multiple users work online on central PostgreSQL
- Individual users can sync specific files offline for focused work
- Merge changes back with conflict resolution

---

## Feature Requirements

### F1: Mode Toggle UI

```
┌─────────────────────────────────────────────────────────────┐
│  LocaNext    [Apps]  [Tasks]  [Settings]        [admin]    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   Connection Mode:  ● Online (PostgreSQL)                   │
│                     ○ Offline (SQLite - Local)              │
│                                                             │
│   [Switch Mode]                                             │
│                                                             │
│   Status: Connected to central server                       │
│   Last Sync: 2026-01-01 10:30:00                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Location:** Settings menu or top navbar indicator

### F2: Sync to Offline (Download)

**Trigger:** Right-click file/folder in Online mode → "Sync to Offline..."

```
┌─────────────────────────────────────────────────────────────┐
│                    SYNC TO OFFLINE                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Source (Online):                                           │
│  📁 BDO_EN_Project / 📄 game_strings.txt (12,450 rows)     │
│                                                             │
│  Destination (Offline SQLite):                              │
│  [▼ Select Project...        ]                              │
│     └─ [▼ Select Folder...   ] (optional)                  │
│                                                             │
│  Options:                                                   │
│  [x] Include TM matches                                     │
│  [ ] Overwrite if exists                                    │
│                                                             │
│                         [Cancel]  [⬇ Sync to Offline]      │
└─────────────────────────────────────────────────────────────┘
```

**Prerequisite:** At least one project must exist in offline SQLite DB

### F3: Sync to Online (Upload)

**Trigger:** Right-click file/folder in Offline mode → "Sync to Online..."

```
┌─────────────────────────────────────────────────────────────┐
│                    SYNC TO ONLINE                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Source (Offline):                                          │
│  📁 Local_Project / 📄 translations.txt (5,000 rows)       │
│                                                             │
│  Destination (Online PostgreSQL):                           │
│  [▼ Select Project...        ]                              │
│     └─ [▼ Select Folder...   ] (optional)                  │
│                                                             │
│  Options:                                                   │
│  [ ] Overwrite if exists                                    │
│  [x] Create project if not exists                           │
│                                                             │
│                         [Cancel]  [⬆ Sync to Online]       │
└─────────────────────────────────────────────────────────────┘
```

### F4: Merge Between Modes

**Use Case:** File exists in both modes with different changes

```
┌─────────────────────────────────────────────────────────────┐
│                      MERGE FILES                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Online Version:  game_strings.txt (modified 2026-01-01)    │
│  Offline Version: game_strings.txt (modified 2025-12-31)   │
│                                                             │
│  Merge Direction:                                           │
│  ● Online → Offline (download updates)                      │
│  ○ Offline → Online (upload my changes)                     │
│  ○ Two-way merge (combine both)                            │
│                                                             │
│  Conflict Resolution:                                       │
│  ● Keep newer version                                       │
│  ○ Keep online version                                      │
│  ○ Keep offline version                                     │
│  ○ Manual review                                            │
│                                                             │
│                         [Cancel]  [🔀 Merge]               │
└─────────────────────────────────────────────────────────────┘
```

### F5: Context Menu Items

**Online Mode Context Menu:**
```
├── Rename
├── Download File
├── Merge...
├── Convert to...
├── ─────────────
├── Sync to Offline...     ← NEW
├── ─────────────
├── Pretranslate...
├── Run QA
└── ...
```

**Offline Mode Context Menu:**
```
├── Rename
├── Download File
├── Merge...
├── Convert to...
├── ─────────────
├── Sync to Online...      ← NEW
├── Merge with Online...   ← NEW
├── ─────────────
├── Pretranslate...
├── Run QA
└── ...
```

---

## Technical Implementation

### Backend Changes

1. **New API Endpoints:**
   ```
   POST /api/sync/to-offline
   POST /api/sync/to-online
   POST /api/sync/merge
   GET  /api/sync/status/{file_id}
   GET  /api/sync/diff/{file_id}
   ```

2. **Sync Service:**
   - Copy file data between PostgreSQL ↔ SQLite
   - Handle row-level sync with timestamps
   - Conflict detection based on `updated_at`

3. **Mode Detection:**
   - Already exists: `connectionMode` prop in FileExplorer
   - Enhance to support manual mode switching

### Frontend Changes

1. **Mode Toggle Component:**
   - Add to Settings or top navbar
   - Show current mode indicator
   - Handle mode switch with confirmation

2. **Sync Modals:**
   - SyncToOfflineModal.svelte
   - SyncToOnlineModal.svelte
   - MergeSyncModal.svelte

3. **Context Menu Updates:**
   - Add sync options based on current mode
   - Show sync status indicators on files

---

## Data Model

### Sync Metadata Table (Both DBs)

```sql
CREATE TABLE sync_metadata (
    id SERIAL PRIMARY KEY,
    file_id INTEGER REFERENCES ldm_files(id),
    local_hash VARCHAR(64),      -- Hash of local content
    remote_hash VARCHAR(64),     -- Hash of remote content
    last_sync_at TIMESTAMP,
    sync_direction VARCHAR(20),  -- 'to_offline', 'to_online', 'merged'
    conflict_status VARCHAR(20), -- 'none', 'pending', 'resolved'
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

---

## UI/UX Flow

### Scenario 1: Download for Offline Work

```
1. User is in ONLINE mode
2. Right-click file → "Sync to Offline..."
3. Select destination project/folder in offline DB
4. Click "Sync to Offline"
5. File copied to SQLite
6. Toast: "File synced to offline successfully"
7. User can now switch to OFFLINE mode and see the file
```

### Scenario 2: Upload Completed Work

```
1. User is in OFFLINE mode (worked without internet)
2. Internet available now
3. Right-click file → "Sync to Online..."
4. Select destination project/folder in online DB
5. Click "Sync to Online"
6. File uploaded to PostgreSQL
7. Toast: "File synced to online successfully"
```

### Scenario 3: Merge Conflict

```
1. User synced file offline, made changes
2. Another user modified same file online
3. User tries to sync back online
4. System detects conflict (different hashes)
5. Merge modal appears with options
6. User selects merge strategy
7. Conflict resolved, file synced
```

---

## Priority & Phases

### Phase 1: Basic Sync (MVP)
- [ ] Mode toggle UI
- [ ] Sync to Offline (file only)
- [ ] Sync to Online (file only)
- [ ] Basic overwrite strategy

### Phase 2: Folder Sync
- [ ] Sync entire folders
- [ ] Recursive sync with progress
- [ ] Folder structure preservation

### Phase 3: Smart Merge
- [ ] Conflict detection
- [ ] Row-level diff
- [ ] Merge strategies
- [ ] Manual conflict resolution UI

### Phase 4: TM Sync
- [ ] Sync Translation Memories
- [ ] TM merge strategies
- [ ] Cross-mode TM matching

---

## Open Questions

1. **Auto-sync option?** - Should we offer automatic sync when connection restored?
2. **Sync history?** - Should we track sync operations for audit?
3. **Partial sync?** - Sync only changed rows vs entire file?
4. **TM sharing?** - How to handle TM sync between modes?

---

## Related Documents

- [Offline/Online Mode](./OFFLINE_ONLINE_MODE.md)
- [Session Context](../current/SESSION_CONTEXT.md)
- [Architecture Summary](./ARCHITECTURE_SUMMARY.md)

---

*Document created: 2026-01-01 | Updated: 2026-01-11*
