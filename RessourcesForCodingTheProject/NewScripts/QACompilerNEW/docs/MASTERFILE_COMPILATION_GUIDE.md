# Master File Compilation Guide

> Critical lessons and reference for QACompiler master file generation, matching, and post-processing.

---

## ⚠ CRITICAL: Header Sync Rule

**If you change or add a translation column header in ANY generator, you MUST update the detection logic to match.**

The detection in `core/matching.py` uses pattern matching (prefix checks, exact matches) — it does NOT import header variables from generators. A mismatch means the translation column returns `None`, and masterfile compilation silently produces empty output for that language.

**Bug example (2026-03-20):** Quest generator used bare `ENG` as header. The detector had `ENG` in `_KNOWN_NON_TRANS` (to avoid false positives for Chinese). Result: English Quest masterfiles compiled empty. Chinese worked fine because `ZHO-CN` wasn't in the exclusion set.

**When changing headers, update ALL of these:**
1. `core/matching.py` → `find_translation_col_in_headers()`
2. `core/matching.py` → `find_translation_col_in_ws()`
3. `generators/wordcount_report.py` → `_find_translation_col()`
4. This guide (section 1 table)

---

## 1. Translation Column Detection

The translation column header varies by generator and language:

| Generator | ENG Header | Non-ENG Header |
|-----------|-----------|----------------|
| Item, Character, Skill, Knowledge, Help, Gimmick | `Translation (ENG)` or `English (ENG)` | `Translation (ZHO-CN)`, `Translation (FRA)`, etc. |
| Quest (ENG) | Bare `ENG` column | — |
| Quest (non-ENG) | — | Bare language code after ENG: `ZHO-CN`, `FRA`, `PT-BR` |
| Script (Sequencer/Dialog) | `TEXT` or `Translation` | `TEXT` or `Translation` |

### Detection Functions

**`core/matching.py` — `find_translation_col_in_headers(col_idx, is_english)` (line 101)**
- Input: `col_idx` dict `{HEADER_UPPER: 0-based index}` from `preload_worksheet_data()`
- Returns: 0-based column index or `None`

**`core/matching.py` — `find_translation_col_in_ws(ws, is_english)` (line 170)**
- Input: worksheet object
- Returns: 1-based column index or `None`

**`generators/wordcount_report.py` — `_find_translation_col(ws)` (line 166)**
- Mirrors the same logic for word count reporting
- Returns: 1-based column index or `None`

### 5-Pass Detection Cascade

All three functions use the same priority order:

| Pass | Match Rule | Example Headers |
|------|-----------|-----------------|
| 1 | `TRANSLATION*` prefix | `Translation (ZHO-CN)`, `Translation (ENG)` |
| 2 | `ENGLISH*` prefix | `English (ENG)` |
| 3 | Language code after ENG — first column after `ENG` that is NOT in `_KNOWN_NON_TRANS` | `ZHO-CN`, `FRA`, `PT-BR` |
| 4 | `ENG` itself | `ENG` (Quest ENG datasheets) |
| 5 | `TEXT` exact match | `TEXT` (Script category) |

### Known Non-Translation Headers (Skipped in Pass 3)

```python
_KNOWN_NON_TRANS = {
    "ORIGINAL", "SOURCETEXT", "STRINGID", "STRINGKEY", "COMMAND",
    "STATUS", "COMMENT", "MEMO", "SCREENSHOT", "DATATYPE", "FILENAME",
    "ENG", "RECORDING", "DIALOGTYPE", "GROUP", "SEQUENCENAME",
    "DIALOGVOICE", "SUBTIMELINENAME", "EVENTNAME", "INSTRUCTIONS",
}
```

Also skips any header starting with `COMMENT_`, `STATUS_`, `TESTER_STATUS_`, `MANAGER_COMMENT_`, `SCREENSHOT_` (matching.py line 164).

### CRITICAL WARNING

If detection returns `None`, ALL matching fails silently — no rows match, no data transfers. Both `find_translation_col_in_headers()` (line 477-481) and `_find_translation_col()` (line 306-307) now log warnings when this happens.

---

## 2. Master File Column Hiding (3-Layer System)

### Layer 1 — Row Hiding

**Function:** `core/processing.py` — `hide_empty_comment_rows()` (line 974)

Hides rows based on tester/manager status:
- Tester status is `NO ISSUE`, `BLOCKED`, or `KOREAN` → hide row
- ALL managers marked `FIXED` or `NON-ISSUE` → hide row
- `ISSUE` rows with any unresolved manager status → **stay visible**

### Layer 2 — Column Hiding (same function)

Hides entire user column blocks when a user's `COMMENT_{user}` column has **zero data across the entire sheet**. Paired columns also hidden:
- `STATUS_{user}`
- `TESTER_STATUS_{user}`
- `MANAGER_COMMENT_{user}`
- `SCREENSHOT_{user}`

### Layer 3 — Final Column Sweep

**Function:** `core/excel_ops.py` — `final_column_sweep(wb)` (line 939)

Runs **LAST**, after all processing including row hiding and beautification. For each user's `COMMENT` column:
1. Checks only **visible** (non-hidden) rows
2. If zero visible content → hides entire column block
3. Catches: resolved users (all `FIXED`), orphaned columns, empty users

### Key Lesson

"Has data" does NOT mean "has something to show." A user with 50 comments that are all `FIXED` has data in the sheet but nothing visible after row hiding. Layer 3 catches this case.

---

## 3. Master File Rebuild Pipeline

**Function:** `core/compiler.py` — `finalize_master()` (line 1476)

Execution order is critical — each step depends on the previous:

| Step | Function | Purpose |
|------|----------|---------|
| 0 | `replicate_duplicate_row_data(wb, cat, is_eng)` | Fill duplicate rows with replicated data |
| 1 | `reapply_manager_dropdowns(ws)` | Re-apply FIXED/REPORTED/CHECKING/NON ISSUE dropdowns |
| 2 | `update_status_sheet(wb, users, stats)` | Rebuild STATUS tab summary |
| 3 | `autofit_rows_with_wordwrap(wb)` | Set column widths + row heights; returns `sheet_data_cache` |
| 4 | `hide_empty_comment_rows(wb, preloaded_sheets=sheet_data_cache)` | Row hiding (Layer 1) + column hiding (Layer 2) |
| 5 | `beautify_master_sheet(ws)` | Color-coded headers (blue/green/orange). **AFTER autofit** so headers aren't stomped |
| 6 | `final_column_sweep(wb)` | Ultimate column visibility check (Layer 3). **ABSOLUTE LAST** before save |
| 7 | `wb.save(path)` | Save to disk |

Step 4 reuses `sheet_data_cache` from step 3 to avoid redundant worksheet loading.

---

## 4. Matching Logic (Content Key System)

**Index builder:** `core/matching.py` — `build_master_index()` (line 386)
**Matcher:** `core/matching.py` — `find_matching_row_in_master()` (line 594)

### Standard Categories (Item, Character, Skill, Quest, Knowledge, Help, Gimmick)

| Priority | Key | Type |
|----------|-----|------|
| Primary | `(StringID, Translation)` | Exact match — both must match |
| Fallback | `Translation` only | Catches empty/changed StringIDs |

### Script Categories (Sequencer/Dialog)

| Priority | Key | Type |
|----------|-----|------|
| Primary | `(Translation, EventName)` | Both must match |
| Fallback | `EventName` only | NOT translation-only |

### Contents Category

| Priority | Key | Type |
|----------|-----|------|
| Primary | `INSTRUCTIONS` column value | Unique identifier, no fallback |

### StringID Order Indexing (CRITICAL)

StringIDs are resolved using a **3-layer ordered indexing system** that ensures each row gets the CORRECT StringID even when the same Korean text appears multiple times in the game data:

**Layer 1 — EXPORT Index** (`base.py` — `build_export_indexes()`):
- Scans `EXPORT/*.xml` files to build: `{normalized_korean_text → set of source filenames}`
- This tells us WHICH game data file a Korean text belongs to

**Layer 2 — Source File Context** (`base.py` — `resolve_translation()`):
- Filters translation candidates to those from the SAME source XML file
- Prevents cross-file StringID collision (same Korean in `QuestData.xml` vs `ItemData.xml`)

**Layer 3 — StringIdConsumer** (`base.py` — `StringIdConsumer` class):
- Maintains an **ordered pointer** per normalized Korean text
- Each call to `_tr_sid()` consumes the NEXT available StringID from the ordered list
- Prevents duplicate consumption: same text appearing 3 times gets 3 different StringIDs in order
- **One fresh consumer per language** — `eng_tbl` uses `consumer=None` (no consumption), `lang_tbl` uses the real consumer

**Example:**
```
XML has: "오크 처치" → [STR_001, STR_047, STR_112] (3 occurrences in order)

Call 1: _tr_sid("오크 처치", ..., consumer) → STR_001 (pointer advances)
Call 2: _tr_sid("오크 처치", ..., consumer) → STR_047 (pointer advances)
Call 3: _tr_sid("오크 처치", ..., consumer) → STR_112 (pointer advances)

ENG: _tr("오크 처치", eng_tbl, ..., None) → always gets first match (no consumption)
```

**Applied to ALL row types:** Mission Name, Desc, CompleteLog, SubMission, Quest Node — all use `_tr_sid()` with the consumer, ensuring StringIDs follow the exact game data XML order.

### Critical Rules

- Empty StringID must NOT block fallback matching (was a bug, fixed)
- Content key must be built identically by both `extract_tester_data_from_master()` (excel_ops.py line 289) and `build_master_index()` (matching.py line 386)
- `sanitize_stringid_for_match()` (line 75) handles: `None`, int/string mismatch, scientific notation, whitespace
- Master index uses `consumed` set to prevent duplicate row assignments
- `clone_with_fresh_consumed()` (line 513) enables reusing the same index across multiple users
- **NEVER pass consumer to eng_tbl lookups** — `_tr(text, eng_tbl, ..., None)` — ENG must not consume
- **One fresh StringIdConsumer per language** — created at the start of each language loop in the generator

---

## 5. Template-Based Masters (No Append)

The master rebuild uses the **latest QA file as the template** — all formatting is preserved from source.

**Process:**
1. `extract_tester_data_from_master()` — extract old master data as `{(sheet, content_key): {user: data_dict}}`
2. New QA file becomes the template (all rows, formatting, structure)
3. `restore_tester_data_to_master()` — match old data onto new template rows
4. Unmatched QA rows are **SKIPPED**, not appended (prevents messy stacked tables)

**Manager data travels as ONE UNIT** with tester data per user:
- `COMMENT_{user}` (tester comment)
- `STATUS_{user}` (tester status)
- `TESTER_STATUS_{user}` (tester status classification)
- `MANAGER_COMMENT_{user}` (manager response)
- `SCREENSHOT_{user}` (screenshot reference)

---

## 6. Word Count Report

**File:** `generators/wordcount_report.py`
**Output:** `GeneratedDatasheets/WordCount_Report.xlsx`

| Feature | Detail |
|---------|--------|
| Trigger | Auto-generated after datasheet generation |
| Layout | One Excel tab per language (detected from filename regex `_([A-Z]{2,3}(?:-[A-Z]{2})?)\.XLSX$`) |
| Tables | One clean table per category, separated by empty row |
| Latin languages | Word count (space-split via `count_words_english`) |
| CJK languages | Character count (via `count_chars_chinese`); codes: `CHS, CHT, CN, JP, JPN, TW, ZH, ZHS, ZHT, JA` |
| Performance | Uses `iter_rows(values_only=True)` streaming — instant even for 10K+ rows |
| Column detection | Same 5-pass cascade as matching (`_find_translation_col`, line 166) |
| CJK auto-detect | Header code check → sample text scan → default to word mode |

---

## 7. Quest Desc + CompleteLog

**File:** `generators/quest.py` — `_build_mission_desc_rows()` (line ~177)

Mission XML elements have two text fields:
- **Desc** — objective text shown BEFORE mission completion
- **CompleteLog** — summary text shown AFTER mission completion

### Behavior

- Both extracted and stacked at `mission_depth + 1` below the Mission Name row
- Rows are bold (structural, not content)
- Applied to all 5 quest builders: main, faction, daily, challenge, minigame
- `br`-tag-only text is filtered out: `clog_kr.replace("<br/>", "").replace("<BR/>", "").strip()` — prevents phantom empty rows
- No StringKey for CompleteLog (line 217: `""`)

### Row Structure

```
[depth N]   Mission Name (Name row)
[depth N+1]   Desc text (if non-empty after br-tag filter)
[depth N+1]   CompleteLog text (if non-empty after br-tag filter)
[depth N+1]   SubMission rows...
```

---

*Reference guide — 2026-03-20*
