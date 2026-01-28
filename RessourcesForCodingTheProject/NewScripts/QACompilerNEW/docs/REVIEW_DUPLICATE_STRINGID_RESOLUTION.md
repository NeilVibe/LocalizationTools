# Code Review: Duplicate StringID Resolution

**Date:** 2026-01-28
**Status:** REVIEWED - ALL CORRECT
**Reviewer:** Claude Code

---

## Overview

This document records the code review of the duplicate StringID resolution system across all data generators in QACompiler.

---

## Review Scope

Two aspects were reviewed:

1. **StringID Resolution for Duplicates** - Does each generator correctly get the right StringID from the right file when duplicates exist?
2. **Duplicate Inclusion** - Are duplicates handled appropriately (included or deduplicated by design)?

---

## Finding 1: EXPORT-Based StringID Resolution

### Verdict: CORRECTLY IMPLEMENTED IN ALL GENERATORS

The core resolution logic is in `generators/base.py:180-248`:

```python
def resolve_translation(korean_text, lang_table, data_filename, export_index):
    # 1. Get all (translation, stringid) candidates for this Korean text
    # 2. If only one candidate -> return it
    # 3. If multiple candidates:
    #    - Look up EXPORT file matching the source data file
    #    - Find which StringID exists in that EXPORT file
    #    - Return the matching (translation, stringid)
    # 4. Fallback: first good translation
```

### How It Works

```
Korean text "안녕" appears in multiple files with different StringIDs:

File: QuestA.xml  -> Korean "안녕" -> EXPORT/QuestA.xml has StringID_001
File: QuestB.xml  -> Korean "안녕" -> EXPORT/QuestB.xml has StringID_002

When processing QuestA.xml:
  resolve_translation("안녕", lang_tbl, "QuestA.xml", export_index)
  -> Checks EXPORT/QuestA.xml -> Finds StringID_001 -> Returns correct translation

When processing QuestB.xml:
  resolve_translation("안녕", lang_tbl, "QuestB.xml", export_index)
  -> Checks EXPORT/QuestB.xml -> Finds StringID_002 -> Returns correct translation
```

### All Generators Pass source_file Correctly

| Generator | File | Lines Using resolve_translation | source_file Passed |
|-----------|------|--------------------------------|-------------------|
| quest.py | lines 132, 146 | `source_file` |
| skill.py | lines 420, 423 | `source_file` |
| character.py | lines 255, 258 | `char.source_file` |
| item.py | lines 588, 614, 830, 901 | `src_file` |
| region.py | lines 669, 675 | `source_file` |
| knowledge.py | lines 479, 486 | `source_file` |
| gimmick.py | lines 270, 285 | `source_file` |
| help.py | lines 299, 305 | `source_file` |

---

## Finding 2: Data-Level Deduplication (By Design)

### These Are NOT Bugs - They Are Intentional Design Decisions

Some generators deduplicate at the **game data extraction level** (not translation level). This is separate from StringID resolution.

| Generator | Deduplication | Behavior | Reason |
|-----------|---------------|----------|--------|
| **Quest** | Dict by tag (line 818) | Last wins | By design - handles multi-file quest definitions |
| **Skill** | Knowledge by StrKey (line 175) | First wins | Prevents duplicate knowledge entries |
| **Item** | ItemInfo by StrKey (line 136) | First wins | Prevents duplicate item definitions |
| **Region** | Global seen set | First wins | Maintains hierarchy integrity |
| **Knowledge** | Groups deduplicated with merging | Smart merge | Combines children from multiple files |
| **Character** | None | All included | No deduplication needed |
| **Help** | None | All included | No deduplication needed |
| **Gimmick** | Shop entries only | Mixed | Shop deduplication, gimmicks all included |

### Important Distinction

```
DATA-LEVEL DEDUPLICATION (Game data extraction)
  Question: "Should we include this game element in output?"
  Example: Quest_ABC appears in File1 and File2 - which one to use?
  Answer: By design, use the last one (dict overwrite)

TRANSLATION-LEVEL RESOLUTION (StringID matching)
  Question: "What StringID does this Korean text get?"
  Example: Korean "안녕" in QuestA.xml vs QuestB.xml
  Answer: EXPORT matching gives correct StringID for each file
```

These are INDEPENDENT systems. Data deduplication happens first, then translation resolution uses EXPORT matching for the included data.

---

## Conclusion

| Aspect | Status |
|--------|--------|
| EXPORT-based StringID resolution | CORRECT in all 8 generators |
| source_file tracking | CORRECT - all generators track and pass it |
| Data-level deduplication | BY DESIGN - not bugs |
| Translation duplicates | HANDLED via EXPORT matching |

**No code changes needed.** The system correctly:
1. Tracks which file each data entry came from
2. Uses EXPORT folder matching to resolve duplicate Korean text to correct StringID
3. Applies intentional deduplication rules at the game data level

---

## Files Reviewed

- `generators/base.py` - Core resolution logic (lines 180-248)
- `generators/quest.py` - Quest generator
- `generators/skill.py` - Skill generator
- `generators/character.py` - Character generator
- `generators/item.py` - Item generator
- `generators/region.py` - Region generator
- `generators/knowledge.py` - Knowledge generator
- `generators/gimmick.py` - Gimmick generator
- `generators/help.py` - Help generator

---

*Code Review Document | 2026-01-28*
