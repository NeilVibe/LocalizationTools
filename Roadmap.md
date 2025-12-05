# LocaNext - Development Roadmap

**Version**: 2512052315 | **Updated**: 2025-12-05 | **Status**: ✅ Telemetry FULL STACK COMPLETE (P12.5.9)

---

## 🔥 Latest: Telemetry Architecture Validated (2025-12-05)

### ✅ Two-Port Simulation Test Results:
1. **Desktop (8888) → Central (9999)** - Cross-port communication WORKING
2. **Registration API** - `/api/v1/remote-logs/register` returns API key + installation ID
3. **Log Submission** - `/api/v1/remote-logs/submit` receives batch logs with auth
4. **Error Detection** - Central Server detects ERROR/CRITICAL in batches

### 🏗️ Production Architecture Validated:
```
┌─────────────────────┐        ┌─────────────────────┐        ┌─────────────────────┐
│  DESKTOP APP        │        │  CENTRAL SERVER     │        │  PATCH SERVER       │
│  (User's Machine)   │  HTTP  │  (Company Server)   │        │  (Future)           │
│                     │───────►│                     │        │                     │
│  Port: 8888 (local) │        │  Port: 9999 (test)  │        │  Build management   │
│  Backend + Frontend │        │  Telemetry receiver │        │  Update distribution│
│  SQLite local       │        │  PostgreSQL central │        │  No GitHub needed   │
└─────────────────────┘        └─────────────────────┘        └─────────────────────┘
        ▲                              ▲                              ▲
        │                              │                              │
   Independent                   Aggregated View                 FUTURE (P13)
   Fully Offline                 All Users Data
```

### 📋 This is a SIMULATION of Production:
- **Dev Testing**: Both servers run on localhost with different ports
- **Production Reality**: Desktop on user IP, Central on company server IP
- **Purpose**: Validate the communication protocol before real deployment

---

## 🔥 HOTFIX 2512051130 - Summary

### ✅ All Fixed:
1. **UI Rendering** - 24 buttons found, XLSTransfer container exists (verified via CDP)
2. **Button Clicks** - Work correctly, call backend API
3. **Backend** - XLSTransfer, QuickSearch, KRSimilar all load
4. **Auth/WebSocket** - Working
5. **Gradio Parasite** - Removed from requirements.txt and progress.py
6. **Python3 → Python.exe** - main.js uses `paths.pythonExe` for Windows
7. **DEV Auto-Login** - Enabled for testing
8. **XLSTransfer Uses API** - Refactored to use backend API instead of Python scripts
   - Load Dictionary ✅
   - Transfer to Close ✅
   - Get Sheets ✅
   - Process Operation ✅
9. **Binary file reading** - Added `readFileBuffer` IPC for Excel files

### ⚠️ Workarounds (NOT Real Fixes):
10. **SvelteKit 404** - `+error.svelte` catches 404 and renders content
    - Real fix: Hash-based routing or proper adapter-static config

### 📋 Not Implemented:
11. **Simple Excel Transfer** - Disabled (no API endpoint, use "Transfer to Excel" instead)

---

## 🗺️ MASTER NAVIGATION TREE (START HERE!)

```
Roadmap.md - FULL DOCUMENT GUIDE
═══════════════════════════════════════════════════════════════════════════
│
├── 📍 YOU ARE HERE ─────────────── Navigation Tree (this section)
│
├─────────────────────────────────────────────────────────────────────────
│   🔥 CURRENT STATUS (Read First)
├─────────────────────────────────────────────────────────────────────────
│   │
│   ├── 🔥 Latest ──────────────── Telemetry validated (2025-12-05)
│   ├── 🔥 Hotfix Summary ──────── 11 fixes, 1 workaround
│   ├── 🌳 STATUS TREE ─────────── Platform overview (QUAD ENTITY)
│   └── ⚡ QUICK COMMANDS ──────── Copy-paste ready
│
├─────────────────────────────────────────────────────────────────────────
│   🎯 PRIORITY SECTIONS (Detailed Documentation)
├─────────────────────────────────────────────────────────────────────────
│   │
│   ├── ✅ P6.0: Structure ─────── All tools under server/tools/
│   ├── ✅ P8.0: First-Run ─────── Setup UI on first launch
│   ├── ✅ P9.0: Auto-Update ───── GitHub releases + latest.yml
│   ├── ✅ P10.0: UI/UX ────────── Modal, Progress (10.3 = BACKLOG)
│   ├── ✅ P11.0: Health Check ─── Auto-repair system
│   ├── ✅ P12.0-12.5: Telemetry ─ Central Server (4 tables, 5 endpoints)
│   │       ├── ✅ 12.5.7: Desktop Client COMPLETE
│   │       ├── ✅ 12.5.8: Dashboard Telemetry Tab COMPLETE
│   │       └── ✅ 12.5.9: Tool Usage Tracking COMPLETE
│   │
│   └── 📋 P13.0: Gitea ────────── Self-hosted Git + CI/CD (FUTURE)
│           └── Full tree + checklist included
│
├─────────────────────────────────────────────────────────────────────────
│   🏗️ ARCHITECTURE & REFERENCE
├─────────────────────────────────────────────────────────────────────────
│   │
│   ├── 🔒 CI SAFETY CHECKS ────── 14 build verification checks
│   ├── 📦 COMPLETED FEATURES ──── Compact summary of all done
│   ├── 🏗️ QUAD ENTITY DIAGRAM ─── ASCII architecture (4 servers)
│   └── 🚀 FULL PRIORITY TREE ──── P1→P16 complete roadmap
│           ├── ✅ Completed: P1-P12.5.9
│           ├── 📋 Backlog: P10.3
│           ├── 📋 Next: P13.0 (Gitea)
│           └── 📋 Future: P14-P16
│
├─────────────────────────────────────────────────────────────────────────
│   📋 ARCHIVE (Historical Reference)
├─────────────────────────────────────────────────────────────────────────
│   │
│   └── 📋 P7.0: Archive ───────── Historical fixes (superseded)
│
└─────────────────────────────────────────────────────────────────────────
    🔑 KEY PRINCIPLES (Bottom of doc)
─────────────────────────────────────────────────────────────────────────

PORT SUMMARY (Quick Reference):
┌──────────────────┬────────┬─────────────────────────────┐
│ Entity           │ Port   │ Purpose                     │
├──────────────────┼────────┼─────────────────────────────┤
│ Desktop App      │ 8888   │ Local backend (per user)    │
│ Central Server   │ 9999   │ Telemetry (company server)  │
│ Admin Dashboard  │ 5175   │ Monitoring UI               │
│ Gitea Server     │ 3000   │ Git + CI/CD (FUTURE)        │
└──────────────────┴────────┴─────────────────────────────┘

WHAT'S NEXT? → P13.0: Gitea Patch Server (Self-hosted Git + CI/CD)
```

---

## 🌳 STATUS TREE

```
LocaNext Platform v2512051540 - QUAD ENTITY ARCHITECTURE
│
├── ✅ Backend (100%) ─────────── FastAPI, 47+ endpoints, async
├── ✅ Frontend (100%) ────────── SvelteKit + Carbon Design
├── ✅ Admin Dashboard (100%) ─── Stats, Users, Logs
├── ✅ Security (7/11) ────────── IP filter, CORS, JWT, audit
├── ✅ Tests (885) ───────────── TRUE simulation (no mocks!)
├── ✅ Structure (100%) ───────── All tools under server/tools/
├── ✅ Documentation (38+) ───── Fully organized tree structure
│
├── 📚 Documentation Tree
│   ├── docs/README.md ──────── Master index (all 38+ docs)
│   ├── docs/testing/DEBUG_AND_TEST_HUB.md ── Testing capabilities
│   ├── docs/architecture/README.md ──────── Architecture index
│   └── CLAUDE.md ───────────── Project hub for Claude AI
│
├── 🛠️ Apps (3 Complete)
│   ├── ✅ XLSTransfer ────────── Excel + Korean BERT AI
│   ├── ✅ QuickSearch ────────── Dictionary (15 langs, 4 games)
│   └── ✅ KR Similar ─────────── Korean semantic similarity
│
├── 📦 Distribution
│   ├── ✅ Electron Desktop ───── Windows .exe
│   ├── ✅ LIGHT Build ────────── ~200MB, deps on first-run
│   ├── ✅ Version Unified ────── 8 files synced
│   └── ✅ Auto-Update ────────── GitHub releases + Custom UI!
│
├── 🌐 QUAD ENTITY ARCHITECTURE ───── 4-Server Production System
│   │
│   ├── 📦 ENTITY 1: Desktop App (User's Machine)
│   │   ├── ✅ Electron + Svelte frontend
│   │   ├── ✅ FastAPI backend (port 8888)
│   │   ├── ✅ SQLite local database
│   │   ├── ✅ Fully independent/offline capable
│   │   └── 🔴 TODO: Telemetry client → Central Server
│   │
│   ├── 🖥️ ENTITY 2: Central Server (Company Server)
│   │   ├── ✅ Remote Logging API (tested!)
│   │   ├── ✅ Registration endpoint (API key + installation_id)
│   │   ├── ✅ Log submission endpoint (batch + error detection)
│   │   ├── ✅ Session tracking (start/heartbeat/end)
│   │   ├── ✅ 4 Database tables (Installation, RemoteSession, RemoteLog, TelemetrySummary)
│   │   ├── ✅ Config: CENTRAL_SERVER_URL + telemetry settings
│   │   ├── 📋 TODO: PostgreSQL (currently SQLite)
│   │   └── 📋 TODO: Dashboard UI for aggregated view
│   │
│   ├── 📊 ENTITY 3: Admin Dashboard (Company Server)
│   │   ├── ✅ Port 5175 (dev) / 80 (prod)
│   │   ├── ✅ User management, stats, logs
│   │   ├── 📋 TODO: Telemetry tab (view all installations)
│   │   └── 📋 TODO: Live session monitoring
│   │
│   └── 📡 ENTITY 4: Patch Server (FUTURE - P13)
│       ├── 📋 Replaces GitHub Actions for internal control
│       ├── 📋 Build/revision management
│       ├── 📋 Update distribution (no GitHub dependency)
│       │
│       └── 🏆 RECOMMENDED: Gitea (MIT License - Company Safe!)
│           ├── ✅ Self-hosted GitHub clone
│           ├── ✅ Single binary install (5 minutes)
│           ├── ✅ Built-in Gitea Actions (same YAML as GitHub!)
│           ├── ✅ Web UI: PRs, Issues, Wiki, Code Review
│           ├── ✅ ~100MB RAM (lightweight)
│           ├── ✅ MIT License = 100% free commercial use
│           │
│           ├── 📦 INSTALL:
│           │   wget https://dl.gitea.com/gitea/1.21/gitea-1.21-linux-amd64
│           │   chmod +x gitea && ./gitea web
│           │   # Open http://server:3000 → done!
│           │
│           └── 🔄 PIPELINE (.gitea/workflows/build.yml):
│               on: push → npm ci → npm run build:win → scp to update server
│
└── 🎯 Priorities
    ├── ✅ P6: Structure ───────── Unified server/tools/
    ├── ✅ P8: First-Run ──────── Setup UI on launch
    ├── ✅ P9: Auto-Update ────── COMPLETE! (latest.yml + GitHub)
    ├── ✅ P10.1-2,4-5: UI/UX ─── Modal, Progress, IPC done
    ├── 📋 P10.3: Patch Notes ─── BACKLOG (deferred)
    ├── ✅ P11: Health Check ──── Auto-repair system done
    ├── ✅ P12.5: Telemetry ──── SERVER-SIDE COMPLETE (4 tables, 5 endpoints)
    └── 📋 P13: Patch Server ─── Build/revision management (FAR FUTURE)
```

---

## 🔒 CI SAFETY CHECKS (14 Total)

```
Build Pipeline Safety Tree
│
├── 🔍 VERSION (2 checks)
│   ├── 1. Unification ✅ ────── All 8 files match
│   └── 2. Increment ✅ ──────── New > Latest release
│
├── 🧪 TESTS (2 checks)
│   ├── 3. Server Launch ✅ ──── Backend starts
│   └── 4. Python Tests ✅ ───── E2E + Unit pass
│
├── 🛡️ SECURITY (2 checks)
│   ├── 5. pip-audit ✅ ──────── Python vulns
│   └── 6. npm audit ✅ ──────── Node vulns
│
├── 🏗️ BUILD (4 checks)
│   ├── 7. Electron ✅ ───────── LocaNext.exe
│   ├── 8. Installer ✅ ──────── Inno Setup
│   ├── 9. latest.yml ✅ ─────── Auto-update manifest
│   └── 10. SHA512 ✅ ─────────── File integrity
│
├── 📦 POST-BUILD (4 checks)
│   ├── 11. Install ✅ ────────── Silent install works
│   ├── 12. Files ✅ ──────────── Critical files exist
│   ├── 13. Import ✅ ─────────── Python imports OK
│   └── 14. Health ✅ ─────────── /health responds
│
└── 🎁 RELEASE
    ├── Upload .exe
    └── Upload latest.yml
```

---

## ⚡ QUICK COMMANDS

```bash
# Start servers
python3 server/main.py              # Backend :8888
cd locaNext && npm run dev          # Frontend :5173

# Run tests
python3 -m pytest -v                # Quick tests
RUN_API_TESTS=1 python3 -m pytest   # Full tests (start server first!)

# Version check
python3 scripts/check_version_unified.py

# Trigger build
echo "Build LIGHT vXXXX" >> BUILD_TRIGGER.txt && git add -A && git commit -m "Trigger" && git push
```

---

## ✅ Priority 9.0: Auto-Update System (COMPLETE)

**Goal:** Users automatically get latest version on app launch.

### How It Works:

```
App Launch → Check GitHub Releases → Compare latest.yml → Download if newer → Install
```

### Checklist:

```
Priority 9.0: Auto-Update
├── 9.1 GitHub Publish ✅ ────── package.json configured
├── 9.2 latest.yml in CI ✅ ──── SHA512 hash generated
├── 9.3 Version Check ✅ ─────── Compare vs latest release
├── 9.4 Release Assets ✅ ────── .exe + latest.yml uploaded
└── 9.5 E2E Test 📋 ──────────── Verify update flow works
```

### Version System:

| File | Type | Example | Purpose |
|------|------|---------|---------|
| `version.py` | DateTime | 2512041724 | Release tags |
| `version.py` | Semantic | 1.0.0 | Auto-updater |
| `latest.yml` | Semantic | 1.0.0 | Update check |

---

## ✅ Priority 10.0: Auto-Update UI/UX (10.3 BACKLOG)

**Goal:** Beautiful, informative update experience with progress tracking and patch notes.

**Current (UGLY):** Basic system dialog with "Update Ready" message.
**Target (ELEGANT):** Custom modal with progress, patch notes, and smooth UX.

### UI Mockup:

```
┌─────────────────────────────────────────────────────────────┐
│  🎉 Update Available!                                    ✕  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  LocaNext v1.1.0 is ready to install                        │
│  (You have v1.0.0)                                          │
│                                                             │
│  📋 What's New:                                             │
│  • Auto-update system                                       │
│  • Performance improvements                                 │
│  • Bug fixes                                                │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ ████████████████░░░░░░░░░░  65%                      │  │
│  │ 45 MB / 70 MB · 2.3 MB/s · ~10s remaining            │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  [Cancel]                              [Restart & Update]   │
└─────────────────────────────────────────────────────────────┘
```

### Checklist:

```
Priority 10.0: Auto-Update UI/UX
├── 10.1 Update Notification Modal ✅
│   ├── Custom Svelte modal (UpdateModal.svelte)
│   ├── Version comparison (current → new)
│   ├── Version badge with "New" tag
│   └── Clean Carbon Design styling
│
├── 10.2 Download Progress UI ✅
│   ├── Progress bar with percentage
│   ├── Download speed (MB/s)
│   ├── Time remaining estimate
│   └── Bytes transferred / total
│
├── 10.3 Patch Notes System 🔄 IN PROGRESS
│   ├── 📋 Fetch release notes from GitHub API
│   ├── 📋 Display in UpdateModal
│   ├── 📋 Markdown rendering
│   └── 📋 "Read full changelog" link
│
├── 10.4 Update Ready State ✅
│   ├── Success notification
│   ├── "Restart Now" / "Later" buttons
│   └── Prevents close during download
│
└── 10.5 IPC Communication ✅
    ├── update-available → Show modal
    ├── update-progress → Update progress bar
    ├── update-downloaded → Show ready state
    └── update-error → Show error message
```

### Files Created/Modified:

| File | Status |
|------|--------|
| `locaNext/src/lib/components/UpdateModal.svelte` | ✅ Created: Custom update UI |
| `locaNext/src/routes/+layout.svelte` | ✅ Modified: Added UpdateModal |
| `locaNext/electron/main.js` | ✅ Modified: IPC handlers + no system dialog |
| `locaNext/electron/preload.js` | ✅ Modified: Expose electronUpdate API |

---

## ✅ Priority 11.0: Repair & Health Check System (COMPLETE)

**Problem:** If Python deps get corrupted/deleted after first-run, app crashes with no recovery option.

**Goal:** Robust self-healing system that detects and repairs broken installations.

### Current Gap:

```
CURRENT (Fragile):
┌─────────────────┐     ┌─────────────────┐
│ First Launch    │────►│ flag exists?    │
│                 │     │ YES → skip setup│
└─────────────────┘     │ NO → run setup  │
                        └─────────────────┘
                        ⚠️ If deps break later = CRASH!

PROPOSED (Robust):
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ Every Launch    │────►│ Health Check    │────►│ All OK?         │
│                 │     │ (quick verify)  │     │ YES → continue  │
└─────────────────┘     └─────────────────┘     │ NO → auto-repair│
                                                └─────────────────┘
```

### Checklist:

```
Priority 11.0: Repair & Health Check
│
├── 11.1 Startup Health Check ✅ DONE
│   ├── ✅ health-check.js module created
│   ├── ✅ Check critical Python imports (fastapi, torch, etc.)
│   ├── ✅ Check model files exist
│   ├── ✅ Check server files exist
│   └── ✅ Run on EVERY launch (integrated in main.js)
│
├── 11.2 Auto-Repair System ✅ DONE
│   ├── ✅ repair.js module created
│   ├── ✅ Detect which component is broken
│   ├── ✅ Show "Repairing..." UI (custom window)
│   ├── ✅ Re-run install_deps.py if packages missing
│   ├── ✅ Re-download model if model missing
│   └── ✅ Record repair attempts (prevent loops)
│
├── 11.3 Manual Repair Option ✅ DONE (backend)
│   ├── ✅ IPC handlers: run-health-check, run-repair
│   ├── ✅ Preload API: electronHealth.runRepair()
│   ├── 📋 Frontend Settings UI (pending)
│   └── 📋 Help menu integration (pending)
│
├── 11.4 Health Status in UI 📋
│   ├── Settings page shows component status
│   ├── Green/Red indicators for each component
│   ├── "Last verified: 2 min ago"
│   └── Backend health endpoint expansion
│
├── 11.5 Graceful Degradation 📋
│   ├── If Korean BERT missing → disable KR Similar only
│   ├── If one tool broken → others still work
│   ├── Clear error messages per tool
│   └── "Tool unavailable - click to repair"
│
├── 11.6 Logger Fix ✅ DONE
│   ├── ✅ Fixed ASAR path issue in logger.js
│   ├── ✅ Logs now write to install_dir/logs/ in production
│   └── ✅ Robust error handling (won't crash on write failure)
│
├── 11.7 Remote Debugging Breakthrough ✅ DONE
│   ├── ✅ Bulletproof logger using process.execPath (Node 18 compatible)
│   ├── ✅ Error dialog interceptor (captures MessageBox content before display)
│   ├── ✅ WSL can read Windows logs via /mnt/c/ path
│   ├── ✅ Fixed import.meta.dirname → fileURLToPath(import.meta.url)
│   └── ✅ See: docs/WINDOWS_TROUBLESHOOTING.md
│
├── 11.8 UI Polish & Firewall Fix ✅ DONE (v2512050104)
│   ├── ✅ Splash screen: overflow hidden (no floating scrollbar)
│   ├── ✅ Setup/Repair windows: no menu bar (setMenu(null))
│   ├── ✅ Setup/Repair windows: larger size (550x480/520)
│   ├── ✅ Server: bind to 127.0.0.1 (not 0.0.0.0 - avoids firewall popup)
│   └── ✅ Progress UI: uses executeJavaScript for inline HTML
│
└── 11.9 Black Screen Debug ✅ COMPLETE
    ├── ✅ ISSUE IDENTIFIED: Two root causes found via renderer logging
    │   ├── 1. preload.js used ES modules (import) but sandbox requires CommonJS
    │   └── 2. SvelteKit generated absolute paths (/_app/) → resolved to C:/_app/ on file://
    ├── ✅ FIX 1: Converted preload.js from ES modules to CommonJS (require)
    ├── ✅ FIX 2: Post-process build output: /_app/ → ./_app/ for relative paths
    ├── ✅ Added renderer logging (console-message, did-fail-load, dom-ready, preload-error)
    ├── ✅ Verified: Login page renders correctly, components mount
    └── 📚 See: docs/ELECTRON_TROUBLESHOOTING.md for debug protocol
```

### Files Created/Modified:

| File | Status | Purpose |
|------|--------|---------|
| `electron/health-check.js` | ✅ Created | Startup verification, Python import checks |
| `electron/repair.js` | ✅ Created | Auto-repair logic with UI window |
| `electron/logger.js` | ✅ Fixed | ASAR path issue, robust logging |
| `electron/main.js` | ✅ Modified | Health check + repair integration |
| `electron/preload.js` | ✅ Fixed | CommonJS (require) + electronHealth API |
| `src/lib/components/RepairModal.svelte` | 📋 Pending | Frontend repair UI |
| `src/routes/settings/+page.svelte` | 📋 Pending | Add repair button |

### User Experience:

**Scenario 1: Package deleted**
```
Launch → Health check fails → "Repairing..." UI → Fixed! → App loads
```

**Scenario 2: User wants manual repair**
```
Settings → "Repair Installation" → Confirm → Full repair runs → Done
```

**Scenario 3: One tool broken**
```
Launch → KR Similar broken → Other tools work → KR Similar shows "Repair needed"
```

---

## 🚨 Priority 12.0: Critical Architecture Issues (DISCOVERED 2025-12-05)

**Date Identified:** 2025-12-05 during Electron frontend testing
**Status Update:** 2025-12-05 - Issues 12.2, 12.3, 12.4 VERIFIED WORKING!
- ✅ Backend starts successfully with database tables
- ✅ Authentication works (admin/superadmin login verified)
- ✅ WebSocket connected
- ✅ Preload script loaded with appendLog
- ⚠️ SvelteKit 404 is cosmetic only - app continues working

### Critical Issues Found:

```
Priority 12.0: Critical Architecture Issues
│
├── 12.1 Central Authentication Architecture 🚨 CRITICAL
│   ├── Problem: Desktop apps have LOCAL databases (isolated)
│   ├── Current: Each app has its own SQLite with no users
│   ├── Expected: Admin Dashboard on server manages users centrally
│   ├── Desktop apps should authenticate against central server
│   └── Status: NEEDS ARCHITECTURE DESIGN
│
├── 12.2 Missing Preload API: appendLog ✅ FIXED
│   ├── Error: "window.electron.appendLog is not a function"
│   ├── Cause: Frontend calls appendLog but preload.js doesn't expose it
│   ├── Fix: Added appendLog to preload.js + IPC handler in main.js
│   └── Status: FIXED (2025-12-05)
│
├── 12.3 Database Initialization on Desktop ✅ FIXED
│   ├── Error: "sqlite3.OperationalError: no such table: users"
│   ├── Cause: Desktop app database not initialized with tables
│   ├── Fix: dependencies.py now calls init_db_tables() on startup
│   └── Status: FIXED (2025-12-05)
│
├── 12.4 SvelteKit Path Issues ⚠️ PARTIAL
│   ├── ✅ Fixed: Absolute paths (/_app/) → Relative (./_app/)
│   ├── ✅ Fixed: preload.js ES modules → CommonJS
│   ├── ✅ Created: scripts/fix-electron-paths.js (automated)
│   ├── 📚 Doc: docs/ELECTRON_TROUBLESHOOTING.md
│   ├── ⚠️ WORKAROUND: +error.svelte renders content on 404 (hides the problem)
│   └── 🔴 REAL FIX NEEDED: SvelteKit adapter-static config or hash-based routing
│
└── 12.5 Central Telemetry System ✅ CORE IMPLEMENTATION COMPLETE
    │
    ├── 🎯 Goal: Track user connections, session duration, tool usage
    │
    ├── 🧪 TWO-PORT SIMULATION TEST (2025-12-05) ✅ PASSED
    │   ├── Desktop (8888) → Central (9999) communication WORKING
    │   ├── Registration: API key + installation_id returned
    │   ├── Log Submission: 3 logs received, 1 ERROR detected
    │   ├── Session Tracking: 48s session, ended with user_closed
    │   └── Database: All 4 tables populated correctly
    │
    ├── ✅ COMPLETED IMPLEMENTATION TREE:
    │   │
    │   ├── 12.5.1 Database Tables ✅ DONE
    │   │   │   File: server/database/models.py
    │   │   │
    │   │   ├── Installation (Central Server registry)
    │   │   │   ├── installation_id (PK, String 22)
    │   │   │   ├── installation_name
    │   │   │   ├── api_key_hash (SHA256, 64 chars)
    │   │   │   ├── version, platform, os_version
    │   │   │   ├── created_at, last_seen
    │   │   │   ├── is_active (Boolean)
    │   │   │   └── extra_data (JSON)
    │   │   │
    │   │   ├── RemoteSession (Session tracking)
    │   │   │   ├── session_id (UUID PK)
    │   │   │   ├── installation_id (FK)
    │   │   │   ├── started_at, ended_at
    │   │   │   ├── duration_seconds
    │   │   │   ├── ip_address, user_agent
    │   │   │   └── end_reason (user_closed/timeout/error)
    │   │   │
    │   │   ├── RemoteLog (Log storage)
    │   │   │   ├── id (Auto PK)
    │   │   │   ├── installation_id (FK)
    │   │   │   ├── timestamp, level, message
    │   │   │   ├── source, component
    │   │   │   ├── data (JSON)
    │   │   │   └── received_at
    │   │   │
    │   │   └── TelemetrySummary (Daily aggregation)
    │   │       ├── id (Auto PK)
    │   │       ├── installation_id (FK)
    │   │       ├── date (Date)
    │   │       ├── total_sessions, total_duration_seconds
    │   │       ├── log_count, error_count, critical_count
    │   │       └── tools_used (JSON)
    │   │
    │   ├── 12.5.2 Central Server Config ✅ DONE
    │   │   │   File: server/config.py
    │   │   │
    │   │   ├── CENTRAL_SERVER_URL (env variable)
    │   │   ├── TELEMETRY_ENABLED (default: true)
    │   │   ├── TELEMETRY_HEARTBEAT_INTERVAL (300s = 5 min)
    │   │   ├── TELEMETRY_RETRY_INTERVAL (60s)
    │   │   └── TELEMETRY_MAX_QUEUE_SIZE (1000 logs)
    │   │
    │   ├── 12.5.3 Session Tracking API ✅ DONE
    │   │   │   File: server/api/remote_logging.py
    │   │   │
    │   │   ├── POST /api/v1/remote-logs/sessions/start
    │   │   │   ├── Creates RemoteSession record
    │   │   │   ├── Updates Installation.last_seen
    │   │   │   └── Returns session_id (UUID)
    │   │   │
    │   │   ├── POST /api/v1/remote-logs/sessions/heartbeat
    │   │   │   ├── Updates session last_seen
    │   │   │   └── Updates Installation.last_seen
    │   │   │
    │   │   └── POST /api/v1/remote-logs/sessions/end
    │   │       ├── Sets ended_at, duration_seconds
    │   │       ├── end_reason: user_closed/timeout/error
    │   │       └── Updates TelemetrySummary
    │   │
    │   ├── 12.5.4 Remote Logging API ✅ DONE
    │   │   │   File: server/api/remote_logging.py
    │   │   │
    │   │   ├── GET /api/v1/remote-logs/health
    │   │   │   └── Service health check
    │   │   │
    │   │   ├── POST /api/v1/remote-logs/register
    │   │   │   ├── Generates installation_id (URL-safe base64)
    │   │   │   ├── Generates api_key (48-byte token)
    │   │   │   ├── Stores SHA256 hash of api_key
    │   │   │   └── Returns: installation_id + api_key
    │   │   │
    │   │   ├── POST /api/v1/remote-logs/submit
    │   │   │   ├── Validates x-api-key header (lowercase!)
    │   │   │   ├── Stores batch of RemoteLog records
    │   │   │   ├── Detects ERROR/CRITICAL levels
    │   │   │   └── Updates TelemetrySummary counters
    │   │   │
    │   │   └── GET /api/v1/remote-logs/status/{installation_id}
    │   │       └── Returns installation info + stats
    │   │
    │   ├── 12.5.5 Database Exports ✅ DONE
    │   │   │   File: server/database/__init__.py
    │   │   │
    │   │   └── Exports: Installation, RemoteSession, RemoteLog, TelemetrySummary
    │   │
    │   └── 12.5.6 Two-Port Integration Test ✅ PASSED
    │       │
    │       ├── Test Setup:
    │       │   ├── Terminal 1: python3 server/main.py (8888)
    │       │   └── Terminal 2: SERVER_PORT=9999 python3 server/main.py (9999)
    │       │
    │       ├── Test Results (All PASSED):
    │       │   ├── ✅ /health - Service healthy
    │       │   ├── ✅ /register - installation_id + api_key returned
    │       │   ├── ✅ /sessions/start - session_id returned
    │       │   ├── ✅ /submit - 3 logs received, 1 error detected
    │       │   └── ✅ /sessions/end - 48s session recorded
    │       │
    │       └── Database Verification:
    │           ├── installations: 1 record
    │           ├── remote_sessions: 1 session (48s, user_closed)
    │           ├── remote_logs: 3 entries
    │           └── telemetry_summary: Daily aggregation
    │
    ├── 📋 PENDING (Future Enhancements):
    │   │
    │   ├── 12.5.7 Tool Usage Tracking (Desktop Client)
    │   │   ├── Hook into XLSTransfer operations
    │   │   ├── Hook into QuickSearch queries
    │   │   ├── Hook into KR Similar searches
    │   │   └── Track: duration, rows processed, errors
    │   │
    │   ├── 12.5.8 Admin Dashboard UI (Telemetry Tab)
    │   │   ├── Active installations list
    │   │   ├── Sessions timeline (who's online now)
    │   │   ├── Tool usage charts
    │   │   └── Error rate monitoring
    │   │
    │   └── 12.5.9 Desktop Telemetry Client
    │       ├── Auto-register on first launch
    │       ├── Session start/heartbeat/end lifecycle
    │       ├── Log submission with offline queue
    │       └── Uses CENTRAL_SERVER_URL from config
    │
    └── Status: ✅ SERVER-SIDE COMPLETE → 📋 CLIENT INTEGRATION NEXT
```

### Architecture Decision Needed:

```
CURRENT (Isolated):
┌─────────────────┐     ┌─────────────────┐
│ Admin Dashboard │     │ Desktop App     │
│ (Server)        │     │ (Local SQLite)  │
│ - Manages users │     │ - Own database  │
│ - Own database  │ ✗   │ - No sync       │
└─────────────────┘     └─────────────────┘
        No connection between them!

PROPOSED (Centralized Auth):
┌─────────────────┐         ┌─────────────────┐
│ Admin Dashboard │         │ Desktop App     │
│ (Central Server)│◄───────►│ (Local + Remote)│
│ - User mgmt     │  API    │ - Auth via API  │
│ - Access ctrl   │  calls  │ - Local cache   │
│ - PostgreSQL    │         │ - Telemetry     │
└─────────────────┘         └─────────────────┘
        Users managed centrally!
```

---

## ✅ Priority 8.0: First-Run Setup (COMPLETE)

**Problem:** Hidden .bat files during install = silent failures.
**Solution:** Visible setup UI on first app launch.

```
Priority 8.0: First-Run Setup ✅
├── 8.1 Remove .bat from installer ✅
├── 8.2 Create first-run-setup.js ✅
├── 8.3 Modify main.js ✅
├── 8.4 FirstTimeSetup UI ✅
├── 8.5 Auto-create folders ✅
├── 8.6 Verification ✅
├── 8.7 Progress output ✅
├── 8.9 CI post-build tests ✅
└── 8.10 Bug fixes ✅
```

**User Experience:**
- First launch: Progress UI → "Installing deps... 45%" → "Done!"
- Later launches: Instant (flag file exists)

---

## ✅ Priority 6.0: Structure Unification (COMPLETE)

**Problem:** Tools scattered across `client/` and `server/`.
**Solution:** Everything under `server/tools/`.

```
server/tools/           ← ALL tools here now
├── xlstransfer/        (moved from client/)
├── quicksearch/
└── kr_similar/
```

---

## 📦 COMPLETED FEATURES

### Platform Core ✅
- FastAPI backend (47+ endpoints, async)
- SvelteKit + Electron frontend
- Admin Dashboard (Overview, Users, Stats, Logs)
- SQLite (local) / PostgreSQL (server) - config switch
- WebSocket real-time progress
- JWT authentication

### Apps ✅
- **XLSTransfer** - AI translation with Korean BERT (447MB)
- **QuickSearch** - Multi-game dictionary (15 langs, 4 games)
- **KR Similar** - Korean semantic similarity

### Security (7/11) ✅
- IP Range Filter (24 tests)
- CORS Origins (11 tests)
- JWT Security (22 tests)
- Audit Logging (29 tests)
- Secrets Management
- Dependency Audits (CI/CD)
- Security Tests (86 total)

### Tests (885 total) ✅
- Unit: 538 | E2E: 115 | API Sim: 168 | Security: 86 | Frontend: 164

### Distribution ✅
- Git LFS, Version unification (8 files)
- LIGHT build (~200MB), GitHub Actions
- Inno Setup installer

---

## 📋 Priority 13.0: Gitea Patch Server (FUTURE)

**Goal:** Replace GitHub with self-hosted Gitea for full company control.

### 🌳 Git/Gitea Documentation Tree

```
SELF-HOSTED GIT INFRASTRUCTURE
│
├── 📚 DOCUMENTATION
│   └── docs/GITEA_SETUP.md ──────── Complete setup guide
│
├── 🔐 AUTHENTICATION
│   ├── SSH Keys (RECOMMENDED)
│   │   ├── Generate: ssh-keygen -t ed25519
│   │   ├── Add to Gitea: Settings → SSH Keys
│   │   └── Clone: git@server:user/repo.git
│   │
│   └── HTTPS + Token (Alternative)
│       ├── Generate: Gitea → Settings → Applications
│       └── Clone: https://server/user/repo.git
│
├── 🖥️ GITEA SERVER
│   ├── Install: Single binary (5 min)
│   │   wget https://dl.gitea.com/gitea/1.21/gitea-1.21-linux-amd64
│   │   chmod +x gitea && ./gitea web
│   │
│   ├── Production: Systemd service or Docker
│   ├── Port 3000: Web UI
│   ├── Port 22/2222: SSH
│   └── License: MIT (100% company safe)
│
├── 🔄 CI/CD PIPELINE (Gitea Actions)
│   ├── Same YAML as GitHub Actions!
│   ├── .gitea/workflows/build.yml
│   │
│   ├── LocaNext Pipeline:
│   │   on: push
│   │   jobs:
│   │     test: pytest
│   │     build: npm run build:win
│   │     deploy: scp to update server
│   │
│   └── Self-Hosted Runner (for Windows builds)
│
├── 📦 UPDATE DISTRIBUTION
│   ├── /var/www/updates/
│   │   ├── latest.yml
│   │   └── LocaNext-Setup-x.x.x.exe
│   │
│   └── Desktop app checks: https://update-server/updates/latest.yml
│
└── 🔒 SECURITY
    ├── SSH keys only (no passwords)
    ├── Internal network only (no public access)
    ├── Regular backups
    └── Two-factor auth enabled
```

### Implementation Checklist

```
P13 TASKS:
│
├── 📋 13.1: Server Setup
│   ├── [ ] Install Gitea on company server
│   ├── [ ] Configure SSH
│   ├── [ ] Create admin account
│   └── [ ] Add developer SSH keys
│
├── 📋 13.2: Repository Migration
│   ├── [ ] Clone from GitHub
│   ├── [ ] Push to Gitea
│   ├── [ ] Update developer remotes
│   └── [ ] Test push/pull workflow
│
├── 📋 13.3: CI/CD Setup
│   ├── [ ] Enable Gitea Actions
│   ├── [ ] Create build.yml workflow
│   ├── [ ] Setup Windows runner
│   └── [ ] Test full pipeline
│
├── 📋 13.4: Update Server
│   ├── [ ] Setup nginx for /updates/
│   ├── [ ] Configure autoUpdater URL
│   ├── [ ] Test update flow
│   └── [ ] Remove GitHub dependency
│
└── 📋 13.5: Documentation
    ├── [x] GITEA_SETUP.md created
    ├── [ ] Developer onboarding guide
    └── [ ] Backup/restore procedures
```

---

## 🏗️ QUAD ENTITY ARCHITECTURE

```
                            PRODUCTION DEPLOYMENT (4 ENTITIES)
═══════════════════════════════════════════════════════════════════════════════════

┌─────────────────────────────┐         ┌─────────────────────────────┐
│  ENTITY 1: DESKTOP APP      │         │  ENTITY 2: CENTRAL SERVER   │
│  (Each User's Machine)      │         │  (Telemetry Receiver)       │
│                             │         │                             │
│  ┌─────────┐  ┌───────────┐ │  HTTP   │  Port 9999                  │
│  │ Svelte  │◄►│ FastAPI   │ │────────►│  • /api/v1/remote-logs/*    │
│  │   UI    │  │  Backend  │ │         │  • Registration             │
│  └─────────┘  └───────────┘ │         │  • Log submission           │
│                             │         │  • Session tracking         │
│  Port 8888 (local)          │         │  • PostgreSQL database      │
│  SQLite + Korean BERT       │         └─────────────────────────────┘
│  Works fully offline!       │                      │
└─────────────────────────────┘                      │ Shared DB
         │                                           ▼
         │ Check for                   ┌─────────────────────────────┐
         │ updates                     │  ENTITY 3: ADMIN DASHBOARD  │
         │                             │  (Monitoring UI)            │
         ▼                             │                             │
┌─────────────────────────────┐        │  Port 5175 (dev) / 80 (prod)│
│  ENTITY 4: GITEA SERVER     │        │  • View all installations   │
│  (Patch Server - P13)       │        │  • Live session monitoring  │
│                             │        │  • Tool usage stats         │
│  Port 3000: Web UI          │        │  • Error alerts             │
│  Port 22: SSH               │        └─────────────────────────────┘
│                             │
│  ┌─────────────────────┐    │
│  │  Git Repository     │    │     DEVELOPER WORKFLOW:
│  │  • LocaNext code    │◄───┼──── git push origin main
│  └─────────────────────┘    │            │
│           │                 │            ▼
│           ▼                 │     ┌──────────────┐
│  ┌─────────────────────┐    │     │ Gitea Actions│
│  │  Gitea Actions      │    │     │ (CI/CD)      │
│  │  • Test             │    │     └──────────────┘
│  │  • Build Windows    │    │            │
│  │  • Deploy update    │────┼────────────┘
│  └─────────────────────┘    │
│           │                 │
│           ▼                 │
│  ┌─────────────────────┐    │
│  │  /var/www/updates/  │    │
│  │  • latest.yml       │◄───┼──── Desktop apps check here
│  │  • LocaNext-x.x.exe │    │
│  └─────────────────────┘    │
│                             │
│  License: MIT (FREE!)       │
│  No GitHub dependency!      │
└─────────────────────────────┘

═══════════════════════════════════════════════════════════════════════════
                          DEVELOPMENT SIMULATION
═══════════════════════════════════════════════════════════════════════════

For testing cross-entity communication on localhost:

  Desktop (Port 8888)  ───HTTP───►  Central (Port 9999)
       │                                   │
       └──── Both run on same machine ─────┘
             Different ports simulate
             different IP addresses

Test Command:
  Terminal 1: python3 server/main.py                    # Desktop on 8888
  Terminal 2: SERVER_PORT=9999 python3 server/main.py   # Central on 9999

  Then test: curl -X POST http://localhost:9999/api/v1/remote-logs/register ...
```

---

## 📋 ARCHIVE: Priority 7.0

Historical fixes superseded by Priority 8.0:
- version.py missing → Fixed in Inno Setup
- PyJWT/bcrypt missing → Moved to first-run
- .bat file issues → Deleted, replaced with first-run UI

---

## 🔑 KEY PRINCIPLES

```
1. Backend is Flawless ─── Don't modify core without confirmed bug
2. LIGHT-First Builds ─── No bundled models
3. TRUE Simulation ─────── No mocks, real functions
4. Version Unification ─── 8 files must match
5. Unified Structure ───── All tools in server/tools/
```

---

---

## 🚀 FULL PRIORITY ROADMAP

```
COMPLETE PRIORITY TREE (Past → Present → Future)
│
├── ✅ COMPLETED
│   │
│   ├── P1-5: Core Platform ──────── Backend, Frontend, Database, WebSocket
│   ├── P6.0: Structure ──────────── All tools unified under server/tools/
│   ├── P7.0: Hotfixes ───────────── Historical fixes (archived)
│   ├── P8.0: First-Run Setup ────── Python deps install on first launch
│   ├── P9.0: Auto-Update ────────── GitHub releases + latest.yml
│   ├── P10.1-2,4-5: UI/UX ───────── Modal, Progress, IPC
│   ├── P11.0: Health Check ──────── Auto-repair system
│   └── P12.5: Telemetry ─────────── Central Server (4 tables, 5 endpoints)
│
├── 📋 BACKLOG (Deferred)
│   │
│   └── P10.3: Patch Notes ───────── Show release notes in update modal
│
├── ✅ JUST COMPLETED
│   │
│   └── P12.5.7: Desktop Telemetry Client ✅ DONE
│       ├── ✅ Auto-register on first launch
│       ├── ✅ Session start/heartbeat/end
│       ├── ✅ Log queue with offline support
│       └── ✅ Frontend API (electronTelemetry)
│
├── ✅ JUST COMPLETED
│   │
│   └── P12.5.8: Admin Dashboard Telemetry Tab ✅ DONE
│       ├── ✅ Admin telemetry endpoints (/api/v2/admin/telemetry/*)
│       ├── ✅ Telemetry page with tabs (Overview, Installations, Sessions, Errors)
│       ├── ✅ Auto-refresh + real-time data
│       └── ✅ Navigation in sidebar
│
├── ✅ COMPLETE (Dec 2025)
│   │
│   └── P12.5.9: Tool Usage Tracking ✅
│       ├── ✅ Hook XLSTransfer operations
│       ├── ✅ Hook QuickSearch queries
│       ├── ✅ Hook KRSimilar operations
│       └── ✅ Duration, rows, errors tracked via telemetry.js
│
└── 📋 NEXT (P13+)
    │
    ├── P13.0: Gitea Patch Server ────────── Self-hosted Git + CI/CD
    │   ├── 13.1: Gitea installation
    │   ├── 13.2: Repository migration
    │   ├── 13.3: CI/CD pipeline
    │   ├── 13.4: Update server
    │   └── 13.5: Documentation
    │
    ├── P14.0: New Tools ─────────────────── Expand platform
    │   ├── GlossarySniffer
    │   ├── WordCountMaster
    │   ├── ExcelRegex
    │   └── TFM (Translation File Manager)
    │
    ├── P15.0: Performance ───────────────── Optimization
    │   ├── Redis caching
    │   ├── Lazy loading
    │   └── Bundle size reduction
    │
    └── P16.0: Enterprise Features ───────── Scale up
        ├── Multi-tenant
        ├── Role-based access
        └── Audit trails
```

### Port Summary (Quad Entity)

| Entity | Port | Purpose |
|--------|------|---------|
| Desktop App | 8888 | Local backend (per user) |
| Central Telemetry | 9999 | Log collection (company server) |
| Admin Dashboard | 5175/80 | Monitoring UI (company server) |
| Gitea Server | 3000 + 22 | Git + CI/CD (company server) |

---

*Login: admin / admin123 | Ports: Backend 8888 | Frontend 5173 | Admin 5175 | Central 9999 | Gitea 3000*
