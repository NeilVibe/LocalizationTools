# Fast Fuzzy Search (Non-Embedding)

**Purpose:** Fast multi-language fuzzy search for translation text
**Use Case:** Search TARGET text in LDM (not Korean source)

---

## Recommended: RapidFuzz

**License:** MIT
**Speed:** 10x faster than FuzzyWuzzy (C++ backend)
**Install:** `pip install rapidfuzz`

### Basic Usage

```python
from rapidfuzz import fuzz, process

# Single comparison
score = fuzz.ratio("Sword of Light", "Sword of Lights")
# Returns: 96.55 (0-100 scale)

# Find best matches from list
translations = ["Sword of Light", "Shield of Darkness", "Sword of Fire"]
matches = process.extract("Sword", translations, limit=5, score_cutoff=60)
# Returns: [('Sword of Light', 80.0), ('Sword of Fire', 71.4)]
```

### Comparison Methods

```python
from rapidfuzz import fuzz

text1 = "Sword of Light"
text2 = "Light Sword"

# Simple ratio (order matters)
fuzz.ratio(text1, text2)           # 64.3

# Partial ratio (substring matching)
fuzz.partial_ratio(text1, text2)    # 71.4

# Token sort (ignores word order)
fuzz.token_sort_ratio(text1, text2) # 100.0

# Token set (ignores duplicates + order)
fuzz.token_set_ratio(text1, text2)  # 100.0

# Weighted ratio (best of above)
fuzz.WRatio(text1, text2)           # 100.0
```

### Batch Processing (Fast)

```python
from rapidfuzz import process, fuzz

# Search 100K entries efficiently
targets = ["translation1", "translation2", ...]  # 100K items

# Single query against all
matches = process.extract(
    query="Sword",
    choices=targets,
    scorer=fuzz.WRatio,
    limit=10,
    score_cutoff=70
)
```

### With Pandas DataFrame

```python
import pandas as pd
from rapidfuzz import process, fuzz

df = pd.DataFrame({
    'target': ["Sword of Light", "Shield of Dark", "Fire Sword"]
})

def fuzzy_search(df, query, column='target', threshold=70, limit=10):
    matches = process.extract(
        query,
        df[column].tolist(),
        scorer=fuzz.WRatio,
        limit=limit,
        score_cutoff=threshold
    )

    results = []
    for match_text, score, idx in matches:
        results.append({
            'row_index': idx,
            'text': match_text,
            'score': score
        })
    return results

# Usage
results = fuzzy_search(df, "Sword", threshold=60)
```

---

## Performance Comparison

| Library | 100K comparisons | Notes |
|---------|------------------|-------|
| RapidFuzz | ~50ms | C++ backend, fastest |
| thefuzz | ~500ms | Pure Python |
| Levenshtein | ~100ms | C extension |
| difflib | ~2000ms | Standard library |

---

## Integration for LDM

### API Endpoint

```python
from rapidfuzz import process, fuzz

@router.get("/search/target")
async def search_target_text(
    query: str,
    file_id: Optional[int] = None,
    threshold: float = 70.0,
    limit: int = 20,
    db: AsyncSession = Depends(get_async_db)
):
    """Fuzzy search on target/translation text"""

    # Get rows
    stmt = select(LDMRow).where(LDMRow.target.isnot(None))
    if file_id:
        stmt = stmt.where(LDMRow.file_id == file_id)

    result = await db.execute(stmt)
    rows = result.scalars().all()

    # Build choices list
    choices = [(row.id, row.target) for row in rows if row.target]

    # Fuzzy search
    matches = process.extract(
        query,
        [c[1] for c in choices],
        scorer=fuzz.WRatio,
        limit=limit,
        score_cutoff=threshold
    )

    # Map back to row IDs
    results = []
    for match_text, score, idx in matches:
        row_id = choices[idx][0]
        results.append({
            'row_id': row_id,
            'target': match_text,
            'similarity': score / 100.0
        })

    return {'matches': results, 'query': query}
```

---

## Use Cases

1. **Find similar translations:** "Did I translate 'Sword' elsewhere?"
2. **QA inconsistency check:** Find different translations of same term
3. **Partial search:** User types "Swor" and finds "Sword of Light"
4. **Cross-file search:** Find translations across all project files

---

## Precision Test Results

```
Typo            | "Sword of Light" vs "Sword of Lights"  | 97%  GOOD
Word order      | "Sword of Light" vs "Light Sword"      | 95%  GOOD
Synonym         | "Sword of Light" vs "Blade of Light"   | 71%  POOR
Abbreviation    | "Attack Power"   vs "ATK"              | 45%  VERY POOR
```

**Verdict:** RapidFuzz is lexical only - CANNOT handle synonyms or abbreviations.

---

## Recommended: Hybrid Approach

| Search Type | Method | Use When |
|-------------|--------|----------|
| Exact/Typos | RapidFuzz | Fast initial filter, threshold 90%+ |
| Semantic | Multilingual Embeddings | Synonyms, abbreviations, paraphrases |

### Multilingual Embedding Options (for semantic search)

```python
# MIT licensed, ~500MB, supports 50+ languages
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

# Encode translations
embeddings = model.encode(["Sword of Light", "Blade of Light", "ATK"])
# Now "Sword" and "Blade" will be semantically similar
```

### Hybrid Search Implementation

```python
def search_target_hybrid(query, targets, threshold=0.7):
    # Step 1: Fast RapidFuzz filter (exact/near-exact)
    from rapidfuzz import process, fuzz
    exact_matches = process.extract(query, targets, scorer=fuzz.WRatio,
                                    score_cutoff=90, limit=10)

    if exact_matches:
        return exact_matches  # Fast path

    # Step 2: Semantic search (slower but finds synonyms)
    query_emb = model.encode([query])
    similarities = cosine_similarity(query_emb, target_embeddings)
    return top_k_by_similarity(similarities, threshold)
```

---

## Comparison

| Aspect | RapidFuzz | Multilingual Embeddings | Hybrid |
|--------|-----------|------------------------|--------|
| Speed | <1ms | 10-50ms | 1-50ms |
| Typos | GOOD | GOOD | GOOD |
| Word order | GOOD | GOOD | GOOD |
| Synonyms | POOR | GOOD | GOOD |
| Abbreviations | POOR | GOOD | GOOD |
| Memory | <10MB | ~500MB | ~500MB |

**Recommendation:** Hybrid approach - RapidFuzz for speed, embeddings for accuracy.
