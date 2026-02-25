# QuickStandaloneScripts (QSS)

Standalone GUI tools for XML language data operations. Each tool is a single `.py` file with tkinter GUI — no dependencies on LocaNext or each other.

---

## Tool Inventory

### 1. XML Diff Extractor (`xml_diff_extractor.py`) — v4.0

**Three tabs: DIFF (file), DIFF FOLDER, and REVERT.**

**DIFF tab** (file mode) compares a single SOURCE (old) vs TARGET (new) XML and extracts ADD/EDIT LocStr elements.

| Feature | Description |
|---------|-------------|
| **Comparison Modes** | Full (all attributes), StrOrigin+StringID, StrOrigin+StringID+Str, StringID+Str |
| **Category Filter** | All, SCRIPT only (Dialog/Sequencer), NON-SCRIPT only |
| **Export Folder** | Shown when category filter is active — provide the `export__` folder |
| **Output** | `DIFF_{filename}_{timestamp}.xml` next to TARGET (mode/filter included when non-default) |

**DIFF FOLDER tab** (v4.0) compares SOURCE folder vs TARGET folder, auto-matching by language suffix.

| Feature | Description |
|---------|-------------|
| **SOURCE folder** | Folder with language-suffixed XML files (old versions) |
| **TARGET folder** | Folder with language-suffixed XML files (new versions) |
| **LOC folder** | Settings-persisted LOC path — discovers valid language suffixes from `languagedata_*.xml` |
| **Language matching** | Auto-pairs files by suffix (ENG↔ENG, FRE↔FRE). Supports `languagedata_*.xml`, suffix files, suffix folders |
| **Comparison Modes** | Same 4 modes as file DIFF tab |
| **Category Filter** | Same 3 filters as file DIFF tab |
| **Export Folder** | Shown when category filter is active — provide the `export__` folder |
| **Output** | Auto-created `DIFF_FOLDER_{mode}{filter}_{timestamp}/` next to script, one `DIFF_{lang}.xml` per language |

Comparison mode details:
- **Full (all attributes)**: Key = StringID. Extract when ANY attribute differs. (v2.0 default behavior)
- **StrOrigin + StringID**: Key = (StrOrigin, StringID) tuple. Extract TARGET entries whose tuple is not in SOURCE.
- **StrOrigin + StringID + Str**: Key = (StrOrigin, StringID, Str) triple. Extract when translation text also differs.
- **StringID + Str**: Key = (StringID, Str) pair. Extract when text changed regardless of StrOrigin.

**REVERT tab** undoes changes between BEFORE/AFTER in a CURRENT file:
- ADDs (new in AFTER) are REMOVED from CURRENT
- EDITs: Str value RESTORED to BEFORE version
- Everything else in CURRENT stays untouched

### 2. Script Long String Extractor (`script_long_string_extractor.py`) — v2.0

Extracts LocStr entries that are SCRIPT type (Dialog/Sequencer) AND above a character length threshold.

| Feature | Description |
|---------|-------------|
| **Input** | Export folder (for category mapping) + Source folder (XML/Excel) |
| **Filter** | SCRIPT categories only + minimum visible character count |
| **Exclusions** | NarrationDialog subfolder excluded |
| **Output** | Per-language Excel (.xlsx) + XML (.xml) in `Extraction_Output/` |

### 3. String Eraser XML (`string_eraser_xml.py`) — v1.0

Removes LocStr nodes from Target XML files that match Source entries by StringID + StrOrigin.

| Feature | Description |
|---------|-------------|
| **Source** | Folder with Excel (.xlsx) or XML files containing StringID + StrOrigin |
| **Target** | Folder with `languagedata_*.xml` files |
| **Match** | Case-insensitive StringID + normalized StrOrigin |
| **Action** | Removes matching `<LocStr>` nodes from Target XML in-place |

### 4. File Eraser By Name (`file_eraser_by_name.py`) — v1.0

Compares filenames between Source and Target folders. Files in Target whose stem matches a Source stem (case-insensitive, extension-ignored) get moved to an `Erased_Files` backup folder.

| Feature | Description |
|---------|-------------|
| **Match** | Filename stem, case-insensitive |
| **Action** | Moves matched files to backup (non-destructive) |

### 5. BlacklistExtractor (`blacklist_extractor.py`) — v1.0

Extracts any LocStr entry from languagedata whose Str value contains a blacklisted term for that language.

| Feature | Description |
|---------|-------------|
| **Source** | Excel file(s) — one column per language (header = language suffix: FRE, GER, ITA, etc.) |
| **Target** | LOC folder (`languagedata_*.xml`) — same as QuickTranslate |
| **LOC folder** | Settings-persisted LOC path — validates column headers against discovered language suffixes |
| **Language Detection** | Column headers validated against language suffixes discovered from LOC folder |
| **Search** | Substring match: `term in str_value` (case-insensitive). Each cell = one blacklisted term |
| **Output** | Per-language Excel (.xlsx) + XML (.xml) with all matching LocStr entries |

**Design decisions:**
- **GUI:** Source file/folder selector + LOC folder selector (with settings persistence, same as QuickTranslate)
- **Validation:** Column headers must match a `languagedata_*.xml` suffix in LOC — unknown columns warned and skipped
- **Search algorithm:** Simple Python `in` operator (substring). No Aho-Corasick — keeps it zero-dependency QSS. If blacklists grow to thousands of terms, Aho-Corasick can be added later
- **Matching:** Substring, not whole-word. "sword" WILL match "swordsman" — intentional for blacklists (catch everything)
- **Empty cells:** Skipped (no blank term matching)
- **Output naming:** `BLACKLIST_{lang}.xml` / `.xlsx` per language, inside `Blacklist_Output/blacklist_{timestamp}/` folder

---

## v4.0 Changes (XML Diff Extractor)

**What changed from v3.0:**

1. **DIFF FOLDER tab** — new tab for folder-to-folder comparison (SOURCE folder vs TARGET folder)
2. **LOC folder setting** — persisted path to discover valid language suffixes from `languagedata_*.xml`
3. **Auto language matching** — pairs SOURCE/TARGET files by language suffix (ENG↔ENG, FRE↔FRE, etc.)
4. **Per-language output** — auto-created `DIFF_FOLDER_{mode}{filter}_{timestamp}/` folder with one XML per language
5. **Original DIFF tab preserved** — file-to-file mode unchanged, now labeled "DIFF (file)"

**What changed from v2.0 → v3.0:**

1. **Comparison Mode dropdown** — 4 modes using composite keys instead of just StringID
2. **Category Filter dropdown** — filter diffs to SCRIPT or NON-SCRIPT entries only
3. **Export Folder browse** — shown only when category filter is active
4. **Smart output naming** — filename includes mode and filter suffix (e.g. `DIFF_SO-SID_SCRIPT_...`)
5. **Backward compatible** — "Full (all attributes)" + "All (no filter)" = identical to v2.0

---

## Shared Patterns

All QSS tools share these patterns (copied, not imported — standalone):

- **XML sanitization**: Fix unescaped `<br/>`, bare `&`, malformed `</>`
- **Attribute case variants**: `STRINGID_ATTRS`, `STRORIGIN_ATTRS`, `STR_ATTRS`
- **lxml/stdlib fallback**: Try lxml first, fallback to xml.etree.ElementTree
- **`<br/>` preservation**: Sentinel-based escaping (`<br/>` → `\x00BR\x00` before XML escape → restore after)
- **XXE protection**: lxml parser uses `resolve_entities=False, load_dtd=False, no_network=True`
- **Encoding fallback**: utf-8-sig → utf-8 → latin-1 (latin-1 always succeeds)
- **Settings persistence**: JSON file next to script, LOC folder path saved/loaded

---

## Future Ideas

- **REVERT by category**: Revert only SCRIPT or NON-SCRIPT changes (apply category filter to REVERT tab)
- **Extraction by specific category**: Filter by Item, Quest, Character, etc. (not just SCRIPT/NON-SCRIPT)
- **Cross-language diff**: Compare same StringID across different language XML files
- **Diff report Excel**: Output diff results as Excel with columns for SOURCE/TARGET values side by side
