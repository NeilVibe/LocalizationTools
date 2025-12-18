# Session Context - Claude Handoff Document

**Last Updated:** 2025-12-18 | **Build:** 299 (pending CI)

---

## Current State

| Item | Status |
|------|--------|
| Build | **299 pushed, waiting for CI** |
| Open Bugs | **0** |
| Code Complete | **5** (PERF-001, PERF-002, FEAT-005, BUG-023, Model2Vec upgrade) |
| Playground | Has Build 298 (needs refresh after CI) |

---

## NEXT SESSION: Refresh Playground

1. **Wait for CI to build** - Check http://172.28.150.120:3000/neilvibe/LocaNext/actions
2. **Once new release exists**, run: `./scripts/playground_install.sh --launch --auto-login`
3. **Test BUG-023 fix** - TM status should show "ready" not "pending"

---

## Build 299 Changes (Pushed, Pending CI)

- **BUG-023 FIX:** `MODEL_NAME` undefined → `self._engine.name` in `tm_indexer.py`
- **Model2Vec Upgrade:** `potion-base-8M` → `potion-multilingual-128M` (101 languages, Korean support)
- **Docs Updated:** All WIP docs clarify engine usage by tool

---

## Recently Completed (This Session)

### FEAT-005: Model2Vec Default Engine - ✅ COMPLETE

**What:** Model2Vec (79x faster) as default embedding engine with UI toggle.

**Files Created:**
- `server/tools/shared/embedding_engine.py` - Engine abstraction
- API endpoints: `/api/ldm/settings/embedding-engine*`

**Files Modified:**
- `server/tools/shared/__init__.py` - Exports
- `server/tools/ldm/api.py` - API endpoints
- `server/tools/ldm/tm_indexer.py` - Uses EmbeddingEngine
- `locaNext/src/lib/components/ldm/TMManager.svelte` - UI toggle

**UI:** TM Manager toolbar has Fast/Deep toggle for engine switching.

---

### PERF-001: Incremental HNSW - ✅ TESTED

**What:** Add entries without full rebuild (~5x faster)

**Test Results:**
- Build 10k index: 5.9s
- Incremental add 100 vectors: 1.25s vs 6.3s full rebuild = **5x faster**

---

### PERF-002: FAISS Factorization - ✅ TESTED

**What:** 12 FAISS copies → 1 `FAISSManager` class

**Test Results:**
- All 3 tools import cleanly
- All FAISS operations work correctly

---

## Completed (Build 298)

| ID | Description | Status |
|----|-------------|--------|
| **FEAT-005** | Model2Vec default engine + UI toggle | ✅ Complete |
| **PERF-001** | Incremental HNSW | ✅ Tested |
| **PERF-002** | FAISS factorization | ✅ Tested |
| BUG-027 | TM Viewer UI/UX overhaul | ✅ Tested |
| FEAT-004 | TM Sync Protocol | ✅ Tested |
| BUG-024 | File Viewer empty 3rd column | ✅ Fixed |
| BUG-025 | Title not clickable | ✅ Fixed |
| BUG-026 | User button shows "User" | ✅ Fixed |

---

## Architecture

### Embedding Engine Usage by Tool

| Tool | Engine | Why |
|------|--------|-----|
| **LDM TM Search** | Model2Vec (default) / Qwen (opt-in) | Real-time needs speed |
| **LDM Standard Pretranslation** | Model2Vec / Qwen (user choice) | Follows user toggle |
| **KR Similar Pretranslation** | **Qwen ONLY** | Quality > speed |
| **XLS Transfer Pretranslation** | **Qwen ONLY** | Quality > speed |

### Model2Vec Model: `potion-multilingual-128M`

| Metric | Value |
|--------|-------|
| Languages | **101** (including Korean) |
| Speed | **29,269 sentences/sec** |
| Dimension | 256 |
| License | MIT |

```
┌─────────────────────────────────────────────────────────────────┐
│  LDM TM Search Pipeline (Model2Vec/Qwen Selectable)              │
│                                                                  │
│  1. EXACT MATCH (hash) ← instant                                │
│  2. CONTAINS (substring) ← fast                                  │
│  3. SEMANTIC (Model2Vec + FAISS HNSW) ← DEFAULT                 │
│     └── potion-multilingual-128M (Korean support)               │
│     └── 29,269 texts/sec                                        │
│     └── <1ms/query search                                       │
│                                                                  │
│  4. SEMANTIC DEEP (Qwen + FAISS) ← opt-in via UI                │
│     └── Toggle: TM Manager → "Deep" button                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Quick Commands

```bash
# Check servers
./scripts/check_servers.sh

# Start backend
python3 server/main.py

# Desktop app
cd locaNext && npm run electron:dev

# Playground install
./scripts/playground_install.sh --launch --auto-login
```

---

## Playground

```
Current:  v25.1217.2220 (Build 298) ← NEEDS REFRESH
Pending:  Build 299 (waiting for CI)
Path:     C:\NEIL_PROJECTS_WINDOWSBUILD\LocaNextProject\Playground\LocaNext
Mode:     ONLINE (PostgreSQL)
Login:    neil/neil
```

---

*This document is the source of truth for session handoff.*
