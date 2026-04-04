# TMX Tools Tab — QuickTranslate Integration Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status:** Completed (2026-03-21)

**Goal:** Add a "TMX Tools" tab (Tab 3) to QuickTranslate with MemoQ-TMX conversion (single + batch) and TMX Cleaner → Excel export.

**Architecture:** Two new files — `core/tmx_tools.py` (all business logic ported from tmxconvert41.py + tmx_cleaner.py) and `gui/tmx_tools_tab.py` (Tab 3 GUI). Minor wiring changes to `gui/app.py` and `core/__init__.py`.

**Tech Stack:** Python 3, tkinter, lxml, xlsxwriter, openpyxl (all already in QuickTranslate)

**Spec:** `docs/superpowers/specs/2026-03-21-tmx-tools-quicktranslate-design.md`

---

### Task 1: Create `core/tmx_tools.py` — TMX Cleaning Logic

**Files:**
- Create: `RessourcesForCodingTheProject/NewScripts/QuickTranslate/core/tmx_tools.py`

Port the cleaning regex engine from `tmx_cleaner.py`. This is Section 1 of the module.

- [ ] **Step 1: Create tmx_tools.py with all compiled regex patterns**

Port all regex patterns from `QuickStandaloneScripts/tmx_cleaner.py` lines 18-117. Include `from __future__ import annotations` per project rules.

Patterns to include:
- `ZERO_WIDTH_RE`
- `MEMOQ_BPT_EPT_ESCAPED_RE` (StaticInfo with &quot; quotes)
- `MEMOQ_BPT_EPT_PLAIN_RE` (StaticInfo with plain " quotes)
- `GENERIC_BPT_EPT_RE`
- `PH_RE`, `PH_SELFCLOSE_RE`, `PH_FMT_RE`
- `IT_RE`, `X_RE`, `G_RE`
- `FORMATTING_CONTENT_RE`
- `BR_VARIANTS_RE`
- `SEG_RE`

- [ ] **Step 2: Add `clean_segment()` and `clean_tmx_string()` functions**

Port from `tmx_cleaner.py` lines 126-218. The `clean_segment()` function has the 5-priority `_ph_repl` and `_staticinfo_repl` with `.strip()` on category/ident captures.

- [ ] **Step 3: Verify cleaning logic works**

Run from QuickTranslate directory:
```bash
cd RessourcesForCodingTheProject/NewScripts/QuickTranslate
python3 -c "
from core.tmx_tools import clean_segment
# Test StaticInfo:Item (was broken before)
result = clean_segment('<bpt i=\"1\">&lt;mq:rxt-req displaytext=\"{Miner_PlateArmor_Helm\" val=\"{StaticInfo:Item:Miner_PlateArmor_Helm#\"&gt;</bpt>광부의 랜턴 모자<ept i=\"1\">&lt;/mq:rxt-req displaytext=\"}\" val=\"}\"&gt;</ept>')
assert result == '{StaticInfo:Item:Miner_PlateArmor_Helm#광부의 랜턴 모자}', f'Got: {result}'
print('PASS')
"
```
Expected: `PASS`

- [ ] **Step 4: Commit**

```bash
git add RessourcesForCodingTheProject/NewScripts/QuickTranslate/core/tmx_tools.py
git commit -m "feat(QuickTranslate): add core/tmx_tools.py — TMX cleaning engine"
```

---

### Task 2: Add MemoQ Postprocessing to `core/tmx_tools.py` (FIXED)

**Files:**
- Modify: `RessourcesForCodingTheProject/NewScripts/QuickTranslate/core/tmx_tools.py`

Port `postprocess_tmx_string()` from tmxconvert41.py with the 5 fixes from the spec.

- [ ] **Step 1: Add `postprocess_tmx_string()` with all fixes applied**

Port from `tmxconvert41.py` lines 207-322 with these changes:

**Fix 1** — Line 235: Change `r'\{Staticinfo:Knowledge:([^#}]+)#([^}]+)\}'` to `r'\{Static[Ii]nfo:(\w+):([^#}]+)#([^}]+)\}'` (3 capture groups now: category, ident, inner). **Also update `sk_repl`** to use new group numbering: `category, ident, inner_txt = m.group(1), m.group(2), m.group(3)`

**Fix 2** — Lines 249-257: Change `mq:rxt` to `mq:rxt-req` in BOTH bpt AND ept. Change ept `</mq:rxt` to `</mq:rxt-req`.

**Fix 3** — Line 252: Change hardcoded `Staticinfo:Knowledge:{ident}` to `StaticInfo:{category}:{ident}` using the captured category group.

**Fix 4** — Line 278: Change `r'\{(?!Staticinfo:Knowledge:)([^}]+)\}'` to `r'\{(?!Static[Ii]nfo:\w+:)([^}]+)\}'`

**Fix 5** — Line 318: Keep `content.rstrip()` (NOT strip() — preserve intentional leading spaces)

- [ ] **Step 2: Verify postprocessor fixes**

```bash
cd RessourcesForCodingTheProject/NewScripts/QuickTranslate
python3 -c "
from core.tmx_tools import postprocess_tmx_string
# Test StaticInfo:Item gets wrapped in bpt/ept
tmx = '<seg>{StaticInfo:Item:Sword_01#검}</seg>'
result = postprocess_tmx_string(tmx)
assert 'mq:rxt-req' in result, f'Missing mq:rxt-req in: {result}'
assert 'StaticInfo:Item:Sword_01#' in result, f'Missing Item category in: {result}'
assert '</mq:rxt-req' in result, f'ept not updated to mq:rxt-req: {result}'
print('PASS: StaticInfo:Item wrapped correctly')

# Test generic {placeholder} still works
tmx2 = '<seg>{Name} says hello</seg>'
result2 = postprocess_tmx_string(tmx2)
assert 'mq:rxt-req' in result2
assert 'val=\"{Name}\"' in result2
print('PASS: Generic placeholder works')

# Test trailing whitespace stripped
tmx3 = '<seg>Hello World   </seg>'
result3 = postprocess_tmx_string(tmx3)
assert result3.endswith('Hello World</seg>'), f'Trailing space not stripped: {result3}'
print('PASS: Trailing whitespace stripped')
"
```

- [ ] **Step 3: Commit**

```bash
git add RessourcesForCodingTheProject/NewScripts/QuickTranslate/core/tmx_tools.py
git commit -m "feat(QuickTranslate): add postprocess_tmx_string with StaticInfo fixes"
```

---

### Task 3: Add Conversion Pipeline to `core/tmx_tools.py`

**Files:**
- Modify: `RessourcesForCodingTheProject/NewScripts/QuickTranslate/core/tmx_tools.py`

Port `combine_xmls_to_tmx()`, `batch_tmx_from_folders()`, and helper functions from tmxconvert41.py.

- [ ] **Step 1: Add helper functions**

Port from tmxconvert41.py:
- `is_korean()` (line ~200 area — or reuse `core.korean_detection.is_korean_text`)
- `replace_newlines_text()` (line 133-141)
- `get_all_xml_files()` (line 172-178)
- `parse_xml_file()` (line 180-200)

**Important:** Reuse `from core.korean_detection import is_korean_text` instead of duplicating `is_korean()`.

- [ ] **Step 2: Add `combine_xmls_to_tmx()`**

Port from tmxconvert41.py lines 473-664. Use `is_korean_text` from core instead of local `is_korean`.

- [ ] **Step 3: Add `batch_tmx_from_folders()`**

Port from tmxconvert41.py lines 667-693.

- [ ] **Step 4: Commit**

```bash
git add RessourcesForCodingTheProject/NewScripts/QuickTranslate/core/tmx_tools.py
git commit -m "feat(QuickTranslate): add TMX conversion pipeline to tmx_tools"
```

---

### Task 4: Add TMX → Excel Pipeline to `core/tmx_tools.py`

**Files:**
- Modify: `RessourcesForCodingTheProject/NewScripts/QuickTranslate/core/tmx_tools.py`

Port TMX → Excel from tmx_cleaner.py with simplified output columns.

- [ ] **Step 1: Add `parse_tmx_to_rows()`, `dedup_rows()`, `write_excel()`, `clean_and_convert_to_excel()`**

Port from tmx_cleaner.py lines 340-510 with these changes to `write_excel()`:

**Simplified output — only 3 merge-ready columns:**
```python
headers = ['StrOrigin', 'Correction', 'StringID']
keys = ['ko_seg', 'tgt_seg', 'x_context']
```

Column widths: StrOrigin=60, Correction=60, StringID=30.

Note: `parse_tmx_to_rows()` still extracts all metadata internally (changedate needed for dedup), but `write_excel()` only outputs the 3 columns the user needs for merge. Keep `dedup_rows()` with the x-context warning for >50% empty.

- [ ] **Step 2: Add `detect_encoding()` and `read_file()` helpers**

Port from tmx_cleaner.py lines 222-238.

- [ ] **Step 3: Verify Excel output**

```bash
cd RessourcesForCodingTheProject/NewScripts/QuickTranslate
python3 -c "
from core.tmx_tools import dedup_rows
rows = [
    {'x_context': '123', 'ko_seg': 'hello', 'changedate': '20260318T060909Z', 'tgt_seg': 'A'},
    {'x_context': '123', 'ko_seg': 'hello', 'changedate': '20260319T060909Z', 'tgt_seg': 'B'},
]
result = dedup_rows(rows)
assert len(result) == 1
assert result[0]['tgt_seg'] == 'B', 'Should keep latest changedate'
print('PASS: Dedup keeps latest')
"
```

- [ ] **Step 4: Commit**

```bash
git add RessourcesForCodingTheProject/NewScripts/QuickTranslate/core/tmx_tools.py
git commit -m "feat(QuickTranslate): add TMX→Excel pipeline with 3-column output"
```

---

### Task 5: Create `gui/tmx_tools_tab.py` — Tab 3 GUI

**Files:**
- Create: `RessourcesForCodingTheProject/NewScripts/QuickTranslate/gui/tmx_tools_tab.py`

- [ ] **Step 1: Create the tab GUI module**

Build the TMX Tools tab following the same scrollable canvas pattern used by Tab 1 and Tab 2 in `gui/app.py` (lines 296-334).

The tab has 2 sections:

**Section 1: MemoQ-TMX Conversion**
- Source folder selector (label + button + path display)
- Target language dropdown (hardcoded TMX language map — same as tmxconvert41.py)
- Two buttons: "Convert Single" and "Batch Convert"

**Section 2: TMX Cleaner → Excel**
- Single button: "Select TMX → Clean & Export to Excel"

All operations use `threading.Thread(daemon=True)` and log via `logging.getLogger(__name__)`.

The tab class: `TMXToolsTab(tk.Frame)` — takes `parent` (notebook frame) and `log_callback` (optional, for status messages).

Language options: Hardcode the TMX language map directly in the tab module (TMX uses BCP-47 codes like `en-US` which differ from QuickTranslate's `config.LANGUAGE_NAMES` codes). This is the same map from tmxconvert41.py:
```python
TMX_LANGUAGE_OPTIONS = {
    "English (US)": "en-US", "French (FR)": "fr-FR", "German (DE)": "de-DE",
    "Traditional Chinese (TW)": "zh-TW", "Simplified Chinese (CN)": "zh-CN",
    "Japanese (JP)": "ja-JP", "Italian (IT)": "it-IT", "Portuguese (Brazil)": "pt-BR",
    "Russian (RU)": "ru-RU", "European Spanish (ES)": "es-ES",
    "Latin American Spanish (MX)": "es-MX", "Polish (PL)": "pl-PL", "Turkish (TR)": "tr-TR",
}
```
Note: TMX BCP-47 codes differ from QuickTranslate's internal codes so this is intentionally separate.

- [ ] **Step 2: Implement button handlers**

Each handler:
1. Opens file/folder dialog
2. Validates selection
3. Spawns thread calling the appropriate `core.tmx_tools` function
4. Shows messagebox on completion (via `self.after(0, ...)`)

For batch: reuse the subfolder picker pattern from tmxconvert41.py (Toplevel with Listbox + EXTENDED select mode).

- [ ] **Step 3: Commit**

```bash
git add RessourcesForCodingTheProject/NewScripts/QuickTranslate/gui/tmx_tools_tab.py
git commit -m "feat(QuickTranslate): add TMX Tools tab GUI"
```

---

### Task 6: Wire Tab 3 into QuickTranslate

**Files:**
- Modify: `RessourcesForCodingTheProject/NewScripts/QuickTranslate/gui/app.py`
- Modify: `RessourcesForCodingTheProject/NewScripts/QuickTranslate/core/__init__.py`

- [ ] **Step 1: Add Tab 3 to app.py notebook**

After Tab 2 block (after line 334), add Tab 3 following the exact same canvas+scrollbar pattern:

```python
# --- Tab 3: TMX Tools ---
tab3_frame = tk.Frame(self._notebook, bg='#f0f0f0')
self._notebook.add(tab3_frame, text="TMX Tools")
# ... canvas + scrollbar setup identical to tab1/tab2 ...
```

Import and instantiate `TMXToolsTab` inside the tab3 inner frame.

- [ ] **Step 2: Add tmx_tools exports to core/__init__.py**

Add at the bottom of `core/__init__.py`:
```python
from .tmx_tools import (
    clean_segment,
    clean_tmx_string,
    postprocess_tmx_string,
    combine_xmls_to_tmx,
    batch_tmx_from_folders,
    clean_and_convert_to_excel,
)
```

And add to `__all__`.

- [ ] **Step 3: Test import chain**

```bash
cd RessourcesForCodingTheProject/NewScripts/QuickTranslate
python3 -c "from core.tmx_tools import clean_segment, postprocess_tmx_string, combine_xmls_to_tmx, clean_and_convert_to_excel; print('All imports OK')"
```

- [ ] **Step 4: Commit**

```bash
git add RessourcesForCodingTheProject/NewScripts/QuickTranslate/gui/app.py RessourcesForCodingTheProject/NewScripts/QuickTranslate/core/__init__.py
git commit -m "feat(QuickTranslate): wire TMX Tools as Tab 3"
```

---

### Task 7: End-to-End Verification

**Files:** None (testing only)

- [ ] **Step 1: Run against real data**

Test the cleaner against the FULL CLEANUP FAIL LIST:
```bash
cd RessourcesForCodingTheProject/NewScripts/QuickTranslate
python3 -c "
import openpyxl
from core.tmx_tools import clean_segment
import re
wb = openpyxl.load_workbook('../QuickStandaloneScripts/FULL CLEANUP FAIL LIST.xlsx', read_only=True)
ws = wb.active
rows = list(ws.iter_rows(values_only=True))
wb.close()
TAG_RE = re.compile(r'<(?:bpt|ept|ph|it|g|x)\b[^>]*>')
problems = 0
total = 0
for row in rows[1:]:
    for val in row:
        if val and isinstance(val, str) and '<' in val:
            total += 1
            cleaned = clean_segment(str(val))
            if TAG_RE.findall(cleaned):
                problems += 1
print(f'{total} cells tested, {problems} problems')
assert problems == 0, f'{problems} cells still have leftover tags!'
print('ALL CLEAN')
"
```

- [ ] **Step 2: Verify app launches without errors**

```bash
cd RessourcesForCodingTheProject/NewScripts/QuickTranslate
python3 -c "from core import tmx_tools; print('All tmx_tools imports OK')"
python3 -c "from gui.tmx_tools_tab import TMXToolsTab; print('GUI tab import OK')"
```

- [ ] **Step 3: Final commit**

```bash
git add -A RessourcesForCodingTheProject/NewScripts/QuickTranslate/
git commit -m "test(QuickTranslate): verify TMX Tools tab end-to-end"
```
