# Session Context - Claude Handoff Document

**Last Updated:** 2025-12-18 | **Build:** 300 (Linux CI passed, Windows pending)

---

## Current State

| Item | Status |
|------|--------|
| Build | **300 Linux CI ✅ PASSED** (Windows build pending) |
| Open Bugs | **0** |
| Code Complete | **6** (PERF-001, PERF-002, FEAT-005, BUG-023, Model2Vec upgrade, Lazy Import Fix) |
| Playground | Has Build 298 (needs refresh after Windows build) |

---

## NEXT SESSION: Refresh Playground

1. **Check if Windows build completed** - Look for new release at http://172.28.150.120:3000/neilvibe/LocaNext/releases
2. **Once new release exists**, run: `./scripts/playground_install.sh --launch --auto-login`
3. **Test BUG-023 fix** - TM status should show "ready" not "pending"

---

## Build 300: Lazy Import Fix - ✅ LINUX CI PASSED

**Problem:** Build 299 failed - server startup exceeded 30s CI timeout.

**Root Cause:** `sentence_transformers` imported at module level in `kr_similar/embeddings.py`, taking 3-30s depending on environment.

**Fix:** Changed to lazy import pattern (TYPE_CHECKING + runtime import)

| Metric | Before | After |
|--------|--------|-------|
| `kr_similar_async` import | 2.99s | 0.01s |
| Total startup imports | ~4s | ~1s |
| CI Build | ❌ Timeout | ✅ Pass |

**Files Changed:**
- `server/tools/kr_similar/embeddings.py` - Lazy import pattern
- `docs/development/CODING_STANDARDS.md` - Documented as Pitfall #1

**Documentation:** This is a **recurring issue**. Now documented in CODING_STANDARDS.md with detection commands:
```bash
# Find eager imports (should return nothing)
grep -rn "^from sentence_transformers\|^import torch" server/ --include="*.py"
```

---

## Build 299: FAILED (CI Timeout)

**Issue:** Server startup exceeded 30s timeout in CI.
**Cause:** Eager import of `sentence_transformers` in `kr_similar/embeddings.py`
**Fixed in:** Build 300

---

## Recently Completed

### Lazy Import Fix (Build 300) - ✅ COMPLETE

**What:** Fixed CI timeout by making ML library imports lazy.

**Pattern Applied:**
```python
# Before (WRONG - blocks startup)
from sentence_transformers import SentenceTransformer
MODELS_AVAILABLE = True

# After (CORRECT - lazy import)
if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

def _check_models_available() -> bool:
    # Check lazily, cache result
    ...
```

---

### BUG-023: TM Status "Pending" - ✅ FIXED (Build 299)

**Culprit:** `MODEL_NAME` undefined in `tm_indexer.py` caused `NameError` during build.

**Fix:** Replaced with `self._engine.name`

---

### FEAT-005: Model2Vec Default Engine - ✅ COMPLETE

**What:** Model2Vec (79x faster) as default embedding engine with UI toggle.

**Model:** `minishlab/potion-multilingual-128M` (101 languages incl Korean)

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

# Check for lazy import violations
grep -rn "^from sentence_transformers\|^import torch" server/ --include="*.py"
```

---

## Playground

```
Current:  v25.1217.2220 (Build 298) ← NEEDS REFRESH
Pending:  Build 300 (Linux CI passed, Windows pending)
Path:     C:\NEIL_PROJECTS_WINDOWSBUILD\LocaNextProject\Playground\LocaNext
Mode:     ONLINE (PostgreSQL)
Login:    neil/neil
```

---

*This document is the source of truth for session handoff.*
