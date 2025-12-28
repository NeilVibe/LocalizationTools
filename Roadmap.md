# LocaNext - Roadmap

> Strategic priorities and architecture. Fast-moving session info in [SESSION_CONTEXT.md](docs/wip/SESSION_CONTEXT.md).

---

## Component Status

| Component | Status |
|-----------|--------|
| LDM (Language Data Manager) | WORKS |
| XLS Transfer | WORKS |
| Quick Search | WORKS |
| KR Similar | WORKS |
| CI/CD (Gitea + GitHub) | WORKS |

---

## CI/CD Build Modes

### Strategy (2025-12-23)

**DEV mode is DEAD.** Workers technology made full test suite so fast that we now run ALL 1000+ tests on every build. No more skipping tests.

| What Changed | Before | After |
|--------------|--------|-------|
| **Default mode** | DEV (skip tests) | QA (all tests) |
| **Test time** | "Too slow" | Fast (workers) |
| **Modes** | DEV, QA, TROUBLESHOOT | QA, QA FULL, TROUBLESHOOT |

### Build Modes

| Mode | Tests | Installer | Platform |
|------|-------|-----------|----------|
| `QA` | **ALL 1000+** | ~150MB | Both (default) |
| `QA FULL` | **ALL 1000+** | ~2GB+ | Gitea only |
| `TROUBLESHOOT` | Resume | Debug | Both |

### Platform Summary

| Platform | Default | Offline | Notes |
|----------|---------|---------|-------|
| **GitHub** | QA | N/A | LFS limits prevent offline bundle |
| **Gitea** | QA | QA FULL | Self-hosted, no limits |

### QA FULL Mode

**GITEA ONLY. Never GitHub.** Too complicated + LFS bandwidth limits.

For TRUE OFFLINE deployments:
- Bundles Qwen model (2.3GB)
- All Python deps pre-installed
- VC++ Redistributable included
- **Zero internet required on user PC**

### Implementation Status

| Mode | Status | Platform |
|------|--------|----------|
| `QA` | ✅ DONE | Both |
| `QA FULL` | ✅ DONE | Gitea only |
| `TROUBLESHOOT` | ✅ DONE | Both |

---

## Code Coverage (P36)

**Current:** 47% → **Target:** 70% | **Measured:** 2025-12-22

### LDM Routes Coverage (NEW MOCKED TESTS!)

| Route | Coverage | Status |
|-------|----------|--------|
| projects.py | **98%** | ✅ DONE |
| folders.py | **90%** | ✅ DONE |
| tm_entries.py | **74%** | ✅ GOOD |
| tm_crud.py | 46% | OK |
| tm_search.py | 46% | OK |

### Test Counts (Build 848)

| Stage | Tests |
|-------|-------|
| Unit Tests | 801 |
| Integration | 198 |
| E2E | 97 |
| API | 131 |
| Security | 86 |
| Fixtures | 74 |
| Performance | 12 |
| **Total** | **1,399** |

**What's done:** Core CRUD routes fully mocked (68-98% coverage)
**What's fine:** Complex routes tested via 145+ E2E tests

---

## Code Quality (P37)

**Status: COMPLETE** - No active monoliths in codebase

### What Was Done
- `api.py` (3156 lines) → **DELETED** (dead code after route migration)
- `tm_indexer.py` (2105 lines) → **SPLIT** into 4 modular files

### LDM Structure Now
```
server/tools/ldm/
├── router.py              # 68 lines - aggregates 44 endpoints
├── routes/                # 14 files - API endpoints
├── schemas/               # 10 files - Pydantic models
├── indexing/              # 5 files - FAISS/Vector (was tm_indexer.py)
└── tm_manager.py          # 1133 lines - well-organized (not monolith)
```

### Global Audit Results
All large files (>500 lines) are well-organized, not true monoliths.

---

## CI/CD

| Platform | Tests | Status |
|----------|-------|--------|
| **Gitea (Linux)** | 1,399 | ✅ Build 848 |
| **Gitea (Windows)** | TBD | 🔄 PATH tests needed |
| **GitHub** | 1,399 | ✅ Synced |

### Windows PATH Tests (CRITICAL)

**Why:** All tests run on Linux. Windows-specific path bugs slip through.

| Test Category | Description | Status |
|---------------|-------------|--------|
| Download Path | File downloads go to correct location | Pending |
| Upload Path | File uploads work from Windows paths | Pending |
| Model Path | Qwen/embeddings load from AppData | Pending |
| PKL Path | Index files save/load correctly | Pending |
| Embeddings Path | Vector indexes stored properly | Pending |
| Install Path | App installs to Program Files | Pending |
| Merge Path | Merged files export to correct location | Pending (P3) |

**Implementation:** Add to `build-windows` job in CI workflow.

### Build Strategy

| Platform | Default | Offline |
|----------|---------|---------|
| **GitHub** | QA (~150MB) | N/A (LFS limits) |
| **Gitea** | QA (~150MB) | QA FULL (~1.2GB) ✅ |

---

## Architecture: Embedding Engines

**Important:** Different tools use different engines for good reasons.

| Tool | Engine | Why |
|------|--------|-----|
| **LDM TM Search** | Model2Vec (default) / Qwen (opt-in) | Real-time needs speed |
| **LDM Standard Pretranslation** | Model2Vec / Qwen (user choice) | Follows user toggle |
| **KR Similar Pretranslation** | **Qwen ONLY** | Quality > speed |
| **XLS Transfer Pretranslation** | **Qwen ONLY** | Quality > speed |

### Model2Vec: `potion-multilingual-128M`

| Metric | Value |
|--------|-------|
| Languages | **101** (including Korean) |
| Speed | **29,269 sentences/sec** |
| Dimension | 256 |
| License | MIT |

> The Fast/Deep toggle affects LDM TM search AND standard pretranslation.
> KR Similar / XLS Transfer pretranslation ALWAYS use Qwen.

---

## Current Priorities

| Priority | Feature | Effort | WIP Doc |
|----------|---------|--------|---------|
| **P1** | Auto-LQA System | High | [AUTO_LQA_IMPLEMENTATION.md](docs/wip/AUTO_LQA_IMPLEMENTATION.md) |
| **P2** | LanguageTool (Spelling/Grammar) | High | [LANGUAGETOOL_IMPLEMENTATION.md](docs/wip/LANGUAGETOOL_IMPLEMENTATION.md) |

### P1: Auto-LQA System
- **LIVE Mode:** Auto-check on cell confirm (like "Use TM" toggle)
- **Full File QA:** Right-click → Run QA → QA Menu report
- **Checks:** Line, Term, Pattern, Character (all from `qa_tools.py`)
- **Features:** QA flags on cells, row filtering, Edit Modal QA panel
- **Battle-test with CDP E2E before adding LanguageTool**

---

## LDM Absorption Status

**Goal:** LDM absorbs ALL features → Legacy apps become redundant → Single unified LocaNext

### Absorption Tracker

| Legacy App | Feature | LDM Status | Notes |
|------------|---------|------------|-------|
| **XLS Transfer** | Dictionary/TM creation | ✅ ABSORBED | TM Management |
| **XLS Transfer** | Pretranslation | ✅ ABSORBED | Works in LDM |
| **XLS Transfer** | Excel import/export | ✅ ABSORBED | File parsing |
| **Quick Search** | Glossary extraction | ✅ ABSORBED | Context menu |
| **Quick Search** | Line Check | ✅ ABSORBED | Auto-LQA P2 |
| **Quick Search** | Term Check | 🔄 P5 | LanguageTool |
| **Quick Search** | Pattern Check | ✅ ABSORBED | Auto-LQA P2 |
| **Quick Search** | Character Check | ✅ ABSORBED | Auto-LQA P2 |
| **KR Similar** | Similarity search | ✅ ABSORBED | TM search |
| **KR Similar** | Pretranslation | ✅ ABSORBED | Deep mode |
| **All** | Spelling/Grammar | 🔄 P2 | LanguageTool |

### Remaining Features (After P1/P2)

| Feature | Source | Priority |
|---------|--------|----------|
| Character Limit Extract | `characterlimit.py` | Future |
| XML → Excel | `tmxtransfer11.py` | Future |
| Excel → XML | `tmxtransfer11.py` | Future |
| Excel ↔ TMX | `tmxtransfer11.py` | Future |
| Merge File | New | Future |

### End State Vision

```
CURRENT (4 apps):
├── LDM ─────────── Main app (growing)
├── XLS Transfer ── Standalone
├── Quick Search ── Standalone
└── KR Similar ──── Standalone

AFTER P1/P2 (transition):
├── LocaNext LDM ── All features absorbed
└── Legacy Menu ─── Button to access old UIs (deprecation period)

FINAL (1 app):
└── LocaNext ────── Single unified app (legacy menu removed)
```

### Tech Debt: LDM Independence

LDM currently imports from legacy apps (violates Rule #0):

| File | Bad Import | Fix |
|------|------------|-----|
| `pretranslate.py` | `xlstransfer/`, `kr_similar/` | Move to `server/utils/` |
| `tm.py` | `kr_similar/` | Move to `server/utils/` |

**Status:** Will fix during P1 implementation

---

## Current Priorities

| Priority | Feature | Description | Status |
|----------|---------|-------------|--------|
| **P1** | Factorization | Move shared code to `server/utils/`, LDM independence | ✅ DONE |
| **P2** | Auto-LQA System | LIVE QA + per-file QA + QA Menu | ✅ DONE |
| **P3** | MERGE System | Right-click → Merge confirmed cells to main LanguageData | ✅ DONE |
| **P4** | File Conversions | Right-click → Convert (XML↔Excel, Excel→TMX, etc.) | ✅ DONE |
| **P5** | LanguageTool | Spelling/Grammar via central server | ✅ DONE |
| **Future** | UIUX Overhaul | Legacy Apps menu, single LocaNext | - |

### P1: Factorization (LDM Independence) ✅ COMPLETE
- Moved shared code to `server/utils/` (qa_helpers.py, code_patterns.py)
- LDM no longer imports from legacy apps
- 785 tests passed after migration

### P2: Auto-LQA System ✅ COMPLETE (2025-12-25)
- **Backend:** LDMQAResult model, 7 API endpoints, 17 unit tests
- **LIVE Mode:** "QA On/Off" toggle → auto-check on cell confirm
- **QA Menu:** Slide-out panel with summary cards + issue list
- **Features:** QA flags on cells, row filtering dropdown, Edit Modal QA panel
- **Checks:** Pattern (code), Character (symbol count), Line (inconsistency)

### P3: MERGE System ✅ COMPLETE (2025-12-26)
- **Backend:** `POST /api/ldm/files/{file_id}/merge` endpoint
- **Frontend:** Right-click → "Merge to LanguageData..." context menu
- **Logic:** Match by StringID + Source → EDIT (update target) or ADD (append new)
- **Formats:** TXT and XML supported (Excel has no StringID)
- **Result:** User downloads merged file, commits to SVN/Perforce manually
- **Future:** Perforce API integration to create changelist directly

### P4: File Conversions ✅ COMPLETE (2025-12-26)
- **Backend:** `GET /api/ldm/files/{file_id}/convert?format=xlsx|xml|txt|tmx`
- **Frontend:** Right-click → "Convert to..." submenu with format options
- **Supported:** TXT→Excel/XML/TMX, XML→Excel/TMX, Excel→XML/TMX
- **NOT supported:** XML/Excel→TXT (StringID loss)

### P5: LanguageTool ✅ COMPLETE (2025-12-26)
- **Server:** LanguageTool 6.6 on 172.28.150.120:8081 (systemd auto-start)
- **Backend:** `/api/ldm/grammar/status`, `/files/{id}/check-grammar`, `/rows/{id}/check-grammar`
- **Frontend:** Right-click → "Check Spelling/Grammar" context menu
- **Modal:** Loading spinner, summary stats, error list with suggestions
- **Performance:** ~43ms/row, 937MB RAM, minimal CPU
- **Languages:** 30+ supported (EN, DE, FR, ES, etc. - Korean NOT supported)

---

## Future Ideas (Backlog)

### Perforce API Integration
**Context:** Game company uses SVN and Perforce for version control.
- SVN: No API, manual commit after merge (nothing we can do)
- Perforce: Has API, could create changelist directly after merge

**Potential Flow:**
```
1. User merges confirmed cells to LanguageData (P3)
2. User clicks "Submit to Perforce"
3. LocaNext calls Perforce API
4. Changelist created automatically
5. User reviews and submits in P4V
```

**Status:** Future consideration after P3 (MERGE) is working

### Other Future Features
- Character Limit Extract (from `characterlimit.py`)
- Batch operations on multiple files

---

## Current Priorities (NEW)

| Priority | Feature | WIP Doc | Status |
|----------|---------|---------|--------|
| **P1** | QA UIUX Overhaul | [QA_UIUX_OVERHAUL.md](docs/wip/QA_UIUX_OVERHAUL.md) | PLANNING |
| **P2** | Font Settings Enhancement | [FONT_SETTINGS_ENHANCEMENT.md](docs/wip/FONT_SETTINGS_ENHANCEMENT.md) | PLANNING |
| **P2** | Gitea Clean Kill Protocol | [GITEA_CLEAN_KILL_PROTOCOL.md](docs/wip/GITEA_CLEAN_KILL_PROTOCOL.md) | IMPLEMENTED |
| **P3** | Offline/Online Mode | [OFFLINE_ONLINE_MODE.md](docs/wip/OFFLINE_ONLINE_MODE.md) | PLANNING |
| **P4** | Color Parser Extension | [COLOR_PARSER_EXTENSION.md](docs/wip/COLOR_PARSER_EXTENSION.md) | DOCUMENTED |
| **P5** | Advanced Search | [ADVANCED_SEARCH.md](docs/wip/ADVANCED_SEARCH.md) | PLANNING |
| **P6** | File Delete + Recycle Bin | TBD | BACKLOG |

### P1: QA UIUX Overhaul
**CRITICAL** - Current QA panel has stability issues:
- Softlock / can't close panel
- Empty results with "issues found" message
- No cancel mechanism for "Run Full QA"
- No timeout for API requests

### P2: Font Settings Enhancement
Add missing font customization:
- Font Family: System, Inter, Roboto, Noto Sans, Source Han (CJK), Consolas, Monaco
- Font Color: Default, Black, Dark Gray, Blue, Green
- Settings dropdown menu instead of direct modal

### P2: Gitea Clean Kill Protocol ✅ IMPLEMENTED
Prevent zombie processes and stuck builds:
- `./scripts/gitea_control.sh` - unified management script
- Commands: `status`, `stop`, `kill`, `start`, `restart`, `monitor`
- Fixed 52% idle CPU issue with simple restart
- Proper systemd + daemon management

### P3: Offline/Online Mode (COMPLEX)
Work offline when central server unavailable:
- Local SQLite for changes while offline
- Auto-sync and merge when reconnecting
- Conflict resolution (reviewed rows protected)
- Merge modes: Full (add + edit) vs Edit-only

### P4: Color Parser Extension
Current parser supports PAColor format only. Document how to add:
- `{Color(#hex)}text{/Color}` format
- `<color=name>text</color>` format
- Auto-detection of format per file

### P5: Advanced Search
Add search mode options: Contain, Exact, Not Contain, Fuzzy (Model2Vec semantic)
- Search by: StringID, Source, Target (extensible for future metadata)

### P6: File Delete + Recycle Bin
- Right-click → Delete file
- Deleted files go to "Bin" (soft delete)
- Bin view to recover or permanently delete

---

## Quick Navigation

| Need | Go To |
|------|-------|
| **Session state** | [SESSION_CONTEXT.md](docs/wip/SESSION_CONTEXT.md) |
| **Open bugs** | [ISSUES_TO_FIX.md](docs/wip/ISSUES_TO_FIX.md) |
| **CI/CD docs** | [docs/cicd/CI_CD_HUB.md](docs/cicd/CI_CD_HUB.md) |
| **CDP Testing** | [testing_toolkit/cdp/README.md](testing_toolkit/cdp/README.md) |
| **Enterprise** | [docs/enterprise/HUB.md](docs/enterprise/HUB.md) |

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

ONLINE:  PostgreSQL (multi-user, WebSocket sync)
OFFLINE: SQLite (single-user, auto-fallback)
```

---

## Quick Commands

```bash
# Check servers
./scripts/check_servers.sh

# Check release/tag sync
./scripts/check_releases_status.sh

# Start backend
python3 server/main.py

# Desktop app
cd locaNext && npm run electron:dev

# Playground INSTALL (fresh install only - use UPDATE for existing app!)
# See CLAUDE.md "INSTALL vs UPDATE" section for when to use each
./scripts/playground_install.sh --launch --auto-login

# Trigger builds
echo "Build" >> GITEA_TRIGGER.txt && git add -A && git commit -m "Build" && git push origin main && git push gitea main
```

---

## Key URLs

| Service | URL |
|---------|-----|
| Backend API | http://localhost:8888 |
| Gitea | http://172.28.150.120:3000 |
| CDP | http://127.0.0.1:9222 |

---

*Strategic Roadmap | Updated 2025-12-28 | Build 415 STABLE | P1-P5 Complete, NEW priorities added*
