# LDM Text Search & TM System

**Version:** 1.0
**Created:** 2025-12-09
**Status:** PLANNING

> Complete documentation for the 5-Tier Cascade Search system used in LDM Translation Memory.

---

## Table of Contents

1. [Overview](#1-overview)
2. [5-Tier Cascade Architecture](#2-5-tier-cascade-architecture)
3. [Dual Threshold System](#3-dual-threshold-system)
4. [Index Types](#4-index-types)
5. [User Workflow](#5-user-workflow)
6. [Implementation Guide](#6-implementation-guide)

---

## 1. Overview

### 1.1 What is This?

A professional-grade Translation Memory (TM) search system that finds similar translations using multiple strategies, from exact matches to semantic similarity.

**Based on:** WebTranslatorNew's proven 5-tier cascade architecture.

### 1.2 Key Features

```
For Translators:
├── Upload TM files (TMX, Excel, TXT)
├── Get automatic suggestions while editing
├── See confidence levels (92%+ = reliable, 49%+ = guidance)
└── Apply suggestions with one click

For the System:
├── 5-tier search from fast to thorough
├── Stops early when confident match found
├── Dual threshold for quality control
└── Incremental index updates (no full rebuilds)
```

### 1.3 Why 5 Tiers?

```
Problem: Single search method has trade-offs

Exact match:     Fast but misses similar text
Fuzzy match:     Catches typos but misses synonyms
Embedding match: Catches meaning but slower

Solution: CASCADE from fast → thorough, stop when confident

Tier 1: Exact?     Yes → Done (1ms)
        ↓ No
Tier 2: Semantic?  Yes (92%+) → Done (10ms)
        ↓ No
Tier 3: Line exact? ...
        ↓
Tier 4: Line semantic? ...
        ↓
Tier 5: N-gram semantic? ...
```

---

## 2. 5-Tier Cascade Architecture

### 2.1 Tier Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         5-TIER CASCADE SEARCH                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ TIER 1: PERFECT WHOLE MATCH                                          │    │
│  │ ────────────────────────────                                         │    │
│  │ Method:   Hash lookup (SHA256 or normalized text key)                │    │
│  │ Speed:    O(1) - instant                                             │    │
│  │ Catches:  Exact duplicates, whitespace variations                    │    │
│  │ Returns:  100% match                                                 │    │
│  │ Stops:    YES - returns immediately                                  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    ↓ No match                                │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ TIER 2: WHOLE TEXT EMBEDDING                                         │    │
│  │ ───────────────────────────────                                      │    │
│  │ Method:   Embed query → FAISS HNSW search                            │    │
│  │ Speed:    10-50ms                                                    │    │
│  │ Catches:  Synonyms, paraphrases, similar meaning                     │    │
│  │ Returns:  Similarity score 0.0-1.0                                   │    │
│  │ Stops:    If best match >= cascade_threshold (0.92)                  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    ↓ No confident match                      │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ TIER 3: PERFECT LINE MATCH                                           │    │
│  │ ─────────────────────────────                                        │    │
│  │ Method:   Split by \n → hash lookup each line                        │    │
│  │ Speed:    O(1) per line                                              │    │
│  │ Catches:  Multi-line text where some lines are exact                 │    │
│  │ Returns:  Per-line matches                                           │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    ↓ Some lines unmatched                    │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ TIER 4: LINE-BY-LINE EMBEDDING                                       │    │
│  │ ─────────────────────────────────                                    │    │
│  │ Method:   Embed each unmatched line → FAISS search                   │    │
│  │ Speed:    10-50ms per line                                           │    │
│  │ Catches:  Similar lines within multi-line text                       │    │
│  │ Returns:  Per-line similarity scores                                 │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    ↓ Still need more matches                 │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ TIER 5: WORD N-GRAM EMBEDDING                                        │    │
│  │ ────────────────────────────────                                     │    │
│  │ Method:   Extract 1,2,3-word n-grams → embed each → FAISS            │    │
│  │ Speed:    10-50ms per gram                                           │    │
│  │ Catches:  Partial matches, shared phrases                            │    │
│  │ Example:  "Start the game now" →                                     │    │
│  │           1-grams: [Start] [the] [game] [now]                        │    │
│  │           2-grams: [Start the] [the game] [game now]                 │    │
│  │           3-grams: [Start the game] [the game now]                   │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Tier Details

| Tier | Name | Method | Time | What It Catches | Stops Cascade? |
|------|------|--------|------|-----------------|----------------|
| 1 | Perfect Whole | Hash O(1) | <1ms | Exact duplicates | Yes (100%) |
| 2 | Whole Embedding | FAISS | 10-50ms | Synonyms, meaning | If >= 0.92 |
| 3 | Perfect Line | Hash O(1) | <1ms/line | Exact lines | No |
| 4 | Line Embedding | FAISS | 10-50ms/line | Similar lines | No |
| 5 | N-gram Embedding | FAISS | 10-50ms/gram | Partial phrases | No |

### 2.3 Why This Order?

```
FAST → THOROUGH
CHEAP → EXPENSIVE
EXACT → FUZZY

Tier 1 is instant - check it first
Tier 2 catches most cases - stop if confident
Tier 3-5 dig deeper for multi-line or partial matches
```

---

## 3. Dual Threshold System

### 3.1 The Two Thresholds

```python
cascade_threshold = 0.92    # HIGH confidence
context_threshold = 0.49    # USEFUL guidance
```

### 3.2 What They Mean

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DUAL THRESHOLD LOGIC                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Similarity Score                                                            │
│  ───────────────                                                             │
│                                                                              │
│  1.00 ─┬─────────────────────────────────────────────────────────────────   │
│        │  PERFECT MATCH (Tier 1)                                             │
│        │  "Exact duplicate found"                                            │
│        │                                                                     │
│  0.92 ─┼─────────────────────────────────────────────────────────────────   │
│        │  PRIMARY MATCHES                                                    │
│        │  ✅ High confidence                                                 │
│        │  ✅ Can auto-apply                                                  │
│        │  ✅ Return ALL matches in this range                                │
│        │                                                                     │
│  0.49 ─┼─────────────────────────────────────────────────────────────────   │
│        │  CONTEXT CANDIDATES                                                 │
│        │  ⚠️  Lower confidence                                               │
│        │  ⚠️  Useful for reference                                           │
│        │  ⚠️  Return only SINGLE BEST match                                  │
│        │                                                                     │
│  0.00 ─┴─────────────────────────────────────────────────────────────────   │
│        │  BELOW THRESHOLD                                                    │
│        │  ❌ Not useful                                                      │
│        │  ❌ Don't return                                                    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.3 Return Logic

```python
# Collect results
primary_matches = []      # All matches >= 0.92
context_candidates = []   # All matches 0.49 to 0.92

# Return
results = primary_matches + [best(context_candidates)]

# Example return:
[
    {"source": "...", "target": "...", "similarity": 0.98, "type": "primary"},
    {"source": "...", "target": "...", "similarity": 0.95, "type": "primary"},
    {"source": "...", "target": "...", "similarity": 0.71, "type": "context"}  # Single best
]
```

### 3.4 Why This Design?

| Problem | Solution |
|---------|----------|
| Too many mediocre matches = noise | Only return ALL if >= 0.92 |
| Missing helpful references | Include SINGLE best from 0.49-0.92 |
| User doesn't know what to trust | Visual indicator: primary vs context |
| Auto-apply wrong translation | Only allow auto-apply for >= 0.92 |

---

## 4. Index Types

### 4.1 What We Build on TM Upload

```
TM UPLOAD → INDEX BUILDER
            │
            ├── HASH INDEXES (O(1) lookup)
            │   ├── whole_text_lookup    # source → {target, entry_id}
            │   └── line_lookup          # line → {target_line, entry_id, line_num}
            │
            └── FAISS INDEXES (Semantic search)
                ├── whole_faiss          # HNSW for whole text embeddings
                └── line_faiss           # HNSW for line embeddings
```

### 4.2 Hash Index (Perfect Match)

```python
# Built on upload
whole_text_lookup = {
    "게임을 시작하세요": {"target": "Start the game", "entry_id": 1},
    "게임을 시작하세요 ": {"target": "Start the game", "entry_id": 1},  # whitespace variant
    ...
}

# Search: O(1)
if query in whole_text_lookup:
    return whole_text_lookup[query]  # Instant!
```

### 4.3 FAISS Index (Embedding Search)

```python
# Built on upload
embeddings = model.encode(all_source_texts)  # Shape: (N, 768)
faiss.normalize_L2(embeddings)

index = faiss.IndexHNSWFlat(768, 32)
index.hnsw.efConstruction = 400
index.hnsw.efSearch = 500
index.add(embeddings)

# Search: O(log N)
query_embedding = model.encode([query])
faiss.normalize_L2(query_embedding)
distances, indices = index.search(query_embedding, top_k=10)
```

### 4.4 Storage Structure

```
server/data/ldm_tm/{tm_id}/
├── metadata.json           # TM info, stats, version
├── entries.pkl             # Raw source/target pairs
│
├── hash/
│   ├── whole_lookup.pkl    # Hash index for whole text
│   └── line_lookup.pkl     # Hash index for lines
│
├── embeddings/
│   ├── whole.npy           # Whole text embeddings
│   ├── whole_mapping.pkl   # idx → entry_id
│   ├── line.npy            # Line embeddings
│   └── line_mapping.pkl    # idx → (entry_id, line_num)
│
└── faiss/
    ├── whole.index         # FAISS HNSW for whole
    └── line.index          # FAISS HNSW for lines
```

---

## 5. User Workflow

### 5.1 Uploading a TM

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            TM UPLOAD FLOW                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  USER                              SYSTEM                                    │
│  ────                              ──────                                    │
│                                                                              │
│  1. Click "Upload TM"                                                        │
│     ↓                                                                        │
│  2. Select file (TMX/Excel/TXT)                                              │
│     ↓                                                                        │
│  3. Configure columns                   → Parse file                         │
│     (source col, target col)            → Extract entries                    │
│     ↓                                   → Validate                           │
│  4. Click "Upload"                                                           │
│     ↓                                                                        │
│  5. See progress bar                    → Build hash indexes                 │
│     "Building indexes..."               → Generate embeddings                │
│     [████████████░░░░░░░░] 60%          → Build FAISS indexes                │
│     ↓                                                                        │
│  6. TM appears in list                  → Save to disk                       │
│     Status: "Ready"                     → Update metadata                    │
│     Entries: 50,000                                                          │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Using TM While Editing

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          EDITING WITH TM                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  USER                              SYSTEM                                    │
│  ────                              ──────                                    │
│                                                                              │
│  1. Open file in LDM grid                                                    │
│     ↓                                                                        │
│  2. Select active TM                    → Load TM indexes into memory        │
│     [BDO Main TM ▼]                                                          │
│     ↓                                                                        │
│  3. Double-click row to edit            → Get source text                    │
│     ↓                                   → Run 5-tier cascade                 │
│  4. Edit modal opens                    → Return matches                     │
│     ↓                                                                        │
│  5. See TM suggestions panel:                                                │
│                                                                              │
│     ┌─ TM Suggestions ─────────────────────────────────────────────────┐    │
│     │                                                                   │    │
│     │  ✅ 98% (Primary)                                                 │    │
│     │  Source: 게임을 시작하세요                                          │    │
│     │  Target: Start the game                          [Apply]          │    │
│     │                                                                   │    │
│     │  ✅ 94% (Primary)                                                 │    │
│     │  Source: 게임을 시작합니다                                          │    │
│     │  Target: Starting the game                       [Apply]          │    │
│     │                                                                   │    │
│     │  ⚠️ 71% (Context)                                                 │    │
│     │  Source: 플레이를 시작하세요                                        │    │
│     │  Target: Start playing                           [Apply]          │    │
│     │                                                                   │    │
│     └───────────────────────────────────────────────────────────────────┘    │
│     ↓                                                                        │
│  6. Click [Apply] on suggestion         → Fill target field                  │
│     ↓                                                                        │
│  7. Edit if needed, then Save                                                │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.3 Understanding Confidence Levels

| Icon | Label | Score | Meaning | Action |
|------|-------|-------|---------|--------|
| ✅ | Primary | 92%+ | High confidence, probably correct | Safe to apply |
| ⚠️ | Context | 49-92% | Helpful reference | Review before applying |

---

## 6. Implementation Guide

### 6.1 File Structure

```
server/tools/ldm/
├── tm_manager.py          # TM upload, list, delete, activate
├── tm_indexer.py          # Build all indexes
├── tm_search.py           # 5-tier cascade search
├── tm_embeddings.py       # Embedding generation
└── tm_updater.py          # Incremental updates

locaNext/src/lib/components/ldm/
├── TMManager.svelte       # TM list and upload UI
├── TMUploadModal.svelte   # Upload configuration
└── TMPanel.svelte         # Suggestions panel in edit modal
```

### 6.2 API Endpoints

```
POST /api/ldm/tm/upload           # Upload new TM
GET  /api/ldm/tm/list             # List all TMs
POST /api/ldm/tm/{id}/activate    # Set active TM
DELETE /api/ldm/tm/{id}           # Delete TM
GET  /api/ldm/tm/{id}/status      # Get indexing status

GET  /api/ldm/tm/suggest          # Search with 5-tier cascade
     ?source=text
     &tm_id=1
     &cascade_threshold=0.92
     &context_threshold=0.49
```

### 6.3 Search Response Format

```json
{
  "suggestions": [
    {
      "source": "게임을 시작하세요",
      "target": "Start the game",
      "similarity": 0.98,
      "type": "primary",
      "tier": 2,
      "strategy": "whole-embedding"
    },
    {
      "source": "플레이를 시작하세요",
      "target": "Start playing",
      "similarity": 0.71,
      "type": "context",
      "tier": 2,
      "strategy": "whole-embedding"
    }
  ],
  "search_time_ms": 45,
  "tier_reached": 2
}
```

---

## Related Documentation

- [P17_LDM_TASKS.md](../wip/P17_LDM_TASKS.md) - Implementation task list
- [LDM_GUIDE.md](LDM_GUIDE.md) - General LDM usage guide
- [WebTranslatorNew Reference](../../RessourcesForCodingTheProject/WebTranslatorNew/) - Source architecture

---

*Document version 1.0 - Based on WebTranslatorNew 5-tier cascade architecture*
