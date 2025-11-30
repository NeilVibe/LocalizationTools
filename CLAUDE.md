# CLAUDE.md - LocaNext Master Navigation Hub

**Version:** 2512011200 (2025-12-01)
**Status:** Backend ✅ | Frontend ✅ | Database ✅ | WebSocket ✅ | TaskManager ✅ | XLSTransfer ✅ | QuickSearch ✅ | KR Similar ✅ | Distribution ✅

---

## 🎯 PROJECT OVERVIEW

**LocaNext** (formerly LocalizationTools) is a **professional desktop platform** that consolidates localization/translation Python scripts into one unified Electron application.

### Key Features:
- 🏢 **Platform approach**: Host 10-20+ tools in one app
- 💻 **Local processing**: Runs on user's CPU, works offline
- 📊 **Central monitoring**: Optional telemetry to server
- 👔 **Professional**: CEO/management-ready quality

### Current Status (2025-11-30):
- ✅ **Backend**: 100% Complete (47+ endpoints, WebSocket, async)
- ✅ **LocaNext Desktop App**: 100% Complete (Electron + Svelte)
- ✅ **XLSTransfer (App #1)**: 100% Complete (10 functions, exact replica)
- ✅ **QuickSearch (App #2)**: 100% Complete (dictionary search with reference)
- ✅ **KR Similar (App #3)**: 100% Complete (Korean semantic similarity, 34 tests)
- ✅ **Distribution**: Git LFS, versioning, build system ready
- ⏳ **Admin Dashboard**: 85% Complete (needs auth & polish)

---

## 📚 DOCUMENTATION TREE (START HERE!)

### 🚀 Getting Started

| Document | What It Covers |
|----------|----------------|
| **[QUICK_START_GUIDE.md](docs/QUICK_START_GUIDE.md)** | How to run servers, tests, common commands (5 min) |
| **[PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md)** | Complete file tree, module organization |
| **Roadmap.md** | Development plan, next steps, progress tracking |

### 🏗️ Architecture & Design

| Document | What It Covers |
|----------|----------------|
| **[DEPLOYMENT_ARCHITECTURE.md](docs/DEPLOYMENT_ARCHITECTURE.md)** | Hybrid model (SQLite + PostgreSQL), 3 applications |
| **[PLATFORM_PATTERN.md](docs/architecture/PLATFORM_PATTERN.md)** | Multi-tool platform approach, scalability |
| **[BACKEND_PRINCIPLES.md](docs/architecture/BACKEND_PRINCIPLES.md)** | "Backend is Flawless" rule, wrapper pattern |
| **[ASYNC_PATTERNS.md](docs/architecture/ASYNC_PATTERNS.md)** | Async/await, WebSocket, real-time updates |

### 🛠️ Development Guides

| Document | What It Covers |
|----------|----------------|
| **[CODING_STANDARDS.md](docs/CODING_STANDARDS.md)** | Rules, patterns, conventions, common pitfalls |
| **[ADD_NEW_APP_GUIDE.md](docs/ADD_NEW_APP_GUIDE.md)** | How to add new tools (XLSTransfer as template) |
| **[TESTING_GUIDE.md](docs/TESTING_GUIDE.md)** | User testing procedures, manual workflow |
| **[TESTING_PROTOCOL.md](docs/TESTING_PROTOCOL.md)** | **FULL autonomous testing with server, API, everything** |
| **[LOGGING_PROTOCOL.md](docs/LOGGING_PROTOCOL.md)** | Comprehensive logging requirements (MANDATORY!) |
| **[MONITORING_COMPLETE_GUIDE.md](docs/MONITORING_COMPLETE_GUIDE.md)** | Monitoring system, real-time logs |

### 📦 Build & Distribution

| Document | What It Covers |
|----------|----------------|
| **[BUILD_AND_DISTRIBUTION.md](docs/BUILD_AND_DISTRIBUTION.md)** | Versioning, manual builds, Git LFS, troubleshooting |
| **[BUILD_TROUBLESHOOTING.md](docs/BUILD_TROUBLESHOOTING.md)** | Debugging failed builds, GitHub Actions |
| **[BUILD_CHECKLIST.md](docs/BUILD_CHECKLIST.md)** | Pre-release checklist |
| **[PACKAGING_GUIDE.md](docs/PACKAGING_GUIDE.md)** | Electron packaging details |

### 🌐 Deployment & Operations

| Document | What It Covers |
|----------|----------------|
| **[DEPLOYMENT.md](docs/DEPLOYMENT.md)** | Production deployment procedures |
| **[ENTERPRISE_DEPLOYMENT.md](docs/ENTERPRISE_DEPLOYMENT.md)** | Enterprise-scale deployment |
| **[POSTGRESQL_SETUP.md](docs/POSTGRESQL_SETUP.md)** | PostgreSQL configuration |
| **[SECURITY_AND_LOGGING.md](docs/SECURITY_AND_LOGGING.md)** | Security best practices |

### 🔒 Security

| Document | What It Covers |
|----------|----------------|
| **[SECURITY_HARDENING.md](docs/SECURITY_HARDENING.md)** | **Production security checklist: CORS, TLS, rate limiting, JWT** |
| **[.env.example](.env.example)** | Production environment configuration template |

### 🤖 Claude AI Guides (READ THESE!)

| Document | What It Covers |
|----------|----------------|
| **[CLAUDE_AUTONOMOUS_TESTING.md](docs/CLAUDE_AUTONOMOUS_TESTING.md)** | **X Server, headless browser, work alone without asking user** |
| **[CLAUDE_AI_WARNINGS.md](docs/CLAUDE_AI_WARNINGS.md)** | AI hallucination prevention (5 documented types) |

### 🎯 Tool-Specific Guides

| Document | What It Covers |
|----------|----------------|
| **[XLSTRANSFER_GUIDE.md](docs/XLSTRANSFER_GUIDE.md)** | XLSTransfer complete reference (dual-mode, API, GUI) |
| **[XLSTransfer_Migration_Audit.md](docs/XLSTransfer_Migration_Audit.md)** | Complete 13-section audit |

### 📖 Reference

| Document | What It Covers |
|----------|----------------|
| **[BEST_PRACTICES.md](docs/BEST_PRACTICES.md)** | Best practices collection |
| **[PERFORMANCE.md](docs/PERFORMANCE.md)** | Performance optimization |
| **[QUICK_TEST_COMMANDS.md](docs/QUICK_TEST_COMMANDS.md)** | Terminal testing commands |
| **[STATS_DASHBOARD_SPEC.md](docs/STATS_DASHBOARD_SPEC.md)** | Admin dashboard specifications |

---

## 🚨 CRITICAL RULES (READ FIRST!)

### 1. Backend is Flawless
- **NEVER** modify backend core code without explicit permission
- Only create wrapper layers (API endpoints, GUI)
- See: [BACKEND_PRINCIPLES.md](docs/architecture/BACKEND_PRINCIPLES.md)

### 2. Logging is Mandatory
- **LOG EVERYTHING** at every step
- Use `logger`, NEVER use `print()`
- See: [LOGGING_PROTOCOL.md](docs/LOGGING_PROTOCOL.md)

### 3. Version Management
- **ALWAYS** run `python3 scripts/check_version_unified.py` before commit
- Builds are **MANUAL** (not automatic on every push)
- See: [BUILD_AND_DISTRIBUTION.md](docs/BUILD_AND_DISTRIBUTION.md)

### 4. Testing Required
- Run `pytest` before every commit
- For FULL tests: `RUN_API_TESTS=1 pytest` (requires server running)
- See: [TESTING_PROTOCOL.md](docs/TESTING_PROTOCOL.md) for autonomous testing

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

# Trigger build (when ready)
echo "Build FULL v$NEW_VERSION" >> BUILD_TRIGGER.txt
git add BUILD_TRIGGER.txt && git commit -m "Trigger build v$NEW_VERSION"
git push origin main
```

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
2. ✅ Read [QUICK_START_GUIDE.md](docs/QUICK_START_GUIDE.md) (5 min)
3. ✅ Run `python3 server/main.py` to verify backend works
4. ✅ Run `python3 -m pytest` to verify tests pass (160 expected)
5. ✅ Check **Roadmap.md** for current task

### Current Phase:
- **Phase 3:** Admin Dashboard (85% complete)
- See Roadmap.md for detailed plan

### Questions to Ask User:
- "Shall we finish the Admin Dashboard?"
- "Want to test XLSTransfer in Electron app?"
- "Should we add another tool to LocaNext?"

---

## 📊 PROJECT STATS

- **Lines of Code:** ~18,000+
- **API Endpoints:** 47+ (async + sync)
- **Database Tables:** 13
- **Tests:** 188+ (63 E2E app tests + 39 infrastructure + 86 utility)
- **Tools:** 3 (XLSTransfer, QuickSearch, KR Similar)
- **Documentation Files:** 38+ (25 active + 13 archived)

---

## 🎉 YOU'RE READY!

This project is **96% complete**, **clean**, **organized**, and **production-ready**.

**Everything is documented. Navigate using the tree above.** 🚀

---

*Last updated: 2025-12-01 by Claude*
*MASTER NAVIGATION HUB - All details are in linked docs*
