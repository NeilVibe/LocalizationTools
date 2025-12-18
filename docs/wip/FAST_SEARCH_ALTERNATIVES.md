# Fast Search Alternatives - Research Notes

**Created:** 2025-12-18 | **Status:** RESEARCH ONLY (Not Chosen)

---

## ⚠️ IMPORTANT: This is Research, NOT the Chosen Solution

**The actual decision was: Model2Vec + FAISS HNSW (FEAT-005)**

See: [MODEL2VEC_BENCHMARK.md](MODEL2VEC_BENCHMARK.md) for the chosen approach.

This document contains research on RapidFuzz (character-based fuzzy matching) as an ALTERNATIVE approach that was NOT chosen for the default TM search.

---

## Summary

| Approach | Type | Chosen? |
|----------|------|---------|
| **Model2Vec + FAISS** | Semantic (meaning-based) | ✅ **YES - FEAT-005** |
| RapidFuzz | Character sequence | ❌ No (research only) |
| Qwen + FAISS | Deep semantic | ✅ Keep as opt-in |

---

## Why Model2Vec Was Chosen Over RapidFuzz

| Aspect | Model2Vec | RapidFuzz |
|--------|-----------|-----------|
| **Type** | Semantic (meaning) | Character sequence |
| **"저장" vs "세이브"** | ~70% (understands meaning) | ~30% (different chars) |
| **Typo handling** | ✅ Yes | ✅ Yes |
| **TM industry standard** | Modern approach | Traditional (memoQ/Trados) |
| **Korean support** | Excellent | Good |

**Decision:** Model2Vec provides semantic understanding while still being fast (79x faster than Qwen). Character-based fuzzy matching (RapidFuzz) is traditional but doesn't understand meaning.

---

## RapidFuzz Research (For Reference Only)

### What It Does

RapidFuzz is a fast character-based fuzzy string matcher (like difflib but 10-100x faster).

```python
from rapidfuzz import fuzz

# Character-based similarity
fuzz.ratio("저장하기", "저장하기 버튼")  # 72% (character match)
fuzz.ratio("저장", "세이브")             # ~30% (different chars, same meaning!)
```

### Why It Wasn't Chosen

1. **No semantic understanding** - "저장" and "세이브" (same meaning) get low score
2. **Model2Vec is fast enough** - 79x faster than Qwen, acceptable for real-time
3. **Industry moving to semantic** - Modern CAT tools use neural matching

### When RapidFuzz Might Be Useful (Future)

- **Exact match preprocessing** - Fast filter before semantic search
- **UI autocomplete** - Instant character matching for dropdown suggestions
- **QA checks** - Find similar strings for consistency checks

---

## The Actual Architecture (FEAT-005)

```
┌─────────────────────────────────────────────────────────────────┐
│  TM Search Pipeline (Decided)                                    │
│                                                                  │
│  1. EXACT MATCH (hash lookup) ← instant                         │
│  2. CONTAINS (substring) ← fast                                  │
│  3. SEMANTIC (Model2Vec + FAISS HNSW) ← DEFAULT                 │
│     └── 79x faster than Qwen                                    │
│     └── 1.2GB RAM (vs 2.1GB Qwen)                               │
│     └── Understands meaning                                     │
│                                                                  │
│  4. SEMANTIC DEEP (Qwen + FAISS HNSW) ← OPT-IN                  │
│     └── Maximum quality                                         │
│     └── For nightly batch / deep matching                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## References

- [RapidFuzz GitHub](https://github.com/rapidfuzz/RapidFuzz) - 14k+ stars, MIT license
- [Model2Vec GitHub](https://github.com/MinishLab/model2vec) - Chosen solution
- [MODEL2VEC_BENCHMARK.md](MODEL2VEC_BENCHMARK.md) - Benchmark results

---

*Research conducted 2025-12-18 | Status: NOT CHOSEN - kept for reference only*
