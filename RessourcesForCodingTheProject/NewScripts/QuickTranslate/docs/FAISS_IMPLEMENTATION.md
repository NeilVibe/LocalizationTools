# FAISS Implementation - QuickTranslate

## Overview

QuickTranslate uses **FAISS IndexFlatIP** with **KR-SBERT** (`snunlp/KR-SBERT-V40K-klueNLI-augSTS`, 768-dim) for fuzzy Korean text matching. This follows the exact same battle-tested pattern used by the three monolith scripts: **TFM FULL**, **XLSTransfer**, and **KR Similar**.

---

## Critical Rules

### IndexFlatIP ONLY - Never HNSW

| | IndexFlatIP (CORRECT) | IndexHNSWFlat (WRONG) |
|--|----------------------|----------------------|
| **Build time** | Instant | Minutes (graph construction) |
| **Accuracy** | 100% exact | Approximate |
| **Memory** | Low | High (graph structure) |
| **Compatible with KR-SBERT** | Yes | No - crashes Python |
| **Scale** | Perfect for <200K vectors | Designed for millions |

**HNSW is for LocaNext's Qwen model (1024-dim, millions of TM entries). IndexFlatIP is for KR-SBERT (768-dim, <200K vectors). Two different worlds.**

### Batch Encoding - batch_size=100

Never encode all texts in one `model.encode()` call. Always batch:

```python
# CORRECT - batch loop (same as TFM FULL monolith)
batch_size = 100
for i in range(0, total, batch_size):
    batch = texts[i:i + batch_size]
    batch_embeddings = model.encode(batch, convert_to_numpy=True, show_progress_bar=False)
    all_embeddings.extend(batch_embeddings)

# WRONG - all at once (memory spike, no progress tracking)
embeddings = model.encode(all_170k_texts)
```

### show_progress_bar=False on EVERY encode call

Every `model.encode()` call MUST have `show_progress_bar=False` to prevent tqdm "Batches: 100% 1/1" terminal spam. No exceptions.

---

## Architecture

### Index Building (`fuzzy_matching.py::build_faiss_index`)

```
texts (List[str])
    |
    v
Batch encode (100 at a time)
    model.encode(batch, convert_to_numpy=True, show_progress_bar=False)
    |
    v
np.array(all_embeddings, dtype=np.float32)
    |
    v
faiss.normalize_L2(embeddings)     # L2 normalize BEFORE adding
    |
    v
index = faiss.IndexFlatIP(dim)     # Inner product = cosine after normalization
index.add(embeddings)              # Instant
```

### Search (`fuzzy_matching.py::search_fuzzy`)

```
query_text (str)
    |
    v
model.encode([query], convert_to_numpy=True, show_progress_bar=False)
    |
    v
faiss.normalize_L2(query_embedding)    # Normalize query too
    |
    v
distances, indices = index.search(query_embedding, k)
    |
    v
Filter by threshold (>= 0.85 default)
```

### Translation (`fuzzy_matching.py::find_matches_fuzzy`)

One text at a time - same as all three monoliths:

```python
for correction in corrections:
    results = search_fuzzy(query, model, index, texts, entries, threshold, k=1)
```

---

## Monolith Reference

All three monoliths use the identical FAISS pattern:

### TFM FULL (`TFMFULL0116.py`)
```python
# Index: IndexFlatIP
index = faiss.IndexFlatIP(d)
faiss.normalize_L2(embeddings)
index.add(embeddings)

# Encoding: batch_size=100
batch_size = 100
for i in range(0, len(data), batch_size):
    batch_embeddings = model.encode(batch_data)

# Search: one at a time
sentence_embeddings = model.encode([sentence])
faiss.normalize_L2(sentence_embeddings)
distances, indices = index.search(sentence_embeddings, 4)
```

### XLSTransfer (`XLSTransfer0225.py`)
```python
# Index: IndexFlatIP
faiss.normalize_L2(ref_kr_embeddings)
index = faiss.IndexFlatIP(ref_kr_embeddings.shape[1])
index.add(ref_kr_embeddings)

# Encoding: one at a time
batch_embeddings = model.encode([text], convert_to_tensor=False)

# Search: one at a time
sentence_embeddings = model.encode([clean_sentence])
faiss.normalize_L2(sentence_embeddings)
distances, indices = index.search(sentence_embeddings, 1)
```

### KR Similar (`KRSIMILAR0124.py`)
```python
# Index: IndexFlatIP (via FAISSManager in modern version)
# Encoding: batch_size=1000
batch_embeddings = model.encode(batch_texts, device=device)

# Search: one at a time
embedding = model.encode([line])
faiss.normalize_L2(embedding)
distances, indices = split_index.search(embedding, 1)
```

---

## Threading

No monolith uses ThreadPoolExecutor for encoding or search. All use `threading.Thread` only for GUI responsiveness. Encoding and FAISS search are sequential.

| Monolith | ThreadPoolExecutor | threading.Thread |
|----------|-------------------|-----------------|
| TFM FULL | Imported, never used | GUI wrapper only |
| XLSTransfer | Not used | GUI wrapper only |
| KR Similar | Text normalization only | GUI wrapper only |
| **QuickTranslate** | Not used | GUI wrapper only |

---

## Files

| File | FAISS Usage |
|------|------------|
| `core/fuzzy_matching.py` | Index building (IndexFlatIP), single-query search |
| `core/matching.py` | Batch search (IndexFlatIP at line 660), quadruple fallback |
| `core/xml_transfer.py` | Calls fuzzy_matching functions |
| `config.py` | Threshold config only (no FAISS params needed for IndexFlatIP) |

---

## History

**2026-02-06**: Replaced IndexHNSWFlat with IndexFlatIP. HNSW was causing slow index builds and Python crashes for 10K+ texts. Added batch encoding (batch_size=100) and show_progress_bar=False to all 7 encode calls.
