# P36: Unified Pretranslation System

**Priority:** P36 | **Status:** Phase 1 COMPLETE ✅, Phase 2 PLANNED | **Created:** 2025-12-16 | **Updated:** 2025-12-17

---

## Core Principles

```
┌──────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│  1. TM DATABASE = SINGLE SOURCE OF TRUTH                                │
│                                                                          │
│  2. QWEN = TEXT SIMILARITY (NOT MEANING)                                │
│     - "저장" vs "저장" = 100% ✅                                          │
│     - "저장" vs "세이브" = 58% (different text, correctly low)          │
│     - We match TEXT patterns, not semantic meaning                      │
│                                                                          │
│  All pretranslation modes use the SAME TM:                              │
│  - Same whole/split embeddings                                          │
│  - Same FAISS indexes                                                   │
│  - Different modes = different POST-PROCESSING on top                   │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Architecture

```
TM Database (PostgreSQL)
    │
    ↓ Export / Sync to local dictionaries
    │
┌───────────────────────────────────────────────────────────────────────┐
│                                                                       │
│  THREE SEPARATE PRETRANSLATION ENGINES (each proven, use as-is):     │
│                                                                       │
│  1. STANDARD (TM)                                                    │
│     └── Uses: TM 5-tier cascade (hash + FAISS + ngram)              │
│     └── Logic: server/tools/ldm/tm_indexer.py                       │
│                                                                       │
│  2. XLS TRANSFER (proven tool - use exact same logic)               │
│     └── Uses: Own split/whole dictionaries + FAISS                  │
│     └── Logic: server/tools/xlstransfer/ (AS-IS)                    │
│     └── Extras: Code preservation, newline adaptation               │
│                                                                       │
│  3. KR SIMILAR (proven tool - use exact same logic)                 │
│     └── Uses: Own split/whole dictionaries + FAISS                  │
│     └── Logic: server/tools/kr_similar/ (AS-IS)                     │
│     └── Extras: Structure adaptation, ▶ markers                     │
│                                                                       │
│  NO REDUNDANCY: Each mode uses its OWN complete logic.              │
│  User selects which engine to use in the pretranslation modal.      │
│                                                                       │
└───────────────────────────────────────────────────────────────────────┘
```

**Key Principle:** XLS Transfer and KR Similar are PROVEN tools used by the team. Do NOT modify their logic. Use them exactly as they are.

---

## Pretranslation Modal UI

**Access:** Right-click file → "Pretranslate..."

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         PRETRANSLATE FILE                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  File: game_strings_2025.xlsx                                          │
│  Rows: 12,450                                                          │
│                                                                         │
│  ═══ DICTIONARY SOURCE ═══                                             │
│                                                                         │
│  [▼ BDO_EN_Main (45,230 entries)                               ]      │
│                                                                         │
│  ═══ PRETRANSLATION ENGINE ═══                                         │
│                                                                         │
│  ● Standard (TM 5-Tier)                                                │
│      Hash lookup + FAISS embedding + N-gram fallback                   │
│                                                                         │
│  ○ XLS Transfer                                                        │
│      Split/whole matching + code preservation                          │
│      Best for: files with {ItemID}, <PAColor> tags                     │
│                                                                         │
│  ○ KR Similar                                                          │
│      Split/whole matching + structure adaptation                       │
│      Best for: Korean dialogue with ▶ markers                          │
│                                                                         │
│  ═══ THRESHOLD ═══                                                     │
│                                                                         │
│  Minimum similarity: [ 90 ] %  ←───────●───── (50% - 100%)            │
│                                                                         │
│  ═══ OPTIONS ═══                                                       │
│                                                                         │
│  [x] Skip rows that already have translation                           │
│  [ ] Overwrite existing translations                                   │
│                                                                         │
│                                                                         │
│                           [Cancel]  [⚡ Pretranslate]                   │
└─────────────────────────────────────────────────────────────────────────┘
```

**Note:** Each engine is INDEPENDENT. Select the one that matches your workflow.

---

## Mode Details

### Mode 1: Standard (TM 5-Tier)

**Uses:** `server/tools/ldm/tm_indexer.py`

**What it does:**
- 5-tier cascade search (hash → embedding → ngram)
- Pure TM matching, no post-processing

**Best for:**
- Clean text without game codes
- Simple source/target pairs
- When you want TM-style matching

### Mode 2: XLS Transfer (Proven Tool - AS-IS)

**Uses:** `server/tools/xlstransfer/` - DO NOT MODIFY

**What it does:**
- XLS Transfer's own split/whole dictionary + FAISS matching
- Code preservation (`simple_number_replace()`)
- Newline auto-adaptation
- Multi-mode fallback (whole → split)

**Code patterns handled:**
```
{ItemID:123}     → Game item codes
{ChangeScene()}  → Function calls
<PAColor>        → Color tags
<Scale>          → Formatting tags
```

**Best for:**
- Game localization files with codes
- Production file transfer workflows

### Mode 3: KR Similar (Proven Tool - AS-IS)

**Uses:** `server/tools/kr_similar/` - DO NOT MODIFY

**What it does:**
- KR Similar's own split/whole dictionary + FAISS matching
- Structure adaptation (`adapt_structure()`)
- Triangle marker handling (▶)
- Line-by-line semantic matching

**Best for:**
- Korean game text with specific formatting
- Multi-line dialogue with markers
- Korean-specific similarity search

### Mode Selection (NOT Cascade)

**Important:** These are SEPARATE engines, not layered.

```
User selects ONE mode:
○ Standard (TM)      → Uses TM 5-tier cascade
○ XLS Transfer       → Uses XLS Transfer logic (proven)
○ KR Similar         → Uses KR Similar logic (proven)

Each mode runs INDEPENDENTLY with its own matching algorithm.
No redundant cascade between modes.
```

---

## Threshold Guidelines

| Threshold | Use Case | Expected Behavior |
|-----------|----------|-------------------|
| **95-100%** | Exact/near-exact only | Very conservative, few matches |
| **92%** | Production quality | Good balance (recommended) |
| **85%** | More coverage | May include looser matches |
| **75%** | Maximum coverage | Review required, may have errors |

---

## TM Merge System

Users can add content to TM from multiple sources:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           MERGE INTO TM                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Target TM: BDO_EN_Main                                                │
│                                                                         │
│  Upload file to merge:                                                 │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  [📁 Choose File...]                                            │   │
│  │                                                                 │   │
│  │  Supported formats:                                             │   │
│  │  • Excel (.xlsx) - A/B column structure                        │   │
│  │  • XML - standard structure                                     │   │
│  │  • TEXT (.txt) - TSV structure                                 │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  Preview:                                                              │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  + 127 new entries (INSERT)                                     │   │
│  │  ~ 45 updated entries (UPDATE)                                  │   │
│  │  = 12,340 unchanged (SKIP)                                      │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│                           [Cancel]  [Merge]                            │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: QWEN Validation - COMPLETED

**Test Date:** 2025-12-16 | **Result:** 26/27 passed (96.3%)

### Test Results Summary

```
================================================================================
 QWEN VALIDATION RESULTS (Qwen/Qwen3-Embedding-0.6B)
================================================================================

 Korean Tests:    14/14 passed (100%)
 English Tests:    7/7 passed (100%)
 Multiline Tests:  4/4 passed (100%)
 Code Strip Tests: 1/2 passed (50%)  ← False failure (100% vs 99-100% range)

 OVERALL: 26/27 passed (96.3%) ✅ QWEN VALIDATED
================================================================================
```

### Actual Similarity Scores

| Category | Test Case | Score | Assessment |
|----------|-----------|-------|------------|
| **Identical** | Same Korean text | 100% | Perfect |
| **Punctuation** | "저장하시겠습니까?" vs "저장하시겠습니까" | 97.4% | Excellent |
| **Punctuation** | "완료되었습니다!" vs "완료되었습니다" | 90.2% | Good |
| **Whitespace** | Extra space | 97.7% | Excellent |
| **One Word Diff** | 파일→문서 | 84.0% | Good separation |
| **One Word Diff** | 시작→종료 | 68.1% | Good separation |
| **Synonym Korean** | Formal vs casual | 83.6%-86.6% | Good |
| **Opposite** | Save vs Delete | 71.9% | Correctly low |
| **Opposite** | Start vs End | 63.9% | Correctly low |
| **Unrelated** | Save vs weather | 37.2% | Correctly very low |
| **Multiline Reorder** | Same content, different order | 88.8% | Good |

### English NPC Validation (Critical)

| Test Case | Score | Status |
|-----------|-------|--------|
| "Save" vs "Save file" | 70.6% | ⚠️ Would FAIL at 80% |
| "Save" vs "Save changes" | 61.3% | ⚠️ Would FAIL at 80% |
| "Cancel" vs "Cancel operation" | 71.8% | ⚠️ Would FAIL at 80% |

**CONFIRMED:** NPC 80% threshold is TOO STRICT for short English strings.

### Threshold Recommendations (From Test Data)

| Use Case | Current | Recommended | Reason |
|----------|---------|-------------|--------|
| **TM Matching** | 92% | **90%** | Punctuation removal scores 90.2% |
| **NPC Check** | 80% | **65%** | Short variations score 61-72% |
| **False Positive Avoidance** | - | **>72%** | Opposite meanings score up to 71.9% |

### Safe Operating Range

```
           0%                                                          100%
            │                                                            │
 UNRELATED  │▓▓▓▓▓▓▓▓▓▓▓▓│                                              │
            │   26-37%    │                                              │
            │             │                                              │
 OPPOSITE   │             │▓▓▓▓▓▓▓▓▓▓▓▓│                                │
            │             │   64-72%    │                                │
            │             │             │                                │
 SEMANTIC   │             │             │▓▓▓▓▓▓▓▓▓▓▓▓▓▓│                │
            │             │             │    68-87%     │                │
            │             │             │               │                │
 EXACT      │             │             │               │▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓│
            │             │             │               │     90-100%    │
            │             │             │               │                │
            └─────────────┴─────────────┴───────────────┴────────────────┘
                         65%           72%             90%

            │←── NPC ──→│ │←─ DANGER ─→│ │←── TM MATCH ────────────────→│
```

### Test File Location

`tests/fixtures/pretranslation/test_qwen_validation.py`

Run with: `python3 tests/fixtures/pretranslation/test_qwen_validation.py`

---

## Workflow Analysis - COMPLETED ✅

### KR Similar - VERIFIED ✅

**Key Functions:**
- `auto_translate()` at `searcher.py:275-424`
- `adapt_structure()` at `core.py:17-89`

**How it works:**
1. Text WITH `▶` markers → Line-by-line split matching against split_index
2. Text WITHOUT `▶` → Whole-first matching, then `adapt_structure()` distributes translation
3. Uses `\\n` literals (NOT actual newlines) - this is the language data file format

**Technical details:**
- FAISS HNSW with efConstruction=400, efSearch=500
- Model: `Qwen/Qwen3-Embedding-0.6B`
- Normalized L2 embeddings with METRIC_INNER_PRODUCT

### XLS Transfer - VERIFIED ✅

**Key Functions:**
- `translate_text_multi_mode()` at `translation.py:153-222`
- `simple_number_replace()` at `core.py:274-353`

**How it works:**
1. Whole-first matching against whole_index
2. Fallback to split mode (line-by-line)
3. `simple_number_replace()` preserves game codes

**Status:** Matches original monolith exactly. No changes needed.
Production-proven code - only fix if specific user feedback received.

---

## Implementation Plan

### Phase 1: Validation - COMPLETE ✅

#### E2E Test Results (2025-12-17)

| Test Suite | Passed | Failed | Status |
|------------|--------|--------|--------|
| XLS Transfer E2E | 537 | 0 | ✅ |
| KR Similar E2E | 530 | 0 | ✅ |
| Standard TM E2E | 566 | 0 | ✅ |
| **QWEN+FAISS Real E2E** | **500 queries** | **0** | ✅ |
| QWEN validation | 26 | 1 | ✅ |
| Real patterns | 13 | 0 | ✅ |
| **TOTAL** | **2,172** | **1** | ✅ |

#### QWEN+FAISS Real Test Results

```
TM: 165 entries | Queries: 500 | Time: 74s

Tier Distribution:
├── Tier 1 (Hash exact): 105 (21%) ✅
├── Tier 2 (FAISS embedding): 25 (5%) ✅
├── Tier 3 (Line hash): 50 (10%) ✅
└── Tier 0 (No match): 320 (64%) - correctly rejected

Category Results:
├── Exact matches: 100/100 → Tier 1 ✅
├── Line matches: 50/50 → Tier 3 ✅
└── Unrelated: 100/100 rejected ✅
```

#### Korean Text Similarity (Verified)

QWEN handles **text similarity** correctly (not semantic meaning):

| Category | Score | Status |
|----------|-------|--------|
| Identical Korean | 100% | ✅ |
| Particles removed | 96% | ✅ |
| Punctuation diff | 89-97% | ✅ |
| Verb forms (하다→합니다) | 87% | ✅ |
| Opposite meanings | 66% | ✅ Low |
| Unrelated text | 47% | ✅ Rejected |
| Different words (저장 vs 세이브) | 58% | ✅ Correctly different |

**Key:** 92% threshold is appropriate for text similarity matching.

#### Test Files
```
tests/fixtures/pretranslation/
├── e2e_test_data.py             # Test data generator
├── test_e2e_xls_transfer.py     # 537 tests ✅
├── test_e2e_kr_similar.py       # 530 tests ✅
├── test_e2e_tm_standard.py      # 566 tests ✅
├── test_e2e_tm_faiss_real.py    # Real QWEN+FAISS (500 queries) ✅
├── test_qwen_korean_accuracy.py # Korean text similarity ✅
├── test_qwen_validation.py      # 27 QWEN tests ✅
└── test_real_patterns.py        # 13 patterns ✅
```

### Phase 2: Backend - DETAILED PLAN

#### 2.1 Unified API Endpoint

**NEW FILE:** `server/api/pretranslate.py`

```python
@router.post("/api/ldm/pretranslate")
async def pretranslate_file(
    file_id: int,
    engine: str,  # "standard" | "xls_transfer" | "kr_similar"
    dictionary_id: int,
    threshold: float = 0.92,
    skip_existing: bool = True,
    background_tasks: BackgroundTasks
) -> PretranslateResponse
```

**Source Reference:** `server/api/xlstransfer_async.py:160-189` (background task pattern)

#### 2.2 Engine Selection (Mode Router)

**NEW FILE:** `server/tools/ldm/pretranslate.py`

```python
class PretranslationEngine:
    """Unified pretranslation with engine selection"""

    def pretranslate(self, rows, engine: str, dictionary_id: int, threshold: float):
        if engine == "standard":
            return self._standard_tm_search(rows, dictionary_id, threshold)
        elif engine == "xls_transfer":
            return self._xls_transfer_search(rows, dictionary_id, threshold)
        elif engine == "kr_similar":
            return self._kr_similar_search(rows, dictionary_id, threshold)
```

**Source References:**
- Standard TM: `server/tools/ldm/tm_indexer.py` (5-tier cascade)
- XLS Transfer: `server/tools/xlstransfer/translation.py:24-200`
- KR Similar: `server/tools/kr_similar/searcher.py:275-450`

#### 2.3 Batch Processing with Queue System

**EXISTING:** `server/tasks/celery_app.py` (Celery + Redis)

```python
# Configuration (already exists)
broker = redis://localhost:6379/1
result_backend = redis://localhost:6379/2
task_time_limit = 3600  # 1 hour hard limit
task_soft_time_limit = 3000  # 50 min soft limit
```

**NEW TASK:** Add to `server/tasks/background_tasks.py`

```python
@celery_app.task(bind=True)
def pretranslate_batch(self, batch_data: dict):
    """
    Process large batches asynchronously.
    - batch_data: {file_id, engine, dictionary_id, threshold, row_ids}
    - Progress callback via WebSocket
    - Chunked processing (500 rows per chunk)
    """
```

**Source Reference:** `server/tasks/background_tasks.py:84-105` (process_large_batch pattern)

#### 2.4 Smart Translation Upgrade (Standard 5-Tier Enhancement)

**UPGRADE TO:** `server/tools/ldm/tm_indexer.py`

**New Features from WebTranslatorNew:**

| Feature | Source | Implementation |
|---------|--------|----------------|
| Dual Threshold | `WebTranslatorNew/TEXT_SEARCH.md:73-84` | `cascade_threshold=0.92`, `context_threshold=0.49` |
| Line-Level Embeddings | `WebTranslatorNew/DATA_PREPROCESSING.md:136-181` | `should_create_line_entries()`, `create_line_entries()` |
| Incremental Updates | `WebTranslatorNew/DATA_PREPROCESSING.md:206-242` | `update_embeddings_incremental()` |
| N-gram Fallback | `WebTranslatorNew/TEXT_SEARCH.md:57-69` | Tier 5: 1,2,3-word n-grams |

**Dual Threshold System:**
```python
# From WebTranslatorNew/TEXT_SEARCH.md:73-84
cascade_threshold = 0.92    # High confidence - auto-apply
context_threshold = 0.49    # Useful guidance - show as suggestion

# Returns:
# - primary_matches (>= 92%): Can auto-apply
# - context_matches (49-92%): Show to user as suggestions
```

#### 2.5 Dynamic Auto-Glossary Creation

**SOURCE:** `RessourcesForCodingTheProject/NewScripts/GlossarySniffer/glossary_sniffer_1124.py`

**Key Features:**
- 13-language support (KOR, ENG, FRA, GER, SPA, ITA, POR, RUS, POL, TUR, THA, JPN, CHS, CHT)
- Aho-Corasick automaton for O(n) multi-pattern matching
- Smart filtering rules (max 15 chars, min 2 occurrences, no punctuation)

**NEW FILE:** `server/tools/ldm/glossary_extractor.py`

```python
class GlossaryExtractor:
    """Extract glossary terms from TM entries"""

    def extract_terms(self, tm_entries: List[dict]) -> List[GlossaryTerm]:
        """
        1. Filter by rules (from glossary_sniffer_1124.py:42-47)
        2. Count occurrences
        3. Build Aho-Corasick automaton
        4. Return extracted terms with translations
        """
```

**Source Reference:** `glossary_sniffer_1124.py:83-176` (extract_multilanguage_glossary)

#### 2.6 Data Preprocessing Pipeline

**SOURCE:** `WebTranslatorNew/DATA_PREPROCESSING.md`

```
Raw Data (Excel/XML/TXT)
    ↓
1. Remove Empty Cells
    ↓
2. Clean Control Characters (_x000D_ removal)
    ↓
3. Resolve Duplicates (majority voting)
    ↓
4. Filter Database Duplicates (skip existing)
    ↓
Cleaned Data → Embedding Pipeline
```

**Integration Point:** `server/tools/ldm/tm_indexer.py` before embedding generation

### Phase 3: UI
- [ ] Pretranslation modal component
- [ ] TM Merge modal component
- [ ] Progress tracking (WebSocket updates)
- [ ] Dual threshold display (primary vs context matches)

### Phase 4: Integration
- [ ] Connect to file context menu
- [ ] Test with real files
- [ ] Performance optimization
- [ ] Glossary extraction UI

---

## Source Code References

### Queue System (Batch Processing)

| File | Lines | What |
|------|-------|------|
| `server/tasks/celery_app.py` | 1-41 | Celery + Redis config |
| `server/tasks/background_tasks.py` | 84-105 | `process_large_batch()` pattern |
| `server/api/xlstransfer_async.py` | 160-189 | BackgroundTasks usage |
| `server/api/kr_similar_async.py` | 399-451 | Async operation pattern |

### Smart Translation

| File | Lines | What |
|------|-------|------|
| `server/tools/xlstransfer/translation.py` | 24-96 | `find_best_match()` |
| `server/tools/xlstransfer/translation.py` | 103-146 | `process_batch()` |
| `server/tools/xlstransfer/translation.py` | 153-200 | `translate_text_multi_mode()` |
| `server/tools/kr_similar/searcher.py` | 275-450 | `auto_translate()` |
| `server/tools/kr_similar/core.py` | 17-89 | `adapt_structure()` |

### Auto-Glossary

| File | Lines | What |
|------|-------|------|
| `RessourcesForCodingTheProject/NewScripts/GlossarySniffer/glossary_sniffer_1124.py` | 83-176 | `extract_multilanguage_glossary()` |
| `RessourcesForCodingTheProject/NewScripts/GlossarySniffer/glossary_sniffer_1124.py` | 42-47 | Filtering rules |
| `RessourcesForCodingTheProject/NewScripts/GlossarySniffer/glossary_sniffer_1124.py` | 292-316 | Aho-Corasick automaton |

### TM Indexer (5-Tier Cascade)

| File | Lines | What |
|------|-------|------|
| `server/tools/ldm/tm_indexer.py` | 40-46 | FAISS HNSW config |
| `server/tools/ldm/tm_indexer.py` | 49-112 | Normalization functions |
| `server/tools/ldm/tm_indexer.py` | 115-200 | TMIndexer class |
| `server/tools/kr_similar/embeddings.py` | 38-127 | EmbeddingsManager |

### WebTranslatorNew Documentation

| File | What |
|------|------|
| `RessourcesForCodingTheProject/WebTranslatorNew/TEXT_SEARCH.md` | 5-Tier Cascade, Dual Threshold |
| `RessourcesForCodingTheProject/WebTranslatorNew/EMBEDDINGS.md` | FAISS HNSW, Batch Embedding |
| `RessourcesForCodingTheProject/WebTranslatorNew/DATA_PREPROCESSING.md` | Deduplication, Line-Level Processing |
| `RessourcesForCodingTheProject/WebTranslatorNew/FUZZY_SEARCH.md` | RapidFuzz for target search |

---

## Files to Modify

### New Files

| File | Purpose |
|------|---------|
| `server/api/pretranslate.py` | Unified pretranslation API endpoint |
| `server/tools/ldm/pretranslate.py` | Engine selection + pretranslation logic |
| `server/tools/ldm/glossary_extractor.py` | Auto-glossary extraction |
| `server/tools/ldm/data_preprocessor.py` | Data cleaning pipeline |
| `locaNext/src/lib/components/ldm/PretranslateModal.svelte` | Pretranslation UI |
| `locaNext/src/lib/components/ldm/GlossaryExtractModal.svelte` | Glossary extraction UI |

### Existing Files to Update

| File | Changes |
|------|---------|
| `server/tools/ldm/tm_indexer.py` | Add dual threshold, line-level embeddings |
| `server/tasks/background_tasks.py` | Add `pretranslate_batch()` task |
| `server/api/ldm_async.py` | Register pretranslate router |
| `server/main.py` | Register new routers |
| `locaNext/src/lib/components/ldm/FileExplorer.svelte` | Add context menu option |

---

## Success Criteria

1. **Standard mode:** Matches existing 5-tier behavior
2. **XLS Transfer mode:** Codes preserved correctly in 100% of cases
3. **KR Similar mode:** Structure maintained in 95%+ of cases
4. **Threshold 92%:** Achieves >90% acceptable translations
5. **Performance:** <2 minutes for 10,000 rows

---

*Created: 2025-12-16*
*Updated: 2025-12-17 02:45 KST*

**Phase 1:** COMPLETE - 2,172 E2E tests passed. QWEN+FAISS verified.
**Phase 2:** PLANNED - Detailed plan with source references added. Ready to implement:
- Unified API endpoint (`/api/ldm/pretranslate`)
- Engine selection (Standard/XLS Transfer/KR Similar)
- Batch processing with Celery queue
- Smart translation upgrades (dual threshold, line-level embeddings)
- Auto-glossary extraction (Aho-Corasick)
