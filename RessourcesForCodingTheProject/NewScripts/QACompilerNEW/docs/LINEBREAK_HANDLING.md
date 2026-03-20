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

## Future Consideration

The cleaner approach would be to **remove `br_to_newline()` entirely** and keep `<br/>` as-is in Excel cells. This preserves the canonical format throughout the pipeline and eliminates the need for re-conversion downstream.

Trade-off: `<br/>` won't visually wrap in Excel cells like `\n` does, but data correctness > display aesthetics.

This is a low-priority change since the QuickTranslate preprocess fix handles the mismatch.

---

*Created 2026-03-20. Documents the linebreak conversion behavior across all QACompiler generators.*
