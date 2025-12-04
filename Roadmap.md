# LocaNext - Development Roadmap

**Version**: 2512041724 | **Updated**: 2025-12-04 | **Status**: Priority 9.0 COMPLETE ✅ | Next: P10 UI/UX

---

## 🗺️ NAVIGATION TREE (Jump to Section)

```
Roadmap.md
│
├── 🌳 STATUS TREE ─────────────── Platform overview at a glance
├── 🔒 CI SAFETY CHECKS ────────── All 14 build verification checks
├── ⚡ QUICK COMMANDS ──────────── Copy-paste commands
│
├── ✅ COMPLETE: Priority 9.0 ──── Auto-Update System (DONE!)
├── 🔄 CURRENT: Priority 10.0 ──── Auto-Update UI/UX (IN PROGRESS)
├── ✅ COMPLETE: Priority 8.0 ──── First-Run Setup
├── ✅ COMPLETE: Priority 6.0 ──── Structure Unification
│
├── 📦 COMPLETED FEATURES ──────── Compact list of all done items
├── 🏗️ ARCHITECTURE ────────────── System diagram
└── 📋 ARCHIVE ─────────────────── Historical fixes (Priority 7.0)
```

---

## 🌳 STATUS TREE

```
LocaNext Platform v2512041724
│
├── ✅ Backend (100%) ─────────── FastAPI, 47+ endpoints, async
├── ✅ Frontend (100%) ────────── SvelteKit + Carbon Design
├── ✅ Admin Dashboard (100%) ─── Stats, Users, Logs
├── ✅ Security (7/11) ────────── IP filter, CORS, JWT, audit
├── ✅ Tests (885) ───────────── TRUE simulation (no mocks!)
├── ✅ Structure (100%) ───────── All tools under server/tools/
│
├── 🛠️ Apps
│   ├── ✅ XLSTransfer ────────── Excel + Korean BERT AI
│   ├── ✅ QuickSearch ────────── Dictionary (15 langs, 4 games)
│   └── ✅ KR Similar ─────────── Korean semantic similarity
│
├── 📦 Distribution
│   ├── ✅ Electron Desktop ───── Windows .exe
│   ├── ✅ LIGHT Build ────────── ~200MB, deps on first-run
│   ├── ✅ Version Unified ────── 8 files synced
│   └── 🔄 Auto-Update ────────── GitHub releases + latest.yml
│
└── 🎯 Priorities
    ├── ✅ P6: Structure ───────── Unified server/tools/
    ├── ✅ P8: First-Run ──────── Setup UI on launch
    ├── ✅ P9: Auto-Update ────── COMPLETE! (latest.yml + GitHub)
    └── 🔄 P10: Update UI/UX ──── IN PROGRESS (Beautiful modals)
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

## 🔄 Priority 9.0: Auto-Update System (CURRENT)

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

## 📋 Priority 10.0: Auto-Update UI/UX (NEXT)

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
├── 10.3 Patch Notes System 📋
│   ├── Parse release notes from GitHub
│   ├── Show in update modal
│   ├── Markdown rendering
│   └── "Read full changelog" link
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

## 🏗️ ARCHITECTURE

```
USER'S PC                           SERVER (Optional)
┌─────────────────────────┐        ┌──────────────────┐
│  LocaNext Electron      │        │  Telemetry       │
│  ┌───────┐ ┌─────────┐  │        │  • Logs          │
│  │Svelte │◄►│ Python  │  │───────►│  • Stats         │
│  │  UI   │ │ Backend │  │ HTTP   │  • Dashboard     │
│  └───────┘ └─────────┘  │        └──────────────────┘
│  • Korean BERT (447MB)  │
│  • Excel processing     │
└─────────────────────────┘
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

*Login: admin / admin123 | Ports: Backend 8888 | Frontend 5173 | Admin 5175*
