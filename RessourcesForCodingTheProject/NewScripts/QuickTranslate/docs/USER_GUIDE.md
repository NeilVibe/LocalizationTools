# QuickTranslate User Guide

**Version 4.0** | February 2026

---

## 1. What is QuickTranslate?

QuickTranslate is a desktop tool for localization teams working with XML language data files. It writes translated corrections into `languagedata_*.xml` files, looks up Korean text across all production languages, and finds untranslated strings.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          QuickTranslate                                 │
│                                                                         │
│   ┌──────────────────────────────────────────┐   ┌───────────────────┐  │
│   │  TRANSFER                   [PRIMARY]    │   │  LOOKUP           │  │
│   │                                          │   │                   │  │
│   │  Write corrections from Excel/XML into   │   │  Search Korean    │  │
│   │  target languagedata_*.xml files.        │   │  text across 17   │  │
│   │                                          │   │  languages.       │  │
│   │  ★ Main workflow for translators         │   │  Export to Excel. │  │
│   │  ★ Voice dubbing teams (EventName)       │   │  Read-only.       │  │
│   │  ★ Batch folder-to-folder processing     │   │                   │  │
│   └──────────────────────────────────────────┘   └───────────────────┘  │
│                                                                         │
│   Also: Find Missing Translations, Pre-Submission Quality Checks        │
└─────────────────────────────────────────────────────────────────────────┘
```

> **If you only learn one feature, learn TRANSFER.** It is the core workflow: take your corrections in Excel, match them to the right strings in XML, and write them in one click.

---

## Quick Start: Your First TRANSFER in 5 Minutes

> New to QuickTranslate? Follow these 5 steps. Corrections written to XML in minutes.

### How TRANSFER Works

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│   Your Excel    │  ────→  │  QuickTranslate   │  ────→  │   XML files     │
│   corrections   │         │    TRANSFER       │         │  Str= updated!  │
└─────────────────┘         └──────────────────┘         └─────────────────┘
  Correction column            matches by ID               languagedata_*.xml
```

### Step 1 — Create Your Excel File

QuickTranslate reads column headers (Row 1) to understand your data. Headers are case-insensitive and can appear in any order.

**Example A — Standard Corrections** (translators, QA teams)

The minimum for Strict match: **StringID** + **StrOrigin** + **Correction**.

```
┌──────────────┬───────────────────────┬───────────────────────────────┐
│  StringID    │  StrOrigin            │  Correction                   │
│  ··········  │  ···················  │  ··························   │
│  The unique  │  The original Korean  │  YOUR TRANSLATION             │
│  ID from XML │  text from XML        │  This gets written to XML!    │
├──────────────┼───────────────────────┼───────────────────────────────┤
│  quest_001   │  퀘스트를 완료하세요   │  Complete the quest           │
│  quest_002   │  아이템을 획득하세요   │  Obtain the item              │
│  npc_greet   │  안녕하세요, 모험가!   │  Hello, adventurer!           │
└──────────────┴───────────────────────┴───────────────────────────────┘
```

> 💡 Where do I get StringID and StrOrigin? Run a **LOOKUP** first (Generate button). The output Excel contains both columns — copy them into your correction file and add translations in the Correction column.

**Example B — Voice Dubbing Team** (audio pipeline, script corrections)

Voice teams often work with **EventName** and **DialogVoice** instead of StringID. QuickTranslate auto-resolves these to the correct StringID.

```
┌────────────────────────────┬──────────────┬───────────────────────────┐
│  EventName                 │  DialogVoice │  Correction               │
│  ························  │  ··········  │  ·······················  │
│  Sound event name          │  Voice actor │  YOUR TRANSLATION         │
│  from audio pipeline       │  prefix      │  This gets written to XML!│
├────────────────────────────┼──────────────┼───────────────────────────┤
│  Play_AIDialog_npc01_      │  npc01       │  I have a task for you.   │
│   quest_greeting           │              │                           │
│  Play_QuestDialog_         │  player      │  What do you need?        │
│   player_response_01       │              │                           │
└────────────────────────────┴──────────────┴───────────────────────────┘
```

QuickTranslate resolves EventName → StringID using a 3-step waterfall:

1. **DialogVoice prefix** — strips DialogVoice from EventName to derive StringID
2. **Keyword extraction** — finds `aidialog`/`questdialog` keywords and extracts the StringID portion
3. **Export folder lookup** — searches `.loc.xml` files for matching `SoundEventName` attributes

> You can mix both styles in the same file. If a row has a **StringID** value, that takes priority. **EventName** is the fallback for rows where StringID is empty.

**Full Column Reference:**

| Column | Purpose | Required? |
|--------|---------|-----------|
| **StringID** | Unique string identifier from XML | Required for Strict/StringID-Only |
| **StrOrigin** | Original Korean text from XML | Required for Strict/StrOrigin Only |
| **Correction** | Your translated text (gets written to XML) | Always required for TRANSFER |
| **EventName** | Sound event name (alternative to StringID) | Optional — for voice/dialogue teams |
| **DialogVoice** | Voice actor prefix (helps resolve EventName) | Optional — used with EventName |

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

> ⚠️ **No language = no TRANSFER.** If QuickTranslate cannot detect the language, the file is skipped. Use language-named folders (`ENG/`, `FRE/`) or add the language code to the filename (`corrections_eng.xlsx`).

### Step 3 — Open QuickTranslate

Set the **Source** path to your corrections folder (the parent folder, e.g., `MyCorrections/`).

### Step 4 — Select Match Type

Pick **Strict** (safest — verifies both StringID and Korean text match before writing).

| Match Type | When To Use | Required Columns |
|------------|-------------|------------------|
| **Strict** | Default choice — highest precision | StringID + StrOrigin + Correction |
| **StringID-Only** | Dialogue/Sequencer scripts (long Korean text) | StringID + Correction |
| **StrOrigin Only** | Fill all entries sharing the same Korean text | StrOrigin + Correction |

### Step 5 — Click TRANSFER

Review the transfer plan in the log area, then click **Yes** to confirm.

```
┌───────────────────────────────────────────────────────────────────────┐
│                       TRANSFER Status Codes                           │
├────────────────────────┬──────────────────────────────────────────────┤
│  UPDATED               │  Correction applied successfully             │
│  UNCHANGED             │  Already has this exact value — no change    │
│  NOT_FOUND             │  StringID does not exist — check for typos   │
│  STRORIGIN_MISMATCH    │  StringID exists but Korean text differs     │
│  SKIPPED_TRANSLATED    │  Already translated (Only untranslated mode) │
│  SKIPPED_NON_SCRIPT    │  Not in Dialog/Sequencer (StringID-Only)     │
│  MISSING EVENTNAME     │  EventName could not be resolved to StringID │
└────────────────────────┴──────────────────────────────────────────────┘
```

> Check `Failed Reports/` for any corrections that did not apply. The failure XML files can be reused as TRANSFER source after fixing the issues.

---

## 2. TRANSFER — Complete Guide

TRANSFER writes the **Correction** column from your Excel/XML file into the `Str` attribute of matching `<LocStr>` elements inside target `languagedata_*.xml` files.

```
 Source (your corrections)              QuickTranslate                Target (game XML)
 +-----------------------+             +---------------+             +-------------------+
 | StringID  | Correction|   ──────→   |   TRANSFER    |   ──────→   | <LocStr           |
 | quest_001 | Complete  |             |   engine      |             |   StringId="..."  |
 | npc_greet | Hello!    |             +-------+-------+             |   Str="Complete"  |
 +-----------------------+                     |                     +-------------------+
                                    match by ID + verify               languagedata_eng.xml
```

> ⚠️ **TRANSFER is destructive.** It writes to XML files in your Perforce workspace. A confirmation dialog shows the full transfer plan before anything is written. Always P4 sync before transferring.

---

### 2.1 Excel File Setup

QuickTranslate detects columns by **header name** (case-insensitive, any column order). Row 1 must be headers. Data starts at Row 2.

#### What Each Column Means

| Column | What to put | Where to get it |
|--------|------------|-----------------|
| **StringID** | The unique identifier of the string (e.g. `quest_001`) | From LOOKUP output Excel, or from XML `StringID=` attribute |
| **StrOrigin** | The **original Korean text** currently in the XML — copy exactly as-is, including `<br/>` tags | From LOOKUP output — never retype manually |
| **Correction** | **Your translated text.** This is what gets written into the XML `Str=` attribute. | **You write this!** |
| **EventName** | Audio event name (alternative to StringID for dialogue lines) | From audio/dubbing pipeline, or from `.loc.xml` `SoundEventName=` attribute |
| **DialogVoice** | Voice actor prefix (helps resolve EventName to StringID) | From audio pipeline metadata |

#### Accepted Header Name Variants

All lookups are **case-insensitive**. These all work:

| Logical Column | Accepted Variants |
|----------------|-------------------|
| **StringID** | `StringID`, `StringId`, `string_id`, `STRINGID` |
| **StrOrigin** | `StrOrigin`, `Str_Origin`, `str_origin`, `STRORIGIN` |
| **Correction** | `Correction`, `correction`, `corrected` |
| **EventName** | `EventName`, `event_name`, `SoundEventName` |
| **DialogVoice** | `DialogVoice`, `dialog_voice` |

#### Required Columns by Match Type

| Match Type | Required | Optional |
|------------|----------|----------|
| **Strict** | StringID + StrOrigin + Correction | EventName, DialogVoice |
| **StringID-Only** | StringID + Correction | StrOrigin, EventName, DialogVoice |
| **StrOrigin Only** | StrOrigin + Correction | StringID, EventName, DialogVoice |

If required columns are missing, that match type radio button is **greyed out** in the GUI. The log area shows which columns were detected when you browse to a source folder.

#### ✅ Correct vs ❌ Wrong Examples

```
+=========================================================================+
| ✅ CORRECT — Headers in Row 1, data starts Row 2                        |
+=========================================================================+
|  StringID    |  StrOrigin              |  Correction                    |
|--------------|-------------------------|--------------------------------|
|  quest_001   |  퀘스트를 완료하세요     |  Complete the quest            |
|  quest_002   |  아이템을 획득하세요     |  Obtain the item               |
|  npc_greet   |  안녕하세요, 모험가!     |  Hello, adventurer!            |
+=========================================================================+
```

```
+=========================================================================+
| ❌ WRONG — Missing Correction column                                     |
+=========================================================================+
|  StringID    |  StrOrigin              |                                 |
|--------------|-------------------------| ← No Correction column!         |
|  quest_001   |  퀘스트를 완료하세요     |   TRANSFER has nothing to      |
|  quest_002   |  아이템을 획득하세요     |   write. File is SKIPPED.      |
+=========================================================================+
```

```
+=========================================================================+
| ❌ WRONG — Correction is still Korean                                    |
+=========================================================================+
|  StringID    |  StrOrigin              |  Correction                    |
|--------------|-------------------------|--------------------------------|
|  quest_001   |  퀘스트를 완료하세요     |  퀘스트를 완료해 주세요         |
|              |                         |  ^^^ Still Korean! Row is      |
|              |                         |      silently SKIPPED.         |
+=========================================================================+
```

> 💡 **Pro tip:** Run a **LOOKUP** first (Generate button). The output Excel has StringID and StrOrigin pre-filled with correct values. Copy them into your corrections file and add a Correction column with your translations. This guarantees matching header names and values.

---

### 2.2 For Voice Dubbing Teams: EventName → StringID Resolution

Voice dubbing teams work with audio scripts that have **EventName** and **DialogVoice** columns but often do **not** have StringID. QuickTranslate resolves EventNames to StringIDs automatically through a **3-step waterfall**.

#### Per-Row Priority Rule

If both **StringID** and **EventName** columns exist in the same Excel file:

- **StringID takes priority** when present in that row
- **EventName is the fallback** only for rows where StringID is empty

This lets you mix: some rows with direct StringIDs, others with EventNames.

#### The 3-Step Resolution Waterfall

```
 EventName from Excel
        |
        v
 +------+------+       +-------+------+       +-------+-------+
 | Step 1       |  NO   | Step 2        |  NO   | Step 3         |  NO
 | DialogVoice  +──────>| Keyword       +──────>| Export Folder  +─────> MISSING
 | Generation   |       | Extraction    |       | Lookup         |      EVENTNAME
 +------+-------+       +-------+------+       +-------+-------+
        | YES                    | YES                  | YES
        v                        v                      v
     StringID                 StringID               StringID
```

**Step 1 — DialogVoice Generation** (requires DialogVoice column)

Strips the DialogVoice prefix from EventName. The remaining suffix becomes the StringID.

```
  EventName:   "John_Conversation_Greeting_001"
  DialogVoice: "John_Conversation"
                ^^^^^^^^^^^^^^^^^ strip this
  Result:      "Greeting_001"  ← this is the StringID
```

Case-insensitive matching. Preserves original case from EventName in the result.

**Step 2 — Keyword Extraction** (no DialogVoice needed)

Searches EventName for `aidialog` or `questdialog` keywords (case-insensitive). Returns everything from the keyword onward.

```
  EventName:   "VO_QuestDialog_NPC_Quest001_001"
                    ^^^^^^^^^^^ keyword found at position 3
  Result:      "QuestDialog_NPC_Quest001_001"  ← StringID
```

**Step 3 — Export Folder Lookup** (scans `.loc.xml` files)

Scans all XML files in the EXPORT folder for elements with a `SoundEventName` attribute matching the EventName. Returns the `StringId` attribute from that same element.

```
  EventName:   "SE_Ambient_Forest_Bird_001"
                         |
                         v
  EXPORT XML:  <LocStr SoundEventName="SE_Ambient_Forest_Bird_001"
                       StringId="Forest_Bird_001" ... />
                         |
  Result:      "Forest_Bird_001"  ← StringID from XML
```

This step builds a mapping by scanning all `.loc.xml` files once, then caches it for the session.

**If All 3 Steps Fail:**

The row is recorded as `MISSING EVENTNAME` in a separate failure report:
`Failed Reports/YYMMDD/source_name/MissingEventNames_YYYYMMDD_HHMMSS.xlsx`

This report has 4 columns: EventName, Correction Text, Source File, Status.

---

### 2.3 Match Types (for TRANSFER)

Three match types support TRANSFER. (Substring is LOOKUP-only — too imprecise for writing.)

#### Strict (StringID + StrOrigin) — Safest, Recommended Default

Requires **both** StringID and StrOrigin to match before writing. This is the highest-precision mode.

**The 4-Step Matching Cascade:**

Before declaring a correction as NOT_FOUND or STRORIGIN_MISMATCH, QuickTranslate tries four progressively looser comparisons:

```
  Step 1: Exact
  +------------------------------------------+
  | Case-insensitive StringID                 |
  | + normalized StrOrigin                    |
  | (HTML unescape, whitespace collapse,      |
  |  &desc; removal)                          |
  +------------------------------------------+
           | no match
           v
  Step 2: Lowercase
  +------------------------------------------+
  | Both sides fully lowercased               |
  +------------------------------------------+
           | no match
           v
  Step 3: Normalized
  +------------------------------------------+
  | HTML unescape + whitespace collapse       |
  | + &desc; removal on both sides            |
  +------------------------------------------+
           | no match
           v
  Step 4: No-Space Fallback
  +------------------------------------------+
  | Remove ALL whitespace from both sides     |
  | and compare                               |
  +------------------------------------------+
           | no match
           v
  NOT_FOUND or STRORIGIN_MISMATCH
  (StringID exists but text differs = MISMATCH)
  (StringID not found at all = NOT_FOUND)
```

**Fuzzy Precision** (optional): After the 4-step cascade fails, enables KR-SBERT semantic similarity search. Uses FAISS IndexFlatIP to find the closest StrOrigin match.

| Threshold | Use Case |
|-----------|----------|
| 0.95 | Minor spelling/whitespace changes only |
| **0.85** (default) | General-purpose rewording detection |
| 0.80 | Significant Korean text changes |
| 0.70 | Maximum coverage (risk of false positives) |

When fuzzy is enabled, the transfer runs in **two passes**: Pass 1 (exact 4-step cascade), then Pass 2 (FAISS fuzzy on unconsumed corrections only). The log shows both passes with match counts.

> **When to use Strict:** Non-SCRIPT categories (System/, World/, Platform/, None/). Any time precision matters more than speed.

#### StringID-Only — For SCRIPT Categories

Matches by **StringID alone**. Ignores StrOrigin completely. **Restricted to SCRIPT categories only** — the Dialog/ and Sequencer/ folders in the EXPORT structure.

```
  SCRIPT categories (StringID-Only processes these):
  +--------------------------------------------+
  | export__/Dialog/AIDialog/                   |
  | export__/Dialog/QuestDialog/                |
  | export__/Sequencer/                         |
  +--------------------------------------------+

  EXCLUDED (skipped, status SKIPPED_EXCLUDED):
  +--------------------------------------------+
  | export__/Dialog/NarrationDialog/            |
  +--------------------------------------------+

  NON-SCRIPT (skipped, status SKIPPED_NON_SCRIPT):
  +--------------------------------------------+
  | export__/System/   export__/World/          |
  | export__/None/     export__/Platform/       |
  +--------------------------------------------+
```

Non-SCRIPT StringIDs are silently skipped with status `SKIPPED_NON_SCRIPT`. NarrationDialog subfolder StringIDs get `SKIPPED_EXCLUDED`.

> **When to use StringID-Only:** Voice dubbing corrections for dialogue/cutscene text. StrOrigin for dialogue lines is often very long and may have changed since extraction — StringID is more stable.

#### StrOrigin Only — Fan-Out Behavior

Matches by **StrOrigin text alone**, ignoring StringID. One correction fills **all** entries sharing the same StrOrigin across the target XML. This is "fan-out" behavior.

```
  Your Excel:
  +-------------------------------+
  | StrOrigin     | Correction    |
  | 확인           | Confirm       |   ← 1 row
  +-------------------------------+

  Target XML has 47 entries with StrOrigin="확인":
  quest_confirm, ui_button_ok, dialog_yes, ...

  Result: ALL 47 entries get Str="Confirm"  ← fan-out
```

Defaults to **"Only untranslated"** scope for safety. Fan-out + "Transfer ALL" can overwrite good translations. A safety warning dialog appears if you switch to "Transfer ALL".

Fuzzy precision is available (same as Strict — two-pass with FAISS fallback on unconsumed corrections).

> **When to use StrOrigin Only:** Bulk-filling untranslated strings that share the same Korean source text. Common for UI labels, button text, status messages.

#### Comparison Table (TRANSFER-Capable Match Types Only)

| | Strict | StringID-Only | StrOrigin Only |
|---|:-:|:-:|:-:|
| **Precision** | Highest | Medium | Medium |
| **Fan-out** | No | No | Yes |
| **Fuzzy available** | Yes | No | Yes |
| **Default scope** | Transfer ALL | Transfer ALL | Only untranslated |
| **Best for** | Non-SCRIPT | Dialog/Sequencer | Bulk UI text |
| **Risk level** | Lowest | Low | Medium (fan-out) |

---

### 2.4 Transfer Scope

| Scope | Behavior | Default For |
|-------|----------|-------------|
| **Transfer ALL** | Overwrite every match, even if the entry already has a non-Korean translation | Strict, StringID-Only |
| **Only untranslated** | Only fill entries where `Str` is empty or still contains Korean text | StrOrigin Only |

The scope toggle is in the GUI next to the match type selection.

> ⚠️ **Safety warning:** Switching StrOrigin Only to "Transfer ALL" triggers a confirmation dialog. Fan-out can overwrite correct translations across dozens of entries with a single row. Use "Only untranslated" unless you are certain.

---

### 2.5 Language Detection

QuickTranslate auto-detects which language each source file belongs to. This determines which `languagedata_*.xml` target file receives the corrections.

**Detection priority (checked in order):**

1. **Folder name** — A folder named as a valid language code, or with a language suffix
   - `ENG/` — all files inside mapped to ENG
   - `Corrections_FRE/` — all files inside mapped to FRE
   - `ZHO_CN/` — resolved to ZHO-CN (hyphenated)

2. **File name suffix** — Language code after the last underscore
   - `corrections_eng.xlsx` — mapped to ENG
   - `languagedata_ger.xml` — mapped to GER
   - `hotfix_SPA.xml` — mapped to SPA

3. **Hyphenated codes** — Regional variants are fully supported
   - `ZHO-CN`, `ZHO-TW`, `SPA-ES`, `SPA-MX`, `POR-BR` (case-insensitive)

Valid language codes are **auto-discovered** from the LOC folder (scans for `languagedata_*.xml` filenames). No manual configuration needed.

**Recommended folder structure for multi-language corrections:**

```
  MyCorrections/                ← set this as Source path
  │
  ├── ENG/
  │   └── corrections.xlsx      ← English translations
  │
  ├── FRE/
  │   ├── corrections.xlsx      ← French translations
  │   └── extra_fixes.xlsx      ← multiple files per language OK
  │
  └── ZHO_CN/
      └── corrections.xlsx      ← Simplified Chinese
```

> ⚠️ **No language = no TRANSFER.** If QuickTranslate cannot detect the language from folder name or filename, the file is skipped. The transfer plan tree shows `[!!] UNRECOGNIZED` for these items.

---

### 2.6 The Golden Rule

> **If StrOrigin is empty, Str must be empty.**

After every TRANSFER, a post-processing pipeline runs automatically on each modified XML file:

1. **Normalize newlines** — Converts all wrong newline representations (`&#10;`, `\n`, `<BR>`, `<br >`, etc.) to `<br/>`, the only correct format
2. **Empty StrOrigin enforcement** — Clears `Str` on any `<LocStr>` element where `StrOrigin` is empty or whitespace-only

This prevents orphan translations on deleted or placeholder strings. You never need to run this manually — it executes after every TRANSFER automatically.

---

### 2.7 Failure Reports

When corrections fail to match, QuickTranslate generates reports in the `Failed Reports/` directory.

**Directory structure:**

```
  Failed Reports/
  └── 260212/                              ← date (YYMMDD)
      └── source_folder_name/
          ├── failed_eng.xml               ← unmerged corrections (XML)
          ├── failed_fre.xml
          ├── FailureReport_260212_143022.xlsx   ← 3-sheet Excel report
          └── MissingEventNames_260212_143022.xlsx  ← if EventName resolution failed
```

**Failed XML files are reusable.** After fixing the issues (e.g. updating StringIDs, re-syncing from Perforce), you can point QuickTranslate at the failed XML files as a new source and re-run TRANSFER.

**3-Sheet Excel Failure Report:**

| Sheet | Contents |
|-------|----------|
| **Summary** | Overall statistics: total corrections, updated, not found, skipped |
| **Breakdown** | Per-language breakdown with match counts |
| **Details** | Every correction row with its status code, old value, new value |

#### All Status Codes

| Status | Icon | Meaning |
|--------|------|---------|
| `UPDATED` | ✅ | Correction applied successfully — `Str` was written |
| `UNCHANGED` | — | StringID matched but `Str` already had the exact same value |
| `NOT_FOUND` | !! | StringID does not exist anywhere in the target XML |
| `STRORIGIN_MISMATCH` | !! | StringID exists but the Korean text differs from your StrOrigin — source XML may have been updated |
| `SKIPPED_TRANSLATED` | — | Entry already has a non-Korean translation ("Only untranslated" scope) |
| `SKIPPED_NON_SCRIPT` | — | StringID is not in Dialog/ or Sequencer/ categories (StringID-Only mode) |
| `SKIPPED_EXCLUDED` | — | StringID is in an excluded subfolder (NarrationDialog, or user-configured exclusion) |
| `MISSING EVENTNAME` | !! | All 3 waterfall steps failed to resolve EventName to StringID |

> 💡 **Most common failure:** `STRORIGIN_MISMATCH` — means the Korean source text was updated in Perforce after you extracted it. Re-run LOOKUP to get the current StrOrigin, or enable Fuzzy precision to match despite the rewording.

---

### 2.8 Korean Correction Filter

TRANSFER **silently skips** rows where the Correction column:

- Contains Korean text (detected by Unicode range analysis — the "correction" has not been translated yet)
- Is empty or whitespace-only

No error is logged. No failure report entry is created. The row is simply ignored.

This prevents accidentally overwriting translated text with untranslated Korean, which would happen if a translator's Excel file has rows they haven't gotten to yet.

---

## 3. Pre-Submission Checks

Three quality gates that scan your Source folder **before** you submit to Perforce. Each check reads `languagedata_*.xml` files, groups them by language, and writes results to `Presubmission Checks/`. Nothing is modified — these are read-only scans that catch mistakes before they reach production.

```
┌─────────────────────────────────────────────────────────────────────┐
│                  🛡️ PRE-SUBMISSION CHECKS                          │
│                                                                     │
│   📂 Source folder          ──→   📂 Presubmission Checks/          │
│   (your languagedata XML)         ├── Korean/                       │
│                                   ├── PatternErrors/                │
│                                   └── QualityReport/                │
│                                                                     │
│   Read-only scans. Your XML files are NEVER modified.              │
└─────────────────────────────────────────────────────────────────────┘
```

---

### 🔍 Check Korean

Finds entries in **non-KOR** files where `Str` still contains Korean characters — meaning the string was never translated.

```
┌───────────────────────────────────────────────────────────────────────┐
│  ⚠️  CAUGHT: Korean in languagedata_eng.xml                          │
│                                                                       │
│  StringID="quest_complete_msg"                                        │
│  StrOrigin="퀘스트를 완료했습니다!"                                      │
│  Str="퀘스트를 완료했습니다!"   ← 🚩 Still Korean! Never translated.    │
│                                                                       │
│  Expected:                                                            │
│  Str="Quest completed!"        ← ✅ Actual translation                │
└───────────────────────────────────────────────────────────────────────┘
```

**Output:** `Presubmission Checks/Korean/korean_findings_eng.xml`

One XML file per language, containing every `<LocStr>` element that still has Korean in its `Str` attribute. Only non-KOR languages are scanned (Korean in `languagedata_kor.xml` is expected).

> Entries containing `staticinfo:knowledge` in Str or StrOrigin are automatically excluded — pattern codes in those entries are not relevant.

---

### 🔍 Check Patterns

Validates that `{code}` placeholders in the translation match the placeholders in the original Korean text. Catches missing, extra, or renamed placeholders that would cause runtime errors or display bugs.

```
┌───────────────────────────────────────────────────────────────────────┐
│  ✅ CORRECT — Placeholders match                                      │
│                                                                       │
│  StrOrigin="{UserName}님, {Item}을 획득했습니다!"                       │
│  Str="{UserName}, you obtained {Item}!"                               │
│       ^^^^^^^^^^              ^^^^^^                                  │
│       Present                 Present         ← All good              │
├───────────────────────────────────────────────────────────────────────┤
│  ❌ WRONG — Placeholder renamed                                       │
│                                                                       │
│  StrOrigin="{UserName}님, {Item}을 획득했습니다!"                       │
│  Str="{UserName}, you obtained {Weapon}!"                             │
│                                ^^^^^^^^                               │
│       {Item} → {Weapon}                       ← 🚩 FLAGGED           │
├───────────────────────────────────────────────────────────────────────┤
│  ❌ WRONG — Placeholder missing                                       │
│                                                                       │
│  StrOrigin="{Count}개의 {Item}을 사용합니다"                            │
│  Str="Use {Item}"                                                     │
│       {Count} missing                         ← 🚩 FLAGGED           │
└───────────────────────────────────────────────────────────────────────┘
```

**Output:** `Presubmission Checks/PatternErrors/pattern_errors_eng.xml`

Pattern matching is **normalized**: `{Staticinfo:Knowledge#123}` and `{Staticinfo:Knowledge#456}` are treated as the same pattern (`{Staticinfo:Knowledge#}`), so variable numeric suffixes do not trigger false positives.

---

### 🔍 Check Quality

A two-part scan that catches deeper issues: wrong writing systems and AI-generated artifacts.

#### Tab 1: Language Issues (Wrong Script)

Detects characters from the wrong Unicode script block in a translation. Each language has an expected script group:

| Script Group | Languages | Flags |
|:------------:|-----------|-------|
| Latin | ENG, FRE, GER, ITA, POL, POR-BR, SPA, TUR | Cyrillic, CJK, Arabic, Thai, ... |
| Cyrillic + Latin | RUS | CJK, Arabic, Thai, ... |
| Japanese (CJK + Kana + Latin) | JPN | Cyrillic, Arabic, Thai, ... |
| Chinese (CJK + Latin) | ZHO-CN, ZHO-TW | Cyrillic, Kana, Arabic, ... |

```
┌───────────────────────────────────────────────────────────────────────┐
│  🚩 CAUGHT: Cyrillic in languagedata_fre.xml                         │
│                                                                       │
│  StringID="npc_greeting_42"                                           │
│  Str="Bienvenue, аventurier!"                                         │
│              ^                                                        │
│              Cyrillic 'а' (U+0430), not Latin 'a' (U+0061)           │
│                                                                       │
│  Wrong Characters: а         Script: Cyrillic                        │
└───────────────────────────────────────────────────────────────────────┘
```

> `{code}` patterns and `<br/>` markup are stripped before scanning, so placeholder content does not trigger false positives. Hangul characters are never flagged here (the separate Check Korean handles those).

#### Tab 2: AI Hallucination

Detects common artifacts from machine translation / LLM output that slipped through review. Three detection methods:

| Detection | What It Catches | Example |
|-----------|----------------|---------|
| **AI Phrase** | Known AI self-reference phrases in 12 languages | `"As an AI, I cannot..."`, `"En tant qu'IA..."` |
| **Length Ratio** | Translation absurdly longer than source (5x+ chars for CJK, 10x+ words for Latin) | 5-word Korean source becomes 60-word English paragraph |
| **Forward Slash** | `/` present in Str but absent from StrOrigin | `"Attack/Defense"` when source has `"공격과 방어"` |

The AI phrase bank (`ai_hallucination_phrases.json`) contains known phrases in English plus 11 localized languages. English phrases are always checked regardless of target language (AI tools sometimes output English fragments in non-English translations).

**Output:** `Presubmission Checks/QualityReport/quality_report_eng.xlsx`

Excel file with two tabs: **"Language Issues"** and **"AI Hallucination"**. Each tab has autofilter and frozen header row for quick triage.

---

### 🔍 Check ALL

Runs all three checks in sequence with a single click. Same as running Check Korean, then Check Patterns, then Check Quality — just faster to trigger.

---

### When to Run Checks

| Situation | Which Check | Why |
|-----------|-------------|-----|
| After TRANSFER | Check Korean + Check Patterns | Verify no untranslated strings slipped through and placeholders survived the merge |
| Before Perforce submit | **Check ALL** | Full quality gate — catch everything before it hits the build |
| Reviewing AI translations | Check Quality | Specifically targets AI hallucination and wrong-script artifacts |
| Quick sanity check | **Check ALL** | Takes seconds, covers everything, no reason not to |
| After bulk import | Check Patterns | Placeholder mismatches are the most common bulk-import casualty |

> 💡 **Pro tip:** Make Check ALL part of your pre-submit ritual. A 10-second scan can prevent a broken build that affects the entire team.

---

## 4. LOOKUP & Other Tools

> These features are read-only and useful for research, verification, and gap analysis. They don't modify any files. All output goes to `Output/`.

### 4.1 Generate (Source Folder → Excel)

Scans all Excel and XML files in the Source folder, matches Korean text against stringtables in the EXPORT folder, and exports a single Excel with all 17 language columns.

- Accepts mixed `.xlsx` + `.xml` / `.loc.xml` in the same folder
- Output: `Output/QuickTranslate_YYYYMMDD_HHMMSS.xlsx`
- Columns: KOR (Input) | Status | StringID | ENG | FRE | GER | ...

| Status | Meaning |
|--------|---------|
| `MATCHED` | Exactly 1 hit |
| `MULTI (N)` | N entries share the same StrOrigin |
| `NOT FOUND` | No match in any EXPORT file |

**Substring match type:** For quick "what does this Korean mean?" lookups. No column headers needed — just paste Korean text into Column A. This match type is LOOKUP-only; TRANSFER is not available.

### 4.2 StringID Lookup

Type or paste a single StringID into the text field, click **Lookup**. Returns all 17 translations instantly.

- Output: `Output/StringID_<ID>_YYYYMMDD_HHMMSS.xlsx`
- No source file needed — works from the text field directly

### 4.3 Reverse Lookup

Browse to a `.txt` file containing one string per line in any language. QuickTranslate auto-detects the language and finds the matching StringIDs.

- Output: `Output/ReverseLookup_YYYYMMDD_HHMMSS.xlsx`
- `NOT FOUND` = no match for that string
- `NO TRANSLATION` = StringID exists but `Str` attribute is empty for that language

### 4.4 Find Missing Translations

Compares a Source folder against the Target LOC folder to find untranslated strings (where `Str` is empty or still Korean).

**Parameter dialog — 4 match modes:**

| Mode | Speed | When to Use |
|------|-------|-------------|
| StringID + KR (Strict) | Instant | Default. Catches 95% of cases |
| StringID + KR (Fuzzy) | Minutes | Korean text was reworded since export |
| KR only (Strict) | Fast | StringID changed but Korean is identical |
| KR only (Fuzzy) | Slow | Maximum coverage, higher false-positive risk |

**Two output types per language:**

- **Excel report:** `Output/MISSING_ENG_YYYYMMDD_HHMMSS.xlsx` — category-clustered list of untranslated strings
- **Close folder:** `Output/Close_ENG/` — mirrors EXPORT folder structure. These files are directly usable as a TRANSFER source

**Exclude Dialog:** Click **Exclude...** to configure folders excluded from results (e.g., `System/Gimmick`, `System/MultiChange`). Settings are saved to `exclude_rules.json` and persist between sessions.

---

## 5. Installation

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
├── settings.json              ← LOC + EXPORT paths (auto-created on first run)
├── exclude_rules.json         ← Find Missing exclusions (auto-created)
├── KRTransformer/             ← KR-SBERT model (for fuzzy matching)
├── Source/                    ← Default source folder (pre-populated in GUI)
├── Output/                    ← LOOKUP results (Excel files)
├── Presubmission Checks/      ← Quality check results
└── Failed Reports/             ← TRANSFER failure reports
```

---

## 6. Settings & Configuration

### settings.json

| Key | Value | Example |
|-----|-------|---------|
| `loc_folder` | Path to LOC folder containing `languagedata_*.xml` files | `F:\\perforce\\cd\\mainline\\...\\loc` |
| `export_folder` | Path to EXPORT folder containing categorized `.loc.xml` files | `F:\\perforce\\cd\\mainline\\...\\export__` |

Rules: double backslashes (`\\`), no trailing backslash, valid JSON. Delete the file and restart to reset to F: drive defaults.

### exclude_rules.json

Managed via the **Exclude...** dialog in the GUI. Stores a list of relative paths to exclude from Find Missing results. Do not edit manually.

```json
{
  "excluded_paths": [
    "System/Gimmick",
    "System/MultiChange"
  ]
}
```

### Supported Languages

Auto-discovered from `languagedata_*.xml` files in the LOC folder. Standard production set:

```
eng  fre  ger  ita  jpn  kor  pol  por-br
rus  spa-es  spa-mx  tur  zho-cn  zho-tw
```

Additional languages (`tha`, `vie`, `ind`, `msa`) are included automatically if their `languagedata_*.xml` files exist.

### Fuzzy Matching

Technology: **KR-SBERT** (Korean Sentence-BERT) + **FAISS** IndexFlatIP. Model folder: `KRTransformer/` next to the app. First load takes ~30 seconds.

| Threshold | Behavior | Use Case |
|:---------:|----------|----------|
| **0.95** | Near-exact | Only minor spelling/whitespace changes |
| **0.85** | Default | General-purpose rewording detection |
| **0.80** | Loose | Significant Korean text changes |
| **0.70** | Maximum | Broadest coverage (risk of false positives) |

Threshold range: 0.70 — 1.00 (step 0.01). Available in Strict and StrOrigin Only match types.

---

## 7. Quick Reference Card

### All Buttons

| Button | Function | Mode |
|--------|----------|------|
| **Generate** | Source folder → Excel with all languages | LOOKUP |
| **TRANSFER** | Write corrections to target XML files | TRANSFER |
| **Lookup** | Look up one StringID → all translations | LOOKUP |
| **Browse** / **Find All** | Reverse lookup: text file → find StringIDs | LOOKUP |
| **Find Missing Translations** | Compare source vs target → gap report | LOOKUP |
| **Exclude...** | Configure excluded paths for Find Missing | Config |
| **Check Korean** | Find untranslated Korean in non-KOR files | Pre-sub |
| **Check Patterns** | Validate `{code}` placeholders match source | Pre-sub |
| **Check Quality** | Wrong script + AI hallucination detection | Pre-sub |
| **Check ALL** | Run all three checks in sequence | Pre-sub |
| **Open Results Folder** | Open Presubmission Checks folder in Explorer | Utility |
| **Save Settings** | Save LOC/EXPORT path changes to settings.json | Config |
| **Clear Log** | Clear the log area | Utility |
| **Clear All** | Reset all fields and selections | Utility |

### Output Locations

| Location | Contents |
|----------|----------|
| `Output/` | LOOKUP results (Excel), Missing Translation reports, Close folders |
| `Presubmission Checks/Korean/` | Check Korean results (XML) |
| `Presubmission Checks/PatternErrors/` | Check Patterns results (XML) |
| `Presubmission Checks/QualityCheck/` | Check Quality results (Excel, two tabs) |
| `Failed Reports/YYMMDD/source_name/` | TRANSFER failure reports (XML + Excel) |

### All Status Codes

**LOOKUP statuses (Generate output):**

| Status | Meaning |
|--------|---------|
| `MATCHED` | Exactly 1 match found |
| `MULTI (N)` | N matches found (multiple StringIDs share this text) |
| `NOT FOUND` | No match in any EXPORT file |
| `NO TRANSLATION` | StringID exists but Str is empty for that language |

**TRANSFER statuses (transfer report + failure report):**

| Status | Meaning |
|--------|---------|
| `UPDATED` | Correction applied successfully |
| `UNCHANGED` | Matched but value already identical — nothing to do |
| `NOT_FOUND` | StringID does not exist in target XML |
| `STRORIGIN_MISMATCH` | StringID exists but StrOrigin text differs from expected |
| `SKIPPED_TRANSLATED` | Already translated (in "Only untranslated" scope) |
| `SKIPPED_NON_SCRIPT` | Not in Dialog/Sequencer categories (StringID-Only mode) |
| `SKIPPED_EXCLUDED` | In an excluded subfolder (NarrationDialog or user-excluded) |
| `MISSING EVENTNAME` | EventName could not be resolved to a StringID |

---

## 8. Troubleshooting

**Match type is greyed out** — Source files are missing required columns for that match type. Check column headers against the table in Section 2.1.

**TRANSFER button disabled** — Substring mode is selected. Substring is LOOKUP-only. Switch to StringID-Only, Strict, or StrOrigin Only.

**Korean corrections skipped** — Correction column still contains Korean text. TRANSFER only writes non-Korean corrections. Ensure the Correction column contains actual translations.

**0 matches found** — Checklist:
- Correct match type selected?
- Column headers match expected names? (StringID, StrOrigin, Correction)
- Source and target paths correct in settings?
- Perforce workspace synced recently?
- For Strict: has Korean source text changed since your Excel was created? Try Fuzzy precision.
- For StringID-Only: are the strings in Dialog/ or Sequencer/ categories? Non-SCRIPT strings are skipped.

**EventName not resolved** — The 3-step resolution waterfall could not find a match. Check that the EventName exists in EXPORT `.loc.xml` files. Verify the DialogVoice column if present. Alternatively, use StringID directly.

**settings.json issues** — Use double backslashes (`\\`). No trailing backslash. Must be valid JSON (check commas and brackets). Delete `settings.json` and restart to reset to F: drive defaults.

**Fuzzy matching slow** — First load of the KR-SBERT model takes ~30 seconds. Subsequent lookups are fast. Lower thresholds (0.70) search more broadly and take longer. If the `KRTransformer/` folder is missing, fuzzy options are disabled.

**Find Missing shows too many results** — Use the **Exclude...** dialog to filter out non-priority folders (e.g., System/Gimmick, System/MultiChange). Exclusions are saved to `exclude_rules.json` and remembered between sessions.

**ToSubmit checkbox** — When checked, automatically includes correction files from the `ToSubmit/` subfolder alongside your selected source folder. Useful for staging pending corrections that should be included in the current TRANSFER run.

**Pre-submission check finds nothing** — Ensure the Source path points to a folder containing `languagedata_*.xml` files (not Excel). These checks operate on XML files, not correction spreadsheets.

**Output folder is empty after Generate** — Check the log area for errors. Common causes: LOC/EXPORT paths are wrong, source folder has no recognizable files, or all input rows failed to match.

*Last updated: February 2026*
