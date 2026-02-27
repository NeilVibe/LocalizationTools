# Linebreak Safeguards — The Complete Pipeline

> **Golden Rules, automatic transformations, and the three-layer defense.**

---

## Golden Rules

| Context | Correct Format | Wrong Formats |
|---------|----------------|---------------|
| **XML on disk** (inside attributes) | `&lt;br/&gt;` | `&#10;`, `\n`, `<br>`, `&lt;BR/&gt;` |
| **XML in memory** (after lxml parse) | `<br/>` | `\n`, `<br>`, `<BR/>`, `&lt;br/&gt;` |
| **Excel cells** | `\n` (Alt+Enter) | `<br/>`, `&lt;br/&gt;` |

**Why two XML formats?** That's just how XML works. `<` is illegal inside attribute values, so on disk it MUST be `&lt;br/&gt;`. When lxml reads it, it automatically unescapes to `<br/>` in memory. When lxml writes it back, it automatically re-escapes to `&lt;br/&gt;`. This is invisible — you work with `<br/>` in code, lxml handles the rest.

---

## Boundary Crossings (Automatic Transformations)

Every time data crosses a format boundary, conversion is automatic:

```
 XML FILE ──read──> MEMORY ──write──> XML FILE
 &lt;br/&gt;         <br/>              &lt;br/&gt;
     lxml auto-unescapes      lxml auto-escapes
     (invisible, free)        (invisible, free)


 EXCEL ──read──> MEMORY ──write──> XML FILE
   \n             <br/>              &lt;br/&gt;
     _convert_linebreaks       lxml auto-escapes
     _for_xml() in transfer


 XML FILE ──read──> MEMORY ──write──> EXCEL
 &lt;br/&gt;         <br/>               \n
     lxml auto-unescapes      _convert_linebreaks
                              _for_excel() in excel_io


 EXCEL ──read──> MEMORY ──write──> EXCEL
   \n             <br/>               \n
     _convert_linebreaks       _convert_linebreaks
     _for_xml() normalizes     _for_excel() converts back
```

**Every path produces the correct format. No manual intervention needed.**

---

## The Three-Layer Defense

### Layer 1: Conversion Functions (boundary crossing)

Called every time data moves between formats.

**`_convert_linebreaks_for_xml()`** — `xml_transfer.py:37`
```
&lt;br/&gt;  →  <br/>     (prevents double-escaping by lxml)
\n           →  <br/>     (Excel Alt+Enter → XML)
\\n          →  <br/>     (literal backslash-n text → XML)
```

Called at 4 merge sites: strict, strorigin-only, stringid-only, fuzzy.

**`_convert_linebreaks_for_excel()`** — `excel_io.py:638`
```
<br/>        →  \n        (XML memory → Excel newline)
&lt;br/&gt;  →  \n        (escaped XML → Excel newline)
<br />       →  \n        (space variant → Excel newline)
\\n          →  \n        (literal text → Excel newline)
```

Called at 3 Excel merge sites: strict, strorigin-only, stringid-only.

### Layer 2: Postprocess Safety Net (runs after EVERY transfer)

Catches anything that slipped through Layer 1.

**`_normalize_newlines()`** — `postprocess.py:51` (7-step pipeline)

| Step | Catches | Converts to |
|------|---------|-------------|
| 1 | `&lt;br/&gt;`, `&lt;br&gt;`, `&lt;BR/&gt;` (HTML-escaped in memory) | `<br/>` |
| 2 | `<br>`, `<BR/>`, `<br />`, `<Br>` (wrong tag variants) | `<br/>` |
| 3 | `&#13;&#10;`, `&#xD;&#xA;` (CRLF entity combos) | `<br/>` |
| 4 | `&#10;`, `&#13;`, `&#xA;`, `&#xD;` (individual entities) | `<br/>` |
| 5 | `\r\n`, `\r`, `\n` (actual control characters) | `<br/>` |
| 6 | `\\r\\n`, `\\n`, `\\r` (literal escape text) | `<br/>` |
| 7 | NEL `\u0085`, Line Sep `\u2028`, Para Sep `\u2029`, VTab, FF | `<br/>` |

Applied via `cleanup_wrong_newlines_on_tree()` → iterates ALL LocStr in the file, normalizes both `Str` and `StrOrigin`.

Called by `run_all_postprocess()` which runs after **every** transfer operation:
- `transfer_folder_to_folder` (line 1908)
- `transfer_file_to_file` (line 2339)

### Layer 3: Detection (pre-submission checker)

User-facing check that flags wrong formats BEFORE submission.

**`_has_wrong_newlines()`** — `checker.py:76`
```python
# Detects (returns True if wrong):
'\n', '\r'           # Actual newlines
'\\n', '\\r'         # Literal escape text
'\u2028', '\u2029'   # Unicode line separators
<br>, <BR/>, etc.    # Any variant that isn't exactly <br/>
```

Runs on both `Str` and `StrOrigin` during Check Patterns. Does NOT fix — just reports.

---

## Double-Escaping Prevention

The trickiest edge case: user copy-pastes `&lt;br/&gt;` from an XML file into Excel.

```
Excel cell contains literal text: &lt;br/&gt;
                                       ↓
_convert_linebreaks_for_xml():     <br/>          ← unescaped FIRST
                                       ↓
loc.set("Str", "...<br/>...")      <br/> in memory
                                       ↓
lxml tree.write():                 &lt;br/&gt;    ← single escape (correct!)
```

Without the `&lt;br/&gt;` → `<br/>` step in `_convert_linebreaks_for_xml()`, lxml would serialize it as `&amp;lt;br/&amp;gt;` (double-escaped, broken).

---

## XML Sanitization (Reading Malformed Files)

**`sanitize_xml_content()`** — `xml_parser.py:98`

Before lxml even sees the file, the sanitizer handles:

1. **Control characters** stripped (`\x00-\x08`, `\x0b`, etc.)
2. **Bad `&` entities** fixed → `&amp;`
3. **Real newlines inside `<seg>`** → `&lt;br/&gt;` (raw text level, before parsing)
4. **Bare `<` in attributes** → `&lt;` (but `<br/>` is preserved — the regex explicitly skips it)
5. **Malformed tag structure** repaired

---

## Quality Checker: Stripping Before Checks

**`_strip_codes_and_markup()`** — `quality_checker.py:185`

Strips ALL markup including `<br/>` before running:
- Wrong-script detection (Korean in non-Korean, etc.)
- Length ratio checks
- Forward-slash false positive prevention (`<br/>` contains `/`)

---

## Function Reference

| Function | File:Line | Direction | Purpose |
|----------|-----------|-----------|---------|
| `_preprocess_newlines()` | `xml_parser.py:40` | XML Read | `\n` → `&lt;br/&gt;` inside `<seg>` (raw text pre-parse) |
| `sanitize_xml_content()` | `xml_parser.py:98` | XML Read | Full sanitization pipeline orchestrator |
| `_convert_linebreaks_for_xml()` | `xml_transfer.py:37` | Excel→XML | `\n`, `&lt;br/&gt;`, `\\n` → `<br/>` in memory |
| `_convert_linebreaks_for_excel()` | `excel_io.py:638` | XML→Excel | `<br/>`, `&lt;br/&gt;` → `\n` for cells |
| `_normalize_newlines()` | `postprocess.py:51` | Post-Transfer | ALL wrong formats → `<br/>` (7-step, comprehensive) |
| `cleanup_wrong_newlines_on_tree()` | `postprocess.py:182` | Post-Transfer | Applies normalize to all LocStr in tree |
| `run_all_postprocess()` | `postprocess.py:370` | Post-Transfer | Runs after every transfer (single parse/write) |
| `_has_wrong_newlines()` | `checker.py:76` | Detection | Flags wrong formats (bool, no fix) |
| `_escape_attr_value()` | `checker.py:107` | Checker Output | Manual `<` → `&lt;` for checker XML output |
| `_strip_codes_and_markup()` | `quality_checker.py:185` | Quality Check | Strips `<br/>` before script/ratio checks |
| `normalize_text()` | `text_utils.py:12` | Matching | `html.unescape()` decodes `&lt;br/&gt;` → `<br/>` |

---

## Edge Cases (All Handled)

| Case | Behavior |
|------|----------|
| Double `<br/><br/>` | Preserved as-is, no dedup |
| `<br/>` at start/end of string | Preserved, never trimmed |
| Mixed formats in same string | Each variant normalized independently |
| Empty string | All functions short-circuit, return as-is |
| `<br/>` inside `{code}` patterns | Treated as part of the code pattern for matching |

---

*Created 2026-02-26. Source of truth for linebreak handling across all tools.*
