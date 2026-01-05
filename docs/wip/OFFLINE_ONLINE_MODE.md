# Offline/Online Mode - Complete Specification

**Priority:** P3 | **Status:** IN PROGRESS | **Created:** 2025-12-28 | **Updated:** 2026-01-05

---

## Executive Summary

**Automatic connection with manual sync** between Online (PostgreSQL) and Offline (SQLite) modes.

- **Auto-connect:** Always online if server reachable, auto-fallback to offline
- **Manual sync:** Users choose WHAT to sync and WHEN (right-click)
- **Add/Edit only:** No deletions synced between modes
- **Recycle Bin:** 30-day soft delete before permanent removal
- **Beautiful UI:** Sync Dashboard, Toast notifications, Info bars, Status icons

---

## P9 Backend Implementation (2026-01-05)

### Pattern: PostgreSQL First, SQLite Fallback

All endpoints now follow this pattern:

```python
# Try PostgreSQL first
result = await db.execute(select(LDMFile).where(LDMFile.id == file_id))
file = result.scalar_one_or_none()

if not file:
    # Fallback to SQLite
    from server.database.offline import get_offline_db
    offline_db = get_offline_db()
    file_data = offline_db.get_local_file(file_id)
    if not file_data:
        raise HTTPException(status_code=404, detail="Not found")
    # Use SQLite data...
```

### Endpoints with SQLite Fallback (Completed)

| Endpoint | Fallback | Notes |
|----------|----------|-------|
| `GET /files/{id}` | ✅ | Returns local file info |
| `GET /files/{id}/rows` | ✅ | Returns local rows |
| `PUT /rows/{id}` | ✅ | Saves to SQLite |
| `GET /files/{id}/convert` | ✅ | Converts local file |
| `GET /files/{id}/extract-glossary` | ✅ | Extracts from local |
| `POST /files/{id}/check-qa` | ✅ | QA check on local |
| `POST /files/{id}/register-as-tm` | ✅ | Creates TM from local |
| `POST /pretranslate` | ✅ | Pretranslates local rows |
| `GET /search` | ✅ | Searches SQLite in offline mode |
| `GET /projects` | ✅ | Includes "Offline Storage" virtual project |
| `GET /tm` | ✅ | Includes SQLite TMs |

### Schema Compatibility (Optional Datetime)

All response schemas have optional datetime fields for SQLite compatibility:

```python
class ProjectResponse(BaseModel):
    id: int
    name: str
    created_at: Optional[datetime] = None  # P9: Optional for SQLite
    updated_at: Optional[datetime] = None  # P9: Optional for SQLite
```

This allows SQLite data (which may have NULL timestamps) to pass validation.

### Virtual "Offline Storage" Project

When local files exist, the projects list includes a virtual project:

```python
# Virtual project in /api/ldm/projects
{
    "id": 0,  # Special ID for Offline Storage
    "name": "Offline Storage",
    "description": "X local file(s)",
    "platform_id": null
}
```

### Search Mode Parameter

The `/api/ldm/search` endpoint accepts `mode` parameter:

```
GET /api/ldm/search?q=test&mode=online   # Search PostgreSQL + local files
GET /api/ldm/search?q=test&mode=offline  # Search SQLite only
```

---

## P9 Launcher Integration (2026-01-04)

### Launcher "Start Offline" Mode

The P9 Launcher adds a **game-launcher style** startup:

```
┌─────────────────────────────────────────────────────────┐
│                    [LocaNext Logo]                      │
│                      v26.104.1600                       │
│                                                         │
│        ╭─────────────────╮  ╭─────────────────╮         │
│        │  Start Offline  │  │     Login       │         │
│        │  Work locally   │  │  Connect to     │         │
│        │  No account     │  │  server         │         │
│        ╰─────────────────╯  ╰─────────────────╯         │
└─────────────────────────────────────────────────────────┘
```

### Offline Mode Permissions (CRITICAL)

**Offline Storage = Your Sandbox** (full control)
**Downloaded Content = Read Structure, Edit Content Only**

```
OFFLINE MODE VIEW
─────────────────────────────────────────────────────
📁 Offline Storage          ← FULL CONTROL
   📁 My Drafts             ← Can create folders
      📄 new_work.txt       ← Can import/create files
   📄 imported.xlsx         ← Can edit, delete, move

📁 Nintendo (downloaded)    ← READ-ONLY STRUCTURE
   📁 Mario Kart            ← Can't rename/delete/move
      📄 menu.txt           ← Can EDIT CONTENT (rows)
                            ← Can't rename/move file
```

| Area | Create | Read | Edit Content | Rename/Move/Delete |
|------|--------|------|--------------|-------------------|
| **Offline Storage** | ✅ Folders, Files | ✅ | ✅ | ✅ |
| **Downloaded paths** | ❌ | ✅ | ✅ (rows only) | ❌ |

### Key Technical Details

- **No admin rights** - OFFLINE user has `role: "user"`
- **Token format** - `OFFLINE_MODE_<timestamp>` (recognized by backend)
- **Storage location** - `~/.local/share/locanext/offline.db` (Linux)
- **Offline Storage visible** - Always shows when `$offlineMode === true`

### Going Online from Offline

1. Click "Go Online" button
2. Login modal appears
3. Enter credentials → authenticate against PostgreSQL
4. Now see BOTH: Offline Storage + PostgreSQL tree
5. Move files from Offline Storage to desired projects (Ctrl+X/V)
6. Files sync to PostgreSQL at new location

---

## Core Principles

| Principle | Description |
|-----------|-------------|
| **Auto-Connect** | Always online if server reachable, auto-fallback to offline |
| **Manual Sync** | User explicitly triggers every sync action (right-click) |
| **File-Level Granularity** | Sync individual files, not entire database |
| **Add/Edit Only** | Merge adds new rows and edits existing - NO DELETE |
| **Path-Aware** | Files matched by full path (platform/project/folder/file) |
| **Server = Path Truth** | Online DB decides file location. Moving files offline reverts on sync. |
| **Visible Mode** | Online/Offline status always clearly visible |
| **Graceful Degradation** | 90% features work offline |
| **Recycle Bin** | Deleted files go to Bin, 30-day expiry before permanent deletion |

### Path Hierarchy Rule (CRITICAL)

**Server is the source of truth for file paths/structure.**

```
ALLOWED offline:
  ✅ Edit file content (target, memo, status)
  ✅ Add new rows to existing files

NOT ALLOWED offline (reverts on sync):
  ❌ Move file to different folder
  ❌ Move folder to different project
  ❌ Rename platform/project/folder
  ❌ Create new platforms/projects/folders

WHY: Prevents merge conflicts on structure. Content can merge, structure cannot.
```

When syncing:
1. Server path is always applied
2. Local path changes are discarded
3. File content (rows) is merged normally

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         LocaNext App                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌─────────────┐                      ┌─────────────┐          │
│   │   ONLINE    │    Manual Sync       │   OFFLINE   │          │
│   │ PostgreSQL  │ ◄────────────────► │   SQLite    │          │
│   │  (Central)  │    Right-Click       │   (Local)   │          │
│   └─────────────┘                      └─────────────┘          │
│         │                                    │                  │
│         │  ┌──────────────────────────┐      │                  │
│         └──│     Sync Manager         │──────┘                  │
│            │  - Path matching         │                         │
│            │  - Add/Edit merge        │                         │
│            │  - Conflict detection    │                         │
│            │  - Change queue          │                         │
│            └──────────────────────────┘                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## User Interface

### 1. Mode Indicator (Always Visible)

**Location:** Top-right of app bar, always visible

```
┌─────────────────────────────────────────────────────────────────┐
│  LocaNext    Files   TM   Dashboard         🟢 ONLINE    ⚙️ 👤  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  LocaNext    Files   TM   Dashboard         🔴 OFFLINE   ⚙️ 👤  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  LocaNext    Files   TM   Dashboard         🟡 SYNCING   ⚙️ 👤  │
└─────────────────────────────────────────────────────────────────┘
```

**Mode Indicator States:**

| Icon | State | Meaning |
|------|-------|---------|
| 🟢 | ONLINE | Connected to central server |
| 🔴 | OFFLINE | Working locally only |
| 🟡 | SYNCING | Sync in progress |
| 🟠 | PENDING | Has local changes not yet synced |

**Click on indicator** → Opens Sync Dashboard Modal (see below)

---

### 2. Sync Dashboard Modal (Click on Mode Indicator)

**Beautiful dashboard showing sync status at a glance:**

```
┌─────────────────────────────────────────────────────────────────┐
│  Sync Dashboard                                           [X]   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────┐  ┌──────────────────────┐            │
│  │  🟢 ONLINE           │  │  📊 Storage          │            │
│  │  ──────────────────  │  │  ──────────────────  │            │
│  │  Server: Connected   │  │  Offline: 45 MB      │            │
│  │  Latency: 23ms       │  │  Bin: 12 MB          │            │
│  │  Last check: Just now│  │  TMs: 8 downloaded   │            │
│  └──────────────────────┘  └──────────────────────┘            │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  📤 PENDING SYNC                                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ File                           Changes   Last Edit      │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │ 📄 PC/BDO/Korean/quest.xlsx    47 edits  2 hours ago   │   │
│  │ 📄 PC/BDO/Korean/items.xlsx    12 edits  30 min ago    │   │
│  │ 📚 BDO_Main_TM                 5 entries 1 hour ago    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  [Sync All]                                                     │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  📥 OFFLINE FILES (8 files, 3 TMs)                              │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ File                           Status    Downloaded     │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │ 📄 PC/BDO/Korean/quest.xlsx    🔄 Modified  Yesterday   │   │
│  │ 📄 PC/BDO/Korean/items.xlsx    🔄 Modified  Yesterday   │   │
│  │ 📄 PC/BDO/UI/buttons.txt       💾 Synced    3 days ago  │   │
│  │ 📚 BDO_Main_TM                 🔄 Modified  Yesterday   │   │
│  │ ... (5 more)                                 [Show All] │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  🗑️ RECYCLE BIN (3 items)                           [View Bin] │
│                                                                 │
│  📜 SYNC HISTORY                                  [View History]│
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Dashboard Sections:**
| Section | Shows |
|---------|-------|
| **Status Card** | Online/Offline, server latency, last check |
| **Storage Card** | Offline storage used, bin size, TM count |
| **Pending Sync** | Files with local changes waiting to sync |
| **Offline Files** | All files downloaded for offline use |
| **Recycle Bin** | Quick access to bin |
| **Sync History** | Recent sync operations |

---

### 3. Auto-Connect Behavior

**Connection is AUTOMATIC.** No manual toggle needed.

```
App Startup:
  └─ Check server → Reachable? → 🟢 ONLINE
                  → Not reachable? → 🔴 OFFLINE (toast notification)

During Use:
  └─ Server becomes unreachable → Auto-switch to 🔴 OFFLINE (toast)
  └─ Server becomes reachable → Auto-switch to 🟢 ONLINE (toast)
```

**Toast Notifications:**

```
┌─────────────────────────────────────────┐
│ 🔴 Switched to Offline Mode             │
│ Server unreachable. Working locally.    │
│                                 [Dismiss]│
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ 🟢 Back Online                          │
│ Server connected. You have 3 files      │
│ with pending changes.        [View Sync]│
└─────────────────────────────────────────┘
```

---

### 4. Sync Reminder (Toast + Info Bar)

**When there are pending changes to sync:**

**Toast (on reconnect):**
```
┌─────────────────────────────────────────┐
│ 📤 Pending Sync                         │
│ 3 files have local changes to sync.     │
│                    [Later]   [View Sync]│
└─────────────────────────────────────────┘
```

**Info Bar (on file with pending changes):**
```
┌─────────────────────────────────────────────────────────────────┐
│ ⚠️ This file has 47 local changes not synced.    [Sync Now] [X] │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [Grid content below...]                                        │
```

The info bar appears at the top of the grid when viewing a file with pending changes.

---

### 5. Right-Click Context Menu (File Level)

**In File Explorer - Right-click on file:**

```
┌─────────────────────────────┐
│ 📄 quest_strings.xlsx       │
├─────────────────────────────┤
│ Open                        │
│ ─────────────────────────── │
│ 📥 Download to Offline      │  ← When ONLINE, file not yet local
│ 📤 Sync to Online           │  ← When file has local changes
│ 🔄 Refresh from Online      │  ← Pull latest from server
│ ─────────────────────────── │
│ Pretranslate...             │
│ Run QA                      │
│ Convert to...               │
│ ─────────────────────────── │
│ Properties                  │
│ Delete                      │
└─────────────────────────────┘
```

**Context menu items explained:**

| Action | When Visible | What It Does |
|--------|--------------|--------------|
| **Download to Offline** | Online mode, file not local | Copy file + structure to SQLite |
| **Sync to Online** | Has local changes pending | Push local edits to PostgreSQL |
| **Refresh from Online** | Online mode, file is local | Pull latest server version |

---

### 6. Right-Click Context Menu (Folder/Project Level)

**In File Explorer - Right-click on folder:**

```
┌─────────────────────────────┐
│ 📁 Korean_Strings           │
├─────────────────────────────┤
│ Open                        │
│ ─────────────────────────── │
│ 📥 Download Folder to Offline│  ← Downloads ALL files in folder
│ 📤 Sync Folder to Online    │  ← Syncs ALL modified files
│ ─────────────────────────── │
│ New File...                 │
│ New Subfolder...            │
│ ─────────────────────────── │
│ Properties                  │
│ Delete                      │
└─────────────────────────────┘
```

---

### 7. File Status Indicators (In Explorer)

```
┌─────────────────────────────────────────────────────────────────┐
│  📁 PC / BDO_EN / Korean_Strings                    [Breadcrumb]│
├─────────────────────────────────────────────────────────────────┤
│  Name                    Size      Status           Modified    │
│  ─────────────────────────────────────────────────────────────  │
│  📄 quest_strings.xlsx   1.2 MB    ☁️ Online Only   2h ago      │
│  📄 item_names.xlsx      800 KB    💾 Offline       1h ago      │
│  📄 ui_text.txt          50 KB     🔄 Modified      5m ago      │
│  📄 new_file.xlsx        200 KB    ⬆️ Local Only    Just now    │
└─────────────────────────────────────────────────────────────────┘
```

**Status Icons:**

| Icon | Status | Meaning |
|------|--------|---------|
| ☁️ | Online Only | File exists on server, not downloaded locally |
| 💾 | Offline | File downloaded, synced with server |
| 🔄 | Modified | Local changes pending sync |
| ⬆️ | Local Only | New file, exists only locally |
| ⚠️ | Conflict | Server and local both changed |

---

### 8. Recycle Bin (Soft Delete with 30-Day Expiry)

**Deleted files go to Bin, not permanently deleted.**

```
┌─────────────────────────────────────────────────────────────────┐
│  🗑️ Recycle Bin                                                 │
├─────────────────────────────────────────────────────────────────┤
│  Name                    Deleted      Expires        Actions    │
│  ─────────────────────────────────────────────────────────────  │
│  📄 old_strings.xlsx     2 days ago   28 days left   [Restore]  │
│  📄 test_file.txt        15 days ago  15 days left   [Restore]  │
│  📁 Old_Folder/          29 days ago  1 day left     [Restore]  │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  [Empty Bin]                              [Restore All]         │
└─────────────────────────────────────────────────────────────────┘
```

**Bin Rules:**
| Rule | Description |
|------|-------------|
| **Soft Delete** | Right-click → Delete moves to Bin (not permanent) |
| **30-Day Expiry** | Files auto-deleted after 30 days in Bin |
| **Restore** | Click Restore to put file back in original location |
| **Permanent Delete** | Right-click in Bin → "Delete Permanently" or "Empty Bin" |
| **Bin Location** | Accessible from File Explorer sidebar or menu |

**Context Menu in Bin:**
```
┌─────────────────────────────┐
│ 📄 old_strings.xlsx         │
├─────────────────────────────┤
│ Restore                     │
│ Restore to...               │  ← Choose different location
│ ─────────────────────────── │
│ Delete Permanently          │  ← No undo!
└─────────────────────────────┘
```

---

### 9. TM Sync (Same as File Sync)

**TMs follow the same sync pattern as files.**

```
┌─────────────────────────────┐
│ 📚 BDO_Main_TM              │
├─────────────────────────────┤
│ Open                        │
│ ─────────────────────────── │
│ 📥 Download to Offline      │  ← Copy TM to local SQLite
│ 📤 Sync to Online           │  ← Push local TM changes
│ 🔄 Refresh from Online      │  ← Pull latest TM entries
│ ─────────────────────────── │
│ View Entries                │
│ Export...                   │
│ ─────────────────────────── │
│ Delete                      │  ← Goes to Bin
└─────────────────────────────┘
```

**Why TM Sync is Simpler:**

| Aspect | Files | TMs |
|--------|-------|-----|
| Local processing | Some | **All** (FAISS, embeddings) |
| Real-time collab | WebSocket sync | Not needed |
| Conflict risk | Higher | Lower (additive) |

**TM sync uses same last-write-wins rule as rows.** Latest entry wins by timestamp.

**TM Status Icons:**
| Icon | Status | Meaning |
|------|--------|---------|
| ☁️ | Online Only | TM on server, not downloaded |
| 💾 | Offline | TM downloaded, synced |
| 🔄 | Modified | Local TM entries pending sync |
| ⬆️ | Local Only | New TM, exists only locally |

---

## User Flows

### Flow 1: Download File for Offline Work

**Scenario:** User wants to work on a file during travel (no internet)

```
┌────────────────────────────────────────────────────────────────┐
│ STEP 1: User is ONLINE, browses File Explorer                  │
│         Sees file: quest_strings.xlsx (☁️ Online Only)         │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│ STEP 2: Right-click → "Download to Offline"                    │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│ STEP 3: System downloads:                                      │
│         - File data (all rows)                                 │
│         - Creates local path: PC/BDO_EN/Korean/quest.xlsx      │
│         - Copies associated TM entries (if any)                │
│         - Progress bar shown                                   │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│ STEP 4: File now shows: 💾 Offline                             │
│         User can work on it even without internet              │
└────────────────────────────────────────────────────────────────┘
```

---

### Flow 2: Work Offline and Sync Back

**Scenario:** User edited files offline, now back online

```
┌────────────────────────────────────────────────────────────────┐
│ STEP 1: User worked offline, made edits                        │
│         File shows: 🔄 Modified (47 edits pending)             │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│ STEP 2: User comes back online (mode changes to 🟢)            │
│         OR manually switches to Online mode                    │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│ STEP 3: Right-click file → "Sync to Online"                    │
│         OR click "Sync All" in Sync Status Panel               │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│ STEP 4: Sync Preview Dialog appears (see below)                │
│         Shows what will be added/edited                        │
│         User confirms                                          │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│ STEP 5: Merge executes:                                        │
│         - ADD: New rows appended                               │
│         - EDIT: Changed rows updated                           │
│         - NO DELETE: Nothing removed                           │
│         - Conflicts flagged for resolution                     │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│ STEP 6: Sync Complete                                          │
│         File shows: 💾 Offline (synced)                        │
│         OR shows conflicts to resolve                          │
└────────────────────────────────────────────────────────────────┘
```

---

### Flow 3: New Local File → Sync to Online (Path Selection)

**Scenario:** User created/uploaded a NEW file while offline, needs to place it in online structure

```
┌────────────────────────────────────────────────────────────────┐
│ STEP 1: User has new file (⬆️ Local Only)                      │
│         File: new_translations.xlsx                            │
│         No matching path exists online                         │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│ STEP 2: Right-click → "Sync to Online"                         │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│ STEP 3: System detects: No matching path online!               │
│         Opens FILE DIALOG for path selection                   │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Save to Online Location                                  [X]   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  📁 PC / BDO_EN / Korean_Strings                   [Breadcrumb] │
│  ─────────────────────────────────────────────────────────────  │
│  │ 📁 ..                                                      │ │
│  │ 📁 Quest_Text                                              │ │
│  │ 📁 Item_Names                                              │ │
│  │ 📁 UI_Strings           ← Double-click to enter            │ │
│  │ 📄 main_strings.xlsx                                       │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                 │
│  File name: [new_translations.xlsx___________________]          │
│                                                                 │
│  [New Folder]                          [Cancel]    [Save Here]  │
└─────────────────────────────────────────────────────────────────┘
```

**File Dialog Features:**
- Browse online folder structure
- Double-click folders to navigate
- Breadcrumb navigation
- Create new folder inline
- Type/edit filename
- Exactly like Windows "Save As" dialog

```
┌────────────────────────────────────────────────────────────────┐
│ STEP 4: User navigates to desired location                     │
│         Clicks [Save Here]                                     │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│ STEP 5: File uploaded to online at selected path               │
│         Local path updated to match                            │
│         File now: 💾 Offline (synced)                          │
└────────────────────────────────────────────────────────────────┘
```

---

### Flow 4: Download Folder (Bulk Download)

**Scenario:** User wants entire folder available offline

```
┌────────────────────────────────────────────────────────────────┐
│ STEP 1: Right-click folder → "Download Folder to Offline"      │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Download Folder                                          [X]   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  📁 Korean_Strings                                              │
│                                                                 │
│  This folder contains:                                          │
│  • 12 files (4.5 MB total)                                      │
│  • 3 subfolders                                                 │
│                                                                 │
│  ☑️ Include subfolders                                          │
│  ☑️ Include associated TMs                                      │
│                                                                 │
│  Estimated download: 5.2 MB                                     │
│                                                                 │
│  [Cancel]                                          [Download]   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Downloading...                                           [X]   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ████████████████████░░░░░░░░░░  67%                            │
│                                                                 │
│  Downloading: quest_strings.xlsx (8 of 12)                      │
│  Speed: 2.3 MB/s                                                │
│  Time remaining: ~5 seconds                                     │
│                                                                 │
│  [Cancel]                                                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## Sync Preview Dialog

Before any sync executes, user sees exactly what will happen:

```
┌─────────────────────────────────────────────────────────────────┐
│  Sync Preview: quest_strings.xlsx                         [X]   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  📊 Summary                                                     │
│  ─────────────────────────────────────────────────────────────  │
│  • Rows to ADD:    5 new translations                           │
│  • Rows to EDIT:   42 modified translations                     │
│  • Conflicts:      2 rows (need resolution)                     │
│  • Deletions:      0 (deletions not synced)                     │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  📝 Edits (42 rows)                               [Show Details]│
│                                                                 │
│  ➕ Additions (5 rows)                            [Show Details]│
│                                                                 │
│  ⚠️ Conflicts (2 rows)                            [Resolve Now] │
│  │ Row 102: Both local and server edited                      │ │
│  │ Row 450: Server marked as "Reviewed"                       │ │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  [Cancel]                    [Skip Conflicts]     [Sync Now]    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Conflict Resolution - AUTOMATIC (Last-Write-Wins)

**No UI needed!** Conflicts are auto-resolved by timestamp.

### How It Works

```python
# PostgreSQL model - auto-updates timestamp on ANY change:
updated_at = Column(DateTime, onupdate=datetime.utcnow)

# In offline.py merge_row():
if server_updated > local_updated:
    # Server wins - ALL fields (target, status, memo, etc.)
else:
    # Local wins - will push to server later
```

### What Gets Auto-Resolved

| Field | Behavior |
|-------|----------|
| Target text | Latest edit wins |
| Status (pending/confirmed/reviewed) | Latest change wins |
| Memo | Latest edit wins |
| Any other field | Latest change wins |

### Example: Confirmation Conflict

| Time | User A (Online) | User B (Offline) | Result |
|------|-----------------|------------------|--------|
| 10:00 | Confirms row 5 | - | Server: `updated_at=10:00` |
| 10:30 | - | Confirms row 5 | Local: `updated_at=10:30` |
| 11:00 | - | Syncs | **User B wins** (10:30 > 10:00) |

### Precision

- Timestamp: Second-level (`datetime.utcnow`)
- Same-second conflicts: Extremely rare, server wins by default

### Why No UI?

1. **Simple rule** - Latest write wins, period
2. **No ambiguity** - Clear winner every time
3. **Fast sync** - No user intervention needed
4. **Consistent** - Same rule for all field types

---

## Merge Rules (Technical)

### Rule 1: Path Matching

Files are matched by **full path**: `platform/project/folder/filename`

```
ONLINE PATH:  PC/BDO_EN/Korean/quest_strings.xlsx
LOCAL PATH:   PC/BDO_EN/Korean/quest_strings.xlsx
              ↓
              MATCH → Merge possible
```

```
ONLINE PATH:  (none)
LOCAL PATH:   Uncategorized/new_file.xlsx
              ↓
              NO MATCH → Auto-place in "Offline Storage" folder
```

### Path Conflict Auto-Resolution

**No UI needed!** Path conflicts are auto-resolved:

| Scenario | Result |
|----------|--------|
| Path still exists online | File syncs to that path ✅ |
| Path no longer exists online | File goes to "Offline Storage" |
| New file created offline | Goes to "Offline Storage" |

**Offline Storage** is a special folder (per-project or global) that holds orphaned files.
User can later move files from Offline Storage to proper location using Ctrl+X/Ctrl+V.

### Rule 2: Row Matching

Rows matched by **StringID + Source** (primary) or **row_num** (fallback)

```python
def find_matching_row(local_row, server_rows):
    # Primary: Match by StringID + Source
    if local_row.string_id:
        match = find_by_string_id_and_source(
            local_row.string_id,
            local_row.source,
            server_rows
        )
        if match:
            return match

    # Fallback: Match by row_num
    return find_by_row_num(local_row.row_num, server_rows)
```

### Rule 3: Merge Operations (ADD/EDIT Only)

| Local State | Server State | Operation |
|-------------|--------------|-----------|
| New row | Not exists | **ADD** to server |
| Modified row | Unchanged | **EDIT** on server |
| Modified row | Also modified | **CONFLICT** |
| Modified row | Marked "Reviewed" | **CONFLICT** (protected) |
| Deleted row | Exists | **NO ACTION** (delete not synced) |
| Unchanged | Modified | **PULL** server version |

### Rule 4: "Reviewed" Status is Sacred

```python
if server_row.status == 'reviewed' and local_row.is_modified:
    # NEVER auto-overwrite reviewed translations
    create_conflict(
        type='reviewed_lock',
        message='This row was reviewed. Manual resolution required.',
        options=['keep_server', 'request_re_review']
    )
```

### Rule 5: Timestamp Tracking

Every local change is timestamped:

```python
local_change = {
    'file_id': 123,
    'row_num': 45,
    'field': 'target',
    'old_value': 'original',
    'new_value': 'edited',
    'timestamp': '2026-01-02T10:30:00Z',  # When edit happened
    'sync_status': 'pending'
}
```

Server changes also have timestamps. **Most recent wins** (unless conflict).

---

## Feature Availability Matrix

### What Works Offline

| Feature | Offline | Online | Notes |
|---------|---------|--------|-------|
| View files | ✅ (if downloaded) | ✅ | |
| Edit cells | ✅ | ✅ | |
| Save changes | ✅ (to SQLite) | ✅ (to PostgreSQL) | |
| TM search (FAISS) | ✅ | ✅ | Local indexes |
| TM add entry | ✅ (local TM) | ✅ | |
| Pretranslation | ✅ | ✅ | Model2Vec/Qwen local |
| QA: Pattern check | ✅ | ✅ | Regex-based, local |
| QA: Character check | ✅ | ✅ | Rule-based, local |
| QA: Line check | ✅ | ✅ | Comparison-based, local |
| Color tag rendering | ✅ | ✅ | Frontend only |
| File upload | ✅ (to SQLite) | ✅ | |
| File conversion | ✅ | ✅ | Local Python |
| Create glossary | ✅ | ✅ | Local processing |
| Merge to LanguageData | ✅ | ✅ | Local processing |

### What Requires Online

| Feature | Offline | Online | Notes |
|---------|---------|--------|-------|
| **Grammar/Spelling** | ❌ | ✅ | LanguageTool server required |
| **Real-time collab** | ❌ | ✅ | WebSocket to server |
| **"Who's working"** | ❌ | ✅ | Presence requires server |
| **Cross-user TMs** | ❌ | ✅ | Other users' TMs on server |
| **Activity log (live)** | ❌ | ✅ | Server-side logging |
| **User management** | ❌ | ✅ | Admin features |

### Graceful Degradation

When user tries offline-unavailable feature:

```
┌─────────────────────────────────────────────────────────────────┐
│  ⚠️ Feature Unavailable Offline                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Grammar/Spelling check requires connection to                  │
│  the LanguageTool server.                                       │
│                                                                 │
│  [Switch to Online]                              [OK]           │
└─────────────────────────────────────────────────────────────────┘
```

---

## Database Schema

### SQLite (Local) - New Tables

```sql
-- Track which files are available offline
CREATE TABLE offline_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    online_file_id INTEGER,           -- ID in PostgreSQL
    platform TEXT,
    project TEXT,
    folder TEXT,
    filename TEXT,
    full_path TEXT UNIQUE,            -- platform/project/folder/filename
    downloaded_at DATETIME,
    last_synced_at DATETIME,
    sync_status TEXT DEFAULT 'synced', -- synced, modified, conflict
    UNIQUE(platform, project, folder, filename)
);

-- Track individual row changes for sync
CREATE TABLE local_changes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER REFERENCES offline_files(id),
    row_num INTEGER,
    string_id TEXT,
    field TEXT,                        -- 'source', 'target', 'status', etc.
    old_value TEXT,
    new_value TEXT,
    changed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    sync_status TEXT DEFAULT 'pending', -- pending, synced, conflict, resolved
    conflict_type TEXT,                 -- null, 'both_edited', 'reviewed_lock', 'deleted'
    resolution TEXT,                    -- null, 'keep_local', 'keep_server', 'merged'
    resolved_at DATETIME
);

-- Sync history log
CREATE TABLE sync_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sync_started_at DATETIME,
    sync_completed_at DATETIME,
    direction TEXT,                    -- 'to_online', 'from_online', 'bidirectional'
    files_synced INTEGER DEFAULT 0,
    rows_added INTEGER DEFAULT 0,
    rows_edited INTEGER DEFAULT 0,
    conflicts_found INTEGER DEFAULT 0,
    conflicts_resolved INTEGER DEFAULT 0,
    status TEXT,                       -- 'success', 'partial', 'failed', 'cancelled'
    error_message TEXT
);

-- Recycle Bin (soft delete)
CREATE TABLE recycle_bin (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_type TEXT NOT NULL,           -- 'file', 'folder', 'tm'
    original_id INTEGER,               -- Original ID in source table
    original_path TEXT,                -- Full path before deletion
    item_name TEXT,                    -- Name for display
    item_data TEXT,                    -- JSON blob of full item data
    deleted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME,               -- 30 days from deleted_at
    deleted_by INTEGER,                -- User who deleted
    UNIQUE(item_type, original_id)
);

-- Index for fast lookups
CREATE INDEX idx_local_changes_file ON local_changes(file_id);
CREATE INDEX idx_local_changes_status ON local_changes(sync_status);
CREATE INDEX idx_offline_files_path ON offline_files(full_path);
CREATE INDEX idx_recycle_bin_expires ON recycle_bin(expires_at);
```

### PostgreSQL (Server) - New Columns

```sql
-- Add to existing ldm_rows table
ALTER TABLE ldm_rows ADD COLUMN last_modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE ldm_rows ADD COLUMN last_modified_by INTEGER REFERENCES users(id);

-- Add to existing ldm_files table
ALTER TABLE ldm_files ADD COLUMN version INTEGER DEFAULT 1;
ALTER TABLE ldm_files ADD COLUMN last_sync_version INTEGER DEFAULT 1;
```

---

## API Endpoints

### Sync Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/sync/status` | GET | Check server connectivity |
| `/api/sync/file/{id}/download` | GET | Download file for offline |
| `/api/sync/file/{id}/diff` | POST | Get diff between local and server |
| `/api/sync/file/{id}/push` | POST | Push local changes to server |
| `/api/sync/file/{id}/pull` | GET | Pull server changes to local |
| `/api/sync/folder/{id}/download` | GET | Download entire folder |
| `/api/sync/resolve` | POST | Submit conflict resolutions |
| `/api/sync/history` | GET | Get sync history |

### Recycle Bin Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/bin` | GET | List all items in recycle bin |
| `/api/bin/{id}/restore` | POST | Restore item to original location |
| `/api/bin/{id}/restore-to` | POST | Restore item to new location |
| `/api/bin/{id}` | DELETE | Permanently delete item |
| `/api/bin/empty` | DELETE | Empty entire bin |
| `/api/bin/cleanup` | POST | Delete expired items (30+ days) |

### Endpoint Details

#### GET `/api/sync/status`

```json
{
    "status": "online",
    "server": "172.28.150.120",
    "latency_ms": 45,
    "last_check": "2026-01-02T10:30:00Z"
}
```

#### GET `/api/sync/file/{id}/download`

Downloads file data + creates local structure.

Response:
```json
{
    "file_id": 123,
    "path": {
        "platform": "PC",
        "project": "BDO_EN",
        "folder": "Korean_Strings",
        "filename": "quest_strings.xlsx"
    },
    "rows": [...],
    "row_count": 5000,
    "version": 15,
    "downloaded_at": "2026-01-02T10:30:00Z"
}
```

#### POST `/api/sync/file/{id}/diff`

Request:
```json
{
    "local_version": 12,
    "local_changes": [
        {"row_num": 45, "field": "target", "checksum": "abc123"},
        {"row_num": 102, "field": "target", "checksum": "def456"}
    ]
}
```

Response:
```json
{
    "server_version": 15,
    "can_fast_forward": false,
    "changes_to_pull": 3,
    "conflicts": [
        {
            "row_num": 102,
            "type": "both_edited",
            "server_value": "서버 번역",
            "server_modified_by": "Kim",
            "server_modified_at": "2026-01-02T08:00:00Z"
        }
    ]
}
```

#### POST `/api/sync/file/{id}/push`

Request:
```json
{
    "changes": [
        {
            "row_num": 45,
            "field": "target",
            "new_value": "새로운 번역",
            "changed_at": "2026-01-02T10:30:00Z"
        }
    ],
    "conflict_resolutions": [
        {
            "row_num": 102,
            "resolution": "keep_local",
            "merged_value": null
        }
    ],
    "new_rows": [
        {
            "string_id": "NEW_001",
            "source": "New text",
            "target": "새 텍스트"
        }
    ]
}
```

Response:
```json
{
    "success": true,
    "rows_added": 1,
    "rows_edited": 1,
    "conflicts_resolved": 1,
    "new_version": 16
}
```

---

## Implementation Phases

### Phase 1: Foundation (Week 1-2)

**Goal:** Basic offline file viewing and editing

| Task | Description | Files |
|------|-------------|-------|
| 1.1 | Create SQLite schema for offline | `server/database/offline_schema.sql` |
| 1.2 | Add mode indicator to UI | `+layout.svelte`, `stores/sync.js` |
| 1.3 | Implement mode toggle | `SyncStatusPanel.svelte` |
| 1.4 | Add "Download to Offline" context menu | `FileExplorer.svelte` |
| 1.5 | Implement file download API | `server/api/sync.py` |
| 1.6 | Store downloaded files in SQLite | `server/database/offline.py` |
| 1.7 | Switch data source based on mode | `LDM.svelte`, `VirtualGrid.svelte` |

**Deliverable:** Can download files and view/edit them offline

---

### Phase 2: Change Tracking (Week 3-4)

**Goal:** Track all local changes for later sync

| Task | Description | Files |
|------|-------------|-------|
| 2.1 | Create local_changes table | `offline_schema.sql` |
| 2.2 | Intercept all edit operations | `VirtualGrid.svelte` |
| 2.3 | Write changes to local_changes | `stores/offline.js` |
| 2.4 | Add file status indicators | `FileExplorer.svelte` |
| 2.5 | Show pending changes count | `SyncStatusPanel.svelte` |
| 2.6 | Add "Modified" badge to files | `FileExplorer.svelte` |

**Deliverable:** All local edits tracked with full history

---

### Phase 3: Sync Engine (Week 5-6)

**Goal:** Push local changes to server

| Task | Description | Files |
|------|-------------|-------|
| 3.1 | Implement diff algorithm | `server/sync/differ.py` |
| 3.2 | Implement merge logic | `server/sync/merger.py` |
| 3.3 | Create push API endpoint | `server/api/sync.py` |
| 3.4 | Add "Sync to Online" context menu | `FileExplorer.svelte` |
| 3.5 | Create Sync Preview dialog | `SyncPreviewDialog.svelte` |
| 3.6 | Execute sync with progress | `stores/sync.js` |

**Deliverable:** Can push local changes to server

---

### Phase 4: Conflict Resolution (Week 7-8)

**Goal:** Handle conflicts gracefully

| Task | Description | Files |
|------|-------------|-------|
| 4.1 | Detect conflicts during diff | `server/sync/differ.py` |
| 4.2 | Create conflict resolution dialog | `ConflictResolver.svelte` |
| 4.3 | Implement "Keep Local/Server" | `stores/sync.js` |
| 4.4 | Implement "Edit & Merge" | `ConflictResolver.svelte` |
| 4.5 | Handle "Reviewed" row protection | `server/sync/merger.py` |
| 4.6 | Bulk conflict resolution | `ConflictResolver.svelte` |

**Deliverable:** All conflict types handled with user choice

---

### Phase 5: File Dialog for New Files (Week 9)

**Goal:** Beautiful path selection for new files

| Task | Description | Files |
|------|-------------|-------|
| 5.1 | Create SyncFileDialog component | `SyncFileDialog.svelte` |
| 5.2 | Implement folder browsing | `SyncFileDialog.svelte` |
| 5.3 | Add breadcrumb navigation | `SyncFileDialog.svelte` |
| 5.4 | Implement "New Folder" inline | `SyncFileDialog.svelte` |
| 5.5 | Wire to sync flow | `FileExplorer.svelte` |

**Deliverable:** Windows-style "Save As" dialog for path selection

---

### Phase 6: Polish & Edge Cases (Week 10)

**Goal:** Robust, production-ready

| Task | Description | Files |
|------|-------------|-------|
| 6.1 | Handle partial sync (network drop) | `stores/sync.js` |
| 6.2 | Add sync history log | `SyncStatusPanel.svelte` |
| 6.3 | Graceful degradation for unavailable features | Various |
| 6.4 | Folder-level bulk sync | `FileExplorer.svelte` |
| 6.5 | TM sync (download TM for offline) | `TMExplorer.svelte` |
| 6.6 | Comprehensive testing | `tests/sync/` |

**Deliverable:** Production-ready offline/online mode

---

## Testing Checklist

### Unit Tests

- [ ] SQLite schema creates correctly
- [ ] Change tracking captures all edits
- [ ] Diff algorithm finds correct changes
- [ ] Merge logic applies ADD/EDIT correctly
- [ ] Conflict detection works for all types
- [ ] "Reviewed" protection enforced

### Integration Tests

- [ ] Download file creates correct local structure
- [ ] Edit offline → changes saved to SQLite
- [ ] Sync pushes changes to PostgreSQL
- [ ] Conflicts detected and shown to user
- [ ] Conflict resolution updates both DBs
- [ ] File Dialog creates correct path

### E2E Tests

- [ ] Full flow: Download → Edit offline → Sync back
- [ ] New file flow: Create → File Dialog → Sync
- [ ] Conflict flow: Both edit → Resolve → Sync
- [ ] Folder download: All files downloaded
- [ ] Mode toggle: Switch between online/offline
- [ ] Graceful degradation: Grammar check shows message

---

## Success Criteria

| Criterion | Measurement |
|-----------|-------------|
| **Offline editing works** | Can edit downloaded files with no network |
| **Sync is manual** | No automatic background sync ever |
| **Add/Edit only** | Deletions never synced |
| **Conflicts auto-resolved** | Last-write-wins, no UI needed |
| **Path auto-resolved** | Orphan files go to Offline Storage |
| **Mode visible** | User always knows online/offline status |
| **90% features offline** | Only LanguageTool + collab require server |
| **No data loss** | All local changes preserved until synced |

---

## File Naming Rules

### Duplicate Names - Per-Parent Unique (Like Windows/Linux)

Names can be duplicated at different depths:

```
✅ ALLOWED:
  Project1/Folder1/test.txt
  Project1/Folder2/test.txt   ← Same name, different parent = OK

❌ NOT ALLOWED:
  Project1/Folder1/test.txt
  Project1/Folder1/test.txt   ← Same name, same parent = Conflict
```

**DB Constraint:** `UniqueConstraint("parent_id", "name")` not `UniqueConstraint("name")`

### Auto-Rename Duplicates (XXX_1, XXX_2)

When creating or pasting a file with a duplicate name:

```
Original:   test.txt
Duplicate:  test_1.txt   ← Auto-renamed
Again:      test_2.txt   ← Increments
```

Same behavior as Windows Explorer - no user intervention needed.

---

## Future: Explorer File Operations

### Ctrl+C / Ctrl+V (Copy)
- Select file/folder → Ctrl+C → navigate → Ctrl+V
- Creates copy with auto-rename if duplicate name

### Ctrl+X / Ctrl+V (Cut/Move)
- Select file/folder → Ctrl+X → navigate → Ctrl+V
- Moves file to new location
- Source shows grayed out until paste completes
- Perfect for moving files from Offline Storage to proper location

### Clipboard State
- Clipboard persists while navigating explorer
- Clear on: new copy/cut, paste, or Esc

---

## Design Decisions (RESOLVED)

| Question | Decision | Rationale |
|----------|----------|-----------|
| **Auto-detect offline?** | ✅ **YES** - Auto-switch | Always online if possible, auto-fallback when server unreachable |
| **Sync reminder?** | ✅ **YES** - Toast + Info Bar | Toast on reconnect, info bar on files with pending changes |
| **TM sync?** | ✅ **Same as files** | Right-click → Download/Sync, identical UX |
| **Offline file expiry?** | ❌ **NO** - Keep forever | Files stay until user manually removes them |
| **Recycle Bin?** | ✅ **YES** - 30-day expiry | Soft delete → Bin → 30 days → permanent delete |

---

## Summary

```
┌─────────────────────────────────────────────────────────────────┐
│                    OFFLINE/ONLINE MODE                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  AUTO-CONNECT         MANUAL SYNC           RECYCLE BIN         │
│  ──────────────       ──────────────        ──────────────      │
│  Online if possible   Right-click files     30-day expiry       │
│  Auto-fallback        Add/Edit only         Restore anytime     │
│  Toast notifications  No deletions synced   Permanent delete    │
│                                                                 │
│  SYNC DASHBOARD       FILE STATUS           TM SYNC             │
│  ──────────────       ──────────────        ──────────────      │
│  Click indicator      ☁️💾🔄⬆️⚠️ icons      Same as files       │
│  Full overview        Info bar on file      Local processing    │
│  Sync All button      See pending changes   Mostly additive     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**10 weeks to production-ready Offline/Online mode.**

---

*Robust, elegant, automatic connection with manual sync. Beautiful UI/UX. No data loss.*
