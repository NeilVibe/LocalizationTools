# Session Context - Last Working State

**Updated:** 2025-12-13 ~09:00 KST | **By:** Claude

---

## Session Summary: TM/QA Core Implementation Complete

### What Was Done

| Task | Status | Notes |
|------|--------|-------|
| **Universal Newline Normalizer** | ✅ IMPLEMENTED | `normalize_newlines_universal()` handles TEXT + XML |
| **5-Tier Cascade Search** | ✅ IMPLEMENTED | `TMSearcher` class with all 5 tiers |
| **PKL vs DB Sync** | ✅ IMPLEMENTED | `TMSyncManager` with INSERT/UPDATE/DELETE detection |
| **NPC (Neil's Probabilistic Check)** | ✅ IMPLEMENTED | `npc_check()` method on TMSearcher |
| **Test Data Generator** | ✅ IMPLEMENTED | `TMTestDataGenerator` for TEXT + XML mock data |
| **Unit Tests** | ✅ 82 PASSING | Normalizer (29) + Search (20) + Sync (17) + NPC (16) |

---

## TM/QA Architecture (FINALIZED)

### SYSTEM 1: TM Matching (WebTranslatorNew Style)
```
Purpose: SUGGESTIONS in Edit Modal

QWEN Embeddings + FAISS (HNSW) + PKL
├── 5-Tier Cascade:
│   1. Perfect whole match → Show if exists
│   2. Whole embedding match → Top 3 ≥92%
│   3. Perfect line match → Show if exists
│   4. Line embedding match → Top 3 ≥92%
│   5. N-gram fallback → Top 3 ≥92%
├── Single Threshold: 92% (simplified from DUAL)
└── TM Update: Incremental (KR Similar logic)
```

### NPC: Neil's Probabilistic Check
```
Purpose: VERIFY translation consistency

1. TM panel shows Source matches ≥92%
2. User clicks [NPC] button
3. Embed user's Target (1 call)
4. Cosine similarity vs TM Targets
5. Any match ≥80%? → ✅ Consistent
   No matches? → ⚠️ Potential issue

Fast: 1 embedding + N cosine calcs (N < 10)
No FAISS needed - direct similarity
```

### SYSTEM 2: QA Checks (QuickSearch Style)
```
Purpose: Find ERRORS/INCONSISTENCIES

Word Check: Aho-Corasick automaton
├── Scans FULL TEXT in one pass - O(text length)
├── Finds ALL glossary terms simultaneously
├── No word splitting needed
└── Glossary rules: ≤26 chars, no sentences

Line Check: Dict lookup
├── normalize_newlines_universal() → all to \n
├── split('\n') → array of lines
├── Lookup each line in dict
└── One line? Still works (array of 1)
```

### Universal Newline Normalization
```python
def normalize_newlines_universal(text):
    """Handle ALL newline formats"""
    text = text.replace('\\n', '\n')      # Escaped
    text = text.replace('<br/>', '\n')    # XML unescaped
    text = text.replace('<br />', '\n')   # XML with space
    text = text.replace('&lt;br/&gt;', '\n')    # XML escaped
    text = text.replace('&lt;br /&gt;', '\n')   # XML escaped + space
    return text
```

### TM Update Architecture
```
DB = CENTRAL (always up-to-date)
├── Re-upload TM → INSERT/UPDATE/DELETE instantly
├── Ctrl+S confirm → INSERT or UPDATE (if TM active)
└── Multi-user: everyone updates same DB

FAISS = LOCAL (synced on demand)
├── User clicks [Synchronize TM]
├── PKL vs DB comparison (pd.merge on Source)
├── INSERT/UPDATE → QWEN embed (expensive)
├── DELETE → skip (not copied)
├── UNCHANGED → copy existing embedding (fast)
└── Rebuild FAISS, Aho-Corasick, Line Dict

Source embeddings only (WHOLE + SPLIT)
Target embeddings = on-demand for NPC (not synced)
```

### Key Decisions
- DB stores canonical `\n` format
- Pre-index everything on TM upload → Instant lookups
- Smart TM Update: Only re-embed new/changed entries
- pd.merge logic: INSERT (new) / UPDATE (changed) / DELETE (removed)
- Spell/Grammar check SKIPPED (no MIT multi-lang library)

---

## Files Modified/Created This Session

| File | Changes |
|------|---------|
| `server/tools/ldm/tm_indexer.py` | Added TMSearcher, TMSyncManager, NPC methods, 1700+ lines |
| `server/tools/ldm/__init__.py` | Updated exports for TM classes |
| `tests/helpers/tm_test_data.py` | NEW: Mock TM data generator (TEXT + XML) |
| `tests/unit/test_tm_normalizer.py` | NEW: 29 tests for newline normalization |
| `tests/unit/test_tm_search.py` | NEW: 20 tests for 5-Tier Cascade search |
| `tests/unit/test_tm_sync.py` | NEW: 17 tests for PKL vs DB sync |
| `tests/unit/test_npc.py` | NEW: 16 tests for NPC verification |
| `docs/wip/SESSION_CONTEXT.md` | This file - session summary |

---

## Open Issues

| ID | Priority | Status | Notes |
|----|----------|--------|-------|
| *None* | - | - | All known bugs fixed |

---

## Next Priorities

### P25 Phase 10: TM/QA Implementation

**Backend (DONE):**
- [x] Universal newline normalizer (`normalize_newlines_universal()`)
- [x] QWEN embedding generation (Source)
- [x] FAISS index (HNSW)
- [x] 5-Tier Cascade + Single Threshold (92%)
- [x] TM Update logic (incremental via pd.merge)
- [x] NPC (Neil's Probabilistic Check) - 80% threshold

**Frontend Integration (TODO):**
- [ ] TM Results in Edit Modal
- [ ] [NPC] button in Edit Modal
- [ ] Display: ✅ Consistent / ⚠️ Potential issue
- [ ] API endpoints for TM search/sync/NPC

**SYSTEM 2 (QA - Error Detection) - TODO:**
- [ ] Glossary extraction (≤26 chars, no sentences)
- [ ] Aho-Corasick automaton (pyahocorasick) for Word Check
- [ ] Dict lookup for Line Check
- [ ] QA panel in Edit Modal

### P17 LDM Remaining
- Custom Excel picker (column selection)
- Custom XML picker (attribute selection)

---

## Quick Reference

| Need | Location |
|------|----------|
| Current task | [Roadmap.md](../../Roadmap.md) |
| TM/QA Architecture | [P25_LDM_UX_OVERHAUL.md](P25_LDM_UX_OVERHAUL.md) Section 9 |
| Known bugs | [ISSUES_TO_FIX.md](ISSUES_TO_FIX.md) |
| Future ideas | [IDEAS_FUTURE.md](IDEAS_FUTURE.md) |
| CDP Testing | [docs/testing/CDP_TESTING_GUIDE.md](../testing/CDP_TESTING_GUIDE.md) |

---

*For full project status, see [Roadmap.md](../../Roadmap.md)*
