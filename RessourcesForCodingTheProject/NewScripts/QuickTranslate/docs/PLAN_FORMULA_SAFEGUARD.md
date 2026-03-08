# Formula Safeguard Plan — QuickTranslate (v3 — post-PRXR double review)

## Problem

Excel formulas can end up in the Correction/Desc columns due to human error (e.g.,
VLOOKUP pasted as formulas instead of values). These get transferred into XML as
literal text like `=VLOOKUP(A2,Sheet2!A:B,2,FALSE)`, error values like `#N/A`, or
openpyxl object repr strings like `openpyxl.worksheet.formula.ArrayFormula...`.

**Current state:** Zero protection. Formulas pass through the entire pipeline unchecked.

## Design Principles (from PRXR double review)

1. **Don't break callers** — `read_corrections_from_excel` keeps its `List[Dict]` return type
2. **Guard only write-to-XML columns** — Correction and Desc. StringID/StrOrigin with formulas produce garbage strings that fail to match (harmless NOT_FOUND); they inflate correction count slightly but cause no data corruption
3. **No new modules** — private helpers in `excel_io.py`, not a new `input_validation.py`
4. **No new failure reason** — formula skips are input validation errors, not merge failures. Use `self._log(..., 'error')` in GUI, `log_callback(msg, 'error')` in xml_transfer
5. **No double-read** — piggyback formula detection on existing validation pass
6. **Whitelist types, don't blacklist** — `isinstance(value, str)` is the primary check
7. **Match existing variable names** — use `corrected` / `d_val` as in current code, not renamed vars

## Detection Patterns

### Layer 1: Type Check (BEFORE str coercion)

Only `str` values are valid translations. Everything else is suspicious:

| `cell.value` type | Action | Why |
|-------------------|--------|-----|
| `str` | PASS — proceed to Layer 2 | Expected type |
| `ArrayFormula` | SKIP + report | openpyxl formula object |
| `DataTableFormula` | SKIP + report | openpyxl formula object |
| `None` | Already handled by existing `if not corrected` guard | |
| `int` / `float` | SKIP + report | Likely cached formula result, not text |
| `bool` | SKIP + report | Excel checkbox, not translation text |
| `datetime` | SKIP + report | Likely `=TODAY()` result, not text |
| Any other non-str | SKIP + report | Unknown object type |

**Implementation:** `isinstance(value, str)` whitelist. If False, skip.

```python
import re

try:
    from openpyxl.worksheet.formula import ArrayFormula, DataTableFormula
    _FORMULA_TYPES = (ArrayFormula, DataTableFormula)
except ImportError:
    _FORMULA_TYPES = ()

def _is_bad_cell_type(value) -> Optional[str]:
    """Check raw cell.value type. Returns reason string if bad, None if OK."""
    if value is None:
        return None  # Already handled by existing None guards
    if isinstance(value, str):
        return None  # Expected type — pass to string check
    if _FORMULA_TYPES and isinstance(value, _FORMULA_TYPES):
        return f'Excel formula object ({type(value).__name__})'
    if isinstance(value, bool):
        return f'Boolean value ({value})'
    if isinstance(value, (int, float)):
        return f'Numeric value ({value})'
    # Catch-all: datetime, openpyxl objects, anything unexpected
    return f'Unexpected type ({type(value).__name__}: {str(value)[:50]})'
```

### Layer 2: String Check (AFTER str coercion)

For values that are already strings, catch formula text and error values:

```python
_FORMULA_RE = re.compile(r'^[=+\-][A-Za-z]')

_EXCEL_ERRORS = frozenset({
    '#N/A', '#REF!', '#VALUE!', '#NAME?', '#NULL!',
    '#DIV/0!', '#NUM!', '#GETTING_DATA',
})

def _is_bad_cell_text(text: str) -> Optional[str]:
    """Check string cell value. Returns reason string if bad, None if OK."""
    if not text:
        return None
    stripped = text.strip()
    if _FORMULA_RE.match(stripped):
        return f'Excel formula ({stripped[:40]})'
    if stripped.upper() in _EXCEL_ERRORS:
        return f'Excel error value ({stripped})'
    # Safety net: catch openpyxl repr strings that somehow got str()-coerced
    if 'openpyxl.' in stripped:
        return f'openpyxl object repr ({stripped[:40]})'
    return None
```

### Formula Regex Decision

`^[=+\-][A-Za-z]` catches `=VLOOKUP(...)`, `=IF(...)`, `+SUM(...)`, `-IF(...)`.

**Will NOT false-positive on:**
- `==` (comparison operator) — second char is `=`, not a letter
- `=` alone — no letter after
- `= ` (equals space) — no letter immediately after `=`
- `+5` or `-3` (signed numbers) — digit, not letter
- `-` alone, `+` alone — no letter after

**Edge case `={code}`:** This IS caught by the regex. Game data uses `{code}` patterns
(e.g., `{ItemName}`) but always WITHOUT a leading `=`. If a false positive is ever
reported, add a whitelist check: `if stripped.startswith('={') and '}' in stripped: return None`.
Not adding it now — no evidence this pattern exists in Correction columns.

**Edge case `+Letter`/`-Letter`:** Strings like `+Bonus damage` or `-Archer penalty` would
be caught. These are plausible game modifier text but very unlikely as standalone Correction
values (corrections are typically full translated sentences). Same mitigation as `={code}`:
add a whitelist or narrow regex to `^=[A-Za-z]` only if false positives are reported.

**Non-Latin formula names** (e.g., Russian `=СУММ(...)`): NOT caught by `[A-Za-z]`.
Acceptable trade-off — this project handles EN/KR/ZH/JP, not Russian Excel. If needed
later, broaden to `^[=+\-]\w` (catches Unicode word characters). Not adding now to
avoid false positives on game text starting with `=K` or similar.

## Files to Modify

### 1. `core/excel_io.py` — Main implementation

**A. Add imports** (top of file, after existing imports):
```python
import re
```
Also add `from typing import Optional` if not already imported.

**B. Add detection functions** (private, after imports):
- `_is_bad_cell_type(value) -> Optional[str]`
- `_is_bad_cell_text(text) -> Optional[str]`

Return `None` for OK, reason string for bad (standard Python `Optional[str]` pattern).

**C. Add `formula_report` parameter** to `read_corrections_from_excel`:
```python
def read_corrections_from_excel(
    excel_path: Path,
    has_header: bool = True,
    formula_report: Optional[list] = None,  # NEW — caller passes [] to collect skips
) -> List[Dict]:  # Return type UNCHANGED
```

**D. Guard Correction column** — add after line 210:

Current code (line 210):
```python
corrected = row[correction_col - 1].value if correction_col is not None and correction_col <= len(row) else None
```

New code:
```python
corrected = row[correction_col - 1].value if correction_col is not None and correction_col <= len(row) else None

# Formula safeguard Layer 1: type check BEFORE str coercion
bad_type = _is_bad_cell_type(corrected)
if bad_type:
    if formula_report is not None:
        formula_report.append({
            'row': row[0].row, 'column': 'Correction',
            'string_id': str(string_id or ''), 'reason': bad_type,
        })
    continue

# ... existing has_id / has_eventname / not corrected guard at line 223 ...

corrected_str = str(corrected).strip()

# Formula safeguard Layer 2: string check AFTER str coercion
bad_text = _is_bad_cell_text(corrected_str)
if bad_text:
    if formula_report is not None:
        formula_report.append({
            'row': row[0].row, 'column': 'Correction',
            'string_id': str(string_id or ''), 'reason': bad_text,
        })
    continue
```

**Key details:**
- Uses `row[0].row` for the actual Excel row number (openpyxl cell attribute), NOT a manual counter
- Uses existing variable name `corrected` (not renamed to `raw_corrected`)
- Layer 1 goes right after the value read (line 210), BEFORE the existing `has_id` / `not corrected` guard (line 223)
- Layer 2 goes right after `corrected_str = str(corrected).strip()` (line 226), BEFORE the Korean check (line 228)
- Both layers use `continue` to skip the entire row (formula in Correction = entire row is bad)

**E. Guard Desc column** — wrap existing desc code (lines 242-247):

Current code:
```python
if desc_col is not None:
    d_val = row[desc_col - 1].value if desc_col <= len(row) else None
    if d_val is not None and str(d_val).strip():
        desc_str = str(d_val).strip()
        if not is_korean_text(desc_str):
            entry["desc_corrected"] = desc_str
```

New code:
```python
if desc_col is not None:
    d_val = row[desc_col - 1].value if desc_col <= len(row) else None
    # Formula safeguard: neutralize bad Desc values (don't skip row)
    bad = _is_bad_cell_type(d_val) or (isinstance(d_val, str) and _is_bad_cell_text(str(d_val).strip()))
    if bad:
        if formula_report is not None:
            formula_report.append({
                'row': row[0].row, 'column': 'Desc',
                'string_id': str(string_id or ''), 'reason': bad,
            })
        d_val = None  # Neutralize — prevents downstream str(d_val) processing
    if d_val is not None and str(d_val).strip():
        desc_str = str(d_val).strip()
        if not is_korean_text(desc_str):
            entry["desc_corrected"] = desc_str
```

**Key details:**
- Sets `d_val = None` to neutralize the formula value — existing `if d_val is not None` guard below naturally skips it
- Does NOT use `pass` (which is a no-op) or `continue` (which would skip valid Correction)
- Row keeps its valid Correction; only Desc is dropped

**F. `read_korean_input` — SKIP (dead code)**

`read_korean_input` (line 99) has **zero callers** anywhere in the codebase. No guard needed.
If it's ever called in the future, add `isinstance(cell_value, str)` check then.

### 2. `gui/app.py` — RED warning display

**In `_validate_source_files_async`** (line 1101):

```python
formula_report = []
entries = read_corrections_from_excel(filepath, formula_report=formula_report)
count = len(entries) if entries else 0

if formula_report:
    formula_count = len(formula_report)
    # Show first 3 for quick diagnosis
    samples = '; '.join(
        f"row {r['row']} {r['column']}: {r['reason']}"
        for r in formula_report[:3]
    )
    self._log(
        f"WARNING: {formula_count} cell(s) skipped in {filepath.name} "
        f"(Excel formulas/errors detected). "
        f"Examples: {samples}. "
        f"Fix: re-save Excel with Paste Values (Ctrl+Shift+V).",
        'error'
    )
    # Distinguish "empty because formulas" from "genuinely empty"
    if count == 0:
        results.append((filepath.name, file_type, lang, 0, "FORMULA",
                         f"All {formula_count} rows contained formulas"))
        continue
```

**Key details:**
- Uses `self._log(..., 'error')` — matches existing GUI logging pattern (lines 1097-1099 in app.py)
- NOT `logger.error()` — that goes to terminal only; `self._log` goes to the GUI log widget (thread-safe)
- When ALL rows are formulas, status is `"FORMULA"` (not misleading `"EMPTY"` / `"No entries parsed"`)

### 3. `core/xml_transfer.py` — Transfer-time reporting

**At line 1773** (main transfer parse):

```python
formula_report = []
corrections = read_corrections_from_excel(source_file, formula_report=formula_report)
if formula_report:
    formula_count = len(formula_report)
    samples = '; '.join(
        f"row {r['row']} {r['column']}: {r['reason']}"
        for r in formula_report[:3]
    )
    msg = (
        f"WARNING: {formula_count} cell(s) skipped in {source_file.name} "
        f"(Excel formulas/errors). Examples: {samples}"
    )
    if log_callback:
        log_callback(msg, 'warning')  # xml_transfer uses 'warning' for skip notifications
    logger.warning(msg)
```

**Key details:**
- Uses `log_callback(msg, 'error')` — xml_transfer.py uses callback pattern, not `self._log`
- Also logs to `logger.warning` for terminal output
- Line 1705 (StringID extraction for FAISS) passes NO `formula_report` — formula rows silently skipped there, which is acceptable because the validation at line 1101 already warned the user

### 4. Other call sites — no changes needed

| Call site | Location | Action |
|-----------|----------|--------|
| `gui/app.py:1101` | Validation | **Modified** — passes `formula_report=[]` |
| `gui/app.py:~1704` | StringID extraction | **No change** — `formula_report` defaults to `None`, formula rows silently skipped (harmless: just missing from FAISS filter set) |
| `xml_transfer.py:1705` | StringID extraction | **No change** — same as above |
| `xml_transfer.py:1773` | Main transfer | **Modified** — passes `formula_report=[]` |

### 5. No changes to `failure_report.py`, `source_scanner.py`, `core/__init__.py`

- `failure_report.py`: Formula skips are input validation, not merge failures
- `source_scanner.py`: Path/language detection, unrelated
- `core/__init__.py`: Re-exports `read_corrections_from_excel` — additive optional param is transparent

## Behavior Summary

```
USER LOADS EXCEL (validation)
  → _validate_source_files_async calls read_corrections_from_excel(formula_report=[])
  → Formula rows detected → RED warning in GUI log via self._log(..., 'error')
  → User sees: "WARNING: 5 cell(s) skipped (Excel formulas/errors detected)..."
  → If ALL rows formula → status shows "FORMULA" not misleading "EMPTY"
  → User can fix Excel (Ctrl+Shift+V paste values) or proceed

USER HITS TRANSFER
  → xml_transfer.py calls read_corrections_from_excel(formula_report=[])
  → Formula rows SKIPPED — never enter correction lookup dict
  → Valid rows transfer normally
  → RED warning via log_callback if any formulas were skipped
  → Transfer completes with valid corrections only
```

## Edge Cases

- `==` in game text → NOT caught (regex requires letter after `=`)
- `=` alone → NOT caught
- `+5`, `-3` → NOT caught (digit after `+`/`-`, not letter)
- `={code}` patterns → caught by regex. Add whitelist if false positive reported
- `+VLOOKUP(...)`, `-SUM(...)` → CAUGHT (Excel alternative formula prefixes)
- ALL rows are formulas → corrections list empty, status "FORMULA" in validation, pipeline handles empty list gracefully
- Mixed rows (some formula, some valid) → valid ones transfer, formula ones skipped
- Formula in Correction + valid Desc → entire row skipped (Correction is primary — bad Correction invalidates the row)
- Formula in Desc + valid Correction → row transfers with Correction; Desc silently dropped
- `None` correction values → already handled by existing `if not corrected` guard
- Duplicate StringID: formulas filtered BEFORE duplicate detection
- Formula in StringID/StrOrigin → passes through as garbage string, fails to match (NOT_FOUND). Not guarded — design principle #2
- `formula_report` list is ephemeral — created locally, logged, then discarded. No persistence in v1

## Testing

1. Excel with `=VLOOKUP(...)` in Correction → row skipped, RED warning
2. Excel with `+SUM(...)` in Correction → row skipped (alt prefix)
3. Excel with `#N/A`, `#REF!`, `#n/a` (case insensitive) in Correction → row skipped
4. Excel with ArrayFormula objects (CSE `{=...}`) → row skipped, RED warning
5. Excel with `int`/`float`/`bool`/`datetime` in Correction → row skipped
6. Excel with `==` in Correction text → NOT skipped (legitimate game text)
7. Excel with `=` alone or `+5` → NOT skipped
8. Mixed rows: formula + valid → valid ones transfer correctly, formulas skipped
9. ALL rows formula → empty corrections, status "FORMULA", clear log message
10. Formula in Desc only → row transfers with Correction, Desc silently dropped
11. Formula in Desc + formula in Correction → row skipped entirely
12. Large Excel (5000+ rows) → negligible performance impact from type/string checks
13. Row numbers in report match actual Excel row numbers (via `row[0].row`)
