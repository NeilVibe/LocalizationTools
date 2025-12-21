# Session Context - Claude Handoff Document

**Last Updated:** 2025-12-21 21:30 | **Build:** 315 (PENDING) | **Previous:** 314

---

## CURRENT TASK: QA BUILD IMPLEMENTATION ✅ DONE

**Goal:** Implement `QA-LIGHT` build mode for thorough testing before Build 315 release.

**Plan:** [P36_CICD_TEST_OVERHAUL.md](P36_CICD_TEST_OVERHAUL.md)

| Build Type | Tests | Status |
|------------|-------|--------|
| `LIGHT` | ~285 essential | ✅ Working |
| `FULL` | ~285 + model | ✅ Working |
| `QA-LIGHT` | ALL tests (6 stages) | ✅ IMPLEMENTED |
| `QA-FULL` | ALL + model | ✅ IMPLEMENTED |

### QA-LIGHT Optimal Staged Testing
```
╔════════════════════════════════════════════════════════════╗
║         QA MODE: OPTIMAL STAGED TESTING                    ║
╚════════════════════════════════════════════════════════════╝

Stage 1: UNIT TESTS        (~400 tests)  ← Fast feedback
Stage 2: INTEGRATION       (~200 tests)  ← Component validation
Stage 3: E2E               (~100 tests)  ← Full workflows
Stage 4: API               (~150 tests)  ← Endpoint validation
Stage 5: SECURITY          (~50 tests)   ← Security checks
Stage 6: FIXTURES          (~200 tests)  ← Edge cases
```

### New Tests Added This Session

| Test File | Coverage | Tests |
|-----------|----------|-------|
| `tests/api/test_feat001_tm_link.py` | FEAT-001 API | 15 tests |
| `tests/unit/test_progress_tracker_silent.py` | Silent tracking | 8 tests |
| `tests/unit/test_tm_dimension_mismatch.py` | Dimension handling | 10 tests |

**FEAT-001 API Tests (`test_feat001_tm_link.py`):**
- `TestTMLinkEndpoints`: Link/unlink TM to project (7 tests)
- `TestAutoAddToTM`: Auto-add on cell confirm (4 tests)
- `TestEmbeddingEngineWarning`: Qwen warning (4 tests)
- `TestTMSyncEndpoints`: Manual sync (2 tests)

**Silent Tracking Tests (`test_progress_tracker_silent.py`):**
- Default silent flag is False
- Silent flag stored correctly
- Silent flag in WebSocket events
- Use case documentation

**Dimension Mismatch Tests (`test_tm_dimension_mismatch.py`):**
- Model2Vec vs Qwen dimension detection
- Re-embed trigger on mismatch
- FAISS index rebuild requirement
- Engine switching scenarios

---

## CI/CD FUTURE IMPROVEMENTS (P36 Roadmap)

| Feature | Priority | Status | Notes |
|---------|----------|--------|-------|
| **Parallel execution** | HIGH | 🔜 TODO | `pytest-xdist -n 4` (safe, 2-3x faster) |
| **Code coverage** | HIGH | 🔜 TODO | `pytest-cov` reports |
| **Performance tests** | MEDIUM | 🔜 TODO | API latency, embedding throughput |
| **Block reorganization** | LOW | 📋 PLANNED | P36 tests/blocks/ structure |
| **Test caching** | SKIP | ❌ NO | Too risky, could miss bugs |

### Parallel Execution Plan
```bash
# Install
pip install pytest-xdist

# Usage (safe, 4 workers max)
pytest tests/ -n 4 -v

# Auto-detect cores (still safe)
pytest tests/ -n auto -v
```

### Code Coverage Plan
```bash
# Install
pip install pytest-cov

# Usage
pytest tests/ --cov=server --cov-report=html

# Output: htmlcov/index.html
```

### Performance Tests Plan
```python
# tests/performance/test_api_latency.py
def test_api_response_under_100ms():
    start = time.time()
    response = client.get("/api/health")
    elapsed = (time.time() - start) * 1000
    assert elapsed < 100, f"API too slow: {elapsed}ms"
```

---

## COMPLETED: FEAT-001 FRONTEND

### Session Progress

| Task | Status | Notes |
|------|--------|-------|
| FEAT-001 Frontend: TM Link UI | ✅ DONE | FileExplorer.svelte |
| Add `silent` flag to TrackedOperation | ✅ DONE | For no-toast auto-updates |
| Track auto-sync with `silent=True` | ✅ DONE | `_auto_sync_tm_indexes()` |
| Track manual sync with toast | ✅ DONE | `sync_tm_indexes()` |
| Qwen engine warning | ✅ DONE | Response includes warning message |
| FEAT-001 Backend | ✅ VERIFIED | Previous session |

### Files Changed This Session
```
locaNext/src/lib/components/ldm/FileExplorer.svelte
  - Lines 78-81: Added linkedTM, showLinkTMModal, selectedLinkTMId state
  - Lines 176-254: Added loadLinkedTM(), linkTMToProject(), unlinkTMFromProject(), openLinkTMModal()
  - Lines 772-786: Added linked-tm-bar UI (shows linked TM or "Link a TM")
  - Lines 941-987: Added Link TM Modal with dropdown + unlink button
  - Lines 1309-1352: Added CSS for linked-tm-bar

server/utils/progress_tracker.py
  - Lines 251: Added `silent` parameter to TrackedOperation
  - Lines 320: Pass `silent` to WebSocket events
  - Lines 361: Updated docstring with silent example

server/tools/ldm/api.py
  - Lines 2156-2207: _auto_sync_tm_indexes() with TrackedOperation(silent=True)
  - Lines 2210-2302: sync_tm_indexes() with TrackedOperation (shows toast)
  - Lines 3035: Added `warning` field to EmbeddingEngineResponse
  - Lines 3074-3116: set_embedding_engine() with Qwen warning
```

---

## TASK TRACKING ARCHITECTURE

### Silent vs Non-Silent Operations

```
┌─────────────────────────────────────────────────────────────────────┐
│                    TASK TRACKING (TrackedOperation)                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  SILENT (silent=True) - NO TOAST:                                  │
│    ├── Auto-sync after cell confirm                                │
│    ├── FAISS incremental add                                       │
│    ├── Auto-embedding on-the-fly                                   │
│    └── Still tracked in Task Manager!                              │
│                                                                     │
│  NON-SILENT (silent=False, default) - SHOWS TOAST:                 │
│    ├── Manual TM sync                                              │
│    ├── Bulk operations                                             │
│    ├── File upload/processing                                      │
│    └── User-initiated operations                                   │
│                                                                     │
│  ALL operations tracked in:                                         │
│    ├── active_operations table (DB)                                │
│    ├── Task Manager (UI)                                           │
│    └── Dashboard logs (analytics)                                  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Usage Example
```python
# Silent operation (no toast, but tracked)
with TrackedOperation(
    "Auto-sync TM",
    user_id,
    tool_name="LDM",
    silent=True  # <-- NO toast
) as op:
    op.update(50, "Working...")

# Normal operation (shows toast)
with TrackedOperation(
    "Manual TM Sync",
    user_id,
    tool_name="LDM"
    # silent=False is default
) as op:
    op.update(50, "Working...")
```

---

## QWEN ENGINE WARNING

When switching to Qwen engine, API returns warning:
```json
{
  "current_engine": "qwen",
  "engine_name": "Qwen3-Embedding-0.6B",
  "warning": "⚠️ Qwen engine is ~30x slower than Model2Vec. Syncing large TMs may take significantly longer. Recommended for batch processing or when quality is critical."
}
```

---

## EMBEDDING ENGINES

### Two Models Available

| Engine | Model | Dim | Speed | Memory | Use Case |
|--------|-------|-----|-------|--------|----------|
| **Model2Vec** | potion-multilingual-128M | 256 | 29,269/sec | ~128MB | DEFAULT (real-time) |
| **Qwen** | Qwen3-Embedding-0.6B | 1024 | ~1,000/sec | ~2.3GB | OPT-IN (quality) |

### Engine Switching
```bash
# Get current engine
GET /api/ldm/settings/embedding-engine
# → {"current_engine": "model2vec", "engine_name": "Model2Vec (Fast)"}

# Switch engine (returns warning for Qwen)
POST /api/ldm/settings/embedding-engine
{"engine": "qwen"}
# → {"current_engine": "qwen", "engine_name": "...", "warning": "⚠️ ..."}
```

### Smart Sync Behavior
- Sync ALWAYS uses the currently ACTIVE engine
- If cached embeddings have different dimension → re-embed ALL entries
- Log: `Embedding dimension mismatch: cached=1024, model=256. Re-embedding all entries.`

---

## FEAT-001: AUTO-ADD TO TM (PREVIOUS SESSION)

**Problem:** When user confirms cell (Ctrl+S → status='reviewed'), should auto-add to linked TM.

**Solution:** IMPLEMENTED & E2E VERIFIED

| Component | Status | Notes |
|-----------|--------|-------|
| `POST /projects/{id}/link-tm` | ✅ DONE | Links TM to project |
| `DELETE /projects/{id}/link-tm/{tm_id}` | ✅ DONE | Unlinks TM |
| `GET /projects/{id}/linked-tms` | ✅ DONE | Lists linked TMs |
| `_get_project_linked_tm()` helper | ✅ DONE | Gets priority TM |
| Auto-add in `update_row()` | ✅ DONE | With BackgroundTasks |
| Dimension mismatch fix | ✅ DONE | Re-embeds if dim differs |
| E2E DB test | ✅ VERIFIED | Entry count 10→12 |
| FAISS sync | ✅ VERIFIED | Both engines work |

---

## TODO: REMAINING WORK

### Phase 3: Frontend TM Link UI ✅ DONE
- [x] Add TM link dropdown to FileExplorer.svelte
- [x] Load linked TM on project expand
- [x] Show linked TM indicator badge

### Phase 4: Dashboard Improvements
- [ ] Dashboard updates for cleaner UX
- [ ] Log all events to dashboard for analytics
- [ ] Operation history view

### Phase 5: Tests
- [ ] Unit tests for link/unlink
- [ ] Integration test: confirm → TM add
- [ ] E2E test: Link TM → Confirm cell → Check TM entry added

---

## SMART FAISS SYNC STRATEGY

```
┌─────────────────────────────────────────────────────────────────────┐
│                SMART SYNC STRATEGY (TMSyncManager)                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  IF INSERT only (no UPDATE, no DELETE):                            │
│    🚀 SUPER FAST INCREMENTAL (~30-50ms)                            │
│    └── FAISSManager.incremental_add()                              │
│    └── Model2Vec.encode() - 79x faster than Qwen                   │
│                                                                     │
│  IF UPDATE or DELETE:                                               │
│    📦 SMART REBUILD (~2-10s)                                       │
│    └── Detect dimension mismatch → re-embed all                    │
│    └── Keep unchanged embeddings if dim matches                    │
│    └── Only re-embed changed entries                               │
│                                                                     │
│  IF dimension mismatch (e.g., Qwen→Model2Vec):                     │
│    🔄 FULL RE-EMBED                                                │
│    └── Detected automatically                                       │
│    └── Re-embeds all entries with current engine                   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## KEY PATHS

| What | Path |
|------|------|
| **TrackedOperation** | `server/utils/progress_tracker.py:226` |
| **Auto-sync (silent)** | `server/tools/ldm/api.py:2156-2207` |
| **Manual sync (toast)** | `server/tools/ldm/api.py:2210-2302` |
| **Qwen warning** | `server/tools/ldm/api.py:3100-3108` |
| **FEAT-001 Design** | `docs/wip/FEAT-001_AUTO_TM_DESIGN.md` |
| **update_row function** | `server/tools/ldm/api.py:750-855` |
| **TM link endpoints** | `server/tools/ldm/api.py:936-1089` |
| **Dimension mismatch fix** | `server/tools/ldm/tm_indexer.py:1854-1878` |
| **FAISS incremental add** | `server/tools/shared/faiss_manager.py:216` |

---

## QUICK COMMANDS

```bash
# Start backend
python3 server/main.py

# Link TM to project
curl -X POST "http://localhost:8888/api/ldm/projects/2/link-tm" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"tm_id": 1, "priority": 0}'

# Check current engine
curl "http://localhost:8888/api/ldm/settings/embedding-engine" \
  -H "Authorization: Bearer $TOKEN"

# Switch to Qwen (shows warning)
curl -X POST "http://localhost:8888/api/ldm/settings/embedding-engine" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"engine": "qwen"}'

# Manual TM sync (shows toast in UI)
curl -X POST "http://localhost:8888/api/ldm/tm/1/sync" \
  -H "Authorization: Bearer $TOKEN"
```

---

## NEXT SESSION PRIORITIES

1. **Frontend UI** - TM link dropdown in FileExplorer.svelte
2. **Dashboard** - Clean UX for viewing operation logs
3. **Frontend Toast Handling** - Check `silent` flag in WebSocket events
4. **Tests** - Unit/integration tests for TM link + auto-add

---

*TASK-002 COMPLETE | TrackedOperation silent flag | Qwen warning | Manual sync tracking*
