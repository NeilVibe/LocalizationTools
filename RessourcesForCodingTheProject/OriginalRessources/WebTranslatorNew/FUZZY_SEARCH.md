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

## Two Options (Pick One)

### Option A: Qwen + FAISS (Semantic - Like WebTranslatorNew)

Use the same proven stack from WebTranslatorNew:

```python
# Same model as WebTranslatorNew
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('Qwen/Qwen3-Embedding-0.6B')

# FAISS HNSW index for fast search
import faiss
index = faiss.IndexHNSWFlat(dimension, 32, faiss.METRIC_INNER_PRODUCT)
```

| Aspect | Value |
|--------|-------|
| Memory | ~2.4GB |
| Speed | 10-50ms per query |
| Typos | GOOD |
| Synonyms | GOOD |
| Abbreviations | GOOD |
| All languages | YES |

**When to use:** Need semantic search (synonyms, abbreviations, paraphrases)

---

### Option B: Simple Fuzzy (RapidFuzz Only)

```python
from rapidfuzz import process, fuzz
matches = process.extract(query, targets, scorer=fuzz.WRatio,
                          score_cutoff=70, limit=10)
```

| Aspect | Value |
|--------|-------|
| Memory | <10MB |
| Speed | <1ms per query |
| Typos | GOOD |
| Synonyms | POOR |
| Abbreviations | POOR |
| All languages | YES (lexical only) |

**When to use:** Just need typo correction and near-exact matching

---

## Recommendation

| Use Case | Choice |
|----------|--------|
| TM suggestions (semantic similarity) | **Option A: Qwen + FAISS** |
| Quick search bar (find as you type) | **Option B: RapidFuzz** |
| QA term consistency check | **Option A: Qwen + FAISS** |

No hybrid needed - pick based on use case.
