# WebTranslatorNew Reference Documentation

**Source Project:** `~/WebTranslatorNew`
**Extracted:** 2025-12-08
**Purpose:** Reusable logic patterns for LocalizationTools

---

## Documentation Index

| Document | Focus Area | Key Functions |
|----------|------------|---------------|
| [TEXT_SEARCH.md](TEXT_SEARCH.md) | 5-Tier Cascade Search | `find_similar_entries_enhanced()` |
| [EMBEDDINGS.md](EMBEDDINGS.md) | Vector Embeddings & FAISS | `generate_embeddings_batch()`, `get_faiss_index()` |
| [DATA_PREPROCESSING.md](DATA_PREPROCESSING.md) | Data Cleaning & Deduplication | `DataPreprocessor`, duplicate resolution |
| [FUZZY_SEARCH.md](FUZZY_SEARCH.md) | Fast Fuzzy Search (non-embedding) | RapidFuzz for target/translation text |

---

## Quick Reference

### 5-Tier Cascade Search
```
Tier 1: Perfect whole text match (O(1) hash)     → Strategy: 'perfect_whole_match'
Tier 2: Whole text embedding (FAISS HNSW)        → Strategy: 'whole-embedding'
Tier 3: Perfect line match (O(1) per line)       → Strategy: 'perfect_line_match'
Tier 4: Line-by-line embedding (FAISS per line)  → Strategy: 'line-embedding'
Tier 5: Word n-gram embedding (1,2,3-grams)      → Strategy: 'word-{n}-gram'
```

### Dual-Threshold System
```python
cascade_threshold = 0.92    # High confidence - auto-apply candidate
context_threshold = 0.49    # Useful guidance - structural reference
```

---

## Source Files in WebTranslatorNew

```
app/services/
├── embedding.py               # 5-tier search, FAISS, embeddings (main file)
├── translation.py             # Translation integration
├── glossary_enhance.py        # Line-by-line refinement
└── glossary/
    ├── preprocessor.py        # Data cleaning
    ├── embedding_pipeline.py  # DB operations
    └── import_manager.py      # File imports

app/models/
└── glossary.py               # GlossaryEntry, GlossaryLineEntry
```

---

*Each doc is focused on one type of logic for easier reading and maintenance.*
