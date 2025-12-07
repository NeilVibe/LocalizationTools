# CLAUDE.md - LocaNext Master Navigation Hub

**Version:** 2512071836 (2025-12-07)
**Status:** Backend ✅ | Frontend ✅ | Database ✅ | WebSocket ✅ | TaskManager ✅ | XLSTransfer ✅ | QuickSearch ✅ | KR Similar ✅ | Distribution ✅ | Security ✅ | Tests ✅ | Structure ✅ | Health Check ✅ | Telemetry ✅ | Testing Toolkit ✅ | **Migration VERIFIED** ✅

---

## 🎯 PROJECT OVERVIEW

**LocaNext** (formerly LocalizationTools) is a **professional desktop platform** that consolidates localization/translation Python scripts into one unified Electron application.

### Key Features:
- 🏢 **Platform approach**: Host 10-20+ tools in one app
- 💻 **Local processing**: Runs on user's CPU, works offline
- 📊 **Central monitoring**: Optional telemetry to server
- 👔 **Professional**: CEO/management-ready quality

### Current Status (2025-12-06):
- ✅ **Backend**: 100% Complete (47+ endpoints, WebSocket, async)
- ✅ **LocaNext Desktop App**: 100% Complete (Electron + Svelte)
- ✅ **XLSTransfer (App #1)**: VERIFIED - 10/10 tests with real Excel files
- ✅ **QuickSearch (App #2)**: VERIFIED - 8/8 tests with TXT + XML files
- ✅ **KR Similar (App #3)**: VERIFIED - 10/10 tests with 41,715 pairs
- ✅ **Migration**: ALL 33 monolith functions verified with production test files
- ✅ **Distribution**: Git LFS, versioning, build system ready
- ✅ **Security**: 7/11 Complete (IP filter, CORS, JWT, audit logging, 86 tests)
- ✅ **Tests**: 885 passed (TRUE simulation - no mocks!)
- ✅ **Structure**: Unified - all tools under `server/tools/` (Priority 6.0 complete)
- ✅ **Admin Dashboard**: 100% Complete (Overview, Users, Stats, Logs, Telemetry)
- ✅ **Health Check**: Priority 11.0 - Auto-repair system complete
- ✅ **Telemetry**: Priority 12.5.9 COMPLETE - Server + Client + Dashboard + Tool Tracking

---

## 📚 DOCUMENTATION TREE (START HERE!)

```
docs/
├── README.md                    # Master index
├── getting-started/             # Onboarding
│   ├── QUICK_START_GUIDE.md
│   ├── PROJECT_STRUCTURE.md
│   └── ADMIN_SETUP.md
├── architecture/                # Design patterns
│   ├── README.md
│   ├── ASYNC_PATTERNS.md
│   ├── BACKEND_PRINCIPLES.md
│   └── PLATFORM_PATTERN.md
├── development/                 # Coding guides
│   ├── CODING_STANDARDS.md
│   ├── ADD_NEW_APP_GUIDE.md
│   ├── LOGGING_PROTOCOL.md
│   ├── BEST_PRACTICES.md
│   └── PERFORMANCE.md
├── build/                       # Build & Distribution
│   ├── BUILD_AND_DISTRIBUTION.md
│   ├── BUILD_TROUBLESHOOTING.md
│   ├── BUILD_CHECKLIST.md
│   └── PACKAGING_GUIDE.md
├── deployment/                  # Deploy & Operations
│   ├── DEPLOYMENT.md
│   ├── DEPLOYMENT_ARCHITECTURE.md
│   ├── GITEA_SETUP.md
│   ├── PATCH_SERVER.md
│   └── POSTGRESQL_SETUP.md
├── security/                    # Security
│   ├── SECURITY_HARDENING.md
│   └── SECURITY_AND_LOGGING.md
├── testing/                     # Testing guides
│   ├── README.md
│   ├── DEBUG_AND_TEST_HUB.md
│   ├── PYTEST_GUIDE.md
│   ├── PLAYWRIGHT_GUIDE.md
│   └── QUICK_COMMANDS.md
├── troubleshooting/             # Debug guides
│   ├── WINDOWS_TROUBLESHOOTING.md
│   ├── ELECTRON_TROUBLESHOOTING.md
│   └── MONITORING_COMPLETE_GUIDE.md
├── tools/                       # Tool-specific
│   ├── XLSTRANSFER_GUIDE.md
│   └── MONOLITH_DEVIATIONS.md
├── history/                     # Completed work
│   └── ROADMAP_ARCHIVE.md
└── deprecated/                  # Outdated docs
```

### 🚀 Getting Started

| Document | Path |
|----------|------|
| Quick Start | `docs/getting-started/QUICK_START_GUIDE.md` |
| Project Structure | `docs/getting-started/PROJECT_STRUCTURE.md` |
| Admin Setup | `docs/getting-started/ADMIN_SETUP.md` |
| **Roadmap** | `Roadmap.md` (root) |

### 🏗️ Architecture

| Document | Path |
|----------|------|
| Architecture Index | `docs/architecture/README.md` |
| Deployment Architecture | `docs/deployment/DEPLOYMENT_ARCHITECTURE.md` |
| Platform Pattern | `docs/architecture/PLATFORM_PATTERN.md` |
| Backend Principles | `docs/architecture/BACKEND_PRINCIPLES.md` |

### 🛠️ Development

| Document | Path |
|----------|------|
| Coding Standards | `docs/development/CODING_STANDARDS.md` |
| Add New App | `docs/development/ADD_NEW_APP_GUIDE.md` |
| Logging Protocol | `docs/development/LOGGING_PROTOCOL.md` |

### 📜 NewScripts (Mini-Projects)

| Document | What It Covers |
|----------|----------------|
| **[NewScripts/README.md](RessourcesForCodingTheProject/NewScripts/README.md)** | Script catalog, patterns, templates, Claude instructions |
| **[NewScripts/WORKFLOW.md](RessourcesForCodingTheProject/NewScripts/WORKFLOW.md)** | 7-phase workflow for creating new scripts |
| **[NewScripts/ROADMAP.md](RessourcesForCodingTheProject/NewScripts/ROADMAP.md)** | Development plan for NewScripts |
| **[GlossarySniffer/](RessourcesForCodingTheProject/NewScripts/GlossarySniffer/)** | Mini-project: Glossary extraction tool |
| **[WordCountMaster/](RessourcesForCodingTheProject/NewScripts/WordCountMaster/)** | Mini-project: Word count diff tool |
| **[ExcelRegex/](RessourcesForCodingTheProject/NewScripts/ExcelRegex/)** | Mini-project: Regex operations on Excel files |

### 📂 Reference Scripts (RessourcesForCodingTheProject)

| Resource | What It Covers |
|----------|----------------|
| **[MAIN PYTHON SCRIPTS/](RessourcesForCodingTheProject/MAIN%20PYTHON%20SCRIPTS/)** | 9 main tools (XLSTransfer, QuickSearch, KRSimilar, TFM, etc.) |
| **[SECONDARY PYTHON SCRIPTS/](RessourcesForCodingTheProject/SECONDARY%20PYTHON%20SCRIPTS/)** | 74 utility scripts (XML, Excel, TMX, text processing) |
| **[datausedfortesting/](RessourcesForCodingTheProject/datausedfortesting/)** | Test data for script development |
| **[guides/](RessourcesForCodingTheProject/guides/)** | Guides for existing reference scripts |
| **[.claude/newscript_instructions.md](.claude/newscript_instructions.md)** | Claude AI instructions for building scripts |

### 🧪 Testing & Debugging (Complete Tree)

| Document | What It Covers |
|----------|----------------|
| **[testing/DEBUG_AND_TEST_HUB.md](docs/testing/DEBUG_AND_TEST_HUB.md)** | **🎯 MASTER GUIDE** - ALL remote access methods, CDP, pytest, Playwright |
| **[testing/README.md](docs/testing/README.md)** | Testing Hub - Quick navigation |
| **[testing_toolkit/](testing_toolkit/)** | **Autonomous CDP testing scripts** (run_test.js, run_all_tests.js) |
| **[testing_toolkit/ADD_TEST_MODE_GUIDE.md](testing_toolkit/ADD_TEST_MODE_GUIDE.md)** | **How to add TEST MODE to new apps** |
| **[testing/QUICK_COMMANDS.md](docs/testing/QUICK_COMMANDS.md)** | Copy-paste commands only |
| **[testing/PYTEST_GUIDE.md](docs/testing/PYTEST_GUIDE.md)** | Python backend tests |
| **[testing/PLAYWRIGHT_GUIDE.md](docs/testing/PLAYWRIGHT_GUIDE.md)** | Frontend E2E tests |
| **[testing/X_SERVER_SETUP.md](docs/testing/X_SERVER_SETUP.md)** | VcXsrv for visual testing |
| **[testing/TOOLS_REFERENCE.md](docs/testing/TOOLS_REFERENCE.md)** | xdotool, ffmpeg, etc. |
| **[WINDOWS_TROUBLESHOOTING.md](docs/troubleshooting/WINDOWS_TROUBLESHOOTING.md)** | CDP debugging, Windows EXE from WSL |
| **[ELECTRON_TROUBLESHOOTING.md](docs/troubleshooting/ELECTRON_TROUBLESHOOTING.md)** | Black screen, preload fixes |

### 📦 Build & Distribution

| Document | What It Covers |
|----------|----------------|
| **[BUILD_AND_DISTRIBUTION.md](docs/build/BUILD_AND_DISTRIBUTION.md)** | Versioning, manual builds, Git LFS, troubleshooting |
| **[BUILD_TROUBLESHOOTING.md](docs/build/BUILD_TROUBLESHOOTING.md)** | Debugging failed builds, GitHub Actions |
| **[BUILD_CHECKLIST.md](docs/build/BUILD_CHECKLIST.md)** | Pre-release checklist |
| **[PACKAGING_GUIDE.md](docs/build/PACKAGING_GUIDE.md)** | Electron packaging details |

#### 🔀 Dual-Build System (GitHub + Gitea)

**ONE codebase, TWO separate build triggers:**

```
LocalizationTools/
├── .github/workflows/build-electron.yml  → Watches BUILD_TRIGGER.txt  (GitHub/Production)
├── .gitea/workflows/build.yml            → Watches GITEA_TRIGGER.txt  (Gitea/Local Test)
├── BUILD_TRIGGER.txt                     → GitHub trigger file
└── GITEA_TRIGGER.txt                     → Gitea trigger file
```

**Quick Build Commands:**

```bash
# === GitHub Build (Production) ===
NEW_VERSION=$(date '+%y%m%d%H%M')
# 1. Update version.py with $NEW_VERSION
# 2. python3 scripts/check_version_unified.py
echo "Build LIGHT v$NEW_VERSION" >> BUILD_TRIGGER.txt
git add -A && git commit -m "Build v$NEW_VERSION"
git push origin main                    # GitHub ONLY

# === Gitea Build (Local Testing) ===
echo "Build LIGHT v$NEW_VERSION" >> GITEA_TRIGGER.txt
git add -A && git commit -m "Gitea test v$NEW_VERSION"
git push gitea main                     # Gitea ONLY

# === Code Sync (No Build) ===
git push origin main && git push gitea main  # BOTH remotes
```

### 🌐 Deployment & Operations

| Document | What It Covers |
|----------|----------------|
| **[DEPLOYMENT.md](docs/deployment/DEPLOYMENT.md)** | Production deployment procedures |
| **[DEPLOYMENT_ARCHITECTURE.md](docs/deployment/DEPLOYMENT_ARCHITECTURE.md)** | Quad Entity architecture |
| **[ADMIN_SETUP.md](docs/getting-started/ADMIN_SETUP.md)** | Initial admin user setup, credentials |
| **[POSTGRESQL_SETUP.md](docs/deployment/POSTGRESQL_SETUP.md)** | PostgreSQL configuration |
| **[GITEA_SETUP.md](docs/deployment/GITEA_SETUP.md)** | Self-hosted Git + CI/CD setup |
| **[PATCH_SERVER.md](docs/deployment/PATCH_SERVER.md)** | **Gitea as patch server for auto-updates** |
| **[SECURITY_AND_LOGGING.md](docs/security/SECURITY_AND_LOGGING.md)** | Security best practices |

### 🔒 Security

| Document | What It Covers |
|----------|----------------|
| **[SECURITY_HARDENING.md](docs/security/SECURITY_HARDENING.md)** | **Full security guide: IP filter, CORS, JWT, audit logging (86 tests)** |
| **[.env.example](.env.example)** | Production environment configuration template |

**Security Implementation Status (7/11):**
- ✅ IP Range Filtering (24 tests) - Primary access control
- ✅ CORS & Origin Restrictions (11 tests)
- ✅ JWT Token Security (22 tests) - Startup validation
- ✅ Audit Logging (29 tests) - Login/security events
- ✅ Secrets Management - .env.example ready
- ✅ Dependency Security - CI/CD audits (CRITICAL/HIGH blocks build)
- ✅ Security Testing - 86 total tests
- 📋 TLS/HTTPS - Optional for internal network
- 📋 Rate Limiting - Optional for internal network

### 🤖 Claude AI Guides (READ THESE!)

| Document | What It Covers |
|----------|----------------|
| **[testing/README.md](docs/testing/README.md)** | **Testing Hub** - Autonomous testing, work alone! |
| **[CLAUDE_AI_WARNINGS.md](docs/development/CLAUDE_AI_WARNINGS.md)** | AI hallucination prevention (5 documented types) |

### 🎯 Tool-Specific Guides

| Document | What It Covers |
|----------|----------------|
| **[XLSTRANSFER_GUIDE.md](docs/tools/XLSTRANSFER_GUIDE.md)** | XLSTransfer complete reference (dual-mode, API, GUI) |
| **[MONOLITH_DEVIATIONS.md](docs/tools/MONOLITH_DEVIATIONS.md)** | Migration audit status |

### 📖 Reference

| Document | What It Covers |
|----------|----------------|
| **[BEST_PRACTICES.md](docs/development/BEST_PRACTICES.md)** | Best practices collection |
| **[PERFORMANCE.md](docs/development/PERFORMANCE.md)** | Performance optimization |
| **[STATS_DASHBOARD_SPEC.md](docs/deprecated/STATS_DASHBOARD_SPEC.md)** | Admin dashboard specifications |

---

## 🚨 CRITICAL RULES (READ FIRST!)

### 0. MONOLITH CODE IS SACRED (MOST IMPORTANT!)
```
⚠️  THE ORIGIN MONOLITH CODE MUST BE PERFECTLY AND IDENTICALLY MIGRATED  ⚠️

The Python scripts in RessourcesForCodingTheProject/ are FLAWLESS.
ANY deviation from monolith logic = BUG in our implementation.
```
- **COPY** monolith logic EXACTLY into `server/tools/{tool}/`
- **ONLY** change UI code (tkinter → API), **NEVER** change core logic
- **TEST** with same input files the monolith uses
- See: [MONOLITH_DEVIATIONS.md](docs/tools/MONOLITH_DEVIATIONS.md) for audit status
- Monolith sources:
  - `XLSTransfer0225.py` → `server/tools/xlstransfer/`
  - `KRSIMILAR0124.py` → `server/tools/kr_similar/`
  - `QuickSearch0818.py` → `server/tools/quicksearch/`

### 1. Backend is Flawless
- **NEVER** modify backend core code without explicit permission
- Only create wrapper layers (API endpoints, GUI)
- See: [BACKEND_PRINCIPLES.md](docs/architecture/BACKEND_PRINCIPLES.md)

### 2. Logging is Mandatory
- **LOG EVERYTHING** at every step
- Use `logger`, NEVER use `print()`
- See: [LOGGING_PROTOCOL.md](docs/development/LOGGING_PROTOCOL.md)

### 3. Version Management
- **ALWAYS** run `python3 scripts/check_version_unified.py` before commit
- Builds are **MANUAL** (not automatic on every push)
- See: [BUILD_AND_DISTRIBUTION.md](docs/build/BUILD_AND_DISTRIBUTION.md)

### 4. Testing Required (FULL SERVER SIMULATION)
- **ALWAYS run with server** for true production simulation:
  ```bash
  python3 scripts/create_admin.py && python3 server/main.py &
  sleep 5 && RUN_API_TESTS=1 python3 -m pytest -v
  ```
- See: [TESTING_PROTOCOL.md](docs/testing/TESTING_PROTOCOL.md) for autonomous testing

### 5. Async by Default
- All new endpoints should be async
- Use `AsyncSession` for database
- See: [ASYNC_PATTERNS.md](docs/architecture/ASYNC_PATTERNS.md)

---

## ⚡ QUICK COMMANDS

### Start Servers
```bash
# Backend server (port 8888)
python3 server/main.py

# LocaNext desktop app
cd locaNext && npm run electron:dev

# Admin dashboard (port 5175)
cd adminDashboard && npm run dev -- --port 5175
```

### Testing
```bash
# Quick tests (no server needed)
python3 -m pytest

# FULL tests with API (start server first!)
python3 scripts/create_admin.py
python3 server/main.py &
sleep 5
RUN_API_TESTS=1 python3 -m pytest -v

# Check version consistency
python3 scripts/check_version_unified.py
```

### Build & Deploy
```bash
# Update version
NEW_VERSION=$(date '+%y%m%d%H%M')
# Edit version.py, then:
python3 scripts/check_version_unified.py
git add -A && git commit -m "Version v$NEW_VERSION"
git push origin main
git push gitea main

# Trigger build (when ready)
echo "Build FULL v$NEW_VERSION" >> BUILD_TRIGGER.txt
git add BUILD_TRIGGER.txt && git commit -m "Trigger build v$NEW_VERSION"
git push origin main
git push gitea main
```

### Git Dual Push (REQUIRED)
```bash
# ALWAYS push to BOTH remotes after every commit:
git push origin main   # GitHub (primary)
git push gitea main    # Gitea (local backup + CI/CD)

# Remotes configured:
# origin = git@github.com:NeilVibe/LocalizationTools.git
# gitea  = neil1988@gitea-local:neilvibe/LocaNext.git
```
> ⚠️ **Claude AI: ALWAYS push to both remotes!** This is NOT automatic.

### Monitoring
```bash
# Real-time logs
bash scripts/monitor_logs_realtime.sh

# System health check
bash scripts/monitor_system.sh

# Clean old logs
bash scripts/clean_logs.sh
```

---

## 🌐 IMPORTANT URLS (When Running)

- Backend: http://localhost:8888
- API Docs: http://localhost:8888/docs
- Health Check: http://localhost:8888/health
- LocaNext Web: http://localhost:5176
- Admin Dashboard: http://localhost:5175

---

## 🤝 FOR NEW CLAUDE SESSIONS

### First Steps:
1. ✅ Read this file completely (you're here!)
2. ✅ Read [QUICK_START_GUIDE.md](docs/getting-started/QUICK_START_GUIDE.md) (5 min)
3. ✅ Run `python3 server/main.py` to verify backend works
4. ✅ Run `RUN_API_TESTS=1 python3 -m pytest` to verify tests pass (885 expected)
5. ✅ Check **Roadmap.md** for current task

### Current Phase:
- **Phase 3:** Security Hardening ✅ COMPLETE (7/11 items, 86 tests)
- **Phase 4:** Admin Dashboard ✅ COMPLETE
- **Priority 11.0:** Health Check & Auto-Repair ✅ COMPLETE
- **Priority 12.5:** Central Telemetry System ✅ FULL STACK COMPLETE
- **Priority 13.0:** Gitea Patch Server ✅ FULLY COMPLETE
  - ✅ Installed: `/home/neil1988/gitea/` (v1.22.3, SQLite)
  - ✅ Scripts: `start.sh`, `stop.sh`, `start_runner.sh`, `stop_runner.sh`
  - ✅ Config: Port 3000 (web), 2222 (SSH)
  - ✅ Repo: `neilvibe/LocaNext` (dual remote configured)
  - ✅ Actions: ENABLED + act_runner v0.2.11 registered
  - ✅ Workflow: `.gitea/workflows/build.yml` (test → build → release)
  - ✅ Runner: "locanext-runner" online
  - ✅ Auto-Update: `updater.js` supports GitHub/Gitea/Custom via env var
  - ✅ DUAL PUSH: `git push origin main && git push gitea main`
  - ✅ Patch Server Docs: `docs/PATCH_SERVER.md` (Option A: Mirror, Option B: Self-hosted)
  - ✅ Mirror Script: `scripts/mirror_release_to_gitea.sh` (tested, v2512071836 mirrored)
  - ✅ Cleanup Script: `scripts/cleanup_old_releases.sh` (tested, keeps latest 2)
  - ✅ API Token: "patch-server-full" saved to ~/.bashrc
- **Testing Toolkit:** ✅ COMPLETE
  - ✅ CDP-based autonomous testing (`testing_toolkit/`)
  - ✅ All 3 apps have TEST MODE (xlsTransfer, quickSearch, krSimilar)
  - ✅ ADD_TEST_MODE_GUIDE.md for future apps (LD Manager template)

### Quick Gitea Commands:
```bash
cd ~/gitea && ./start.sh   # Start Gitea → http://localhost:3000
cd ~/gitea && ./stop.sh    # Stop Gitea
```

### Questions to Ask User:
- "Start P17 LD Manager (CAT Tool)?" - Big feature, language data editor
- "Should we add another tool to LocaNext?" (P14 - New Tools)
- "Want to fix P10.3 (Patch Notes display)?" - Nice-to-have, backlog

### Windows Build Debugging:
- See **[WINDOWS_TROUBLESHOOTING.md](docs/troubleshooting/WINDOWS_TROUBLESHOOTING.md)** for WSL debugging commands
- User can provide Windows install path (e.g., `C:\Users\...\LocaNext`)
- Access via WSL: `/mnt/c/Users/.../LocaNext`

---

## 📊 PROJECT STATS

- **Lines of Code:** ~19,000+
- **API Endpoints:** 55+ (async + sync, includes 8 admin telemetry)
- **Database Tables:** 17 (13 core + 4 telemetry)
- **Tests:** 912 total (TRUE simulation - no mocks!)
- **E2E Tests:** 115 (KR Similar 18 + QuickSearch 11 + XLSTransfer 9 + Edge Cases 23 + Workflows 54)
- **Frontend E2E:** 164 (Playwright - LocaNext 134 + Admin Dashboard 30)
  - LocaNext 134: Login 10 + Nav 10 + Tools 11 + API 8 + Frontend-Backend 16 + Full Workflow 17 + TaskManager 22 + File Operations 20 + WebSocket/Real-time 19 + Screenshot 1
  - Admin Dashboard 30: Dashboard 15 + Telemetry 15
- **Unit Tests:** 377+ (auth, cache, websocket, dependencies, tools, QA Tools 27)
- **API Simulation Tests:** 168 (Tools 26 + Admin 15 + Errors 25 + WebSocket 10 + Full System 72)
- **Security Tests:** 86 (IP filter, CORS, JWT, audit logging)
- **Tools:** 3 (XLSTransfer, QuickSearch, KR Similar) - all under `server/tools/`, 14/14 CDP tests passed
- **Documentation Files:** 30 active + 9 archived (updated WINDOWS_TROUBLESHOOTING.md)

---

## 🎉 YOU'RE READY!

This project is **97% complete**, **clean**, **organized**, and **production-ready**.

**Everything is documented. Navigate using the tree above.**

---

*Last updated: 2025-12-06 by Claude*
*Tests: 912 total | Structure unified | Frontend: 164 | API Sim: 168 | Security: 86 | QA Tools: 27*
*Tools: 3/3 complete (XLSTransfer, QuickSearch + QA Tools, KR Similar)*
*MASTER NAVIGATION HUB - All tools unified under server/tools/*
