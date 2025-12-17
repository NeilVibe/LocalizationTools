# P36: Technical Design Document

**Priority:** P36 | **Status:** DESIGN PHASE | **Created:** 2025-12-17

---

## Purpose

This document covers the **foundational design decisions** for P36 Pretranslation System before any code is written. These decisions affect architecture, performance, and data integrity.

---

## Table of Contents

0. [Database Changes Required](#0-database-changes-required) ← **NEW**
1. [Batch Processing Architecture](#1-batch-processing-architecture)
2. [StringID Handling in Embeddings](#2-stringid-handling-in-embeddings)
3. [Glossary Creation Flow](#3-glossary-creation-flow)
4. [Data Preprocessing Strategy](#4-data-preprocessing-strategy)

---

## 0. Database Changes Required

**Reviewed:** 2025-12-17 | **Status:** ⏳ TO IMPLEMENT

### Current DB Model Analysis

#### LDMRow (for Files) - ✅ HAS StringID
```python
# server/database/models.py:636-678
class LDMRow(Base):
    __tablename__ = "ldm_rows"
    string_id = Column(String(255), nullable=True, index=True)  # ✅ EXISTS
    source = Column(Text, nullable=True)
    target = Column(Text, nullable=True)
```

#### LDMTMEntry (for TM) - ❌ MISSING StringID
```python
# server/database/models.py:795-831
class LDMTMEntry(Base):
    __tablename__ = "ldm_tm_entries"
    source_text = Column(Text, nullable=False)
    target_text = Column(Text, nullable=True)
    source_hash = Column(String(64), nullable=False, index=True)
    # ❌ NO string_id column!
```

#### LDMTranslationMemory - ❌ MISSING Mode
```python
# server/database/models.py:747-792
class LDMTranslationMemory(Base):
    __tablename__ = "ldm_translation_memories"
    name = Column(String(255), nullable=False)
    source_lang = Column(String(10), default="ko")
    target_lang = Column(String(10), default="en")
    # ❌ NO mode column (standard vs stringid)!
```

### Required Changes

#### 1. Add `string_id` to `LDMTMEntry`
```python
# ADD to server/database/models.py LDMTMEntry class
string_id = Column(String(255), nullable=True, index=True)
```

#### 2. Add `mode` to `LDMTranslationMemory`
```python
# ADD to server/database/models.py LDMTranslationMemory class
mode = Column(String(20), default="standard")  # "standard" or "stringid"
```

#### 3. Update Indexes
```python
# In LDMTMEntry.__table_args__
Index("idx_ldm_tm_entry_stringid", "string_id"),
Index("idx_ldm_tm_entry_tm_hash_stringid", "tm_id", "source_hash", "string_id"),
```

#### 4. Migration Script
```sql
-- Alembic migration or manual SQL
ALTER TABLE ldm_tm_entries ADD COLUMN string_id VARCHAR(255);
CREATE INDEX idx_ldm_tm_entry_stringid ON ldm_tm_entries(string_id);

ALTER TABLE ldm_translation_memories ADD COLUMN mode VARCHAR(20) DEFAULT 'standard';
```

### Excel Handler Update

#### Current (`tm_manager.py:193-241`)
```python
def _parse_excel_for_tm(self, ..., source_col=0, target_col=1):
    # Only 2 columns - NO StringID support
```

#### Required
```python
def _parse_excel_for_tm(self, ..., source_col=0, target_col=1, stringid_col=None, mode="standard"):
    # Support optional StringID column
    # Validate based on mode (strict for stringid, lenient for standard)
```

### Implementation Order

1. ✅ DB model changes (add columns)
2. ✅ Migration script
3. ✅ Excel handler update
4. ✅ API updates (accept mode + stringid_column params)
5. ✅ PKL builder update (variations structure)
6. ✅ Frontend modal (mode selection + column mapping)

---

## 1. Batch Processing Architecture

### Resource Usage: 100% LOCAL Processing

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PRETRANSLATION = LOCAL CPU POWER                          │
│                                                                             │
│  USER'S PC (LocaNext.exe)          CENTRAL SERVER (PostgreSQL)             │
│  ════════════════════════          ════════════════════════════             │
│  ✅ Qwen embeddings (2.3GB)        ❌ No compute                            │
│  ✅ FAISS vector search            ✅ Data storage only                     │
│  ✅ Hash lookups                   ✅ User auth                             │
│  ✅ N-gram matching                ✅ Session management                    │
│  ✅ Multiprocessing (4 workers)                                             │
│  ✅ Celery + Redis (local)                                                  │
│                                                                             │
│  WHY LOCAL?                                                                 │
│  ├── No network latency for millions of vector comparisons                 │
│  ├── User's CPU is dedicated to their work                                 │
│  ├── Server doesn't bottleneck under multi-user load                       │
│  └── Offline mode works (SQLite fallback)                                  │
│                                                                             │
│  CPU USAGE:                                                                 │
│  ├── Embedding generation: HIGH (Qwen model inference)                     │
│  ├── FAISS search: MEDIUM-HIGH (vector similarity)                         │
│  ├── Hash/N-gram: LOW                                                      │
│  └── Workers: 4 (uses ~50% of CPU, leaves headroom)                        │
│                                                                             │
│  MEMORY USAGE:                                                              │
│  ├── Qwen model: ~2.3GB (loaded once)                                      │
│  ├── FAISS index: Varies by TM size (~100MB per 100k entries)              │
│  └── Per chunk: ~50MB (500 rows × embeddings)                              │
│                                                                             │
│  EXPECTED PERFORMANCE:                                                      │
│  ├── 10,000 rows: ~2 minutes                                               │
│  ├── 100,000 rows: ~20 minutes                                             │
│  └── Scales linearly with row count                                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Current Infrastructure

We already have Celery + Redis:

```python
# server/tasks/celery_app.py (EXISTS)
broker = redis://localhost:6379/1
result_backend = redis://localhost:6379/2
task_time_limit = 3600      # 1 hour hard limit
task_soft_time_limit = 3000  # 50 min soft limit
```

### The Question: How to Optimize?

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| **A. Celery Only** | Single queue, single worker | Simple, already exists | Slower for large batches |
| **B. Celery + Multiprocess** | Queue + multiprocessing within worker | Faster, uses all CPU cores | More complex, memory usage |
| **C. Multiple Celery Workers** | Multiple worker processes | Scalable, distributed | More infrastructure |
| **D. Chunked Processing** | Break into chunks, progress tracking | Resumable, good UX | Overhead per chunk |

### RECOMMENDATION: Option D (Chunked) + Option B (Multiprocess)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    RECOMMENDED ARCHITECTURE                                  │
│                                                                             │
│  User Request: Pretranslate 10,000 rows                                    │
│       │                                                                     │
│       ▼                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ CELERY TASK: pretranslate_batch                                      │   │
│  │                                                                      │   │
│  │  1. Validate request                                                │   │
│  │  2. Split into chunks (500 rows each = 20 chunks)                  │   │
│  │  3. For each chunk:                                                 │   │
│  │     ├── Multiprocess pool (4-8 workers)                            │   │
│  │     ├── Each worker processes ~60-125 rows                         │   │
│  │     ├── Update progress via WebSocket                              │   │
│  │     └── Save results to DB                                          │   │
│  │  4. Return final results                                            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  Benefits:                                                                  │
│  - Resumable (if task fails, restart from last chunk)                      │
│  - Progress tracking (user sees 5/20 chunks done)                          │
│  - Memory efficient (only 500 rows in memory at a time)                    │
│  - Fast (multiprocessing uses all CPU cores)                               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Configuration Parameters

```python
# Recommended defaults (can be tuned)
CHUNK_SIZE = 500           # Rows per chunk
WORKERS_PER_CHUNK = 4      # Multiprocess workers (adjust based on CPU cores)
PROGRESS_UPDATE_INTERVAL = 50  # Update WebSocket every N rows
```

### Why This Works

| Metric | Value | Reasoning |
|--------|-------|-----------|
| **Chunk Size: 500** | ~500 rows | Small enough for memory, large enough for efficiency |
| **Workers: 4** | CPU cores / 2 | Leave CPU headroom for other tasks |
| **Progress: 50 rows** | ~10 updates per chunk | Responsive UX without WebSocket spam |

### Code Structure (Conceptual)

```python
# server/tasks/pretranslate_tasks.py

from celery import shared_task
from multiprocessing import Pool

@shared_task(bind=True)
def pretranslate_batch(self, file_id: int, engine: str, dictionary_id: int, threshold: float):
    """
    Main Celery task for batch pretranslation.
    Uses chunking + multiprocessing for optimal performance.
    """
    # 1. Load file rows
    rows = load_file_rows(file_id)
    total_rows = len(rows)

    # 2. Split into chunks
    chunks = list(chunked(rows, CHUNK_SIZE))
    total_chunks = len(chunks)

    results = []
    for chunk_idx, chunk in enumerate(chunks):
        # 3. Process chunk with multiprocessing
        with Pool(processes=WORKERS_PER_CHUNK) as pool:
            chunk_results = pool.map(
                partial(process_row, engine=engine, dictionary_id=dictionary_id, threshold=threshold),
                chunk
            )

        # 4. Save chunk results to DB
        save_chunk_results(file_id, chunk_results)

        # 5. Update progress
        progress = (chunk_idx + 1) / total_chunks * 100
        self.update_state(state='PROGRESS', meta={'progress': progress, 'chunk': chunk_idx + 1, 'total': total_chunks})
        send_websocket_progress(file_id, progress)

        results.extend(chunk_results)

    return {'status': 'complete', 'total_processed': len(results)}
```

### Open Questions

- [ ] Should we allow cancellation mid-batch?
- [ ] How to handle partial failures (some rows fail, others succeed)?
- [ ] Should chunks be processed in parallel (multiple Celery tasks)?

---

## 2. StringID Handling in Embeddings

### User Choice: Process WITH or WITHOUT StringID

**The user decides at TM creation time:**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    TM CREATION - MODE SELECTION                              │
│                                                                             │
│  ○ Standard Mode (Source + Target only)                                    │
│    └── Rows without target are skipped                                     │
│    └── Most common translation wins for duplicates                         │
│    └── Works with any file format                                          │
│                                                                             │
│  ○ StringID Mode (Source + Target + StringID)                              │
│    └── PRECHECK: All rows MUST have Source + Target + StringID             │
│    └── If any row is missing data → ERROR, cannot process                  │
│    └── Preserves context differentiation for game UI                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### StringID Mode: Strict Validation

**If user selects StringID mode, we run a PRECHECK:**

```python
def precheck_stringid_mode(df: pd.DataFrame) -> tuple[bool, str, dict]:
    """
    Validate data for StringID mode processing.
    ALL rows must have Source + Target + StringID.

    Returns: (is_valid, error_message, stats)
    """
    stats = {
        'total_rows': len(df),
        'missing_source': 0,
        'missing_target': 0,
        'missing_stringid': 0,
        'valid_rows': 0
    }

    # Check for missing data
    stats['missing_source'] = df['source'].isna().sum() + (df['source'] == '').sum()
    stats['missing_target'] = df['target'].isna().sum() + (df['target'] == '').sum()
    stats['missing_stringid'] = df['string_id'].isna().sum() + (df['string_id'] == '').sum()
    stats['valid_rows'] = len(df) - max(stats['missing_source'], stats['missing_target'], stats['missing_stringid'])

    # If ANY discrepancies, reject
    if stats['missing_source'] > 0 or stats['missing_target'] > 0 or stats['missing_stringid'] > 0:
        error_msg = f"""
Data has discrepancies and cannot be processed with StringID mode:
- Rows missing Source: {stats['missing_source']}
- Rows missing Target: {stats['missing_target']}
- Rows missing StringID: {stats['missing_stringid']}
- Total rows: {stats['total_rows']}

Please clean your data or use Standard Mode instead.
"""
        return False, error_msg, stats

    return True, "", stats
```

### Standard Mode: Lenient Processing

**If user selects Standard mode (no StringID), use existing robust logic:**

```python
# ALREADY EXISTS in process_operation.py:85
df = df.iloc[:, [col_kr_index, col_fr_index]].dropna()  # Skip rows without target

# ALREADY EXISTS - clean_text() removes _x000D_, strips whitespace
kr_texts = df.iloc[:, 0].apply(clean_text).tolist()
fr_texts = df.iloc[:, 1].apply(clean_text).tolist()

# ALREADY EXISTS - most frequent translation wins for duplicates
most_freq_trans = df.groupby('KR')['FR'].agg(safe_most_frequent).reset_index()
most_freq_trans = most_freq_trans.dropna()
```

### The Differentiation Problem

**Why StringID matters in games:**

```
Same source "저장" → Different targets based on context:
- UI_BUTTON_SAVE    → "Save"
- UI_MENU_SAVE      → "Save Game"
- DIALOGUE_SAVE_NPC → "I'll keep it safe"
```

If we only use Source as the key, we lose this differentiation!

### PKL Structure Options

| Option | PKL Structure | Pros | Cons |
|--------|--------------|------|------|
| **A. Source-only key** | `{source: target}` | Simple, current approach | Loses StringID context |
| **B. Compound key** | `{(source, string_id): target}` | Preserves differentiation | Exact StringID match required |
| **C. Source key + metadata** | `{source: {target, string_id, ...}}` | Flexible lookup | Complex, last-write-wins for duplicates |
| **D. Source key + list** | `{source: [{target, string_id}, ...]}` | All variations preserved | Multiple results to handle |

### RECOMMENDATION: Option D (Source key + list of variations)

```python
# Proposed PKL structure
{
    "저장": [
        {"target": "Save", "string_id": "UI_BUTTON_SAVE", "context": "button"},
        {"target": "Save Game", "string_id": "UI_MENU_SAVE", "context": "menu"},
        {"target": "I'll keep it safe", "string_id": "DIALOGUE_SAVE_NPC", "context": "dialogue"}
    ],
    "취소": [
        {"target": "Cancel", "string_id": "UI_CANCEL", "context": "button"}
    ],
    ...
}
```

### How Matching Would Work

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    MATCHING WITH STRINGID                                    │
│                                                                             │
│  Input: Source="저장", StringID="UI_BUTTON_SAVE"                            │
│                                                                             │
│  Step 1: Embedding lookup for "저장" → Find similar sources                │
│                                                                             │
│  Step 2: For each match, check variations:                                 │
│          └── Match found: "저장" has 3 variations                          │
│                                                                             │
│  Step 3: StringID matching (if provided):                                  │
│          ├── Exact StringID match? → Use that target (highest priority)   │
│          ├── Partial StringID match? → Suggest as option                   │
│          └── No StringID match? → Return all variations for user choice   │
│                                                                             │
│  Result:                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ Best Match: "Save" (StringID: UI_BUTTON_SAVE) ← Exact match         │   │
│  │ Alternatives:                                                        │   │
│  │   - "Save Game" (StringID: UI_MENU_SAVE)                            │   │
│  │   - "I'll keep it safe" (StringID: DIALOGUE_SAVE_NPC)               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Embedding Array Alignment

**Important:** Embeddings array and PKL must stay aligned!

```python
# Current (simple):
embeddings[0] → sources[0] → pkl[sources[0]]

# With variations (proposed):
embeddings[0] → sources[0] → pkl[sources[0]][0]  # First variation
                           → pkl[sources[0]][1]  # Second variation (SAME embedding!)
```

**Key insight:** We embed the SOURCE text, not the target. So multiple variations with the same source share ONE embedding.

```python
# Structure
sources = ["저장", "취소", ...]           # Unique sources only
embeddings = [emb_저장, emb_취소, ...]    # One embedding per unique source
pkl = {
    "저장": [variation1, variation2, ...],  # Multiple targets per source
    "취소": [variation1],
    ...
}

# Alignment: len(sources) == len(embeddings) == len(pkl.keys())
# Variations are metadata, not separate embeddings
```

### Database Schema Consideration

```sql
-- Current (if exists)
CREATE TABLE tm_entries (
    id SERIAL PRIMARY KEY,
    tm_id INTEGER,
    source_text TEXT,
    target_text TEXT
);

-- Proposed (with StringID)
CREATE TABLE tm_entries (
    id SERIAL PRIMARY KEY,
    tm_id INTEGER,
    source_text TEXT,
    target_text TEXT,
    string_id TEXT,           -- NEW: Optional StringID
    context TEXT,             -- NEW: Optional context hint
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    UNIQUE(tm_id, source_text, string_id)  -- Compound unique constraint
);
```

### Technical Feasibility: YES - Here's Why

**Key Insight:** Embeddings are based on SOURCE TEXT only. StringID is just metadata for selection.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    END-TO-END STRINGID IMPLEMENTATION                        │
│                                                                             │
│  ════════════════════════════════════════════════════════════════════════  │
│  PHASE 1: TM CREATION (User uploads file with Source/Target/StringID)      │
│  ════════════════════════════════════════════════════════════════════════  │
│                                                                             │
│  Input File:                                                               │
│  ┌──────────────┬───────────────────┬────────────────────────┐            │
│  │ Source       │ Target            │ StringID               │            │
│  ├──────────────┼───────────────────┼────────────────────────┤            │
│  │ 저장         │ Save              │ UI_BUTTON_SAVE         │            │
│  │ 저장         │ Save Game         │ UI_MENU_SAVE           │            │
│  │ 저장         │ I'll keep it safe │ DIALOGUE_SAVE_NPC      │            │
│  │ 취소         │ Cancel            │ UI_CANCEL              │            │
│  └──────────────┴───────────────────┴────────────────────────┘            │
│                                                                             │
│  Step 1: Precheck (StringID Mode)                                          │
│  └── All rows have Source + Target + StringID? → YES, proceed             │
│                                                                             │
│  Step 2: Database Insert                                                   │
│  └── INSERT INTO tm_entries (source_text, target_text, string_id)         │
│      4 rows inserted (NOT deduplicated - we keep all variations)          │
│                                                                             │
│  Step 3: Build Embeddings (source only, deduplicated)                      │
│  └── Unique sources: ["저장", "취소"] → 2 embeddings                       │
│  └── embeddings.npy shape: (2, 768)                                        │
│                                                                             │
│  Step 4: Build PKL with variations                                         │
│  └── {                                                                     │
│          "저장": [                                                          │
│              {"target": "Save", "string_id": "UI_BUTTON_SAVE", "entry_id": 1},│
│              {"target": "Save Game", "string_id": "UI_MENU_SAVE", "entry_id": 2},│
│              {"target": "I'll keep it safe", "string_id": "DIALOGUE_SAVE_NPC", "entry_id": 3}│
│          ],                                                                │
│          "취소": [                                                          │
│              {"target": "Cancel", "string_id": "UI_CANCEL", "entry_id": 4} │
│          ]                                                                 │
│      }                                                                     │
│                                                                             │
│  Result:                                                                   │
│  - embeddings.npy: 2 vectors (one per unique source)                       │
│  - pkl: 2 keys, but "저장" has 3 variations                                │
│  - Alignment: embeddings[0] → "저장" → pkl["저장"] (all 3 variations)      │
│                                                                             │
│  ════════════════════════════════════════════════════════════════════════  │
│  PHASE 2: PRETRANSLATION (User has new file to translate)                  │
│  ════════════════════════════════════════════════════════════════════════  │
│                                                                             │
│  Input: New file with Source + StringID (no Target yet)                    │
│  ┌──────────────┬────────────────────────┐                                 │
│  │ Source       │ StringID               │                                 │
│  ├──────────────┼────────────────────────┤                                 │
│  │ 저장         │ UI_BUTTON_SAVE         │  ← Want to find translation    │
│  │ 저장         │ NEW_SAVE_CONTEXT       │  ← New StringID, no exact match│
│  │ 새로운       │ UI_NEW                 │  ← New source, no match at all │
│  └──────────────┴────────────────────────┘                                 │
│                                                                             │
│  Query 1: Source="저장", StringID="UI_BUTTON_SAVE"                         │
│  ├── Step A: Embed "저장" → vector                                         │
│  ├── Step B: FAISS search → finds "저장" at 100% similarity               │
│  ├── Step C: Get variations from PKL → 3 options                          │
│  ├── Step D: StringID exact match? → YES! "UI_BUTTON_SAVE" exists         │
│  └── Result: "Save" (exact StringID match, confidence=100%)               │
│                                                                             │
│  Query 2: Source="저장", StringID="NEW_SAVE_CONTEXT"                       │
│  ├── Step A: Embed "저장" → vector                                         │
│  ├── Step B: FAISS search → finds "저장" at 100% similarity               │
│  ├── Step C: Get variations from PKL → 3 options                          │
│  ├── Step D: StringID exact match? → NO, "NEW_SAVE_CONTEXT" not found     │
│  └── Result: Return ALL 3 variations for user to choose                   │
│      [                                                                     │
│        {"target": "Save", "string_id": "UI_BUTTON_SAVE"},                 │
│        {"target": "Save Game", "string_id": "UI_MENU_SAVE"},              │
│        {"target": "I'll keep it safe", "string_id": "DIALOGUE_SAVE_NPC"} │
│      ]                                                                     │
│                                                                             │
│  Query 3: Source="새로운", StringID="UI_NEW"                               │
│  ├── Step A: Embed "새로운" → vector                                       │
│  ├── Step B: FAISS search → no match above threshold                      │
│  └── Result: No match found                                                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Why This is Technically Doable

| Concern | Answer |
|---------|--------|
| **Embedding alignment?** | No change needed! Embeddings are per unique SOURCE. Variations are metadata in PKL. |
| **FAISS search change?** | No change! Search by source embedding, then filter by StringID in post-processing. |
| **Database change?** | Minor: Add `string_id` column to `tm_entries` table. |
| **PKL format change?** | Yes: Change from `{source: target}` to `{source: [variations]}` |
| **Backward compatible?** | Yes: If `string_id` is NULL, behave like current system (single target per source). |

### Implementation Steps

```python
# Step 1: Modify TM entry model (database)
class LDMTMEntry(Base):
    id = Column(Integer, primary_key=True)
    tm_id = Column(Integer, ForeignKey('ldm_tms.id'))
    source_text = Column(Text, nullable=False)
    target_text = Column(Text, nullable=False)
    string_id = Column(Text, nullable=True)  # NEW - optional

# Step 2: Modify PKL builder (tm_indexer.py)
def _build_whole_lookup_with_stringid(self, entries):
    lookup = {}
    for entry in entries:
        source = normalize_for_hash(entry["source_text"])
        if source not in lookup:
            lookup[source] = []
        lookup[source].append({
            "entry_id": entry["id"],
            "target_text": entry["target_text"],
            "string_id": entry.get("string_id")
        })
    return lookup

# Step 3: Modify search to handle variations (tm_indexer.py)
def search_with_stringid(self, source: str, string_id: str = None):
    # Get all variations for this source
    variations = self.lookup.get(normalize_for_hash(source), [])

    if not variations:
        return None

    # If StringID provided, try exact match first
    if string_id:
        for var in variations:
            if var.get("string_id") == string_id:
                return {"match": var, "exact_stringid": True}

    # No exact StringID match - return all variations
    return {"match": variations[0], "alternatives": variations, "exact_stringid": False}
```

### Open Questions

- [ ] What if user doesn't provide StringID in the file? (Default to NULL, match by source only?)
- [ ] Should StringID matching be exact or fuzzy? (UI_BUTTON_SAVE vs UI_BTN_SAVE)
- [ ] How to handle TM uploads from files without StringID column?
- [ ] UI: How to display multiple variations to user?

---

## 3. Excel to TM Creation Flow

### Supported Excel Structures

**Two valid structures:**

```
STRUCTURE A: Source + Target (Standard TM)
══════════════════════════════════════════
┌──────────────────┬──────────────────┐
│ Source           │ Target           │
├──────────────────┼──────────────────┤
│ 저장             │ Save             │
│ 취소             │ Cancel           │
│ 확인             │ OK               │
└──────────────────┴──────────────────┘

→ General purpose TM
→ Duplicates: most frequent target wins
→ Simple 1:1 source→target matching


STRUCTURE B: Source + Target + StringID (Precise TM)
════════════════════════════════════════════════════
┌──────────────────┬──────────────────┬──────────────────┐
│ Source           │ Target           │ StringID         │
├──────────────────┼──────────────────┼──────────────────┤
│ 저장             │ Save             │ UI_BUTTON_SAVE   │
│ 저장             │ Save Game        │ UI_MENU_SAVE     │
│ 저장             │ I'll keep it     │ DIALOGUE_NPC     │
│ 취소             │ Cancel           │ UI_CANCEL        │
└──────────────────┴──────────────────┴──────────────────┘

→ Context-aware TM (game UI vs dialogue)
→ Keeps ALL variations (no deduplication)
→ StringID matching for precise results
```

### User Flow: Excel → TM

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    EXCEL TO TM CREATION FLOW                                 │
│                                                                             │
│  Step 1: User right-clicks Excel file in File Explorer                     │
│  ════════════════════════════════════════════════════════════════════════  │
│                                                                             │
│  ┌────────────────────────────────┐                                        │
│  │  📥 Download File               │                                        │
│  │  ─────────────────────────────  │                                        │
│  │  📚 Create TM from this file... │ ← User clicks this                    │
│  │  ─────────────────────────────  │                                        │
│  │  🔍 Run Full QA Check           │                                        │
│  └────────────────────────────────┘                                        │
│                                                                             │
│  Step 2: TM Creation Modal appears                                         │
│  ════════════════════════════════════════════════════════════════════════  │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     CREATE TM FROM EXCEL                             │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │                                                                      │   │
│  │  Source File: game_strings_2025.xlsx                                │   │
│  │  Detected Rows: 12,450                                              │   │
│  │                                                                      │   │
│  │  ═══ TM NAME ═══                                                    │   │
│  │                                                                      │   │
│  │  Name: [ BDO_UI_Terms_v1                    ]                       │   │
│  │        ✅ Name is valid                                             │   │
│  │                                                                      │   │
│  │  ═══ TM MODE ═══                                                    │   │
│  │                                                                      │   │
│  │  ○ Standard Mode (Source + Target)                                  │   │
│  │    └── General purpose, duplicates merged                           │   │
│  │                                                                      │   │
│  │  ● StringID Mode (Source + Target + StringID)                       │   │
│  │    └── Precise matching, keeps all variations                       │   │
│  │                                                                      │   │
│  │  ═══ COLUMN MAPPING ═══                                             │   │
│  │                                                                      │   │
│  │  Source Column:   [ A ▼ ]  Preview: 저장, 취소, 확인...             │   │
│  │  Target Column:   [ B ▼ ]  Preview: Save, Cancel, OK...             │   │
│  │  StringID Column: [ C ▼ ]  Preview: UI_BTN_SAVE, UI_CANCEL...       │   │
│  │                                                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  Step 3: Data Validation (automatic)                                       │
│  ════════════════════════════════════════════════════════════════════════  │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  ═══ DATA VALIDATION ═══                                            │   │
│  │                                                                      │   │
│  │  Standard Mode:                         StringID Mode:              │   │
│  │  ┌─────────────────────────────┐       ┌─────────────────────────┐ │   │
│  │  │ Total rows: 12,450          │       │ Total rows: 12,450      │ │   │
│  │  │ Valid rows: 12,380 ✅       │       │ Valid rows: 12,450 ✅   │ │   │
│  │  │ Skipped (no target): 70     │       │ Missing Source: 0       │ │   │
│  │  │ After dedup: 8,920          │       │ Missing Target: 0       │ │   │
│  │  │                             │       │ Missing StringID: 0     │ │   │
│  │  │ Ready to process ✅         │       │ Ready to process ✅     │ │   │
│  │  └─────────────────────────────┘       └─────────────────────────┘ │   │
│  │                                                                      │   │
│  │  ⚠️ StringID Mode ERROR example:                                    │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │ ❌ Cannot process in StringID Mode                          │   │   │
│  │  │                                                             │   │   │
│  │  │ Data has discrepancies:                                     │   │   │
│  │  │ - Rows missing Source: 5                                    │   │   │
│  │  │ - Rows missing Target: 23                                   │   │   │
│  │  │ - Rows missing StringID: 142                                │   │   │
│  │  │                                                             │   │   │
│  │  │ Please clean your data or use Standard Mode instead.        │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  │                                                                      │   │
│  │                        [Cancel]  [Create TM]                        │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  Step 4: Processing (background task)                                      │
│  ════════════════════════════════════════════════════════════════════════  │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Creating TM "BDO_UI_Terms_v1"...                                   │   │
│  │                                                                      │   │
│  │  ████████████████░░░░░░░░ 68%                                       │   │
│  │                                                                      │   │
│  │  Stage: Building embeddings                                         │   │
│  │  Progress: 8,500 / 12,450 entries                                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  Step 5: TM appears in TM Explorer                                         │
│  ════════════════════════════════════════════════════════════════════════  │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  📁 Translation Memories                                            │   │
│  │  ├── 📚 BDO_EN_Main (45,230 entries)                               │   │
│  │  ├── 📚 BDO_KR_Reference (32,100 entries)                          │   │
│  │  └── 📚 BDO_UI_Terms_v1 (12,450 entries) [StringID] ← NEW          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### TM Naming Validation

```python
def validate_tm_name(name: str) -> tuple[bool, str]:
    """
    Validate TM name before creation.

    Rules:
    1. Not empty
    2. 3-50 characters
    3. Only: letters, numbers, underscore, hyphen, space
    4. No leading/trailing spaces
    5. Not duplicate of existing TM

    Returns: (is_valid, error_message)
    """
    if not name or not name.strip():
        return False, "Name cannot be empty"

    name = name.strip()

    if len(name) < 3:
        return False, "Name must be at least 3 characters"

    if len(name) > 50:
        return False, "Name must be 50 characters or less"

    import re
    if not re.match(r'^[a-zA-Z0-9_\- ]+$', name):
        return False, "Only letters, numbers, underscore, hyphen, space allowed"

    # Check duplicate
    existing = get_existing_tm_names()
    if name.lower() in [n.lower() for n in existing]:
        return False, f"TM '{name}' already exists"

    return True, ""
```

### Data Validation by Mode

```python
def validate_excel_for_tm(df: pd.DataFrame, mode: str) -> dict:
    """
    Validate Excel data before TM creation.

    Args:
        df: DataFrame with Source, Target, (optional StringID)
        mode: "standard" or "stringid"

    Returns:
        {
            "valid": bool,
            "total_rows": int,
            "valid_rows": int,
            "errors": list,
            "warnings": list
        }
    """
    result = {
        "valid": True,
        "total_rows": len(df),
        "valid_rows": 0,
        "errors": [],
        "warnings": []
    }

    if mode == "standard":
        # Lenient: skip rows without source OR target
        valid_mask = df['source'].notna() & df['target'].notna()
        valid_mask &= (df['source'] != '') & (df['target'] != '')
        result["valid_rows"] = valid_mask.sum()
        result["skipped"] = len(df) - result["valid_rows"]

        if result["skipped"] > 0:
            result["warnings"].append(f"{result['skipped']} rows skipped (missing source/target)")

    elif mode == "stringid":
        # Strict: ALL rows must have source + target + stringid
        missing_source = df['source'].isna().sum() + (df['source'] == '').sum()
        missing_target = df['target'].isna().sum() + (df['target'] == '').sum()
        missing_stringid = df['string_id'].isna().sum() + (df['string_id'] == '').sum()

        if missing_source > 0 or missing_target > 0 or missing_stringid > 0:
            result["valid"] = False
            result["errors"].append(f"Missing Source: {missing_source}")
            result["errors"].append(f"Missing Target: {missing_target}")
            result["errors"].append(f"Missing StringID: {missing_stringid}")
        else:
            result["valid_rows"] = len(df)

    return result
```

---

## 4. Glossary Creation Flow

**Translation of entries requires external API → FUTURE feature**

### Flow Design

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    GLOSSARY CREATION FLOW                                    │
│                                                                             │
│  Step 1: User right-clicks file → "Create Glossary..."                     │
│                                                                             │
│  Step 2: Modal appears                                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │              CREATE GLOSSARY                                         │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │                                                                      │   │
│  │  Source File: game_strings_2025.xlsx                                │   │
│  │  Rows: 12,450                                                       │   │
│  │                                                                      │   │
│  │  Glossary Name: [ BDO_UI_Terms_v1              ]                    │   │
│  │                  └── Validation: no duplicates, valid chars         │   │
│  │                                                                      │   │
│  │  ═══ EXTRACTION RULES ═══                                           │   │
│  │                                                                      │   │
│  │  Max length:    [ 26 ] characters                                   │   │
│  │  [ ] Include sentences (ending with . ! ?)                          │   │
│  │  [x] Skip duplicates (same source text)                             │   │
│  │                                                                      │   │
│  │  ═══ PREVIEW ═══                                                    │   │
│  │                                                                      │   │
│  │  Unique terms found: 2,340                                          │   │
│  │  After filtering: 1,892                                             │   │
│  │  Already in existing TMs: 1,450                                     │   │
│  │  NEW terms to add: 442                                              │   │
│  │                                                                      │   │
│  │                        [Cancel]  [Create Glossary]                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  Step 3: Processing (background task with progress)                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Creating glossary "BDO_UI_Terms_v1"...                             │   │
│  │  ████████████░░░░░░░░ 62%                                           │   │
│  │  Processing: 275/442 terms                                          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  Step 4: Glossary appears in TM Explorer                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  📁 Translation Memories                                            │   │
│  │  ├── 📚 BDO_EN_Main (45,230 entries)                               │   │
│  │  ├── 📚 BDO_KR_Reference (32,100 entries)                          │   │
│  │  └── 📝 BDO_UI_Terms_v1 (442 entries) ← NEW (source-only)          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Naming Validation

```python
def validate_glossary_name(name: str) -> tuple[bool, str]:
    """
    Validate glossary name before creation.

    Rules:
    - Not empty
    - 3-50 characters
    - Only alphanumeric, underscore, hyphen, space
    - No leading/trailing spaces
    - Not a duplicate of existing TM/glossary name

    Returns: (is_valid, error_message)
    """
    # Check empty
    if not name or not name.strip():
        return False, "Name cannot be empty"

    name = name.strip()

    # Check length
    if len(name) < 3:
        return False, "Name must be at least 3 characters"
    if len(name) > 50:
        return False, "Name must be 50 characters or less"

    # Check characters
    import re
    if not re.match(r'^[a-zA-Z0-9_\- ]+$', name):
        return False, "Name can only contain letters, numbers, underscore, hyphen, and space"

    # Check duplicate
    existing = get_existing_tm_names()
    if name.lower() in [n.lower() for n in existing]:
        return False, f"A TM/Glossary named '{name}' already exists"

    return True, ""
```

### Glossary Entry Structure

```python
# Source-only glossary entry (target filled later)
{
    "source_text": "저장하기",
    "target_text": None,           # NULL - to be filled later
    "string_id": "UI_BUTTON_SAVE", # Optional - if available in source file
    "status": "untranslated",      # untranslated | translated | reviewed
    "created_at": "2025-12-17T11:00:00Z",
    "source_file": "game_strings_2025.xlsx"
}
```

### Open Questions

- [ ] Should glossaries be visually different from TMs in the explorer? (different icon?)
- [ ] Can user edit entries directly in the glossary? (add target manually)
- [ ] How to merge a glossary into an existing TM?
- [ ] Should we track which file the term came from?

---

## 4. Data Preprocessing Strategy

### EXISTING ROBUST LOGIC (Already Implemented!)

We already have comprehensive data preprocessing across both XLS Transfer and LDM:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    EXISTING PREPROCESSING LOGIC                              │
│                                                                             │
│  ╔═══════════════════════════════════════════════════════════════════════╗ │
│  ║ XLS TRANSFER (process_operation.py)                                    ║ │
│  ╠═══════════════════════════════════════════════════════════════════════╣ │
│  ║ Line 85:  df.dropna()           → Skip rows without source OR target  ║ │
│  ║ Line 87:  clean_text()          → Remove _x000D_, strip whitespace    ║ │
│  ║ Line 112: groupby.agg(most_freq) → Most frequent translation wins     ║ │
│  ║ Line 112: dropna()              → Remove any remaining NaN values     ║ │
│  ╚═══════════════════════════════════════════════════════════════════════╝ │
│                                                                             │
│  ╔═══════════════════════════════════════════════════════════════════════╗ │
│  ║ LDM TM MANAGER (tm_manager.py)                                         ║ │
│  ╠═══════════════════════════════════════════════════════════════════════╣ │
│  ║ Line 431: Filter comprehension  → Only keep entries with BOTH         ║ │
│  ║           source AND target present (skip empty)                       ║ │
│  ╚═══════════════════════════════════════════════════════════════════════╝ │
│                                                                             │
│  ╔═══════════════════════════════════════════════════════════════════════╗ │
│  ║ LDM TM INDEXER (tm_indexer.py)                                         ║ │
│  ╠═══════════════════════════════════════════════════════════════════════╣ │
│  ║ Line 370: if not source: continue     → Skip entries without source   ║ │
│  ║ Line 378: if not line.strip(): continue → Skip empty lines            ║ │
│  ║ Line 430: if not source: continue     → Skip for embeddings           ║ │
│  ║ Line 434: if normalized:              → Only embed non-empty text     ║ │
│  ║ Line 102: normalize_for_embedding()   → Normalize whitespace          ║ │
│  ║ Line 89:  normalize_for_hash()        → Lowercase + normalize         ║ │
│  ╚═══════════════════════════════════════════════════════════════════════╝ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Summary: What's Already Handled

| Issue | XLS Transfer | LDM | Status |
|-------|-------------|-----|--------|
| Empty source | `dropna()` | `if not source: continue` | ✅ HANDLED |
| Empty target | `dropna()` | Filter comprehension | ✅ HANDLED |
| Empty lines | N/A | `if not line.strip(): continue` | ✅ HANDLED |
| Control chars | `clean_text()` | N/A (clean on upload) | ✅ HANDLED |
| Whitespace | `clean_text()` | `normalize_for_embedding()` | ✅ HANDLED |
| Duplicate sources | Most frequent wins | First occurrence wins | ✅ HANDLED |

### Code References

**XLS Transfer - process_operation.py:85-112:**
```python
# Skip rows without translation
df = df.iloc[:, [col_kr_index, col_fr_index]].dropna()

# Clean text
kr_texts = df.iloc[:, 0].apply(clean_text).tolist()
fr_texts = df.iloc[:, 1].apply(clean_text).tolist()

# Most frequent translation wins
most_freq_trans = df.groupby('KR')['FR'].agg(safe_most_frequent).reset_index()
most_freq_trans = most_freq_trans.dropna()
```

**LDM - tm_manager.py:425-432:**
```python
# Only keep entries with BOTH source AND target
formatted_entries = [
    {"source_text": e.get("source") or e.get("source_text"),
     "target_text": e.get("target") or e.get("target_text")}
    for e in entries
    if (e.get("source") or e.get("source_text")) and (e.get("target") or e.get("target_text"))
]
```

**LDM - tm_indexer.py:370-384:**
```python
for entry in entries:
    source = entry["source_text"]
    if not source:
        continue  # Skip entries without source

    for i, line in enumerate(source_lines):
        if not line.strip():
            continue  # Skip empty lines

        normalized_line = normalize_for_hash(line)
        if not normalized_line:
            continue  # Skip if normalization produces empty string
```

### What This Means for P36

**We DON'T need to re-implement preprocessing!**

The existing logic already:
1. Skips rows without source or target
2. Cleans control characters and whitespace
3. Handles duplicates (most frequent or first wins)
4. Normalizes text for both hash and embedding matching

### Additional Preprocessing (Optional Enhancement)

The only NEW preprocessing we might add from WebTranslatorNew is:

| Feature | Source | Benefit |
|---------|--------|---------|
| DB duplicate check BEFORE embedding | `preprocessor.py` | Skip already-in-TM entries |

```python
# OPTIONAL: Check if entry already exists in TM before processing
existing_pairs = {(e.source_text, e.target_text) for e in existing_entries}
new_entries = [e for e in entries if (e.source, e.target) not in existing_pairs]
```

This is an OPTIMIZATION, not a requirement. We can add it later if needed.

### Preprocessing Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    DATA PREPROCESSING FLOW                                   │
│                                                                             │
│  Input: 1,000 rows from uploaded file                                      │
│                                                                             │
│  Step 1: Remove empty rows                                                 │
│          ├── 1,000 rows                                                    │
│          └── 985 rows (15 empty removed)                                   │
│                                                                             │
│  Step 2: Clean whitespace and control chars                                │
│          └── 985 rows (cleaned in-place)                                   │
│                                                                             │
│  Step 3: Resolve duplicates within file                                    │
│          ├── 985 rows                                                      │
│          ├── Found 45 duplicate sources                                    │
│          └── 940 unique entries                                            │
│                                                                             │
│  Step 4: Check against existing TM                                         │
│          ├── 940 entries                                                   │
│          ├── 720 already exist (exact source+target match)                │
│          └── 220 NEW entries to add                                        │
│                                                                             │
│  Output: 220 entries ready for embedding generation                        │
│                                                                             │
│  Summary shown to user:                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Upload Summary:                                                     │   │
│  │  - Total rows: 1,000                                                │   │
│  │  - Empty removed: 15                                                │   │
│  │  - Duplicates merged: 45                                            │   │
│  │  - Already in TM: 720                                               │   │
│  │  - NEW to add: 220                                                  │   │
│  │                                                                      │   │
│  │  [Cancel]  [Add 220 new entries]                                    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Open Questions

- [ ] Should preprocessing happen on upload or on-demand?
- [ ] How to handle encoding issues (UTF-8 BOM, etc.)?
- [ ] Should we log what was removed/merged for audit?

---

## Summary of Recommendations

| Topic | Recommendation | Status |
|-------|----------------|--------|
| **Batch Processing** | Chunked (500 rows) + Multiprocessing (4 workers) | TO IMPLEMENT |
| **StringID Handling** | User choice: Standard (lenient) vs StringID (strict precheck) | TO IMPLEMENT |
| **Glossary Creation** | User names first, validates, appears in TM explorer | TO IMPLEMENT |
| **Data Preprocessing** | Already robust! Skip empty, clean text, handle duplicates | ✅ EXISTS |

---

## Key Takeaways

### What's Already Done (Don't Re-implement!)

1. **Data Cleaning** - `clean_text()`, `dropna()`, skip empty rows
2. **Duplicate Handling** - Most frequent translation wins (XLS), first wins (LDM)
3. **Normalization** - `normalize_for_hash()`, `normalize_for_embedding()`
4. **5-Tier Cascade** - Hash → FAISS HNSW → N-gram (already in tm_indexer.py)

### What's New to Implement

1. **StringID Mode** - Strict precheck, compound key with variations
2. **Batch Optimization** - Chunked + Multiprocessing for large files
3. **Glossary Creation** - Right-click → name → extract to TM explorer
4. **Unified Pretranslation API** - `/api/ldm/pretranslate` with engine selection

---

## Next Steps

1. [ ] Review and approve these design decisions
2. [ ] Address open questions (especially StringID matching strategy)
3. [ ] Create detailed API specs based on decisions
4. [ ] Begin implementation

---

*Created: 2025-12-17*
*Status: AWAITING REVIEW*
