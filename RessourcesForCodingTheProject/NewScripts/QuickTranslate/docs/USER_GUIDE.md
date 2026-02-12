# QuickTranslate User Guide

**Version 4.0** | February 2026

---

## 1. What is QuickTranslate?

QuickTranslate is a desktop tool for localization teams that does two things:

- **LOOKUP** (Generate button) — Read-only. Searches Korean text across 17 languages and exports results to Excel.
- **TRANSFER** (TRANSFER button) — Writes corrections from Excel/XML into target `languagedata_*.xml` files.

Input formats: Excel (`.xlsx`) and XML (`.xml` / `.loc.xml`). Languages are auto-discovered from the LOC folder.

---

## 2. Installation

### Setup Installer (Recommended)

Download `QuickTranslate_vX.X.X_Setup.exe` from GitHub Releases. Run it, choose an install drive, done. Creates Start Menu shortcut and desktop icon.

### Portable Version

Download `QuickTranslate_vX.X.X_Portable.zip`. Extract anywhere. Run `QuickTranslate.exe`.

### First-Run Configuration

On first launch, `settings.json` is created next to the executable:

```json
{
  "loc_folder": "F:\\perforce\\cd\\mainline\\resource\\GameData\\stringtable\\loc",
  "export_folder": "F:\\perforce\\cd\\mainline\\resource\\GameData\\stringtable\\export__"
}
```

Edit these paths to match your Perforce workspace. Use double backslashes (`\\`) in JSON. You can also change paths from the Settings section in the GUI.

### Folder Layout After Install

```
QuickTranslate/
├── QuickTranslate.exe
├── settings.json          ← LOC + EXPORT paths
├── exclude_rules.json     ← Find Missing exclusions (auto-created)
├── Source/                ← Default source folder (pre-populated in GUI)
├── Output/                ← LOOKUP results (Excel)
├── Presubmission Checks/  ← Quality check results
└── Failed Reports/        ← TRANSFER failure reports
```

---

## ⚡ Quick Start: Your First TRANSFER in 5 Minutes

> 🆕 **New to QuickTranslate?** Follow these 5 steps. You'll have corrections written to XML in minutes.

### How TRANSFER Works

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│   📄 Your Excel  │  ────→  │  QuickTranslate   │  ────→  │  📂 XML files   │
│   corrections   │         │    TRANSFER       │         │  Str= updated!  │
└─────────────────┘         └──────────────────┘         └─────────────────┘
  Correction column            matches by ID               languagedata_*.xml
```

### Step 1 — Create Your Excel File

Open Excel and create a file with **exactly these 3 column headers** in Row 1:

```
┌──────────────────────────────────────────────────────────────────────┐
│                        📊 YOUR EXCEL FILE                            │
├──────────────┬───────────────────────┬───────────────────────────────┤
│  StringID    │  StrOrigin            │  Correction                   │
│  ··········  │  ···················  │  ··························   │
│  The unique  │  The original Korean  │  ✏️ YOUR TRANSLATION          │
│  ID from XML │  text from XML        │  This is what you write!     │
├──────────────┼───────────────────────┼───────────────────────────────┤
│  quest_001   │  퀘스트를 완료하세요   │  Complete the quest           │
│  quest_002   │  아이템을 획득하세요   │  Obtain the item              │
│  npc_greet   │  안녕하세요, 모험가!   │  Hello, adventurer!           │
└──────────────┴───────────────────────┴───────────────────────────────┘
```

> 💡 **Where do I get StringID and StrOrigin?** Run a **LOOKUP** first (Generate button). The output Excel contains both columns — copy them into your correction file and add your translations in the Correction column.

### Step 2 — Organize by Language

QuickTranslate auto-detects the target language from **folder names** or **file name suffixes**:

```
📂 MyCorrections/                  ← Set this as SOURCE in QuickTranslate
│
├── 📁 ENG/
│   └── 📄 corrections.xlsx       ← English translations
│
├── 📁 FRE/
│   └── 📄 corrections.xlsx       ← French translations
│
└── 📁 GER/
    └── 📄 corrections.xlsx       ← German translations
```

> ⚠️ **No language = no TRANSFER.** If QuickTranslate can't detect the language, the file is skipped. Either use language-named folders (`ENG/`, `FRE/`) or add the language code to the filename (`corrections_eng.xlsx`).

### Step 3 — Open QuickTranslate

Set the **Source** path to your corrections folder (the parent, e.g., `MyCorrections/`).

### Step 4 — Select Match Type

Pick **Strict** (safest — verifies both StringID and Korean text match before writing).

### Step 5 — Click TRANSFER

Review the transfer plan in the log area → click **Yes** to confirm → done.

```
┌──────────────────────────────────────────────────────────────────────┐
│  ✅ UPDATED      │  Correction applied successfully                  │
│  ⚠️ NOT_FOUND    │  StringID doesn't exist — check for typos        │
│  ⚠️ MISMATCH     │  Korean text differs — source XML may have changed│
│  ℹ️ UNCHANGED    │  Already has this exact value — nothing to do     │
└──────────────────────────────────────────────────────────────────────┘
```

> Check `Failed Reports/` for any corrections that didn't apply. The failure XML files can be reused as source for a retry after fixing the issues.

---

## 3. Excel Column Reference

This is the most important section. QuickTranslate detects columns by header name (case-insensitive, any order).

### Recognized Header Names

| Logical Column | Accepted Headers |
|----------------|-----------------|
| **StringID** | `StringID`, `StringId`, `string_id`, `STRINGID` |
| **StrOrigin** | `StrOrigin`, `Str_Origin`, `str_origin`, `STRORIGIN` |
| **Correction** | `Correction`, `correction`, `corrected` |
| **EventName** | `EventName`, `event_name`, `SoundEventName` |
| **DialogVoice** | `DialogVoice`, `dialog_voice` |

### What Each Column Means

| Column | What to put in it | Where to get it |
|--------|-------------------|-----------------|
| **StringID** | The unique identifier of the string (e.g., `quest_001`) | From LOOKUP output or directly from XML (`StringID=` attribute) |
| **StrOrigin** | The **original Korean text** currently in the XML | From LOOKUP output — copy exactly as-is, including `<br/>` tags |
| **Correction** | ✏️ **Your translated text** — this gets written into the XML `Str=` attribute | **You write this!** The actual translation. |
| **EventName** | Sound event name (alternative to StringID for dialogue lines) | From audio/dialogue pipeline, or from `.loc.xml` `SoundEventName=` attribute |
| **DialogVoice** | Voice actor prefix (helps resolve EventName → StringID) | From audio pipeline metadata |

> ⚠️ **The Correction column is YOUR translation.** Don't leave it in Korean — TRANSFER silently skips rows where Correction still contains Korean text.

### Required Columns by Match Type

| Match Type | Required Columns | Optional |
|------------|-----------------|----------|
| **Substring** | Column A with Korean text (no headers needed) | — |
| **StringID-Only** | StringID + Correction | StrOrigin, EventName, DialogVoice |
| **Strict** | StringID + StrOrigin + Correction | EventName, DialogVoice |
| **StrOrigin Only** | StrOrigin + Correction | StringID, EventName, DialogVoice |

If required columns are missing, that match type radio button is greyed out in the GUI. The log area shows which columns were detected when you browse to a source folder.

### ✅ Correct vs ❌ Wrong Excel Examples

```
✅ CORRECT — Headers in Row 1, data starts Row 2:
┌──────────────┬──────────────────────┬────────────────────────┐
│  StringID    │  StrOrigin           │  Correction            │  ← Row 1 (headers)
├──────────────┼──────────────────────┼────────────────────────┤
│  quest_001   │  퀘스트를 완료하세요  │  Complete the quest    │  ← Row 2+
│  quest_002   │  아이템을 획득하세요  │  Obtain the item       │
└──────────────┴──────────────────────┴────────────────────────┘

❌ WRONG — Missing Correction column:
┌──────────────┬──────────────────────┐
│  StringID    │  StrOrigin           │  ← No Correction column!
├──────────────┼──────────────────────┤  ← TRANSFER has nothing to write
│  quest_001   │  퀘스트를 완료하세요  │
└──────────────┴──────────────────────┘

❌ WRONG — Translation still in Korean:
┌──────────────┬──────────────────────┬────────────────────────┐
│  StringID    │  StrOrigin           │  Correction            │
├──────────────┼──────────────────────┼────────────────────────┤
│  quest_001   │  퀘스트를 완료하세요  │  퀘스트를 완료해 주세요 │  ← Still Korean!
└──────────────┴──────────────────────┴────────────────────────┘     Silently skipped.
```

> 💡 **Pro tip:** Run a LOOKUP first to generate an Excel with StringID and StrOrigin pre-filled. Then add a Correction column with your translations. This guarantees correct column names and values.

---

## 4. Match Types

### Substring (LOOKUP only)

Searches your Korean text as a substring inside the StrOrigin field of every `.loc.xml` in the EXPORT folder. No headers needed — just Korean text in Column A.

- Good for: "What does this Korean text mean in English?"
- TRANSFER is **not available** (too imprecise for writing)
- Short strings (1-2 chars) may return hundreds of matches

### StringID-Only (SCRIPT categories)

Matches by StringID alone. Ignores StrOrigin completely. **Only processes SCRIPT categories** — Dialog/ and Sequencer/ folders in EXPORT. Excludes NarrationDialog subfolder.

- Good for: Dialogue and cutscene corrections where StrOrigin is very long
- Non-SCRIPT StringIDs are skipped (status: `SKIPPED_NON_SCRIPT`)
- Required: StringID + Correction columns

### Strict (StringID + StrOrigin)

Requires **both** StringID and StrOrigin to match. Safest mode for non-SCRIPT categories. Uses a 4-step matching cascade before declaring failure:

1. **Exact** — case-insensitive StringID + normalized StrOrigin
2. **Lowercase** — both sides lowercased
3. **Normalized** — HTML unescape + whitespace collapse + `&desc;` removal
4. **No-space fallback** — remove all whitespace and compare

If all 4 steps fail: `NOT_FOUND` (StringID missing) or `STRORIGIN_MISMATCH` (StringID exists but text differs).

**Fuzzy precision** is available: after the 4-step cascade fails, uses KR-SBERT semantic similarity search. Threshold range 0.70–1.00 (default 0.85). Slower but catches rewording.

### StrOrigin Only (fills duplicates)

Matches by StrOrigin text alone, ignoring StringID. One correction fills **all** entries sharing the same StrOrigin — this is "fan-out" behavior.

- Defaults to "Only untranslated" scope for safety (fan-out can overwrite good translations)
- Switching to "Transfer ALL" triggers a safety warning
- Fuzzy precision available (same as Strict)

### Comparison Table

| | Substring | StringID-Only | Strict | StrOrigin Only |
|---|:-:|:-:|:-:|:-:|
| LOOKUP | Yes | Yes | Yes | Yes |
| TRANSFER | No | Yes | Yes | Yes |
| Precision | Low | Medium | Highest | Medium |
| Fan-out | N/A | No | No | Yes |
| Fuzzy available | No | No | Yes | Yes |

---

## 5. LOOKUP Features

All LOOKUP operations are read-only. Output goes to `Output/`.

### Generate (Source Folder → Excel)

Point the Source path at a folder containing Excel/XML files. QuickTranslate scans all files, matches against stringtables, and exports an Excel file with all 17 languages.

- Accepts mixed Excel + XML files in the same folder
- Output: `Output/QuickTranslate_YYYYMMDD_HHMMSS.xlsx`
- Output columns: KOR (Input) | Status | StringID | ENG | FRE | GER | ...
- Status values: `MATCHED` (1 hit), `MULTI (N)` (N hits), `NOT FOUND`

### StringID Lookup

Type or paste a StringID in the text field, click **Lookup**. Gets all 17 translations instantly.

- Output: `Output/StringID_<ID>_YYYYMMDD_HHMMSS.xlsx`

### Reverse Lookup

Browse to a `.txt` file with one string per line (any language). QuickTranslate auto-detects the language and finds matching StringIDs.

- Output: `Output/ReverseLookup_YYYYMMDD_HHMMSS.xlsx`
- Special values: `NOT FOUND` (no match), `NO TRANSLATION` (StringID exists but Str is empty)

### Find Missing Translations

Compares a Source folder against a Target LOC folder to find untranslated strings (where Str is empty or still Korean).

**Parameter dialog with 4 match modes:**

| Mode | Speed | Use Case |
|------|-------|----------|
| StringID + KR (Strict) | Instant | Default — catches 95% of cases |
| StringID + KR (Fuzzy) | Minutes | Korean text was reworded |
| KR only (Strict) | Fast | StringID changed but Korean is same |
| KR only (Fuzzy) | Slow | Maximum coverage |

**Two types of output per language:**
- Excel report: `Output/MISSING_ENG_YYYYMMDD_HHMMSS.xlsx` (category-clustered)
- Close folder: `Output/Close_ENG/` (mirrors EXPORT structure — usable as TRANSFER source)

**Exclude Dialog:** Configure folders to exclude from results (e.g., System/Gimmick). Saved to `exclude_rules.json` and remembered between sessions.

---

## 6. TRANSFER Features

TRANSFER writes the Correction column value into the `Str` attribute of matching `<LocStr>` elements in the target `languagedata_*.xml` files.

**Available for:** StringID-Only, Strict, and StrOrigin Only. **Not available for** Substring (LOOKUP only).

### How It Works

1. Reads all correction files from Source folder (Excel + XML)
2. Detects target language for each file (see Language Detection below)
3. Resolves EventNames to StringIDs if applicable
4. Shows transfer plan in log (full file mapping tree)
5. Confirmation dialog — user must click "Yes"
6. Writes corrections to target XML files
7. Runs golden rule cleanup
8. Generates transfer report + failure reports

### Transfer Scope

| Scope | Behavior | Default For |
|-------|----------|------------|
| **Transfer ALL** | Overwrite every match, even if already translated | Strict, StringID-Only |
| **Only untranslated** | Only fill entries where Str is empty or Korean | StrOrigin Only |

### Language Detection

QuickTranslate auto-detects which language each source file belongs to. Detection priority:

1. **Folder name:** `Corrections_ENG/` → eng, or `ENG/` → eng
2. **File name suffix:** `corrections_eng.xlsx` → eng, `languagedata_ger.xml` → ger
3. **Hyphenated codes work:** `ZHO-CN`, `spa-es`, `por-br` (case-insensitive)

Folder-based organization is most reliable. For 5 languages, create 5 subfolders.

### The Golden Rule

After every TRANSFER, a cleanup pass enforces: **if StrOrigin is empty → Str must be empty**. This prevents orphan translations on deleted/placeholder strings. Runs automatically.

### Failure Reports

When corrections fail to match, reports are generated at:

```
Failed Reports/YYMMDD/source_folder_name/
├── failed_eng.xml                        ← Unmerged corrections (reusable as source)
├── failed_fre.xml
└── FailureReport_YYMMDD_HHMMSS.xlsx     ← 3-sheet Excel (Summary, Breakdown, Details)
```

### Failure Status Codes

| Code | Meaning |
|------|---------|
| `UPDATED` | Correction applied successfully |
| `UNCHANGED` | Matched but value already correct |
| `NOT_FOUND` | StringID does not exist in target |
| `STRORIGIN_MISMATCH` | StringID exists but StrOrigin text differs |
| `SKIPPED_TRANSLATED` | Already translated ("Only untranslated" scope) |
| `SKIPPED_NON_SCRIPT` | Not in Dialog/Sequencer (StringID-Only mode) |
| `SKIPPED_EXCLUDED` | In excluded subfolder (NarrationDialog or user-excluded) |

### Korean Correction Filter

TRANSFER silently skips rows where the Correction column contains Korean text (meaning it hasn't actually been translated yet). Empty corrections are also skipped.

---

## 7. Pre-Submission Checks

Three quality checks that scan Source folder files before submission. Output goes to `Presubmission Checks/`.

### Check Korean

Finds entries in non-KOR `languagedata_*.xml` files where `Str` still contains Korean text (= untranslated).

- Output: `Presubmission Checks/Korean/korean_eng_YYYYMMDD.xml`

### Check Patterns

Validates that `{code}` placeholders in translations match the placeholders in StrOrigin. Catches missing, extra, or renamed placeholders.

- Example: StrOrigin has `{Item}` but translation has `{Weapon}` → flagged
- Output: `Presubmission Checks/PatternErrors/pattern_eng_YYYYMMDD.xml`

### Check Quality

Two-part scan:

1. **Wrong script detection** — finds characters from the wrong writing system (e.g., Cyrillic in a French file)
2. **AI hallucination detection** — finds common machine translation artifacts: AI phrases ("I'd be happy to help"), extreme length ratios (5x+ longer than source), forward slashes in non-code text

- Output: `Presubmission Checks/QualityCheck/quality_eng_YYYYMMDD.xlsx` (two tabs: "Language Issues" and "AI Hallucination")

### Check ALL

Runs all three checks in sequence.

---

## 8. EventName Resolution

When your Excel has an **EventName** column instead of StringID, QuickTranslate resolves it through a 3-step waterfall:

1. **DialogVoice generation** — If DialogVoice column exists, strips the DialogVoice prefix from EventName to derive StringID
2. **Keyword extraction** — Looks for `aidialog`/`questdialog` keywords in EventName and extracts the StringID portion
3. **Export folder lookup** — Searches EXPORT `.loc.xml` files for `SoundEventName` attribute matches

If all 3 steps fail: `MISSING EVENTNAME` (appears in failure report).

**Per-row priority:** If both StringID and EventName columns exist, StringID is used when present. EventName is the fallback for rows where StringID is empty.

---

## 9. Quick Reference

### All Buttons

| Button | What It Does |
|--------|-------------|
| **Generate** | LOOKUP: source folder → Excel with 17 languages |
| **TRANSFER** | Write corrections to target XML files |
| **Lookup** | Look up one StringID → all translations |
| **Browse** / **Find All** | Reverse lookup: text file → find StringIDs |
| **Find Missing Translations** | Compare source vs target → gap report |
| **Exclude...** | Configure excluded paths for Find Missing |
| **Check Korean** | Find untranslated Korean in non-KOR files |
| **Check Patterns** | Validate {code} placeholders match |
| **Check Quality** | Wrong script + AI hallucination detection |
| **Check ALL** | Run all three checks |
| **Open Results Folder** | Open Presubmission Checks folder |
| **Save Settings** | Save LOC/EXPORT path changes |
| **Clear Log** | Clear the log area |
| **Clear All** | Reset all fields |

### Output Locations

| Location | Contents |
|----------|---------|
| `Output/` | LOOKUP results (Excel), Missing Translation reports, Close folders |
| `Presubmission Checks/` | Check Korean (XML), Check Patterns (XML), Check Quality (Excel) |
| `Failed Reports/YYMMDD/` | TRANSFER failure reports (XML + Excel) |

### Supported Languages

Auto-discovered from LOC folder. Standard production set:

`eng`, `fre`, `ger`, `ita`, `jpn`, `kor`, `pol`, `por-br`, `rus`, `spa-es`, `spa-mx`, `tur`, `zho-cn`, `zho-tw`

Additional languages (e.g., `tha`, `vie`, `ind`, `msa`) are auto-discovered if present.

### Settings Files

| File | Purpose |
|------|---------|
| `settings.json` | LOC and EXPORT folder paths |
| `exclude_rules.json` | Excluded folders for Find Missing (managed via Exclude dialog) |

### Fuzzy Matching Details

Technology: KR-SBERT (Korean Sentence-BERT) with FAISS IndexFlatIP. Model folder: `KRTransformer/` next to the app. First load takes ~30 seconds.

| Threshold | Use Case |
|-----------|----------|
| 0.95 | Only minor spelling/whitespace changes |
| 0.85 (default) | General-purpose rewording detection |
| 0.80 | Significant Korean text changes |
| 0.70 | Maximum coverage (risk of false positives) |

---

## 10. Troubleshooting

**Match type is greyed out** — Source files are missing required columns for that match type. Check column headers against the table in Section 3.

**TRANSFER button disabled** — Substring mode is selected. Substring is LOOKUP-only. Switch to StringID-Only, Strict, or StrOrigin Only.

**Korean corrections skipped** — Correction column still contains Korean text. TRANSFER only writes non-Korean corrections. Ensure corrections are actually translated.

**0 matches found** — Checklist:
- Correct match type selected?
- Column headers match expected names?
- Source and target paths correct?
- Perforce synced recently?
- For Strict: has Korean source text changed? (try Fuzzy precision)
- For StringID-Only: are strings in Dialog/ or Sequencer/ categories?

**EventName not resolved** — The 3-step waterfall could not find a match. Check if EventName exists in EXPORT folder, verify DialogVoice column if present, or use StringID directly.

**settings.json issues** — Use double backslashes (`\\`). No trailing backslash. Valid JSON (check commas/brackets). Delete `settings.json` and restart to reset to F: drive defaults.

**ToSubmit checkbox** — When checked, automatically includes correction files from the `ToSubmit/` folder alongside your selected source folder. Useful for staging pending corrections.
