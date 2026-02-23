# WIP: QuickTranslate GUI Reorganization

> **Status:** PRE-REWORK (all bug fixes done, review findings documented)
> **Created:** 2026-02-23
> **Last updated:** 2026-02-23
> **Priority:** HIGH
> **Scope:** GUI restructuring, new features, UX improvements

---

## 1. Vision

Reorganize QuickTranslate from a single flat scrollable panel into a **tab-based layout** that separates primary translation workflows from secondary helper tools. This makes the main screen cleaner, reduces cognitive overload, and creates a scalable structure for future features.

### Before vs After

```
BEFORE (Current)                          AFTER (Target)
┌──────────────────┬──────┐              ┌──────────────────────────┬──────┐
│ Match Type       │      │              │ [Main] [Helper Functions]│      │
│ Files            │ Log  │              ├──────────────────────────┤      │
│ Quick Actions    │      │              │ Match Type (3 types)     │ Log  │
│ Pre-Submission   │      │              │ Files                    │      │
│ Settings         │      │              │ Pre-Submission Checks    │      │
│                  │      │              │ Settings                 │      │
└──────────────────┴──────┘              └──────────────────────────┴──────┘
  6 sections, cluttered                    Clean main tab, extras in tabs
  Substring Match confuses users           Substring Match hidden from main
  Quick Actions rarely used                Quick Actions → Helper Functions
  No room for new features                 Extensible tab system
```

---

## 2. Current GUI Layout (Reference)

The GUI is a **single-window PanedWindow** split 65/35 (controls | log):

| Section | Location | Usage Frequency |
|---------|----------|-----------------|
| **Match Type** (4 radio buttons + precision/fuzzy/scope) | Left pane, top | HIGH (core feature) |
| **Files** (Source + Target browse) | Left pane | HIGH (always needed) |
| **Quick Actions** (StringID Lookup, Reverse Lookup, Find Missing) | Left pane | LOW (rarely used) |
| **Pre-Submission Checks** (Korean, Patterns, Quality, Check ALL) | Left pane | HIGH (used before every submission) |
| **Settings** (LOC Path, Export Path) | Left pane, bottom | LOW (set once) |
| **Log + Progress** | Right pane | ALWAYS VISIBLE |

### Match Types (Current)

| Match Type | Purpose | Usage | Keep in Main? |
|------------|---------|-------|---------------|
| **Substring Match** | Lookup only, finds Korean in StrOrigin | Almost never used | NO - move out |
| **StringID-Only (SCRIPT)** | Match by StringID in Dialog/Sequencer | Frequently used | YES |
| **Strict (StringID + StrOrigin)** | Both must match exactly | Frequently used | YES |
| **StrOrigin Only** | Match by StrOrigin text only | Frequently used | YES |

**Key insight:** Substring Match is lookup-only (no TRANSFER), rarely used, and confuses users by being selected by default. It should be removed from the main Match Type section entirely.

---

## 3. Reorganization Plan

### 3.1 Tab System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  QuickTranslate                    [Clear Log] [Clear All] [Exit]│
├─────────────────────────────────────────────────────────────────┤
│  [  Main  ] [ Helper Functions ]                                 │
├────────────────────────────┬────────────────────────────────────┤
│                            │                                     │
│   TAB CONTENT AREA         │   LOG + PROGRESS                    │
│   (scrollable, 65%)        │   (always visible, 35%)             │
│                            │                                     │
└────────────────────────────┴────────────────────────────────────┘
```

**Implementation:** Use `ttk.Notebook` widget inside the left pane. The right pane (Log + Progress) stays **outside** the tab system and is always visible regardless of which tab is selected.

### 3.2 Main Tab (Translation Workflow)

Everything needed for the primary Generate/Transfer workflow:

```
┌─ Main Tab ──────────────────────────────────┐
│                                              │
│  ┌─ Match Type ───────────────────────────┐  │
│  │  ◎ StringID-Only (SCRIPT)              │  │
│  │  ◎ StringID + StrOrigin (Strict)       │  │
│  │  ◎ StrOrigin Only                      │  │
│  │  [Precision options when applicable]    │  │
│  │  [Transfer scope when applicable]       │  │
│  └────────────────────────────────────────┘  │
│                                              │
│  ┌─ Files ────────────────────────────────┐  │
│  │  Source: [...........................] 📁│  │
│  │  Target: [...........................] 📁│  │
│  └────────────────────────────────────────┘  │
│                                              │
│  ┌─ Pre-Submission Checks ────────────────┐  │
│  │  [Check Korean] [Patterns] [Quality]   │  │
│  │  [Check ALL]          [Open Results]   │  │
│  │  ☑ Skip staticinfo:knowledge entries   │  │
│  └────────────────────────────────────────┘  │
│                                              │
│  ┌─ Settings ─────────────────────────────┐  │
│  │  LOC Path: [..........................] 📁│  │
│  │  Export:   [..........................] 📁│  │
│  │  [Save Settings]                       │  │
│  └────────────────────────────────────────┘  │
│                                              │
│         [Generate]           [TRANSFER]       │
└──────────────────────────────────────────────┘
```

**Changes from current:**
- Substring Match **removed** from match type radio buttons
- Quick Actions **removed** (moved to Helper Functions tab)
- Default selection: **StringID-Only** (most common workflow)
- Generate/Transfer buttons stay in top bar (always accessible)

### 3.3 Helper Functions Tab

Secondary tools that don't need to clutter the main workflow:

```
┌─ Helper Functions ──────────────────────────┐
│                                              │
│  ┌─ Quick Actions ──────────────── [?] ───┐  │
│  │                                         │  │
│  │  StringID Lookup                        │  │
│  │  [________________] [Lookup]            │  │
│  │  Find all translations for a StringID   │  │
│  │                                         │  │
│  │  Reverse Lookup                         │  │
│  │  [________________] [📁] [Find All]     │  │
│  │  Find all language translations in file │  │
│  │                                         │  │
│  │  Substring Search                       │  │
│  │  [________________] [Search]            │  │
│  │  Find Korean text in StrOrigin fields   │  │
│  │  (uses source files as search base)     │  │
│  │                                         │  │
│  │  Find Missing Translations              │  │
│  │  [Find Missing...] [Exclude: 5] ⚙      │  │
│  │  Korean entries in target not in source  │  │
│  └─────────────────────────────────────────┘  │
│                                              │
│  ┌─ String Erase ─────────────────────────┐  │
│  │                                         │  │
│  │  Source (keys to erase):                │  │
│  │  [________________] [📁] 📁=folder      │  │
│  │  Supports: XML languagedata, Excel      │  │
│  │                                         │  │
│  │  Target (files to erase from):          │  │
│  │  [________________] [📁] 📁=folder      │  │
│  │  Supports: XML languagedata files       │  │
│  │                                         │  │
│  │  Match by: (StringID + StrOrigin)       │  │
│  │  ☑ Recursive folder scanning            │  │
│  │                                         │  │
│  │  [Erase Matching Strings]               │  │
│  │  Clears Str="" for matched entries      │  │
│  └─────────────────────────────────────────┘  │
│                                              │
└──────────────────────────────────────────────┘
```

**Key features:**
- **Quick Actions** moved here with all existing functionality preserved
- **Substring Match** transformed into "Substring Search" action (not a match mode)
- **String Erase** integrated as new feature (reuses existing source/target XML/Excel logic)
- **[?] Help button** next to Quick Actions header opens user guide popup

### 3.4 Substring Match Handling

**Current problem:** Substring Match is one of 4 match types but behaves completely differently:
- Lookup only (no Transfer)
- Rarely used
- Selected by default (confusing for new users)
- Disables the Transfer button when selected

**Solution:** Remove it from the match type radio group entirely. Repackage it as "Substring Search" in the Quick Actions section on the Helper Functions tab. This:
- Simplifies the main Match Type to 3 clear options (all support Generate + Transfer)
- Makes Substring Search explicitly a lookup tool
- Eliminates the confusing "Transfer disabled" state

**Migration path:**
1. Remove `"substring"` from match type radios on Main tab
2. Change default match type to `"stringid_only"`
3. Add "Substring Search" action to Quick Actions on Helper Functions tab
4. Reuse existing `generate()` logic with `match_type="substring"` internally

---

## 4. New Features

### 4.1 String Erase (Integrated from Standalone Script)

**What:** Erase (clear) Str values in target XML files when StringID + StrOrigin match source files.

**Why:** Already built as standalone script (`QuickStandaloneScripts/string_eraser_xml.py`). Integrating it into QuickTranslate gives users one tool for all XML translation operations.

**How it works:**
1. User selects source files/folder (Excel or XML with StringID + StrOrigin columns)
2. User selects target folder (languagedata XML files)
3. Tool builds key set from source: `(StringID.lower(), normalized_StrOrigin)`
4. For each target XML LocStr element, if key matches → set `Str=""`
5. Writes modified XML back, reports what was erased

**Reuses from QuickTranslate:**
- Source file loading (Excel + XML parsing already exists)
- StrOrigin normalization (`normalize_text`, `normalize_nospace`)
- XML reading/writing
- Log panel and progress bar
- Threading infrastructure

**Implementation:** Create `core/string_eraser.py` that adapts logic from `string_eraser_xml.py`, wired to GUI via existing worker thread pattern.

### 4.2 Long String Extraction (Integrated from Standalone Script)

**What:** Extract SCRIPT-type (Dialog/Sequencer) LocStr entries above a configurable character length threshold. Outputs Excel report.

**Why:** Already built as standalone script (`QuickStandaloneScripts/script_long_string_extractor.py`). Integrating into QuickTranslate's Helper Functions tab gives users direct access alongside other tools.

**How it works:**
1. Uses export folder (already configured in Settings) to build StringID → Category mapping
2. Scans source XML/Excel files for LocStr entries
3. Filters: only SCRIPT categories (Dialog/Sequencer) + visible char count >= threshold
4. Outputs sorted Excel report (longest strings first)

**Reuses from QuickTranslate:**
- Export folder path (already in config/settings)
- `build_stringid_to_category()` from `language_loader.py`
- XML parsing, Excel reading infrastructure
- Log panel, threading, progress bar

### 4.3 Transfer Length Threshold Filter

**What:** Optional minimum character length filter on TRANSFER operations. When enabled, only corrections whose target `Str` value has >= N visible characters get applied.

**Why:** Allows users to selectively transfer only long strings (e.g. dialog lines) while skipping short UI labels. Useful when corrections were generated in bulk but only long narrative text needs updating.

**How it works:**
1. New optional spinbox in Transfer settings area (default: OFF / 0 = no filter)
2. When set to e.g. 50, the merge functions (`merge_corrections_to_xml`, `_merge_excel_*`) skip entries where the **existing** target `Str` value has fewer visible chars than the threshold
3. Skipped entries reported as `SKIPPED_SHORT` in the result details
4. Works alongside existing SCRIPT filter — both filters apply independently

**Implementation:** Add `min_char_length` parameter to merge functions. Check `visible_char_count(existing_str)` before applying correction. GUI adds optional spinbox to transfer settings.

### 4.4 Help Button [?] → User Guide Popup

**What:** A small `[?]` button next to the "Quick Actions" label that opens a popup window with contextual help.

**Popup content:**
- Brief description of each Quick Action with examples
- Tips for when to use each one
- Link/reference to full USER_GUIDE.md

**Implementation:**
- `tk.Toplevel` window (~400x500px)
- Styled text with headers and examples
- Can load content from bundled USER_GUIDE.md or hardcoded help text
- Non-modal (user can keep it open while working)

```
┌─ Quick Actions Help ──────────── [X] ─┐
│                                        │
│  StringID Lookup                       │
│  ─────────────────                     │
│  Enter a StringID to find all its      │
│  translations across languages.        │
│                                        │
│  Example: STR_QUEST_001_TITLE          │
│  → Shows EN, KR, JP, etc. values       │
│                                        │
│  Reverse Lookup                        │
│  ──────────────                        │
│  Select an XML file to see ALL         │
│  language translations for every       │
│  entry in that file.                   │
│                                        │
│  Substring Search                      │
│  ────────────────                      │
│  Search for Korean text within         │
│  StrOrigin fields. Useful for finding  │
│  where specific Korean text appears.   │
│                                        │
│  Find Missing Translations             │
│  ────────────────────────              │
│  Compares target against source to     │
│  find Korean entries that have no      │
│  corresponding source translation.     │
│                                        │
│  ──────────────────────────────        │
│  Full guide: QuickTranslate_UserGuide  │
└────────────────────────────────────────┘
```

---

## 5. Implementation Tasks

### Phase 1: Tab Infrastructure (Foundation)

| # | Task | Details | Risk |
|---|------|---------|------|
| 1.1 | Add `ttk.Notebook` to left pane | Replace direct `_left_inner` content with notebook containing "Main" and "Helper Functions" tabs. Log/progress pane stays outside notebook. | LOW - structural change but isolated |
| 1.2 | Move existing sections to Main tab | Match Type, Files, Pre-Submission, Settings → Main tab frame. Should look identical to current layout minus Quick Actions. | LOW - just reparenting widgets |
| 1.3 | Move Quick Actions to Helper Functions tab | Reparent `quick_frame` and all its children to Helper Functions tab. | LOW |
| 1.4 | Test all existing functionality | Every button, every mode, log output, progress bar, cancel — must work exactly as before. | MEDIUM - regression risk |

### Phase 2: Substring Match Relocation

| # | Task | Details | Risk |
|---|------|---------|------|
| 2.1 | Remove Substring from match type radios | Remove the "substring" radiobutton from Main tab. Change default to "stringid_only". | LOW |
| 2.2 | Add Substring Search to Quick Actions | New entry in Quick Actions with text input + Search button. Internally calls `generate()` with `match_type="substring"`. | MEDIUM - need to decouple from radio state |
| 2.3 | Clean up Transfer button logic | Transfer button no longer needs "disabled for substring" logic since substring is gone from Main. | LOW |
| 2.4 | Update `_on_match_type_change()` | Remove substring-specific branches. Simplify enable/disable logic. | LOW |

### Phase 3: Bug Fixes (From Code Reviews 2026-02-23)

> All 3A/3B/3C bugs fixed and committed. Phase 3D documents new findings from the 6-agent post-fix review.

#### 3A. URGENT — ALL DONE ✅

| # | Task | Status |
|---|------|--------|
| 3A.1 | Column shift after `_insert_str_column` corrupts reads | **DONE** ✅ `d0ba2ffc` |
| 3A.2 | `_generate()` silently fails for StrOrigin Only | **DONE** ✅ `d0ba2ffc` |
| 3A.3 | Remove StrOrigin requirement for StringID-Only mode | **DONE** ✅ `d0ba2ffc` |
| 3A.4 | Recovery pass uses STRICT merge for StringID-only NOT_FOUND | **DONE** ✅ `d0ba2ffc` |
| 3A.5 | Auto-detect EventNames in StringID column | **DONE** ✅ `d0ba2ffc` |
| 3A.6 | SCRIPT filter skips EventNames as "Uncategorized" | **DONE** ✅ `5da55030` |
| 3A.7 | StringID-only NOT_FOUND report misleading when target StrOrigin empty | **DONE** ✅ `d0ba2ffc` |

#### 3B. IMPORTANT — ALL DONE ✅

| # | Task | Status |
|---|------|--------|
| 3B.1 | STRICT XML merge dict overwrites duplicate corrections | **DONE** ✅ `31ce29b2` |
| 3B.2 | `_merge_excel_strict` target lookup overwrites duplicates | **DONE** ✅ `31ce29b2` |
| 3B.3 | StrOrigin Only Excel merge: corrections dict overwrites duplicates | **DONE** ✅ `31ce29b2` |
| 3B.4 | Diagnostic maps overwrite on duplicate StringIDs | **DONE** ✅ `9bd940f5` |

#### 3C. SHOULD FIX — ALL DONE ✅ (except 3C.6 deferred)

| # | Task | Status |
|---|------|--------|
| 3C.1 | Inconsistent attribute case variants (xml_io.py 4→6) | **DONE** ✅ `9bd940f5` |
| 3C.2 | `_fix_bad_entities` double-escapes numeric entities | **DONE** ✅ `9bd940f5` |
| 3C.3 | Hallucination phrase "tradu" false positives | **DONE** ✅ `9bd940f5` |
| 3C.4 | Exit button bypasses `_on_close` cleanup | **DONE** ✅ `9bd940f5` |
| 3C.5 | Duplicate `iter_locstr_elements` implementations | **DONE** ✅ `9bd940f5` |
| 3C.6 | `or` chain treats empty string `""` as missing | DEFERRED — no real-world impact |
| 3C.7 | Column detection only triggers via Browse button | **DONE** ✅ `9bd940f5` |
| 3C.8 | `LANGUAGE_ORDER` never refreshed after settings change | **DONE** ✅ `9bd940f5` |
| 3C.9 | `traceback.print_exc()` should use logger | **DONE** ✅ `9bd940f5` |

#### 3D. POST-FIX REVIEW FINDINGS (6-Agent Review, 2026-02-23)

> **None of these break core transfer logic.** All transfer modes (StringID-only, Strict, StrOrigin-only, Fuzzy) work correctly. These are polish/robustness items to fix before or during the GUI rework.

##### 3D-CRITICAL (report/robustness issues, NOT transfer-breaking)

| # | File | Issue | Impact |
|---|------|-------|--------|
| 3D.C1 | `xml_transfer.py:854` | `by_category["not_found"]` incremented for BOTH NOT_FOUND and SKIPPED_EMPTY_STRORIGIN — inflates per-category not_found count | Report cosmetics only. Top-level counter is correct. Fix: guard `by_category` increment with `if status == "NOT_FOUND"`. |
| 3D.C2 | `xml_transfer.py:577` | `skipped_empty_strorigin` counter not initialized in result dict, never aggregated in `transfer_folder_to_folder()`, never displayed in `format_transfer_report()`, classified as "OTHER" in `failure_report.py` | Report cosmetics. New status is invisible to user. Fix: init counter, add aggregation, add report line, add to failure_report classifier. |
| 3D.C3 | `excel_io.py:1037` | `_merge_excel_stringid_only` filters out rows with empty `str_origin` — drops ALL rows when target has no StrOrigin column (allowed by 3A.3 fix) | Edge case: Excel-to-Excel StringID-only when target lacks StrOrigin col. XML transfer unaffected. Fix: remove `if not entry["str_origin"].strip(): continue` filter in `_merge_excel_stringid_only`. |
| 3D.C4 | `xml_parser.py:117` | Line 117 attribute-value ampersand regex `&[^ltgapoqu]` corrupts `&#nnn;` entities inside attribute values. Also clobbers ALL `&` in matched attribute via global `.replace("&", "&amp;")`. Line 107's `_fix_bad_entities` already handles this correctly. | Rare XML edge case. Fix: remove lines 116-118 entirely (redundant with line 107). |
| 3D.C5 | `missing_translation_finder.py`, `indexing.py`, `language_loader.py`, `category_mapper.py` | Still use 4 StringId variants (missing `Stringid`, `stringId`). Only `xml_io.py` and `checker.py` have full 6 variants. | Only matters if XML uses unusual casing. Fix: centralize constants in `xml_parser.py` and import everywhere. |
| 3D.C6 | `config.py:272` | `reload_settings()` does NOT re-discover languages — missing `LANGUAGE_ORDER, LANGUAGE_NAMES` from globals declaration, no call to `_discover_languages_from_loc()` | Dead code path (never called currently). Fix: add globals + re-discovery to match `update_settings()`. |

##### 3D-WARNING (quality/robustness, low priority)

| # | File | Issue | Impact |
|---|------|-------|--------|
| 3D.W1 | `excel_io.py:1019` | Uses `from core.eventname_resolver` (absolute import) instead of `from .eventname_resolver` (relative). Works only when run from project root. | Import style. Fix: change to relative import. |
| 3D.W2 | `app.py:1826` | `_quick_detect_columns` doesn't close workbook on exception — potential file handle leak on Windows | Fix: wrap in try/finally for `wb.close()`. |
| 3D.W3 | `app.py:1820` | Imports private `_detect_column_indices` from `core.excel_io` — fragile, breaks if renamed | Fix: use public `detect_excel_columns()` API instead. |
| 3D.W4 | `app.py:1857+2760` | Duplicated 24-line column validation block in `_generate()` and `_transfer()` | Fix: extract to `_validate_columns_for_mode()` helper. |
| 3D.W5 | `source_scanner.py` | `_cached_valid_codes` never cleared when LOC folder changes — `clear_language_code_cache()` exists but is never called | Fix: call `clear_language_code_cache()` in `_save_settings()` in app.py. |
| 3D.W6 | `language_loader.py`, `indexing.py` | Have their own `_iter_locstr_case_insensitive` copies instead of using `xml_parser.iter_locstr_elements` | Fix: delegate to `xml_parser` like `missing_translation_finder.py` does. |
| 3D.W7 | `missing_translation_finder.py:131-164` | Has its own `_parse_xml_file` that duplicates `xml_parser.parse_xml_file` (with minor differences: returns None, latin-1 fallback) | Low priority. Could consolidate but has intentional differences. |
| 3D.W8 | `xml_transfer.py` (5+ locations) | Duplicated LocStr tag search + attribute access patterns — same `locstr_tags` list and `loc.get("StringId") or loc.get("StringID") or ...` chain repeated in many functions | Fix during GUI rework: centralize in `xml_parser.py` helpers. |
| 3D.W9 | `xml_transfer.py` | Recovery pass re-parses and rewrites target XML a second time (first pass already wrote it) | Performance note. Not a bug. Acceptable for correctness. |

##### 3D-STANDALONE (Script Long String Extractor fixes)

| # | Issue | Status |
|---|-------|--------|
| 3D.S1 | `visible_char_count` missing PAOldColor, Scale, color, Style, \n, {code} tags | **DONE** ✅ `83d5133d` |
| 3D.S2 | NarrationDialog subfolder not excluded | **DONE** ✅ `83d5133d` |
| 3D.S3 | Excel language regex fails for hyphenated codes (ZHO-CN) | TODO |
| 3D.S4 | Excel row index not bounds-checked (IndexError on sparse sheets) | TODO |
| 3D.S5 | `build_stringid_to_category` silently swallows all exceptions | **DONE** ✅ `83d5133d` (added logger.warning) |
| 3D.S6 | `IntVar.get()` TclError not caught when spinbox has invalid input | TODO |
| 3D.S7 | Missing Str column check — returns 0 results with no explanation | TODO |

### Phase 4: String Erase Integration

| # | Task | Details | Risk |
|---|------|---------|------|
| 4.1 | Create `core/string_eraser.py` | Port logic from `QuickStandaloneScripts/string_eraser_xml.py`. Adapt to use QuickTranslate's existing normalize functions and XML utilities. | LOW - logic already proven |
| 4.2 | Add String Erase section to Helper Functions tab | Source/Target file pickers, recursive checkbox, Erase button. | LOW |
| 4.3 | Wire to worker thread | Use existing `_run_in_thread()` pattern for async execution. Show progress in shared log/progress bar. | LOW |
| 4.4 | Add erase report output | Summary of erased entries written to log + optional export file. | LOW |

### Phase 4B: Long String Extraction & Transfer Length Filter

| # | Task | Details | Risk |
|---|------|---------|------|
| 4B.1 | Add Long String Extraction to Helper Functions tab | Spinbox for min length, uses existing export folder from settings, Extract button. Standalone version: `QuickStandaloneScripts/script_long_string_extractor.py` | LOW - logic proven in standalone |
| 4B.2 | Create `core/long_string_extractor.py` | Port extraction logic, reuse `build_stringid_to_category` from `language_loader.py` and `visible_char_count` helper. | LOW |
| 4B.3 | Add Transfer length threshold filter | Optional `min_char_length` spinbox in Transfer settings. Merge functions skip entries where existing target Str < threshold. New status: `SKIPPED_SHORT`. | LOW-MEDIUM |
| 4B.4 | Add `visible_char_count()` to shared helpers | Strip `<br/>`, PAColor tags, HTML entities, then count. Used by both extraction and transfer filter. | LOW |

### Phase 5: Help Button & Guide Popup

| # | Task | Details | Risk |
|---|------|---------|------|
| 5.1 | Add [?] button to Quick Actions header | Small button next to "Quick Actions" LabelFrame label. | LOW |
| 5.2 | Create help popup `Toplevel` window | Non-modal window with styled help text for each Quick Action. | LOW |
| 5.3 | Load help content from USER_GUIDE.md or hardcoded | Decide: parse markdown at runtime or maintain separate help strings. Hardcoded is simpler and more reliable. | LOW |

### Phase 6: Polish & Testing

| # | Task | Details | Risk |
|---|------|---------|------|
| 6.1 | Keyboard navigation | Tab switching via Ctrl+1/Ctrl+2. Focus management within tabs. | LOW |
| 6.2 | Remember last active tab | Persist in settings.json which tab was active. Restore on startup. | LOW |
| 6.3 | Window resize behavior | Ensure notebook tabs resize properly with window. Test minimum window size. | MEDIUM |
| 6.4 | Full regression test | Test every feature end-to-end in both tabs. | HIGH priority |
| 6.5 | Update USER_GUIDE.md | Document new tab layout, String Erase feature, help button. | LOW |
| 6.6 | Build and verify installer | Ensure PyInstaller bundles correctly, Inno Setup works. | MEDIUM |

---

## 6. Extensibility Design

The tab system is designed to grow:

```
Current Plan:
  [Main] [Helper Functions]

Future (if needed):
  [Main] [Helper Functions] [Advanced]
  [Main] [Helper Functions 1] [Helper Functions 2]
  [Main] [Helpers] [Batch Operations] [Reports]
```

**Rules for adding new tabs:**
1. Core translation workflow (Generate/Transfer) always stays on Main
2. Pre-submission checks stay on Main (used before every submission)
3. Lookup/search tools → Helper Functions
4. New standalone features → Helper Functions (or new tab if too crowded)
5. If Helper Functions gets too full → split into numbered tabs or themed tabs

**Adding a new tab (developer guide):**
```python
# In gui/app.py, inside _build_gui():
new_tab = ttk.Frame(self.notebook)
self.notebook.add(new_tab, text="New Feature")
# Build widgets on new_tab frame
self._build_new_feature_section(new_tab)
```

---

## 7. Technical Notes

### File Changes Required

| File | Change |
|------|--------|
| `gui/app.py` | Major: add Notebook, reparent widgets, new String Erase section, help popup |
| `core/string_eraser.py` | NEW: port from standalone script |
| `config.py` | Minor: remove `"substring"` from default match type, add String Erase defaults |
| `docs/USER_GUIDE.md` | Update: document new tab layout, String Erase, help button |
| `QuickTranslate.spec` | Verify: no changes expected (no new data files) |

### Shared State Across Tabs

The Log panel and Progress bar are **shared** across all tabs (they live outside the Notebook widget in the right pane). This means:
- String Erase operations show progress in the same log
- Quick Actions results appear in the same log
- Cancel button works for any running operation regardless of active tab
- Only one operation can run at a time (existing `_worker_thread` constraint)

### Source/Target Reuse for String Erase

String Erase can optionally reuse the Source/Target paths from the Main tab's Files section:
- If user already set Source/Target on Main → auto-populate in String Erase section
- String Erase can also have independent Source/Target fields
- **Decision needed during implementation:** share paths or keep independent

---

## 8. Success Criteria

### Bug Fixes (Phase 3A/3B/3C) — ALL DONE ✅

- [x] Column shift after `_insert_str_column` fixed ✅ `d0ba2ffc`
- [x] `_generate()` handles StrOrigin Only match type ✅ `d0ba2ffc`
- [x] StringID-Only mode works without StrOrigin column ✅ `d0ba2ffc`
- [x] EventName recovery uses correct merge mode ✅ `d0ba2ffc`
- [x] Auto-detect EventNames when no EventName column ✅ `d0ba2ffc`
- [x] SKIPPED_EMPTY_STRORIGIN instead of misleading NOT_FOUND ✅ `d0ba2ffc`
- [x] SCRIPT filter resolves EventNames before skipping ✅ `5da55030`
- [x] StringID-Only Excel transfer updates ALL matching rows ✅ `8a1f19bd`
- [x] STRICT merge handles duplicate corrections ✅ `31ce29b2`
- [x] `_merge_excel_strict` handles duplicate target rows ✅ `31ce29b2`
- [x] StrOrigin Only Excel merge logs conflicting corrections ✅ `31ce29b2`
- [x] Diagnostic maps keep first occurrence ✅ `9bd940f5`
- [x] Attribute case variants unified in xml_io.py ✅ `9bd940f5`
- [x] Hallucination phrases use full phrases (no "tradu") ✅ `9bd940f5`
- [x] Exit button calls `_on_close` cleanup ✅ `9bd940f5`
- [x] Column detection works for pasted paths ✅ `9bd940f5`
- [x] `LANGUAGE_ORDER` refreshed on settings change ✅ `9bd940f5`
- [x] `traceback.print_exc()` replaced with `logger.exception()` ✅ `9bd940f5`
- [x] Numeric entity regex fixed ✅ `9bd940f5`
- [x] Duplicate `iter_locstr_elements` consolidated ✅ `9bd940f5`

### Post-Fix Review (Phase 3D) — TODO before or during GUI rework

- [ ] 3D.C1-C6: 6 critical-level polish items (report cosmetics, consistency)
- [ ] 3D.W1-W9: 9 warning-level quality items (imports, duplication, caching)
- [ ] 3D.S3-S7: 4 standalone extractor minor fixes

### GUI Reorganization (Phases 1-2, 4-6) — NOT STARTED

- [ ] Main tab contains only: Match Type (3 options), Files, Pre-Submission Checks, Settings
- [ ] Helper Functions tab contains: Quick Actions (with Substring Search), String Erase
- [ ] Substring Match removed from main Match Type radios
- [ ] Default match type is StringID-Only (not Substring)
- [ ] String Erase works with XML and Excel source files
- [ ] [?] help button shows contextual guide popup
- [ ] Log and Progress visible from all tabs
- [ ] All existing functionality preserved (zero regression)
- [ ] Generate and Transfer buttons work from Main tab
- [ ] Tab state persisted across sessions
- [ ] USER_GUIDE.md updated to reflect new layout

---

## 9. Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| ~~Column shift bug corrupts transfers silently~~ | ~~CRITICAL~~ | ✅ FIXED `d0ba2ffc` |
| ~~StrOrigin Only generate produces empty output~~ | ~~CRITICAL~~ | ✅ FIXED `d0ba2ffc` |
| ~~Dict-overwrite bugs in other merge modes~~ | ~~HIGH~~ | ✅ FIXED `31ce29b2` |
| Widget reparenting breaks layout | HIGH | Phase 1 is purely structural — test before adding features |
| Substring Search decoupled from radio state causes bugs | MEDIUM | Keep internal `match_type` parameter, just change how it's triggered |
| String Erase logic diverges from standalone script | LOW | Port directly, keep standalone as reference |
| Users confused by layout change | MEDIUM | Help button, clear tab labels, update user guide |
| Window too small for Notebook tabs | LOW | Test minimum size, ensure graceful scroll |
| 3D.C3 Excel StringID-only drops all rows when target has no StrOrigin | MEDIUM | Fix before GUI rework. Only affects Excel-to-Excel, not XML transfer. |

---

## 10. Implementation Order (Updated 2026-02-23)

```
COMPLETED ✅:
  Phase 3A → All 7 urgent bugs fixed (d0ba2ffc)
  Phase 3B → All 4 dict-overwrite bugs fixed (31ce29b2, 9bd940f5)
  Phase 3C → All 9 robustness fixes done (9bd940f5), 3C.6 deferred

NEXT — Fix before or during GUI rework:
  Phase 3D → 6 critical polish items (3D.C1-C6) + 9 warnings (3D.W1-W9)
             None break transfer. All are report/quality/consistency fixes.
             Can be done as part of Phase 1 refactoring.

THEN (GUI rework):
  Phase 1  → Tab infrastructure (Notebook widget, reparent widgets)
  Phase 2  → Substring match relocation (Main → Helper Functions)
  Phase 4  → String Erase integration
  Phase 4B → Long String Extraction integration + Transfer length filter
  Phase 5  → Help button
  Phase 6  → Polish & testing
```

---

*Last updated: 2026-02-23 (all Phase 3 fixes done, 6-agent review findings documented as Phase 3D)*
