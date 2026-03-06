# Model2Vec Migration — QuickTranslate

## Goal

Remove KR-SBERT entirely. Model2Vec only. Use LocaNext's battle-tested patterns.

## LocaNext's Full Model2Vec Pipeline (Our Reference)

### Load

```python
# server/tools/shared/embedding_engine.py
from model2vec import StaticModel
model = StaticModel.from_pretrained("minishlab/potion-multilingual-128M")
# QuickTranslate: from local folder, not download
model = StaticModel.from_pretrained(str(MODEL2VEC_PATH))
```

### Encode

```python
# server/tools/shared/embedding_engine.py
embeddings = model.encode(texts)                          # Raw embeddings
embeddings = np.array(embeddings, dtype=np.float32)       # Ensure float32
# Optional encode-side normalization (LocaNext does this):
norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
norms = np.where(norms == 0, 1, norms)                   # Zero-norm guard
embeddings = embeddings / norms                           # L2 normalize
```

### Normalize for FAISS

```python
# server/tools/shared/faiss_manager.py
vectors = np.ascontiguousarray(vectors, dtype=np.float32)  # C-contiguous memory
faiss.normalize_L2(vectors)                                 # In-place L2 normalize
```

LocaNext normalizes TWICE (encode + FAISS). This is idempotent and safe.

### Create HNSW Index

```python
# server/tools/shared/faiss_manager.py — ALL positional args
HNSW_M = 32                    # Connections per layer (higher = better recall, more RAM)
HNSW_EF_CONSTRUCTION = 400     # Build-time effort (higher = slower build, better quality)
HNSW_EF_SEARCH = 500           # Search-time effort (higher = slower search, better recall)

index = faiss.IndexHNSWFlat(dim, 32, faiss.METRIC_INNER_PRODUCT)
index.hnsw.efConstruction = 400
index.hnsw.efSearch = 500
```

Why METRIC_INNER_PRODUCT: normalized vectors → `cos(u,v) = u·v` → inner product = cosine similarity.

### Add Vectors

```python
# server/tools/shared/faiss_manager.py
vectors = np.ascontiguousarray(vectors, dtype=np.float32)
faiss.normalize_L2(vectors)   # Normalize before add
index.add(vectors)            # Single batch add
```

### Search

```python
# server/tools/shared/faiss_manager.py
query = np.ascontiguousarray(query, dtype=np.float32)
faiss.normalize_L2(query)     # Normalize query too
distances, indices = index.search(query, k)
# distances = cosine similarity scores
# indices = 0-based row positions (-1 = not found)
```

### Key Details from LocaNext

- **Model2Vec dimension:** 256 (validated at load time via test encode)
- **No explicit batching:** Model2Vec handles any list size internally
- **Double normalization is safe:** L2 norm is idempotent after first application
- **HNSW supports online insertion:** Can add vectors after initial build
- **Empty vector guard:** `if vectors.size == 0: return` (skip silently)
- **Zero-norm guard:** `np.where(norms == 0, 1, norms)` prevents div-by-zero

## HNSW Decision: YES

**History:** FAISS_IMPLEMENTATION.md says HNSW crashed with KR-SBERT (768-dim, torch, 10K+ vectors).
That crash was caused by **torch memory overhead** (~2GB RAM) + HNSW graph construction — NOT FAISS.
LocaNext runs HNSW with hundreds of thousands of Model2Vec vectors without any issue.

**Why HNSW is safe now with Model2Vec:**
- No torch = ~2GB less RAM
- 256-dim vs 768-dim = 3x smaller vectors
- Model2Vec encoding is near-instant (static embeddings, no inference)
- LocaNext has battle-tested this exact HNSW config with Model2Vec

**Why HNSW > IndexFlatIP for 170K vectors:**
- `IndexFlatIP` = brute-force scan of ALL 170K vectors per query (O(n))
- `IndexHNSWFlat` = graph traversal, ~O(log n) per query (~99%+ recall)

**HNSW everywhere.** All FAISS indexes use the same config:
`IndexHNSWFlat(dim, 32, METRIC_INNER_PRODUCT)`, efConstruction=400, efSearch=500.
Small pools (< 100 entries) in matching.py stay as numpy dot product (no FAISS needed).

## Normalization Decision

LocaNext normalizes at BOTH encode and FAISS boundary. This is idempotent and safe.
QuickTranslate does the same — normalize at FAISS boundary with `faiss.normalize_L2()`.
The encode helper returns raw float32 embeddings; normalization happens before `index.add()` and `index.search()`.

## Shared Encode Helper

Single helper in `fuzzy_matching.py`, imported by matching.py and missing_translation_finder.py:

```python
def encode_texts(model, texts):
    """Encode texts with Model2Vec. Returns np.ndarray(float32).

    Callers MUST check for empty lists before calling.
    """
    import numpy as np
    result = model.encode(texts)
    return np.array(result, dtype=np.float32)
```

**Empty-list guards are the CALLER's responsibility.** `if not texts: continue/return` before calling.

## What Changes (12 files)

### 1. `config.py`
- **Remove:** `KRTRANSFORMER_PATH`, `FUZZY_ENGINE_KRSBERT`, `FUZZY_ENGINE_MODEL2VEC`, `FUZZY_ENGINE_DEFAULT`
- **Keep:** `MODEL2VEC_PATH = SCRIPT_DIR / "Model2Vec"`
- **Keep:** All threshold constants
- **Update comment:** FAISS comment → "IndexHNSWFlat with Model2Vec (LocaNext pattern)"

### 2. `core/fuzzy_matching.py`
- **Remove:** `check_model_available()` (KR-SBERT checker, lines 33-67)
- **Remove:** `load_model()` (KR-SBERT loader, lines 179-226)
- **Remove:** `_cached_model` (KR-SBERT cache variable)
- **Remove:** `check_engine_available()`, `load_engine()` (dispatchers, lines 102-158)
- **Remove:** `_encode_texts()` (class-name sniffing dispatcher, lines 161-176)
- **Remove:** `_cached_model2vec`, `_model2vec_lock` (separate cache variables)
- **Rename:** `check_model2vec_available()` → `check_model_available()`
- **Rename:** `load_model2vec()` → `load_model()`
- **Keep:** `_cached_model`, `_cache_lock` (single cache, reuse names)
- **Add:** `encode_texts(model, texts)` — shared helper (exported)
- **Update:** `clear_cache()` — single model cache, remove `_model2vec_lock` block
- **Update docstring:** Remove KR-SBERT references
- **Rewrite `build_faiss_index()`:**
  - Use `encode_texts()` helper for batched encoding
  - `np.ascontiguousarray(embeddings, dtype=np.float32)`
  - `faiss.normalize_L2(embeddings)` (in-place)
  - `index = faiss.IndexHNSWFlat(dim, 32, faiss.METRIC_INNER_PRODUCT)`
  - `index.hnsw.efConstruction = 400`
  - `index.hnsw.efSearch = 500`
  - `index.add(embeddings)`
- **Rewrite `search_fuzzy()`:**
  - Use `encode_texts()` for query encoding
  - `np.ascontiguousarray(query_embedding, dtype=np.float32)`
  - `faiss.normalize_L2(query_embedding)` before search
  - Guard: if `index.ntotal == 0`, return empty list

### 3. `core/matching.py`
- **Remove:** `_encode_texts_compat()` helper (lines 22-31)
- **Add:** `from .fuzzy_matching import encode_texts` (inside try/except ImportError)
- **Replace:** 4 call sites with `encode_texts(fuzzy_model, texts)`
- **Update:** Pools >= 100 entries: `IndexFlatIP` → `IndexHNSWFlat` (same HNSW config)
- **Keep:** Pools < 100 entries: numpy dot product
- **Add:** Empty-list guard before each encode call

### 4. `core/missing_translation_finder.py`
- **Remove:** `_encode_texts_compat()` helper (lines 27-39)
- **Add:** `from .fuzzy_matching import encode_texts` (inside try/except ImportError)
- **Replace:** 4 call sites (lines 1919, 1989, 2131, 2200) with `encode_texts(model, texts)`
- **Update:** "KR-SBERT" string literals (lines 1900, 1905) → "Model2Vec"

### 5. `gui/app.py`
- **Remove:** `self.fuzzy_engine` StringVar, `self._fuzzy_engine_used` tracking
- **Remove:** Engine radio buttons from `fuzzy_sub_frame`
- **Remove:** `_on_engine_changed()` method
- **Remove:** All `self._fuzzy_engine_used` checks in cache validation
- **Remove imports:** `check_model2vec_available`, `check_engine_available`, `load_model2vec`, `load_engine`
- **Keep imports:** `check_model_available`, `load_model` (now point to Model2Vec)
- **Simplify:** `_update_fuzzy_model_status()` — direct `check_model_available()`, no dispatch
- **Simplify:** `_ensure_fuzzy_model()` — direct `load_model(callback)`, no engine param
- **Remove:** Engine persistence in settings.json
- **Update:** Log lines → "Model2Vec" (lines 2233, 2851)

### 6. `QuickTranslate.spec`
- **Remove from METADATA_PACKAGES:** `'torch'`, `'sentence-transformers'`, `'transformers'`, `'huggingface-hub'`
- **Remove from COLLECT_ALL_PACKAGES:** `'sentence_transformers'`, `'transformers'`, `'huggingface_hub'`
- **Remove from hiddenimports:** `'torch'`, `'safetensors.torch'`
- **Remove:** `runtime_hooks=[os.path.join(spec_dir, 'runtime_hook_torch.py')]` → `runtime_hooks=[]`
- **Keep:** `'model2vec'`, `'safetensors'`, `'tokenizers'`, `'faiss-cpu'`, `'numpy'`
- **Update comments:** Remove torch/sentence-transformers references
- **Result:** Build shrinks by ~2GB (no torch)

### 7. `requirements-ml.txt`
- **Remove:** `sentence-transformers>=2.2.0`, `torch>=2.0.0`
- **Keep:** `model2vec>=0.3.0`, `faiss-cpu>=1.7.0`, `numpy>=1.24.0`

### 8. `core/__init__.py`
- **Keep:** `from .fuzzy_matching import check_model_available, load_model as load_fuzzy_model` — works after rename
- **Update comment:** "sentence-transformers" → "model2vec"

### 9. `main.py` — Smoke test overhaul
- **Remove:** All torch tests (sections 3, 9), sentence-transformers tests (section 6), transformers tests (section 7)
- **Remove:** `huggingface_hub`, `scipy`, `sklearn` from section 8
- **Update:** config check: `KRTRANSFORMER_PATH` → `MODEL2VEC_PATH`
- **Add:** `import model2vec` test, `from model2vec import StaticModel` test
- **Update:** Total test count in pass message

### 10. `runtime_hook_torch.py`
- **Delete the file entirely**

### 11. `core/xml_transfer.py` (VERIFY — no code change)
- Line 1721: `from .fuzzy_matching import load_model` → works automatically after rename
- No code change needed

### 12. `.github/workflows/quicktranslate-build.yml` — CI overhaul
- **Remove:** torch install, sentence-transformers install
- **Replace with:** `pip install --no-cache-dir model2vec faiss-cpu numpy`
- **Remove:** torch/sentence-transformers verification steps
- **Replace with:** Model2Vec + FAISS verification
- **Remove:** torch DLL checks, sentence_transformers dir check, runtime_hook_torch check
- **Update:** Build size threshold: 1500MB → ~500MB
- **Keep:** requests + deps (may be needed by model2vec/tokenizers)

## LocaNext Techniques Applied

| What | LocaNext | QuickTranslate (after migration) |
|------|----------|----------------------------------|
| Encoding | `model.encode()` → `np.array(float32)` | Same (via `encode_texts()`) |
| FAISS index | `IndexHNSWFlat(dim, 32, METRIC_INNER_PRODUCT)` | Same |
| HNSW M | 32 | Same |
| HNSW efConstruction | 400 | Same |
| HNSW efSearch | 500 | Same |
| Model loading | `StaticModel.from_pretrained(path)` | Same |
| Normalization | `faiss.normalize_L2()` + `np.ascontiguousarray()` | Same |
| Zero-norm guard | `np.where(norms == 0, 1, norms)` | Same (at FAISS boundary) |

## What We DON'T Copy from LocaNext

- `EmbeddingEngine` ABC — one engine, no abstraction needed
- `FAISSManager` class — throwaway indexes, no persistence
- Engine switching API/UI — only Model2Vec
- Incremental index updates — rebuilds per session
- 5-tier search cascade — QuickTranslate uses single FAISS tier
- Hash-based perfect match tier — not applicable

## Documentation Files to Update (post-migration cleanup)

Stale docs after migration:
- `docs/FAISS_IMPLEMENTATION.md` — KR-SBERT refs, "IndexFlatIP ONLY" rule
- `docs/DEV_GUIDE.md` — `runtime_hook_torch.py` reference
- `docs/PYINSTALLER_ML_BUNDLING.md` — torch bundling docs
- `requirements.txt` — "SBERT + FAISS" comment

## `from __future__ import annotations` Sweep

All modified `.py` files get `from __future__ import annotations` (NewScripts protocol):
- `core/fuzzy_matching.py`, `core/matching.py`, `core/missing_translation_finder.py`
- `config.py`, `main.py`

## Execution Order

1. Wait for Build 032 to pass
2. Test Model2Vec fuzzy matching with real data on offline PC
3. If it works → execute this migration (one commit)
4. If Model2Vec too slow → add difflib as no-ML fallback before migrating

## Net Result

- ~400 lines deleted (net, including CI cleanup)
- Build size: -2GB (no torch)
- One model, one code path, zero dispatch logic
- Battle-tested encoding + HNSW indexing from LocaNext
- Single `encode_texts()` helper replaces 3 duplicate `_encode_texts_compat()` functions
- Single normalization point (`faiss.normalize_L2`) at FAISS boundary
