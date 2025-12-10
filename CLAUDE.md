# CLAUDE.md - LocaNext Master Navigation Hub

**Version:** 2512101440 (2025-12-10)
**Status:** Backend ✅ | Frontend ✅ | Database ✅ | WebSocket ✅ | TaskManager ✅ | XLSTransfer ✅ | QuickSearch ✅ | KR Similar ✅ | **LDM (App #4)** 🔄 62% | Distribution ✅ | Security ✅ | Tests ✅ | Structure ✅ | Health Check ✅ | Telemetry ✅ | Testing Toolkit ✅ | **Migration VERIFIED** ✅ | **CI/CD COMPLETE** ✅ | **Smart Cache v2.0** ✅ | **DB Opt P18** ✅ | **TM API** ✅ | **P21 DB Powerhouse** ✅

---

## 🌟 THIS FILE IS THE HUB

```
                    ┌─────────────────────────────────────────────┐
                    │          CLAUDE.md = THE HUB               │
                    │  (Central Navigation + Quick Reference)     │
                    └────────────────────┬────────────────────────┘
                                         │
         ┌───────────┬───────────┬───────┴───────┬───────────┬───────────┐
         ▼           ▼           ▼               ▼           ▼           ▼
    ┌─────────┐ ┌─────────┐ ┌─────────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
    │Roadmap  │ │ docs/   │ │ docs/wip/   │ │ server/ │ │locaNext/│ │ tests/  │
    │.md      │ │         │ │             │ │         │ │         │ │         │
    │(GLOBAL) │ │(GUIDES) │ │(GRANULAR)   │ │(CODE)   │ │(APP)    │ │(VERIFY) │
    └─────────┘ └─────────┘ └─────────────┘ └─────────┘ └─────────┘ └─────────┘
        │           │             │
        │           │             └── P17_LDM_TASKS.md (128 tasks)
        │           │                 P17_TM_ARCHITECTURE.md (54 tasks)
        │           │                 P13_GITEA_CACHE_PLAN.md
        │           │
        │           └── architecture/, build/, deployment/, security/, testing/
        │
        └── High-level priorities + completion status

    NAVIGATION PATTERN:
    1. CLAUDE.md → Find what you need (tables link to docs)
    2. Roadmap.md → See global priorities + status
    3. docs/wip/*.md → Dive into detailed task lists
```

---

## 📖 GLOSSARY (Quick Reference)

| Term | Full Name | What It Is |
|------|-----------|------------|
| **RM** | Roadmap | `Roadmap.md` - GLOBAL view of all priorities, concise status |
| **WIP** | Work In Progress | `docs/wip/*.md` - DETAILED task breakdowns per priority |
| **LDM** | Language Data Manager | CAT tool (App #4) - edit TXT/XML translation files |
| **TM** | Translation Memory | Database of source→target pairs for suggestions |
| **CAT** | Computer-Assisted Translation | Software that helps translators work faster |
| **FAISS** | Facebook AI Similarity Search | Vector index for fast semantic search |
| **CDP** | Chrome DevTools Protocol | Remote debugging for Electron apps |
| **WSL** | Windows Subsystem for Linux | Run Linux on Windows |

### RM vs WIP: The Two-Level System

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    WHY TWO LEVELS? CLARITY + FOCUS                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  RM (Roadmap.md)                      WIP (docs/wip/*.md)                   │
│  ══════════════                       ═══════════════════                   │
│  • GLOBAL overview                    • GRANULAR details                    │
│  • All priorities listed              • ONE priority per file               │
│  • "P17 LDM: 59%"                     • "128 tasks with [x] checkboxes"     │
│  • Read in 2 minutes                  • Read when working on that task      │
│  • Updated AFTER phase complete       • Updated DURING work                 │
│  • CEO/PM readable                    • Developer working doc               │
│                                                                             │
│  ANALOGY:                                                                   │
│  RM = Table of Contents               WIP = Individual Chapters             │
│  RM = City Map                        WIP = Building Blueprints             │
│  RM = "We're building a house"        WIP = "Nail specs, wire gauges..."    │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  RULE: RM stays CONCISE. Details go in WIP. Never bloat RM with tasks.      │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Document Structure:**
- **RM (Roadmap.md)** = "What are we building?" (high-level, status overview)
- **WIP (docs/wip/*.md)** = "How exactly?" (136 tasks with checkboxes)
- **CLAUDE.md** = "Where do I find it?" (HUB with links to everything)

---

## 🎯 PROJECT OVERVIEW

**LocaNext** (formerly LocalizationTools) is a **professional desktop platform** that consolidates localization/translation Python scripts into one unified Electron application.

### Key Features:
- 🏢 **Platform approach**: Host 10-20+ tools in one app
- 💻 **Local processing**: Runs on user's CPU, works offline
- 📊 **Central monitoring**: Optional telemetry to server
- 👔 **Professional**: CEO/management-ready quality

### Current Status (2025-12-09):
- ✅ **Backend**: 100% Complete (63+ endpoints, WebSocket, async)
- ✅ **LocaNext Desktop App**: 100% Complete (Electron + Svelte)
- ✅ **XLSTransfer (App #1)**: VERIFIED - 10/10 tests with real Excel files
- ✅ **QuickSearch (App #2)**: VERIFIED - 8/8 tests with TXT + XML files
- ✅ **KR Similar (App #3)**: VERIFIED - 10/10 tests with 41,715 pairs
- 🔄 **LDM (App #4)**: 60% Complete - CAT tool with 5-Tier TM System
  - Phase 1-5: ✅ Core Complete (Foundation, FileExplorer, Sync, VirtualGrid, Basic TM)
  - Phase 6.0-6.1: ✅ Cell Display (dynamic heights, ↵ newlines, hover, TM pre-fetch)
  - Phase 7: 📋 **Full TM System** (5-Tier Cascade + Dual Threshold) ← NEXT
  - Phase 8: 📋 LocaNext Nice View (pattern rendering)
  - **Docs:** `docs/tools/LDM_TEXT_SEARCH.md`, `docs/wip/P17_LDM_TASKS.md`
  - Performance: 16MB/103,500 rows in ~50 seconds
- ✅ **Migration**: ALL 33 monolith functions verified with production test files
- ✅ **Distribution**: Git LFS, versioning, build system ready
- ✅ **Security**: 7/11 Complete (IP filter, CORS, JWT, audit logging, 86 tests)
- ✅ **Tests**: 912 passed (TRUE simulation - no mocks!)
- ✅ **Structure**: Unified - all tools under `server/tools/` (Priority 6.0 complete)
- ✅ **Admin Dashboard**: 100% Complete (Overview, Users, Stats, Logs, Telemetry)
- ✅ **Health Check**: Priority 11.0 - Auto-repair system complete
- ✅ **Telemetry**: Priority 12.5.9 COMPLETE - Server + Client + Dashboard + Tool Tracking
- ✅ **CI/CD P13.11**: COMPLETE - GitHub + Gitea BOTH WORKING with patched act_runner v15

---

## 📋 DOCUMENTATION WORKFLOW

### Roadmap vs WIP Structure

```
Roadmap.md (ROOT)                    docs/wip/*.md (DETAILED)
────────────────────                 ────────────────────────
• GLOBAL view                        • DETAILED task breakdown
• Shows all priorities               • Per-priority implementation
• Quick status overview              • Step-by-step tasks
• Links to WIP docs                  • Technical specs
• Updated after completion           • Updated DURING work

EXAMPLE:
Roadmap.md says:                     docs/wip/P17_LDM_TASKS.md has:
"P17: LDM 56% Complete"              128 tasks with checkboxes
                                     Priority order
                                     Architecture diagrams
```

### When to Update What

| Action | Update Roadmap.md | Update WIP Doc |
|--------|-------------------|----------------|
| Start new priority | Add section | Create new WIP file |
| Complete a task | No | Mark [x] in WIP |
| Complete a phase | Update % | Mark phase ✅ |
| Priority fully done | Move to "Completed" | Archive or delete |

### File Naming Convention
```
docs/wip/
├── P13_GITEA_CACHE_PLAN.md    # P{priority}_{short_name}.md
├── P17_LDM_TASKS.md           # Task tracker for P17
└── P17_TM_ARCHITECTURE.md     # Architecture doc for P17 TM system
```

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
├── demos/                       # Demo screenshots & videos
│   ├── ldm/                     # LDM workflow (11 screenshots)
│   ├── xlstransfer/             # XLSTransfer demos
│   ├── quicksearch/             # QuickSearch demos
│   ├── krsimilar/               # KR Similar demos
│   └── general/                 # Platform-wide demos
├── wip/                         # Work in Progress
│   └── P17_LDM_TASKS.md         # LDM task tracking (65/68 tasks)
└── deprecated/                  # Outdated docs
```

### 🚀 Getting Started

| Document | Path |
|----------|------|
| **Executive Summary** | `docs/EXECUTIVE_SUMMARY.md` ← **FOR BOSS/MANAGEMENT** |
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

#### 🚀 Build → Release → Update Flow

```
BUILD TRIGGER         →    BUILD             →    RELEASE           →    APP UPDATE
─────────────────────      ───────────────        ──────────────         ───────────────
Add line to trigger   →    CI/CD builds     →    GitHub: AUTO     →    App checks
file + git push            installer + yml       Gitea: AUTO            latest.yml
                                                                        on startup
```

**Release Status:**
| Platform | Build | Release | App Auto-Update |
|----------|-------|---------|-----------------|
| GitHub | ✅ Auto | ✅ Auto (softprops/action-gh-release) | ✅ Works |
| Gitea | ✅ Auto | ✅ Auto (API + upload in build job) | ✅ Works |

**App Update Source (configured via env):**
```javascript
// locaNext/electron/updater.js
UPDATE_SERVER=github  // Default - uses GitHub Releases
UPDATE_SERVER=gitea   // Company - uses Gitea Releases
UPDATE_SERVER=http://... // Custom server
```

**Patch Notes:** Currently template-based (version + tools list). For detailed changelog, add to GITEA_TRIGGER.txt comment or update workflow body.

#### 🔧 App Self-Repair & Health Check System

The desktop app has a comprehensive **auto-repair system** that runs on every launch:

```
APP LAUNCH → HEALTH CHECK → REPAIR IF NEEDED → MAIN APP
     │             │                │
     │             ▼                ▼
     │      ┌─────────────┐   ┌──────────────────┐
     │      │Quick Check: │   │Auto Repair:      │
     │      │• Python exe │   │• Reinstall deps  │
     │      │• Server     │   │• Download model  │
     │      │• Model      │   │• Verify install  │
     │      │• Packages   │   │• Progress UI     │
     │      └─────────────┘   └──────────────────┘
```

**Files:**
| File | Purpose |
|------|---------|
| `locaNext/electron/health-check.js` | Checks Python, packages, model, server on startup |
| `locaNext/electron/repair.js` | Auto-repairs with progress UI (deps, model) |
| `locaNext/electron/first-run-setup.js` | First-time installation with progress |
| `locaNext/electron/updater.js` | Auto-updates from GitHub/Gitea/custom |

**Health Status Flow:**
- `OK` → Launch main app normally
- `NEEDS_REPAIR` → Run auto-repair, then launch
- `CRITICAL_FAILURE` → Show error, cannot continue

**Repair Prevention:** Tracks `last_repair.json` to prevent repair loops (max once per hour).

### 🌐 Deployment & Operations

| Document | What It Covers |
|----------|----------------|
| **[DEPLOYMENT.md](docs/deployment/DEPLOYMENT.md)** | Production deployment procedures |
| **[DEPLOYMENT_ARCHITECTURE.md](docs/deployment/DEPLOYMENT_ARCHITECTURE.md)** | Quad Entity architecture |
| **[ADMIN_SETUP.md](docs/getting-started/ADMIN_SETUP.md)** | Initial admin user setup, credentials |
| **[POSTGRESQL_SETUP.md](docs/deployment/POSTGRESQL_SETUP.md)** | PostgreSQL configuration |
| **[GITEA_SETUP.md](docs/deployment/GITEA_SETUP.md)** | Self-hosted Git + CI/CD setup |
| **[WINDOWS_RUNNER_SETUP.md](docs/deployment/WINDOWS_RUNNER_SETUP.md)** | **Windows CI/CD runner (Git, NSSM, Service)** |
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
| **[LDM_GUIDE.md](docs/tools/LDM_GUIDE.md)** | LDM (LanguageData Manager) - CAT tool for translation files |
| **[MONOLITH_DEVIATIONS.md](docs/tools/MONOLITH_DEVIATIONS.md)** | Migration audit status |

### 📖 Reference

| Document | What It Covers |
|----------|----------------|
| **[BEST_PRACTICES.md](docs/development/BEST_PRACTICES.md)** | Best practices collection |
| **[PERFORMANCE.md](docs/development/PERFORMANCE.md)** | Performance optimization |
| **[STATS_DASHBOARD_SPEC.md](docs/deprecated/STATS_DASHBOARD_SPEC.md)** | Admin dashboard specifications |

---

## 🤖 CLAUDE PERSONALITY SETTINGS

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    MANDATORY BEHAVIOR FOR CLAUDE                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   1. BE FRANK, NOT AGREEABLE                                                │
│      ════════════════════════                                               │
│      • NEVER give biased answers that lean toward what user wants to hear   │
│      • If an idea is bad, SAY IT'S BAD with clear reasons                   │
│      • If an idea works, say it works - but don't oversell                  │
│      • User's feelings < Technical correctness                              │
│                                                                             │
│   2. COLD, HONEST OPINIONS                                                  │
│      ═══════════════════════                                                │
│      • No sugarcoating, no "great idea!" when it's mediocre                 │
│      • Give the real tradeoffs, not just the positives                      │
│      • If something is overkill, say "overkill"                             │
│      • If something is risky, say "risky"                                   │
│                                                                             │
│   3. RECOMMEND OPTIMAL SOLUTIONS                                            │
│      ═══════════════════════════                                            │
│      • Always lead with the MOST RECOMMENDED approach                       │
│      • Explain WHY it's recommended (cost, complexity, reliability)         │
│      • Present alternatives with honest pros/cons                           │
│      • Don't let user enthusiasm override good engineering                  │
│                                                                             │
│   4. SAY "THIS DOESN'T WORK" WHEN IT DOESN'T                                │
│      ════════════════════════════════════════                               │
│      • If user proposes something that won't work, immediately say so       │
│      • Don't try to "make it work" just to please                           │
│      • Offer what WILL work instead                                         │
│                                                                             │
│   EXAMPLE:                                                                  │
│   User: "What if we store 100TB in RAM?"                                    │
│   BAD:  "That's an interesting approach! We could look into..."             │
│   GOOD: "That won't work. 100TB RAM costs $5M+. Use tiered storage instead."│
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

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
  - ✅ Workflow: `.gitea/workflows/build.yml` (test → build → release)
  - ✅ Runner: Patched v15 (NUL byte fix) + Ephemeral mode
  - ✅ DUAL PUSH: `git push origin main && git push gitea main`
- **Priority 13.12:** Smart Build Cache v2.0 ✅ COMPLETE
  - ✅ Hash-based invalidation (`requirements.txt` hash auto-refresh)
  - ✅ Version tracking (Python/VC++ version changes auto-invalidate)
  - ✅ Build #307 verified: ALL CACHE HITS
  - ✅ Performance: ~1.5 min (vs ~3 min without cache)
  - **Docs:** `docs/wip/P13_GITEA_CACHE_PLAN.md`
- **P18: Database Optimization:** 🔄 Phase 1 COMPLETE
  - ✅ Batch inserts (`bulk_insert_tm_entries`, `bulk_insert_rows`)
  - ✅ Full-Text Search (FTS) with PostgreSQL tsvector
  - ✅ GIN trigram indexes for similarity search
  - 📋 Async DB, Redis caching (future)
  - **WIP:** `docs/wip/P_DB_OPTIMIZATION.md`
- **Testing Toolkit:** ✅ COMPLETE
  - ✅ CDP-based autonomous testing (`testing_toolkit/`)
  - ✅ All 3 apps have TEST MODE (xlsTransfer, quickSearch, krSimilar)
  - ✅ ADD_TEST_MODE_GUIDE.md for future apps (LD Manager template)
- **P17: LDM (LanguageData Manager):** 🔄 IN PROGRESS (60% - 81/136 tasks)
  - ✅ **Phase 1-4:** Foundation + Grid + Sync + Virtual Scroll (58/58 tasks)
  - ✅ **Phase 5.1-5.4:** Basic TM + Panel + Keyboard Shortcuts (7/10 tasks)
  - ✅ **Phase 6.0-6.1:** Cell Display - dynamic heights, newlines, hover (7/16 tasks)
  - 🎯 **NEXT: Phase 7.1-7.2** - TM Database + Upload (10 tasks) ← START HERE
  - 📋 **Phase 7.3-7.5:** Index Building + Cascade Search + API (22 tasks)
  - 📋 **Phase 5.5:** Glossary integration (3 tasks)
  - 📋 **Phase 8:** Nice View - Pattern rendering (12 tasks)
  - **Task File:** `docs/wip/P17_LDM_TASKS.md` - Full breakdown with priority order
  - **Demo:** 11 screenshots in `docs/demos/ldm/`
  - **Performance:** 103K rows in 50 sec
- **P21: Database Powerhouse:** ✅ COMPLETE (2025-12-10)
  - ✅ COPY TEXT for bulk uploads (31K entries/sec)
  - ✅ PgBouncer 1.16 on port 6433 (1000 connections)
  - ✅ PostgreSQL tuned (8GB shared_buffers, 24GB cache)
  - ✅ Performance indexes on all LDM tables
  - **WIP:** `docs/wip/P21_DATABASE_POWERHOUSE.md`

### Quick Gitea Commands:
```bash
cd ~/gitea && ./start.sh   # Start Gitea → http://localhost:3000
cd ~/gitea && ./stop.sh    # Stop Gitea
```

### Quick DB Commands:
```bash
# Check PgBouncer status
pgrep -a pgbouncer

# Connect through PgBouncer
PGPASSWORD='locanext_dev_2025' psql -h 127.0.0.1 -p 6433 -U localization_admin -d localizationtools

# Restart PgBouncer (if needed)
sudo killall pgbouncer; sudo -u postgres pgbouncer -d /etc/pgbouncer/pgbouncer.ini
```

### Questions to Ask User:
- "Continue P17 LDM? Remaining: Phase 7-8 (TM System + Nice View)"
- "Continue P17 LDM? Remaining: Glossary integration + Phase 6 Polish"
- "Add 'Save + Add to TM' button in cell edit?" - Simple glossary feature discussed

### Context from Last Session (2025-12-10):
**P21 Database Powerhouse - Phase 1 COMPLETE:**
```
✅ COPY TEXT implementation (bulk_copy, bulk_copy_tm_entries, bulk_copy_rows)
✅ PostgreSQL 14.20 configured and running
✅ Credentials: .env auto-loading with python-dotenv
✅ Benchmark: 15-24K entries/sec (both INSERT and COPY TEXT)
✅ 1M rows = ~60 seconds
```

**Async vs Sync Verdict:**
```
Sync SQLAlchemy = BETTER for 100 users
- Simpler code, easier maintenance
- Database is the bottleneck, not Python's concurrency
- Async only helps at 500+ concurrent connections
```

**Technology Stack (Industry Standard):**
```
✅ PostgreSQL 14.20 - Used by Instagram, Spotify, Reddit
✅ Connection pooling - 10 pool, 20 overflow
✅ Batch/COPY inserts - 15-24K entries/sec
📋 PgBouncer - Phase 3 (for 1000+ connections)
```

**DB Sizing:**
```
100 users × 1M rows = 100M rows = 20GB data
Recommended: 8 cores, 32GB RAM, 1TB NVMe (~$100-150/month)
```

### Windows Environment (C: Drive - SSD):
```
C:\NEIL_PROJECTS_WINDOWSBUILD\
├── LocaNextProject\
│   ├── LocaNext\                    # Installed app (playground/testing)
│   │   ├── LocaNext.exe             # Main executable
│   │   ├── server/                  # Backend
│   │   ├── tools/                   # Python tools
│   │   └── logs/                    # App logs
│   └── TestFilesForLocaNext\        # Test files
│       ├── *.xlsx                   # Excel test files
│       ├── *.txt                    # Text test files
│       └── sample_localization.xml  # XML test file (for QuickSearch/LD Manager)
│
└── GiteaRunner\                     # Windows act_runner (P13.11)
    ├── act_runner.exe               # Runner binary
    └── _work\                       # Build workspace
```

**WSL Access:**
```bash
# LocaNext App
/mnt/c/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/LocaNext/

# Test Files
/mnt/c/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/TestFilesForLocaNext/

# Launch app with CDP
cd /mnt/c/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/LocaNext && ./LocaNext.exe --remote-debugging-port=9222 &
```

- See **[WINDOWS_TROUBLESHOOTING.md](docs/troubleshooting/WINDOWS_TROUBLESHOOTING.md)** for WSL debugging commands

---

## 📊 PROJECT STATS

- **Lines of Code:** ~19,000+
- **API Endpoints:** 63+ (async + sync, includes 8 admin telemetry + 8 TM CRUD)
- **Database Tables:** 17 (13 core + 4 telemetry)
- **Tests:** 912 total (TRUE simulation - no mocks!)
- **E2E Tests:** 115 (KR Similar 18 + QuickSearch 11 + XLSTransfer 9 + Edge Cases 23 + Workflows 54)
- **Frontend E2E:** 164 (Playwright - LocaNext 134 + Admin Dashboard 30)
  - LocaNext 134: Login 10 + Nav 10 + Tools 11 + API 8 + Frontend-Backend 16 + Full Workflow 17 + TaskManager 22 + File Operations 20 + WebSocket/Real-time 19 + Screenshot 1
  - Admin Dashboard 30: Dashboard 15 + Telemetry 15
- **Unit Tests:** 377+ (auth, cache, websocket, dependencies, tools, QA Tools 27)
- **API Simulation Tests:** 168 (Tools 26 + Admin 15 + Errors 25 + WebSocket 10 + Full System 72)
- **Security Tests:** 86 (IP filter, CORS, JWT, audit logging)
- **Tools:** 4 (XLSTransfer, QuickSearch, KR Similar, LDM) - all under `server/tools/`, 14/14 CDP tests passed
- **Demo Screenshots:** 11 LDM workflow images in `docs/demos/ldm/`
- **Documentation Files:** 30 active + 9 archived (updated WINDOWS_TROUBLESHOOTING.md)

---

## 🎉 YOU'RE READY!

This project is **97% complete**, **clean**, **organized**, and **production-ready**.

**Everything is documented. Navigate using the tree above.**

---

*Last updated: 2025-12-09 by Claude*
*Tests: 912 total | Structure unified | Frontend: 164 | API Sim: 168 | Security: 86 | QA Tools: 27*
*Tools: 4 (XLSTransfer, QuickSearch + QA Tools, KR Similar, LDM 56%)*
*P17 LDM: Phase 6 in progress - Cell display, Glossary remaining*
*Demo: 11 screenshots in docs/demos/ldm/ | Performance: 103K rows in 50 sec*
*MASTER NAVIGATION HUB - All paths documented | Self-Repair ✅ | Auto-Update ✅*
