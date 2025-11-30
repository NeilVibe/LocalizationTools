# LocaNext - Development Roadmap

> **IMPORTANT**: This roadmap is for the **LocaNext platform ONLY** (infrastructure, APIs, deployment).
> **New Apps**: Can ONLY be added with EXPRESS DIRECT ORDER from user.
> **Standalone Scripts**: Are tracked separately in [`NewScripts/ROADMAP.md`](RessourcesForCodingTheProject/NewScripts/ROADMAP.md).

**Last Updated**: 2025-11-30
**Project Status**: Production Ready - LIGHT Build Strategy
**Current Focus**: LIGHT installer with post-install model download

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
| GitHub Actions | ⏳ Blocked | LFS bandwidth quota exceeded |

### The Problem (2025-11-22)
- Git LFS free tier: 1GB/month
- Model size: 447MB × 2 jobs = ~894MB per build
- **Result**: Quota exceeded after first test build

---

## 🎯 NEW STRATEGY: LIGHT-First Build (2025-11-30)

### The Solution
Instead of bundling the 447MB model in the build (expensive LFS bandwidth), we:
1. **Build LIGHT installer** (~100-150MB) - NO model bundled
2. **Download model during install wizard** - User's bandwidth, not GitHub's
3. **No LFS costs** - Model never goes through GitHub Actions

### Why This Is Better
| Aspect | OLD (FULL) | NEW (LIGHT) |
|--------|------------|-------------|
| Build size | ~2GB | ~100-150MB |
| LFS bandwidth/build | ~894MB | ~0MB |
| GitHub Actions | Blocked by quota | No issues |
| User experience | Faster install | Slightly longer (model download) |
| Cost | $5/50GB data pack | FREE |

### Implementation Plan

#### Phase 1: LIGHT Build Setup (Priority 1) ⚡
**Status**: TODO
**Goal**: Create working LIGHT build with post-install model download

**Step 1.1: Update Inno Setup Installer**
- [ ] Modify `installer/locanext_full.iss` → `installer/locanext_light.iss`
- [ ] Remove model files from `[Files]` section
- [ ] Add post-install script to download model
- [ ] Show progress during model download in wizard

**Inno Setup Post-Install Model Download**:
```ini
[Run]
; Download model after installation
Filename: "{app}\scripts\download_model.bat"; \
  Description: "Downloading AI Model (447MB - Required for XLSTransfer)"; \
  Flags: runhidden waituntilterminated; \
  StatusMsg: "Downloading Korean BERT model... This may take 5-10 minutes."

; Then launch app
Filename: "{app}\LocaNext.exe"; \
  Description: "Launch LocaNext"; \
  Flags: nowait postinstall skipifsilent
```

**Step 1.2: Update GitHub Actions Workflow**
- [ ] Modify `.github/workflows/build-installers.yml`
- [ ] Remove `lfs: true` from checkout (not needed!)
- [ ] Build LIGHT version only
- [ ] Smaller artifacts, faster builds

**Updated Workflow (no LFS)**:
```yaml
- name: Checkout code
  uses: actions/checkout@v4
  # NO lfs: true - model downloaded by user post-install

- name: Build executable
  run: |
    # Build without model - user downloads during install
    pyinstaller LocaNext_light.spec --clean --noconfirm
```

**Step 1.3: Create/Update Download Scripts**
- [ ] Ensure `scripts/download_bert_model.py` works standalone
- [ ] Ensure `scripts/download_model.bat` shows progress
- [ ] Add retry logic for failed downloads
- [ ] Verify model integrity after download

**Step 1.4: Test Full Flow**
- [ ] Build LIGHT installer locally
- [ ] Run installer on clean Windows VM
- [ ] Verify model downloads during install
- [ ] Verify app works after model download
- [ ] Test offline scenario (model already present)

#### Phase 2: GitHub Actions Build (Priority 2)
**Status**: Pending Phase 1
**Goal**: Automated LIGHT builds via GitHub Actions

- [ ] Push updated workflow
- [ ] Trigger build (no LFS quota issues!)
- [ ] Download artifact and test
- [ ] Create GitHub Release

#### Phase 3: Polish & Documentation (Priority 3)
**Status**: Pending Phase 2

- [ ] Update README with new install process
- [ ] Document model download requirements
- [ ] Add troubleshooting for download failures
- [ ] Update BUILD_TRIGGER.txt format

---

## 📋 Action Items (Ordered)

### Immediate (This Session)
1. [ ] Update `installer/locanext_light.iss` with post-install download
2. [ ] Update `.github/workflows/build-installers.yml` (remove LFS)
3. [ ] Verify `scripts/download_model.bat` works standalone
4. [ ] Test locally if possible

### Next Session
1. [ ] Push changes and trigger GitHub Actions build
2. [ ] Test LIGHT installer on Windows
3. [ ] Create first release

### Future
1. [ ] Admin Dashboard authentication
2. [ ] Export functionality (CSV/Excel/PDF)
3. [ ] Production web deployment

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

### Distribution Infrastructure - 90% Complete
- ✅ Git LFS configured (model tracked)
- ✅ Version management system (YYMMDDHHMM format)
- ✅ Security audit (no secrets in repo)
- ✅ Model download scripts (Python + batch)
- ✅ Local Electron build tested (103MB AppImage)
- ✅ GitHub Actions workflow created
- ⏳ LIGHT build strategy (in progress)

---

## 🏗️ Architecture Overview

### Technology Stack
- **Frontend**: SvelteKit 2.0 + Carbon Design System
- **Backend**: FastAPI + SQLAlchemy 2.0 (async)
- **Database**: SQLite (dev) / PostgreSQL (prod)
- **AI/ML**: Korean BERT via sentence-transformers
- **Desktop**: Electron
- **Build**: PyInstaller + Inno Setup
- **CI/CD**: GitHub Actions

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
| `docs/BUILD_AND_DISTRIBUTION.md` | Build process |
| `docs/TESTING_GUIDE.md` | Testing procedures |

---

## 🔑 Key Principles

1. **Backend is Flawless** - Never modify core backend without confirmed bug
2. **BaseToolAPI Pattern** - All new apps use shared base class
3. **Real-time Progress** - Every long operation emits WebSocket updates
4. **Comprehensive Logging** - All operations logged for debugging
5. **LIGHT-First Builds** - No bundled models, download post-install

---

**Last Updated**: 2025-11-30
**Current Focus**: LIGHT-first build strategy
**Next Milestone**: Working LIGHT installer with post-install model download
**Platform Status**: Core Complete - Distribution Optimization
