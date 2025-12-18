# FAISS & Embedding Optimization Plan

**Created:** 2025-12-18 | **Updated:** 2025-12-18 | **Status:** ✅ COMPLETE

---

## Status Summary

| ID | Description | Status | Files |
|----|-------------|--------|-------|
| **PERF-001** | Incremental HNSW (no full rebuild) | ✅ TESTED | `tm_indexer.py` |
| **PERF-002** | FAISS code factorization (DRY) | ✅ TESTED | `shared/faiss_manager.py` |
| **FEAT-005** | Model2Vec as default engine | ✅ COMPLETE | `shared/embedding_engine.py` |

---

## PERF-001: Incremental HNSW - ✅ TESTED

### Problem

Current code rebuilds entire FAISS index on every sync, even when adding 1 entry to 500k TM.

### Solution Implemented

Added `_incremental_sync()` method to `TMSyncManager` in `tm_indexer.py`.

### Test Results

| Scenario | Before | After |
|----------|--------|-------|
| Build 10k index | ~6s | ~6s |
| Incremental add 100 | ~6s | **1.25s (5x faster)** |
| Search per query | ~2.4ms | ~2.4ms |

---

## PERF-002: FAISS Code Factorization - ✅ TESTED

### Problem

FAISS logic was duplicated 12 times across 3 files with identical configuration.

### Solution Implemented

Created centralized `FAISSManager` in `server/tools/shared/faiss_manager.py`.

### Test Results

- All 3 tools import cleanly (ldm, kr_similar, xlstransfer)
- All FAISS operations work correctly

---

## FEAT-005: Model2Vec Default Engine - ✅ COMPLETE

### Problem

Qwen (2.3GB) is slow to load (~30s) and heavy on RAM.

### Solution Implemented

Created `EmbeddingEngine` abstraction with Model2Vec as default.

### Test Results (Model2Vec - potion-multilingual-128M)

| Metric | Result |
|--------|--------|
| Model | `minishlab/potion-multilingual-128M` (101 languages incl Korean) |
| Speed | **29,269 sentences/sec** |
| Dimension | 256 |
| Search per query | **<1ms** |

### Model Selection

| Model | Speed | Use Case |
|-------|-------|----------|
| `potion-multilingual-128M` | 29K/sec | **Default** - Korean-English TM |
| `potion-base-8M` | 44K/sec | English-only (not used) |

### Files Created

- `server/tools/shared/embedding_engine.py` - Engine abstraction
- API: `GET/POST /api/ldm/settings/embedding-engine`

### Files Modified

- `server/tools/shared/__init__.py` - Exports
- `server/tools/ldm/api.py` - API endpoints
- `server/tools/ldm/tm_indexer.py` - Uses EmbeddingEngine
- `locaNext/src/lib/components/ldm/TMManager.svelte` - UI toggle

### UI

TM Manager toolbar has **Fast/Deep** toggle:
- **Fast** (Model2Vec): 79x faster, default
- **Deep** (Qwen): Better semantic understanding, opt-in

---

## Architecture (IMPLEMENTED)

### Embedding Engine Usage by Tool

| Tool | Engine | Why |
|------|--------|-----|
| **LDM TM Search** | Model2Vec (default) / Qwen (opt-in) | Real-time search needs speed; user can toggle for quality |
| **KR Similar** | **Qwen ONLY** | Pretranslation quality > speed |
| **XLS Transfer** | **Qwen ONLY** | Batch processing; quality matters |

> **Important:** The Model2Vec/Qwen toggle in LDM TM Manager ONLY affects LDM TM search.
> Pretranslation tools (KR Similar, XLS Transfer) ALWAYS use Qwen for maximum accuracy.

### LDM TM Search Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│  LDM TM Search Pipeline (Model2Vec/Qwen Selectable)              │
│                                                                  │
│  1. EXACT MATCH (hash lookup) ← instant                         │
│  2. CONTAINS (substring) ← fast                                  │
│  3. SEMANTIC (Model2Vec + FAISS HNSW) ← DEFAULT                 │
│     └── 79x faster embedding than Qwen                          │
│     └── 48,632 texts/sec                                        │
│     └── 0.2ms/query search                                      │
│                                                                  │
│  4. SEMANTIC DEEP (Qwen + FAISS HNSW) ← OPT-IN via UI           │
│     └── Toggle in TM Manager: "Deep" button                     │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  KR Similar / XLS Transfer (Qwen Only)                          │
│                                                                  │
│  Always Qwen for maximum semantic accuracy.                     │
│  Batch processing - speed less critical than quality.           │
└─────────────────────────────────────────────────────────────────┘
```

---

## API Endpoints

```
GET  /api/ldm/settings/embedding-engines   # List available engines
GET  /api/ldm/settings/embedding-engine    # Get current engine
POST /api/ldm/settings/embedding-engine    # Set engine {"engine": "model2vec"|"qwen"}
```

---

## Scale Projections

| TM Size | Real-time Add | Search | Full Rebuild |
|---------|---------------|--------|--------------|
| 10k | ~0.1ms | ~1ms | ~2s |
| 100k | ~0.1ms | ~2ms | ~20s |
| 500k | ~0.1ms | ~3ms | ~60s |
| 1M | ~0.1ms | ~5ms | ~120s |

---

*Completed 2025-12-18*
