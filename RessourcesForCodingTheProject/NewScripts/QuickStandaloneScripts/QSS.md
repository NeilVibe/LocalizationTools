# QuickStandaloneScripts (QSS)

**Standalone GUI tools for XML language data operations in a game localization pipeline.**

Each tool is a **single `.py` file** with a tkinter GUI. No dependencies on LocaNext or each other — every script runs independently. They all operate on the same data: XML files containing `<LocStr>` elements with `StringID`, `StrOrigin`, and `Str` attributes that hold game text translations.

```
RessourcesForCodingTheProject/NewScripts/QuickStandaloneScripts/
├── xml_diff_extractor.py          # 1,463 lines — v4.0
├── script_long_string_extractor.py #   736 lines — v2.0
├── string_eraser_xml.py           #   593 lines — v1.0
├── file_eraser_by_name.py         #   325 lines — v1.0
├── script_novoice_extractor.py    #   807 lines — v1.0
├── blacklist_extractor.py         #   841 lines — v1.0
├── QSS.md                         # This document
└── Extraction_Output/             # Shared output directory for extractors
```

**Total: 6 tools, ~4,765 lines of Python.**

---

## How To Run

All tools are plain Python scripts with a tkinter GUI. Run from any terminal:

```bash
python xml_diff_extractor.py
python script_long_string_extractor.py
python string_eraser_xml.py
python file_eraser_by_name.py
python script_novoice_extractor.py
python blacklist_extractor.py
```

Can also be bundled with PyInstaller for standalone `.exe` distribution.

---

## Dependencies

| Dependency | Required By | Purpose |
|------------|-------------|---------|
| **Python 3.8+** | All | Runtime |
| **tkinter** | All | GUI (included with Python) |
| **lxml** | All except File Eraser | XML parsing with recovery mode. Falls back to stdlib `xml.etree` if missing |
| **xlsxwriter** | Long String, No-Voice, Blacklist | Writing Excel output |
| **openpyxl** | String Eraser, Blacklist | Reading Excel input |

Install optional deps: `pip install lxml xlsxwriter openpyxl`

---

## Data Concepts

Before diving into the tools, here are the key data concepts:

| Concept | Meaning |
|---------|---------|
| **LocStr** | XML element holding one translated string. Has attributes like `StringID`, `StrOrigin`, `Str` |
| **StringID** | Unique identifier for a text string across all languages |
| **StrOrigin** | Path-like origin showing where the string came from in the game data |
| **Str** | The actual translated text content |
| **languagedata_*.xml** | Per-language XML file in the LOC folder (e.g. `languagedata_ENG.xml`, `languagedata_FRE.xml`) |
| **export__ folder** | Game export folder with category subfolders (Dialog, Sequencer, Item, Quest, etc.) containing `*.loc.xml` files |
| **SCRIPT type** | Strings from Dialog or Sequencer categories — typically voiced dialogue |
| **SoundEventName** | Attribute linking a string to voice audio. Strings with this have recorded voice acting |
| **`<br/>`** | Newline representation in XML language data. Must ALWAYS be preserved, never escaped |

---

## Tool #1: XML Diff Extractor

**File:** `xml_diff_extractor.py` — **v4.0** — 1,463 lines

**Purpose:** Compare old vs new XML language data and extract what changed (additions + edits). Also revert unwanted changes.

**When to use:** After receiving updated translation files, to see exactly what changed and isolate the diff for review or selective import.

### Three Tabs

#### DIFF (file mode)
Compare a single SOURCE file (old) against a TARGET file (new).

| Input | Description |
|-------|-------------|
| **SOURCE** | Old XML file (the baseline) |
| **TARGET** | New XML file (the updated version) |
| **Comparison Mode** | How to detect changes (see below) |
| **Category Filter** | All / SCRIPT only / NON-SCRIPT only |
| **Export Folder** | Required when category filter is active — provides StringID→Category mapping |

| Comparison Mode | Key Used | Detects |
|-----------------|----------|---------|
| Full (all attributes) | StringID | Any attribute change |
| StrOrigin + StringID | (StrOrigin, StringID) | New origin+ID combos |
| StrOrigin + StringID + Str | (StrOrigin, StringID, Str) | Translation text changes |
| StringID + Str | (StringID, Str) | Text changes regardless of origin |

**Output:** `DIFF_{filename}_{timestamp}.xml` next to TARGET file.

#### DIFF FOLDER (folder mode)
Compare SOURCE folder vs TARGET folder. Auto-matches files by language suffix (ENG↔ENG, FRE↔FRE, etc.).

| Input | Description |
|-------|-------------|
| **SOURCE folder** | Folder with old language-suffixed XML files |
| **TARGET folder** | Folder with new language-suffixed XML files |
| **LOC folder** | Discovers valid language suffixes from `languagedata_*.xml` filenames |

**Output:** `DIFF_FOLDER_{mode}{filter}_{timestamp}/` folder with one `DIFF_{lang}.xml` per language.

#### REVERT
Undo specific changes by comparing BEFORE, AFTER, and CURRENT states.

| What Happened | What REVERT Does |
|---------------|------------------|
| String was **added** in AFTER | **Removes** it from CURRENT |
| String was **edited** in AFTER | **Restores** BEFORE version in CURRENT |
| String unchanged | Left alone |

---

## Tool #2: Script Long String Extractor

**File:** `script_long_string_extractor.py` — **v2.0** — 736 lines

**Purpose:** Find SCRIPT-type dialogue strings that are unusually long — candidates for shortening or splitting.

**When to use:** To audit translation quality by finding overly long dialogue/sequencer strings that may cause text overflow in-game.

| Input | Description |
|-------|-------------|
| **Export Folder** | `export__` folder to build StringID→Category mapping |
| **Source Folder** | Folder with `languagedata_*.xml` or `.xlsx` files to scan |
| **Min Length** | Minimum visible character count threshold (default: 50) |

**Filter logic:**
1. Must be SCRIPT category (Dialog or Sequencer)
2. Must have visible character count >= threshold
3. NarrationDialog subfolder is **excluded** (narration is expected to be long)

**Visible character count** strips markup tags (`<br/>`, `<PAColor>`, `<Scale>`, `<color>`, `<Style:>`, `{code blocks}`), unescapes HTML entities, and counts remaining characters.

| Output | Content |
|--------|---------|
| **Excel** | StringID, StrOrigin, Str, CharCount — sorted by CharCount descending |
| **XML** | Raw `<LocStr>` elements sorted by CharCount descending |

**Output location:** `Extraction_Output/extraction_{threshold}chars_{timestamp}/`

---

## Tool #3: String Eraser XML

**File:** `string_eraser_xml.py` — **v1.0** — 593 lines

**Purpose:** Remove specific LocStr entries from languagedata XML files. Destructive operation (modifies files in-place).

**When to use:** To clean up languagedata by removing entries that are no longer needed, have been deprecated, or were added in error.

| Input | Description |
|-------|-------------|
| **Source** | Folder with Excel (.xlsx) or XML files listing which strings to remove (must have StringID + StrOrigin columns) |
| **Target** | Folder with `languagedata_*.xml` files to modify |

**Match logic:** Case-insensitive StringID + normalized StrOrigin. Both must match for a `<LocStr>` node to be removed.

**Action:** Removes matching `<LocStr>` nodes from Target XML **in-place**. Backs up originals first.

---

## Tool #4: File Eraser By Name

**File:** `file_eraser_by_name.py` — **v1.0** — 325 lines

**Purpose:** Bulk-remove files from a Target folder based on filename matching against a Source folder.

**When to use:** When you have a list of files (by name) that need to be cleaned up from a delivery or export folder.

| Input | Description |
|-------|-------------|
| **Source** | Folder whose filenames define what to remove |
| **Target** | Folder to clean up |

**Match logic:** Filename stem only, case-insensitive. Extensions are ignored — `data.xml` in Source matches `data.txt` in Target.

**Action:** Non-destructive — matched files are **moved** to an auto-created `Erased_Files/` backup folder (not deleted).

---

## Tool #5: Script No-Voice Extractor

**File:** `script_novoice_extractor.py` — **v1.0** — 807 lines

**Purpose:** Extract SCRIPT-type strings that have no associated voice audio — text-only dialogue and sequencer strings that are never spoken aloud.

**When to use:** To find script strings that lack voice recording, for quality review or to feed corrections back via QuickTranslate.

| Input | Description |
|-------|-------------|
| **EXPORT Folder** | `export__` folder — scanned once to build both the StringID→Category map AND the set of voiced StringIDs |
| **LOC Folder** | Folder with `languagedata_*.xml` files to extract from |

**Filter logic (two conditions, both must be true):**
1. StringID belongs to a SCRIPT category (Dialog or Sequencer)
2. StringID does NOT appear with a `SoundEventName` attribute anywhere in the EXPORT data

**Key design decisions:**
- **Single pass** over EXPORT folder — builds category map AND voiced set simultaneously (halves I/O)
- **Scans ALL XML elements** for SoundEventName, not just LocStr — voice references can be on any element type
- **No NarrationDialog exclusion** — unlike the Long String Extractor, unvoiced narration IS worth catching here
- **SoundEventName variants scanned:** `SoundEventName`, `soundeventname`, `Soundeventname`, `SOUNDEVENTNAME`, `EventName`, `eventname`, `EVENTNAME`

| Output | Content |
|--------|---------|
| **Excel** | StringID, StrOrigin, Str, **Correction** (empty), Category — sorted by StringID |
| **XML** | Raw `<LocStr>` elements sorted by StringID |

The empty **Correction** column is for the user to fill in corrections, then feed the Excel back into QuickTranslate's TRANSFER feature.

**Output location:** `Extraction_Output/novoice_script_{timestamp}/` with `NOVOICE_{LANG}.xlsx` + `NOVOICE_{LANG}.xml` per language.

**Statistics shown in log:**
```
EXPORT INDEX
  Total StringIDs indexed: 45,230
  SCRIPT StringIDs (Dialog/Sequencer): 12,450
  Voiced StringIDs (with SoundEventName): 8,320
  → SCRIPT + No Voice candidates: 4,130

EXTRACTION
  ENG: 4,130 no-voice SCRIPT entries extracted
  FRE: 4,128 no-voice SCRIPT entries extracted
  Orphaned (in LOC, not in EXPORT): 247 — skipped
```

---

## Tool #6: BlacklistExtractor

**File:** `blacklist_extractor.py` — **v1.0** — 841 lines

**Purpose:** Find all LocStr entries whose translated text contains any forbidden/blacklisted term.

**When to use:** To scan translations for prohibited words, brand names that shouldn't appear, outdated terminology, or any terms that need review across all languages.

| Input | Description |
|-------|-------------|
| **LOC Folder** | Folder with `languagedata_*.xml` — dual purpose: (1) discovers language suffixes, (2) is the search target |
| **Source** | Excel file(s) with blacklist terms — one column per language (header = language suffix like ENG, FRE, GER) |

**Search logic:** Substring match — `term.lower() in str_value.lower()`. Each cell in the Excel = one blacklisted term. Intentionally catches substrings (e.g. "sword" matches "swordsman") because blacklists should be aggressive.

**Multi-source support:** Can point to a single `.xlsx` file OR a folder of `.xlsx` files — all terms are combined and deduplicated per language.

| Output | Content |
|--------|---------|
| **Excel** | StringID, StrOrigin, Str, MatchedTerm — one row per match (same entry can appear multiple times if it matches multiple terms) |
| **XML** | Raw `<LocStr>` elements, deduplicated by StringID |

**Output location:** `Blacklist_Output/blacklist_{timestamp}/` with `BLACKLIST_{LANG}.xlsx` + `BLACKLIST_{LANG}.xml` per language.

---

## Workflow: How The Tools Work Together

The tools form a pipeline for localization quality management:

```
┌──────────────────────────────────────────────────────────────┐
│                    EXTRACTION PHASE                          │
│                                                              │
│  XML Diff Extractor ──→ What changed between versions?       │
│  Long String Extractor ──→ Which scripts are too long?       │
│  No-Voice Extractor ──→ Which scripts lack voice?            │
│  BlacklistExtractor ──→ Which strings have forbidden terms?  │
│                                                              │
│  All produce: Excel (for review) + XML (for reimport)        │
├──────────────────────────────────────────────────────────────┤
│                    REVIEW PHASE                              │
│                                                              │
│  Human reviews Excel output, fills in Correction column      │
│  (No-Voice Extractor + Long String Extractor)                │
│                                                              │
│  Corrections fed back into QuickTranslate TRANSFER feature   │
├──────────────────────────────────────────────────────────────┤
│                    CLEANUP PHASE                             │
│                                                              │
│  String Eraser XML ──→ Remove deprecated strings from XML    │
│  File Eraser By Name ──→ Remove obsolete files               │
│  XML Diff Extractor (REVERT) ──→ Undo unwanted changes       │
└──────────────────────────────────────────────────────────────┘
```

---

## Shared Technical Patterns

All QSS tools that parse XML share these patterns (copied into each file, not imported):

### XML Handling
- **`<br/>` preservation:** `<br/>` is the newline format in game XML data. All tools use sentinel-based escaping (`<br/>` → `\x00BR\x00` → XML escape → restore `<br/>`) to prevent corruption
- **XML sanitization:** Fixes bare `&`, malformed `</>`, and unescaped `<` in attribute values before parsing
- **Encoding fallback:** Tries utf-8-sig → utf-8 → latin-1 (latin-1 always succeeds as it decodes any byte sequence)
- **XXE protection:** lxml parser uses `resolve_entities=False, load_dtd=False, no_network=True`
- **lxml/stdlib fallback:** Tries lxml first (recovery mode, attribute order preservation), falls back to stdlib `xml.etree`

### Attribute Matching
All tools handle case variants of LocStr element attributes:

```python
LOCSTR_TAGS    = ['LocStr', 'locstr', 'LOCSTR', 'LOCStr', 'Locstr']
STRINGID_ATTRS = ('StringId', 'StringID', 'stringid', 'STRINGID', 'Stringid', 'stringId')
STRORIGIN_ATTRS = ('StrOrigin', 'Strorigin', 'strorigin', 'STRORIGIN')
STR_ATTRS       = ('Str', 'str', 'STR')
```

### GUI
- tkinter with ttk widgets
- `scrolledtext.ScrolledText` log area with color-coded tags (info/success/warning/error/header)
- Settings persistence via JSON file next to script
- PyInstaller-compatible path detection (`sys.frozen` check)

### Output
- Excel via **xlsxwriter** (write-only, reliable) — with autofilter, freeze panes, formatting
- XML as hand-built string output (not serialized from tree) for full control over formatting
- Timestamped output folders to prevent overwriting previous runs

---

## Roadmap: Mega QSS → QuickTranslate Integration

### The Vision

Today: 6 separate `.py` files, each with its own window, its own settings, its own EXPORT/LOC folder picker. Users switch between tools constantly. Folder paths get re-entered. Context is lost.

**Phase A:** Combine all 6 tools into a single **Mega QSS** — one window, tabbed interface, shared settings.
**Phase B:** Integrate Mega QSS into **QuickTranslate** as additional tabs in its planned GUI rework.

```
TODAY                           PHASE A                         PHASE B
                                (Mega QSS)                      (QuickTranslate)
┌──────────────────┐
│ xml_diff_ext...  │           ┌─────────────────────────┐     ┌──────────────────────────────┐
├──────────────────┤           │ ┌─Shared Settings──────┐│     │ [Main] [Helpers] [Extractors]│
│ long_string_e... │           │ │ EXPORT: [........] 📁││     ├──────────────────────────────┤
├──────────────────┤           │ │ LOC:    [........] 📁││     │                              │
│ novoice_extra... │  ──────→  │ └──────────────────────┘│ ──→ │  Extraction/Cleanup/Diff     │
├──────────────────┤           │ [Diff][Long][NoVoice]   │     │  tools share QuickTranslate  │
│ blacklist_ext... │           │ [Blacklist][Eraser][File]│     │  settings, log, and thread   │
├──────────────────┤           │                         │     │  infrastructure              │
│ string_eraser... │           │ ┌─Shared Log───────────┐│     │                              │
├──────────────────┤           │ │                       ││     │  Output feeds directly into  │
│ file_eraser_b... │           │ └───────────────────────┘│     │  TRANSFER workflow           │
└──────────────────┘           └─────────────────────────┘     └──────────────────────────────┘
 6 windows                      1 window, 6 tabs                1 app, everything integrated
 6 settings files               1 shared settings               QuickTranslate settings
 paths re-entered               paths entered once              paths already configured
```

### Phase A: Mega QSS (Standalone)

Combine all tools into one `mega_qss.py` or small package with a `ttk.Notebook` tabbed interface.

**Shared settings panel (always visible, above tabs):**

```
┌─ Settings ──────────────────────────────────────────────┐
│  EXPORT folder: [....................................] 📁│
│  LOC folder:    [....................................] 📁│
│  [Save Settings]                                        │
└─────────────────────────────────────────────────────────┘
```

These two paths are used by 4 of the 6 tools. Set once, used everywhere.

**Tab layout:**

| Tab | Tool | Needs EXPORT | Needs LOC | Extra Inputs |
|-----|------|:---:|:---:|---|
| **Diff** | XML Diff Extractor | for category filter | for folder mode | SOURCE/TARGET files or folders, comparison mode |
| **Long Strings** | Script Long String Extractor | Yes | Yes (source) | Min char threshold |
| **No-Voice** | Script No-Voice Extractor | Yes | Yes | — |
| **Blacklist** | BlacklistExtractor | — | Yes | Excel blacklist file(s) |
| **String Eraser** | String Eraser XML | — | — (has own target) | Source keys folder, Target XML folder |
| **File Eraser** | File Eraser By Name | — | — | Source folder, Target folder |

**Shared components:**
- Log panel (right pane, always visible regardless of tab)
- Progress reporting in shared log
- Settings persistence in single JSON file
- EXPORT index built once, cached, reused across tabs (Long Strings + No-Voice + Diff all need `category_map`)

**Key benefit — shared EXPORT index:**

```
Current: Each tool scans EXPORT folder independently
  Long String Extractor: scans EXPORT → category_map (30s)
  No-Voice Extractor:    scans EXPORT → category_map + voiced_sids (30s)
  XML Diff (filtered):   scans EXPORT → category_map (30s)

Mega QSS: Build index ONCE, share across tabs
  First tab to need it → builds full index (category_map + voiced_sids) (30s)
  Other tabs → instant reuse from cache
  [Rebuild Index] button if EXPORT folder changed
```

**Architecture:**

```
mega_qss/
├── mega_qss.py              # Entry point + GUI shell (Notebook + shared settings + log)
├── shared/
│   ├── xml_utils.py         # sanitize_xml, parse, iter_locstr, br preservation, encoding
│   ├── excel_utils.py       # xlsxwriter report writing, openpyxl reading
│   ├── export_index.py      # category_map + voiced_sids (built once, cached)
│   └── settings.py          # JSON persistence for all paths
├── tabs/
│   ├── diff_tab.py          # XML Diff + Revert (from xml_diff_extractor.py)
│   ├── long_string_tab.py   # Long String Extraction (from script_long_string_extractor.py)
│   ├── novoice_tab.py       # No-Voice Extraction (from script_novoice_extractor.py)
│   ├── blacklist_tab.py     # Blacklist search (from blacklist_extractor.py)
│   ├── string_eraser_tab.py # String Eraser (from string_eraser_xml.py)
│   └── file_eraser_tab.py   # File Eraser (from file_eraser_by_name.py)
└── mega_qss_settings.json   # Persisted paths + per-tab settings
```

**The standalone `.py` files stay as-is** — they're battle-tested and useful on their own. Mega QSS is a new layer on top, sharing the same logic.

### Phase B: QuickTranslate Integration

QuickTranslate already has a planned GUI rework (see `QuickTranslate/docs/WIP_GUI_REORGANIZATION.md`) that adds a `[Main] [Helper Functions]` tab layout. The Mega QSS tools slot in naturally:

**Option 1: Helper Functions sub-tabs**
```
QuickTranslate
├── [Main]              ← Translation workflow (Generate, Transfer, Pre-Submission)
├── [Helper Functions]  ← Quick Actions, Substring Search
└── [Extractors]        ← All 6 QSS tools as sub-tabs
```

**Option 2: Integrated into Helper Functions**
```
QuickTranslate
├── [Main]              ← Translation workflow
└── [Helper Functions]  ← Quick Actions + Diff + Eraser + Extractors (scrollable sections)
```

**Option 3: Selective integration (recommended)**

Not all tools are equally useful inside QuickTranslate. Integration priority:

| Priority | Tool | Why |
|----------|------|-----|
| **HIGH** | XML Diff + Revert | Used in every patch/merge cycle. Output feeds directly into TRANSFER |
| **HIGH** | String Eraser | Common cleanup before TRANSFER |
| **MEDIUM** | Long String Extractor | QA review of dialogue. Uses same EXPORT folder already in QuickTranslate settings |
| **MEDIUM** | No-Voice Extractor | QA review. Same EXPORT folder. Correction column feeds back into TRANSFER |
| **LOW** | BlacklistExtractor | Useful but less frequent. Own input (Excel blacklist) |
| **SKIP** | File Eraser By Name | File-level operation, not LocStr-level. Stays standalone |

**The pipeline becomes seamless:**
```
QuickTranslate (one app)
  1. [Extractors tab] → Run No-Voice extraction → produces NOVOICE_ENG.xlsx
  2. Human reviews Excel, fills Correction column
  3. [Main tab] → Load NOVOICE_ENG.xlsx as Source → TRANSFER corrections back to XML
```

No context switching. No re-entering paths. No separate windows.

**What QuickTranslate already has that Mega QSS tools need:**
- EXPORT folder path (in settings)
- LOC folder path (in settings)
- XML parsing infrastructure (`xml_parser.py`, `xml_io.py`)
- Excel reading/writing
- Threaded worker pattern
- Shared log + progress bar
- `<br/>` preservation throughout

### Implementation Order

```
1. STANDALONE QSS TOOLS (current state) — DONE ✅
   All 6 tools exist and work independently

2. MEGA QSS (Phase A) — FUTURE
   Combine into tabbed interface with shared settings + EXPORT index cache
   Still a standalone tool, no QuickTranslate dependency
   Deliverable: single .exe via PyInstaller

3. QUICKTRANSLATE INTEGRATION (Phase B) — FUTURE
   Port high-priority tools (Diff, Eraser, Long String, No-Voice) into QT's Helper tab
   Reuse QT infrastructure (settings, XML parsing, threading, log)
   Low-priority tools (Blacklist, File Eraser) stay standalone or in Mega QSS
```

### Decision: Skip Mega QSS and go straight to QuickTranslate?

Possible, but Mega QSS has value even if QuickTranslate integration happens later:

| Mega QSS First | Skip to QT Integration |
|---|---|
| Faster to build (no QT coupling) | Fewer total steps |
| Useful for people who don't use QT | Only useful inside QT |
| Tests the shared architecture before bigger integration | Riskier — touching QT's complex GUI |
| Can be distributed to non-translators (QA, PMs) | QT is a translator tool |
| Shared EXPORT index saves time even standalone | QT already has EXPORT path |

**Recommendation:** Build Mega QSS first as an intermediate step. It validates the shared architecture and the tabbed layout. Then porting to QuickTranslate is mostly moving tab modules into QT's Notebook with minimal adaptation.

---

## Version History

| Tool | Version | Key Changes |
|------|---------|-------------|
| XML Diff Extractor | v4.0 | DIFF FOLDER tab, LOC folder setting, auto language matching |
| | v3.0 | 4 comparison modes, category filter, export folder |
| | v2.0 | Full attribute diff, REVERT tab |
| Script Long String Extractor | v2.0 | Per-language output, Excel+XML, NarrationDialog exclusion |
| String Eraser XML | v1.0 | Initial release |
| File Eraser By Name | v1.0 | Initial release |
| Script No-Voice Extractor | v1.0 | Initial release |
| BlacklistExtractor | v1.0 | Initial release |
