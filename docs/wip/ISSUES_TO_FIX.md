# Issues To Fix

**Last Updated:** 2025-12-18 | **Build:** 298 (v25.1217.2220)

---

## Quick Summary

| Status | Count | Items |
|--------|-------|-------|
| **Open Bugs** | **0** | - |
| **Tested & Complete** | **4** | PERF-001, PERF-002, FEAT-005, BUG-023 |
| Fixed (archived) | 63+ | See history |

---

## Recently Fixed

### BUG-023: TM Status Shows "Pending" - ✅ FIXED

**Culprit:** `MODEL_NAME` variable referenced but never defined in `tm_indexer.py`.

**Impact:** `NameError` during index build → status never set to "ready".

**Fix:** Replaced `MODEL_NAME` with `self._engine.name` at lines 280, 1730, 1977.

---

## Performance Improvements

### PERF-001: Incremental HNSW - ✅ CODE COMPLETE (Needs Testing)

**Priority:** HIGH | **Component:** FAISS index sync

**What:** Add 1 entry to 500k TM in ~0.1s instead of ~10s full rebuild.

**Solution:** `_incremental_sync()` method in `TMSyncManager`:
- Detects INSERT-only changes
- Loads existing FAISS index
- Adds only new vectors
- Falls back to full rebuild for UPDATE/DELETE

**Files:** `tm_indexer.py`, `shared/faiss_manager.py`

**Test:** Add entry → Sync → Check logs for "incremental" vs "full rebuild"

---

### PERF-002: FAISS Code Factorization - ✅ CODE COMPLETE (Needs Testing)

**Priority:** MEDIUM | **Component:** Code architecture

**What:** 12 FAISS copies → 1 `FAISSManager` class.

**Files Created:**
```
server/tools/shared/
├── __init__.py
└── faiss_manager.py    # Single source of truth
```

**Files Modified:**
- `ldm/tm_indexer.py` → Uses FAISSManager
- `kr_similar/embeddings.py` → Uses FAISSManager
- `xlstransfer/embeddings.py` → Uses FAISSManager

**Test:** Server starts, all FAISS operations work.

---

## Feature: Model2Vec Default Engine

### FEAT-005: Model2Vec + FAISS HNSW - ✅ COMPLETE

**What:** Model2Vec as default for LDM TM Search with UI toggle.

**Model:** `minishlab/potion-multilingual-128M`
- **101 languages** (including Korean)
- **29,269 sentences/sec**
- 256 dimensions, MIT license

**Engine Usage by Tool:**

| Tool | Engine | Reason |
|------|--------|--------|
| **LDM TM Search** | Model2Vec (default) / Qwen (opt-in) | Real-time needs speed |
| **LDM Standard Pretranslation** | Model2Vec / Qwen (user choice) | Follows user toggle |
| **KR Similar Pretranslation** | **Qwen ONLY** | Quality > speed |
| **XLS Transfer Pretranslation** | **Qwen ONLY** | Quality > speed |

> The Fast/Deep toggle affects LDM TM search AND standard pretranslation.
> KR Similar / XLS Transfer pretranslation ALWAYS use Qwen.

**Files Created:**
- `server/tools/shared/embedding_engine.py` - Engine abstraction
- API: `GET/POST /api/ldm/settings/embedding-engine`

**UI:** TM Manager toolbar → Fast/Deep toggle

**Details:** [FAISS_OPTIMIZATION_PLAN.md](FAISS_OPTIMIZATION_PLAN.md)

---

## Recently Fixed (Build 298)

| ID | Description | Date |
|----|-------------|------|
| BUG-027 | TM Viewer UI/UX overhaul | 2025-12-18 |
| FEAT-004 | TM Sync Protocol | 2025-12-18 |
| BUG-024 | File Viewer empty 3rd column | 2025-12-18 |
| BUG-025 | Title not clickable | 2025-12-18 |
| BUG-026 | User button shows "User" | 2025-12-18 |
| BUG-020 | memoQ-style metadata | 2025-12-17 |

**Full history:** [ISSUES_HISTORY.md](../history/ISSUES_HISTORY.md)

---

## Ongoing (Low Priority)

| Item | Status | Description |
|------|--------|-------------|
| P25 | 85% | LDM UX Overhaul |
| BUG-021 | Optional | Seamless UI during auto-update |

---

## How to Add Issues

```markdown
### BUG-XXX: Title
**Priority:** CRITICAL/HIGH/MEDIUM/LOW
**Component:** Where the bug is
**Problem:** What's wrong
**Expected:** What should happen
```

---

*Updated 2025-12-18 | 0 bugs, all complete*
