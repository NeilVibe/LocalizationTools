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
- ✅ Newline display as ↵ symbol in grid
- ✅ Full content display (no truncation)
- ✅ Cell hover highlight + TM pre-fetch on click

PRIORITY 2: Phase 7.1-7.2 - TM Database + Upload (10 tasks) ← NEXT
────────────────────────────────────────────────────────────
Why next: Need TM data before building indexes
- 7.1.1-7.1.4 Database models (LDMTranslationMemory, LDMTMEntry, LDMActiveTM)
- 7.2.1-7.2.6 TM Upload + parsers (TMX, Excel, TXT)

PRIORITY 3: Phase 7.3 - Index Building (6 tasks)
────────────────────────────────────────────────────────────
Why next: Need indexes for fast search
- 7.3.1-7.3.6 whole_text_lookup, line_lookup, FAISS indexes

PRIORITY 4: Phase 7.4 - Cascade Search (8 tasks)
────────────────────────────────────────────────────────────
Why next: Core TM functionality
- 7.4.1-7.4.8 5-Tier cascade + dual threshold search

PRIORITY 5: Phase 7.5 - TM Search API + Frontend (8 tasks)
────────────────────────────────────────────────────────────
Why next: Wire backend to frontend
- 7.5.1-7.5.8 APIs + TMManager.svelte + TMUploadModal.svelte

PRIORITY 6: Phase 5.5 - Glossary (3 tasks)
────────────────────────────────────────────────────────────
Optional but useful
- 5.5.1-5.5.3 Glossary backend + API + panel

PRIORITY 7: Phase 8 - Nice View (12 tasks)
────────────────────────────────────────────────────────────
Polish and patterns
- 8.1-8.12 Pattern rendering, special display modes

═══════════════════════════════════════════════════════════════════════════════
```

---

## Progress Overview

```
Phase 1-4: Foundation + Grid    [X] 58/58 tasks  ✅ COMPLETE
Phase 5: Basic CAT              [▓▓▓] 7/10 tasks  (TM panel done)
Phase 6: UI Polish              [▓▓▓▓] 7/16 tasks ✅ 6.0 + 6.1 COMPLETE
Phase 7: Full TM System         [ ] 0/32 tasks   (5-Tier Cascade)
Phase 8: Nice View              [ ] 0/12 tasks   (Pattern rendering)
─────────────────────────────────────────
TOTAL                           72/128 tasks (56%)
```

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

### 7.1 Database Models (4 tasks)

- [ ] **7.1.1** Create `LDMTranslationMemory` model
  ```python
  class LDMTranslationMemory(Base):
      __tablename__ = "ldm_translation_memories"

      id = Column(Integer, primary_key=True)
      name = Column(String(255), nullable=False)
      description = Column(Text)
      owner_id = Column(Integer, ForeignKey("users.id"))

      # Stats
      entry_count = Column(Integer, default=0)
      whole_pairs = Column(Integer, default=0)
      line_pairs = Column(Integer, default=0)

      # Status
      status = Column(String(50), default="pending")  # pending, indexing, ready, error
      storage_path = Column(String(500))

      created_at = Column(DateTime, default=datetime.utcnow)
      updated_at = Column(DateTime, onupdate=datetime.utcnow)
  ```

- [ ] **7.1.2** Create `LDMTMEntry` model
  ```python
  class LDMTMEntry(Base):
      __tablename__ = "ldm_tm_entries"

      id = Column(Integer, primary_key=True)
      tm_id = Column(Integer, ForeignKey("ldm_translation_memories.id"))
      source_text = Column(Text, nullable=False)
      target_text = Column(Text)
      source_hash = Column(String(64), index=True)  # For exact lookup
      created_at = Column(DateTime, default=datetime.utcnow)
  ```

- [ ] **7.1.3** Create `LDMActiveTM` model (user's selected TM per file)

- [ ] **7.1.4** Database migration script

---

### 7.2 TM Upload & Parsing (6 tasks)

- [ ] **7.2.1** Create `server/tools/ldm/tm_manager.py`
  ```python
  class TMManager:
      def upload_tm(self, file, name: str) -> dict
      def build_indexes(self, tm_id: int, progress_callback=None) -> dict
      def load_tm(self, tm_id: int) -> bool
      def delete_tm(self, tm_id: int) -> bool
  ```

- [ ] **7.2.2** TMX parser
  ```python
  def parse_tmx(file_path: str) -> List[dict]:
      """Parse TMX <tu> elements → source/target pairs"""
  ```

- [ ] **7.2.3** Excel parser (source_col, target_col configurable)

- [ ] **7.2.4** TXT parser (tab-delimited)

- [ ] **7.2.5** API: `POST /api/ldm/tm/upload`
  ```
  Request: multipart/form-data
  - file: TM file
  - name: TM name
  - source_column: int (for Excel/TXT)
  - target_column: int (for Excel/TXT)

  Response:
  {"tm_id": 1, "status": "indexing", "entry_count": 50000}
  ```

- [ ] **7.2.6** APIs: `GET /list`, `DELETE /{id}`, `POST /{id}/activate`

---

### 7.3 Index Building (6 tasks)

- [ ] **7.3.1** Create `server/tools/ldm/tm_indexer.py`

- [ ] **7.3.2** Build **whole_text_lookup** (hash index for Tier 1)
  ```python
  def build_whole_text_lookup(entries: List[dict]) -> dict:
      lookup = {}
      for entry in entries:
          source = normalize_newlines(entry['source'])
          lookup[source] = {'target': entry['target'], 'entry_id': entry['id']}
          lookup[source.strip()] = ...  # whitespace variant
      return lookup
  ```

- [ ] **7.3.3** Build **line_lookup** (hash index for Tier 3)
  ```python
  def build_line_lookup(entries: List[dict]) -> dict:
      lookup = {}
      for entry in entries:
          source_lines = entry['source'].split('\n')
          target_lines = entry['target'].split('\n') if entry['target'] else []
          for i, line in enumerate(source_lines):
              if line.strip():
                  lookup[normalize(line)] = {
                      'target_line': target_lines[i] if i < len(target_lines) else '',
                      'entry_id': entry['id'],
                      'line_num': i
                  }
      return lookup
  ```

- [ ] **7.3.4** Generate **whole embeddings** + build **FAISS HNSW** (Tier 2)
  ```python
  def build_whole_faiss(entries: List[dict], model) -> faiss.Index:
      texts = [normalize(e['source']) for e in entries]
      embeddings = model.encode(texts, batch_size=64)
      faiss.normalize_L2(embeddings)

      index = faiss.IndexHNSWFlat(768, 32)  # 768 dim, M=32
      index.hnsw.efConstruction = 400
      index.hnsw.efSearch = 500
      index.add(embeddings)
      return index
  ```

- [ ] **7.3.5** Generate **line embeddings** + build **line FAISS** (Tier 4)

- [ ] **7.3.6** Save all indexes to disk
  ```
  server/data/ldm_tm/{tm_id}/
  ├── metadata.json
  ├── entries.pkl
  ├── hash/
  │   ├── whole_lookup.pkl
  │   └── line_lookup.pkl
  ├── embeddings/
  │   ├── whole.npy
  │   ├── whole_mapping.pkl    # idx → entry_id
  │   ├── line.npy
  │   └── line_mapping.pkl     # idx → (entry_id, line_num)
  └── faiss/
      ├── whole.index
      └── line.index
  ```

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

### 7.5 Incremental Update (4 tasks)

> Reference: KR Similar `embeddings.py` lines 232-309

- [ ] **7.5.1** Create `server/tools/ldm/tm_updater.py`

- [ ] **7.5.2** Change detection
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

- [ ] **7.5.3** Incremental embedding update
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

- [ ] **7.5.4** API: `POST /api/ldm/tm/{id}/update`

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

*Last updated: 2025-12-09 - Aligned with WebTranslatorNew 5-tier cascade + dual threshold*
