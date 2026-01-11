# P36 StringID Testing Plan

**Created:** 2025-12-17 | **Updated:** 2025-12-17 15:55 KST | **Status:** IN PROGRESS | **Phase:** 2D

---

## Current Status

| Item | Status |
|------|--------|
| Bug fix: StringID matching in pretranslate.py | ✅ DONE |
| Basic tests (37 tests with small data) | ✅ PASSING |
| TRUE E2E: Standard TM | ✅ **COMPLETE** (6/6 tests pass) |
| TRUE E2E: XLS Transfer | 🔄 **TODO** (next) |
| TRUE E2E: KR Similar | ⏳ **PENDING** |

**Standard TM TRUE E2E Results (2025-12-17 15:30 KST):**
```
File: tests/fixtures/stringid/true_e2e_standard.py
Tests: 6/6 PASSED
Runtime: 66 seconds
TM: 5000 entries (from sampleofLanguageData.txt)
Duplicates: 2446 entries with different StringIDs
Test file: 150 rows
Match rate: 100%
StringID exact matches: 50/50 correct
```

**Bug Fixed (2025-12-17):**
`_pretranslate_standard()` was ignoring StringID - always took first variation.
Fixed in `server/tools/ldm/pretranslate.py:150-176` to:
1. Get top_k=10 results (all variations)
2. Filter by row.string_id if exists
3. Fallback to first result

---

## Overview

Testing plan for StringID mode functionality - ensuring the same Korean source text can have multiple translations based on context (StringID).

---

## Functions Modified (Need Testing)

### Backend Files Modified

| File | Function | Change | Test Required |
|------|----------|--------|---------------|
| `server/database/models.py` | `LDMTMEntry` | Added `string_id` column | DB storage test |
| `server/database/models.py` | `LDMTranslationMemory` | Added `mode` column | TM mode test |
| `server/database/db_utils.py` | `bulk_copy_tm_entries()` | Added string_id param | Bulk insert test |
| `server/tools/ldm/tm_indexer.py` | `build_indexes()` | Fetches string_id from DB | Index build test |
| `server/tools/ldm/tm_indexer.py` | `_build_whole_lookup()` | Variations structure | PKL structure test |
| `server/tools/ldm/tm_indexer.py` | `_build_line_lookup()` | Added string_id | Line PKL test |
| `server/tools/ldm/tm_indexer.py` | `_build_whole_embeddings()` | Added string_id to mapping | Embedding test |
| `server/tools/ldm/tm_indexer.py` | `_build_line_embeddings()` | Added string_id to mapping | Line embedding test |
| `server/tools/ldm/tm_indexer.py` | `TMSearcher.search()` | Handles variations | Search test |
| `server/tools/ldm/tm_indexer.py` | `load_indexes()` | Optional line indexes | Load test |
| `server/tools/ldm/pretranslate.py` | `PretranslationEngine` | NEW - Routes to engines | Pretranslate test |
| `server/tools/ldm/api.py` | `/api/ldm/pretranslate` | NEW endpoint | API test |
| `server/tools/ldm/api.py` | `/tm/upload` | Added mode, stringid_col | Upload test |

---

## 1. Source Data: sampleofLanguageData.txt

**Location:** `/mnt/c/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/TestFilesForLocaNext/sampleofLanguageData.txt`

**Structure (Tab-Separated):**
```
Col 0: Flag (0)
Col 1: StringID (numeric ID like 390, 37579, 18613)
Col 2-4: Metadata (0, 0, 1)
Col 5: Korean source text
Col 6: Target translation (FR)
Col 7: Status ("Current")
```

**Rich Data Includes:**
- Color codes: `<PAColor0xffe9bd23>...</PAOldColor>`
- Text bindings: `{TextBind:CLICK_ON_RMB_ONLY}`
- Newlines: `\n` (literal)
- Korean text with special patterns
- 16MB of real production data

---

## 2. Test Fixture Generation Strategy

### 2.1 Universal Format Conversion

From the master TXT data, we can generate:

| Format | Structure | Notes |
|--------|-----------|-------|
| **TXT** | Cols 0-4=StringID prefix, 5=Source, 6=Target | Native format |
| **XML** | `<Row id="StringID"><StrOrigin>Korean</StrOrigin><Str>Target</Str></Row>` | Map StringID to attr |
| **Excel** | Col A=Source, Col B=Target, Col C=StringID | 3-column mode |

### 2.2 Creating Duplicate Sources with Different StringIDs

**The Key Test Case:** Same Korean source, different StringID, different translations.

**Example from Real Data:**
```
StringID  Korean              Target
49310     카이아 낚시 배 뱃머리   Proue de bateau de pêche de Kaia
49310     카이아 낚시 배 뱃머리   [LONG_DESCRIPTION with color codes]
```

**Manual Test Data Creation:**
```python
# Example: Same Korean word with different contexts
duplicates = [
    {"string_id": "UI_SAVE_BUTTON", "source": "저장", "target": "Save"},
    {"string_id": "GAME_SAVE_MENU", "source": "저장", "target": "Save Game"},
    {"string_id": "FILE_STORAGE", "source": "저장", "target": "Storage"},

    {"string_id": "UI_SETTINGS_BTN", "source": "설정", "target": "Settings"},
    {"string_id": "TECH_CONFIG", "source": "설정", "target": "Configuration"},

    {"string_id": "UI_CONFIRM_OK", "source": "확인", "target": "OK"},
    {"string_id": "UI_CONFIRM_YES", "source": "확인", "target": "Confirm"},
]
```

---

## 3. Test Fixtures to Generate

### 3.1 Text Format (TXT/TSV)

**File:** `tests/fixtures/stringid/stringid_test_data.txt`

```
0	UI_SAVE_BUTTON	0	0	1	저장	Save	Current
0	GAME_SAVE_MENU	0	0	1	저장	Save Game	Current
0	FILE_STORAGE	0	0	1	저장	Storage	Current
0	UI_SETTINGS_BTN	0	0	1	설정	Settings	Current
0	TECH_CONFIG	0	0	1	설정	Configuration	Current
0	UI_CONFIRM_OK	0	0	1	확인	OK	Current
0	UI_CONFIRM_YES	0	0	1	확인	Confirm	Current
```

### 3.2 XML Format

**File:** `tests/fixtures/stringid/stringid_test_data.xml`

```xml
<?xml version="1.0" encoding="utf-8"?>
<LanguageData>
    <Row id="UI_SAVE_BUTTON">
        <StrOrigin>저장</StrOrigin>
        <Str>Save</Str>
    </Row>
    <Row id="GAME_SAVE_MENU">
        <StrOrigin>저장</StrOrigin>
        <Str>Save Game</Str>
    </Row>
    <!-- ... more entries ... -->
</LanguageData>
```

### 3.3 Excel Format (XLSX)

**File:** `tests/fixtures/stringid/stringid_test_data.xlsx`

| Source | Target | StringID |
|--------|--------|----------|
| 저장 | Save | UI_SAVE_BUTTON |
| 저장 | Save Game | GAME_SAVE_MENU |
| 저장 | Storage | FILE_STORAGE |
| 설정 | Settings | UI_SETTINGS_BTN |
| 설정 | Configuration | TECH_CONFIG |
| 확인 | OK | UI_CONFIRM_OK |
| 확인 | Confirm | UI_CONFIRM_YES |

---

## 4. Test Cases for StringID Mode (Detailed)

### 4.1 TM Upload Tests (`/api/ldm/tm/upload`)

| ID | Test Case | Input | Expected Result | Verify |
|----|-----------|-------|-----------------|--------|
| TM-01 | Upload StringID Excel | 3-col Excel, mode=stringid | All 7 entries stored | `SELECT COUNT(*) FROM ldm_tm_entries WHERE tm_id=X` = 7 |
| TM-02 | Upload Standard Excel | 2-col Excel, mode=standard | Duplicates merged | Count = 5 (unique sources) |
| TM-03 | Verify string_id stored | Query DB | string_id NOT NULL | `SELECT string_id FROM ldm_tm_entries WHERE tm_id=X` |
| TM-04 | Verify TM mode | Query DB | mode='stringid' | `SELECT mode FROM ldm_translation_memories WHERE id=X` |
| TM-05 | Empty StringID col | 3-col with empty col C | Entries have NULL string_id | No error, string_id=NULL |
| TM-06 | Mixed StringID | Some rows have StringID, some don't | Partial storage | Mixed NULL/values |
| TM-07 | Upload TXT format | Tab-separated, col 1=StringID | Correct parsing | string_id from col 1 |
| TM-08 | Upload XML format | `<Row id="StringID">` | Correct parsing | string_id from id attr |

### 4.2 Index Building Tests (`TMIndexer.build_indexes()`)

| ID | Test Case | Input | Expected Result | Verify |
|----|-----------|-------|-----------------|--------|
| IDX-01 | Build with StringID TM | TM mode=stringid | PKL has variations | Load and check structure |
| IDX-02 | Build with Standard TM | TM mode=standard | PKL has single entries | No "variations" key |
| IDX-03 | whole_lookup structure | StringID TM | `{"저장": {"variations": [...]}}` | 3 variations for "저장" |
| IDX-04 | whole_mapping structure | StringID TM | Each entry has string_id | Check mapping[0]["string_id"] |
| IDX-05 | line_lookup structure | Multi-line entries | string_id in line entries | Check line PKL |
| IDX-06 | line_mapping structure | Multi-line entries | string_id in line mapping | Check line_mapping[0] |
| IDX-07 | No line indexes | TM without multi-line | No line.npy/line.index | Files don't exist, no error |
| IDX-08 | Rebuild indexes | Delete PKL, rebuild | Same structure | Compare before/after |

### 4.3 Search Tests (`TMSearcher.search()`)

| ID | Test Case | Query | Expected Result | Verify |
|----|-----------|-------|-----------------|--------|
| SRC-01 | Tier 1 exact - variations | "저장" | Returns 3 variations | len(results) == 3 |
| SRC-02 | Tier 1 exact - single | "취소" | Returns 1 result | len(results) == 1, string_id present |
| SRC-03 | Tier 1 - string_id in result | "설정" | Results have string_id | results[0]["string_id"] == "TECH_CONFIG" |
| SRC-04 | Tier 2 embedding | "저장하기" | Returns matches | score < 1.0, string_id present |
| SRC-05 | Tier 2 - variations | Similar to "저장" | Multiple results | Each has string_id |
| SRC-06 | No match | "XXXXXXX" | Empty results | len(results) == 0 |
| SRC-07 | Standard TM search | TM mode=standard | Single result per source | No variations key |
| SRC-08 | Score preserved | Any match | score field present | results[0]["score"] exists |
| SRC-09 | match_type preserved | Any match | match_type field | "perfect_whole" or "embedding_whole" |

### 4.4 Pretranslation Tests (`PretranslationEngine.pretranslate()`)

| ID | Test Case | File | TM | Expected Result | Verify |
|----|-----------|------|-----|-----------------|--------|
| PRE-01 | Standard engine | 5 rows | Standard TM | Matches found | matched_count > 0 |
| PRE-02 | StringID exact match | Row has StringID="UI_SAVE_BUTTON" | StringID TM | Returns "Save" | target == "Save" |
| PRE-03 | StringID different | Row has StringID="GAME_SAVE_MENU" | StringID TM | Returns "Save Game" | target == "Save Game" |
| PRE-04 | StringID no match | Row StringID not in TM | StringID TM | Returns all variations | Multiple options |
| PRE-05 | File without StringID | No string_id col | StringID TM | First/all variations | Fallback behavior |
| PRE-06 | Skip existing | Row has target | Any TM | Skipped | skipped_count > 0 |
| PRE-07 | Don't skip existing | skip_existing=False | Any TM | All processed | processed == total |
| PRE-08 | Threshold filter | 0.95 threshold | TM | Only high matches | All scores >= 0.95 |
| PRE-09 | XLS Transfer engine | File | XLS Transfer dict | Correct matching | Engine-specific logic |
| PRE-10 | KR Similar engine | File with ▶ | KR Similar dict | Triangle handling | Structure preserved |

### 4.5 API Endpoint Tests (`/api/ldm/pretranslate`)

| ID | Test Case | Request | Expected Response | Verify |
|----|-----------|---------|-------------------|--------|
| API-01 | Valid request | file_id, engine, dict_id | 200 OK | success=true |
| API-02 | Invalid file_id | file_id=999999 | 404 | File not found |
| API-03 | Invalid engine | engine="invalid" | 400 | Invalid engine |
| API-04 | Invalid dict_id | dict_id=999999 | 404 | Dictionary not found |
| API-05 | Missing params | No file_id | 422 | Validation error |
| API-06 | Response structure | Valid request | Correct JSON | total, matched, skipped |

### 4.6 Backward Compatibility Tests

| ID | Test Case | Input | Expected | Verify |
|----|-----------|-------|----------|--------|
| BC-01 | Standard TM still works | mode=standard | First-wins merging | Duplicates merged |
| BC-02 | Old PKL format | PKL without variations | Search still works | No errors |
| BC-03 | TM without mode | Existing TM, no mode col | Defaults to standard | Works normally |
| BC-04 | Entry without string_id | Entry with NULL string_id | Search returns it | string_id=null in result |

### 4.7 Edge Cases

| ID | Test Case | Input | Expected | Verify |
|----|-----------|-------|----------|--------|
| EDGE-01 | Empty TM | TM with 0 entries | Empty PKL | No crash |
| EDGE-02 | Unicode StringID | string_id="한글ID" | Stored correctly | Retrieved correctly |
| EDGE-03 | Very long StringID | 255 char string_id | Truncated/stored | No crash |
| EDGE-04 | Special chars in StringID | string_id with <>&'" | Escaped properly | No XSS/injection |
| EDGE-05 | Duplicate StringID | Same string_id, different source | Both stored | 2 entries |
| EDGE-06 | Case sensitivity | "UI_Save" vs "ui_save" | Treated as different | 2 entries |
| EDGE-07 | Whitespace StringID | "  UI_SAVE  " | Trimmed | string_id="UI_SAVE" |

---

## 5. E2E Test Script Structure

**File:** `tests/fixtures/pretranslation/test_e2e_stringid.py`

```python
"""
E2E Tests for StringID Mode

Tests:
1. TM Upload with StringID
2. Index building with variations
3. PKL structure verification
4. TMSearcher with variations
5. Pretranslation with StringID matching
"""

import pytest
from pathlib import Path

# Test data with duplicate sources
STRINGID_TEST_DATA = [
    {"string_id": "UI_SAVE_BUTTON", "source": "저장", "target": "Save"},
    {"string_id": "GAME_SAVE_MENU", "source": "저장", "target": "Save Game"},
    {"string_id": "FILE_STORAGE", "source": "저장", "target": "Storage"},
    # ... more test cases
]

class TestStringIDMode:
    """Test suite for StringID functionality."""

    def test_tm_upload_stringid(self):
        """Test TM upload with StringID mode stores all variations."""
        pass

    def test_index_build_variations(self):
        """Test index building creates variations structure in PKL."""
        pass

    def test_pkl_structure(self):
        """Verify PKL files have correct string_id metadata."""
        pass

    def test_search_returns_variations(self):
        """Test TMSearcher returns all variations for same source."""
        pass

    def test_pretranslate_with_stringid(self):
        """Test pretranslation uses StringID to select correct translation."""
        pass
```

---

## 6. Test Data Patterns (From Real Data + Expansion)

### 6.1 Patterns Found in sampleofLanguageData.txt

| Pattern Type | Example | Count | Extract Command |
|--------------|---------|-------|-----------------|
| **Color Codes** | `<PAColor0xffe9bd23>텍스트</PAOldColor>` | Many | `grep "PAColor" sampleofLanguageData.txt` |
| **TextBind** | `{TextBind:CLICK_ON_RMB_ONLY}` | Many | `grep "TextBind" sampleofLanguageData.txt` |
| **Newlines** | `\n` (literal) | Many | `grep "\\\\n" sampleofLanguageData.txt` |
| **Scale Tags** | `<Scale:1.2>텍스트</Scale>` | Some | `grep "Scale:" sampleofLanguageData.txt` |
| **Multiple Codes** | `<PAColor><TextBind>텍스트` | Some | Complex grep |

### 6.2 Color Code Test Cases

```python
# From real data - color codes with StringID
COLOR_CODE_TEST_DATA = [
    {
        "string_id": "ITEM_DESC_001",
        "source": "<PAColor0xffe9bd23>아이템 설명</PAOldColor>",
        "target": "<PAColor0xffe9bd23>Item Description</PAOldColor>"
    },
    {
        "string_id": "ITEM_DESC_002",
        "source": "<PAColor0xffe9bd23>아이템 설명</PAOldColor>",  # Same source, different target
        "target": "<PAColor0xffe9bd23>Item Info</PAOldColor>"
    },
    {
        "string_id": "NPC_DIALOGUE_001",
        "source": "<PAColor0xff0000>경고!</PAOldColor> 위험합니다",
        "target": "<PAColor0xff0000>Warning!</PAOldColor> Danger ahead"
    },
    # Multiple colors in same string
    {
        "string_id": "MULTI_COLOR_001",
        "source": "<PAColor0xff0000>빨강</PAOldColor> <PAColor0x00ff00>초록</PAOldColor>",
        "target": "<PAColor0xff0000>Red</PAColor> <PAColor0x00ff00>Green</PAOldColor>"
    },
]
```

### 6.3 TextBind Test Cases

```python
# TextBind patterns with StringID
TEXTBIND_TEST_DATA = [
    {
        "string_id": "KEYBIND_RMB",
        "source": "{TextBind:CLICK_ON_RMB_ONLY}를 눌러 공격",
        "target": "Press {TextBind:CLICK_ON_RMB_ONLY} to attack"
    },
    {
        "string_id": "KEYBIND_RMB_ALT",
        "source": "{TextBind:CLICK_ON_RMB_ONLY}를 눌러 공격",  # Same source
        "target": "{TextBind:CLICK_ON_RMB_ONLY} for attack"   # Different target
    },
    {
        "string_id": "KEYBIND_INTERACT",
        "source": "{TextBind:INTERACT}로 상호작용",
        "target": "{TextBind:INTERACT} to interact"
    },
    # Multiple bindings
    {
        "string_id": "MULTI_BIND_001",
        "source": "{TextBind:ATTACK} 공격, {TextBind:DEFEND} 방어",
        "target": "{TextBind:ATTACK} attack, {TextBind:DEFEND} defend"
    },
]
```

### 6.4 Newline Test Cases

```python
# Newline handling with StringID
NEWLINE_TEST_DATA = [
    {
        "string_id": "MULTILINE_001",
        "source": "첫 번째 줄\n두 번째 줄",
        "target": "First line\nSecond line"
    },
    {
        "string_id": "MULTILINE_002",
        "source": "첫 번째 줄\n두 번째 줄",  # Same multi-line source
        "target": "Line 1\nLine 2"           # Different translation
    },
    {
        "string_id": "MULTILINE_COMPLEX",
        "source": "제목\n\n본문 내용\n끝",
        "target": "Title\n\nBody content\nEnd"
    },
]
```

### 6.5 Complex Mixed Patterns

```python
# Real-world complex patterns combining multiple features
COMPLEX_TEST_DATA = [
    {
        "string_id": "COMPLEX_001",
        "source": "<PAColor0xffe9bd23>{TextBind:INTERACT}</PAOldColor>를 눌러\n상호작용",
        "target": "Press <PAColor0xffe9bd23>{TextBind:INTERACT}</PAOldColor>\nto interact"
    },
    {
        "string_id": "COMPLEX_002",
        "source": "<Scale:1.2><PAColor0xff0000>경고</PAOldColor></Scale>\n{TextBind:ESCAPE}로 취소",
        "target": "<Scale:1.2><PAColor0xff0000>Warning</PAOldColor></Scale>\n{TextBind:ESCAPE} to cancel"
    },
]
```

### 6.6 KR Similar Test Data (Triangle Markers)

**Note:** sampleofLanguageData.txt doesn't contain triangle markers (▶). Create these manually.

```python
# KR Similar specific - triangle markers
KR_SIMILAR_TEST_DATA = [
    {
        "string_id": "KRSIM_001",
        "source": "▶첫 번째 줄\n▶두 번째 줄",
        "target": "▶First line\n▶Second line"
    },
    {
        "string_id": "KRSIM_002",
        "source": "▶첫 번째 줄\n▶두 번째 줄",  # Same source
        "target": "▶Line one\n▶Line two"      # Different translation
    },
    # Triangle with tags
    {
        "string_id": "KRSIM_SCALE",
        "source": "▶<Scale:1.2>큰 텍스트</Scale>",
        "target": "▶<Scale:1.2>Large text</Scale>"
    },
    # Triangle with colors
    {
        "string_id": "KRSIM_COLOR",
        "source": "▶<PAColor0xff0000>빨간 텍스트</PAOldColor>",
        "target": "▶<PAColor0xff0000>Red text</PAOldColor>"
    },
]
```

### 6.7 XLS Transfer Test Data

```python
# XLS Transfer patterns - code preservation
XLS_TRANSFER_TEST_DATA = [
    # Code at start
    {
        "string_id": "XLS_CODE_START",
        "source": "<PAColor0xff0000>아이템</PAOldColor> 획득",
        "target": "<PAColor0xff0000>Item</PAOldColor> obtained"
    },
    # Code in middle
    {
        "string_id": "XLS_CODE_MIDDLE",
        "source": "당신은 <PAColor0xff0000>영웅</PAOldColor>입니다",
        "target": "You are a <PAColor0xff0000>hero</PAOldColor>"
    },
    # Multiple codes
    {
        "string_id": "XLS_MULTI_CODE",
        "source": "<PAColor0xff0000>빨강</PAOldColor>과 <PAColor0x00ff00>초록</PAOldColor>",
        "target": "<PAColor0xff0000>Red</PAOldColor> and <PAColor0x00ff00>Green</PAOldColor>"
    },
    # _x000D_ removal (Excel artifact)
    {
        "string_id": "XLS_X000D",
        "source": "첫줄_x000D_\n둘째줄",
        "target": "First_x000D_\nSecond"
    },
]
```

### 6.8 Full Test Data Set (Combined)

**Total Test Cases:** ~50+ covering all patterns

```python
ALL_STRINGID_TEST_DATA = (
    BASIC_STRINGID_DATA +      # 7 basic cases (저장, 설정, 확인)
    COLOR_CODE_TEST_DATA +     # 4 color code cases
    TEXTBIND_TEST_DATA +       # 4 textbind cases
    NEWLINE_TEST_DATA +        # 3 newline cases
    COMPLEX_TEST_DATA +        # 2 complex cases
    KR_SIMILAR_TEST_DATA +     # 4 KR Similar cases
    XLS_TRANSFER_TEST_DATA     # 4 XLS Transfer cases
)
# = ~28 test entries with duplicate sources for StringID testing
```

### 6.9 Extracting Real Data Samples

```bash
# Extract 50 rows with color codes (real data)
grep "PAColor" /mnt/c/.../sampleofLanguageData.txt | head -50 > color_samples.txt

# Extract 50 rows with TextBind (real data)
grep "TextBind" /mnt/c/.../sampleofLanguageData.txt | head -50 > textbind_samples.txt

# Extract rows with both color and textbind
grep "PAColor" /mnt/c/.../sampleofLanguageData.txt | grep "TextBind" | head -20 > complex_samples.txt

# Find duplicate Korean sources (for StringID testing)
cut -f6 sampleofLanguageData.txt | sort | uniq -d > duplicate_sources.txt

# Get full rows for duplicate sources
while read src; do
    grep -F "$src" sampleofLanguageData.txt
done < duplicate_sources.txt > duplicates_with_context.txt
```

---

## 7. Feature Testing Order (E2E One-by-One)

**Strategy:** Test each feature independently with its own E2E test file.

| Order | Feature | Test File | Tests | Status |
|-------|---------|-----------|-------|--------|
| **1** | TM Upload with StringID | `test_e2e_1_tm_upload.py` | 10/10 | ✅ **PASSED** |
| **2** | PKL Index Building | `test_e2e_2_pkl_index.py` | 8/8 | ✅ **PASSED** |
| **3** | TMSearcher Variations | `test_e2e_3_tm_search.py` | 9/9 | ✅ **PASSED** |
| **4** | Pretranslation StringID | `test_e2e_4_pretranslate.py` | 8/8 | ✅ **PASSED** |
| **5** | API Endpoints | (covered by existing tests) | - | ✅ Skipped |

**Total: 35 tests PASSED**

### Feature 1: TM Upload with StringID Mode

**What it tests:**
- `/api/ldm/tm/upload` endpoint with mode=stringid
- DB storage of string_id column
- TM mode column persistence
- All 3 formats: TXT, XML, Excel

**Test Cases:**
- TM-01 to TM-08 (8 tests)

**Expected Results:**
- All entries stored with string_id NOT NULL
- TM mode = "stringid"
- Count matches input (no merging)

---

### Feature 2: PKL Index Building with Variations

**What it tests:**
- `TMIndexer.build_indexes()` with StringID TM
- `_build_whole_lookup()` variations structure
- `_build_whole_embeddings()` string_id in mapping
- `_build_line_lookup()` and `_build_line_embeddings()`

**Test Cases:**
- IDX-01 to IDX-08 (8 tests)

**Expected Results:**
- `whole_lookup.pkl`: `{"저장": {"variations": [3 entries]}}`
- `whole_mapping.pkl`: Each entry has `string_id` field
- Line PKLs have string_id (if multi-line entries exist)

---

### Feature 3: TMSearcher with Variations

**What it tests:**
- `TMSearcher.search()` with variations structure
- Tier 1 (hash) returns all variations
- Tier 2 (embedding) includes string_id
- Result format with string_id field

**Test Cases:**
- SRC-01 to SRC-09 (9 tests)

**Expected Results:**
- Query "저장" → 3 results (variations)
- Each result has `string_id` field
- score and match_type preserved

---

### Feature 4: Pretranslation with StringID Matching

**What it tests:**
- `PretranslationEngine.pretranslate()` with StringID TM
- StringID exact match → correct translation
- No StringID match → all variations returned
- File without StringID → fallback behavior

**Test Cases:**
- PRE-01 to PRE-10 (10 tests)

**Expected Results:**
- Row with StringID="UI_SAVE_BUTTON" → target="Save"
- Row with StringID="GAME_SAVE_MENU" → target="Save Game"
- Unknown StringID → multiple options

---

### Feature 5: API Endpoint Integration

**What it tests:**
- `/api/ldm/pretranslate` endpoint
- Request validation
- Response format
- Error handling

**Test Cases:**
- API-01 to API-06 (6 tests)
- BC-01 to BC-04 (4 backward compat tests)
- EDGE-01 to EDGE-07 (7 edge cases)

**Expected Results:**
- 200 OK for valid requests
- Proper error codes for invalid
- Backward compatibility maintained

---

## 8. Implementation Steps

### Step 1: Create Test Fixture Generator
- [ ] Create `tests/fixtures/stringid/` directory
- [ ] Create `generate_fixtures.py` script
- [ ] Generate TXT, XML, Excel from test data
- [ ] Add real data samples from sampleofLanguageData.txt

### Step 2: Create E2E Tests (One per Feature)
- [ ] `test_e2e_1_tm_upload.py` - TM Upload
- [ ] `test_e2e_2_pkl_index.py` - PKL Building
- [ ] `test_e2e_3_tm_search.py` - TMSearcher
- [ ] `test_e2e_4_pretranslate.py` - Pretranslation
- [ ] `test_e2e_5_api.py` - API Endpoints

### Step 3: Run and Verify
- [ ] Run each test in order
- [ ] Fix any failures
- [ ] Document results

### Step 4: Integration
- [ ] Add to CI pipeline
- [ ] Update e2e_test_data.py with StringID cases

---

## 8. Success Criteria

| Metric | Target |
|--------|--------|
| TM Upload | All StringID entries stored correctly |
| PKL Structure | Variations format verified |
| Search | All variations returned for duplicate sources |
| Pretranslation | Correct translation selected by StringID |
| Backward Compat | Standard mode still works (first-wins) |

---

## 9. Files Affected

### New Files
- `tests/fixtures/stringid/` - StringID test fixtures
- `tests/fixtures/stringid/generate_fixtures.py` - Fixture generator
- `tests/fixtures/stringid/stringid_test_data.txt`
- `tests/fixtures/stringid/stringid_test_data.xml`
- `tests/fixtures/stringid/stringid_test_data.xlsx`
- `tests/fixtures/pretranslation/test_e2e_stringid.py`

### Modified Files
- `tests/fixtures/pretranslation/e2e_test_data.py` - Add StringID cases

---

## 10. Quick Reference: Data Extraction

```bash
# Extract sample rows from sampleofLanguageData.txt
head -100 /mnt/c/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/TestFilesForLocaNext/sampleofLanguageData.txt > sample_100.txt

# Find rows with color codes
grep "PAColor" sampleofLanguageData.txt | head -50 > color_code_samples.txt

# Find rows with TextBind
grep "TextBind" sampleofLanguageData.txt | head -50 > textbind_samples.txt

# Count unique StringIDs
cut -f2 sampleofLanguageData.txt | sort -u | wc -l
```

---

## 11. TRUE E2E TESTS (TODO)

**Current tests are SMALL (10 TM entries, 1-3 test rows). Need TRUE E2E with realistic data sizes.**

### Requirements for TRUE E2E

| Engine | TM Size | Test File | Description |
|--------|---------|-----------|-------------|
| **Standard TM** | ~5000 rows | ~150 rows | Full StringID variations testing |
| **XLS Transfer** | Own dictionary | ~150 rows | Color codes, TextBind preservation |
| **KR Similar** | Own dictionary | ~150 rows | Triangle markers, structure adaptation |

### Each Engine's TRUE E2E Steps

```
1. CREATE LARGE TM/DICTIONARY
   ├── Use sampleofLanguageData.txt (16MB) as base
   ├── 5000+ rows with realistic patterns
   ├── Include duplicate sources with different StringIDs
   └── Pattern types: color codes, TextBind, newlines, Korean

2. BUILD EMBEDDINGS/INDEXES
   ├── Run TMIndexer.build_indexes() or equivalent
   ├── Wait for completion (~5 min for 5000 rows)
   └── Verify PKL files have variations structure

3. CREATE TEST FILE TO PRETRANSLATE
   ├── 150+ rows (mix of exact match, similar, no-match)
   ├── Include rows with StringID that match TM entries
   ├── Include rows with StringID that DON'T match TM
   └── Include rows WITHOUT StringID (fallback test)

4. RUN PRETRANSLATION
   ├── Call PretranslationEngine.pretranslate()
   ├── Engine = "standard" | "xls_transfer" | "kr_similar"
   └── Record match count, time, etc.

5. VERIFY RESULTS
   ├── For each row with StringID: verify correct target
   ├── Example: Row string_id="UI_BUTTON_SAVE" → target="Save"
   ├── Example: Row string_id="UI_MENU_SAVE" → target="Save Game"
   └── Count matches, verify no incorrect targets
```

### Test Data Sources

```
/mnt/c/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/TestFilesForLocaNext/
├── sampleofLanguageData.txt     # 16MB - Use for TM creation
├── closetotest.txt              # Korean dialogue with ▶ markers (KR Similar)
└── [other test files]

Data Patterns:
├── Color codes: <PAColor0xffe9bd23>text</PAOldColor>
├── TextBind: {TextBind:INTERACT}
├── Newlines: \n (literal)
├── Triangle markers: ▶ (KR Similar)
└── Scale tags: <Scale:1.2>text</Scale>
```

### Test Files to Create

```
tests/fixtures/stringid/
├── true_e2e_standard.py       # Standard TM with 5000 rows
├── true_e2e_xls_transfer.py   # XLS Transfer dictionary
├── true_e2e_kr_similar.py     # KR Similar dictionary
└── fixtures/
    ├── large_tm_standard.xlsx # 5000 rows for Standard TM
    ├── large_dict_xls.pkl     # Pre-built XLS Transfer dictionary
    ├── large_dict_kr.pkl      # Pre-built KR Similar dictionary
    ├── test_file_150.txt      # 150 rows to pretranslate
    └── expected_results.json  # Expected targets for verification
```

### Verification Method

```python
def verify_pretranslation_results(file_id: int, expected: dict):
    """
    Verify each row got the correct target based on StringID.

    expected = {
        1: {"string_id": "UI_BUTTON_SAVE", "expected_target": "Save"},
        2: {"string_id": "UI_MENU_SAVE", "expected_target": "Save Game"},
        3: {"string_id": "TECH_STORAGE", "expected_target": "Storage"},
        # ... 150 rows
    }
    """
    rows = db.query(LDMRow).filter(LDMRow.file_id == file_id).all()
    errors = []

    for row in rows:
        exp = expected.get(row.row_num)
        if exp and row.target != exp["expected_target"]:
            errors.append(
                f"Row {row.row_num}: StringID='{row.string_id}' "
                f"expected='{exp['expected_target']}', got='{row.target}'"
            )

    assert len(errors) == 0, f"Found {len(errors)} incorrect targets:\n" + "\n".join(errors)
```

---

*Last updated: 2025-12-17 15:30 KST*
