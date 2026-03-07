# QuickTranslate User Guide

**Version 5.0** | March 2026

---

## What Does QuickTranslate Do?

Writes translated corrections from Excel/XML into `languagedata_*.xml` files. One tool, two tabs:

| Tab | What's There |
|-----|-------------|
| **Transfer** | Match type, source/target paths, TRANSFER button, pre-submission checks, settings |
| **Other Tools** | Find Missing Translations, exclude rules |

---

## 1. Setting Up Your Excel File

### The Basics

Row 1 = headers (case-insensitive, any order). Data starts Row 2.

**Standard corrections (most common):**

```
┌──────────────┬───────────────────────┬───────────────────────┐
│  StringID    │  StrOrigin            │  Correction           │
├──────────────┼───────────────────────┼───────────────────────┤
│  quest_001   │  퀘스트를 완료하세요   │  Complete the quest   │
│  quest_002   │  아이템을 획득하세요   │  Obtain the item      │
│  npc_greet   │  안녕하세요, 모험가!   │  Hello, adventurer!   │
└──────────────┴───────────────────────┴───────────────────────┘
```

**Voice dubbing teams (EventName instead of StringID):**

```
┌────────────────────────────┬──────────────┬───────────────────┐
│  EventName                 │  DialogVoice │  Correction       │
├────────────────────────────┼──────────────┼───────────────────┤
│  Play_AIDialog_npc01_      │  npc01       │  I have a task.   │
│   quest_greeting           │              │                   │
│  Play_QuestDialog_         │  player      │  What do you need?│
│   player_response_01       │              │                   │
└────────────────────────────┴──────────────┴───────────────────┘
```

EventName → StringID conversion is automatic (3-step waterfall: DialogVoice prefix → keyword extraction → export folder lookup).

**Standard corrections with voice direction descriptions:**

```
┌──────────┬──────────────┬──────────────┬──────────────┬──────────┐
│ StringID │ StrOrigin    │ Correction   │ DescOrigin   │ Desc     │
├──────────┼──────────────┼──────────────┼──────────────┼──────────┤
│ npc_001  │ 안녕하세요   │ Hello there  │ 밝은 톤으로  │ Bright   │
│          │              │              │              │ tone     │
│ npc_002  │ 감사합니다   │ Thank you    │              │          │
└──────────┴──────────────┴──────────────┴──────────────┴──────────┘
```

DescOrigin/Desc are optional. Rows without Desc are processed normally — only the main Correction is transferred.

### Accepted Header Names

Header names are **case-insensitive** and accept these variants:

| Column | Accepted Names |
|--------|----------------|
| StringID | `StringID`, `string_id` |
| StrOrigin | `StrOrigin`, `str_origin` |
| Correction | `Correction`, `Corrected` |
| EventName | `EventName`, `event_name`, `SoundEventName` |
| DialogVoice | `DialogVoice`, `dialog_voice` |
| DescOrigin | `DescOrigin`, `desc_origin` |
| Desc | `Desc`, `DescText`, `desc_text`, `DescCorrection` |

### Column Reference

| Column | What | Required? |
|--------|------|-----------|
| **StringID** | Unique ID from XML | Strict / StringID-Only |
| **StrOrigin** | Original Korean text from XML (copy exactly, including `<br/>`) | Strict / StrOrigin Only |
| **Correction** | Your translation — this gets written to XML | Always |
| **EventName** | Sound event name (alternative to StringID) | Optional |
| **DialogVoice** | Voice actor prefix (helps resolve EventName) | Optional |
| **DescOrigin** | Original Korean voice direction description | Optional |
| **Desc** | Translated voice direction description — written to XML | Optional |

### What Gets Skipped

- **No Correction** → file skipped entirely
- **Korean in Correction** → row silently skipped (not translated yet)
- **Empty Correction** → row silently skipped

### Organize by Language

Put files in language-named folders. QuickTranslate auto-detects.

```
MyCorrections/              ← set as Source
├── ENG/
│   └── corrections.xlsx
├── FRE/
│   └── corrections.xlsx
└── ZHO_CN/
    └── corrections.xlsx
```

No language detected = file skipped. Use `ENG/`, `FRE/`, etc. or add suffix: `corrections_eng.xlsx`.

---

## 2. Match Types

### Strict (Default — Safest)

Requires **StringID + StrOrigin + Correction**. Both ID and Korean text must match.

Uses a 2-step cascade before declaring failure:
1. **Normalized match** — case-insensitive StringID, normalized StrOrigin (HTML unescape, whitespace collapse)
2. **No-space fallback** — removes ALL whitespace from both sides and compares

**Fuzzy option:** After cascade fails, Model2Vec semantic similarity finds closest match.

| Threshold | Use |
|:---------:|-----|
| 0.95 | Minor spelling/space changes |
| **0.85** | Default — general rewording |
| 0.80 | Significant text changes |
| 0.70 | Maximum coverage (more false positives) |

**Best for:** Non-SCRIPT categories (System/, World/, Platform/). When precision matters.

### StringID-Only (SCRIPT Categories)

Requires **StringID + Correction**. Ignores StrOrigin. Only processes Dialog/ and Sequencer/ folders.

Non-SCRIPT strings get `SKIPPED_NON_SCRIPT`.

**Best for:** Voice dubbing corrections. StrOrigin is often too long or changed since extraction.

### StrOrigin Only (Fan-Out)

Requires **StrOrigin + Correction**. One correction fills **ALL** entries sharing the same Korean text.

```
1 Excel row with StrOrigin="확인" → 47 XML entries updated
```

Defaults to "Only untranslated" for safety. "Transfer ALL" triggers a warning dialog.

**Best for:** Bulk-filling untranslated UI labels, buttons, status messages.

### Comparison

| | Strict | StringID-Only | StrOrigin Only |
|---|:-:|:-:|:-:|
| **Precision** | Highest | Medium | Medium |
| **Fan-out** | No | No | Yes |
| **Fuzzy** | Yes | No | Yes |
| **Desc Transfer** | Yes | Yes | No |
| **Default scope** | Transfer ALL | Transfer ALL | Only untranslated |
| **Risk** | Lowest | Low | Medium |

---

## 3. Running TRANSFER

1. Set **Source** → your corrections folder
2. Set **Target** → LOC folder with `languagedata_*.xml` files
3. Pick match type
4. Click **TRANSFER** → review plan → confirm

### Status Codes

| Status | Meaning |
|--------|---------|
| `UPDATED` | Applied successfully |
| `UNCHANGED` | Already identical |
| `NOT_FOUND` | StringID doesn't exist |
| `STRORIGIN_MISMATCH` | StringID exists, Korean text differs |
| `SKIPPED_TRANSLATED` | Already translated (untranslated-only mode) |
| `SKIPPED_NON_SCRIPT` | Not in Dialog/Sequencer (StringID-Only) |
| `MISSING EVENTNAME` | EventName couldn't resolve to StringID |
| `RECOVERED_UPDATED` | Recovery pass resolved a failed entry |

### Post-Processing (Automatic)

After every TRANSFER:
1. Normalizes all newlines to `<br/>`
2. Clears `Str` where `StrOrigin` is empty (Golden Rule)
3. Replaces "no translation" with `StrOrigin` value

### Desc Transfer (Voice Direction Descriptions)

Some XML entries have a `DescOrigin` attribute — the original Korean voice direction description (e.g. "밝은 톤으로", "슬픈 목소리"). When you translate dialogue, you can also translate these descriptions so voice actors know the intended tone.

**How to build an Excel with Desc columns:**

1. **Get DescOrigin** — When you extract strings (via ExtractAnything or copy from XML), the DescOrigin value comes from the `DescOrigin` attribute on `<LocStr>` elements. Put it in a column named `DescOrigin`.
2. **Add your translation** — Create a `Desc` column next to it. Write your translated description there (e.g. "Bright tone", "Sad voice").
3. **Leave blank when not needed** — Not every row needs Desc. Rows without Desc are transferred normally (only Correction → Str).

```
┌──────────┬──────────────┬──────────────┬──────────────┬──────────┐
│ StringID │ StrOrigin    │ Correction   │ DescOrigin   │ Desc     │
├──────────┼──────────────┼──────────────┼──────────────┼──────────┤
│ npc_001  │ 안녕하세요   │ Hello there  │ 밝은 톤으로  │ Bright   │
│          │              │              │              │ tone     │
│ npc_002  │ 감사합니다   │ Thank you    │              │          │
└──────────┴──────────────┴──────────────┴──────────────┴──────────┘
```

**Shortcut:** If your Excel has DescOrigin but no Desc column yet, QuickTranslate auto-creates the Desc column during Excel merge — you can fill it in later.

**Transfer rules:**

- **Strict and StringID-Only only** — StrOrigin Only mode does not transfer Desc
- **Both sides required:** your Excel row needs a non-empty Desc AND the target XML `<LocStr>` must have a non-empty `DescOrigin`
- **Post-processing:** Same cleanup applies to Desc (newline normalization, empty DescOrigin clearing, "no translation" replacement)
- **Validation warning:** If no Desc/DescOrigin is found in source files, the log shows a warning and Desc transfer is skipped

### Failure Reports

`Failed Reports/YYMMDD/source_name/` — contains reusable XML files and a 3-sheet Excel report (Summary, Breakdown, Details).

---

## 4. Pre-Submission Checks

Read-only scans on `languagedata_*.xml` files. Nothing modified.

### Check Korean

Finds non-KOR entries where `Str` still contains Korean. Scans everything, no exceptions.

### Check Patterns (5 sub-checks)

| Check | What |
|-------|------|
| **Pattern codes** | `{code}` placeholders in Str must match StrOrigin |
| **Newlines** | Only `<br/>` allowed — flags `\n`, `&#10;`, `<BR/>`, etc. |
| **Brackets** | `()`, `[]`, `{}` counts must match between StrOrigin and Str |
| **Broken XML** | Malformed `<LocStr>` elements (split attributes, corrupted tags) |
| **Empty Str** | `Str` is empty but `StrOrigin` has text — missed translation |

### Check Quality (2 parts)

- **Wrong Script** — Cyrillic in French file, CJK in English file, etc.
- **AI Hallucination** — AI self-reference phrases, absurd length ratios, spurious `/` characters

### Check ALL

Runs all three checks sequentially. **Use before every Perforce submit.**

---

## 5. Find Missing Translations (Other Tools Tab)

Compares Source vs Target to find untranslated strings. Uses Source/Target paths from the Transfer tab.

4 match modes: StringID+KR Strict (fastest), StringID+KR Fuzzy, KR-only Strict, KR-only Fuzzy.

Output: Excel report + Close folder (reusable as TRANSFER source).

**Exclude...** button configures folders to skip (saved to `exclude_rules.json`).

---

## 6. Installation & Settings

### Install

- **Setup:** `QuickTranslate_vX.X.X_Setup.exe` — run and go
- **Portable:** Extract zip, run `QuickTranslate.exe`

### First Run

Configure in Settings section or edit `settings.json`:

```json
{
  "loc_folder": "F:\\perforce\\...\\stringtable\\loc",
  "export_folder": "F:\\perforce\\...\\stringtable\\export__"
}
```

### Files Created

| File | Purpose |
|------|---------|
| `settings.json` | LOC + EXPORT paths |
| `exclude_rules.json` | Find Missing exclusions |
| `presubmission_settings.json` | Check settings |
| `Model2Vec/` | Model2Vec model (fuzzy matching) |

---

## 7. Quick Reference

### Buttons

**Transfer tab:** TRANSFER, Check Korean, Check Patterns, Check Quality, Check ALL, Open Results, Save Settings, Clear Log, Clear All

**Other Tools tab:** Find Missing Translations, Exclude...

### Output Folders

| Folder | Contents |
|--------|----------|
| `Output/` | Missing Translation reports |
| `Presubmission Checks/` | Korean, PatternErrors, BracketErrors, BrokenXML, EmptyStr, QualityReport |
| `Failed Reports/` | TRANSFER failure reports |

---

## 8. Troubleshooting

| Problem | Fix |
|---------|-----|
| Match type greyed out | Source files missing required columns |
| 0 matches | Wrong match type, wrong paths, P4 out of sync, or enable Fuzzy |
| STRORIGIN_MISMATCH everywhere | Korean source updated since extraction — sync P4, try Fuzzy |
| Permission denied | P4 checkout needed on target XML |
| Excel not read | Close Excel first (it locks files) |
| Fuzzy greyed out | `Model2Vec/` folder missing |

---

## 9. Glossary

| Term | Meaning |
|------|---------|
| **StringID** | Unique text entry identifier in XML |
| **StrOrigin** | Original Korean source text in XML |
| **Str** | Translated text attribute in XML |
| **Correction** | Your translation in Excel — written to Str |
| **DescOrigin** | Original Korean voice direction description in XML |
| **Desc** | Translated voice direction description — written to XML |
| **LOC folder** | Contains `languagedata_*.xml` (one per language) |
| **EXPORT folder** | Contains categorized `.loc.xml` files (Dialog/, System/, etc.) |
| **SCRIPT** | Dialog/ and Sequencer/ categories |
| **Fan-out** | One correction fills ALL entries sharing the same StrOrigin |
| **`<br/>`** | Only correct newline format in XML |
| **Model2Vec** | Static embedding model for fuzzy matching (256-dim, no torch needed) |

*Last updated: March 2026*
