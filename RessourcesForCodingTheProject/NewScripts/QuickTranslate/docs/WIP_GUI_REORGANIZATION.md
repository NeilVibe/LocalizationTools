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
│  ┌─ XML Diff / Revert ─────────── ⭐ ────┐  │
│  │                                         │  │
│  │  [DIFF] [REVERT]  ← sub-tabs           │  │
│  │                                         │  │
│  │  ── DIFF mode ──                        │  │
│  │  Source (old): [_______________] [📁]   │  │
│  │  Target (new): [_______________] [📁]   │  │
│  │  [Run Diff]                             │  │
│  │  → Extracts ADD + EDIT LocStr as raw XML│  │
│  │                                         │  │
│  │  ── REVERT mode ──                      │  │
│  │  Before (good):  [_______________] [📁] │  │
│  │  After (bad):    [_______________] [📁] │  │
│  │  Current (fix):  [_______________] [📁] │  │
│  │  [Run Revert]                           │  │
│  │  → Removes ADDs, restores EDITs in-place│  │
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

### 4.5 XML Diff / Revert (Integrated from Standalone Script) ⭐ HIGH VALUE

**What:** Two-in-one tool:
- **DIFF:** Compare SOURCE (old) vs TARGET (new) XML, extract all ADD/EDIT LocStr elements as raw XML. Works exactly like WinMerge but for LocStr — anything that changed gets extracted.
- **REVERT:** Undo changes that occurred between BEFORE/AFTER in a CURRENT file. ADDs get removed, EDITs get restored to the BEFORE version.

**Why:** This is the **most useful** standalone tool for integration. Every localization workflow involves comparing XML versions — after a patch, after a merge, after a handoff. Currently users must either run the standalone script or manually diff in WinMerge. Having it inside QuickTranslate's Helper Functions tab means zero context-switching.

**Standalone script:** `QuickStandaloneScripts/xml_diff_extractor.py`

**Diff output format:**
```xml
<root>
  <LocStr StringId="STR_001" StrOrigin="..." Str="..." KR="..." />
  <LocStr StringId="STR_002" StrOrigin="..." Str="..." KR="..." />
</root>
```
No XML declaration, no extra attributes, no comments. Just raw LocStr under `<root>`.

**How DIFF works:**
1. Parse both XML files → build StringId → attrs maps
2. Compare: new StringIds = ADD, changed attrs = EDIT
3. Write all ADD + EDIT LocStr to output XML (raw, no decoration)
4. Report: X added, Y edited, Z deleted (deleted = info only, not extracted)

**How REVERT works:**
1. Parse BEFORE, AFTER, CURRENT XML files
2. Diff BEFORE vs AFTER → identify ADDs and EDITs
3. In CURRENT: remove ADDs, restore EDITs to BEFORE version (Str attribute)
4. Write CURRENT back in-place

**Reuses from QuickTranslate:**
- XML sanitization (`sanitize_xml` — handles `<br/>`, bare `&`, malformed tags)
- XML parsing infrastructure (lxml with fallback to stdlib)
- Attribute handling and `<br/>` preservation
- Log panel, threading, progress bar
- File browse dialogs

**Implementation:** Create `core/xml_diff.py` that adapts logic from `xml_diff_extractor.py`. Two sub-sections in Helper Functions tab — Diff panel and Revert panel (or a sub-notebook within the tab, matching the standalone's two-tab layout).

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

#### 3D. POST-FIX REVIEW FINDINGS — ALL DONE ✅

> All items fixed in `d5fd896a`. 4 review agents verified. W7-W9 deferred (intentional differences / GUI rework scope / not a bug).

##### 3D-CRITICAL — ALL DONE ✅

| # | File | Issue | Status |
|---|------|-------|--------|
| 3D.C1 | `xml_transfer.py` | `by_category["not_found"]` inflated by SKIPPED_EMPTY_STRORIGIN | **DONE** ✅ `d5fd896a` |
| 3D.C2 | `xml_transfer.py` + `failure_report.py` | `skipped_empty_strorigin` counter invisible to user | **DONE** ✅ `d5fd896a` |
| 3D.C3 | `excel_io.py` | StringID-only Excel merge drops rows when target has no StrOrigin | **DONE** ✅ `d5fd896a` |
| 3D.C4 | `xml_parser.py` | Redundant `&` regex corrupts `&#nnn;` entities | **DONE** ✅ `d5fd896a` |
| 3D.C5 | 5 files | StringId variants not centralized (4 instead of 6) | **DONE** ✅ `d5fd896a` |
| 3D.C6 | `config.py` | `reload_settings()` doesn't re-discover languages | **DONE** ✅ `d5fd896a` |

##### 3D-WARNING — ALL DONE ✅ (W7-W9 deferred)

| # | File | Issue | Status |
|---|------|-------|--------|
| 3D.W1 | `excel_io.py` | Absolute import instead of relative | **DONE** ✅ `d5fd896a` |
| 3D.W2 | `app.py` | File handle leak in `_quick_detect_columns` | **DONE** ✅ `d5fd896a` (uses public API now) |
| 3D.W3 | `app.py` | Imports private `_detect_column_indices` | **DONE** ✅ `d5fd896a` (uses `detect_excel_columns()`) |
| 3D.W4 | `app.py` | Duplicated 24-line column validation block | **DONE** ✅ `d5fd896a` (`_validate_columns_for_mode()`) |
| 3D.W5 | `app.py` | `_cached_valid_codes` never cleared on LOC change | **DONE** ✅ `d5fd896a` |
| 3D.W6 | `language_loader.py`, `indexing.py` | Duplicate `_iter_locstr_case_insensitive` copies | **DONE** ✅ `d5fd896a` |
| 3D.W7 | `missing_translation_finder.py` | Duplicate `_parse_xml_file` | DEFERRED — intentional differences (latin-1 fallback) |
| 3D.W8 | `xml_transfer.py` | Duplicated LocStr tag search patterns | DEFERRED — scope for GUI rework |
| 3D.W9 | `xml_transfer.py` | Recovery pass re-parses XML twice | DEFERRED — not a bug, acceptable for correctness |

##### 3D-STANDALONE — ALL DONE ✅

| # | Issue | Status |
|---|-------|--------|
| 3D.S1 | `visible_char_count` missing tag types | **DONE** ✅ `83d5133d` |
| 3D.S2 | NarrationDialog subfolder not excluded | **DONE** ✅ `83d5133d` |
| 3D.S3 | Excel language regex fails for hyphenated codes (ZHO-CN) | **DONE** ✅ `d5fd896a` |
| 3D.S4 | Excel row index not bounds-checked | **DONE** ✅ `d5fd896a` |
| 3D.S5 | `build_stringid_to_category` silently swallows exceptions | **DONE** ✅ `83d5133d` |
| 3D.S6 | `IntVar.get()` TclError not caught | **DONE** ✅ `d5fd896a` |
| 3D.S7 | Missing Str column check | **DONE** ✅ `d5fd896a` |

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

### Phase 4C: XML Diff / Revert Integration ⭐

| # | Task | Details | Risk |
|---|------|---------|------|
| 4C.1 | Create `core/xml_diff.py` | Port diff + revert logic from `QuickStandaloneScripts/xml_diff_extractor.py`. Reuse QuickTranslate's `sanitize_xml` and XML parsing. | LOW - logic proven in standalone |
| 4C.2 | Add Diff/Revert section to Helper Functions tab | Sub-tabs (or toggle) for DIFF vs REVERT mode. Source/Target pickers for diff, Before/After/Current pickers for revert. | LOW |
| 4C.3 | Wire diff output to log + file | Show summary in shared log (X added, Y edited, Z deleted). Write raw XML output to timestamped file next to target. | LOW |
| 4C.4 | Wire revert to worker thread | In-place revert is destructive — show confirmation dialog before applying. Report removed/reverted counts in log. | LOW-MEDIUM |

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

## 7. Standalone Scripts → QuickTranslate Integration Map

All standalone scripts live in `QuickStandaloneScripts/`. The table below shows which ones are candidates for integration into QuickTranslate's Helper Functions tab and their value.

| Script | What It Does | Integration Value | Phase | Status |
|--------|-------------|-------------------|-------|--------|
| **xml_diff_extractor.py** | DIFF: extract ADD/EDIT LocStr between two XMLs. REVERT: undo changes in-place. | ⭐ **HIGHEST** — used in every patch/merge/handoff cycle | 4C | PLANNED |
| **string_eraser_xml.py** | Erase (clear Str) in target XMLs for matching StringID+StrOrigin entries | HIGH — common cleanup operation | 4 | PLANNED |
| **script_long_string_extractor.py** | Extract SCRIPT-type LocStr above character length threshold (Excel+XML output) | MEDIUM — useful for QA review of long dialog strings | 4B | PLANNED |
| **file_eraser_by_name.py** | Move files from target folder when filename matches source folder | LOW — file-level operation, not LocStr-level. Better as standalone. | — | NO INTEGRATION |

### Why Diff is the Highest Value

Every localization workflow hits these scenarios:
1. **Patch received** → "What changed between v1 and v2?" → DIFF
2. **Bad merge happened** → "Undo the damage from that merge" → REVERT
3. **Handoff review** → "Show me only the LocStr that were touched" → DIFF
4. **Regression check** → "Did this update break anything?" → DIFF output feeds into QuickTranslate's main TRANSFER workflow

The diff output (raw LocStr XML under `<root>`) can be directly used as a QuickTranslate source file for further translation/transfer operations. This creates a powerful pipeline: **DIFF → review → TRANSFER**.

---

## 8. Technical Notes

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

## 9. Success Criteria

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

### Post-Fix Review (Phase 3D) — ALL DONE ✅

- [x] 3D.C1-C6: 6 critical-level polish items ✅ `d5fd896a`
- [x] 3D.W1-W6: 6 warning-level quality items ✅ `d5fd896a` (W7-W9 deferred)
- [x] 3D.S3-S7: 4 standalone extractor fixes ✅ `d5fd896a`

### GUI Reorganization (Phases 1-2, 4-6) — NOT STARTED

- [ ] Main tab contains only: Match Type (3 options), Files, Pre-Submission Checks, Settings
- [ ] Helper Functions tab contains: Quick Actions (with Substring Search), String Erase
- [ ] Substring Match removed from main Match Type radios
- [ ] Default match type is StringID-Only (not Substring)
- [ ] String Erase works with XML and Excel source files
- [ ] XML Diff extracts raw ADD/EDIT LocStr under `<root>` (no decoration)
- [ ] XML Revert removes ADDs and restores EDITs in-place with confirmation
- [ ] [?] help button shows contextual guide popup
- [ ] Log and Progress visible from all tabs
- [ ] All existing functionality preserved (zero regression)
- [ ] Generate and Transfer buttons work from Main tab
- [ ] Tab state persisted across sessions
- [ ] USER_GUIDE.md updated to reflect new layout

---

## 10. Risk Assessment

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
| ~~3D.C3 Excel StringID-only drops all rows when target has no StrOrigin~~ | ~~MEDIUM~~ | ✅ FIXED `d5fd896a` |

---

## 11. Implementation Order (Updated 2026-02-25)

```
COMPLETED ✅:
  Phase 3A → All 7 urgent bugs fixed (d0ba2ffc)
  Phase 3B → All 4 dict-overwrite bugs fixed (31ce29b2, 9bd940f5)
  Phase 3C → All 9 robustness fixes done (9bd940f5), 3C.6 deferred
  Phase 3D → All 19 polish/quality items fixed (d5fd896a), W7-W9 deferred

NEXT (GUI rework):
  Phase 1  → Tab infrastructure (Notebook widget, reparent widgets)
  Phase 2  → Substring match relocation (Main → Helper Functions)
  Phase 4  → String Erase integration
  Phase 4B → Long String Extraction integration + Transfer length filter
  Phase 4C → XML Diff / Revert integration ⭐ HIGH VALUE
  Phase 5  → Help button
  Phase 6  → Polish & testing
```

---

*Last updated: 2026-02-25 (added XML Diff/Revert integration plan + standalone scripts integration map)*
