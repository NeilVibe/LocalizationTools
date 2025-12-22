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

### The 4 Modes

| Mode | Tests | Installer | Use Case |
|------|-------|-----------|----------|
| `LIGHT` | Essential (~285) | ~150MB | Daily dev + releases |
| `FULL` | Essential (~285) | ~2GB+ | **TRUE OFFLINE** - zero internet |
| `QA-LIGHT` | **ALL 1500+** | ~150MB | Pre-release verification |
| `QA-FULL` | **ALL 1500+** | ~2GB+ | **PRISTINE** offline release |

### LIGHT vs FULL

| | LIGHT | FULL |
|--|-------|------|
| Installer | ~150MB | ~2GB+ |
| First launch | Downloads deps | Ready immediately |
| Internet | Yes (first run) | **NO - zero internet** |

**FULL bundles EVERYTHING:** All Python deps, Qwen model, Model2Vec, VC++ Redistributable

### QA Modes

**QA = Same build, PRISTINE validation first** - All 1500+ tests must pass before creating installer

### Implementation Status

| Mode | Status |
|------|--------|
| `LIGHT` | ✅ DONE (current) |
| `FULL` | TODO |
| `QA-LIGHT` | ✅ DONE (Build 342 testing) |
| `QA-FULL` | TODO |
| `TROUBLESHOOT` | ✅ DONE (debug mode) |

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

### Test Counts

| Category | Count |
|----------|-------|
| LDM Mocked Tests | 27 |
| LDM Unit Tests | 89 |
| Total Unit Tests | 737 |

**What's done:** Core CRUD routes fully mocked
**What's fine:** Complex routes (file upload, FAISS) tested via integration

**Details:** [P36_COVERAGE_GAPS.md](docs/wip/P36_COVERAGE_GAPS.md)

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

**Details:** [P37_LDM_REFACTORING.md](docs/wip/P37_LDM_REFACTORING.md)

---

## CI/CD

| Platform | Tests | Notes |
|----------|-------|-------|
| **Gitea** | ~285 essential | Fast daily builds |
| **GitHub** | 830+ full suite | Comprehensive |

### Build Modes

| Mode | Tests | Installer |
|------|-------|-----------|
| `LIGHT` | Essential | ~150MB ✅ |
| `FULL` | Essential | ~2GB (offline) |
| `TROUBLESHOOT` | Resume from failure | Debug mode ✅ |

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

## Future Vision: LDM as Mother App

**Goal:** Progressively merge monolith features into LDM (Svelte 5).

```
Current:
├── LDM ─────────── Main app (growing)
├── XLS Transfer ── Standalone tool
├── Quick Search ── Standalone tool
└── KR Similar ──── Standalone tool

Future:
├── LDM ─────────── Mother app (all features)
│   ├── TM Management (done)
│   ├── Pretranslation (done)
│   ├── QA Checks (done)
│   ├── Glossary Extraction (done)
│   └── ... more monolith features
│
└── Legacy Menu ─── Access to standalone tools
```

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

# Playground install
./scripts/playground_install.sh --launch --auto-login

# Trigger builds
echo "Build LIGHT" >> GITEA_TRIGGER.txt   # Gitea
echo "Build LIGHT" >> BUILD_TRIGGER.txt   # GitHub
git add -A && git commit -m "Build" && git push origin main && git push gitea main
```

---

## Key URLs

| Service | URL |
|---------|-----|
| Backend API | http://localhost:8888 |
| Gitea | http://172.28.150.120:3000 |
| CDP | http://127.0.0.1:9222 |

---

*Strategic Roadmap | Updated 2025-12-22*
