# Linebreak Handling in QACompiler

## Current Behavior

All generators convert `<br/>` → `\n` (real newline) when writing to Excel via `br_to_newline()`.

This means Excel cells show visual line breaks (Alt+Enter style), but the canonical `<br/>` tag is lost.

### Affected Generators (ALL of them)

| Generator | File | Applies to |
|-----------|------|------------|
| base.py | `emit_rows_to_worksheet()` | SourceText + Translation |
| help.py | GameAdvice writer | Original (KR) + English + Translation |
| item.py | Item writer | kor_text + trans |
| character.py | Character writer | kor_text + trans |
| region.py | Region writer | text + trans_eng + trans_other |
| quest.py | Quest writer | orig + eng + loc |
| gimmick.py | Gimmick writer | text + trans_eng + trans_other |
| knowledge.py | Knowledge writer | text + eng_tr + other_tr |
| itemknowledgecluster.py | IKC writer | kor_text + trans |
| skill.py | Skill writer | kor_text + trans (name + desc) |

### Function

```python
# generators/base.py
_br_tag_re = re.compile(r'<br\s*/?>', flags=re.IGNORECASE)

def br_to_newline(text: str) -> str:
    return _br_tag_re.sub('\n', text)
```

## The Problem

XML language data uses `<br/>` as the canonical linebreak format. When QACompiler converts these to `\n` in Excel output, downstream consumers (QuickTranslate, ExtractAnything) must convert `\n` back to `<br/>` to match against XML targets.

### Data Flow

```
XML on disk:     &lt;br/&gt;      (escaped)
lxml in memory:  <br/>            (canonical)
QACompiler:      \n               (converted for Excel display)
QuickTranslate:  must convert \n → <br/> to match XML targets
```

### Downstream Impact

**QuickTranslate** reads QACompiler Excel output as input. When matching StrOrigin from Excel against StrOrigin in XML target files:
- Excel StrOrigin has `\n` (from `br_to_newline()`)
- XML StrOrigin has `<br/>` (canonical format)
- Without normalization, these don't match

**Fix applied in QuickTranslate** (2026-03-20): `_convert_linebreaks_for_excel()` is now called as a preprocess on StrOrigin and DescOrigin when reading from Excel, converting `\n` → `<br/>` before matching.

## StrOrigin Fix (2026-03-20)

**Problem:** SourceText (KR) column used raw game data Korean text, which can differ from language data `StrOrigin` (linebreaks, whitespace, placeholder formatting). This caused matching failures in QuickTranslate.

**Fix:** `resolve_translation()` and `get_first_translation()` now return a 3-tuple `(translation, stringid, str_origin)`. All generators use `str_origin` (from language data) for the SourceText column, falling back to game data text when no match is found.

Changed files: `base.py` (language table + resolve functions) + all 9 generator files.

## Per-Generator Raw Mode (2026-03-23)

**GameAdvice (`help.py`) now outputs raw `<br/>` format** — no `br_to_newline()` conversion.

This was done so the Excel output matches the original language data exactly, which is needed for downstream matching (QuickTranslate, testing). The `<br/>` tags appear as literal text in cells instead of visual line breaks.

### How the change was made

Removed `br_to_newline()` wrapper from all three text columns in `write_workbook()`:

```python
# BEFORE (converted):
c1 = ws.cell(row_idx, 1, br_to_newline(kor_display))  # KR
c2 = ws.cell(row_idx, 2, br_to_newline(eng_tr))        # ENG
c3 = ws.cell(row_idx, 3, br_to_newline(loc_tr))        # Translation

# AFTER (raw):
c1 = ws.cell(row_idx, 1, kor_display)                   # KR
c2 = ws.cell(row_idx, 2, eng_tr)                         # ENG
c3 = ws.cell(row_idx, 3, loc_tr)                         # Translation
```

### How to apply to other generators

Each generator has its own `write_workbook()` or equivalent writer function. To switch a generator to raw mode:

1. Find the `ws.cell()` calls that write text columns (KR, ENG, Translation)
2. Remove the `br_to_newline()` wrapper — just pass the text directly
3. The `br_to_newline` import can be kept (other code may use it) or removed if unused

| Generator | Writer function | Text cell lines to change |
|-----------|----------------|--------------------------|
| help.py (GameAdvice) | `write_workbook()` | **DONE** (2026-03-23) |
| item.py | `write_workbook()` | Find `br_to_newline(kor_text)` / `br_to_newline(trans)` |
| character.py | `write_workbook()` | Find `br_to_newline(kor_text)` / `br_to_newline(trans)` |
| region.py | `write_workbook()` | Find `br_to_newline(text)` / `br_to_newline(trans_*)` |
| quest.py | `write_workbook()` | Find `br_to_newline(orig)` / `br_to_newline(eng)` / `br_to_newline(loc)` |
| gimmick.py | `write_workbook()` | Find `br_to_newline(text)` / `br_to_newline(trans_*)` |
| knowledge.py | `write_workbook()` | Find `br_to_newline(text)` / `br_to_newline(*_tr)` |
| itemknowledgecluster.py | `write_workbook()` | Find `br_to_newline(kor_text)` / `br_to_newline(trans)` |
| skill.py | `write_workbook()` | Find `br_to_newline(kor_text)` / `br_to_newline(trans)` |
| script.py | `write_workbook()` | Find `br_to_newline()` calls on text columns |

### Trade-off

`<br/>` won't visually wrap in Excel cells like `\n` does, but data correctness > display aesthetics. Raw format means Excel output matches XML source exactly, eliminating re-conversion in downstream tools.

---

*Created 2026-03-20. Updated 2026-03-23 (GameAdvice raw mode).*
