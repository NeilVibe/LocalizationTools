# WIP: QuickTranslate GUI Reorganization

> **Status:** PLANNING
> **Created:** 2026-02-23
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

### Phase 3: Bug Fixes (CRITICAL — From Code Review 2026-02-23)

> **8 review agents audited the entire codebase.** Bugs below are categorized by urgency.

#### 3A. URGENT — Fix Before Next Build

| # | Task | Details | Status |
|---|------|---------|--------|
| 3A.1 | **Column shift after `_insert_str_column` corrupts reads** | `excel_io.py`. When target Excel has no "Str" column, `_insert_str_column()` shifts columns right but `stringid_col` and `strorigin_col` are NOT updated. **Fix:** After insert, increment any `*_col` variable `>= str_col`. | **DONE** ✅ |
| 3A.2 | **`_generate()` silently fails for StrOrigin Only** | `app.py`. The `work()` function has `if/elif/elif` for substring, stringid_only, strict — but **no branch for strorigin_only**. Falls through silently. **Fix:** Added `elif match_type == "strorigin_only":` branch. | **DONE** ✅ |
| 3A.3 | **Remove StrOrigin requirement for StringID-Only mode** | `excel_io.py`. Rejects Excel targets missing StrOrigin column even in StringID-only mode. **Fix:** StrOrigin only required for strict/strorigin_only, optional for stringid_only. | **DONE** ✅ |
| 3A.4 | **Recovery pass uses STRICT merge for StringID-only NOT_FOUND** | `xml_transfer.py`. EventName recovery called STRICT merge which requires StrOrigin match. **Fix:** Added `original_merge_mode` param, uses `merge_corrections_stringid_only` when original was stringid_only. | **DONE** ✅ |
| 3A.5 | **Auto-detect EventNames in StringID column** | When no EventName column, StringIDs not in category index are auto-tagged as `_source_eventname` for pre-merge resolution. **Fix:** `_no_eventname_col` flag in excel_io + auto-detect in transfer pipeline before EventName resolution. | **DONE** ✅ |
| 3A.6 | **SCRIPT filter skips EventNames as "Uncategorized"** | Multi-pass: before skipping as non-SCRIPT, try resolving as EventName via keyword extraction + export lookup. | **DONE** ✅ `5da55030` |
| 3A.7 | **StringID-only NOT_FOUND report is misleading when target StrOrigin is empty** | Golden Rule skips LocStr with empty StrOrigin but reports as "NOT_FOUND". **Fix:** Built `target_stringids_all` set from ALL LocStr, reports `SKIPPED_EMPTY_STRORIGIN` instead of `NOT_FOUND` when StringID exists but StrOrigin is empty. | **DONE** ✅ |

#### 3B. IMPORTANT — Fix Soon (Same Class of Bug as StringID Duplicate)

| # | Task | Details | Status |
|---|------|---------|--------|
| 3B.1 | **STRICT XML merge dict overwrites duplicate corrections** | `xml_transfer.py` — `correction_lookup` used plain dict. Multiple corrections with same (StringID, StrOrigin) lost all but last. Inflated NOT_FOUND count. **Fix:** `defaultdict(list)`, mark ALL as matched. | **DONE** ✅ `31ce29b2` |
| 3B.2 | **`_merge_excel_strict` target lookup overwrites duplicates** | `excel_io.py` — `target_lookup` used plain dict. Duplicate target rows with same (StringID, StrOrigin) lost all but last. **Fix:** `defaultdict(list)`, iterate all matching entries. | **DONE** ✅ `31ce29b2` |
| 3B.3 | **StrOrigin Only Excel merge: corrections dict overwrites duplicates** | `excel_io.py` — `correction_lookup` had no conflict detection (XML version had it). **Fix:** Added conflict detection + warning logging. | **DONE** ✅ `31ce29b2` |
| 3B.4 | **Diagnostic maps overwrite on duplicate StringIDs** | `excel_io.py` line 747 + `xml_transfer.py` line 146. `target_strorigin_map[sid.lower()] = so` — when multiple rows share a StringID, mismatch diagnostics show the wrong StrOrigin. Misleading error messages. **Fix:** Store list or keep first occurrence. | TODO |

#### 3C. SHOULD FIX — Correctness & Robustness

| # | Task | Details | Risk |
|---|------|---------|------|
| 3C.1 | **Inconsistent attribute case variants between xml_io.py and xml_transfer.py** | `xml_io.py` checks 4 StringId variants (`StringId`, `StringID`, `stringid`, `STRINGID`). `xml_transfer.py` checks 6 (adds `Stringid`, `stringId`). Corrections from XML with unusual casing silently dropped by xml_io.py. **Fix:** Unify to 6 variants in both files. | MEDIUM — silent data loss |
| 3C.2 | **`_fix_bad_entities` double-escapes numeric entities** | `xml_parser.py` line 117. Regex `[^ltgapoqu]` doesn't exclude `#` so `&#123;` → `&amp;#123;`. **Fix:** Add `#` to exclusion set or use proper negative lookahead. | MEDIUM |
| 3C.3 | **Hallucination phrase "tradu" causes massive false positives** | `ai_hallucination_phrases.json` + `quality_checker.py` line 304. `"tradu"` matches "tradition", "traduit", etc. via substring. English phrases are already done correctly (full phrases). **Fix:** Use full phrases for all languages (e.g., `"voici la traduction"`) or word-boundary matching. | MEDIUM — report pollution |
| 3C.4 | **Exit button bypasses `_on_close` cleanup** | `app.py` line 260. Uses `self.root.quit` instead of `self._on_close`. Handler leak + worker threads not signaled to stop. **Fix:** Change to `command=self._on_close`. | LOW |
| 3C.5 | **Duplicate `iter_locstr_elements` implementations** | `xml_parser.py` and `language_loader.py` both implement LocStr iteration with different variant lists. Bug fix to one won't propagate to other. **Fix:** Consolidate to single function in xml_parser.py. | LOW — maintenance risk |
| 3C.6 | **`or` chain treats empty string `""` as missing** | `xml_transfer.py` at ~15 locations. `loc.get("Str") or loc.get("str")` — if `Str=""` exists, falls through to lowercase variant. Safe in practice but architecturally incorrect. **Fix:** Use `is not None` checks instead of `or`. | LOW |
| 3C.7 | **Column detection only triggers via Browse button** | `app.py` lines 164-171. Manual path entry/paste bypasses `_validate_source_files_async`. `_source_columns` stays all-False → non-substring modes blocked with misleading error. **Fix:** Add `trace_add` on source entry or validate on Generate/Transfer click. | LOW |
| 3C.8 | **`LANGUAGE_ORDER` never refreshed after settings change** | `config.py` line 212 vs 255-267. `_discover_languages_from_loc()` runs once at import. After changing LOC path via Settings, language list is stale → wrong Excel output columns. **Fix:** Re-run discovery in `update_settings()`. | LOW |
| 3C.9 | **`traceback.print_exc()` should use logger** | `app.py` line 1695. Bypasses project logging convention. **Fix:** Replace with `logger.exception()`. | LOW |

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

### Bug Fixes (Phase 3)
- [ ] Column shift after `_insert_str_column` fixed — all target columns read correctly
- [ ] `_generate()` handles StrOrigin Only match type
- [ ] StringID-Only mode works without StrOrigin column in target Excel
- [ ] EventName recovery uses correct merge mode (not always STRICT)
- [ ] Auto-populate `_source_eventname` when no EventName column
- [x] ~~SCRIPT filter resolves EventNames before skipping as non-SCRIPT~~ ✅ `5da55030`
- [x] ~~StringID-Only Excel transfer updates ALL matching rows~~ ✅ `8a1f19bd`
- [x] ~~STRICT merge handles duplicate corrections (no silent overwrite)~~ ✅ `31ce29b2`
- [x] ~~`_merge_excel_strict` handles duplicate target rows~~ ✅ `31ce29b2`
- [x] ~~StrOrigin Only Excel merge logs conflicting corrections~~ ✅ `31ce29b2`
- [ ] Attribute case variants unified across xml_io.py and xml_transfer.py
- [ ] Hallucination phrases use full phrases / word boundaries (no "tradu" false positives)

### GUI Reorganization (Phases 1-2, 4-6)
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
| Column shift bug corrupts transfers silently | **CRITICAL** | Fix FIRST before any other work (Phase 3A.1) |
| StrOrigin Only generate produces empty output | **CRITICAL** | Fix immediately (Phase 3A.2) |
| Dict-overwrite bugs in other merge modes | HIGH | Same fix pattern as StringID-only (defaultdict) |
| Widget reparenting breaks layout | HIGH | Phase 1 is purely structural — test before adding features |
| Substring Search decoupled from radio state causes bugs | MEDIUM | Keep internal `match_type` parameter, just change how it's triggered |
| String Erase logic diverges from standalone script | LOW | Port directly, keep standalone as reference |
| Users confused by layout change | MEDIUM | Help button, clear tab labels, update user guide |
| Window too small for Notebook tabs | LOW | Test minimum size, ensure graceful scroll |

---

## 10. Implementation Order (Recommended)

```
URGENT (do first):
  Phase 3A → Fix 4 critical/high bugs (column shift, strorigin_only generate,
             strorigin requirement, recovery merge mode)

THEN:
  Phase 3B → Fix dict-overwrite bugs in strict/excel merge (same pattern)
  Phase 3C → Fix remaining correctness issues

THEN (GUI work):
  Phase 1  → Tab infrastructure
  Phase 2  → Substring match relocation
  Phase 4  → String Erase integration
  Phase 5  → Help button
  Phase 6  → Polish & testing
```

---

*Last updated: 2026-02-23 (code review findings added)*
