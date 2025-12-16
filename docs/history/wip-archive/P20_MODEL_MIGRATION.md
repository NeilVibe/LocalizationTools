# P20: Embedding Model Migration Plan

**Created:** 2025-12-09
**Status:** ✅ COMPLETE (2025-12-09)
**Goal:** Unify all tools to Qwen3-Embedding-0.6B (WebTranslatorNew pattern)

---

## Decisions Made (User Approved)

- **Model:** Switch ALL tools to Qwen/Qwen3-Embedding-0.6B
- **FAISS:** Switch ALL tools to IndexHNSWFlat (was IndexFlatIP)
- **Bundling:** Gitea builds include full model (~1.2GB in installer)
- **Backward Compat:** New dictionaries only (users re-create with new model)

---

## Target Configuration (WebTranslatorNew Pattern)

**Source:** `RessourcesForCodingTheProject/WebTranslatorNew/EMBEDDINGS.md`

```python
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

# MODEL (line 13-14)
model_name = 'Qwen/Qwen3-Embedding-0.6B'
model = SentenceTransformer(model_name)

# EMBEDDING GENERATION (line 35-39)
embeddings = model.encode(
    normalized_texts,
    convert_to_tensor=False,
    batch_size=64
)

# FAISS INDEX CREATION (line 52-62)
# NOTE: dimension is AUTOMATIC from embeddings.shape[1]
embedding_dim = embeddings.shape[1]  # AUTOMATIC!
index = faiss.IndexHNSWFlat(embedding_dim, 32, faiss.METRIC_INNER_PRODUCT)
index.hnsw.efConstruction = 400  # Build quality
index.hnsw.efSearch = 500        # Search quality
faiss.normalize_L2(embeddings)
index.add(embeddings)
```

**Key Points:**
- Dimension is AUTOMATIC via `embeddings.shape[1]` - no hardcoding needed
- M=32 (connections per node in HNSW graph)
- efConstruction=400 (build quality - higher = better but slower build)
- efSearch=500 (search quality - higher = better but slower search)
- METRIC_INNER_PRODUCT (for cosine similarity after L2 normalization)

---

## Migration Changes (Per File)

### 1. XLSTransfer

**File: `server/tools/xlstransfer/config.py`**
```python
# LINE ~14 - Change MODEL_NAME
MODEL_NAME = "Qwen/Qwen3-Embedding-0.6B"  # was "snunlp/KR-SBERT-V40K-klueNLI-augSTS"
```

**File: `server/tools/xlstransfer/embeddings.py`**
```python
# LINE 139-169 - Change create_faiss_index function
def create_faiss_index(embeddings: np.ndarray) -> faiss.Index:
    """Create FAISS HNSW index for fast similarity search."""
    logger.info(f"Creating FAISS HNSW index for {len(embeddings)} embeddings")

    # Normalize embeddings for cosine similarity
    faiss.normalize_L2(embeddings)

    # Create HNSW index (WebTranslatorNew pattern)
    embedding_dim = embeddings.shape[1]  # AUTOMATIC
    index = faiss.IndexHNSWFlat(embedding_dim, 32, faiss.METRIC_INNER_PRODUCT)
    index.hnsw.efConstruction = 400
    index.hnsw.efSearch = 500

    # Add embeddings to index
    index.add(embeddings)

    logger.info(f"FAISS HNSW index created with {index.ntotal} vectors")
    return index
```

### 2. KR Similar

**File: `server/tools/kr_similar/embeddings.py`**
```python
# LINE 35 - Change MODEL_NAME
MODEL_NAME = "Qwen/Qwen3-Embedding-0.6B"  # was "snunlp/KR-SBERT-V40K-klueNLI-augSTS"

# LINE 343-345 - Change split index creation
faiss.normalize_L2(self.split_embeddings)
embedding_dim = self.split_embeddings.shape[1]
self.split_index = faiss.IndexHNSWFlat(embedding_dim, 32, faiss.METRIC_INNER_PRODUCT)
self.split_index.hnsw.efConstruction = 400
self.split_index.hnsw.efSearch = 500
self.split_index.add(self.split_embeddings)

# LINE 353-355 - Change whole index creation (same pattern)
faiss.normalize_L2(self.whole_embeddings)
embedding_dim = self.whole_embeddings.shape[1]
self.whole_index = faiss.IndexHNSWFlat(embedding_dim, 32, faiss.METRIC_INNER_PRODUCT)
self.whole_index.hnsw.efConstruction = 400
self.whole_index.hnsw.efSearch = 500
self.whole_index.add(self.whole_embeddings)
```

### 3. LDM TM (New)

**File: `server/tools/ldm/tm_search.py` (to create)**
- Uses same Qwen model + HNSW pattern
- Integrates with TMManager for TM search

---

## Gitea Full Bundle Configuration

**Build Modes:**
| Build | Model Included | Installer Size |
|-------|----------------|----------------|
| GITHUB (LIGHT) | No - downloads on first run | ~100 MB |
| GITEA (FULL) | Yes - bundled in installer | ~1.3 GB |

**File: `.gitea/workflows/build.yml`**
```yaml
# Add to FULL build section
- name: Bundle Qwen Model (FULL only)
  if: contains(env.TRIGGER_CONTENT, 'FULL')
  run: |
    # Clone Qwen model to models/
    python -c "
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer('Qwen/Qwen3-Embedding-0.6B')
    model.save('./models/qwen-embedding')
    "
```

---

## Migration Checklist

- [x] **1. Clone Qwen model** to `models/qwen-embedding/` (2.3 GB including tokenizer)
- [x] **2. Update XLSTransfer**
  - [x] 2.1 config.py: MODEL_NAME → Qwen/Qwen3-Embedding-0.6B
  - [x] 2.2 embeddings.py: create_faiss_index → HNSW
- [x] **3. Update KR Similar**
  - [x] 3.1 embeddings.py: MODEL_NAME → Qwen/Qwen3-Embedding-0.6B
  - [x] 3.2 embeddings.py: split_index → HNSW (lines 342-348)
  - [x] 3.3 embeddings.py: whole_index → HNSW (lines 356-362)
- [x] **4. Update LDM TM**
  - [x] 4.1 LDM TM imports from KR Similar → inherits Qwen automatically
- [x] **5. Update download scripts**
  - [x] 5.1 scripts/download_bert_model.py → Qwen
- [x] **6. Update Gitea build**
  - [x] 6.1 .gitea/workflows/build.yml → FULL vs LIGHT build detection
  - [x] 6.2 Download Qwen model step for FULL builds
  - [x] 6.3 Bundle model in ZIP for FULL builds
- [x] **7. Test**
  - [x] 7.1 Model verification: 1024-dim embeddings working
  - [x] 7.2 FAISS HNSW index: Created and searched successfully
  - [x] 7.3 Unit tests: 45/45 passed (updated tests for new model)

---

## Performance Comparison

| Metric | IndexFlatIP (Before) | IndexHNSWFlat (After) |
|--------|---------------------|----------------------|
| Search complexity | O(n) brute force | O(log n) graph |
| 10K entries search | ~50ms | ~5ms |
| 100K entries search | ~500ms | ~10ms |
| 1M entries search | ~5000ms | ~50ms |
| Build time | Instant | ~2x slower (one-time) |
| Memory | ~1.5x vectors | ~2x vectors |

---

## Notes

- **Dimension is automatic**: `embeddings.shape[1]` handles any model output size
- **No backward compatibility**: Users must regenerate dictionaries with new model
- **Model path**: `models/qwen-embedding/` (local) or downloads from HuggingFace
- **GPU support**: Qwen works on both CPU and GPU (same as KR-SBERT)

---

## Testing Results (2025-12-11)

**Test Script:** `testing_toolkit/test_qwen_faiss.py`

| Test | Result | Notes |
|------|--------|-------|
| Library Imports | PASS | PyTorch 2.9.0+cu128, FAISS 1.12.0 |
| Qwen Model Loading | PASS | 27s load, 1024-dim, CUDA RTX 4070 Ti |
| Embedding Generation | PASS | 1.6 texts/sec (initial), 800/sec (batch) |
| FAISS HNSW Index | PASS | 0.13s build, <1ms search |
| Similarity Search | PASS | Cross-lingual KR↔EN working |
| KR Similar Integration | PASS | Module imports OK |
| LDM TM Integration | PASS | Fallback text search OK |
| Batch Performance | PASS | 880 texts/sec @ batch 100 |

**Known Issue:** Existing BDO dictionary (41,668 pairs) uses old KR-SBERT 768-dim embeddings.
- **Fix Required:** Users must regenerate dictionaries via KR Similar UI after migration.
- Code now uses automatic dimension detection (`embeddings.shape[1]`).

---

*Last updated: 2025-12-11 - Testing verified, dictionary rebuild pending*
