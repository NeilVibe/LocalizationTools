# Other Tools Tab — Converter Buttons Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add 5 quick-action converter buttons to QuickTranslate's "Other Tools" tab: XML→Excel, Excel→XML, TMX→Excel, Excel→TMX, and Concatenate XML.

**Architecture:** New `core/converters.py` module with 5 standalone functions. Each function takes a file/folder path and an output path, performs the conversion, returns a result summary. GUI adds a new "Quick Converters" LabelFrame to Tab 2 with file/folder mode toggle and 5 action buttons. Reuses existing patterns from `tmx_tools.py` (TMX↔Excel) and `tmxtransfer11.py` (XML↔Excel reference).

**Tech Stack:** lxml (XML parsing), xlsxwriter (Excel write), openpyxl (Excel read), tkinter (GUI), threading (background ops)

**Existing code to reuse:**
- `tmx_tools.clean_and_convert_to_excel()` → TMX→Excel (already exists)
- `tmx_tools.excel_to_memoq_tmx()` → Excel→TMX (already exists)
- `tmx_tools.combine_xmls_to_tmx()` → reference for XML folder walking
- `tmxtransfer11.py xml_to_excel()` → reference pattern for XML→Excel
- `tmxtransfer11.py excel_to_xml()` → reference pattern for Excel→XML
- `tmxconvert41.py concatenate_all_xmls_to_single_xml()` → exact logic to port

---

### Task 1: Create `core/converters.py` — XML→Excel, Excel→XML, Concatenate XML

**Files:**
- Create: `RessourcesForCodingTheProject/NewScripts/QuickTranslate/core/converters.py`

These 3 functions are new. The TMX↔Excel functions already exist in tmx_tools.py and will be called directly from the GUI.

- [ ] **Step 1: Create converters.py with xml_to_excel()**

Reads all XML files from a folder (or single file), extracts `<LocStr>` attributes, writes to Excel with columns: StrOrigin, Str, StringId, DescOrigin, Desc (+ any extra attributes found).

- [ ] **Step 2: Add excel_to_xml()**

Reads Excel (openpyxl), maps columns back to `<LocStr>` attributes, writes XML. Columns: StrOrigin→StrOrigin, Str→Str, StringId→StringId, DescOrigin→DescOrigin, Desc→Desc.

- [ ] **Step 3: Add concatenate_xmls()**

Walks folder recursively, finds all .xml files, extracts all `<LocStr>` elements, merges into single output XML under `<root>`. Port from tmxconvert41.py `concatenate_all_xmls_to_single_xml()`.

- [ ] **Step 4: Syntax check**

- [ ] **Step 5: Commit**

---

### Task 2: Add "Quick Converters" section to Other Tools tab GUI

**Files:**
- Modify: `RessourcesForCodingTheProject/NewScripts/QuickTranslate/gui/app.py`

- [ ] **Step 1: Add converter UI section after Extract Translations**

New LabelFrame "Quick Converters" with:
- File/Folder mode toggle (radio buttons)
- Input path row with Browse button
- 5 action buttons in 2 rows:
  - Row 1: XML→Excel, Excel→XML, Concatenate XML
  - Row 2: TMX→Excel, Excel→TMX
- Concatenate XML button only enabled in Folder mode

- [ ] **Step 2: Add browse and action handler methods**

- [ ] **Step 3: Syntax check all modified files**

- [ ] **Step 4: Commit**

---

### Task 3: Review + Build trigger

- [ ] **Step 1: Code review**
- [ ] **Step 2: Commit + push + trigger CI build**
