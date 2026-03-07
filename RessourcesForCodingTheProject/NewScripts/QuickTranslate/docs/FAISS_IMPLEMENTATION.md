# FAISS Implementation - QuickTranslate

## Overview

QuickTranslate uses **FAISS IndexHNSWFlat** with **Model2Vec** (`minishlab/potion-multilingual-128M`, 256-dim) for fuzzy Korean text matching. Model2Vec provides 79x faster encoding than KR-SBERT with no torch dependency.

---

## Critical Rules

### IndexHNSWFlat - Approximate Nearest Neighbor

| Parameter | Value | Why |
|-----------|-------|-----|
| **M** | 32 | Graph connectivity (higher = more accurate, more memory) |
| **efConstruction** | 400 | Build-time accuracy (higher = slower build, better graph) |
| **efSearch** | 500 | Query-time accuracy (higher = slower search, better recall) |
| **Metric** | `METRIC_INNER_PRODUCT` | Cosine similarity after L2 normalization |

For <200K vectors, HNSW gives O(log n) search with near-perfect recall at these settings.

### Batch Encoding - batch_size=100

Same batch pattern as TFM FULL monolith:

```python
# CORRECT - batch loop with np.vstack
batch_size = 100
all_embeddings = []
for i in range(0, total, batch_size):
    batch = texts[i:i + batch_size]
    batch_emb = encode_texts(model, batch)
    all_embeddings.append(batch_emb)

embeddings = np.vstack(all_embeddings).astype(np.float32)
```

### Single Normalization Point

`faiss.normalize_L2()` is called ONCE at the FAISS boundary — never inside `encode_texts()`. This prevents double-normalization.

### Empty String Guard

Empty strings produce zero vectors → NaN after normalize_L2. Guard:
```python
texts = [t if t.strip() else " " for t in texts]
```

---

## Architecture

### Encoding (`fuzzy_matching.py::encode_texts`)

```python
def encode_texts(model, texts):
    """Encode texts with Model2Vec. Returns np.ndarray(float32)."""
    import numpy as np
    result = model.encode(texts)
    return np.array(result, dtype=np.float32)
```

### Index Building (`fuzzy_matching.py::build_faiss_index`)

```
texts (List[str])
    |
    v
Empty string guard (" " for blank texts)
    |
    v
Batch encode (100 at a time)
    encode_texts(model, batch)
    |
    v
np.vstack(all_embeddings).astype(np.float32)
    |
    v
faiss.normalize_L2(embeddings)     # L2 normalize BEFORE adding
    |
    v
index = faiss.IndexHNSWFlat(dim, 32, faiss.METRIC_INNER_PRODUCT)
index.hnsw.efConstruction = 400
index.hnsw.efSearch = 500
index.add(embeddings)
```

### Search (`fuzzy_matching.py::find_matches_fuzzy`)

Used by `xml_transfer.py` for fuzzy transfer mode:

```python
for correction in corrections:
    query_emb = encode_texts(model, [query])
    faiss.normalize_L2(query_emb)
    D, I = index.search(query_emb, k)
    # Filter by threshold (>= 0.85 default)
```

---

## Model Folder

`Model2Vec/` folder placed next to exe (same pattern as legacy `KRTransformer/`). Contains:
- `config.json`
- `model.safetensors`
- `tokenizer.json` (+ related tokenizer files)

NOT bundled in PyInstaller build — too large (~506 MB). Distributed separately or downloaded on first run.

---

## Files

| File | FAISS Usage |
|------|------------|
| `core/fuzzy_matching.py` | Index building (IndexHNSWFlat), encode_texts, search, best-score capture for unmatched |
| `core/xml_transfer.py` | Calls fuzzy_matching functions, accumulates `_fuzzy_matched`/`_fuzzy_unmatched` in results for report |
| `core/failure_report.py` | `generate_fuzzy_report_excel()` — 3-sheet color-coded score distribution report |
| `core/missing_translation_finder.py` | Uses encode_texts for Find Missing fuzzy modes |
| `config.py` | MODEL2VEC_PATH, threshold config |

---

## History

**2026-02-06**: Replaced IndexHNSWFlat with IndexFlatIP. HNSW was causing slow index builds and Python crashes for 10K+ texts. Added batch encoding (batch_size=100) and show_progress_bar=False to all 7 encode calls.

**2026-03-07**: Replaced KR-SBERT (torch, 768-dim) with Model2Vec (256-dim). Switched back to IndexHNSWFlat with tuned parameters (M=32, efConstruction=400, efSearch=500). Build size dropped from ~2GB to 160MB. Encoding speed improved 79x. Added engine-agnostic `encode_texts()` dispatcher, empty string guard, and single normalization point.
