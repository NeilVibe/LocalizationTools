# P17: LocaNext LDM - Detailed Task List

**Started:** 2025-12-08
**Status:** IN PROGRESS
**Last Updated:** 2025-12-09

> Task breakdown for LDM with 5-Tier Cascade TM System (WebTranslatorNew architecture)

---

## 🎯 PRIORITY ORDER (Coding Sequence)

```
RECOMMENDED CODING ORDER:
═══════════════════════════════════════════════════════════════════════════════

PRIORITY 1: Phase 6.1 - Cell Display (4 tasks) ✅ COMPLETE
────────────────────────────────────────────────────────────
- ✅ Dynamic row heights (content-based sizing)
- ✅ Newline auto-escape (actual line breaks in grid, not ↵ symbol)
- ✅ Full content display (no truncation)
- ✅ Cell hover highlight + TM pre-fetch on click

PRIORITY 2: Phase 7.1 - TM Database Models (4 tasks) ✅ COMPLETE
────────────────────────────────────────────────────────────
- ✅ LDMTranslationMemory (TM container with stats, status)
- ✅ LDMTMEntry (source/target pairs with hash index)
- ✅ LDMActiveTM (TM-to-project/file links with priority)
- ✅ LDMBackup (backup tracking for disaster recovery)

PRIORITY 3: Phase 7.2 - TM Upload + Parsers (6 tasks) ✅ COMPLETE
────────────────────────────────────────────────────────────
- ✅ 7.2.1 TMManager class (upload, build, load, delete)
- ✅ 7.2.3-7.2.4 Parsers (Excel, TXT via existing handlers)
- ✅ 7.2.5-7.2.6 Upload API + CRUD endpoints (8 new routes)

PRIORITY 4: Phase 7.3 - Index Building (7 tasks) ✅ COMPLETE
────────────────────────────────────────────────────────────
- ✅ 7.3.1 TMIndexer class (tm_indexer.py)
- ✅ 7.3.2-7.3.3 Hash indexes (whole_text_lookup, line_lookup)
- ✅ 7.3.4-7.3.5 FAISS HNSW indexes (whole, line embeddings)
- ✅ 7.3.6 Disk storage structure
- ✅ 7.3.7 API endpoints (build-indexes, indexes status)

PRIORITY 5: Phase 7.4 - Cascade Search (8 tasks)
────────────────────────────────────────────────────────────
Why next: Core TM functionality
- 7.4.1-7.4.8 5-Tier cascade + dual threshold search

PRIORITY 6: Phase 7.5 - TM Search API + Frontend (8 tasks)
────────────────────────────────────────────────────────────
Why next: Wire backend to frontend
- 7.5.1-7.5.8 APIs + TMManager.svelte + TMUploadModal.svelte

PRIORITY 7: Phase 7.6 - Adaptive TM (4 tasks) ★ NEW
────────────────────────────────────────────────────────────
Powerful: TM grows as users work (auto-save edits)
- 7.6.1-7.6.4 Toggle + hook + incremental index + UI indicator

PRIORITY 8: Phase 5.5 - Glossary (3 tasks)
────────────────────────────────────────────────────────────
Optional but useful
- 5.5.1-5.5.3 Glossary backend + API + panel

PRIORITY 9: Phase 8 - Nice View (12 tasks)
────────────────────────────────────────────────────────────
Polish and patterns
- 8.1-8.12 Pattern rendering, special display modes

═══════════════════════════════════════════════════════════════════════════════
```

---

## 🔧 TECHNICAL DECISIONS (2025-12-09)

### Embedding Model Unification

**Current Models in Codebase:**
| Location | Model | Size | License |
|----------|-------|------|---------|
| models/kr-sbert/ | snunlp/KR-SBERT-V40K-klueNLI-augSTS | **447 MB** | MIT |
| WebTranslatorNew | Qwen/Qwen3-Embedding-0.6B | **1.21 GB** | Apache 2.0 |

**Decision Options:**
```
Option A: Keep Both (Status Quo)
├── KR-SBERT for XLSTransfer, KR Similar (Korean-only)
├── Qwen for LDM TM system (multilingual)
└── Total: ~1.65 GB

Option B: Unify to Qwen ★ RECOMMENDED
├── Single model for ALL tools
├── Total: 1.21 GB
├── Benefits:
│   ├── Multilingual (100+ languages)
│   ├── Better KR↔EN cross-lingual matching
│   ├── WebTranslatorNew pattern already proven
│   └── Apache 2.0 (commercial OK)
└── Migration: Update embeddings.py in each tool
```

**Pattern from WebTranslatorNew:**
```python
# EMBEDDINGS.md - proven pattern
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('Qwen/Qwen3-Embedding-0.6B')
embeddings = model.encode(texts, batch_size=64)

# FAISS HNSW index
index = faiss.IndexHNSWFlat(dimension, 32, faiss.METRIC_INNER_PRODUCT)
index.hnsw.efConstruction = 400
index.hnsw.efSearch = 500
```

### Gitea LFS Bundling (Zero-Download Option)

**New Capability (via Gitea):**
- GitHub: 1GB LFS limit (can't bundle 1.2GB model)
- Gitea: **NO storage restrictions** ✅

**Option: Bundle Model in Build**
```
LocaNext-Setup.exe (~300MB installer)
├── downloads Qwen model on first run (current)
└── OR bundles model directly (~1.5GB installer, zero user download)
```

**Benefits of Bundling:**
- ✅ Zero-download user experience
- ✅ Works offline immediately
- ✅ No network dependency after install
- ⚠️ Larger installer size (~1.5GB vs 300MB)

**Decision: Pending** - User to confirm preference

---

## Progress Overview

```
Phase 1-4: Foundation + Grid    [X] 58/58 tasks  ✅ COMPLETE
Phase 5: Basic CAT              [▓▓▓] 7/10 tasks  (TM panel done)
Phase 6: UI Polish              [▓▓▓▓] 7/16 tasks ✅ 6.0 + 6.1 COMPLETE
Phase 7: Full TM System         [▓▓▓▓▓▓▓▓] 22/44 tasks (DB + TMManager + API + INDEXER COMPLETE!)
Phase 8: Nice View              [ ] 0/12 tasks   (Pattern rendering)
─────────────────────────────────────────
TOTAL                           94/140 tasks (67%)

NEW FEATURE: File Re-Upload with Incremental Update
├── 7.5.1-7.5.4: LDM file update (diff-based, 95% faster for typical updates)
└── 7.5.5-7.5.8: TM update (hash-based, preserves history)
```

---

## Database Safeguards

### Backup Strategy (via LDMBackup table)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        DATABASE BACKUP SAFEGUARDS                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  AUTOMATIC BACKUPS:                                                          │
│  ├── pre_delete    → Before deleting project/file/TM                        │
│  ├── pre_import    → Before large TM import (>10k entries)                  │
│  └── scheduled     → Daily/weekly full backup (configurable)                │
│                                                                              │
│  BACKUP TYPES:                                                               │
│  ├── full          → All LDM tables (disaster recovery)                     │
│  ├── project       → Single project + files + rows                          │
│  ├── file          → Single file + rows + edit history                      │
│  └── tm            → Single TM + entries                                    │
│                                                                              │
│  RETENTION:                                                                  │
│  ├── pre_delete    → 30 days (recoverable)                                  │
│  ├── pre_import    → 7 days (rollback window)                               │
│  └── scheduled     → Keep last 5 (auto-cleanup)                             │
│                                                                              │
│  RESTORE:                                                                    │
│  └── Admin API: POST /api/ldm/backup/{id}/restore                           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Data Integrity Features

- **Edit History**: Every cell change tracked in `LDMEditHistory`
- **Row Locking**: `LDMActiveSession.editing_row` prevents conflicts
- **WebSocket Sync**: Real-time broadcast prevents stale data
- **Hash Verification**: TM entries use SHA256 for deduplication

---

## Phase 1-4: COMPLETE

*Foundation, File Explorer, Real-time Sync, Virtual Scroll - 58 tasks done*

---

## Phase 5: Basic CAT Features

### 5.1-5.4: COMPLETE ✅
- [x] Basic TM (Jaccard similarity) - will be replaced by Phase 7
- [x] TM panel in edit modal
- [x] Keyboard shortcuts (Ctrl+Enter, Tab, Escape)

### 5.5: Glossary (TODO)
- [ ] **5.5.1** Create `glossary.py`
- [ ] **5.5.2** Glossary check API
- [ ] **5.5.3** GlossaryPanel.svelte

---

## Phase 6: UI Polish

### 6.0: COMPLETE ✅
- [x] Hover transitions
- [x] Row selection

### 6.1: Cell Text Display ✅ COMPLETE
- [x] **6.1.1** Dynamic row heights (content-based sizing)
- [x] **6.1.2** Newline display logic (grid: `↵` symbol, modal: actual breaks)
- [x] **6.1.3** Full content display (no truncation)
- [x] **6.1.4** Cell hover highlight + single-click TM pre-fetch

### 6.2: Later
- [ ] Version history, exports, permissions, etc.

---

## Phase 7: Full TM System (5-Tier Cascade + Dual Threshold)

> **Architecture:** WebTranslatorNew 5-tier cascade + dual threshold
> **Documentation:** [LDM_TEXT_SEARCH.md](../tools/LDM_TEXT_SEARCH.md)

### 7.0 Architecture Summary

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    5-TIER CASCADE + DUAL THRESHOLD                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  TIER 1: Perfect Whole Match    Hash O(1)         → 100% (stops cascade)    │
│  TIER 2: Whole Text Embedding   FAISS HNSW        → stops if ≥0.92          │
│  TIER 3: Perfect Line Match     Hash per line     → exact line matches      │
│  TIER 4: Line-by-Line Embedding FAISS per line    → semantic line matches   │
│  TIER 5: Word N-Gram Embedding  1,2,3-grams→FAISS → partial phrase matches  │
│                                                                              │
│  DUAL THRESHOLD:                                                             │
│  ├── cascade_threshold = 0.92  → PRIMARY matches (high confidence)          │
│  └── context_threshold = 0.49  → CONTEXT match (single best reference)      │
│                                                                              │
│  INDEXES:                                                                    │
│  ├── whole_text_lookup.pkl     (hash for exact whole match)                 │
│  ├── line_lookup.pkl           (hash for exact line match)                  │
│  ├── whole.index               (FAISS HNSW for whole embeddings)            │
│  └── line.index                (FAISS HNSW for line embeddings)             │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### 7.1 Database Models (4 tasks) ✅ COMPLETE

- [x] **7.1.1** Create `LDMTranslationMemory` model ✅
  - Added to `server/database/models.py` (lines 707-752)
  - Includes: name, description, owner, source/target lang, stats, status, storage_path
  - Status flow: pending → indexing → ready → error

- [x] **7.1.2** Create `LDMTMEntry` model ✅
  - Added to `server/database/models.py` (lines 755-790)
  - Includes: source_text, target_text, source_hash (SHA256 for O(1) lookup)
  - Composite index on (tm_id, source_hash) for fast TM-specific lookups

- [x] **7.1.3** Create `LDMActiveTM` model ✅
  - Added to `server/database/models.py` (lines 793-828)
  - Links TM to project OR file with priority ordering
  - Unique constraint prevents duplicate TM links

- [x] **7.1.4** Create `LDMBackup` model ✅ (BONUS - Safeguard)
  - Added to `server/database/models.py` (lines 835-872)
  - Tracks: backup_type, backup_path, status, trigger, expires_at
  - Supports: full, project, file, TM backups
  - Triggers: scheduled, pre_delete, manual, pre_import

- [x] **7.1.5** Create `BackupService` class ✅ (SMART BACKUP)
  - Added to `server/tools/ldm/backup_service.py`
  - **GZIP Compression**: 70-90% space savings
  - **Smart Expiration**:
    - pre_delete: 7 days
    - pre_import: 3 days
    - scheduled: 7 days
    - manual: 30 days
  - **Max Backups**: full=3, project=5, file=10, tm=5
  - **Auto-cleanup**: Removes expired + excess backups
  - **Restore**: Supports file/project/TM restore
  - Methods: `backup_before_delete_*()`, `restore_backup()`

- [x] **7.1.6** Database tables created (run db_setup.py) ✅

- [x] **7.1.7** Create `LDMTrash` table ✅ (TRASH BIN)
  - Soft delete for projects, folders, files, TMs
  - 30-day retention before permanent delete
  - Easy 1-click restore from UI
  - Stores full JSON snapshot for restore

- [x] **7.1.8** Create `LDMTMIndex` table ✅ (INDEX TRACKING)
  - Tracks FAISS index files per TM
  - Types: whole_faiss, line_faiss, whole_hash, line_hash
  - Status: building → ready → error
  - Stores file paths + sizes

- [x] **7.1.9** Database Optimization Utilities ✅ (P18 Integration)
  - Created `server/database/db_utils.py` with:
    - `bulk_insert()` - Generic batch insert (10x faster)
    - `bulk_insert_tm_entries()` - TM-specific with auto SHA256 hash
    - `bulk_insert_rows()` - LDM row upload optimization
    - `search_rows_fts()` - Full-text search with PostgreSQL tsvector
    - `add_fts_indexes()` - Migration script for FTS columns
    - `add_trigram_index()` - GIN trigram index for similarity
    - `chunked_query()` - Memory-safe large dataset iteration
    - `upsert_batch()` - Insert or update with conflict handling
  - WIP Document: `docs/wip/P_DB_OPTIMIZATION.md`

---

### 7.2 TM Upload & Parsing (6 tasks) ← IN PROGRESS

**PARSING STRATEGY: REUSE EXISTING HANDLERS!**
```
═══════════════════════════════════════════════════════════════════════════════

TXT FILES → REUSE: server/tools/ldm/file_handlers/txt_handler.py
├── parse_txt_file(file_content, filename)
├── Column 5 = Source (Korean)
├── Column 6 = Target (Translation)
└── Already handles encoding, normalization ✅

XML FILES → REUSE: server/tools/ldm/file_handlers/xml_handler.py
├── parse_xml_file(file_content, filename)
├── <LocStr StrOrigin="source" Str="target" />
└── Already handles XML parsing ✅

EXCEL FILES → NEW SIMPLE PARSER:
├── Column A (index 0) = Source
├── Column B (index 1) = Target
└── Use openpyxl (already in project)

TMManager wraps these parsers + adds:
├── bulk_insert_tm_entries() for fast import (20k/sec!)
├── SHA256 hash generation for exact match
└── Progress callback for UI updates

═══════════════════════════════════════════════════════════════════════════════
```

**TM Input Sources:**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           TM INPUT SOURCES                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. TXT Tab-Delimited    → REUSE txt_handler.py (col 5/6)                   │
│  2. XML LocStr           → REUSE xml_handler.py (StrOrigin/Str)             │
│  3. Excel (A/B columns)  → NEW simple parser (col 0/1)                      │
│  4. ★ ADAPTIVE TM ★     → Auto-save edits as TM entries (reactive)         │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**★ Adaptive TM Feature (NEW CONCEPT):**
```
USER EDITS CELL              ADAPTIVE TM
─────────────────            ──────────────────────────────────────
Source: "안녕하세요"    →    Option: "Auto-save to TM?" [✓]
Target: "Hello"         →    Creates TM entry automatically
                             TM grows as users work!

BENEFITS:
├── TM builds organically from real translations
├── No separate TM upload needed
├── Project-specific TM created automatically
└── Toggle per project/file (user choice)
```

- [x] **7.2.1** Create `server/tools/ldm/tm_manager.py` ✅
  - TMManager class with upload_tm(), list_tms(), get_tm(), delete_tm(), add_entry()
  - REUSES txt_handler.py for TXT parsing (Column 5=Source, Column 6=Target)
  - REUSES xml_handler.py for XML parsing (StrOrigin=Source, Str=Target)
  - NEW simple Excel parser (Column A=Source, Column B=Target)
  - Uses bulk_insert_tm_entries() for 20k+ entries/sec import
  - Includes search_exact() for O(1) hash lookup

- [ ] **7.2.2** TMX parser (deferred - use TXT/XML/Excel for now)

- [x] **7.2.3** Excel parser ✅ (in TMManager._parse_excel_for_tm)
  - Column A = source, Column B = target
  - Configurable via source_col, target_col params

- [x] **7.2.4** TXT parser ✅ (REUSES txt_handler.py)
  - Column 5 = source, Column 6 = target

- [x] **7.2.5** API: `POST /api/ldm/tm/upload` ✅ (2025-12-09)
  ```
  Request: multipart/form-data
  - file: TM file (TXT, XML, XLSX)
  - name: TM name
  - source_lang: str (default: ko)
  - target_lang: str (default: en)
  - description: str (optional)

  Response:
  {"tm_id": 1, "name": "...", "entry_count": 50000, "status": "ready", "time_seconds": 2.5, "rate_per_second": 20000}
  ```

- [x] **7.2.6** APIs: TM CRUD endpoints ✅ (2025-12-09)
  - `GET /api/ldm/tm` - List all TMs
  - `GET /api/ldm/tm/{tm_id}` - Get single TM
  - `DELETE /api/ldm/tm/{tm_id}` - Delete TM
  - `GET /api/ldm/tm/{tm_id}/search/exact` - O(1) hash lookup
  - `GET /api/ldm/tm/{tm_id}/search` - LIKE pattern search
  - `POST /api/ldm/tm/{tm_id}/entries` - Add entry (Adaptive TM)

---

### 7.3 Index Building (6 tasks) ✅ COMPLETE

- [x] **7.3.1** Create `server/tools/ldm/tm_indexer.py` ✅
  - TMIndexer class with build_indexes(), load_indexes(), delete_indexes()
  - Stores indexes in server/data/ldm_tm/{tm_id}/

- [x] **7.3.2** Build **whole_text_lookup** (hash index for Tier 1) ✅
  ```python
  def build_whole_text_lookup(entries: List[dict]) -> dict:
      lookup = {}
      for entry in entries:
          source = normalize_newlines(entry['source'])
          lookup[source] = {'target': entry['target'], 'entry_id': entry['id']}
          lookup[source.strip()] = ...  # whitespace variant
      return lookup
  ```

- [x] **7.3.3** Build **line_lookup** (hash index for Tier 3) ✅
  - Implemented in TMIndexer._build_line_lookup()
  - Maps individual lines to target translations

- [x] **7.3.4** Generate **whole embeddings** + build **FAISS HNSW** (Tier 2) ✅
  - Implemented in TMIndexer._build_whole_embeddings()
  - Uses Qwen3-Embedding-0.6B model
  - HNSW index with M=32, efConstruction=400, efSearch=500

- [x] **7.3.5** Generate **line embeddings** + build **line FAISS** (Tier 4) ✅
  - Implemented in TMIndexer._build_line_embeddings()
  - Extracts lines from multi-line texts for granular matching

- [x] **7.3.6** Save all indexes to disk ✅
  - Storage structure implemented:
  ```
  server/data/ldm_tm/{tm_id}/
  ├── metadata.json
  ├── hash/
  │   ├── whole_lookup.pkl
  │   └── line_lookup.pkl
  ├── embeddings/
  │   ├── whole.npy
  │   ├── whole_mapping.pkl
  │   ├── line.npy
  │   └── line_mapping.pkl
  └── faiss/
      ├── whole.index
      └── line.index
  ```

- [x] **7.3.7** API endpoints for index building ✅
  - `POST /api/ldm/tm/{tm_id}/build-indexes` - Build FAISS indexes
  - `GET /api/ldm/tm/{tm_id}/indexes` - Get index status

---

### 7.4 5-Tier Cascade Search (8 tasks)

- [ ] **7.4.1** Create `server/tools/ldm/tm_search.py`
  ```python
  class TMCascadeSearch:
      cascade_threshold = 0.92
      context_threshold = 0.49

      def search(self, query: str, tm_id: int, top_k: int = 5) -> dict:
          """Run 5-tier cascade, return primary + context matches"""
  ```

- [ ] **7.4.2** **Tier 1: Perfect Whole Match**
  ```python
  def _tier1_perfect_whole(self, query: str) -> List[dict]:
      """O(1) hash lookup - FASTEST"""
      normalized = normalize_newlines(query)
      if normalized in self.whole_lookup:
          match = self.whole_lookup[normalized]
          return [{
              "source": normalized,
              "target": match['target'],
              "similarity": 1.0,
              "tier": 1,
              "strategy": "perfect_whole_match"
          }]
      # Also try stripped version
      if normalized.strip() in self.whole_lookup:
          ...
      return []
  ```

- [ ] **7.4.3** **Tier 2: Whole Text Embedding**
  ```python
  def _tier2_whole_embedding(self, query: str, top_k: int = 10) -> List[dict]:
      """FAISS HNSW semantic search"""
      query_emb = self.model.encode([normalize(query)])
      faiss.normalize_L2(query_emb)
      distances, indices = self.whole_index.search(query_emb, top_k)

      results = []
      sources = list(self.whole_dict.keys())
      for dist, idx in zip(distances[0], indices[0]):
          if dist >= self.context_threshold:
              source = sources[idx]
              results.append({
                  "source": source,
                  "target": self.whole_dict[source],
                  "similarity": float(dist),
                  "tier": 2,
                  "strategy": "whole-embedding"
              })
      return results
  ```

- [ ] **7.4.4** **Tier 3: Perfect Line Match**
  ```python
  def _tier3_perfect_line(self, query: str) -> List[dict]:
      """O(1) hash lookup per line"""
      results = []
      for line in query.split('\n'):
          normalized_line = normalize(line)
          if normalized_line in self.line_lookup:
              match = self.line_lookup[normalized_line]
              results.append({
                  "source_line": normalized_line,
                  "target_line": match['target_line'],
                  "similarity": 1.0,
                  "tier": 3,
                  "strategy": "perfect_line_match",
                  "line_num": match['line_num']
              })
      return results
  ```

- [ ] **7.4.5** **Tier 4: Line-by-Line Embedding**
  ```python
  def _tier4_line_embedding(self, query: str, matched_lines: set) -> List[dict]:
      """FAISS search per unmatched line"""
      results = []
      for i, line in enumerate(query.split('\n')):
          if i in matched_lines or not line.strip():
              continue

          line_emb = self.model.encode([normalize(line)])
          faiss.normalize_L2(line_emb)
          distances, indices = self.line_index.search(line_emb, 5)

          for dist, idx in zip(distances[0], indices[0]):
              if dist >= self.context_threshold:
                  results.append({
                      "similarity": float(dist),
                      "tier": 4,
                      "strategy": "line-embedding",
                      "query_line_num": i
                  })
      return results
  ```

- [ ] **7.4.6** **Tier 5: Word N-Gram Embedding**
  ```python
  def _tier5_ngram_embedding(self, query: str) -> List[dict]:
      """1,2,3-word n-grams → embed each → FAISS search"""
      from nltk import ngrams
      from nltk.tokenize import word_tokenize

      words = word_tokenize(query)
      results = []

      for n in [1, 2, 3]:
          grams = [' '.join(g) for g in ngrams(words, n)]
          for gram in grams:
              if len(gram) < 3:  # Skip very short grams
                  continue

              gram_emb = self.model.encode([gram])
              faiss.normalize_L2(gram_emb)
              distances, indices = self.line_index.search(gram_emb, 3)

              for dist, idx in zip(distances[0], indices[0]):
                  if dist >= self.context_threshold:
                      results.append({
                          "gram": gram,
                          "similarity": float(dist),
                          "tier": 5,
                          "strategy": f"word-{n}-gram"
                      })
      return results
  ```

- [ ] **7.4.7** **Dual Threshold + Result Assembly**
  ```python
  def _apply_dual_threshold(self, all_results: List[dict]) -> dict:
      """
      Separate into PRIMARY (>=0.92) and CONTEXT (0.49-0.92)
      Return: all primary + single best context
      """
      # Deduplicate by source text
      seen = set()
      unique_results = []
      for r in all_results:
          key = r.get('source') or r.get('source_line') or r.get('gram')
          if key not in seen:
              seen.add(key)
              unique_results.append(r)

      # Split by threshold
      primary = [r for r in unique_results if r['similarity'] >= self.cascade_threshold]
      context = [r for r in unique_results
                 if self.context_threshold <= r['similarity'] < self.cascade_threshold]

      # Mark types
      for r in primary:
          r['type'] = 'primary'

      # Get single best context
      output = sorted(primary, key=lambda x: -x['similarity'])
      if context:
          best_context = max(context, key=lambda x: x['similarity'])
          best_context['type'] = 'context'
          output.append(best_context)

      return output
  ```

- [ ] **7.4.8** **API: `GET /api/ldm/tm/suggest`**
  ```
  Parameters:
  - source: str (text to search)
  - tm_id: int (which TM to use)
  - cascade_threshold: float = 0.92
  - context_threshold: float = 0.49
  - top_k: int = 5

  Response:
  {
    "suggestions": [
      {
        "source": "게임을 시작하세요",
        "target": "Start the game",
        "similarity": 0.98,
        "type": "primary",
        "tier": 2,
        "strategy": "whole-embedding"
      },
      {
        "source": "플레이를 시작하세요",
        "target": "Start playing",
        "similarity": 0.71,
        "type": "context",
        "tier": 2,
        "strategy": "whole-embedding"
      }
    ],
    "search_time_ms": 45,
    "tier_reached": 2
  }
  ```

---

### 7.5 Incremental Update (8 tasks) - FILE RE-UPLOAD OPTIMIZATION

> **Use Case:** User uploads languagedata_fr.txt, works on it, then re-uploads updated version.
> Instead of full delete + re-insert, detect changes and only update what changed.
> **Performance:** 5% changed = 95% faster than full replace!

**Strategy Documented:** `docs/wip/P_DB_OPTIMIZATION.md` → "Incremental Update Strategy"

#### 7.5.1-7.5.4: File Re-Upload (LDM Rows)

- [ ] **7.5.1** Create `server/tools/ldm/file_updater.py`
  ```python
  class FileUpdater:
      def update_file_incremental(file_id, new_rows) -> dict
      def detect_changes(file_id, new_rows) -> dict  # {inserted, updated, deleted}
      def preview_changes(file_id, new_rows) -> dict  # Show before applying
  ```

- [ ] **7.5.2** Diff detection by string_id
  - Load existing rows as {string_id: row}
  - Compare with new rows
  - Return: new, modified, deleted, unchanged counts

- [ ] **7.5.3** Batch UPDATE using PostgreSQL UPSERT
  ```sql
  INSERT INTO ldm_rows (file_id, string_id, source, target)
  VALUES (...)
  ON CONFLICT (file_id, string_id) DO UPDATE SET
    source = EXCLUDED.source,
    target = EXCLUDED.target,
    updated_at = NOW();
  ```

- [ ] **7.5.4** API: `POST /api/ldm/files/{id}/update`
  ```
  Request: multipart/form-data (new file)
  Response: {"inserted": 50, "updated": 200, "deleted": 10, "unchanged": 99740}
  ```

#### 7.5.5-7.5.8: TM Re-Upload (TM Entries)

> Reference: KR Similar `embeddings.py` lines 232-309

- [ ] **7.5.5** Create `server/tools/ldm/tm_updater.py`

- [ ] **7.5.6** Change detection using source_hash
  ```python
  def detect_changes(new_entries: List[dict], existing_lookup: dict) -> dict:
      """Compare new TM with existing, return changes"""
      new = []
      modified = []
      deleted_ids = set(e['entry_id'] for e in existing_lookup.values())

      for entry in new_entries:
          source = normalize(entry['source'])
          if source not in existing_lookup:
              new.append(entry)
          else:
              existing = existing_lookup[source]
              deleted_ids.discard(existing['entry_id'])
              if existing['target'] != entry['target']:
                  modified.append({**entry, 'existing_id': existing['entry_id']})

      return {"new": new, "modified": modified, "deleted": list(deleted_ids)}
  ```

- [ ] **7.5.7** Incremental embedding update
  ```python
  def update_embeddings(changes: dict, tm_path: Path):
      """
      Update embeddings without full rebuild:
      1. Load existing embeddings + mapping
      2. Generate embeddings ONLY for new/modified
      3. Replace modified in-place
      4. Append new
      5. Rebuild FAISS index
      """
      embeddings = np.load(tm_path / 'embeddings/whole.npy')
      # ... (like KR Similar)
  ```

- [ ] **7.5.8** API: `POST /api/ldm/tm/{id}/update`

---

### 7.6 Frontend TM UI (4 tasks)

- [ ] **7.6.1** Create `TMManager.svelte`
  ```
  ┌─ Translation Memories ─────────────────────────────────────┐
  │ [+ Upload TM]                                              │
  │                                                            │
  │ Name             Entries    Status     Actions             │
  │ ─────────────────────────────────────────────────────────  │
  │ BDO Main TM      150,000    ✅ Ready   [Active ✓] [Delete] │
  │ BDM Strings      45,000     ✅ Ready   [Activate] [Delete] │
  │ New Upload       12,000     🔄 Indexing...                 │
  └────────────────────────────────────────────────────────────┘
  ```

- [ ] **7.6.2** Create `TMUploadModal.svelte`
  - File input (TMX, Excel, TXT)
  - Name input
  - Column mapping for Excel/TXT
  - Progress bar during indexing

- [ ] **7.6.3** Update TM Panel in edit modal
  ```
  ┌─ TM Suggestions ─────────────────────────────────────────────┐
  │ Using: BDO Main TM [Change]                                  │
  │                                                              │
  │ ✅ 98% PRIMARY - Tier 2: whole-embedding                     │
  │ Source: 게임을 시작하세요                                      │
  │ Target: Start the game                         [Apply]       │
  │                                                              │
  │ ✅ 94% PRIMARY - Tier 1: perfect_whole_match                 │
  │ Source: 게임을 시작합니다                                      │
  │ Target: Starting the game                      [Apply]       │
  │                                                              │
  │ ⚠️ 71% CONTEXT - Tier 2: whole-embedding                     │
  │ Source: 플레이를 시작하세요                                    │
  │ Target: Start playing                          [Apply]       │
  └──────────────────────────────────────────────────────────────┘
  ```

- [ ] **7.6.4** TM selector in LDM header

---

## Phase 8: LocaNext Nice View

> Pattern rendering for color codes, variables, tags

### 8.1 Pattern Detection (6 tasks)
- [ ] **8.1.1** Create `patternRenderer.js`
- [ ] **8.1.2** Color code rendering (`<PAColor>text<549039Color>` → green text)
- [ ] **8.1.3** Variable rendering (`{player_name}` → pill)
- [ ] **8.1.4** Tag rendering (`<b>text</b>` → bold)
- [ ] **8.1.5** Link rendering
- [ ] **8.1.6** Newline rendering (`\n` → `↵`)

### 8.2 Nice View Toggle (6 tasks)
- [ ] **8.2.1** Add toggle to grid header
- [ ] **8.2.2** Create `NiceText.svelte` component
- [ ] **8.2.3** Apply to grid cells
- [ ] **8.2.4** Apply to edit modal (source preview)
- [ ] **8.2.5** Store preference in localStorage
- [ ] **8.2.6** CSS styling for rendered elements

---

## Priority Order

### IMMEDIATE: Phase 7 (Full TM System)
1. **7.1** Database models
2. **7.2** TM upload + parsing
3. **7.3** Index building (hash + FAISS)
4. **7.4** 5-tier cascade search with dual threshold
5. **7.6** Frontend UI

### THEN
6. **7.5** Incremental updates
7. **6.1** Cell text display

### LATER
8. **8.1-8.2** Nice View
9. **5.5** Glossary
10. **6.2** Exports, permissions

---

## Reference Documents

| Document | Location | Purpose |
|----------|----------|---------|
| **LDM Text Search** | `docs/tools/LDM_TEXT_SEARCH.md` | Full 5-tier cascade documentation |
| **WebTranslatorNew** | `RessourcesForCodingTheProject/WebTranslatorNew/` | Source architecture |
| **KR Similar** | `server/tools/kr_similar/embeddings.py` | Update logic pattern |

---

*Last updated: 2025-12-11 - Phase 7.3 Index Building COMPLETE (TMIndexer + FAISS + API)*
