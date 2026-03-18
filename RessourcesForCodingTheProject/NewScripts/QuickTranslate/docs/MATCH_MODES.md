# QuickTranslate — Match Modes Reference

Complete reference for all transfer match modes. Each mode defines how source corrections are matched against target XML strings.

---

## Overview

| Mode | Key | Use Case | Precision |
|------|-----|----------|-----------|
| **Strict** | StringID + StrOrigin | Default. Both must match. | Highest (but fails when StringIDs change) |
| **StringID-Only** | StringID | SCRIPT strings (Dialog/Sequencer). Tolerates text edits. | High (StringID is stable) |
| **StrOrigin Only** | StrOrigin text | Non-script strings. No StringID needed. | Medium (ambiguous for common text) |
| **StrOrigin + DescOrigin** | StrOrigin + DescOrigin | Voiced lines where DescOrigin disambiguates. | High |
| **StrOrigin + FileName** | StrOrigin + Export Filepath | StringIDs changed but Korean text identical. Filepath = security fence. | High |

All modes except StringID-Only support **Fuzzy** precision (Model2Vec + FAISS fallback on unmatched corrections).

All modes except StrOrigin Only and StringID-Only support **Non-Script Only** filtering (exclude Dialog/Sequencer).

---

## StrOrigin + FileName (2-Pass) — Build 071+

### The Problem It Solves

Game updates often change StringIDs (new build, restructured data). Translations from the old version become orphaned — `strict` mode can't match because the StringID changed, even though the Korean source text is identical.

`strorigin_only` would match by text alone, but it's dangerous: common strings like "이름" (Name) appear in 50+ files. You'd overwrite all of them with the same translation, even when they mean different things in different contexts.

**StrOrigin + FileName gives you `strorigin_only` matching power with export-filepath security.** It guarantees: "this Korean text, in this specific file" — not some random duplicate in a completely different file.

### How It Works

#### The Key Component: Export Filepath Index

The EXPORT folder (`export__/`) contains the game's string data organized by category:

```
export__/
├── Dialog/
│   └── NarrationDialog/
│       └── quest01.loc.xml          → StringIDs for quest dialog
├── UI/
│   └── characterinfo.loc.xml       → StringIDs for character UI
├── Items/
│   └── iteminfo.loc.xml            → StringIDs for item descriptions
└── Sequencer/
    └── cutscene01.loc.xml          → StringIDs for cutscenes
```

At load time, QuickTranslate scans every `*.loc.xml` in the export folder and builds an index:

```
StringID (lowercased) → Relative filepath
───────────────────────────────────────────
"str_char_old_001"    → "UI/characterinfo.loc.xml"
"str_char_new_001"    → "UI/characterinfo.loc.xml"    ← different ID, SAME file
"str_item_042"        → "Items/iteminfo.loc.xml"
"str_dialog_007"      → "Dialog/NarrationDialog/quest01.loc.xml"
```

Both source corrections and target strings resolve their filepath through this same index (by looking up their respective StringID). The export folder is the single source of truth.

#### The 2-Pass Matching

**PASS 1 (Maximum Precision):**
```
Key = (normalized_StrOrigin, export_filepath, normalized_DescOrigin)
```
All three must match. Catches exact matches where text, file, AND description align.

**PASS 2 (Relaxed — catches DescOrigin mismatches):**
```
Key = (normalized_StrOrigin, export_filepath)
```
Text + file must match. DescOrigin is ignored. Catches cases where DescOrigin changed or is empty.

PASS 2 only runs on corrections that PASS 1 didn't match.

#### Real-World Example

**Scenario:** Game update changed StringIDs. Old translations need to be transferred.

Source correction (from old version):
- StringID: `STR_CHAR_OLD_001`
- StrOrigin: `"이름"` (Korean for "Name")
- Str (translation): `"Nom"` (French)

Target string (new version):
- StringID: `STR_CHAR_NEW_001`
- StrOrigin: `"이름"`
- Str: empty (needs translation)

**Without StrOrigin + FileName:**
- `strict` mode: NO MATCH (StringIDs differ)
- `strorigin_only`: matches, but ALSO fills `"이름"` in `iteminfo.loc.xml`, `skillinfo.loc.xml`, etc.

**With StrOrigin + FileName:**

1. Export index resolves both StringIDs:
   - `str_char_old_001` → `"UI/characterinfo.loc.xml"`
   - `str_char_new_001` → `"UI/characterinfo.loc.xml"`

2. Source builds PASS2 key: `("이름", "UI/characterinfo.loc.xml")`

3. Target builds PASS2 key: `("이름", "UI/characterinfo.loc.xml")`

4. **MATCH** — same Korean text, same file origin. The `"이름"` in `iteminfo.loc.xml` resolves to a different filepath and is NOT matched.

Result: precise transfer, no false matches.

### Options Available

| Option | Values | Description |
|--------|--------|-------------|
| **Match Precision** | Exact / Fuzzy | Fuzzy uses Model2Vec + FAISS on unmatched corrections |
| **Non-Script Only** | On / Off | Filter out Dialog/Sequencer categories |
| **Transfer Scope** | All / Untranslated | Skip strings that already have translations |

### Prerequisites

- Source files must have **StrOrigin** + **Correction** columns
- **EXPORT folder** must be configured in Settings (same requirement as StringID-Only mode)

### Edge Cases

| Case | Behavior |
|------|----------|
| StringID not in export index | Filepath = "". Only matches other strings also missing from export. |
| Empty StrOrigin | Skipped (golden rule — same as all modes) |
| Empty DescOrigin on source | Not added to PASS1 dict. PASS2 catches it. |
| Empty DescOrigin on target | PASS1 skipped. PASS2 catches it. |
| Duplicate StrOrigin in different files | Correctly disambiguated — this is the whole point |

### Technical Details

- **Filepath format:** Full relative path from export root (e.g., `"UI/characterinfo.loc.xml"`, not just `"characterinfo"`)
- **Case sensitivity:** StringID lookups use `.lower()` throughout. StrOrigin/DescOrigin use `normalize_for_matching()` (lowercase + whitespace collapse).
- **Index function:** `build_stringid_to_filepath()` in `core/language_loader.py`
- **Lookup building:** `_build_correction_lookups()` in `core/xml_transfer.py` — `correction_lookup` = PASS1 dict, `correction_lookup_nospace` = PASS2 dict (repurposed)
- **Merge logic:** `_fast_folder_merge()` in `core/xml_transfer.py` — inline 2-pass with dict.get()

---

## Strict (StringID + StrOrigin)

**Key:** `(StringID.lower(), normalized_StrOrigin)`

Both StringID and StrOrigin must match. The safest default — no false positives. Has a nospace fallback (strips all whitespace from StrOrigin for whitespace-tolerant matching).

**When to use:** When StringIDs are stable between versions and you want maximum safety.

**Options:** Exact/Fuzzy precision, Non-Script Only, Transfer Scope.

---

## StringID-Only (SCRIPT)

**Key:** `StringID.lower()`

Matches by StringID alone, ignoring StrOrigin. Only processes SCRIPT categories (Dialog, Sequencer) by default — can be overridden with "All Categories" checkbox.

**When to use:** For Dialog/Sequencer strings where StrOrigin is a description (not the actual Korean text) and may change between versions.

**Options:** Transfer Scope, All Categories checkbox. No fuzzy variant.

---

## StrOrigin Only

**Key:** `normalized_StrOrigin`

Matches by Korean source text only. No StringID check. Fills ALL target strings with the same StrOrigin — dangerous for ambiguous text but useful when StringIDs are unavailable.

**When to use:** When source data has no StringIDs (e.g., plain text corrections) or when you want aggressive matching regardless of StringID.

**Options:** Exact/Fuzzy precision, Unique Only (skip duplicate StrOrigins), Transfer Scope.

**Safety:** Defaults to "Untranslated only" scope. Skips Dialog/Sequencer strings automatically (complement of StringID-Only).

---

## StrOrigin + DescOrigin

**Key:** `(normalized_StrOrigin, normalized_DescOrigin)`

Both text fields must match. More precise than StrOrigin Only — DescOrigin disambiguates voiced lines where the same StrOrigin has different voice directions.

**When to use:** For voiced content where DescOrigin provides meaningful disambiguation.

**Options:** Exact/Fuzzy precision, Non-Script Only, Transfer Scope.

---

## Fuzzy Precision (All Modes)

When "Fuzzy" precision is selected, the transfer runs in two phases:

1. **Exact phase:** Normal dict-lookup matching (the mode's standard behavior)
2. **Fuzzy phase:** Unmatched corrections are encoded with Model2Vec (256-dim) and searched against a FAISS HNSW index built from the target folder. FAISS returns the closest-matching target StringID, and a second merge pass runs in StringID-Only mode using the fuzzy match.

Fuzzy matching adds a similarity threshold (default from config) — only matches above the threshold are applied.

---

## Normalization Reference

| Function | What it does | Used by |
|----------|-------------|---------|
| `normalize_text()` | HTML unescape, strip, collapse whitespace, remove `&desc;` prefix | Strict mode |
| `normalize_for_matching()` | `normalize_text()` + `.lower()` | StrOrigin Only, StrOrigin+DescOrigin, StrOrigin+FileName |
| `normalize_nospace()` | Remove all whitespace from already-normalized string | Nospace fallback (Strict, StrOrigin Only) |
