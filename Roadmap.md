# LocaNext - Development Roadmap

> **IMPORTANT**: This roadmap is for the **LocaNext platform ONLY** (infrastructure, APIs, deployment).
> **New Apps**: Can ONLY be added with EXPRESS DIRECT ORDER from user.
> **Standalone Scripts**: Are tracked separately in [`NewScripts/ROADMAP.md`](RessourcesForCodingTheProject/NewScripts/ROADMAP.md).

**Last Updated**: 2025-11-30
**Project Status**: Production Ready - LIGHT Build Strategy
**Current Version**: 2511221939

---

## 📊 Current Status

### Platform Overview
- **Backend**: FastAPI with 23 tool endpoints + 16 admin endpoints
- **Frontend**: SvelteKit with modern UI + Electron desktop
- **Admin Dashboard**: Full analytics, rankings, and activity logs
- **Database**: SQLite (dev) / PostgreSQL (prod)
- **Real-time**: WebSocket progress tracking
- **Auth**: JWT-based authentication & sessions
- **AI/ML**: Korean BERT (snunlp/KR-SBERT-V40K-klueNLI-augSTS) - 447MB

### Operational Apps
1. ✅ **XLSTransfer** (App #1) - AI-powered Excel translation with Korean BERT
2. ✅ **QuickSearch** (App #2) - Multi-game dictionary search (15 languages, 4 games)

### Build Status
| Component | Status | Notes |
|-----------|--------|-------|
| Web Platform | ✅ Done | SvelteKit + FastAPI (localhost) |
| Desktop App | ✅ Done | Electron (Windows .exe, Linux AppImage) |
| Local Build | ✅ Done | 103MB AppImage tested |
| LIGHT Build | ✅ Ready | Post-install model download |
| Version Unification | ✅ Done | 8 files checked, all unified |

---

## ✅ Recent Progress (2025-11-30)

### LIGHT Build Strategy - COMPLETE
- ✅ Created `scripts/download_model_silent.bat` - Silent download for wizard
- ✅ Created `installer/locanext_light.iss` - LIGHT installer (no model bundled)
- ✅ Updated `.github/workflows/build-electron.yml` - No LFS required
- ✅ Updated `BUILD_TRIGGER.txt` - VRS-Manager format (LIGHT/FULL)

### VRS-Manager Protocol Alignment - COMPLETE
- ✅ Version unification script checks 8 files
- ✅ Manual builds only (triggers on BUILD_TRIGGER.txt change)
- ✅ Single source of truth: `version.py`
- ✅ All files unified at version `2511221939`

### How LIGHT Build Works
1. GitHub Actions builds without LFS (~100-150MB installer)
2. User runs installer → files copied
3. Post-install → `download_model_silent.bat` runs automatically
4. Model downloads from Hugging Face (official, secure)
5. App ready with AI features

---

## 🎯 Next Steps

### Priority 1: First LIGHT Build ⚡
**Status**: Ready to trigger
**Goal**: Verify LIGHT build works in GitHub Actions

- [ ] Trigger build via BUILD_TRIGGER.txt
- [ ] Monitor GitHub Actions for errors
- [ ] Download and test installer artifact
- [ ] Create first GitHub Release

### Priority 2: UI/UX Enhancements 🎨
**Status**: Planned
**Goal**: Add Settings menu with About and Preferences

#### 2.1 Settings Dropdown Menu
Add a settings dropdown in the header with:

**About Section:**
- [ ] App name and logo
- [ ] Current version (from version.py)
- [ ] Build date
- [ ] Repository link
- [ ] Update notification (compare local vs latest release)
- [ ] "Check for Updates" button

**Preferences Section:**
- [ ] **Theme**: Dark mode / Light mode toggle
- [ ] **Language**: UI language selection (English, Korean, etc.)
- [ ] **Notifications**: Enable/disable desktop notifications
- [ ] **Auto-update**: Enable/disable auto-update check
- [ ] **Data**: Clear cache, reset preferences

#### 2.2 Implementation Plan
```
Settings Menu Structure:
├── About
│   ├── Version: 2511221939
│   ├── Build: 2025-11-30
│   ├── Check for Updates [button]
│   └── GitHub Repository [link]
│
└── Preferences
    ├── Appearance
    │   ├── Theme: [Dark / Light / System]
    │   └── Accent Color: [dropdown]
    ├── Language
    │   └── UI Language: [English / Korean / ...]
    ├── Notifications
    │   └── Desktop Notifications: [toggle]
    └── Advanced
        ├── Clear Cache [button]
        └── Reset to Defaults [button]
```

#### 2.3 Update Warning System
- Fetch latest release from GitHub API
- Compare version numbers
- Show notification badge on Settings icon if update available
- Display update dialog with changelog

### Priority 3: Admin Dashboard Authentication
**Status**: Pending
- [ ] Add login page for admin dashboard
- [ ] Protect admin routes with auth middleware
- [ ] Role-based access control

### Priority 4: Export Functionality
**Status**: Pending
- [ ] Export rankings to CSV/Excel
- [ ] Export statistics to PDF
- [ ] Download buttons in dashboard

---

## 📋 Build Protocol (VRS-Manager Style)

### Before Building
```bash
# 1. Update version in version.py (if needed)
# 2. Run version unification check
python3 scripts/check_version_unified.py

# 3. If all green ✅, proceed
# 4. Add build trigger
echo "Build LIGHT v2511221939" >> BUILD_TRIGGER.txt

# 5. Commit and push
git add -A && git commit -m "Trigger LIGHT build" && git push
```

### Build Triggers
- `Build LIGHT v[version]` → LIGHT installer (~100-150MB)
- `Build FULL v[version]` → FULL installer (~2GB) [needs LFS quota]

---

## ✅ Completed Milestones

### Core Platform - 100% Complete
- ✅ Backend: FastAPI with 39 endpoints (23 tool + 16 admin)
- ✅ Frontend: SvelteKit + Carbon Design System
- ✅ Admin Dashboard: Analytics, rankings, activity logs
- ✅ Database: SQLite with async SQLAlchemy
- ✅ WebSocket: Real-time progress tracking
- ✅ Auth: JWT-based authentication

### Apps - 2 Complete
- ✅ XLSTransfer (App #1) - AI-powered translation with Korean BERT
- ✅ QuickSearch (App #2) - Multi-game dictionary search

### Distribution Infrastructure - 100% Complete
- ✅ Git LFS configured (model tracked)
- ✅ Version unification (8 files, VRS-Manager protocol)
- ✅ Security audit (no secrets in repo)
- ✅ Model download scripts (Python + batch + silent)
- ✅ Local Electron build tested (103MB AppImage)
- ✅ GitHub Actions workflow (LIGHT build ready)
- ✅ Inno Setup installer (LIGHT version)
- ✅ BUILD_TRIGGER.txt (manual build control)

---

## 🏗️ Architecture Overview

### Technology Stack
- **Frontend**: SvelteKit 2.0 + Carbon Design System
- **Backend**: FastAPI + SQLAlchemy 2.0 (async)
- **Database**: SQLite (dev) / PostgreSQL (prod)
- **AI/ML**: Korean BERT via sentence-transformers
- **Desktop**: Electron
- **Build**: Electron-builder + Inno Setup
- **CI/CD**: GitHub Actions (manual trigger)

### Project Structure
```
LocalizationTools/
├── locaNext/              # Frontend (SvelteKit + Electron)
├── adminDashboard/        # Admin UI (SvelteKit)
├── server/                # Backend (FastAPI)
│   ├── api/               # API endpoints
│   ├── database/          # SQLAlchemy models
│   ├── tools/             # Tool implementations
│   └── utils/             # Utilities
├── models/                # AI models (LFS tracked)
│   └── kr-sbert/          # Korean BERT (447MB)
├── scripts/               # Build & setup scripts
├── installer/             # Inno Setup scripts
├── tests/                 # Test suite
└── docs/                  # Documentation
```

---

## 🚀 Quick Start

### Development Mode
```bash
# Terminal 1: Backend
python3 server/main.py
# → http://localhost:8888

# Terminal 2: Frontend
cd locaNext && npm run dev
# → http://localhost:5173

# Terminal 3: Admin Dashboard
cd adminDashboard && npm run dev
# → http://localhost:5174
```

### Access Points
- **Main App**: http://localhost:5173
- **Admin Dashboard**: http://localhost:5174
- **API Docs**: http://localhost:8888/docs
- **Health Check**: http://localhost:8888/health

### Default Credentials
```
Username: admin
Password: admin123
```

---

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| `CLAUDE.md` | Master navigation hub |
| `Roadmap.md` | This file - status & plans |
| `docs/ADD_NEW_APP_GUIDE.md` | Adding new tools |
| `docs/BUILD_AND_DISTRIBUTION.md` | Build process (LIGHT strategy) |
| `docs/TESTING_GUIDE.md` | Testing procedures |

---

## 🔑 Key Principles

1. **Backend is Flawless** - Never modify core backend without confirmed bug
2. **BaseToolAPI Pattern** - All new apps use shared base class
3. **Real-time Progress** - Every long operation emits WebSocket updates
4. **Comprehensive Logging** - All operations logged for debugging
5. **LIGHT-First Builds** - No bundled models, download post-install
6. **Version Unification** - All 8 files must match before build

---

**Last Updated**: 2025-11-30
**Current Version**: 2511221939
**Current Focus**: First LIGHT build test
**Next Milestone**: Settings menu with About/Preferences
**Platform Status**: Core Complete - Ready for First Release
