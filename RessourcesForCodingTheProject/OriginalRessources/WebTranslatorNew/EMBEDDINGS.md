# Vector Embeddings & FAISS

**Source:** `~/WebTranslatorNew/app/services/embedding.py:59-456`

---

## Embedding Model

### Model Setup
```python
from sentence_transformers import SentenceTransformer

model_name = 'Qwen/Qwen3-Embedding-0.6B'  # Multilingual
_global_model = SentenceTransformer(model_name)
```

- **Model:** Qwen3 Embedding 0.6B (multilingual)
- **Memory:** ~2.4GB
- **Singleton:** Thread-safe with lock

### Batch Embedding Generation
```python
def generate_embeddings_batch(
    texts: List[str],
    progress_callback = None,
    task_id: str = None
) -> np.ndarray:
    """
    Generate embeddings for batch of texts.
    - Automatic batching (64 texts per batch)
    - Cancellation support via task_id
    - Progress callbacks for UI
    """
    model = get_embedding_model()
    embeddings = model.encode(
        normalized_texts,
        convert_to_tensor=False,
        batch_size=64
    )
    return embeddings
```

---

## FAISS Index Creation

### HNSW Index (Recommended)
```python
import faiss

def get_faiss_index(glossary_id: int, force_reload: bool = False):
    # Create HNSW index (Hierarchical Navigable Small World)
    dimension = 384  # Depends on model
    index = faiss.IndexHNSWFlat(dimension, 32, faiss.METRIC_INNER_PRODUCT)

    # High quality construction
    index.hnsw.efConstruction = 400
    index.hnsw.efSearch = 500

    # Normalize for cosine similarity
    faiss.normalize_L2(embeddings)
    index.add(embeddings)

    return index
```

**Performance:**
- 97%+ precision with O(log n) search
- ~4 bytes per dimension × entry count
- 1000 entries × 384 dims = ~1.5MB

### Caching Strategy
```python
# Global caches
_faiss_indices_cache = {}           # key: "glossary_{id}"
_line_faiss_indices_cache = {}      # key: "glossary_lines_{id}"
_whole_text_lookup_cache = {}       # key: "whole_text_lookup_{id}"
_line_lookup_cache = {}             # key: "line_lookup_{id}"

# Cache invalidation
force_reload=True  # Rebuild on data change
```

---

## Perfect Match Lookups (O(1))

### Whole Text Lookup
```python
def build_whole_text_lookup(glossary_id: int) -> dict:
    lookup = {}
    for entry in glossary_entries:
        source = normalize_newlines(entry.source_text)
        lookup[source] = {
            'target_text': entry.target_text,
            'entry_id': entry.id
        }
        lookup[source.strip()] = {...}  # Whitespace variant
    return lookup
```

### Line Lookup
```python
def build_line_lookup(glossary_id: int) -> dict:
    lookup = {}
    for line_entry in line_entries:
        source_line = normalize_newlines(line_entry.source_line)
        if source_line.strip():
            lookup[source_line] = {
                'target_line': line_entry.target_line,
                'entry_id': line_entry.entry_id,
                'line_number': line_entry.line_number
            }
    return lookup
```

---

## Text Normalization

```python
def normalize_newlines(text: str) -> str:
    """Convert escaped newlines to actual newlines"""
    return text.replace('\\n', '\n') if text else text

def normalize_text_for_embedding(text: str) -> str:
    """Normalize for embedding generation"""
    text = normalize_newlines(text)
    return text.strip()
```

---

## Database Storage

```python
# Store embedding as binary blob
embedding_binary = embedding.astype(np.float32).tobytes()

# Load from binary
embedding = np.frombuffer(embedding_binary, dtype=np.float32)
```

---

## Integration Notes

**Reuse for LDM TM:**
1. KR Similar already uses FAISS
2. Can share model singleton across tools
3. Line-level embeddings useful for LanguageData rows
4. Perfect lookup hash for exact matches

**Memory per 10,000-entry glossary:** ~10-15MB
