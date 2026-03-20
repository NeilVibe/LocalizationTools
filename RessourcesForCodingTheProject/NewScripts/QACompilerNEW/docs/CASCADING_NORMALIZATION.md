# Cascading Normalization for StrOrigin Matching

## Overview

When generators look up translations from language data, the Korean source text from game data may not exactly match the `StrOrigin` in language data. A sequential cascade of normalization levels is applied until a match is found **in the correct export file**.

If no match is found at any level, the row is **skipped** (not written to the datasheet).

**Status:** Working as of 2026-03-20. Confirmed with `{StaticInfo:Status:Fishing}-힘겨루기` → `낚시-힘겨루기` matching.

## The Cascade

Each level normalizes the game data Korean text differently, then attempts a lookup in the language table filtered to the correct export filename key.

| Level | Name | What it does | Example |
|-------|------|-------------|---------|
| **0/1** | Placeholders | `normalize_placeholders()` — strip `{...#suffix}`, `<br/>`→space, collapse whitespace | `{StaticInfo:Status:Fishing}-힘겨루기` (unchanged, no match) |
| **2** | Code Resolution | Resolve `{StaticInfo:Category:StrKey}` codes → Korean via DevMemo/DevComment lookup | `낚시-힘겨루기` (match!) |

## Level 2: Code Resolution Detail

**Real example:**

Game data (`GameAdviceInfo.staticinfo.xml`):
```xml
<GameAdviceInfo Title="{StaticInfo:Status:Fishing}-힘겨루기" ...>
```

Language data (`languagedata_jpn.xml`):
```xml
<LocStr StrOrigin="낚시-힘겨루기" Str="釣り - いなす" StringId="16346883740347138453"/>
```

StaticInfo (`statusinfo.staticinfo.xml`):
```xml
<StatusInfo StrKey="Fishing" DevMemo="낚시" .../>
```

**Resolution steps:**
1. Regex isolates `{StaticInfo:Status:Fishing}`
2. Extract last segment after `:` → `Fishing`
3. StrKey lookup (lazy-built, scans entire StaticInfo folder via `parse_xml_file()`) finds `StrKey="Fishing"` → `DevMemo="낚시"`
4. Replace: `{StaticInfo:Status:Fishing}` → `낚시`
5. Result: `낚시-힘겨루기`
6. `normalize_placeholders()` applied → `낚시-힘겨루기`
7. Look up in language table → match found in correct export file

**Critical implementation detail:** StrKey lookup uses `parse_xml_file()` (not raw `ET.parse()`). StaticInfo XMLs need sanitization + virtual `<ROOT>` wrapper to parse with lxml. Using raw parsing silently fails on every file.

## StrKey Lookup

Built lazily on first encounter of a `{StaticInfo:...}` code. Scans the entire `RESOURCE_FOLDER` recursively for elements with `StrKey` attribute, maps `StrKey` → `DevMemo` or `DevComment`.

- Uses `_cfg.RESOURCE_FOLDER` (read at call time, not import time)
- Cached in `_STRKEY_LOOKUP` module-level variable
- Lookup is case-insensitive (`strkey.lower()`)

## Matching Constraint

**Every match MUST be validated against the export filename key.** A StrOrigin that exists in language data but belongs to a different export file is NOT a valid match.

## Consumer Compatibility

The `StringIdConsumer` (order-based disambiguation) always uses the level-0/1 normalized key (`normalize_placeholders(korean_text)`) regardless of which cascade level matched. This is because the ordered export index was built with `normalize_placeholders()` normalization. If the cascade matched at level 2, the consumer may return `None` — the code falls through to export-index file-set matching.

## Adding New Levels

The cascade is extensible. To add a new normalization level:

1. Write a normalization function: `def normalize_level_N(text: str) -> str`
2. Add it to the `NORMALIZATION_CASCADE` list in `generators/base.py`
3. The cascade runner applies each level sequentially and stops at first match

Future levels can be added as new patterns are discovered. Each level should be more aggressive than the previous one.

## Architecture

```
_find_candidates_cascading(korean_text, lang_table)
    for each normalization level in NORMALIZATION_CASCADE:
        normalized = level(korean_text)
        candidates = lang_table.get(normalized)
        if candidates:
            return (candidates, normalized)
    return (None, "")

resolve_translation(korean_text, lang_table, data_filename, ...)
    candidates = _find_candidates_cascading(...)
    → disambiguate via consumer / export_index
    → return (translation, stringid, str_origin)
```

## Key Files

| File | What |
|------|------|
| `generators/base.py` | `NORMALIZATION_CASCADE`, `_find_candidates_cascading`, `resolve_staticinfo_codes`, `_build_strkey_lookup`, `get_strkey_lookup` |
| `config.py` | `RESOURCE_FOLDER` path to StaticInfo XMLs |

---

*Created 2026-03-20. Confirmed working. Extensible — add new normalization levels as patterns are discovered.*
