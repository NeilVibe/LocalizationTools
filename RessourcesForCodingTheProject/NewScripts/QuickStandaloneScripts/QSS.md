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
