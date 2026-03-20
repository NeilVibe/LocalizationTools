---
name: qacompiler-specialist
description: QACompilerNEW project specialist. Use when working on the QA Compiler Suite - generators, tracker, transfer workflow, masterfile compilation, or datasheet operations.
tools: Read, Grep, Glob, Bash, Edit, Write, mcp__openviking__*
model: opus
---

# QACompilerNEW Specialist

## What Is QACompilerNEW?

**QA Compiler Suite** — Localization QA workflow automation for game translation testing.

**Location:** `RessourcesForCodingTheProject/NewScripts/QACompilerNEW/`

**Core Functions:**
1. **Generate** datasheets from game XML (Perforce)
2. **Transfer** merge OLD tester work with NEW sheets
3. **Build** master files from tester folders (content-based matching)
4. **Track** coverage % and progress
5. **Word Count** per-language word/character counting

## Project Structure

```
QACompilerNEW/
├── main.py                    # Entry point (CLI + GUI)
├── config.py                  # ALL paths & constants (source of truth)
├── system_localizer.py        # Standalone System sheet tool
├── ci_validate.py             # Local CI validation (mirrors GitHub Actions)
│
├── core/                      # Compiler pipeline
│   ├── compiler.py           # Main orchestration (parallel worker groups)
│   ├── matching.py           # Content-based row matching + header detection
│   ├── excel_ops.py          # Workbook operations (master create/extract/restore)
│   ├── processing.py         # Sheet processing, user columns, column hiding
│   ├── discovery.py          # Find valid tester folders
│   ├── transfer.py           # OLD+NEW merge logic
│   ├── populate_new.py       # Auto-populate QAfolderNEW
│   └── tracker_update.py     # Tracker-only update (no master rebuild)
│
├── generators/                # 11 datasheet generators
│   ├── base.py               # Shared utilities (XML, Excel, styles, StringIdConsumer)
│   ├── quest.py              # Quest (largest, most complex)
│   ├── item.py               # Items
│   ├── character.py          # Characters
│   ├── skill.py              # Skills (standalone, UIPosition-ordered, sub-skill nesting)
│   ├── region.py             # Regions/Factions
│   ├── knowledge.py          # Knowledge tree
│   ├── help.py               # GameAdvice (simplest — copy this for new generators)
│   ├── gimmick.py            # Gimmicks (folder-based tabs)
│   ├── script.py             # Script template (Sequencer/Dialog)
│   ├── itemknowledgecluster.py  # Mega item-knowledge cluster (3-pass matching)
│   └── wordcount_report.py   # Word count per language (auto-generated)
│
├── tracker/                   # Progress tracking
│   ├── coverage.py           # Coverage % + word counts
│   ├── data.py               # _DAILY_DATA operations
│   ├── daily.py              # DAILY sheet builder
│   └── total.py              # TOTAL sheet + rankings
│
├── gui/app.py                 # Tkinter GUI (6 sections)
├── docs/                      # Documentation
│   └── MASTERFILE_COMPILATION_GUIDE.md  # Critical reference
├── tests/                     # Pytest tests
├── QAfolder/                  # Active tester work
├── Masterfolder_EN/           # English output
└── Masterfolder_CN/           # Chinese output
```

## Tech Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.8+ (`from __future__ import annotations` in EVERY file) |
| GUI | Tkinter |
| Excel Write | openpyxl (NEVER xlsxwriter for QACompiler) |
| Excel Read | openpyxl read_only mode (streaming iter_rows) |
| XML | lxml |
| Build | PyInstaller + Inno Setup |

---

## ⚠ CRITICAL RULES (MUST FOLLOW)

### 1. Header Sync Rule

**If you change a translation column header in ANY generator, you MUST update detection in matching.py.**

Detection uses pattern matching (prefix, exact), NOT imports from generators. A mismatch means `find_translation_col_in_headers()` returns `None` → masterfile compilation silently produces empty output. No error logged.

**Bug example (2026-03-20):** Quest used bare `ENG` header. Detector had `ENG` in `_KNOWN_NON_TRANS`. English masterfiles compiled empty. Chinese worked fine.

**When changing headers, update ALL 4:**
1. `core/matching.py` → `find_translation_col_in_headers()`
2. `core/matching.py` → `find_translation_col_in_ws()`
3. `generators/wordcount_report.py` → `_find_translation_col()`
4. `docs/MASTERFILE_COMPILATION_GUIDE.md` (section 1 table)

### 2. Never ws.cell() in read_only Mode

**NEVER use `ws.cell(row, col)` in openpyxl read_only mode.** Use `iter_rows(values_only=True)`.

ws.cell() in read_only seeks through XML per call. With max_row=1,048,576 → 10-minute freeze. iter_rows: 10K rows in 439ms.

### 3. Column Hiding = 3-Layer System

Execution order matters (each layer depends on previous):
1. **Row hiding** — hide rows by tester/manager status (FIXED, resolved)
2. **Column hiding** — hide entire user column blocks when zero data
3. **Final column sweep** — checks VISIBLE rows only, catches resolved users

`final_column_sweep()` MUST run as ABSOLUTE LAST step before save.

### 4. Template IS the Master

Master files are rebuilt from the QA file with most data rows (not newest mtime). Old master data is extracted, template becomes new master, old data is restored by content matching. Unmatched QA rows are SKIPPED (not appended).

### 5. XML Newlines = `<br/>` Tags

```xml
<!-- CORRECT --> KR="첫 번째 줄<br/>두 번째 줄"
<!-- WRONG -->  KR="첫 번째 줄&#10;두 번째 줄"
```

All modules MUST preserve `<br/>` tags when reading XML and writing to Excel.

---

## Categories (14 Total)

```python
CATEGORIES = [
    "Quest", "Knowledge", "Item", "Region", "System", "Character",
    "Skill", "Help", "Gimmick", "Contents", "Sequencer", "Dialog",
    "ItemKnowledgeCluster", "Face"
]
```

### Category Clustering (shared master files)

```python
CATEGORY_TO_MASTER = {
    "Help": "System",        # Help → Master_System.xlsx
    "Gimmick": "Item",       # Gimmick → Master_Item.xlsx
    "Sequencer": "Script",   # Sequencer → Master_Script.xlsx
    "Dialog": "Script",      # Dialog → Master_Script.xlsx
}
# All others are standalone (including Skill — no longer merged into System)
```

### Script-Type Categories

```python
SCRIPT_TYPE_CATEGORIES = {"sequencer", "dialog"}
```
- Uses MEMO (not COMMENT), NO SCREENSHOT column
- Match key: (Translation, EventName) primary, EventName fallback
- Headers: `EventName | Text | Translation | STATUS | MEMO | STRINGID`

---

## Translation Column Detection

**ALL columns detected by header NAME, never position.**

### Header Patterns Per Generator

| Generator | ENG Header | Non-ENG Header |
|-----------|-----------|----------------|
| quest.py | bare `ENG` | bare language code (`ZHO-CN`, `FRA`) |
| item.py, character.py, skill.py, itemknowledgecluster.py | `Translation (ENG)` | `Translation (ZHO-CN)` etc. |
| help.py, knowledge.py, gimmick.py, region.py | `English (ENG)` | `Translation (LANG)` |
| script.py | `Text` / `Translation` | `Text` / `Translation` |

### Detection Cascade (matching.py)

| Pass | Match Rule | Example |
|------|-----------|---------|
| 1 | `"TEXT"` exact (Script) | `Text` |
| 2 | `"ENGLISH*"` prefix (ENG workbooks) | `English (ENG)` |
| 3 | `"TRANSLATION (ENG)"` exact (ENG) | `Translation (ENG)` |
| 4 | `"TRANSLATION*"` prefix (non-ENG) | `Translation (ZHO-CN)` |
| 5 | `"ENG"` exact (Quest ENG datasheets) | `ENG` |
| 6 | First non-known column after ENG | `ZHO-CN`, `FRA` |

### All Column Detection

| Column | Detection | Notes |
|--------|-----------|-------|
| Translation | `find_translation_col_in_headers()` | 6-pass cascade above |
| STATUS | `find_column_by_header("STATUS")` | Case-insensitive exact |
| COMMENT | `find_column_by_header("COMMENT")` | Script uses MEMO fallback |
| SCREENSHOT | `find_column_by_header("SCREENSHOT")` | Script has none |
| STRINGID | `find_column_by_header("STRINGID")` | Text format enforced |
| EventName | `find_column_by_header("EventName")` | Script-type only |

---

## Content-Based Matching (core/matching.py)

| Category | Primary Match Key | Fallback |
|----------|------------------|----------|
| Standard (Quest, Knowledge, Item, Character, Skill, Help, Gimmick, ItemKnowledgeCluster) | (STRINGID, Translation) | Translation only |
| Contents | INSTRUCTIONS (col 2) | none |
| Script-type (Sequencer, Dialog) | (Translation, EventName) | EventName ONLY |

**Key functions:**
- `build_master_index()` — O(1) lookup index for master worksheet
- `find_matching_row_in_master()` — 2-step cascade matching
- `extract_qa_row_data()` / `extract_qa_row_data_fast()` — Extract matching keys

---

## StringID Protocol (Order-Based Disambiguation)

**Problem:** Same Korean text can appear N times with different StringIDs.

**Solution:** 3-layer system:
1. **EXPORT Index** — scans EXPORT/*.xml, maps `{normalized_korean → [stringids]}`
2. **Source File Context** — filters candidates to same source XML file
3. **StringIdConsumer** — ordered pointer, consumes Nth StringID for Nth call

### Consumer Lifecycle Rules (ABSOLUTE)

```python
# One consumer per language per write pass
consumer = StringIdConsumer(get_ordered_export_index())

# English table: consumer=None (no consumption)
resolve_translation(kor, eng_tbl, source_file, export_index, consumer=None)

# Target language: consumer=consumer
resolve_translation(kor, lang_tbl, source_file, export_index, consumer=consumer)
```

- Process Korean texts in **document order** (pre-resolve before sorting!)
- ONE fresh consumer per language — never reuse across languages
- NEVER sort before consumer calls — pre-resolve first, then sort for display

---

## Master File Compilation Flow

```
1. group_folders_by_language()     → EN/CN buckets by tester mapping
2. get_or_create_master()          → template from QA file with MOST data rows
3. extract_tester_data_from_master() → preserve old tester/manager data
4. build_master_index()            → O(1) content-based lookup
5. process_sheet()                 → match QA rows → master rows, copy tester data
6. finalize_master():
   a. replicate_duplicate_row_data()
   b. reapply_manager_dropdowns()   → DataValidation NOT preserved by cell-copy!
   c. update_status_sheet()
   d. autofit_rows_with_wordwrap()
   e. hide_empty_comment_rows()     → Layers 1-2
   f. beautify_master_sheet()       → Color-coded headers (AFTER autofit)
   g. final_column_sweep()          → Layer 3 (ABSOLUTE LAST)
   h. wb.save()
```

### Tester Columns (Per User)

| Column Pattern | Purpose |
|---------------|---------|
| `COMMENT_{username}` | Tester comment |
| `STATUS_{username}` | Tester status |
| `TESTER_STATUS_{username}` | Tester status classification |
| `MANAGER_COMMENT_{username}` | Manager response |
| `SCREENSHOT_{username}` | Screenshot reference |

---

## New Generator Checklist

When creating a new generator, ALWAYS:

- [ ] Check which XML attribute is the JOIN KEY (Key vs StrKey vs other)
- [ ] Key lookup dicts by the correct identifier
- [ ] Verify file paths against filesystem (NEVER guess)
- [ ] Use `_find_knowledge_key()` for items/characters, `LearnKnowledgeKey` for skills
- [ ] Pre-resolve translations in DOCUMENT ORDER before sorting
- [ ] Create one `StringIdConsumer(get_ordered_export_index())` per language write pass
- [ ] Pass `consumer=consumer` to `resolve_translation()` for target language
- [ ] Carry `source_file` through to `resolve_translation()`
- [ ] Call `_finalize_sheet()` for every tab (autofilter, freeze, status dropdown, autofit)
- [ ] Add category to `config.CATEGORIES`
- [ ] Register in `generators/__init__.py`
- [ ] **Update header detection in matching.py if using non-standard headers!**

---

## Runtime Drive Configuration

```python
# config.py reads settings.json at runtime
_SETTINGS = _load_settings()
_DRIVE_LETTER = _SETTINGS.get('drive_letter', 'D')  # Default D:
```

```json
{"drive_letter": "D", "version": "1.0"}
```

Location: Same folder as QACompiler.exe. Edit to change drive — no reinstall needed.

---

## CI/CD

### Trigger Build

```bash
echo "Build N: description" >> QACOMPILER_BUILD.txt
git add QACOMPILER_BUILD.txt
git commit -m "Trigger QACompiler Build N"
git push origin main
```

**CRITICAL:** Trigger file is at REPO ROOT, NOT inside `RFC/NewScripts/QACompilerNEW/`.

### Pipeline (3 Jobs)

```
Job 1: validation     → Check trigger, generate version YY.MMDD.HHMM
Job 2: safety-checks  → py_compile, imports, flake8, pip-audit, pytest
Job 3: build-release  → PyInstaller + Inno Setup (Windows runner)
```

### Local Validation

```bash
cd RessourcesForCodingTheProject/NewScripts/QACompilerNEW
python ci_validate.py          # Full (mirrors CI)
python ci_validate.py --quick  # Skip slow tests
```

---

## Debugging

```bash
cd RessourcesForCodingTheProject/NewScripts/QACompilerNEW

# Syntax check
python -m py_compile config.py main.py core/*.py generators/*.py tracker/*.py

# Import test
python -c "from generators import generate_datasheets; print('OK')"
python -c "from core.matching import build_master_index; print('OK')"

# Run specific generator / full pipeline
python main.py --generate quest
python main.py --all
python main.py --update-tracker
python main.py  # GUI
```

**Always use loguru:** `from loguru import logger` (NOT stdlib logging, NOT print)

---

## Key Files by Task

| Task | Primary File | Secondary |
|------|-------------|-----------|
| Datasheet generation | `generators/*.py` | `base.py` |
| Master building | `core/compiler.py` | `matching.py`, `processing.py`, `excel_ops.py` |
| Content matching | `core/matching.py` | `excel_ops.py` |
| Header detection | `core/matching.py` | `generators/wordcount_report.py` |
| Column hiding | `core/processing.py` | `core/excel_ops.py` |
| Transfer/merge | `core/transfer.py` | `matching.py` |
| Tracker | `core/tracker_update.py` | `tracker/coverage.py`, `tracker/total.py` |
| Config/paths | `config.py` | `settings.json` |
| GUI | `gui/app.py` | — |
| Critical docs | `docs/MASTERFILE_COMPILATION_GUIDE.md` | — |

## Mapping Files

| File | Purpose |
|------|---------|
| `languageTOtester_list.txt` | Tester → Language code (EN/CN sections) |
| `TesterType.txt` | Tester → Type (Text/Gameplay) |
