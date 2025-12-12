# Session Context - Last Working State

**Updated:** 2025-12-13 ~05:30 KST | **By:** Claude

---

## Session Summary: TM/QA + NPC Finalized

### What Was Done

| Task | Status | Notes |
|------|--------|-------|
| **TM/QA Architecture Design** | ✅ Finalized | Two separate systems fully documented |
| **NPC (Neil's Probabilistic Check)** | ✅ Approved | Simple Target verification via cosine sim |
| **Single Threshold (92%)** | ✅ Decided | Simplified from DUAL threshold |
| **TM Display Rules** | ✅ Defined | Perfect = show if exists, Embedding = top 3 |
| **TM DB Sync Architecture** | ✅ Designed | DB=central, FAISS=local, 3 triggers |
| **pd.merge INSERT/UPDATE/DELETE** | ✅ Documented | Full diff logic for TM updates |
| **Roadmap.md Phase 10** | ✅ Updated | SYSTEM 1 + NPC + SYSTEM 2 |
| **P25_LDM_UX_OVERHAUL.md** | ✅ Updated | Full TM update flow + NPC + tasks |
| **IDEAS_FUTURE.md** | ✅ Updated | NPC moved from parked → approved |

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

## Files Modified This Session

| File | Changes |
|------|---------|
| `Roadmap.md` | Phase 10 updated with SYSTEM 1 + SYSTEM 2 |
| `docs/wip/P25_LDM_UX_OVERHAUL.md` | Complete TM/QA architecture + pseudocode |
| `docs/wip/IDEAS_FUTURE.md` | Created - parked Probabilistic QA idea |
| `docs/wip/SESSION_CONTEXT.md` | This file - session summary |

---

## Open Issues

| ID | Priority | Status | Notes |
|----|----------|--------|-------|
| *None* | - | - | All known bugs fixed |

---

## Next Priorities

### P25 Phase 10: TM/QA Implementation (READY TO BUILD)

**Shared:**
- [ ] Universal newline normalizer (`normalize_newlines_universal()`)

**SYSTEM 1 (TM Matching - Suggestions):**
- [ ] QWEN embedding generation (Source AND Target)
- [ ] FAISS index (HNSW)
- [ ] 5-Tier Cascade + Single Threshold (92%)
- [ ] Display rules: Perfect = show if exists, Embedding = top 3
- [ ] TM Update logic (incremental via pd.merge)
- [ ] TM Results in Edit Modal

**NPC (Neil's Probabilistic Check):**
- [ ] [NPC] button in Edit Modal
- [ ] Embed user's Target (1 call)
- [ ] Cosine similarity vs TM Targets (threshold: 80%)
- [ ] Display: ✅ Consistent / ⚠️ Potential issue

**SYSTEM 2 (QA - Error Detection):**
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
