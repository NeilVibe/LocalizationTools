# WebTranslatorNew Project Reference

**Purpose:** How to correctly search and navigate the WebTranslatorNew project
**Updated:** 2025-12-17

---

## Project Location

```
CORRECT:  /home/neil1988/WebTranslatorNew/
WRONG:    /home/neil1988/LocalizationTools/RessourcesForCodingTheProject/WebTranslatorNew/
          (This folder only contains documentation MD files, NOT the actual code)
```

---

## Key Directories

```
/home/neil1988/WebTranslatorNew/
├── app/
│   ├── services/                  # MAIN LOGIC HERE
│   │   ├── glossary_original.py   # Clustering, Dynamic Glossary (117KB)
│   │   ├── translation.py         # Translation service (46KB)
│   │   ├── embedding.py           # Embedding generation (71KB)
│   │   ├── glossary_enhance.py    # Glossary enhancement (5KB)
│   │   └── task_processor.py      # Queue system (50KB)
│   ├── routes/                    # API endpoints
│   └── models/                    # Database models
├── CLAUDE.md                      # Project overview
├── PROJECT_ROADMAP.md             # Features and status
└── MULTILINE_PROTOCOL.md          # Multi-line handling
```

---

## How to Search

### 1. Search for Feature Keywords

```bash
# From LocaNext project directory:
grep -r "cluster" /home/neil1988/WebTranslatorNew/app/services/ --include="*.py"
grep -r "dynamic.glossary" /home/neil1988/WebTranslatorNew/app/services/ --include="*.py"
grep -r "character.phase" /home/neil1988/WebTranslatorNew/app/services/ --include="*.py"
```

### 2. List All Services

```bash
ls -la /home/neil1988/WebTranslatorNew/app/services/
```

### 3. Read Specific File Sections

```bash
# Read glossary_original.py lines 843-943 (clustering embeddings)
sed -n '843,943p' /home/neil1988/WebTranslatorNew/app/services/glossary_original.py

# Read task_processor.py lines 28-75 (queue system)
sed -n '28,75p' /home/neil1988/WebTranslatorNew/app/services/task_processor.py
```

---

## Key Functions by Feature

### Clustering for Translation Optimization

| Function | File | Lines |
|----------|------|-------|
| `generate_embeddings_for_clustering()` | `glossary_original.py` | 843-943 |
| `build_similarity_graph()` | `glossary_original.py` | 945-1016 |
| `find_connected_components()` | `glossary_original.py` | 1018-1073 |
| `translate_cluster_representatives()` | `glossary_original.py` | 1075-1250 |

**Search command:**
```bash
grep -n "def build_similarity_graph\|def find_connected_components\|def translate_cluster_representatives" \
  /home/neil1988/WebTranslatorNew/app/services/glossary_original.py
```

### Character-Based Phased Processing

| Function | File | Lines |
|----------|------|-------|
| `create_character_phases()` | `glossary_original.py` | 1935-2000 |
| `process_character_phase_parallel()` | `glossary_original.py` | 1989-2100 |

**Search command:**
```bash
grep -n "def create_character_phases\|def process_character_phase" \
  /home/neil1988/WebTranslatorNew/app/services/glossary_original.py
```

### Dynamic Glossary Auto-Creation

| Function | File | Lines |
|----------|------|-------|
| `filter_candidates()` | `glossary_original.py` | 71-128 |
| `translate_candidates()` | `glossary_original.py` | 131-191 |
| `create_dynamic_glossary_entries()` | `glossary_original.py` | 194-237 |
| `generate_dynamic_glossary()` | `glossary_original.py` | 1600-1920 |

**Search command:**
```bash
grep -n "def filter_candidates\|def translate_candidates\|def generate_dynamic_glossary" \
  /home/neil1988/WebTranslatorNew/app/services/glossary_original.py
```

### Queue System (Task Processor)

| Function | File | Lines |
|----------|------|-------|
| `TaskProcessor` class | `task_processor.py` | 28-75 |
| `_process_task()` | `task_processor.py` | 157-222 |
| `_process_dynamic_glossary_workflow()` | `task_processor.py` | 543-803 |

**Search command:**
```bash
grep -n "class TaskProcessor\|def _process_task\|def _process_dynamic_glossary" \
  /home/neil1988/WebTranslatorNew/app/services/task_processor.py
```

---

## Feature Comparison: LocaNext vs WebTranslatorNew

### Already in LocaNext (DO NOT PORT)

| Feature | LocaNext Location |
|---------|-------------------|
| Dual Threshold (0.92/0.49) | `server/tools/ldm/tm_indexer.py` - `find_similar_entries_enhanced()` |
| Line-Level Embeddings | `server/tools/ldm/tm_indexer.py:356-398` - `_build_line_lookup()` |
| 5-Tier Cascade | `server/tools/ldm/tm_indexer.py` - whole/line/hash/embedding/ngram |
| FAISS HNSW Index | `server/tools/ldm/tm_indexer.py:40-46` - M=32, efConstruction=400 |
| Celery Queue | `server/tasks/celery_app.py` - Redis broker |

### NEW in WebTranslatorNew (TO PORT)

| Feature | WebTranslatorNew Location |
|---------|---------------------------|
| Clustering Optimization | `glossary_original.py:945-1250` |
| Character-Based Phases | `glossary_original.py:1935-2000` |
| Dynamic Glossary Auto-Create | `glossary_original.py:1600-1920` |
| Vectorial Centrality Selection | `glossary_original.py:1099-1121` |
| Progressive FAISS Rebuild | `glossary_original.py:1788-1814` |

---

## Quick Reference Commands

```bash
# Check if WebTranslatorNew exists
ls /home/neil1988/WebTranslatorNew/

# List all Python files in services
find /home/neil1988/WebTranslatorNew/app/services -name "*.py" -exec wc -l {} \;

# Search for any function
grep -n "def FUNCTION_NAME" /home/neil1988/WebTranslatorNew/app/services/*.py

# Read full file with line numbers
cat -n /home/neil1988/WebTranslatorNew/app/services/FILE.py | head -100

# Read specific line range
sed -n 'START,ENDp' /home/neil1988/WebTranslatorNew/app/services/FILE.py
```

---

## Common Mistakes

1. **Wrong project path** - Always use `/home/neil1988/WebTranslatorNew/`, NOT the RessourcesForCodingTheProject folder

2. **Listing features we already have** - Check LocaNext first before saying "we need this from WebTranslatorNew"

3. **Not checking actual line numbers** - The line numbers in documentation may shift. Always verify with grep.

4. **Assuming semantic similarity** - QWEN = TEXT similarity, not meaning similarity

---

*Created: 2025-12-17*
