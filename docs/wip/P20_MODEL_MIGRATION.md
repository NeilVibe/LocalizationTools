# P20: Embedding Model Migration Plan

**Created:** 2025-12-09
**Status:** PLANNING
**Goal:** Unify all tools to Qwen3-Embedding-0.6B (WebTranslatorNew pattern)

---

## Current State Analysis

### XLSTransfer (`server/tools/xlstransfer/embeddings.py`)
```python
# MODEL
MODEL_NAME = "snunlp/KR-SBERT-V40K-klueNLI-augSTS"
model = SentenceTransformer(config.MODEL_NAME)

# FAISS INDEX
index = faiss.IndexFlatIP(embedding_dim)  # Flat brute-force
faiss.normalize_L2(embeddings)
index.add(embeddings)

# EMBEDDING
batch_embeddings = model.encode(batch_texts, convert_to_tensor=False)
# Dimension: 384
```

### KR Similar (`server/tools/kr_similar/embeddings.py`)
```python
# MODEL
MODEL_NAME = "snunlp/KR-SBERT-V40K-klueNLI-augSTS"
self.model = SentenceTransformer(MODEL_NAME)
self.model.to(self.device)  # GPU support

# FAISS INDEX
faiss.normalize_L2(self.split_embeddings)
self.split_index = faiss.IndexFlatIP(self.split_embeddings.shape[1])
self.split_index.add(self.split_embeddings)

# EMBEDDING
batch_embeddings = self.model.encode(batch, device=self.device)
# Dimension: 384
```

### WebTranslatorNew (Target Pattern)
```python
# MODEL
model_name = 'Qwen/Qwen3-Embedding-0.6B'
_global_model = SentenceTransformer(model_name)

# FAISS INDEX (HNSW - faster for large datasets!)
dimension = 384
index = faiss.IndexHNSWFlat(dimension, 32, faiss.METRIC_INNER_PRODUCT)
index.hnsw.efConstruction = 400  # Build quality
index.hnsw.efSearch = 500         # Search quality
faiss.normalize_L2(embeddings)
index.add(embeddings)

# EMBEDDING
embeddings = model.encode(normalized_texts, convert_to_tensor=False, batch_size=64)
# Dimension: 384 (SAME!)
```

---

## Key Differences

| Aspect | Current (KR-SBERT) | Target (Qwen3) |
|--------|-------------------|----------------|
| **Model** | snunlp/KR-SBERT-V40K | Qwen/Qwen3-Embedding-0.6B |
| **Size** | 447 MB | 1.21 GB |
| **Languages** | Korean only | 100+ multilingual |
| **Dimension** | 384 | 384 (COMPATIBLE!) |
| **License** | MIT | Apache 2.0 |
| **FAISS Index** | IndexFlatIP (brute force) | IndexHNSWFlat (O(log n)) |
| **Search Speed** | O(n) | O(log n) - MUCH FASTER |

---

## Migration Tasks

### Phase 1: Shared Embedding Module (NEW)

- [ ] **1.1** Create `server/utils/embeddings/qwen_embeddings.py`
  ```python
  """
  Unified Qwen3 Embedding Manager
  Shared by XLSTransfer, KR Similar, LDM
  """
  from sentence_transformers import SentenceTransformer
  import faiss

  MODEL_NAME = 'Qwen/Qwen3-Embedding-0.6B'
  EMBEDDING_DIM = 384

  class QwenEmbeddingManager:
      _model = None  # Singleton

      @classmethod
      def get_model(cls):
          if cls._model is None:
              cls._model = SentenceTransformer(MODEL_NAME)
          return cls._model

      @staticmethod
      def create_hnsw_index(embeddings):
          """Create HNSW index (WebTranslatorNew pattern)"""
          index = faiss.IndexHNSWFlat(EMBEDDING_DIM, 32, faiss.METRIC_INNER_PRODUCT)
          index.hnsw.efConstruction = 400
          index.hnsw.efSearch = 500
          faiss.normalize_L2(embeddings)
          index.add(embeddings)
          return index
  ```

- [ ] **1.2** Add config option for model selection
  ```python
  # server/config.py or tool config
  EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'qwen')  # 'qwen' or 'kr-sbert'
  ```

### Phase 2: XLSTransfer Migration

- [ ] **2.1** Update `server/tools/xlstransfer/config.py`
  ```python
  # OLD
  MODEL_NAME = "snunlp/KR-SBERT-V40K-klueNLI-augSTS"

  # NEW
  MODEL_NAME = "Qwen/Qwen3-Embedding-0.6B"
  ```

- [ ] **2.2** Update `server/tools/xlstransfer/embeddings.py`
  - Change `IndexFlatIP` to `IndexHNSWFlat`
  - Add HNSW params
  - Keep backward compatibility for existing dictionaries

- [ ] **2.3** Update dictionary format version
  ```python
  # Add version header to saved dictionaries
  DICT_VERSION = "2.0"  # Qwen + HNSW
  ```

### Phase 3: KR Similar Migration

- [ ] **3.1** Update `server/tools/kr_similar/embeddings.py`
  - Change MODEL_NAME to Qwen
  - Change IndexFlatIP to IndexHNSWFlat
  - Keep GPU support

- [ ] **3.2** Update dictionary save/load
  - Version check for old vs new format
  - Auto-migration on first load

### Phase 4: Model Download Scripts

- [ ] **4.1** Update `scripts/download_bert_model.py`
  ```python
  # Download Qwen instead of KR-SBERT
  model = SentenceTransformer('Qwen/Qwen3-Embedding-0.6B')
  model.save('./models/qwen-embedding')
  ```

- [ ] **4.2** Update `scripts/download_model.bat` (Windows)

- [ ] **4.3** Update `scripts/download_model_silent.bat`

### Phase 5: LFS Bundling (Optional)

- [ ] **5.1** Add Qwen model to Git LFS
  ```bash
  git lfs track "models/qwen-embedding/*"
  ```

- [ ] **5.2** Update `.gitea/workflows/build.yml`
  - Include model in installer (if bundling enabled)

- [ ] **5.3** Test installer with bundled model (~1.5GB)

### Phase 6: Testing & Verification

- [ ] **6.1** Unit tests for new embedding module
- [ ] **6.2** Compare similarity scores: KR-SBERT vs Qwen
- [ ] **6.3** Benchmark search speed: Flat vs HNSW
- [ ] **6.4** E2E test with real files

### Phase 7: Cleanup

- [ ] **7.1** Remove old KR-SBERT references
- [ ] **7.2** Update documentation
- [ ] **7.3** Migration guide for existing users

---

## Backward Compatibility

```python
def load_dictionary(path):
    """Load dictionary with version detection"""
    with open(path / 'metadata.json') as f:
        meta = json.load(f)

    if meta.get('version', '1.0') == '1.0':
        # Old KR-SBERT dictionary
        # Option A: Auto-migrate
        # Option B: Warn user, require re-creation
        logger.warning("Old dictionary format detected, regeneration recommended")

    # Load based on version...
```

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Similarity scores differ | Medium | Side-by-side testing before rollout |
| Old dictionaries incompatible | Medium | Version detection + migration path |
| Larger model size (1.2GB vs 447MB) | Low | LFS bundling option |
| Memory usage increase | Low | Qwen 0.6B is still small |

---

## Decision Required

**Before starting, confirm:**

1. **Model switch approved?** ☐ Yes / ☐ No
2. **LFS bundling preferred?** ☐ Yes (larger installer) / ☐ No (download on first run)
3. **Backward compatibility level?**
   - ☐ Auto-migrate old dictionaries
   - ☐ Require manual re-creation
   - ☐ Support both formats indefinitely

---

## Timeline Estimate

| Phase | Tasks | Effort |
|-------|-------|--------|
| Phase 1 | Shared module | 2-3 hours |
| Phase 2 | XLSTransfer | 1-2 hours |
| Phase 3 | KR Similar | 1-2 hours |
| Phase 4 | Download scripts | 1 hour |
| Phase 5 | LFS bundling | 2-3 hours |
| Phase 6 | Testing | 2-3 hours |
| Phase 7 | Cleanup | 1 hour |
| **Total** | | **~12-15 hours** |

---

*Created by Claude - awaiting user confirmation to proceed*
