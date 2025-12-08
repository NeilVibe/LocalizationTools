# 5-Tier Cascade Text Search

**Source:** `~/WebTranslatorNew/app/services/embedding.py:639-1089`

---

## Overview

Multi-level search strategy that progressively deepens until a high-confidence match is found.

---

## Tier Architecture

### Tier 1: Perfect Whole Text Match
```python
# O(1) hash lookup - FASTEST
lookup[source_text] = {'target_text': ..., 'entry_id': ...}
lookup[source_text.strip()] = ...  # Whitespace variations
```
- **Time:** <1ms
- **Strategy:** `'perfect_whole_match'`
- **Stops cascade:** Yes (returns immediately)

### Tier 2: Whole Text Embedding
```python
# FAISS HNSW vector search
index = faiss.IndexHNSWFlat(dimension, 32, faiss.METRIC_INNER_PRODUCT)
index.hnsw.efConstruction = 400
index.hnsw.efSearch = 500
distances, indices = index.search(query_embedding, top_k)
```
- **Time:** 10-50ms
- **Strategy:** `'whole-embedding'`
- **Stops cascade:** If similarity >= cascade_threshold

### Tier 3: Perfect Line Match
```python
# For multi-line text, O(1) per line
for line in source_text.split('\n'):
    if line.strip() in line_lookup:
        matches.append(line_lookup[line.strip()])
```
- **Time:** <1ms per line
- **Strategy:** `'perfect_line_match'`

### Tier 4: Line-by-Line Embedding
```python
# Only for lines without high confidence matches
for line in unmatched_lines:
    line_embedding = model.encode([line])
    matches = line_faiss_index.search(line_embedding, top_k)
```
- **Time:** 10-50ms per line
- **Strategy:** `'line-embedding'`

### Tier 5: Word N-Gram Embedding
```python
# Partial matching via 1,2,3-word n-grams
from nltk import ngrams, word_tokenize

words = word_tokenize(text)
for n in [1, 2, 3]:
    grams = [' '.join(g) for g in ngrams(words, n)]
    for gram in grams:
        # Search line entries for gram matches
```
- **Time:** 10-50ms per gram
- **Strategy:** `'word-{n}-gram'`

---

## Dual-Threshold System

```python
cascade_threshold = 0.92    # High confidence - stops cascade
context_threshold = 0.49    # Useful guidance

primary_matches = []        # >= cascade_threshold
context_candidates = []     # context_threshold to cascade_threshold
best_context_match = None   # Single best from context_candidates

# Returns: all primary_matches + single best_context_match
```

**Benefits:**
- Primary (92%+): Reliable, can auto-apply
- Context (49-92%): Structural guidance without false positives

---

## Main Function Signature

```python
def find_similar_entries_enhanced(
    text: str,
    glossary_ids: List[int],
    top_k: int = 5,
    threshold: float = 0.92,
    max_time: int = 600,
    cascade_threshold: float = 0.92,
    context_threshold: float = 0.49
) -> List[Dict]:
    """
    Returns list of matches sorted by similarity (descending):
    {
        'source_text': str,
        'target_text': str,
        'similarity': float,
        'entry_id': int,
        'glossary_id': int,
        'strategy': str  # Which tier found this
    }
    """
```

---

## Integration for LDM TM

```python
# Example usage in LocalizationTools
matches = find_similar_entries_enhanced(
    text=source_text,
    glossary_ids=[project_glossary_id],
    cascade_threshold=0.92,
    context_threshold=0.49
)

# Tier 1 perfect match - use directly
if matches[0]['strategy'] == 'perfect_whole_match':
    apply_translation(matches[0]['target_text'])

# Show to user with confidence levels
for match in matches:
    if match['similarity'] >= 0.92:
        suggest_as_primary(match)
    else:
        show_as_context(match)
```
