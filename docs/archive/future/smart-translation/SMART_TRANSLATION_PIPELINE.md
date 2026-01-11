# Smart Translation Pipeline (API-Dependent)

**Status:** FUTURE - Requires External Translation API (QWEN/Claude)
**Source:** WebTranslatorNew project
**Created:** 2025-12-17
**Prerequisite:** Access to translation API (QWEN MT or Claude)

---

## Overview

This document contains the complete Smart Translation Pipeline from WebTranslatorNew.
**ALL features in this document require external API calls for translation.**

When LocaNext gains access to a translation API, this documentation provides everything needed to implement the Smart Translation system.

---

## Prerequisites

Before implementing these features, you need:

1. **Translation API Access:**
   - QWEN MT API (recommended - cost-effective for batch translation)
   - OR Claude API (higher quality, higher cost)

2. **API Configuration:**
   ```python
   # Example config needed
   TRANSLATION_API = {
       'provider': 'qwen',  # or 'claude'
       'api_key': 'your-api-key',
       'model': 'qwen-mt-turbo',  # or 'claude-3-sonnet'
       'rate_limit': 100,  # requests per minute
   }
   ```

3. **Cost Considerations:**
   - QWEN MT: ~$0.002 per 1K tokens
   - Claude: ~$0.003-0.015 per 1K tokens
   - Batch of 10,000 entries could cost $5-50+ depending on text length

---

## The Complete 2-Stage Smart Translation System

```
+-----------------------------------------------------------------------------+
|                     SMART TRANSLATION PIPELINE                               |
|                                                                             |
|  +---------------------------------------------------------------------+   |
|  | STAGE 1: CLUSTER PREPROCESSING (Core Glossary)                       |   |
|  |                                                                      |   |
|  |  1. Generate embeddings for all entries (whole + line level)        |   |
|  |  2. Build similarity graph (FAISS, 90% threshold)                   |   |
|  |  3. Find connected components (clusters via DFS)                    |   |
|  |  4. Select representatives (vectorial centrality)                   |   |
|  |  5. Translate representatives ONLY  <-- API CALL                    |   |
|  |                                                                      |   |
|  |  Result: Core Glossary with translated cluster representatives      |   |
|  +---------------------------------------------------------------------+   |
|                                    |                                        |
|                                    v                                        |
|  +---------------------------------------------------------------------+   |
|  | STAGE 2: ENHANCED SMART TRANSLATION (Character-Based Phases)         |   |
|  |                                                                      |   |
|  |  1. Filter out already translated entries from Stage 1              |   |
|  |  2. Group by character length (2, 3, 4... 51+ chars)               |   |
|  |  3. Process SHORTEST entries first  <-- API CALLS                   |   |
|  |  4. After each phase: DB save -> FAISS refresh                      |   |
|  |  5. Shorter entries become references for longer entries           |   |
|  |                                                                      |   |
|  |  12 Character Phases:                                               |   |
|  |  - Phase 1-8:  Single char lengths (2, 3, 4, 5, 6, 7, 8, 9)        |   |
|  |  - Phase 9:    10-20 chars                                          |   |
|  |  - Phase 10:   21-30 chars                                          |   |
|  |  - Phase 11:   31-50 chars                                          |   |
|  |  - Phase 12:   51+ chars                                            |   |
|  +---------------------------------------------------------------------+   |
|                                    |                                        |
|                                    v                                        |
|  +---------------------------------------------------------------------+   |
|  | STAGE 3: POST-PROCESSING (Multi-line Refinement)                     |   |
|  |                                                                      |   |
|  |  For each translated entry with multiple lines:                     |   |
|  |  1. Use full translation as context reference                       |   |
|  |  2. Refine line-by-line with context  <-- API CALLS                 |   |
|  |  3. Preserve structure (newlines, formatting)                      |   |
|  |  4. Update dynamic glossary with refined translation               |   |
|  |  5. Generate line-level embeddings                                 |   |
|  |  6. Refresh FAISS indexes                                          |   |
|  +---------------------------------------------------------------------+   |
|                                                                             |
+-----------------------------------------------------------------------------+
```

---

## Stage 1: Cluster Preprocessing (Core Glossary)

**Source:** `/home/neil1988/WebTranslatorNew/app/services/glossary_original.py:1345-1500`

**Function:** `create_core_glossary_via_clustering()`

### Process

```
Phase 1: Generate embeddings
- generate_whole_line_embeddings() at glossary_original.py:847-943
- Whole entry embeddings + line-level embeddings
- 12-worker parallel processing
- NO API CALLS (uses local QWEN embedding model)

Phase 2: Build similarity graph
- build_similarity_graph() at glossary_original.py:945-1016
- FAISS HNSW index (M=32, efConstruction=400)
- Find k=100 nearest neighbors per entry
- Threshold: 90% similarity
- NO API CALLS

Phase 3: Find clusters
- find_connected_components() at glossary_original.py:1018-1073
- DFS traversal of similarity graph
- Result: groups of similar entries
- NO API CALLS

Phase 4: Translate representatives
- translate_cluster_representatives() at glossary_original.py:1075-1250
- Select representative via vectorial centrality (most connections)
- Sort by text length (shortest first)
- Translate ONE entry per cluster
- API CALLS HERE (1 call per cluster)
```

### Vectorial Centrality Selection

```python
# glossary_original.py:1099-1121
# Pick entry with MOST connections within cluster (most representative)
for idx in cluster:
    connections_in_cluster = sum(
        1 for connected_idx in similarity_graph.get(idx, [])
        if connected_idx in cluster
    )
    if connections_in_cluster > max_connections:
        max_connections = connections_in_cluster
        best_idx = idx
```

### Cost Optimization

If you have 100 similar entries in a cluster:
- Without clustering: 100 API calls
- With clustering: 1 API call (representative only)
- Savings: 99 API calls

**Note:** Actual savings depend on how clustered your data is. Test with real data to measure.

---

## Stage 2: Character-Based Phases

**Source:** `/home/neil1988/WebTranslatorNew/app/services/glossary_original.py:1935-2100`

### Functions

- `create_character_phases()` at `glossary_original.py:1935-1987`
- `process_character_phase_parallel()` at `glossary_original.py:1989-2088`

### Why Shortest First?

- Short entries = game terms, UI labels, common words
- Once translated, they become context for longer entries
- Better translation quality for complex sentences

### Character Phases

```python
# From glossary_original.py:1935-1987
def create_character_phases(candidates):
    phases = {
        '2_chars': [],
        '3_chars': [],
        '4_chars': [],
        '5_chars': [],
        '6_chars': [],
        '7_chars': [],
        '8_chars': [],
        '9_chars': [],
        '10_20_chars': [],
        '21_30_chars': [],
        '31_50_chars': [],
        '51plus_chars': [],
    }

    for candidate in candidates:
        length = len(candidate)
        if length == 2:
            phases['2_chars'].append(candidate)
        elif length == 3:
            phases['3_chars'].append(candidate)
        # ... etc
```

### Phase Processing

```
For each character phase:
  1. Get all candidates of that length
  2. Process with 12 workers parallel (QWEN automatic batching)
  3. Save translations to database  <-- API CALLS
  4. Rebuild FAISS index (progressive_refresh)
  5. Move to next phase

After each phase, the glossary grows -> better context for next phase
```

---

## Stage 3: Multi-line Refinement

**Source:** `/home/neil1988/WebTranslatorNew/app/services/glossary_enhance.py:5-124`

**Function:** `refine_translation_line_by_line()`

### When Triggered

For entries with 2+ lines (after normalization)

### Process

```python
# From task_processor.py:646-661
if line_count > 1:
    refined_translation = refine_translation_line_by_line(
        source_text=source_text,
        initial_translation=final_translation,
        source_lang=source_lang,
        target_lang=target_lang,
        model_key=model_key
    )
```

### How Refinement Works

```
1. Split source into lines
2. Create context reference (full source -> full translation)
3. For each non-empty line:
   - Translate with context prompt  <-- API CALL per line
   - "REFERENCE: [full translation], CURRENT LINE: [this line]"
4. Join refined lines preserving original line separators
5. Update glossary entry with refined translation
6. Generate line-level embeddings for the refined entry
```

### Context Prompt Format

```python
# From glossary_enhance.py:68-73
context_prompt = (
    f"REFERENCE TRANSLATION:\n\n"
    f"FULL SOURCE TEXT:\n{temp_reference['source']}\n\n"
    f"FULL TRANSLATION:\n{temp_reference['target']}\n\n"
    f"CURRENT LINE: Extract and translate only the following line, maintaining any formatting codes:"
)
```

---

## Dynamic Glossary Auto-Creation

**Source:** `/home/neil1988/WebTranslatorNew/app/services/glossary_original.py:71-237`

### Key Functions

| Function | Lines | What It Does |
|----------|-------|--------------|
| `filter_candidates()` | 71-128 | Skip entries with perfect matches (>= 92%) |
| `translate_candidates()` | 131-191 | Translate with glossary context <-- API CALLS |
| `create_dynamic_glossary_entries()` | 194-237 | Create entries with embeddings |

### Smart Filtering (No API calls)

```python
# Only translate what's NEW (filter_candidates)
for candidate in candidates:
    matches = find_similar_entries_enhanced(candidate, glossary_ids, threshold=0.92)
    if not matches or matches[0]['similarity'] < 0.92:
        need_translation.append(candidate)  # No perfect match -> translate
```

### Translation with Context (API calls)

```python
# translate_candidates() at glossary_original.py:131-191
def translate_candidates(candidates, context_matches, source_lang, target_lang, model_key):
    """Translate candidates using glossary context"""
    for candidate in candidates:
        # Build context from similar entries
        context = format_similar_entries_with_metadata(context_matches.get(candidate, []))

        # API CALL HERE
        translation = translate_text(
            text=candidate,
            glossary_ids=[],
            source_lang=source_lang,
            target_lang=target_lang,
            model_key=model_key,
            user_prompt=context
        )
```

---

## Data Preprocessing (NO API calls)

**Source:** `/home/neil1988/WebTranslatorNew/app/services/glossary/preprocessor.py`

**This feature does NOT require API access - can be implemented now.**

### Class: DataPreprocessor

| Feature | Method | What It Does |
|---------|--------|--------------|
| Empty cell removal | `_remove_empty_cells()` | Remove rows with blank source/target |
| Control char cleaning | `_clean_control_characters()` | Remove `_x000D_`, strip whitespace |
| Duplicate resolution | `_resolve_duplicates()` | Keep most frequent target for duplicate sources |
| **DB duplicate filter** | `_filter_database_duplicates()` | Skip exact matches BEFORE embedding |

### Database Duplicate Filtering (KEY FEATURE)

```python
# From preprocessor.py:180-228
def _filter_database_duplicates(self, df, glossary_id):
    # Get existing source+target pairs
    existing_entries = GlossaryEntry.query.filter_by(glossary_id=glossary_id).all()
    existing_pairs = {(entry.source_text.strip(), entry.target_text.strip())
                      for entry in existing_entries}

    # Filter out exact duplicates BEFORE processing
    mask = df.apply(lambda row: (row['source'], row['target']) not in existing_pairs, axis=1)
    return df[mask]
```

**Benefit:** 477 entries -> 422 exact duplicates filtered -> 55 to process (massive speed gain)

---

## Source Code References

### WebTranslatorNew Files

| File | Lines | What |
|------|-------|------|
| `glossary_original.py` | 847-943 | `generate_whole_line_embeddings()` |
| `glossary_original.py` | 945-1016 | `build_similarity_graph()` |
| `glossary_original.py` | 1018-1073 | `find_connected_components()` - Clustering DFS |
| `glossary_original.py` | 1075-1250 | `translate_cluster_representatives()` |
| `glossary_original.py` | 1345-1500 | `create_core_glossary_via_clustering()` |
| `glossary_original.py` | 1604-1920 | `generate_dynamic_glossary()` - Full workflow |
| `glossary_original.py` | 1935-2000 | `create_character_phases()` |
| `glossary_original.py` | 71-128 | `filter_candidates()` |
| `glossary_original.py` | 131-191 | `translate_candidates()` |
| `glossary_enhance.py` | 5-124 | `refine_translation_line_by_line()` |
| `task_processor.py` | 543-803 | `_process_dynamic_glossary_workflow()` |
| `glossary/preprocessor.py` | all | `DataPreprocessor` class |

### How to Navigate WebTranslatorNew

```bash
# Correct path
/home/neil1988/WebTranslatorNew/

# List services
ls /home/neil1988/WebTranslatorNew/app/services/

# Search for functions
grep -n "def FUNCTION_NAME" /home/neil1988/WebTranslatorNew/app/services/*.py

# Read specific lines
sed -n 'START,ENDp' /home/neil1988/WebTranslatorNew/app/services/FILE.py
```

---

## Implementation Checklist (When API is Available)

### Phase 1: Core Infrastructure
- [ ] Configure translation API (QWEN/Claude)
- [ ] Add API cost tracking
- [ ] Implement rate limiting
- [ ] Add progress tracking for long operations

### Phase 2: Clustering System
- [ ] Port `generate_whole_line_embeddings()`
- [ ] Port `build_similarity_graph()`
- [ ] Port `find_connected_components()`
- [ ] Port `translate_cluster_representatives()`

### Phase 3: Character-Based Phases
- [ ] Port `create_character_phases()`
- [ ] Port `process_character_phase_parallel()`
- [ ] Implement progressive FAISS refresh

### Phase 4: Multi-line Refinement
- [ ] Port `refine_translation_line_by_line()`
- [ ] Add glossary update with refined translation
- [ ] Generate line-level embeddings

### Phase 5: Dynamic Glossary
- [ ] Port `filter_candidates()`
- [ ] Port `translate_candidates()`
- [ ] Port `create_dynamic_glossary_entries()`
- [ ] Port `generate_dynamic_glossary()` full workflow

### Phase 6: UI
- [ ] Smart Translation modal
- [ ] Progress tracking
- [ ] Cost estimation display

---

## Cost Estimation Formula

```python
def estimate_translation_cost(entries, avg_chars_per_entry=50):
    """
    Estimate API cost for translation

    Assumptions:
    - 1 token ~= 4 characters (English)
    - 1 token ~= 2 characters (Korean)
    - QWEN MT: $0.002 per 1K tokens
    - Claude: $0.003-0.015 per 1K tokens
    """
    avg_tokens = avg_chars_per_entry / 3  # rough estimate
    total_tokens = len(entries) * avg_tokens

    qwen_cost = (total_tokens / 1000) * 0.002
    claude_cost = (total_tokens / 1000) * 0.01  # mid-range

    return {
        'entries': len(entries),
        'estimated_tokens': total_tokens,
        'qwen_cost_usd': qwen_cost,
        'claude_cost_usd': claude_cost
    }
```

---

*This documentation is ready to use when LocaNext gains access to translation API.*
*Last updated: 2025-12-17*
