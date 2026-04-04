# LAUNCHER + Offline/Online Mode Plan

> **Status:** PLANNING | **Created:** 2026-01-04

---

## The Vision

**The Launcher REPLACES the login page.** It's the beautiful first impression with built-in updates.

### Normal State (No Update)

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│                    ╭──────────────────╮                         │
│                    │    [LocaNext]    │                         │
│                    │      LOGO        │                         │
│                    ╰──────────────────╯                         │
│                                                                 │
│              ┌─────────────────────────────────┐                │
│              │  ●  Central Server Connected    │                │
│              └─────────────────────────────────┘                │
│                                                                 │
│                   ╭───────────────────────╮                     │
│                   │    Start Offline      │                     │
│                   ╰───────────────────────╯                     │
│                                                                 │
│                   ╭───────────────────────╮                     │
│                   │        Login          │                     │
│                   ╰───────────────────────╯                     │
│                                                                 │
│                         v26.104.1600                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Update In Progress State (Industry Giant Style!)

Like League of Legends, Battle.net, Steam, Epic Games - **BIG progress bar at bottom with ALL details:**

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│                    ╭──────────────────╮                         │
│                    │    [LocaNext]    │                         │
│                    │      LOGO        │                         │
│                    ╰──────────────────╯                         │
│                                                                 │
│                   ╭───────────────────────╮                     │
│                   │    Start Offline      │  ← Still usable!   │
│                   ╰───────────────────────╯                     │
│                                                                 │
│                   ╭───────────────────────╮                     │
│                   │        Login          │                     │
│                   ╰───────────────────────╯                     │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  ⚡ UPDATING TO v26.105.1200                                    │
│                                                                 │
│  ████████████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  68%     │
│                                                                 │
│  📦 Downloading: app.asar                          12.3 / 18 MB │
│  ⚡ Speed: 2.1 MB/s                             ~3 sec remaining │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ ✓ manifest.json                                    verified ││
│  │ ● app.asar                                      downloading ││
│  │ ○ component-state.json                             pending  ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│  Total: 18.2 MB  •  Files: 2/3  •  Saved: 606 MB (97% smaller!) │
└─────────────────────────────────────────────────────────────────┘
```

### Details Panel Shows:

| Element | Description |
|---------|-------------|
| **Version Badge** | "UPDATING TO v26.105.1200" |
| **Main Progress Bar** | Big, colorful, animated |
| **Current File** | "Downloading: app.asar" |
| **Size Progress** | "12.3 / 18 MB" |
| **Speed** | "2.1 MB/s" |
| **Time Remaining** | "~3 sec remaining" |
| **File List** | ✓ done, ● current, ○ pending |
| **Summary Footer** | Total size, file count, savings % |

### Update Complete State

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│                    ╭──────────────────╮                         │
│                    │    [LocaNext]    │                         │
│                    │      LOGO        │                         │
│                    ╰──────────────────╯                         │
│                                                                 │
│              ┌─────────────────────────────────┐                │
│              │  ✓ Updated to v26.105!          │                │
│              │    Only 18 MB (97% smaller!)    │                │
│              └─────────────────────────────────┘                │
│                                                                 │
│                   ╭───────────────────────╮                     │
│                   │    Start Offline      │                     │
│                   ╰───────────────────────╯                     │
│                                                                 │
│                   ╭───────────────────────╮                     │
│                   │        Login          │                     │
│                   ╰───────────────────────╯                     │
│                                                                 │
│                         v26.105.xxxx                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Server Offline State

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│                    ╭──────────────────╮                         │
│                    │    [LocaNext]    │                         │
│                    │      LOGO        │                         │
│                    ╰──────────────────╯                         │
│                                                                 │
│              ┌─────────────────────────────────┐                │
│              │  ○  Central Server Offline      │                │
│              │     Working in offline mode     │                │
│              └─────────────────────────────────┘                │
│                                                                 │
│                   ╭───────────────────────────╮                 │
│                   │    Start Offline          │  ← Only option  │
│                   ╰───────────────────────────╯                 │
│                                                                 │
│                   ╭───────────────────────────╮                 │
│                   │        Login              │  ← Disabled     │
│                   ╰───────────────────────────╯                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## KEY: Launcher REPLACES Login Page

The current `Login.svelte` page becomes the `Launcher.svelte`:

| Current | New |
|---------|-----|
| Login page shows after app loads | Launcher shows FIRST |
| UpdateModal is separate popup | Updates built into launcher |
| No offline option | [Start Offline] button |
| Must have credentials | Work without login |

---

## Core Concept

| Mode | Credentials | Database | Updates | Use Case |
|------|-------------|----------|---------|----------|
| **Offline** | None needed | Local SQLite | Yes (if server reachable) | Quick start, no account, single-user |
| **Online** | Required | Central PostgreSQL | Yes | Multi-user, sync, full features |

**Key Insight:** Updates don't require authentication! Central server can serve updates to anyone.

---

## User Flows

### Flow 1: Start Offline (No Credentials)

```
User opens app
    ↓
┌─────────────────────┐
│ LAUNCHER            │
│ • Check updates     │ ← Can update even without login!
│ • Show status       │
└─────────────────────┘
    ↓
User clicks [Start Offline]
    ↓
┌─────────────────────┐
│ MAIN APP            │
│ • Local SQLite      │
│ • Single-user mode  │
│ • All tools work    │
└─────────────────────┘
    ↓
User wants online features
    ↓
┌─────────────────────┐
│ LOGIN MODAL POPS    │ ← Auto-appears when online feature needed
│ • Enter credentials │
│ • [x] Remember me   │
└─────────────────────┘
    ↓
Now in Online mode (seamless transition)
```

### Flow 2: Login Directly

```
User opens app
    ↓
┌─────────────────────┐
│ LAUNCHER            │
│ • Check updates     │
│ • Download patches  │
└─────────────────────┘
    ↓
User clicks [Login]
    ↓
┌─────────────────────┐
│ LOGIN FORM          │
│ • Username          │
│ • Password          │
│ • [x] Remember me   │
└─────────────────────┘
    ↓
┌─────────────────────┐
│ MAIN APP            │
│ • Central PostgreSQL│
│ • Multi-user sync   │
│ • Full features     │
└─────────────────────┘
```

### Flow 3: Offline → Online Transition

```
User is in Offline mode
    ↓
Clicks feature that needs online (e.g., shared TM)
    ↓
┌─────────────────────────────────────┐
│ CONNECT ONLINE                      │
│                                     │
│ This feature requires online mode.  │
│                                     │
│ Username: [____________]            │
│ Password: [____________]            │
│ [x] Remember credentials            │
│                                     │
│ [Cancel]              [Connect]     │
└─────────────────────────────────────┘
    ↓
Credentials validated → Switch to Online mode
    ↓
Feature now works, data syncs to central server
```

### Flow 4: No Internet, Has Cached Credentials

```
User opens app (no internet)
    ↓
┌─────────────────────┐
│ LAUNCHER            │
│ • Server: Offline   │
│ • Can't check for   │
│   updates           │
└─────────────────────┘
    ↓
[Start Offline] ← Only option available
    ↓
App works with local data
```

---

## Architecture

### Launcher Component

```
locaNext/
├── electron/
│   ├── launcher.html      ← Launcher window (small, beautiful)
│   ├── launcher-preload.js
│   └── main.js            ← Creates launcher window first
└── src/
    └── lib/
        └── components/
            └── Launcher.svelte  ← Launcher UI
```

### Launcher Responsibilities

1. **Check Central Server Status**
   - Ping server health endpoint (no auth needed)
   - Show: "Connected ●" or "Offline ○"

2. **Check for Updates**
   - Fetch manifest.json (no auth needed)
   - Download patches if available
   - Show progress bar

3. **Present Options**
   - [Start Offline] - Always available
   - [Login] - Available if server connected

4. **Handle Credentials**
   - Store in secure storage (electron-store encrypted)
   - Auto-fill if remembered
   - Validate before launching main app

### Mode Manager

```javascript
// stores/mode.js
export const appMode = writable('offline'); // 'offline' | 'online'
export const serverStatus = writable('unknown'); // 'connected' | 'offline' | 'unknown'

// When mode changes from offline to online:
// 1. Validate credentials
// 2. Connect to PostgreSQL
// 3. Sync local changes to server
// 4. Switch database adapter
```

### Database Switching

```
OFFLINE MODE                    ONLINE MODE
├── SQLite (local)              ├── PostgreSQL (central)
├── /appdata/locanext.db        ├── <GITEA_HOST>:5432
├── Single-user                 ├── Multi-user
└── No sync                     └── WebSocket sync
```

---

## UI Components

### 1. Launcher Window

- Small window (400x500px)
- Beautiful gradient background
- LocaNext logo
- Update progress bar
- Status indicators
- Two main buttons

### 2. Online/Offline Toggle (Main App)

```
┌──────────────────────────────────────┐
│ Header                    [○ Offline]│  ← Click to switch
└──────────────────────────────────────┘
```

When clicked in Offline mode → Login modal appears

### 3. Login Modal (In-App)

- Appears when:
  - User clicks [Login] in launcher
  - User tries online feature while offline
  - User clicks Online toggle
- Fields: Username, Password, Remember me
- Shows server status

---

## What Works in Each Mode

| Feature | Offline | Online |
|---------|---------|--------|
| XLSTransfer | ✅ | ✅ |
| QuickSearch | ✅ | ✅ |
| KR Similar | ✅ | ✅ |
| LDM (local files) | ✅ | ✅ |
| LDM (shared projects) | ❌ | ✅ |
| Translation Memory (local) | ✅ | ✅ |
| Translation Memory (shared) | ❌ | ✅ |
| Qwen AI | ✅ | ✅ |
| User Management | ❌ | ✅ |
| Activity Logging | Local | Central |
| Real-time Sync | ❌ | ✅ |

---

## Implementation Phases

### Phase 1: Launcher Window
- Create launcher.html and Launcher.svelte
- Server status check (no auth)
- Update check and download
- [Start Offline] and [Login] buttons

### Phase 2: Offline Mode Foundation
- SQLite database setup
- Local-only user (no auth needed)
- All tools work locally

### Phase 3: Mode Switching
- Online/Offline toggle in main app
- Login modal component
- Credential storage (secure)

### Phase 4: Database Adapter
- Abstract database layer
- SQLite adapter for offline
- PostgreSQL adapter for online
- Seamless switching

### Phase 5: Sync Engine
- Queue local changes when offline
- Sync to server when going online
- Conflict resolution

---

## Key Benefits

1. **Instant Start** - No login needed for offline work
2. **Always Updated** - Patches download before app starts
3. **Seamless Transition** - Switch modes without restarting
4. **Works Anywhere** - No internet? No problem.
5. **Beautiful UX** - Launcher-style professional feel

---

## Questions to Decide

1. **Launcher size?** Minimal (400x500) or larger with more info?
2. **Auto-login?** If credentials saved, skip launcher and go straight to app?
3. **Sync conflict resolution?** Last-write-wins or manual merge?
4. **Offline user identity?** Anonymous or local username?

---

*Plan created: 2026-01-04*
