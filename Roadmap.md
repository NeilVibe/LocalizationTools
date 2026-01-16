# LocaNext Roadmap

> **Last Updated:** 2026-01-16 (Session 45) | **CI:** Gitea 455 ✅ GitHub 456 ✅

---

## Quick Status

| What | Status |
|------|--------|
| **Open Bugs** | **0** (127 fixed) |
| **CI/CD** | ✅ Both passing |
| **Tests** | ~1,400+ (all passing) |
| **Repository Pattern** | ✅ 100% complete |

---

## What Works NOW

| Component | Status | Notes |
|-----------|--------|-------|
| **LDM (CAT Tool)** | ✅ WORKS | Full TM, QA, Grid, Sync |
| **XLS Transfer** | ✅ WORKS | Pretranslation, Dictionary |
| **Quick Search** | ✅ WORKS | Dictionary, QA checks |
| **KR Similar** | ✅ WORKS | FAISS similarity search |
| **CI/CD** | ✅ WORKS | Gitea + GitHub, 7 stages |
| **Offline Mode** | ✅ WORKS | SQLite, full functionality |
| **Online Mode** | ✅ WORKS | PostgreSQL, multi-user |

---

## Architecture

```
LocaNext.exe (User PC)           Central PostgreSQL
├─ Electron + Svelte 5       →   ├─ All text data
├─ Embedded Python Backend       ├─ Users, sessions
├─ FAISS indexes (local)         ├─ LDM rows, TM entries
├─ Model2Vec (~128MB)            └─ Logs
├─ Qwen (2.3GB, opt-in)
└─ File parsing (local)

        FACTORY (Repository Pattern)
              /\
             /  \
            /    \
    PostgreSQL    SQLite
      Repo          Repo

ONLINE:  PostgreSQL (multi-user, WebSocket sync)
OFFLINE: SQLite (single-user, auto-fallback)
```

### Repository Pattern - VERIFIED ✅

**9 Repositories implemented, all routes migrated:**

| Repository | PostgreSQL | SQLite | Routes |
|------------|------------|--------|--------|
| TMRepository | ✅ | ✅ | tm_assignment, tm_crud, tm_entries, tm_indexes, tm_search, tm_linking |
| FileRepository | ✅ | ✅ | files.py, sync.py, pretranslate.py |
| RowRepository | ✅ | ✅ | rows.py, qa.py, grammar.py, tm_search.py |
| ProjectRepository | ✅ | ✅ | projects.py, sync.py |
| FolderRepository | ✅ | ✅ | folders.py, sync.py |
| PlatformRepository | ✅ | ✅ | platforms.py |
| QAResultRepository | ✅ | ✅ | qa.py |
| TrashRepository | ✅ | ✅ | trash.py |
| CapabilityRepository | ✅ | ✅ | capabilities.py |

### TM Operations - Both Modes ✅

| Operation | Repository | Offline | Online |
|-----------|------------|---------|--------|
| List TMs | ✅ `repo.get_all()` | ✅ | ✅ |
| Get/Delete TM | ✅ `repo.get/delete()` | ✅ | ✅ |
| **Get Entries** | ✅ `repo.get_entries()` | ✅ | ✅ |
| **Add Entry** | ✅ `repo.add_entry()` | ✅ | ✅ |
| **Update Entry** | ✅ `repo.update_entry()` | ✅ | ✅ |
| **Delete Entry** | ✅ `repo.delete_entry()` | ✅ | ✅ |
| **Confirm Entry** | ✅ `repo.confirm_entry()` | ✅ | ✅ |
| Upload TM (file) | ❌ TMManager | ❌ | ✅ |
| Export TM (file) | ❌ TMManager | ❌ | ✅ |

**Note:** Upload/Export use TMManager (complex file parsing) - Online only by design.

---

## Current Priorities

| Priority | Task | Status |
|----------|------|--------|
| **P11** | Platform Stability | **ACTIVE** |
| P10 | DB Abstraction Layer | ✅ COMPLETE |
| P9 | Launcher + Offline/Online | ✅ COMPLETE |
| P8 | Dashboard Overhaul | LOW PRIORITY |

### P11: Platform Stability (ACTIVE)

| Task | Status |
|------|--------|
| TM Tree Folder Mirroring | ✅ FIXED |
| P10 Permission Gap | ✅ FIXED |
| Playwright Tests | ✅ 154 passed |
| P10 CI Verification | ✅ Gitea 455, GitHub 456 |
| TM Repository Pattern | ✅ VERIFIED (Session 45) |
| Windows PATH Tests | TODO |

#### Windows PATH Tests (TODO)

| Test | Description |
|------|-------------|
| Download Path | File downloads go to correct location |
| Upload Path | File uploads work from Windows paths |
| Model Path | Qwen/embeddings load from AppData |
| PKL Path | Index files save/load correctly |
| Embeddings Path | Vector indexes stored properly |
| Install Path | App installs to Program Files |
| Merge Path | Merged files export to correct location |

### P8: Dashboard Overhaul (LOW PRIORITY)

**Status:** PLANNED | After platform stability

| Phase | Task |
|-------|------|
| 1 | Svelte 5 Upgrade |
| 2 | Capability Assignment UI |
| 3 | UI/UX Improvements |
| 4 | Database Changes |
| 5 | Translation Activity Logging |
| 6 | QA Usage Logging |
| 7 | Translation Stats Page |
| 8 | QA Analytics Page |
| 9 | Custom Report Builder |

---

## Test Coverage

| Stage | Tests |
|-------|-------|
| Unit Tests | 871 |
| Integration | 198 |
| E2E | 97 |
| API | 131 |
| Security | 86 |
| Fixtures | 74 |
| Performance | 12 |
| **Total** | **~1,400+** |

### Route Coverage

| Route | Coverage |
|-------|----------|
| projects.py | 98% |
| folders.py | 90% |
| tm_entries.py | 74% |
| tm_crud.py | 46% |
| tm_search.py | 46% |

---

## CI/CD

| Platform | Default | Tests | Build |
|----------|---------|-------|-------|
| **Gitea** | QA | 1,399 | 455 ✅ |
| **GitHub** | QA | 1,399 | 456 ✅ |

### Build Modes

| Mode | Tests | Installer | Platform |
|------|-------|-----------|----------|
| `QA` | ALL 1000+ | ~150MB | Both (default) |
| `QA FULL` | ALL 1000+ | ~2GB+ | Gitea only |
| `TROUBLESHOOT` | Resume | Debug | Both |

---

## TM Hierarchy System

```
File Explorer (structure owner)     TM Explorer (READ-ONLY mirror)
├── Platform: PC                    ├── [Unassigned] ← TM-only
│   └── Project: Game1              ├── Platform: PC
│       └── Folder: French          │   └── Project: Game1
│           └── file.txt            │       └── Folder: French
│                                   │           └── french.tm [ACTIVE]
```

### Key Rules

1. TM Explorer = READ-ONLY mirror of File Explorer structure
2. Never create folders in TM Explorer - only place/activate TMs
3. Unassigned exists ONLY in TM Explorer - safety net for orphaned TMs
4. Hierarchical activation - TM at folder level applies to all files in folder

### Implementation Status

| Sprint | Task | Status |
|--------|------|--------|
| 1 | Database: platforms table, tm_assignments | ✅ DONE |
| 2 | Backend: TM resolution logic | ✅ DONE |
| 3 | Frontend: TM Explorer GRID UI | ✅ DONE |
| 4 | Frontend: File viewer TM indicator + TM source in matches | ✅ DONE (Session 45) |
| 5 | Frontend: Platform management UI | PLANNED |

---

## Embedding Engines

| Tool | Engine | Why |
|------|--------|-----|
| **LDM TM Search** | Model2Vec (default) / Qwen (opt-in) | Speed for real-time |
| **LDM Pretranslation** | Model2Vec / Qwen (user choice) | User toggle |
| **KR Similar** | Qwen ONLY | Quality > speed |
| **XLS Transfer** | Qwen ONLY | Quality > speed |

### Model2Vec Stats

| Metric | Value |
|--------|-------|
| Languages | 101 (including Korean) |
| Speed | 29,269 sentences/sec |
| Dimension | 256 |
| License | MIT |

---

## Completed Milestones

<details>
<summary>P10: DB Abstraction Layer ✅</summary>

**Status:** COMPLETE | 65→7 direct DB calls, 20 routes clean, 9 repositories

| Phase | Status |
|-------|--------|
| Phase 1 | Documentation & Foundation ✅ |
| Phase 2 | Core Repositories (File, Row, Project) ✅ |
| Phase 3 | Hierarchy Repositories (Folder, Platform) ✅ |
| Phase 4 | Support Repositories (QA, Trash) ✅ |
| Phase 5 | Route Migration ✅ |
| Phase 5B | sync.py → SyncService ✅ |
| Phase 6 | Testing & Validation ✅ |

</details>

<details>
<summary>P9: Launcher + Offline/Online ✅</summary>

**Status:** COMPLETE | Build 453

- Beautiful game-launcher style first screen
- Mode switching (Offline ↔ Online)
- Auto-connect with fallback
- Manual sync (Right-click → Download/Sync)
- TM sync with last-write-wins

</details>

<details>
<summary>P3: Offline/Online Mode ✅</summary>

**Status:** COMPLETE | Build 447

| Phase | Status |
|-------|--------|
| Phase 1 | Basic offline viewing/editing ✅ |
| Phase 2 | Change tracking ✅ |
| Phase 3 | Sync engine ✅ |
| Phase 4 | Conflict resolution (last-write-wins) ✅ |
| Phase 5 | File path selection ✅ |
| Phase 6 | Polish & edge cases ✅ |

</details>

<details>
<summary>P1-P5: Core Features ✅</summary>

| Priority | Feature | Status |
|----------|---------|--------|
| P1 | Factorization (LDM Independence) | ✅ |
| P2 | Auto-LQA System | ✅ |
| P3 | MERGE System | ✅ |
| P4 | File Conversions | ✅ |
| P5 | LanguageTool Integration | ✅ |

</details>

<details>
<summary>UI Overhaul (Session 9) ✅</summary>

- UI-087: Dropdown position ✅
- UI-094: Remove TM button ✅
- UI-095: Remove QA buttons ✅
- UI-096: Reference file picker ✅
- UI-097: Consolidate Settings ✅

</details>

<details>
<summary>EXPLORER Features (Sessions 21-24) ✅</summary>

- EXPLORER-001: Ctrl+C/V/X clipboard ✅
- EXPLORER-002: Hierarchy validation ✅
- EXPLORER-003/006: Confirmation modals ✅
- EXPLORER-004: Explorer search ✅
- EXPLORER-005: Cross-project move ✅
- EXPLORER-007: Undo/Redo ✅
- EXPLORER-008: Recycle Bin ✅
- EXPLORER-009: Privileged operations ✅

</details>

<details>
<summary>DESIGN-001: Public Permissions ✅</summary>

- Public by default, optional restriction
- Globally unique names
- Access grants system
- Admin endpoints for restriction management

</details>

---

## Quick Reference

### Commands

```bash
# Check servers
./scripts/check_servers.sh

# Start backend
python3 server/main.py

# Desktop app
cd locaNext && npm run electron:dev

# Playground install
./scripts/playground_install.sh --launch --auto-login

# Trigger builds
echo "Build" >> GITEA_TRIGGER.txt && git add -A && git commit -m "Build" && git push origin main && git push gitea main
```

### URLs

| Service | URL |
|---------|-----|
| Backend API | http://localhost:8888 |
| Gitea | http://172.28.150.120:3000 |
| CDP | http://127.0.0.1:9222 |

### Navigation

| Need | Go To |
|------|-------|
| Session state | [SESSION_CONTEXT.md](docs/current/SESSION_CONTEXT.md) |
| Open bugs | [ISSUES_TO_FIX.md](docs/current/ISSUES_TO_FIX.md) |
| CI/CD docs | [docs/reference/cicd/](docs/reference/cicd/) |
| Architecture | [docs/architecture/](docs/architecture/) |

---

*Strategic Roadmap | Session 45 | All systems operational*
