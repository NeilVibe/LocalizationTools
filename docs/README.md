# Documentation Index

**Last Updated**: 2025-12-05 | **Total Docs**: 35+

This is the **MASTER INDEX** for all LocaNext documentation.

---

## 🗺️ DOCUMENTATION TREE

```
docs/
═══════════════════════════════════════════════════════════════════════════════
│
├── 📍 README.md ────────────────── THIS FILE (Master Index)
│
├─────────────────────────────────────────────────────────────────────────────
│   🚀 GETTING STARTED
├─────────────────────────────────────────────────────────────────────────────
│   │
│   ├── QUICK_START_GUIDE.md ────── How to run servers, tests (5 min)
│   ├── PROJECT_STRUCTURE.md ────── Complete file tree, modules
│   └── ADMIN_SETUP.md ──────────── Initial admin user setup
│
├─────────────────────────────────────────────────────────────────────────────
│   🏗️ ARCHITECTURE (docs/architecture/)
├─────────────────────────────────────────────────────────────────────────────
│   │
│   ├── architecture/README.md ──── Architecture index
│   ├── architecture/PLATFORM_PATTERN.md ── Multi-tool platform
│   ├── architecture/BACKEND_PRINCIPLES.md ── "Backend is Flawless"
│   ├── architecture/ASYNC_PATTERNS.md ──── Async/await, WebSocket
│   └── DEPLOYMENT_ARCHITECTURE.md ──────── Hybrid SQLite/PostgreSQL
│
├─────────────────────────────────────────────────────────────────────────────
│   🧪 TESTING & DEBUGGING (docs/testing/)
├─────────────────────────────────────────────────────────────────────────────
│   │
│   ├── testing/DEBUG_AND_TEST_HUB.md ── 🎯 MASTER GUIDE (Start Here!)
│   ├── testing/README.md ───────────── Testing hub navigation
│   ├── testing/QUICK_COMMANDS.md ───── Copy-paste commands
│   ├── testing/PYTEST_GUIDE.md ─────── Python backend tests
│   ├── testing/PLAYWRIGHT_GUIDE.md ─── Frontend E2E tests
│   ├── testing/X_SERVER_SETUP.md ───── VcXsrv visual testing
│   ├── testing/TOOLS_REFERENCE.md ──── xdotool, ffmpeg, etc.
│   │
│   ├── WINDOWS_TROUBLESHOOTING.md ──── CDP, Windows EXE from WSL
│   ├── ELECTRON_TROUBLESHOOTING.md ─── Black screen, preload fixes
│   └── TESTING_GUIDE.md ────────────── General testing overview
│
├─────────────────────────────────────────────────────────────────────────────
│   📦 BUILD & DISTRIBUTION
├─────────────────────────────────────────────────────────────────────────────
│   │
│   ├── BUILD_AND_DISTRIBUTION.md ──── Versioning, builds, Git LFS
│   ├── BUILD_TROUBLESHOOTING.md ───── Failed builds, GitHub Actions
│   ├── BUILD_CHECKLIST.md ─────────── Pre-release checklist
│   └── PACKAGING_GUIDE.md ─────────── Electron packaging
│
├─────────────────────────────────────────────────────────────────────────────
│   🌐 DEPLOYMENT & OPERATIONS
├─────────────────────────────────────────────────────────────────────────────
│   │
│   ├── DEPLOYMENT.md ──────────────── Production deployment
│   ├── ENTERPRISE_DEPLOYMENT.md ───── Enterprise-scale
│   ├── POSTGRESQL_SETUP.md ────────── PostgreSQL config
│   ├── GITEA_SETUP.md ─────────────── Self-hosted Git + CI/CD (P13)
│   └── MONITORING_COMPLETE_GUIDE.md ─ Log monitoring system
│
├─────────────────────────────────────────────────────────────────────────────
│   🔒 SECURITY
├─────────────────────────────────────────────────────────────────────────────
│   │
│   ├── SECURITY_HARDENING.md ──────── Full security guide (86 tests)
│   ├── SECURITY_AND_LOGGING.md ────── Security best practices
│   └── LOGGING_PROTOCOL.md ────────── How to log properly
│
├─────────────────────────────────────────────────────────────────────────────
│   📝 DEVELOPMENT GUIDES
├─────────────────────────────────────────────────────────────────────────────
│   │
│   ├── CODING_STANDARDS.md ────────── Rules, patterns, conventions
│   ├── ADD_NEW_APP_GUIDE.md ───────── Add new tools (XLSTransfer template)
│   ├── BEST_PRACTICES.md ──────────── Best practices collection
│   └── PERFORMANCE.md ─────────────── Performance optimization
│
├─────────────────────────────────────────────────────────────────────────────
│   🎯 TOOL-SPECIFIC
├─────────────────────────────────────────────────────────────────────────────
│   │
│   ├── XLSTRANSFER_GUIDE.md ───────── XLSTransfer complete reference
│   ├── XLSTransfer_Migration_Audit.md ── Migration audit (13 sections)
│   └── STATS_DASHBOARD_SPEC.md ────── Admin dashboard specs
│
├─────────────────────────────────────────────────────────────────────────────
│   🤖 CLAUDE AI
├─────────────────────────────────────────────────────────────────────────────
│   │
│   └── CLAUDE_AI_WARNINGS.md ──────── Hallucination prevention
│
└─────────────────────────────────────────────────────────────────────────────
    📋 ARCHIVE (docs/archive/)
─────────────────────────────────────────────────────────────────────────────
    │
    └── Historical docs (superseded, for reference only)

═══════════════════════════════════════════════════════════════════════════════
```

---

## ⚡ Quick Navigation

| I want to... | Go to... |
|--------------|----------|
| Get started quickly | [QUICK_START_GUIDE.md](QUICK_START_GUIDE.md) |
| Run tests | [testing/DEBUG_AND_TEST_HUB.md](testing/DEBUG_AND_TEST_HUB.md) |
| Debug Windows EXE | [WINDOWS_TROUBLESHOOTING.md](WINDOWS_TROUBLESHOOTING.md) |
| Add a new tool | [ADD_NEW_APP_GUIDE.md](ADD_NEW_APP_GUIDE.md) |
| Build the app | [BUILD_AND_DISTRIBUTION.md](BUILD_AND_DISTRIBUTION.md) |
| Deploy to production | [DEPLOYMENT.md](DEPLOYMENT.md) |
| Set up security | [SECURITY_HARDENING.md](SECURITY_HARDENING.md) |
| Understand architecture | [architecture/README.md](architecture/README.md) |

---

## 📊 Documentation Stats

| Category | Files | Primary Entry Point |
|----------|-------|---------------------|
| Getting Started | 3 | QUICK_START_GUIDE.md |
| Architecture | 5 | architecture/README.md |
| Testing & Debugging | 10 | testing/DEBUG_AND_TEST_HUB.md |
| Build & Distribution | 4 | BUILD_AND_DISTRIBUTION.md |
| Deployment | 5 | DEPLOYMENT.md |
| Security | 3 | SECURITY_HARDENING.md |
| Development | 4 | CODING_STANDARDS.md |
| Tool-Specific | 3 | XLSTRANSFER_GUIDE.md |
| Claude AI | 1 | CLAUDE_AI_WARNINGS.md |
| **Total** | **38+** | |

---

## 🔗 Key Entry Points

1. **CLAUDE.md** (project root) - Master navigation hub for Claude AI
2. **Roadmap.md** (project root) - Development plan and priorities
3. **docs/README.md** (this file) - Documentation master index
4. **docs/testing/DEBUG_AND_TEST_HUB.md** - All testing capabilities

---

*For the main project hub, see [CLAUDE.md](../CLAUDE.md)*
