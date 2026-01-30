# P17: LDM TM System - COMPLETE ARCHITECTURE

**Version:** 1.1
**Created:** 2025-12-09
**Updated:** 2025-12-09 (P20 Qwen Migration)
**Status:** READY FOR IMPLEMENTATION

> This document defines the COMPLETE TM architecture with MAXIMUM analysis and MAXIMUM indexing.
> **Model:** Qwen/Qwen3-Embedding-0.6B (1024-dim, 100+ languages) - unified across all tools (P20).
> **FAISS:** IndexHNSWFlat (M=32, efConstruction=400, efSearch=500, METRIC_INNER_PRODUCT).

---

## Table of Contents

1. [Overview](#1-overview)
2. [Storage Architecture](#2-storage-architecture)
3. [Analysis Types (12 Types)](#3-analysis-types-12-types)
4. [Index Types (10 Indexes)](#4-index-types-10-indexes)
5. [Update Logic](#5-update-logic)
6. [Search Cascade](#6-search-cascade)
7. [Implementation Plan](#7-implementation-plan)

---

## 1. Overview

### 1.1 Design Principles

```
MAXIMUM ANALYSIS + MAXIMUM INDEXING + OPTIMAL PERFORMANCE
────────────────────────────────────────────────────────────

1. ANALYZE EVERYTHING
   - Every granularity: whole → sentence → line → word → character
   - Every method: semantic, lexical, fuzzy, exact

2. INDEX EVERYTHING
   - Pre-build ALL indexes on TM upload
   - Each analysis type has dedicated index
   - O(1) or O(log n) lookups, never O(n)

3. UPDATE INCREMENTALLY
   - NEVER full rebuild unless necessary
   - Track changes at entry level
   - Update only affected index portions
   - Version all indexes for rollback

4. SEARCH OPTIMALLY
   - Cascade from fastest to slowest
   - Early termination on perfect match
   - Parallel search when beneficial
   - Cache hot queries
```

### 1.2 System Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              TM SYSTEM ARCHITECTURE                              │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌─────────────┐     ┌──────────────────────────────────────────────────────┐   │
│  │  TM UPLOAD  │────▶│                   INDEX BUILDER                       │   │
│  │ TMX/Excel/  │     │                                                       │   │
│  │    TXT      │     │  ┌─────────────────────────────────────────────────┐  │   │
│  └─────────────┘     │  │              ANALYSIS ENGINE                     │  │   │
│                      │  │                                                  │  │   │
│                      │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐         │  │   │
│                      │  │  │  WHOLE   │ │   LINE   │ │ SENTENCE │         │  │   │
│                      │  │  │ Embedding│ │ Embedding│ │ Embedding│         │  │   │
│                      │  │  └────┬─────┘ └────┬─────┘ └────┬─────┘         │  │   │
│                      │  │       │            │            │                │  │   │
│                      │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐         │  │   │
│                      │  │  │   WORD   │ │  N-GRAM  │ │   HASH   │         │  │   │
│                      │  │  │  Tokens  │ │ Char/Word│ │  Exact   │         │  │   │
│                      │  │  └────┬─────┘ └────┬─────┘ └────┬─────┘         │  │   │
│                      │  │       │            │            │                │  │   │
│                      │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐         │  │   │
│                      │  │  │  LENGTH  │ │  PREFIX  │ │  FUZZY   │         │  │   │
│                      │  │  │  Bucket  │ │   Trie   │ │  BK-Tree │         │  │   │
│                      │  │  └──────────┘ └──────────┘ └──────────┘         │  │   │
│                      │  └─────────────────────────────────────────────────┘  │   │
│                      │                                                       │   │
│                      │  ┌─────────────────────────────────────────────────┐  │   │
│                      │  │                INDEX STORAGE                     │  │   │
│                      │  │                                                  │  │   │
│                      │  │  FAISS Indexes (3)  │  Lookup Indexes (4)        │  │   │
│                      │  │  ├── whole.hnsw     │  ├── exact_hash.pkl        │  │   │
│                      │  │  ├── line.hnsw      │  ├── prefix_trie.pkl       │  │   │
│                      │  │  └── sentence.hnsw  │  ├── ngram_inverted.pkl    │  │   │
│                      │  │                     │  └── length_buckets.pkl    │  │   │
│                      │  │                                                  │  │   │
│                      │  │  Fuzzy Indexes (2)  │  Cache (1)                 │  │   │
│                      │  │  ├── bktree.pkl     │  └── query_cache.pkl       │  │   │
│                      │  │  └── rapidfuzz.pkl  │                            │  │   │
│                      │  └─────────────────────────────────────────────────┘  │   │
│                      └──────────────────────────────────────────────────────┘   │
│                                                                                  │
│  ┌─────────────┐     ┌──────────────────────────────────────────────────────┐   │
│  │   SEARCH    │────▶│                 CASCADE SEARCH                        │   │
│  │   QUERY     │     │                                                       │   │
│  └─────────────┘     │  Tier 1: Exact Hash      (0ms)     → 100%            │   │
│                      │  Tier 2: Prefix Match    (1ms)     → 98-99%          │   │
│                      │  Tier 3: Near-Exact      (2ms)     → 95-98%          │   │
│                      │  Tier 4: FAISS Whole     (5ms)     → 80-95%          │   │
│                      │  Tier 5: FAISS Line      (5ms)     → 70-90%          │   │
│                      │  Tier 6: FAISS Sentence  (5ms)     → 60-85%          │   │
│                      │  Tier 7: N-gram Jaccard  (10ms)    → 50-70%          │   │
│                      │  Tier 8: BK-Tree Edit    (15ms)    → 40-60%          │   │
│                      │  Tier 9: RapidFuzz       (20ms)    → 30-50%          │   │
│                      │                                                       │   │
│                      │  + Context Boost: +5% project, +3% file type          │   │
│                      └──────────────────────────────────────────────────────┘   │
│                                                                                  │
│  ┌─────────────┐     ┌──────────────────────────────────────────────────────┐   │
│  │   UPDATE    │────▶│              INCREMENTAL UPDATER                      │   │
│  │  (new TM)   │     │                                                       │   │
│  └─────────────┘     │  1. Detect changes (new/modified/deleted)             │   │
│                      │  2. Update ONLY affected entries                      │   │
│                      │  3. Rebuild ONLY affected index portions              │   │
│                      │  4. Version bump + atomic swap                        │   │
│                      └──────────────────────────────────────────────────────┘   │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Storage Architecture

### 2.1 Directory Structure

```
server/data/ldm_tm/{tm_id}/
│
├── metadata.json                 # TM metadata + stats + version
│
├── raw/                          # Raw data (for rebuild)
│   ├── entries.parquet           # All TM entries (source, target, metadata)
│   └── changelog.jsonl           # Append-only change log
│
├── embeddings/                   # Embedding arrays
│   ├── whole/
│   │   ├── embeddings.npy        # Shape: (N, 1024) - Qwen3-Embedding-0.6B
│   │   ├── mapping.pkl           # idx → entry_id mapping
│   │   └── dict.pkl              # source → target dictionary
│   ├── line/
│   │   ├── embeddings.npy
│   │   ├── mapping.pkl
│   │   └── dict.pkl
│   └── sentence/
│       ├── embeddings.npy
│       ├── mapping.pkl
│       └── dict.pkl
│
├── faiss/                        # FAISS indexes
│   ├── whole.hnsw                # HNSW index for whole embeddings
│   ├── line.hnsw                 # HNSW index for line embeddings
│   └── sentence.hnsw             # HNSW index for sentence embeddings
│
├── lookup/                       # Fast lookup indexes
│   ├── exact_hash.pkl            # SHA256 → entry_id (O(1) exact match)
│   ├── prefix_trie.pkl           # Trie for prefix search
│   ├── ngram_char.pkl            # Character trigram → entry_ids
│   ├── ngram_word.pkl            # Word bigram → entry_ids
│   └── length_buckets.pkl        # length_bucket → entry_ids
│
├── fuzzy/                        # Fuzzy matching indexes
│   ├── bktree.pkl                # BK-tree for edit distance
│   └── rapidfuzz_prepared.pkl    # Pre-processed for RapidFuzz
│
├── cache/                        # Runtime caches
│   ├── query_cache.pkl           # LRU cache of recent queries
│   └── hot_entries.pkl           # Frequently accessed entries
│
└── versions/                     # Version history for rollback
    ├── v001/
    ├── v002/
    └── current -> v002           # Symlink to current version
```

### 2.2 Metadata Schema

```json
{
  "tm_id": 1,
  "name": "BDO Main TM",
  "description": "Main game translation memory",
  "owner_id": 1,
  "project_id": null,

  "stats": {
    "total_entries": 150000,
    "unique_sources": 142000,
    "unique_targets": 138000,
    "whole_pairs": 142000,
    "line_pairs": 85000,
    "sentence_pairs": 95000,
    "avg_source_length": 45,
    "avg_target_length": 52
  },

  "indexes": {
    "faiss_whole": {"status": "ready", "entries": 142000, "build_time_sec": 120},
    "faiss_line": {"status": "ready", "entries": 85000, "build_time_sec": 75},
    "faiss_sentence": {"status": "ready", "entries": 95000, "build_time_sec": 85},
    "exact_hash": {"status": "ready", "entries": 142000},
    "prefix_trie": {"status": "ready", "entries": 142000},
    "ngram_char": {"status": "ready", "trigrams": 450000},
    "ngram_word": {"status": "ready", "bigrams": 280000},
    "length_buckets": {"status": "ready", "buckets": 50},
    "bktree": {"status": "ready", "entries": 142000},
    "rapidfuzz": {"status": "ready", "entries": 142000}
  },

  "version": 5,
  "created_at": "2025-12-09T10:00:00Z",
  "updated_at": "2025-12-09T15:30:00Z",
  "last_indexed_at": "2025-12-09T15:30:00Z"
}
```

---

## 3. Analysis Types (12 Types)

### 3.1 Granularity Levels

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ANALYSIS GRANULARITY                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Level 1: WHOLE TEXT                                                         │
│  ────────────────────                                                        │
│  Input:  "게임을 시작하세요.\n준비되셨나요?"                                    │
│  Output: Single embedding for entire text                                    │
│  Use:    Best for short strings, UI text, single concepts                   │
│                                                                              │
│  Level 2: LINE-BY-LINE                                                       │
│  ─────────────────────                                                       │
│  Input:  "게임을 시작하세요.\n준비되셨나요?"                                    │
│  Output: ["게임을 시작하세요.", "준비되셨나요?"] → 2 embeddings                │
│  Use:    Multi-line text, dialogue, descriptions                            │
│                                                                              │
│  Level 3: SENTENCE-LEVEL                                                     │
│  ──────────────────────                                                      │
│  Input:  "게임을 시작하세요. 준비되셨나요? 시작합니다!"                         │
│  Output: 3 embeddings (split by .!?)                                         │
│  Use:    Long paragraphs, mixed content                                      │
│                                                                              │
│  Level 4: WORD/TOKEN                                                         │
│  ────────────────────                                                        │
│  Input:  "게임을 시작하세요"                                                   │
│  Output: ["게임을", "시작하세요"] → word-level analysis                       │
│  Use:    Terminology matching, glossary                                      │
│                                                                              │
│  Level 5: CHARACTER N-GRAM                                                   │
│  ─────────────────────────                                                   │
│  Input:  "게임"                                                               │
│  Output: ["게임", "게", "임"] (char bigrams/trigrams)                         │
│  Use:    Typo tolerance, partial matching                                    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Analysis Type Details

| # | Analysis Type | Method | Index Type | Complexity | Use Case |
|---|---------------|--------|------------|------------|----------|
| 1 | **Exact Hash** | SHA256 | Hash table | O(1) | Perfect 100% match |
| 2 | **Prefix Match** | Trie | Prefix trie | O(k) | "starts with" queries |
| 3 | **Near-Exact** | Levenshtein ≤2 | BK-tree | O(log n) | Typos, minor edits |
| 4 | **Whole Embedding** | Qwen3-Embedding-0.6B | FAISS HNSW | O(log n) | Semantic whole text |
| 5 | **Line Embedding** | Qwen3-Embedding-0.6B | FAISS HNSW | O(log n) | Semantic per line |
| 6 | **Sentence Embedding** | Qwen3-Embedding-0.6B | FAISS HNSW | O(log n) | Semantic per sentence |
| 7 | **Word N-gram** | Jaccard | Inverted index | O(k) | Word overlap |
| 8 | **Char N-gram** | Jaccard | Inverted index | O(k) | Char overlap |
| 9 | **Length Filter** | Bucket | Bucket index | O(1) | Pre-filter by length |
| 10 | **Fuzzy Ratio** | RapidFuzz | Prepared list | O(n*) | Aggressive fuzzy |
| 11 | **Fuzzy Partial** | RapidFuzz partial | Prepared list | O(n*) | Substring fuzzy |
| 12 | **Token Sort** | RapidFuzz token_sort | Prepared list | O(n*) | Word order invariant |

*O(n*) = O(n) but with heavy pre-filtering by length/ngram to reduce n

### 3.3 Analysis Implementation

```python
# server/tools/ldm/tm_analyzer.py

class TMAnalyzer:
    """
    Performs ALL 12 analysis types on TM entries.
    Uses Qwen/Qwen3-Embedding-0.6B (1024-dim) for semantic embeddings.
    """

    def __init__(self):
        self.model = None  # Qwen3-Embedding-0.6B (lazy load)

    # ═══════════════════════════════════════════════════════════════
    # GRANULARITY ANALYSIS
    # ═══════════════════════════════════════════════════════════════

    def analyze_whole(self, text: str) -> np.ndarray:
        """
        Level 1: Whole text → single embedding
        """
        normalized = self.normalize(text)
        return self.model.encode([normalized])[0]

    def analyze_lines(self, text: str) -> List[Tuple[str, np.ndarray]]:
        """
        Level 2: Split by \n → embedding per line
        """
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        if not lines:
            return []

        embeddings = self.model.encode(lines)
        return list(zip(lines, embeddings))

    def analyze_sentences(self, text: str) -> List[Tuple[str, np.ndarray]]:
        """
        Level 3: Split by sentence boundaries → embedding per sentence
        """
        # Korean sentence splitting (. ! ? 。)
        import re
        sentences = re.split(r'(?<=[.!?。])\s+', text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            return []

        embeddings = self.model.encode(sentences)
        return list(zip(sentences, embeddings))

    def analyze_words(self, text: str) -> List[str]:
        """
        Level 4: Tokenize → word list
        """
        # Korean tokenization (simple space + morpheme boundaries)
        words = text.split()
        return [w.strip() for w in words if w.strip()]

    def analyze_char_ngrams(self, text: str, n: int = 3) -> Set[str]:
        """
        Level 5: Character n-grams
        """
        text = self.normalize(text)
        if len(text) < n:
            return {text}
        return {text[i:i+n] for i in range(len(text) - n + 1)}

    def analyze_word_ngrams(self, text: str, n: int = 2) -> Set[str]:
        """
        Level 5b: Word n-grams (bigrams)
        """
        words = self.analyze_words(text)
        if len(words) < n:
            return {' '.join(words)}
        return {' '.join(words[i:i+n]) for i in range(len(words) - n + 1)}

    # ═══════════════════════════════════════════════════════════════
    # HASH & EXACT ANALYSIS
    # ═══════════════════════════════════════════════════════════════

    def compute_hash(self, text: str) -> str:
        """
        SHA256 hash for exact matching
        """
        normalized = self.normalize(text)
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()

    def compute_prefix_keys(self, text: str, max_length: int = 20) -> List[str]:
        """
        Generate prefix keys for trie indexing
        """
        normalized = self.normalize(text)
        return [normalized[:i] for i in range(1, min(len(normalized), max_length) + 1)]

    # ═══════════════════════════════════════════════════════════════
    # LENGTH ANALYSIS
    # ═══════════════════════════════════════════════════════════════

    def compute_length_bucket(self, text: str, bucket_size: int = 10) -> int:
        """
        Length bucket for pre-filtering
        """
        return len(self.normalize(text)) // bucket_size

    def get_length_range(self, text: str, tolerance: float = 0.3) -> Tuple[int, int]:
        """
        Get acceptable length range for fuzzy matching
        """
        length = len(self.normalize(text))
        min_len = int(length * (1 - tolerance))
        max_len = int(length * (1 + tolerance))
        return (min_len, max_len)

    # ═══════════════════════════════════════════════════════════════
    # NORMALIZATION
    # ═══════════════════════════════════════════════════════════════

    def normalize(self, text: str) -> str:
        """
        Normalize text for consistent matching
        """
        import unicodedata
        # NFD normalize, lowercase, strip, collapse whitespace
        text = unicodedata.normalize('NFC', text)
        text = text.strip()
        text = ' '.join(text.split())  # Collapse whitespace
        return text

    # ═══════════════════════════════════════════════════════════════
    # FULL ANALYSIS (ALL TYPES)
    # ═══════════════════════════════════════════════════════════════

    def full_analysis(self, text: str) -> dict:
        """
        Perform ALL analysis types on text.
        Returns comprehensive analysis result.
        """
        normalized = self.normalize(text)

        return {
            # Hash
            'hash': self.compute_hash(text),

            # Length
            'length': len(normalized),
            'length_bucket': self.compute_length_bucket(text),

            # Embeddings (computed separately in batch)
            'needs_whole_embedding': True,
            'needs_line_embedding': '\n' in text,
            'needs_sentence_embedding': any(c in text for c in '.!?。'),

            # N-grams
            'char_trigrams': self.analyze_char_ngrams(text, 3),
            'word_bigrams': self.analyze_word_ngrams(text, 2),

            # Words
            'words': self.analyze_words(text),
            'word_count': len(self.analyze_words(text)),

            # Prefix keys
            'prefix_keys': self.compute_prefix_keys(text),

            # Lines/Sentences (if applicable)
            'lines': [l.strip() for l in text.split('\n') if l.strip()],
            'line_count': len([l for l in text.split('\n') if l.strip()]),
        }
```

---

## 4. Index Types (10 Indexes)

### 4.1 Index Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              INDEX TYPES                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  EMBEDDING INDEXES (FAISS)                                                   │
│  ─────────────────────────                                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                          │
│  │ WHOLE HNSW  │  │  LINE HNSW  │  │  SENT HNSW  │                          │
│  │  142K vecs  │  │  85K vecs   │  │  95K vecs   │                          │
│  │  1024 dim   │  │  1024 dim   │  │  1024 dim   │  (Qwen)                  │
│  │  M=32       │  │  M=32       │  │  M=32       │                          │
│  │  ef=200     │  │  ef=200     │  │  ef=200     │                          │
│  └─────────────┘  └─────────────┘  └─────────────┘                          │
│                                                                              │
│  LOOKUP INDEXES                                                              │
│  ──────────────                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ EXACT HASH  │  │PREFIX TRIE  │  │ CHAR NGRAM  │  │ WORD NGRAM  │         │
│  │  O(1)       │  │  O(k)       │  │  O(k)       │  │  O(k)       │         │
│  │  142K keys  │  │  142K keys  │  │  450K grams │  │  280K grams │         │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘         │
│                                                                              │
│  FILTER INDEXES                                                              │
│  ──────────────                                                              │
│  ┌─────────────┐  ┌─────────────┐                                           │
│  │LENGTH BUCKET│  │  BK-TREE    │                                           │
│  │  O(1)       │  │  O(log n)   │                                           │
│  │  50 buckets │  │  142K nodes │                                           │
│  └─────────────┘  └─────────────┘                                           │
│                                                                              │
│  FUZZY INDEXES                                                               │
│  ─────────────                                                               │
│  ┌─────────────┐  ┌─────────────┐                                           │
│  │  RAPIDFUZZ  │  │QUERY CACHE  │                                           │
│  │  Prepared   │  │  LRU 10K    │                                           │
│  │  142K texts │  │  Hot queries│                                           │
│  └─────────────┘  └─────────────┘                                           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Index Implementation

```python
# server/tools/ldm/tm_indexer.py

class TMIndexBuilder:
    """
    Builds and manages ALL index types for TM.
    """

    def __init__(self, tm_path: Path):
        self.tm_path = tm_path
        self.analyzer = TMAnalyzer()

    # ═══════════════════════════════════════════════════════════════
    # FAISS INDEXES (Embeddings)
    # ═══════════════════════════════════════════════════════════════

    def build_faiss_index(
        self,
        embeddings: np.ndarray,
        index_path: Path,
        index_type: str = 'hnsw'
    ) -> faiss.Index:
        """
        Build FAISS HNSW index for fast ANN search.

        HNSW Parameters (optimized for 100K-500K entries):
        - M=32: Number of connections per layer (higher = more accurate, more memory)
        - efConstruction=400: Build-time search depth (higher = better index quality)
        - efSearch=500: Query-time search depth (higher = more accurate)

        Memory: ~2KB per vector (1024 dim Qwen) + ~200 bytes HNSW overhead
        Speed: ~1ms for k=10 search on 100K vectors
        """
        dim = embeddings.shape[1]
        n_vectors = embeddings.shape[0]

        logger.info(f"Building FAISS {index_type} index", {
            "vectors": n_vectors,
            "dimensions": dim
        })

        # Normalize for cosine similarity (FAISS uses inner product)
        embeddings_normalized = embeddings.copy()
        faiss.normalize_L2(embeddings_normalized)

        if index_type == 'hnsw':
            # HNSW - best for our use case (fast, accurate, updatable)
            # P20: Unified params - M=32, efC=400, efS=500, METRIC_INNER_PRODUCT
            index = faiss.IndexHNSWFlat(dim, 32, faiss.METRIC_INNER_PRODUCT)
            index.hnsw.efConstruction = 400
            index.hnsw.efSearch = 500
        elif index_type == 'ivf':
            # IVF - alternative for very large TMs (1M+)
            nlist = int(np.sqrt(n_vectors))
            quantizer = faiss.IndexFlatIP(dim)
            index = faiss.IndexIVFFlat(quantizer, dim, nlist)
            index.train(embeddings_normalized)
        else:
            # Flat - exact search (for small TMs or verification)
            index = faiss.IndexFlatIP(dim)

        index.add(embeddings_normalized)

        # Save index
        index_path.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(index, str(index_path))

        logger.success(f"FAISS index built", {
            "path": str(index_path),
            "vectors": n_vectors,
            "size_mb": index_path.stat().st_size / 1024 / 1024
        })

        return index

    # ═══════════════════════════════════════════════════════════════
    # EXACT HASH INDEX
    # ═══════════════════════════════════════════════════════════════

    def build_hash_index(self, entries: List[dict], index_path: Path) -> dict:
        """
        Build SHA256 hash → entry_id mapping for O(1) exact lookup.

        Structure:
        {
            "abc123...": {"entry_id": 1, "target": "translation"},
            "def456...": {"entry_id": 2, "target": "another"},
            ...
        }
        """
        logger.info(f"Building hash index", {"entries": len(entries)})

        hash_index = {}
        for entry in entries:
            source_hash = self.analyzer.compute_hash(entry['source'])
            hash_index[source_hash] = {
                'entry_id': entry['id'],
                'source': entry['source'],
                'target': entry['target']
            }

        # Save
        index_path.parent.mkdir(parents=True, exist_ok=True)
        with open(index_path, 'wb') as f:
            pickle.dump(hash_index, f)

        logger.success(f"Hash index built", {"keys": len(hash_index)})
        return hash_index

    # ═══════════════════════════════════════════════════════════════
    # PREFIX TRIE INDEX
    # ═══════════════════════════════════════════════════════════════

    def build_prefix_trie(self, entries: List[dict], index_path: Path) -> 'Trie':
        """
        Build prefix trie for "starts with" queries.

        Example:
        - "게임" matches "게임을 시작하세요", "게임이 로딩됩니다", etc.
        """
        from pygtrie import CharTrie

        logger.info(f"Building prefix trie", {"entries": len(entries)})

        trie = CharTrie()
        for entry in entries:
            normalized = self.analyzer.normalize(entry['source'])
            # Store entry_id at each prefix endpoint
            if normalized in trie:
                trie[normalized].append(entry['id'])
            else:
                trie[normalized] = [entry['id']]

        # Save
        index_path.parent.mkdir(parents=True, exist_ok=True)
        with open(index_path, 'wb') as f:
            pickle.dump(trie, f)

        logger.success(f"Prefix trie built", {"keys": len(list(trie.keys()))})
        return trie

    # ═══════════════════════════════════════════════════════════════
    # N-GRAM INVERTED INDEX
    # ═══════════════════════════════════════════════════════════════

    def build_ngram_index(
        self,
        entries: List[dict],
        index_path: Path,
        ngram_type: str = 'char',
        n: int = 3
    ) -> dict:
        """
        Build inverted index: ngram → [entry_ids]

        Used for fast candidate filtering before expensive similarity.

        Example (char trigrams):
        {
            "게임을": [1, 5, 23, 456],
            "임을시": [1, 23],
            "을시작": [1, 5, 23],
            ...
        }
        """
        logger.info(f"Building {ngram_type} {n}-gram index", {"entries": len(entries)})

        inverted_index = defaultdict(set)

        for entry in entries:
            if ngram_type == 'char':
                ngrams = self.analyzer.analyze_char_ngrams(entry['source'], n)
            else:  # word
                ngrams = self.analyzer.analyze_word_ngrams(entry['source'], n)

            for ngram in ngrams:
                inverted_index[ngram].add(entry['id'])

        # Convert sets to lists for serialization
        inverted_index = {k: list(v) for k, v in inverted_index.items()}

        # Save
        index_path.parent.mkdir(parents=True, exist_ok=True)
        with open(index_path, 'wb') as f:
            pickle.dump(inverted_index, f)

        logger.success(f"N-gram index built", {
            "ngrams": len(inverted_index),
            "type": ngram_type,
            "n": n
        })
        return inverted_index

    # ═══════════════════════════════════════════════════════════════
    # LENGTH BUCKET INDEX
    # ═══════════════════════════════════════════════════════════════

    def build_length_index(
        self,
        entries: List[dict],
        index_path: Path,
        bucket_size: int = 10
    ) -> dict:
        """
        Build length bucket → [entry_ids] for pre-filtering.

        Strings of similar length are more likely to match.
        Filter to ±30% length before expensive comparisons.

        Example:
        {
            0: [entry_ids with length 0-9],
            1: [entry_ids with length 10-19],
            2: [entry_ids with length 20-29],
            ...
        }
        """
        logger.info(f"Building length bucket index", {"entries": len(entries)})

        length_index = defaultdict(list)

        for entry in entries:
            bucket = self.analyzer.compute_length_bucket(entry['source'], bucket_size)
            length_index[bucket].append({
                'entry_id': entry['id'],
                'length': len(self.analyzer.normalize(entry['source']))
            })

        # Convert to regular dict
        length_index = dict(length_index)

        # Save
        index_path.parent.mkdir(parents=True, exist_ok=True)
        with open(index_path, 'wb') as f:
            pickle.dump(length_index, f)

        logger.success(f"Length index built", {"buckets": len(length_index)})
        return length_index

    # ═══════════════════════════════════════════════════════════════
    # BK-TREE (Edit Distance)
    # ═══════════════════════════════════════════════════════════════

    def build_bktree(self, entries: List[dict], index_path: Path) -> 'BKTree':
        """
        Build BK-tree for efficient edit distance queries.

        BK-tree allows O(log n) search for strings within edit distance k.
        Perfect for finding near-exact matches (typos, minor edits).
        """
        from pybktree import BKTree
        from Levenshtein import distance as levenshtein_distance

        logger.info(f"Building BK-tree", {"entries": len(entries)})

        # Build tree with (normalized_source, entry_id) tuples
        items = [
            (self.analyzer.normalize(e['source']), e['id'])
            for e in entries
        ]

        def distance_func(a, b):
            return levenshtein_distance(a[0], b[0])

        tree = BKTree(distance_func, items)

        # Save
        index_path.parent.mkdir(parents=True, exist_ok=True)
        with open(index_path, 'wb') as f:
            pickle.dump(tree, f)

        logger.success(f"BK-tree built", {"nodes": len(items)})
        return tree

    # ═══════════════════════════════════════════════════════════════
    # RAPIDFUZZ PREPARED INDEX
    # ═══════════════════════════════════════════════════════════════

    def build_rapidfuzz_index(self, entries: List[dict], index_path: Path) -> dict:
        """
        Prepare data structure optimized for RapidFuzz queries.

        Pre-processes:
        - Normalized sources
        - Length-sorted for quick filtering
        - Lowercase versions for case-insensitive
        """
        logger.info(f"Building RapidFuzz index", {"entries": len(entries)})

        # Prepare entries sorted by length
        prepared = []
        for entry in entries:
            normalized = self.analyzer.normalize(entry['source'])
            prepared.append({
                'entry_id': entry['id'],
                'source': entry['source'],
                'source_normalized': normalized,
                'source_lower': normalized.lower(),
                'target': entry['target'],
                'length': len(normalized)
            })

        # Sort by length for efficient filtering
        prepared.sort(key=lambda x: x['length'])

        # Build length lookup for range queries
        length_to_start_idx = {}
        for i, item in enumerate(prepared):
            if item['length'] not in length_to_start_idx:
                length_to_start_idx[item['length']] = i

        rapidfuzz_data = {
            'entries': prepared,
            'length_to_start_idx': length_to_start_idx,
            'total': len(prepared)
        }

        # Save
        index_path.parent.mkdir(parents=True, exist_ok=True)
        with open(index_path, 'wb') as f:
            pickle.dump(rapidfuzz_data, f)

        logger.success(f"RapidFuzz index built", {"entries": len(prepared)})
        return rapidfuzz_data

    # ═══════════════════════════════════════════════════════════════
    # BUILD ALL INDEXES
    # ═══════════════════════════════════════════════════════════════

    def build_all_indexes(
        self,
        entries: List[dict],
        embeddings_whole: np.ndarray,
        embeddings_line: np.ndarray,
        embeddings_sentence: np.ndarray,
        progress_callback: callable = None
    ) -> dict:
        """
        Build ALL indexes for complete TM system.

        Order: Fast indexes first, then expensive ones.
        """
        results = {}
        total_steps = 10
        current_step = 0

        def report_progress(name):
            nonlocal current_step
            current_step += 1
            if progress_callback:
                progress_callback(current_step, total_steps, name)
            logger.info(f"Building index {current_step}/{total_steps}: {name}")

        # 1. Hash index (fastest to build, most useful)
        report_progress("exact_hash")
        results['exact_hash'] = self.build_hash_index(
            entries, self.tm_path / 'lookup' / 'exact_hash.pkl'
        )

        # 2. Length buckets (fast, used for filtering)
        report_progress("length_buckets")
        results['length_buckets'] = self.build_length_index(
            entries, self.tm_path / 'lookup' / 'length_buckets.pkl'
        )

        # 3. Prefix trie
        report_progress("prefix_trie")
        results['prefix_trie'] = self.build_prefix_trie(
            entries, self.tm_path / 'lookup' / 'prefix_trie.pkl'
        )

        # 4. Character n-gram index
        report_progress("ngram_char")
        results['ngram_char'] = self.build_ngram_index(
            entries, self.tm_path / 'lookup' / 'ngram_char.pkl', 'char', 3
        )

        # 5. Word n-gram index
        report_progress("ngram_word")
        results['ngram_word'] = self.build_ngram_index(
            entries, self.tm_path / 'lookup' / 'ngram_word.pkl', 'word', 2
        )

        # 6. BK-tree (edit distance)
        report_progress("bktree")
        results['bktree'] = self.build_bktree(
            entries, self.tm_path / 'fuzzy' / 'bktree.pkl'
        )

        # 7. RapidFuzz prepared
        report_progress("rapidfuzz")
        results['rapidfuzz'] = self.build_rapidfuzz_index(
            entries, self.tm_path / 'fuzzy' / 'rapidfuzz_prepared.pkl'
        )

        # 8. FAISS whole embeddings
        report_progress("faiss_whole")
        results['faiss_whole'] = self.build_faiss_index(
            embeddings_whole, self.tm_path / 'faiss' / 'whole.hnsw'
        )

        # 9. FAISS line embeddings
        report_progress("faiss_line")
        results['faiss_line'] = self.build_faiss_index(
            embeddings_line, self.tm_path / 'faiss' / 'line.hnsw'
        )

        # 10. FAISS sentence embeddings
        report_progress("faiss_sentence")
        results['faiss_sentence'] = self.build_faiss_index(
            embeddings_sentence, self.tm_path / 'faiss' / 'sentence.hnsw'
        )

        return results
```

---

## 5. Update Logic

### 5.1 Change Detection

```python
# server/tools/ldm/tm_updater.py

class TMUpdater:
    """
    Handles incremental TM updates.

    NEVER rebuilds everything. Only updates what changed.
    """

    def __init__(self, tm_path: Path):
        self.tm_path = tm_path
        self.analyzer = TMAnalyzer()
        self.indexer = TMIndexBuilder(tm_path)

    def detect_changes(
        self,
        new_entries: List[dict],
        existing_hash_index: dict
    ) -> dict:
        """
        Compare new entries with existing TM.

        Returns:
        {
            "new": [entries not in existing TM],
            "modified": [entries with same source but different target],
            "unchanged": [entries identical in both],
            "deleted": [entry_ids in existing but not in new]
        }
        """
        changes = {
            'new': [],
            'modified': [],
            'unchanged': [],
            'deleted_ids': set(e['entry_id'] for e in existing_hash_index.values())
        }

        for entry in new_entries:
            source_hash = self.analyzer.compute_hash(entry['source'])

            if source_hash not in existing_hash_index:
                # New entry
                changes['new'].append(entry)
            else:
                existing = existing_hash_index[source_hash]
                changes['deleted_ids'].discard(existing['entry_id'])

                if existing['target'] != entry['target']:
                    # Modified (same source, different target)
                    changes['modified'].append({
                        **entry,
                        'existing_entry_id': existing['entry_id']
                    })
                else:
                    # Unchanged
                    changes['unchanged'].append(entry)

        changes['deleted_ids'] = list(changes['deleted_ids'])

        logger.info("Change detection complete", {
            "new": len(changes['new']),
            "modified": len(changes['modified']),
            "unchanged": len(changes['unchanged']),
            "deleted": len(changes['deleted_ids'])
        })

        return changes

    # ═══════════════════════════════════════════════════════════════
    # INCREMENTAL UPDATE - EMBEDDINGS
    # ═══════════════════════════════════════════════════════════════

    def update_embeddings(
        self,
        changes: dict,
        embedding_type: str,  # 'whole', 'line', 'sentence'
        progress_callback: callable = None
    ):
        """
        Incrementally update embeddings.

        Like KR Similar lines 258-283:
        1. Load existing embeddings + mapping
        2. Generate embeddings ONLY for new/modified entries
        3. Replace modified entries in-place
        4. Append new entries
        5. Mark deleted entries (or compact if many deleted)
        6. Save updated embeddings
        7. Rebuild FAISS index
        """
        embeddings_dir = self.tm_path / 'embeddings' / embedding_type
        embeddings_path = embeddings_dir / 'embeddings.npy'
        mapping_path = embeddings_dir / 'mapping.pkl'
        dict_path = embeddings_dir / 'dict.pkl'

        # Load existing
        embeddings = np.load(embeddings_path)
        with open(mapping_path, 'rb') as f:
            idx_to_entry = pickle.load(f)
        with open(dict_path, 'rb') as f:
            source_to_target = pickle.load(f)

        entry_to_idx = {v: k for k, v in idx_to_entry.items()}

        # === Process MODIFIED entries ===
        if changes['modified']:
            modified_sources = [e['source'] for e in changes['modified']]
            modified_embeddings = self.analyzer.model.encode(modified_sources)

            for i, entry in enumerate(changes['modified']):
                existing_idx = entry_to_idx[entry['existing_entry_id']]
                # Replace in-place
                embeddings[existing_idx] = modified_embeddings[i]
                # Update dictionary
                source_to_target[entry['source']] = entry['target']

            logger.info(f"Updated {len(changes['modified'])} modified embeddings")

        # === Process NEW entries ===
        if changes['new']:
            new_sources = [e['source'] for e in changes['new']]
            new_embeddings = self.analyzer.model.encode(new_sources)

            # Append to embeddings array
            embeddings = np.vstack([embeddings, new_embeddings])

            # Update mappings
            next_idx = len(idx_to_entry)
            for i, entry in enumerate(changes['new']):
                idx_to_entry[next_idx + i] = entry['id']
                source_to_target[entry['source']] = entry['target']

            logger.info(f"Added {len(changes['new'])} new embeddings")

        # === Handle DELETED entries ===
        if changes['deleted_ids']:
            # Mark as deleted (don't compact unless > 20% deleted)
            deleted_ratio = len(changes['deleted_ids']) / len(idx_to_entry)

            if deleted_ratio > 0.2:
                # Compact: rebuild without deleted entries
                logger.info(f"Compacting embeddings (deleted ratio: {deleted_ratio:.2%})")
                valid_mask = np.array([
                    idx_to_entry[i] not in changes['deleted_ids']
                    for i in range(len(embeddings))
                ])
                embeddings = embeddings[valid_mask]
                # Rebuild mappings...
            else:
                # Just mark as deleted (lazy deletion)
                for entry_id in changes['deleted_ids']:
                    if entry_id in entry_to_idx:
                        idx = entry_to_idx[entry_id]
                        idx_to_entry[idx] = None  # Mark as deleted

        # === Save updated embeddings ===
        np.save(embeddings_path, embeddings)
        with open(mapping_path, 'wb') as f:
            pickle.dump(idx_to_entry, f)
        with open(dict_path, 'wb') as f:
            pickle.dump(source_to_target, f)

        # === Rebuild FAISS index ===
        faiss_path = self.tm_path / 'faiss' / f'{embedding_type}.hnsw'
        self.indexer.build_faiss_index(embeddings, faiss_path)

        logger.success(f"{embedding_type} embeddings updated", {
            "total": len(embeddings),
            "modified": len(changes['modified']),
            "new": len(changes['new']),
            "deleted": len(changes['deleted_ids'])
        })

    # ═══════════════════════════════════════════════════════════════
    # INCREMENTAL UPDATE - LOOKUP INDEXES
    # ═══════════════════════════════════════════════════════════════

    def update_hash_index(self, changes: dict):
        """Update hash index incrementally."""
        hash_path = self.tm_path / 'lookup' / 'exact_hash.pkl'

        with open(hash_path, 'rb') as f:
            hash_index = pickle.load(f)

        # Remove deleted
        hashes_to_remove = []
        for h, data in hash_index.items():
            if data['entry_id'] in changes['deleted_ids']:
                hashes_to_remove.append(h)
        for h in hashes_to_remove:
            del hash_index[h]

        # Update modified
        for entry in changes['modified']:
            source_hash = self.analyzer.compute_hash(entry['source'])
            hash_index[source_hash] = {
                'entry_id': entry['existing_entry_id'],
                'source': entry['source'],
                'target': entry['target']
            }

        # Add new
        for entry in changes['new']:
            source_hash = self.analyzer.compute_hash(entry['source'])
            hash_index[source_hash] = {
                'entry_id': entry['id'],
                'source': entry['source'],
                'target': entry['target']
            }

        with open(hash_path, 'wb') as f:
            pickle.dump(hash_index, f)

        logger.info("Hash index updated")

    def update_ngram_index(self, changes: dict, ngram_type: str = 'char'):
        """Update n-gram inverted index incrementally."""
        index_path = self.tm_path / 'lookup' / f'ngram_{ngram_type}.pkl'
        n = 3 if ngram_type == 'char' else 2

        with open(index_path, 'rb') as f:
            inverted_index = pickle.load(f)

        # Convert lists back to sets for efficient updates
        inverted_index = {k: set(v) for k, v in inverted_index.items()}

        # Remove deleted entries from all ngrams
        for entry_id in changes['deleted_ids']:
            for ngram_set in inverted_index.values():
                ngram_set.discard(entry_id)

        # Add new entries
        for entry in changes['new'] + changes['modified']:
            entry_id = entry.get('existing_entry_id', entry['id'])
            if ngram_type == 'char':
                ngrams = self.analyzer.analyze_char_ngrams(entry['source'], n)
            else:
                ngrams = self.analyzer.analyze_word_ngrams(entry['source'], n)

            for ngram in ngrams:
                if ngram not in inverted_index:
                    inverted_index[ngram] = set()
                inverted_index[ngram].add(entry_id)

        # Convert back to lists and save
        inverted_index = {k: list(v) for k, v in inverted_index.items()}
        with open(index_path, 'wb') as f:
            pickle.dump(inverted_index, f)

        logger.info(f"{ngram_type} n-gram index updated")

    # ═══════════════════════════════════════════════════════════════
    # FULL INCREMENTAL UPDATE
    # ═══════════════════════════════════════════════════════════════

    def incremental_update(
        self,
        new_entries: List[dict],
        progress_callback: callable = None
    ) -> dict:
        """
        Perform full incremental update of ALL indexes.
        """
        # Load existing hash index for change detection
        with open(self.tm_path / 'lookup' / 'exact_hash.pkl', 'rb') as f:
            existing_hash = pickle.load(f)

        # Detect changes
        changes = self.detect_changes(new_entries, existing_hash)

        if not changes['new'] and not changes['modified'] and not changes['deleted_ids']:
            logger.info("No changes detected, skipping update")
            return {"status": "no_changes"}

        # Update each index type
        steps = [
            ("hash_index", lambda: self.update_hash_index(changes)),
            ("ngram_char", lambda: self.update_ngram_index(changes, 'char')),
            ("ngram_word", lambda: self.update_ngram_index(changes, 'word')),
            ("embeddings_whole", lambda: self.update_embeddings(changes, 'whole')),
            ("embeddings_line", lambda: self.update_embeddings(changes, 'line')),
            ("embeddings_sentence", lambda: self.update_embeddings(changes, 'sentence')),
            # Trie, BK-tree, RapidFuzz - rebuild if significant changes
        ]

        for i, (name, update_fn) in enumerate(steps):
            if progress_callback:
                progress_callback(i + 1, len(steps), name)
            update_fn()

        # Update metadata version
        self._bump_version()

        return {
            "status": "updated",
            "changes": {
                "new": len(changes['new']),
                "modified": len(changes['modified']),
                "deleted": len(changes['deleted_ids'])
            }
        }
```

---

## 6. Search Cascade

### 6.1 9-Tier Cascade

```python
# server/tools/ldm/tm_search.py

class TMCascadeSearch:
    """
    9-tier cascade search with optimal performance.

    Each tier is progressively slower but catches more matches.
    Early termination when good match found.
    """

    # Thresholds
    TIERS = {
        1: {'name': 'exact', 'threshold': 1.00, 'max_time_ms': 1},
        2: {'name': 'prefix', 'threshold': 0.98, 'max_time_ms': 2},
        3: {'name': 'near_exact', 'threshold': 0.95, 'max_time_ms': 5},
        4: {'name': 'embedding_whole', 'threshold': 0.85, 'max_time_ms': 10},
        5: {'name': 'embedding_line', 'threshold': 0.80, 'max_time_ms': 10},
        6: {'name': 'embedding_sentence', 'threshold': 0.75, 'max_time_ms': 10},
        7: {'name': 'ngram_jaccard', 'threshold': 0.60, 'max_time_ms': 15},
        8: {'name': 'bktree_edit', 'threshold': 0.50, 'max_time_ms': 20},
        9: {'name': 'rapidfuzz', 'threshold': 0.40, 'max_time_ms': 30},
    }

    # Context boost
    CONTEXT_BOOST = {
        'same_project': 0.05,
        'same_file_type': 0.03,
        'same_domain': 0.02
    }

    def __init__(self, tm_path: Path):
        self.tm_path = tm_path
        self.indexes = {}  # Lazy loaded
        self.cache = LRUCache(maxsize=10000)

    def search(
        self,
        query: str,
        context: dict = None,
        max_results: int = 10,
        min_threshold: float = 0.40,
        stop_at_tier: int = None,
        return_all_tiers: bool = False
    ) -> dict:
        """
        Perform cascade search.

        Parameters:
        - query: Source text to match
        - context: {"project_id": 1, "file_type": "xml", "domain": "ui"}
        - max_results: Max results to return
        - min_threshold: Minimum similarity to include
        - stop_at_tier: Stop cascade at this tier (for debugging)
        - return_all_tiers: Return results from all tiers (for analysis)

        Returns:
        {
            "best_match": {...},
            "suggestions": [...],
            "tier_results": {...},  # if return_all_tiers
            "search_time_ms": 25,
            "tier_reached": 4
        }
        """
        import time
        start_time = time.time()

        # Check cache
        cache_key = f"{query}:{context}"
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            cached['from_cache'] = True
            return cached

        # Normalize query
        query_normalized = self.analyzer.normalize(query)
        query_hash = self.analyzer.compute_hash(query)

        results = []
        tier_results = {} if return_all_tiers else None
        tier_reached = 0

        # Execute tiers in order
        for tier_num, tier_config in self.TIERS.items():
            if stop_at_tier and tier_num > stop_at_tier:
                break

            tier_start = time.time()
            tier_matches = self._execute_tier(
                tier_num, query_normalized, query_hash, max_results
            )
            tier_time = (time.time() - tier_start) * 1000

            if tier_matches:
                tier_reached = tier_num

                # Apply context boost
                if context:
                    tier_matches = self._apply_context_boost(tier_matches, context)

                # Filter by threshold
                tier_matches = [
                    m for m in tier_matches
                    if m['similarity'] >= min_threshold
                ]

                results.extend(tier_matches)

                if return_all_tiers:
                    tier_results[tier_config['name']] = {
                        'matches': tier_matches,
                        'time_ms': tier_time
                    }

                # Early termination if we have a great match
                if tier_matches and tier_matches[0]['similarity'] >= 0.95:
                    break

        # Sort by similarity and deduplicate
        results = self._deduplicate_results(results)
        results = sorted(results, key=lambda x: -x['similarity'])[:max_results]

        total_time = (time.time() - start_time) * 1000

        response = {
            'best_match': results[0] if results else None,
            'suggestions': results,
            'search_time_ms': total_time,
            'tier_reached': tier_reached
        }

        if return_all_tiers:
            response['tier_results'] = tier_results

        # Cache result
        self.cache[cache_key] = response

        return response

    def _execute_tier(
        self,
        tier_num: int,
        query: str,
        query_hash: str,
        max_results: int
    ) -> List[dict]:
        """Execute specific tier search."""

        if tier_num == 1:  # Exact hash
            return self._tier_exact(query_hash)

        elif tier_num == 2:  # Prefix
            return self._tier_prefix(query, max_results)

        elif tier_num == 3:  # Near-exact (BK-tree, distance ≤ 2)
            return self._tier_near_exact(query, max_results)

        elif tier_num == 4:  # Embedding whole
            return self._tier_embedding(query, 'whole', max_results)

        elif tier_num == 5:  # Embedding line
            return self._tier_embedding(query, 'line', max_results)

        elif tier_num == 6:  # Embedding sentence
            return self._tier_embedding(query, 'sentence', max_results)

        elif tier_num == 7:  # N-gram Jaccard
            return self._tier_ngram(query, max_results)

        elif tier_num == 8:  # BK-tree edit distance
            return self._tier_bktree(query, max_results)

        elif tier_num == 9:  # RapidFuzz
            return self._tier_rapidfuzz(query, max_results)

        return []

    # === TIER IMPLEMENTATIONS ===

    def _tier_exact(self, query_hash: str) -> List[dict]:
        """Tier 1: O(1) exact hash lookup"""
        hash_index = self._get_index('exact_hash')
        if query_hash in hash_index:
            match = hash_index[query_hash]
            return [{
                'source': match['source'],
                'target': match['target'],
                'similarity': 1.0,
                'tier': 1,
                'match_type': 'exact'
            }]
        return []

    def _tier_prefix(self, query: str, max_results: int) -> List[dict]:
        """Tier 2: Prefix trie lookup"""
        trie = self._get_index('prefix_trie')
        # Find all entries that start with query
        try:
            matches = list(trie.items(prefix=query))[:max_results]
            return [
                {
                    'source': source,
                    'target': self._get_target(entry_ids[0]),
                    'similarity': len(query) / len(source) if len(source) > 0 else 0,
                    'tier': 2,
                    'match_type': 'prefix'
                }
                for source, entry_ids in matches
            ]
        except KeyError:
            return []

    def _tier_embedding(
        self,
        query: str,
        embedding_type: str,
        max_results: int
    ) -> List[dict]:
        """Tier 4/5/6: FAISS semantic search"""
        # Encode query
        query_embedding = self.analyzer.model.encode([query])
        faiss.normalize_L2(query_embedding)

        # Search FAISS index
        index = self._get_index(f'faiss_{embedding_type}')
        distances, indices = index.search(query_embedding, max_results)

        # Load mapping
        mapping = self._get_index(f'mapping_{embedding_type}')
        source_dict = self._get_index(f'dict_{embedding_type}')
        sources = list(source_dict.keys())

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < len(sources) and dist > 0:
                source = sources[idx]
                results.append({
                    'source': source,
                    'target': source_dict[source],
                    'similarity': float(dist),
                    'tier': {'whole': 4, 'line': 5, 'sentence': 6}[embedding_type],
                    'match_type': f'embedding_{embedding_type}'
                })

        return results

    def _tier_ngram(self, query: str, max_results: int) -> List[dict]:
        """Tier 7: N-gram Jaccard similarity"""
        query_trigrams = self.analyzer.analyze_char_ngrams(query, 3)
        ngram_index = self._get_index('ngram_char')

        # Find candidate entries by trigram overlap
        candidate_counts = defaultdict(int)
        for trigram in query_trigrams:
            if trigram in ngram_index:
                for entry_id in ngram_index[trigram]:
                    candidate_counts[entry_id] += 1

        # Score top candidates
        results = []
        for entry_id, overlap_count in sorted(
            candidate_counts.items(),
            key=lambda x: -x[1]
        )[:max_results * 2]:
            entry = self._get_entry(entry_id)
            entry_trigrams = self.analyzer.analyze_char_ngrams(entry['source'], 3)

            # Jaccard similarity
            intersection = len(query_trigrams & entry_trigrams)
            union = len(query_trigrams | entry_trigrams)
            jaccard = intersection / union if union > 0 else 0

            if jaccard > 0.3:
                results.append({
                    'source': entry['source'],
                    'target': entry['target'],
                    'similarity': jaccard,
                    'tier': 7,
                    'match_type': 'ngram_jaccard'
                })

        return sorted(results, key=lambda x: -x['similarity'])[:max_results]

    def _tier_rapidfuzz(self, query: str, max_results: int) -> List[dict]:
        """Tier 9: RapidFuzz with pre-filtering"""
        from rapidfuzz import fuzz, process

        rapidfuzz_data = self._get_index('rapidfuzz')
        entries = rapidfuzz_data['entries']

        # Pre-filter by length (±30%)
        query_len = len(query)
        min_len = int(query_len * 0.7)
        max_len = int(query_len * 1.3)

        candidates = [
            e for e in entries
            if min_len <= e['length'] <= max_len
        ]

        # Score with RapidFuzz
        results = []
        for entry in candidates[:1000]:  # Limit candidates
            score = fuzz.ratio(query, entry['source_normalized']) / 100
            if score > 0.4:
                results.append({
                    'source': entry['source'],
                    'target': entry['target'],
                    'similarity': score,
                    'tier': 9,
                    'match_type': 'rapidfuzz'
                })

        return sorted(results, key=lambda x: -x['similarity'])[:max_results]
```

---

## 7. Implementation Plan

### 7.1 Task Breakdown

```
Phase 7.1: Database Models (4 tasks)
├── 7.1.1 LDMTranslationMemory model
├── 7.1.2 LDMTMEntry model
├── 7.1.3 LDMActiveTM model
└── 7.1.4 Database migration

Phase 7.2: TM Upload & Parsing (6 tasks)
├── 7.2.1 TMManager class
├── 7.2.2 TMX parser
├── 7.2.3 Excel parser
├── 7.2.4 TXT parser
├── 7.2.5 Upload API endpoint
└── 7.2.6 List/Delete APIs

Phase 7.3: Analysis Engine (6 tasks)
├── 7.3.1 TMAnalyzer class
├── 7.3.2 Whole text analysis
├── 7.3.3 Line analysis
├── 7.3.4 Sentence analysis
├── 7.3.5 N-gram analysis (char + word)
└── 7.3.6 Hash/prefix analysis

Phase 7.4: Index Builder (10 tasks)
├── 7.4.1 TMIndexBuilder class
├── 7.4.2 FAISS HNSW whole index
├── 7.4.3 FAISS HNSW line index
├── 7.4.4 FAISS HNSW sentence index
├── 7.4.5 Exact hash index
├── 7.4.6 Prefix trie index
├── 7.4.7 Char n-gram inverted index
├── 7.4.8 Word n-gram inverted index
├── 7.4.9 Length bucket index
└── 7.4.10 BK-tree + RapidFuzz indexes

Phase 7.5: Incremental Updater (8 tasks)
├── 7.5.1 TMUpdater class
├── 7.5.2 Change detection algorithm
├── 7.5.3 Incremental embedding update (whole)
├── 7.5.4 Incremental embedding update (line)
├── 7.5.5 Incremental embedding update (sentence)
├── 7.5.6 Incremental lookup index update
├── 7.5.7 Version management
└── 7.5.8 Update API endpoint

Phase 7.6: Cascade Search (10 tasks)
├── 7.6.1 TMCascadeSearch class
├── 7.6.2 Tier 1: Exact hash
├── 7.6.3 Tier 2: Prefix match
├── 7.6.4 Tier 3: Near-exact (BK-tree)
├── 7.6.5 Tier 4: Embedding whole
├── 7.6.6 Tier 5: Embedding line
├── 7.6.7 Tier 6: Embedding sentence
├── 7.6.8 Tier 7: N-gram Jaccard
├── 7.6.9 Tier 8-9: Fuzzy (BK-tree + RapidFuzz)
└── 7.6.10 Context boost + caching

Phase 7.7: Search API (4 tasks)
├── 7.7.1 GET /api/ldm/tm/suggest
├── 7.7.2 GET /api/ldm/tm/{id}/status
├── 7.7.3 POST /api/ldm/tm/{id}/activate
└── 7.7.4 Query result formatting

Phase 7.8: Frontend TM UI (6 tasks)
├── 7.8.1 TMManager.svelte
├── 7.8.2 TMUploadModal.svelte
├── 7.8.3 TM selector in settings
├── 7.8.4 Advanced TM panel in edit modal
├── 7.8.5 Tier indicator badges
└── 7.8.6 Apply suggestion UI

═══════════════════════════════════════
TOTAL: 54 tasks for Phase 7
═══════════════════════════════════════
```

### 7.2 Estimated Build Times

| Index Type | 100K entries | 500K entries | 1M entries |
|------------|-------------|--------------|------------|
| Exact Hash | 2s | 10s | 20s |
| Prefix Trie | 5s | 25s | 50s |
| Char N-gram | 10s | 50s | 100s |
| Word N-gram | 8s | 40s | 80s |
| Length Buckets | 1s | 5s | 10s |
| BK-tree | 30s | 150s | 300s |
| RapidFuzz | 5s | 25s | 50s |
| FAISS Whole | 120s | 600s | 1200s |
| FAISS Line | 80s | 400s | 800s |
| FAISS Sentence | 90s | 450s | 900s |
| **TOTAL** | **~6 min** | **~30 min** | **~60 min** |

### 7.3 Expected Search Performance

| Tier | Index Type | 100K TM | 500K TM | Typical Match |
|------|-----------|---------|---------|---------------|
| 1 | Exact Hash | <1ms | <1ms | 100% |
| 2 | Prefix | 1ms | 2ms | 98-99% |
| 3 | Near-exact | 2ms | 5ms | 95-98% |
| 4 | FAISS Whole | 3ms | 8ms | 80-95% |
| 5 | FAISS Line | 3ms | 8ms | 70-90% |
| 6 | FAISS Sent | 3ms | 8ms | 60-85% |
| 7 | N-gram | 5ms | 15ms | 50-70% |
| 8 | BK-tree | 10ms | 30ms | 40-60% |
| 9 | RapidFuzz | 20ms | 50ms | 30-50% |

**Typical cascade (stops at Tier 4):** <15ms

---

## Summary

This architecture provides:

1. **MAXIMUM ANALYSIS** - 12 analysis types covering every granularity
2. **MAXIMUM INDEXING** - 10 specialized indexes, each optimized for its use case
3. **OPTIMAL PERFORMANCE** - O(1) to O(log n) lookups, cascade stops early
4. **INCREMENTAL UPDATES** - Never rebuild everything, only update what changed
5. **VERSION CONTROL** - Rollback capability for all indexes

Ready to implement?
