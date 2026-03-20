# Cascading Normalization for StrOrigin Matching

## Overview

When generators look up translations from language data, the Korean source text from game data may not exactly match the `StrOrigin` in language data. A sequential cascade of normalization levels is applied until a match is found **in the correct export file**.

If no match is found at any level, the row is **skipped** (not written to the datasheet).

## The Cascade

Each level normalizes the game data Korean text differently, then attempts a lookup in the language table filtered to the correct export filename key.

| Level | Name | What it does | Example |
|-------|------|-------------|---------|
| **0** | Raw | No normalization — exact text match | `{StaticInfo:Status:Fishing}-힘겨루기` |
| **1** | Placeholders | Current `normalize_placeholders()` — strip `{...#suffix}`, `<br/>`→space, collapse whitespace | `{StaticInfo:Status:Fishing}-힘겨루기` |
| **2** | Code Resolution | Resolve `{StaticInfo:Category:StrKey}` codes → Korean via DevMemo/DevComment lookup | `낚시-힘겨루기` |

### Level 2: Code Resolution Detail

Pattern: `{StaticInfo:Category:StrKey}` where:
- `Category` = XML element type (e.g., `Status`, `MiniGame`)
- `StrKey` = the key attribute value (e.g., `Fishing`)

Resolution:
1. Extract the last segment after `:` → `Fishing`
2. Scan StaticInfo XMLs for elements with `StrKey="Fishing"`
3. Read `DevMemo` or `DevComment` attribute → `낚시`
4. Replace the full `{StaticInfo:Status:Fishing}` with `낚시`
5. Apply Level 1 normalization on the result
6. Look up in language table, filtered to correct export file

## Matching Constraint

**Every match MUST be validated against the export filename key.** A StrOrigin that exists in language data but belongs to a different export file is NOT a valid match.

## Adding New Levels

The cascade is designed to be extensible. To add a new normalization level:

1. Write a normalization function: `def normalize_level_N(text: str, context: dict) -> str`
2. Add it to the `NORMALIZATION_CASCADE` list in order
3. The cascade runner applies each level sequentially and stops at first match

Future levels can be added as new patterns are discovered. Each level should be more aggressive than the previous one.

## Architecture

```
cascading_resolve(korean_text, lang_table, export_key, export_index, consumer)
    for each normalization level:
        normalized = level.normalize(korean_text)
        candidates = lang_table.get(normalized)
        if candidates:
            filtered = [c for c in candidates if c.stringid in export_file_sids]
            if filtered:
                return (translation, stringid, str_origin)
    return None  # skip this row
```

---

*Created 2026-03-20. Extensible — add new normalization levels as patterns are discovered.*
