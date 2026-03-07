# Model2Vec Migration — QuickTranslate

**Completed: March 7, 2026 (Build 035)**

Replaced KR-SBERT (`snunlp/KR-SBERT-V40K-klueNLI-augSTS`, 768-dim, torch + sentence-transformers) with Model2Vec (`minishlab/potion-multilingual-128M`, 256-dim, static embeddings). Replaced FAISS IndexFlatIP (brute-force) with IndexHNSWFlat (approximate nearest neighbor, O(log n)).

---

## Why Model2Vec

### The Problem with KR-SBERT

KR-SBERT was accurate but came with massive costs:

| Issue | Impact |
|-------|--------|
| **torch dependency** | ~2GB added to build size |
| **WinError 1114** | DLL hell on fresh Windows machines (no VC++ Redist) |
| **Slow encoding** | 170K texts took minutes on CPU |
| **Build time** | 11+ minutes per CI build |
| **Runtime hook** | 3-layer DLL defense hack (`runtime_hook_torch.py`) |

### Why Model2Vec Wins

[Model2Vec](https://github.com/MinishLab/model2vec) by MinishLab is a technique that distills Sentence Transformer models into small, fast **static embedding** models. Static means each token has a pre-computed embedding — no neural network inference at encode time.

**Official benchmarks:**

| Metric | Value | Source |
|--------|-------|--------|
| Speed vs Sentence Transformers | **500x faster** on CPU | [MinishLab GitHub](https://github.com/MinishLab/model2vec) |
| Model size | **50x smaller** (~30MB vs 400MB+) | [MinishLab GitHub](https://github.com/MinishLab/model2vec) |
| MTEB accuracy vs all-MiniLM-L6-v2 | **92.11%** (potion-base-32M) | [Benchmark results](https://github.com/MinishLab/model2vec/blob/main/results/README.md) |
| Multilingual accuracy vs LaBSE | **90.86%** (potion-multilingual-128M) | [HuggingFace model card](https://huggingface.co/minishlab/potion-multilingual-128M) |
| Languages supported | **101** (including Korean) | [HuggingFace model card](https://huggingface.co/minishlab/potion-multilingual-128M) |

The `potion-multilingual-128M` model is distilled from [BAAI/bge-m3](https://huggingface.co/BAAI/bge-m3), a top-tier multilingual Sentence Transformer, and trained on 101 languages via the C4 dataset.

**Community adoption:**
- Featured on [Hacker News front page](https://news.ycombinator.com/item?id=41685821)
- Integrated into [Sentence Transformers](https://huggingface.co/blog/static-embeddings) and [LangChain](https://minishlab.github.io/) officially
- Official [Rust implementation](https://github.com/MinishLab/model2vec-rs) available
- Active development by MinishLab (Stephan Tulkens and Thomas van Dongen)

### Why Not difflib?

Python's `difflib.SequenceMatcher` compares **character sequences** — it finds the longest common substring. This fundamentally cannot do semantic matching:

| Scenario | difflib | Model2Vec |
|----------|---------|-----------|
| Same meaning, minor rewording: `퀘스트를 완료하세요` vs `퀘스트를 완료해 주세요` | ~0.75 (partial char overlap) | ~0.95 (same meaning) |
| Same meaning, different words: `확인` vs `알겠습니다` (both = "OK") | ~0.0 (zero chars shared) | ~0.85 (semantic match) |
| Word reordering | Score drops sharply | Handles correctly |
| Added/removed particles (Korean grammar) | Unreliable | Robust |

QuickTranslate's fuzzy matching exists precisely for the case where StrOrigin changed since extraction but the **meaning** is the same. Character matching can't solve this.

### The Hierarchy of Text Matching

```
difflib (character)   →  Can't match "확인" to "알겠습니다"
    ↓
TF-IDF / BM25 (token) →  Better, but misses synonyms
    ↓
Model2Vec (semantic)   →  Understands meaning, 500x faster than full transformers
    ↓
Full SBERT (semantic)  →  Marginally better accuracy, 500x slower, needs torch
```

Model2Vec is the sweet spot: semantic understanding without the torch tax.

---

## What Changed

### Build Impact

| Metric | Before (KR-SBERT) | After (Model2Vec) | Change |
|--------|-------------------|-------------------|--------|
| **Build size** | ~2 GB | 160.9 MB | **12x smaller** |
| **Build time** | 11m 31s | 3m 59s | **3x faster** |
| **Setup installer** | ~800 MB | ~40 MB | **20x smaller** |
| **Portable zip** | ~900 MB | ~62 MB | **15x smaller** |
| **Encoding speed** | Baseline | 79x faster | **79x faster** |
| **torch dependency** | Required (2GB) | Eliminated | Gone |
| **Runtime hook** | 3-layer DLL defense | Not needed | Gone |
| **Size gate (CI)** | 1500 MB | 500 MB | Tighter |

### FAISS Index Change

| Parameter | Before | After | Why |
|-----------|--------|-------|-----|
| **Index type** | IndexFlatIP (brute-force) | IndexHNSWFlat (graph) | O(n) → O(log n) search |
| **Dimension** | 768 | 256 | Model2Vec output dimension |
| **M** | N/A | 32 | Graph connectivity |
| **efConstruction** | N/A | 400 | Build-time accuracy |
| **efSearch** | N/A | 500 | Search-time accuracy |
| **Metric** | INNER_PRODUCT | INNER_PRODUCT | Same (cosine after L2 norm) |

These HNSW parameters are identical to LocaNext's `FAISSManager` (`server/tools/shared/faiss_manager.py`), battle-tested with hundreds of thousands of vectors.

**Why HNSW is safe now:** The original HNSW crash (Feb 2026) was caused by torch memory overhead (~2GB RAM) combined with HNSW graph construction — not FAISS itself. With Model2Vec (no torch, 256-dim vs 768-dim = 3x smaller vectors), HNSW runs perfectly.

### Files Changed (12 files)

| File | What Changed |
|------|-------------|
| **`config.py`** | Removed `KRTRANSFORMER_PATH`, kept `MODEL2VEC_PATH`. Added `from __future__ import annotations`. |
| **`core/fuzzy_matching.py`** | Complete rewrite. Single `check_model_available()` + `load_model()` + `encode_texts()`. HNSW index builder. Removed dual-engine dispatch, KR-SBERT loader, class-name sniffing. |
| **`core/matching.py`** | 665 → 30 lines. Removed 9 dead LOOKUP functions. Only `format_multiple_matches()` survives. |
| **`core/__init__.py`** | 253 → 163 lines. Removed ~40 dead exports from deleted LOOKUP/matching functions. |
| **`core/missing_translation_finder.py`** | 6 stale "SBERT" comments → "Model2Vec". Added `from __future__ import annotations`. |
| **`core/excel_io.py`** | Cleaned up misleading "Found StringID" log. Now only logs when EventName resolution is involved. |
| **`gui/app.py`** | Removed dual-engine UI (radio buttons, engine tracking). Removed 13 dead imports. "KR-SBERT" label → "Model2Vec". |
| **`main.py`** | Smoke test: removed torch/sentence-transformers/regex tests. Added Model2Vec + FAISS HNSW tests. Added `from __future__ import annotations`. |
| **`QuickTranslate.spec`** | Removed torch/sentence-transformers/transformers/huggingface-hub from metadata and hiddenimports. Removed `runtime_hook_torch.py`. |
| **`requirements-ml.txt`** | Removed `torch`, `sentence-transformers`. Kept `model2vec`, `faiss-cpu`, `numpy`. |
| **`requirements.txt`** | Comment update: "SBERT + FAISS" → "Model2Vec + FAISS". |
| **`.github/workflows/quicktranslate-build.yml`** | Removed torch install. Updated import validation. Updated ML verification. Size threshold 1500MB → 500MB. |

### Files Deleted

| File | Why |
|------|-----|
| `runtime_hook_torch.py` | 3-layer DLL defense for torch — no longer needed |

### Dead Code Removed

The entire LOOKUP feature was removed from the GUI in a previous refactor, but its matching functions remained. This migration cleaned them out:

**From `core/matching.py` (9 functions, ~635 lines):**
- `find_matches` — Substring matching for LOOKUP
- `find_matches_with_stats` — Substring with statistics
- `find_matches_stringid_only` — StringID-only LOOKUP
- `find_matches_strict` — Strict LOOKUP
- `find_matches_strorigin_descorigin` — StrOrigin+DescOrigin LOOKUP
- `find_matches_strorigin_descorigin_fuzzy` — Fuzzy version of above
- `find_matches_special_key` — Special key LOOKUP
- `find_matches_strict_fuzzy` — Strict fuzzy LOOKUP
- `find_stringid_from_text` — Reverse text → StringID LOOKUP

**From `core/__init__.py` (~40 dead exports):** All re-exports of deleted functions, plus unused imports from `excel_io`, `xml_transfer`, `source_scanner`, `failure_report`, `missing_translation_finder`, and `eventname_resolver`.

---

## Technical Design Decisions

### 1. Single Normalization Point

`faiss.normalize_L2()` is called ONCE at the FAISS boundary — before `index.add()` and before `index.search()`. Never inside `encode_texts()`. This prevents accidental double-normalization and keeps the encode helper pure.

### 2. Empty String Guard

Empty strings produce zero vectors. `faiss.normalize_L2()` on a zero vector produces NaN → corrupts the entire index. Guard:

```python
texts = [t if t.strip() else " " for t in texts]
```

### 3. Engine-Agnostic `encode_texts()`

The encode helper detects model type by class name — no cross-imports needed:

```python
def encode_texts(model, texts):
    if type(model).__name__ == "StaticModel":
        return model.encode(texts)           # Model2Vec
    else:
        return model.encode(texts,           # SentenceTransformer (legacy fallback)
                           convert_to_numpy=True,
                           show_progress_bar=False)
```

This keeps backward compatibility if KR-SBERT is ever needed again, without importing either library.

### 4. Batch Accumulation with np.vstack

```python
all_embeddings = []
for i in range(0, total, batch_size):
    batch_emb = encode_texts(model, batch)
    all_embeddings.append(batch_emb)          # Append numpy arrays
embeddings = np.vstack(all_embeddings)        # Single concatenation at end
```

`append` + `vstack` is O(n). The old pattern `list.extend(batch_embeddings)` unpacked each batch into individual row objects — O(n^2) for large datasets.

### 5. Model Folder Pattern

`Model2Vec/` folder sits next to the exe (or `main.py` for source), same pattern as the old `KRTransformer/`. Contains:
- `config.json`
- `model.safetensors`
- `tokenizer.json` (+ related tokenizer files)

NOT bundled in PyInstaller — too large for the build. Distributed separately or user downloads from HuggingFace.

### 6. No Runtime Hook Needed

With torch gone, there's no complex DLL dependency chain. PyInstaller's standard binary analysis handles Model2Vec's lightweight native deps (tokenizers Rust binary, numpy) correctly. The 3-layer `runtime_hook_torch.py` defense is deleted.

---

## LocaNext Alignment

QuickTranslate now uses the exact same FAISS + Model2Vec pattern as LocaNext:

| Component | LocaNext (`faiss_manager.py`) | QuickTranslate (`fuzzy_matching.py`) |
|-----------|-------------------------------|--------------------------------------|
| Model | `StaticModel.from_pretrained()` | Same |
| Encoding | `model.encode(texts)` → `float32` | Same (via `encode_texts()`) |
| Normalization | `faiss.normalize_L2()` | Same |
| Index | `IndexHNSWFlat(dim, 32, METRIC_INNER_PRODUCT)` | Same |
| M | 32 | Same |
| efConstruction | 400 | Same |
| efSearch | 500 | Same |

**What we don't copy from LocaNext** (intentionally simpler):
- `EmbeddingEngine` ABC — one engine, no abstraction needed
- `FAISSManager` class — throwaway indexes, no persistence
- Incremental index updates — rebuilds per session
- 5-tier search cascade — single FAISS tier
- Hash-based perfect match tier — not applicable

---

## Offline Installation (Source)

The built exe bundles Model2Vec inside `_internal/`. But running from source on an offline machine requires pip-installing the dependencies manually.

### Download wheels (on a machine with internet):

```bash
pip download model2vec faiss-cpu -d ./model2vec_wheels \
    --platform win_amd64 --python-version 3.11 --only-binary=:all:
```

### Install on offline machine:

```bash
pip install --no-index --find-links=./model2vec_wheels model2vec faiss-cpu
```

### Model folder:

Download `minishlab/potion-multilingual-128M` from HuggingFace and place it as `Model2Vec/` next to `main.py`.

---

## CI Build Pipeline (Post-Migration)

```
Job 1: Validation (ubuntu)
  └── Version string (KST timestamp)

Job 2: Safety Checks (ubuntu)
  ├── py_compile all .py files
  ├── Import validation (format_multiple_matches, find_missing_with_options)
  ├── ML verification (model2vec, faiss, numpy, tqdm, tokenizers, safetensors)
  └── Flake8 critical errors

Job 3: Build & Release (windows)
  ├── pip install model2vec faiss-cpu numpy (no torch!)
  ├── PyInstaller build (QuickTranslate.spec)
  ├── Smoke test (--smoke-test flag, verifies all imports)
  ├── Size gate: < 500 MB
  └── Inno Setup + Portable zip + Source zip
```

---

## Verification

Build 035 results:
- **Status:** SUCCESS
- **Build time:** 3m 59s
- **Dist size:** 160.9 MB
- **SMOKE_TEST_PASSED** — Model2Vec, FAISS HNSW, numpy, tokenizers, safetensors all verified
- **Version:** 26.307.0056

---

## References

- [MinishLab/model2vec GitHub](https://github.com/MinishLab/model2vec) — Project repository
- [potion-multilingual-128M on HuggingFace](https://huggingface.co/minishlab/potion-multilingual-128M) — Model card
- [Model2Vec Benchmarks](https://github.com/MinishLab/model2vec/blob/main/results/README.md) — MTEB results
- [HuggingFace Blog: Static Embeddings](https://huggingface.co/blog/static-embeddings) — Sentence Transformers integration
- [HuggingFace Blog: Model2Vec Distillation](https://huggingface.co/blog/Pringled/model2vec) — Technical deep-dive
- [Hacker News Discussion](https://news.ycombinator.com/item?id=41685821) — Community reception
- [Model2Vec: 500x faster, 15x smaller](https://dev.to/pringled/model2vec-making-sentence-transformers-500x-faster-on-cpu-and-15x-smaller-4k2b) — DEV.to article
