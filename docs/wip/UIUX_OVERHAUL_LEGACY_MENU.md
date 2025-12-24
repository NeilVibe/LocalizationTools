# UIUX Overhaul - Legacy Apps Menu

**Status:** FUTURE (After P1-P4) | **Created:** 2025-12-25

---

## Vision

**Current:** 4 separate apps with clunky dropdown
**Future:** Single LocaNext LDM with clean "Legacy Apps" button for transition period
**Final:** Pure LocaNext (legacy menu removed when no longer needed)

---

## Current UI Problem

```
┌─────────────────────────────────────────┐
│ LocaNext                                │
├─────────────────────────────────────────┤
│ [Apps Dropdown ▼]  ← Clunky, confusing  │
│   ├── LDM                               │
│   ├── XLS Transfer                      │
│   ├── Quick Search                      │
│   └── KR Similar                        │
└─────────────────────────────────────────┘
```

**Problems:**
- LDM is buried with legacy apps
- Users don't know which app to use
- Duplicate functionality confuses users

---

## Target UI

### Phase 1: Clean Legacy Menu

```
┌─────────────────────────────────────────┐
│ LocaNext LDM                            │
├─────────────────────────────────────────┤
│ [Main LDM Interface]                    │
│                                         │
│ All features accessible directly:       │
│ - TM Management                         │
│ - Pretranslation                        │
│ - QA Checks (Auto-LQA)                  │
│ - File Operations                       │
│                                         │
├─────────────────────────────────────────┤
│ [Legacy Apps ▼] ← Small button, corner  │
│   ├── XLS Transfer (deprecated)         │
│   ├── Quick Search (deprecated)         │
│   └── KR Similar (deprecated)           │
└─────────────────────────────────────────┘
```

### Phase 2: Final State

```
┌─────────────────────────────────────────┐
│ LocaNext                                │
├─────────────────────────────────────────┤
│ [Single Unified Interface]              │
│                                         │
│ Everything in one place.                │
│ No legacy menu needed.                  │
└─────────────────────────────────────────┘
```

---

## Legacy Apps - What They Contain

### XLS Transfer (11 files)

| File | Functions | LDM Status |
|------|-----------|------------|
| `core.py` | `clean_text`, `simple_number_replace`, `analyze_code_patterns` | Move to `utils/` |
| `embeddings.py` | `EmbeddingsManager`, `generate_embeddings`, `create_faiss_index` | Move to `utils/` |
| `translation.py` | `translate_text_multi_mode`, `find_best_match` | Move to `utils/` |
| `excel_utils.py` | Excel read/write helpers | ✅ LDM has own |
| `config.py` | Configuration | ✅ LDM has own |
| Others | UI-specific, can be deleted | N/A |

### Quick Search (5 files)

| File | Functions | LDM Status |
|------|-----------|------------|
| `qa_tools.py` | QA checks (line, term, pattern, char) | 🔄 P2 absorbing |
| `parser.py` | XML/TXT parsing | ✅ LDM has own |
| `searcher.py` | Dictionary search | ✅ LDM has TM search |
| `dictionary.py` | Dictionary management | ✅ LDM has TM |

### KR Similar (4 files)

| File | Functions | LDM Status |
|------|-----------|------------|
| `core.py` | `normalize_text`, `adapt_structure` | Move to `utils/` |
| `embeddings.py` | `EmbeddingsManager` | Move to `utils/` |
| `searcher.py` | `SimilaritySearcher` | Move to `utils/` |

---

## Migration Plan

### Step 1: Move Shared Code to utils/

```
server/utils/
├── text_processing.py    # normalize_text, clean_text, simple_number_replace
├── embeddings.py         # EmbeddingsManager (unified)
├── similarity_search.py  # SimilaritySearcher
├── qa_helpers.py         # QA check helpers
└── code_patterns.py      # analyze_code_patterns, extract_code_blocks
```

### Step 2: Update Imports

- LDM imports from `server/utils/`
- Legacy apps import from `server/utils/` (backwards compat)

### Step 3: Update Frontend

- Remove old dropdown
- Add clean "Legacy Apps" button in corner
- LDM becomes the main/only interface

### Step 4: Deprecation Period

- Legacy Apps menu shows "(deprecated)" label
- Tooltip: "Use LDM instead - all features available"

### Step 5: Final Removal

- When users confirm they don't need legacy UIs
- Delete `server/tools/xlstransfer/`, `quicksearch/`, `kr_similar/`
- Remove Legacy Apps menu
- Rename to just "LocaNext"

---

## Implementation Checklist

- [ ] Move shared code to `server/utils/`
- [ ] Update all imports (LDM + legacy)
- [ ] Create new Legacy Apps dropdown component
- [ ] Update main navigation
- [ ] Add deprecation labels
- [ ] User testing / feedback
- [ ] Final removal (when ready)

---

*Future task - after P1-P4 complete*
