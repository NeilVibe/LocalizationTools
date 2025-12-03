# LocaNext - Development Roadmap

**Version**: 2512010029 | **Updated**: 2025-12-03 | **Status**: Production Ready

---

## 🌳 STATUS TREE

```
LocaNext Platform
├── ✅ Backend (100%) ─────────── FastAPI, 39 endpoints, async
├── ✅ Frontend (100%) ────────── SvelteKit + Carbon Design
├── ✅ Admin Dashboard (100%) ─── Stats, Users, Logs
├── ✅ Security (7/11) ────────── IP filter, CORS, JWT, audit
├── ✅ Tests (1049) ───────────── 53% coverage, TRUE simulation
│
├── Apps
│   ├── ✅ XLSTransfer ────────── Excel translation + Korean BERT
│   ├── ✅ QuickSearch ────────── Dictionary search (15 langs)
│   └── ✅ KR Similar ─────────── Korean semantic similarity
│
├── Distribution
│   ├── ✅ Electron Desktop ───── Windows .exe, Linux AppImage
│   ├── ✅ LIGHT Build ────────── Post-install model download
│   └── ✅ Version Unified ────── 8 files synced
│
├── ✅ 5.7 Analytics ─────────── Team/language stats
├── ✅ 5.8 DB Backup ──────────── Claude-assisted backups
├── ✅ 4.1 Settings Menu ──────── About + Preferences modals
│
└── 🎉 ALL ROADMAP ITEMS COMPLETE!
```

---

## 📊 Test Summary

| Category | Tests | Status |
|----------|-------|--------|
| Security | 86 | ✅ IP, CORS, JWT, audit |
| E2E Apps | 115 | ✅ All 3 tools |
| API Simulation | 168 | ✅ TRUE sim (no mocks) |
| Unit Tests | 350+ | ✅ Server + client |
| Frontend E2E | 164 | ✅ Playwright |
| **Total** | **1049** | **53% coverage** |

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

## 📋 What's Next

### Priority 6.0: Project Structure Unification 🔴 IN PROGRESS

**Problem:** XLSTransfer is in `client/tools/` while QuickSearch and KR Similar are in `server/tools/`. This creates confusion and inconsistent imports.

**Goal:** All tools in `server/tools/` with consistent import pattern.

#### Current (INCONSISTENT):
```
client/tools/xls_transfer/     ← XLSTransfer (WRONG PLACE)
server/tools/quicksearch/      ← QuickSearch
server/tools/kr_similar/       ← KR Similar
```

#### Target (CONSISTENT):
```
server/tools/
├── xlstransfer/               ← XLSTransfer (MOVED)
├── quicksearch/               ← QuickSearch
└── kr_similar/                ← KR Similar
```

#### What Gets Moved:

**1. XLSTransfer Backend (3,683 lines - NO CHANGES TO LOGIC):**
```
client/tools/xls_transfer/  →  server/tools/xlstransfer/
├── core.py              (13KB, 49 functions)
├── embeddings.py        (16KB, BERT+FAISS)
├── translation.py       (12KB, matching logic)
├── process_operation.py (27KB, 5 operations)
├── excel_utils.py       (15KB)
├── progress_tracker.py  (7KB)
├── config.py            (7KB)
├── get_sheets.py
├── load_dictionary.py
├── translate_file.py
├── simple_transfer.py
├── __init__.py
├── README.md
└── cli/
    ├── xlstransfer_cli.py  (8.7KB - CLI entry point)
    └── xlstransfer.sh      (shell wrapper)
```

**2. Client Utilities:**
```
client/utils/  →  server/utils/client/
├── file_handler.py
├── logger.py
└── progress.py
```

**3. Client Config:**
```
client/config.py  →  server/config/client_config.py
```

#### Files to Update (Import Changes Only):

| File | Changes |
|------|---------|
| **Server API** | |
| `server/api/xlstransfer_async.py` | `from client.tools.xls_transfer` → `from server.tools.xlstransfer` |
| **XLSTransfer Internal (after move)** | |
| `server/tools/xlstransfer/core.py` | `from client.tools.xls_transfer` → `from server.tools.xlstransfer` |
| `server/tools/xlstransfer/translation.py` | Update imports |
| `server/tools/xlstransfer/embeddings.py` | Update imports |
| `server/tools/xlstransfer/excel_utils.py` | Update imports |
| `server/tools/xlstransfer/__init__.py` | Update imports |
| `server/tools/xlstransfer/cli/xlstransfer_cli.py` | Update imports |
| **E2E Tests** | |
| `tests/e2e/test_xlstransfer_e2e.py` | Import path |
| `tests/e2e/test_full_simulation.py` | Import path |
| `tests/e2e/test_production_workflows_e2e.py` | Import path |
| `tests/e2e/test_edge_cases_e2e.py` | Import path |
| `tests/e2e/test_complete_user_flow.py` | CLI path update |
| **Unit Tests** | |
| `tests/unit/test_xlstransfer_modules.py` | Import path |
| `tests/unit/test_code_patterns.py` | Import path |
| `tests/unit/client/test_utils_progress.py` | `from client.utils` → `from server.utils.client` |
| `tests/unit/client/test_utils_file_handler.py` | `from client.utils` → `from server.utils.client` |
| `tests/unit/client/test_utils_logger.py` | `from client.utils` → `from server.utils.client` |
| **Config** | |
| `tests/conftest.py` | `client.config` → `server.config.client_config` |
| **Scripts** | |
| `scripts/profile_memory.py` | Import path |

#### What Gets Deleted:
```
client/data/                   ← 56MB old cache (GARBAGE)
client/ui/                     ← Empty folder
client/assets/                 ← Empty folder
client/models/                 ← Empty folder (real models in /models/)
client/__init__.py             ← Empty
client/                        ← ENTIRE FOLDER GONE
```

#### Execution Steps:
- [ ] 1. Commit current state (safety checkpoint)
- [ ] 2. Create `server/tools/xlstransfer/` folder
- [ ] 3. Copy all files from `client/tools/xls_transfer/`
- [ ] 4. Update internal imports in xlstransfer modules
- [ ] 5. Create `server/utils/client/` and move utils
- [ ] 6. Create `server/config/client_config.py`
- [ ] 7. Update `server/api/xlstransfer_async.py` imports
- [ ] 8. Update all test imports
- [ ] 9. Update `scripts/profile_memory.py`
- [ ] 10. Run full test suite - MUST PASS 100%
- [ ] 11. Delete `client/` folder
- [ ] 12. Update docs (BACKEND_PRINCIPLES.md, PROJECT_STRUCTURE.md, XLSTRANSFER_GUIDE.md)
- [ ] 13. Final commit

#### Docs to Update:
- `docs/architecture/BACKEND_PRINCIPLES.md` - Remove `client/tools/` references
- `docs/PROJECT_STRUCTURE.md` - Remove `client/` section, update tree
- `docs/XLSTRANSFER_GUIDE.md` - Update paths
- `CLAUDE.md` - Update if needed

---

### Priority 4.1: Settings Menu ✅ COMPLETE
```
Header [Settings ▼]
        ├── About... → Opens AboutModal
        │   └── Version, build date, update check button
        └── Preferences... → Opens PreferencesModal
            └── Theme toggle, language, notifications
```
- [x] SettingsDropdown component (header gear icon)
- [x] AboutModal (version info, check updates)
- [x] PreferencesModal (theme, language, notifications)

### Priority 5.7: Analytics Enhancement ✅ COMPLETE
- [x] Activity by team - `GET /api/v2/admin/stats/analytics/by-team`
- [x] Activity by language - `GET /api/v2/admin/stats/analytics/by-language`
- [x] User rankings with profile - `GET /api/v2/admin/stats/analytics/user-rankings`
- [x] Admin Dashboard Stats page updated with Team/Language/User cards

### Priority 5.8: Database Backup ✅ COMPLETE
- [x] `scripts/backup_db.py` - Create backup, list, status, cleanup
- [x] `scripts/restore_db.py` - Restore from backup (interactive or --latest)
- [x] Keep last 7 backups, auto-cleanup older ones
- [x] Backups stored in `server/data/backups/`

---

## ✅ Completed

### Platform Core
- ✅ FastAPI backend (39 endpoints)
- ✅ SvelteKit frontend + Electron
- ✅ Admin Dashboard (Overview, Users, Stats, Logs)
- ✅ SQLite + async SQLAlchemy
- ✅ WebSocket real-time progress
- ✅ JWT authentication

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
| `docs/SECURITY_HARDENING.md` | Security config |
| `docs/BUILD_AND_DISTRIBUTION.md` | Build process |

---

## 🔑 Key Principles

1. **Backend is Flawless** - Don't modify core without confirmed bug
2. **LIGHT-First Builds** - No bundled models
3. **TRUE Simulation Tests** - No mocks, real functions
4. **Version Unification** - 8 files must match

---

*Default login: admin / admin123*
*Ports: Backend 8888 | Frontend 5173 | Admin 5175*
