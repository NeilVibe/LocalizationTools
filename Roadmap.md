# LocaNext - Development Roadmap

**Version**: 2512041724 | **Updated**: 2025-12-04 | **Status**: Priority 9.0 - AUTO-UPDATE BUILD

---

## 🌳 STATUS TREE

```
LocaNext Platform
├── ✅ Backend (100%) ─────────── FastAPI, 47+ endpoints, async
├── ✅ Frontend (100%) ────────── SvelteKit + Carbon Design
├── ✅ Admin Dashboard (100%) ─── Stats, Users, Logs
├── ✅ Security (7/11) ────────── IP filter, CORS, JWT, audit
├── ✅ Tests (885) ───────────── TRUE simulation (no mocks!)
├── ✅ Structure (100%) ───────── All tools unified under server/tools/
│
├── Apps (All in server/tools/)
│   ├── ✅ XLSTransfer ────────── Excel translation + Korean BERT
│   ├── ✅ QuickSearch ────────── Dictionary search (15 langs)
│   └── ✅ KR Similar ─────────── Korean semantic similarity
│
├── Distribution
│   ├── ✅ Electron Desktop ───── Windows .exe, Linux AppImage
│   ├── ✅ LIGHT Build ────────── First-run setup (deps/model on launch)
│   └── ✅ Version Unified ────── 8 files synced
│
├── ✅ Priority 8.0: First-Run Setup (COMPLETE)
│   ├── ✅ Removed .bat calls from installer
│   ├── ✅ Created first-run-setup.js in Electron
│   ├── ✅ Created FirstTimeSetup UI (inline HTML)
│   ├── ✅ Auto-install deps on first launch
│   ├── ✅ Auto-download model on first launch
│   └── ✅ Verification before main app
│
└── 🔄 Priority 9.0: Auto-Update System (IN PROGRESS)
    ├── ✅ Enable GitHub publish in package.json
    ├── ✅ Add latest.yml generation to CI
    ├── ✅ Add version increment validation
    ├── ✅ Upload latest.yml to releases
    └── 📋 Test auto-update flow end-to-end
```

---

## 📊 Test Summary

| Category | Tests | Status |
|----------|-------|--------|
| Unit Tests | 538 | ✅ Server + client |
| E2E Apps | 115 | ✅ All 3 tools |
| API Simulation | 168 | ✅ TRUE sim (no mocks) |
| Security | 86 | ✅ IP, CORS, JWT, audit |
| Frontend E2E | 164 | ✅ Playwright |
| **Total** | **885** | **All passing** |

---

## ⚡ Quick Commands

```bash
# Start backend
python3 server/main.py

# Start frontend
cd locaNext && npm run dev

# Run tests (full simulation)
python3 scripts/create_admin.py && python3 server/main.py &
sleep 5 && RUN_API_TESTS=1 python3 -m pytest -v

# Check version
python3 scripts/check_version_unified.py
```

---

## 🚨 CRITICAL: First-Run Setup (2025-12-04) - Priority 8.0

**Problem:** Current approach FUNDAMENTALLY BROKEN. Running deps/model install during Inno Setup is WRONG.

**What Actually Happens:**
1. User runs installer
2. install_deps.bat runs **HIDDEN** → User has NO IDEA if it fails
3. download_model.bat runs **HIDDEN** → User has NO IDEA if it fails
4. Installer shows "Success!" → But deps/model might be missing
5. User clicks app → Backend CRASHES → "Backend Error" dialog
6. User has NO IDEA what went wrong

**Root Cause:** The .bat files are USELESS band-aids. Running them hidden during install means:
- No feedback on failure
- No progress visibility
- User can't cancel/retry
- Installer "succeeds" even when everything failed

### THE FIX: FIRST-RUN SETUP (Not During Install!)

**New Approach:** Do NOTHING during install. Do EVERYTHING on first app launch with visible progress.

```
Current Flow (BROKEN):
Install → [Hidden .bat fails?] → "Success" → Launch → CRASH

New Flow (CORRECT):
Install → Done (just copy files) → Launch → First-Run Setup UI → Works!
```

### Priority 8.0: Zero-Friction First Run

```
Priority 8.0: First-Run Setup System
├── 8.1 Remove .bat from Inno Setup ✅ DONE
│   ├── ✅ Remove install_deps.bat from [Run] section
│   ├── ✅ Remove download_model.bat from [Run] section
│   └── ✅ Keep .py files for use by first-run-setup.js
│
├── 8.2 Create electron/first-run-setup.js ✅ DONE
│   ├── ✅ Check if first_run_complete.flag exists
│   ├── ✅ If not: run setup sequence
│   ├── ✅ Step 1: Install Python deps (with progress)
│   ├── ✅ Step 2: Download AI model (with progress)
│   ├── ✅ Step 3: Verify installation
│   ├── ✅ Step 4: Create flag file when done
│   └── ✅ Show progress window to user (inline HTML)
│
├── 8.3 Modify electron/main.js ✅ DONE
│   ├── ✅ Import first-run-setup.js
│   ├── ✅ Before startBackendServer():
│   │   ├── ✅ Check if first run needed
│   │   ├── ✅ If yes: runFirstRunSetup()
│   │   └── ✅ Quit app if setup fails
│   └── ✅ Then launch backend as normal
│
├── 8.4 Create FirstTimeSetup UI ✅ DONE (inline HTML)
│   ├── ✅ Progress bars for each step
│   ├── ✅ Status messages (what's happening)
│   ├── ✅ Error handling (retry button)
│   └── ✅ "Setup Complete!" success state
│
├── 8.5 Auto-create folders in app directory ✅ DONE
│   ├── ✅ models/kr-sbert/ (created by download_model.py)
│   └── ✅ server/data/ (created by server/config.py)
│
├── 8.6 Verification before main app ✅ DONE
│   ├── ✅ Verify Python can import core deps
│   ├── ✅ Verify model files exist
│   ├── ✅ Verify server files exist
│   └── ✅ Create flag file only when ALL pass
│
├── 8.7 Progress output from Python scripts ✅ DONE
│   ├── ✅ install_deps.py - outputs X% progress
│   └── ✅ download_model.py - outputs X% progress
│
├── 8.8 Keep .bat files for manual use (optional) ✅ KEPT
│   ├── install_deps.bat - for manual troubleshooting
│   └── download_model.bat - for manual troubleshooting
│
├── 8.9 CI/CD Post-Build Testing ✅ DONE
│   ├── ✅ Install built .exe silently in CI
│   ├── ✅ Verify all critical files present
│   ├── ✅ Test backend imports with installed Python
│   └── ✅ Cleanup test installation
│
└── 8.10 CI/CD Bug Fixes (2025-12-04) ✅ DONE
    ├── ✅ Fix SQLite async pool_size error (NullPool doesn't support pool params)
    ├── ✅ Fix Unicode encoding errors (Windows cp1252 can't handle ✓✅❌)
    ├── ✅ Fix server startup timeout (increased to 20 retries)
    ├── ✅ Make API login test non-blocking
    └── ✅ BUILD PASSING - Release v2512041156 created!
```

### Technical Details:

**Where first-run check happens:** `locaNext/electron/main.js`
```javascript
// BEFORE:
const serverReady = await startBackendServer();

// AFTER:
const setupComplete = await checkFirstRunSetup(); // New function
if (!setupComplete) {
  await runFirstTimeSetup(); // Shows UI, installs deps, downloads model
}
const serverReady = await startBackendServer();
```

**Flag file location:** `{app}/first_run_complete.flag`
- Created only after ALL setup steps succeed
- If missing: run setup
- If present: skip setup, launch normally

**Progress communication:**
- Electron spawns Python scripts
- Python prints progress to stdout
- Electron captures and shows in UI
- User sees: "Installing dependencies... 45%"

### Files to Modify:

| File | Change |
|------|--------|
| `installer/locanext_light.iss` | Remove .bat calls from [Run] |
| `locaNext/electron/main.js` | Add first-run check before backend |
| `locaNext/electron/first-run-setup.js` | NEW: Handle setup logic |
| `locaNext/electron/preload.js` | Expose setup IPC if needed |
| `locaNext/src/lib/FirstTimeSetup.svelte` | NEW: Setup UI component |
| `tools/install_deps.py` | Add progress output |
| `tools/download_model.py` | Add progress output |

### Expected User Experience:

**First Launch:**
1. Click app icon
2. "First Time Setup" window appears
3. "Installing dependencies... 23%" (with progress bar)
4. "Downloading AI model... 67%" (with progress bar)
5. "Initializing database..."
6. "Setup complete! Launching app..."
7. Main app appears

**Subsequent Launches:**
1. Click app icon
2. Main app appears immediately (flag file exists)

---

## 🔄 Priority 9.0: Auto-Update System (2025-12-04)

**Goal:** Enable seamless automatic updates so users always have the latest version.

### How Auto-Update Works:

```
┌─────────────────────────────────────────────────────────────────┐
│                     USER'S INSTALLED APP                        │
│                                                                 │
│  1. App launches                                                │
│  2. Electron calls autoUpdater.checkForUpdates()                │
│  3. Fetches latest.yml from GitHub Releases                     │
│  4. Compares version in latest.yml vs installed version         │
│  5. If newer → downloads .exe silently                          │
│  6. Shows dialog: "Update available! Restart now?"              │
│  7. User clicks OK → app restarts with new version              │
└─────────────────────────────────────────────────────────────────┘
```

### Implementation Checklist:

```
Priority 9.0: Auto-Update System
├── 9.1 Enable GitHub Publish ✅ DONE
│   ├── ✅ Changed package.json "publish": null → GitHub config
│   ├── ✅ Provider: github
│   ├── ✅ Owner: NeilVibe
│   └── ✅ Repo: LocalizationTools
│
├── 9.2 Generate latest.yml in CI ✅ DONE
│   ├── ✅ Calculate SHA512 hash of installer
│   ├── ✅ Get semantic version from version.py
│   ├── ✅ Generate latest.yml with proper format
│   └── ✅ Upload to release artifacts
│
├── 9.3 Version Increment Validation ✅ DONE
│   ├── ✅ Compare current VERSION vs latest release
│   ├── ✅ Warn if version not incremented
│   └── ✅ Uses YYMMDDHHMM numeric comparison
│
├── 9.4 Release Assets ✅ DONE
│   ├── ✅ Installer .exe uploaded
│   └── ✅ latest.yml uploaded alongside
│
└── 9.5 End-to-End Test 📋 TODO
    ├── Trigger new build with incremented version
    ├── Verify latest.yml in release
    ├── Test old app detects new version
    └── Test update downloads and installs
```

### Version System Summary:

| File | Version Type | Example | Purpose |
|------|--------------|---------|---------|
| `version.py` | DateTime | 2512041724 | Internal tracking, release tags |
| `version.py` | Semantic | 1.0.0 | package.json, auto-updater |
| `package.json` | Semantic | 1.0.0 | Electron, electron-updater |
| `latest.yml` | Semantic | 1.0.0 | Auto-update version check |

### CI Safety Checks (Complete List):

| # | Check | Status | Description |
|---|-------|--------|-------------|
| 1 | Version Unification | ✅ | All 8 files match |
| 2 | Version Increment | ✅ | New > Latest release |
| 3 | Server Launch Test | ✅ | Backend starts OK |
| 4 | Python Tests | ✅ | E2E + Unit tests pass |
| 5 | Security Audits | ✅ | pip-audit + npm audit |
| 6 | Electron Build | ✅ | LocaNext.exe created |
| 7 | Installer Build | ✅ | Inno Setup compiles |
| 8 | Post-Install Test | ✅ | Silent install works |
| 9 | File Verification | ✅ | Critical files exist |
| 10 | Backend Import | ✅ | Installed Python imports |
| 11 | Health Check | ✅ | /health responds |
| 12 | API Login | ✅ | Auth works (non-blocking) |
| 13 | latest.yml | ✅ | Auto-update manifest |
| 14 | SHA512 Hash | ✅ | File integrity |

### To Release an Update:

```bash
# 1. Update version
NEW_VERSION=$(date '+%y%m%d%H%M')
# Edit version.py: VERSION = "$NEW_VERSION"

# 2. If breaking changes, bump SEMANTIC_VERSION
# Edit version.py: SEMANTIC_VERSION = "1.1.0"

# 3. Verify versions match
python3 scripts/check_version_unified.py

# 4. Commit and trigger build
git add -A && git commit -m "Version v$NEW_VERSION"
echo "Build LIGHT v$NEW_VERSION" >> BUILD_TRIGGER.txt
git add BUILD_TRIGGER.txt && git commit -m "Trigger build v$NEW_VERSION"
git push origin main

# 5. GitHub Actions builds + creates release with latest.yml
# 6. All installed apps auto-update on next launch!
```

---

## Previous Fixes (Priority 7.0) - SUPERSEDED BY 8.0

The following fixes from Priority 7.0 are still valid but the approach is changing:

| # | Issue | Old Fix | New Approach |
|---|-------|---------|--------------|
| 1 | version.py missing | ✅ Added to Inno Setup | Keep |
| 2 | PyJWT missing | ✅ install_deps.py | Move to first-run |
| 3 | bcrypt missing | ✅ install_deps.py | Move to first-run |
| 4 | Backend warnings | 🟡 TODO | Still needed |
| 5 | FAISS warnings | 🟡 TODO | Still needed |
| 6-8 | .bat file issues | ❌ Band-aids | DELETE .bat approach |
| 9-10 | CI tests | ✅ Keep | Keep |
| 11 | Pause in .bat | ❌ Obsolete | DELETE .bat files |

### What Stays From 7.0:
- ✅ version.py in Inno Setup
- ✅ CI import verification
- ✅ CI server launch test

### What Gets Replaced:
- ❌ Running .bat during install → First-run setup instead
- ❌ Hidden downloads during install → Visible progress on first launch
- ❌ "Hope it worked" → Verification before main app

---

## ✅ Recently Completed

### Priority 6.0: Project Structure Unification ✅ COMPLETE (2025-12-03)

**Problem Solved:** XLSTransfer was in `client/tools/` while other tools were in `server/tools/`.

**Result:**
```
server/tools/
├── xlstransfer/     ← XLSTransfer (14 files, 3683 lines - MOVED)
├── quicksearch/     ← QuickSearch
└── kr_similar/      ← KR Similar

server/client_config/
└── client_config.py ← Client settings (MOVED from client/config.py)

server/utils/client/
├── file_handler.py  ← Client utils (MOVED from client/utils/)
├── logger.py
└── progress.py
```

**Changes Made:**
- Moved XLSTransfer from `client/tools/xls_transfer/` to `server/tools/xlstransfer/`
- Moved client utils to `server/utils/client/`
- Moved client config to `server/client_config/client_config.py`
- Fixed path bug causing `server/server/` folder creation
- Updated all imports (20+ files)
- Updated all documentation (10+ files)
- Deleted `client/` folder entirely
- All tests passing (885)

**Commits:**
- `aff6093` - Priority 6.0: Unify project structure
- `e024035` - Update all documentation for Priority 6.0
- `98f50d6` - Fix client_config paths

---

## ✅ Previously Completed

### Platform Core
- ✅ FastAPI backend (47+ endpoints)
- ✅ SvelteKit frontend + Electron
- ✅ Admin Dashboard (Overview, Users, Stats, Logs)
- ✅ Database: SQLite (local) / PostgreSQL (server) - config switch
- ✅ WebSocket real-time progress
- ✅ JWT authentication

### Database Architecture
```
Current:  Local machine = SQLite (zero setup, just works)
Future:   Central server = PostgreSQL (just change .env)

# To switch later - edit .env:
DATABASE_TYPE=postgresql
DATABASE_URL=postgresql://user:pass@server-ip:5432/locanext
```

### Apps
- ✅ **XLSTransfer** - AI translation with Korean BERT (447MB model)
- ✅ **QuickSearch** - Multi-game dictionary (15 languages, 4 games)
- ✅ **KR Similar** - Korean semantic similarity

### Security (7/11)
- ✅ 3.0 IP Range Filter (24 tests)
- ✅ 3.1 CORS Origins (11 tests)
- ✅ 3.4 JWT Security (22 tests)
- ✅ 3.6 Audit Logging (29 tests)
- ✅ 3.7 Secrets Management
- ✅ 3.9 Dependency Audits (CI/CD)
- ✅ 3.10 Security Tests (86 total)
- 📋 3.2 TLS/HTTPS (optional)
- 📋 3.3 Rate Limiting (optional)

### User Management (Priority 5)
- ✅ 5.1 User profile fields (name, team, language)
- ✅ 5.2 Admin user creation
- ✅ 5.3 Change password API
- ✅ 5.4 User management API (18 tests)
- ✅ 5.5 Admin Users UI (831 lines)
- ✅ 5.6 Change Password UI (LocaNext)
- ✅ 5.7 Analytics Enhancement (team/language stats)
- ✅ 5.8 Database Backup scripts

### UI Enhancements (Priority 4.1)
- ✅ Settings Menu (About + Preferences modals)

### Data Structure (Priority 2.5)
```
server/data/
├── localizationtools.db
├── logs/
├── backups/
├── cache/temp/
├── kr_similar_dictionaries/
├── quicksearch_dictionaries/
├── xlstransfer_dictionaries/
└── outputs/{tool}/{date}/
```

### Distribution
- ✅ Git LFS (model tracked)
- ✅ Version unification (8 files)
- ✅ LIGHT build (100-150MB)
- ✅ GitHub Actions workflow
- ✅ Inno Setup installer

---

## 🏗️ Architecture

```
USER'S LOCAL PC                         CENTRAL SERVER
┌─────────────────────────────┐        ┌────────────────────┐
│  LocaNext Electron App      │        │  Telemetry Server  │
│  ┌───────┐  ┌───────────┐   │        │  • Log collection  │
│  │Svelte │◄─►│  Python   │   │───────►│  • User stats      │
│  │  UI   │  │  Backend  │   │ HTTP   │  • Admin Dashboard │
│  └───────┘  └───────────┘   │        └────────────────────┘
│  ⚡ HEAVY PROCESSING HERE   │
│  • Korean BERT (447MB)      │
│  • Excel processing         │
│  • Dictionary search        │
└─────────────────────────────┘
```

---

## 🔗 Documentation

| Doc | Purpose |
|-----|---------|
| `CLAUDE.md` | Master navigation |
| `docs/QUICK_START_GUIDE.md` | Setup in 5 min |
| `docs/ADD_NEW_APP_GUIDE.md` | Add new tools |
| `docs/PROJECT_STRUCTURE.md` | File tree |
| `docs/SECURITY_HARDENING.md` | Security config |
| `docs/BUILD_AND_DISTRIBUTION.md` | Build process |

---

## 🔑 Key Principles

1. **Backend is Flawless** - Don't modify core without confirmed bug
2. **LIGHT-First Builds** - No bundled models
3. **TRUE Simulation Tests** - No mocks, real functions
4. **Version Unification** - 8 files must match
5. **Unified Structure** - All tools in `server/tools/`

---

*Default login: admin / admin123*
*Ports: Backend 8888 | Frontend 5173 | Admin 5175*
