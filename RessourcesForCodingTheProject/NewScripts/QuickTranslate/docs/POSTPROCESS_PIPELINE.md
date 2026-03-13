# QuickTranslate Postprocess Pipeline

> **File:** `core/postprocess.py`
> **Runs:** After every transfer operation (folder merge, file-to-file, fuzzy)
> **Golden Rule:** Only `Str` and `Desc` are modified. `StrOrigin`/`DescOrigin` are NEVER touched.

---

## Steps (in order)

### Step 1: Normalize Newlines → `<br/>`

`<br/>` is the ONLY correct newline format in XML language data.

| What | Example | Result |
|------|---------|--------|
| Wrong `<br>` variants | `<br>`, `<BR/>`, `</br>`, `<br />` | `<br/>` |
| Double-escaped br | `&lt;br/&gt;` in memory (from `&amp;lt;br/&amp;gt;` on disk) | `<br/>` |
| Actual newlines | `\n`, `\r\n`, `\r` | `<br/>` |
| Literal escape text | `\\n`, `\\r\\n` | `<br/>` |
| XML numeric entities | `&#10;`, `&#13;`, `&#xA;`, `&#xD;` | `<br/>` |
| Unicode line breaks | NEL U+0085, Line Separator U+2028, Paragraph Separator U+2029, VT, FF | `<br/>` |

### Step 2: Empty StrOrigin Enforcement

If `StrOrigin` is empty → `Str` MUST be empty. Same for `DescOrigin`/`Desc`.

### Step 3: "no translation" Replacement

If `Str` equals "no translation" (case-insensitive, whitespace-collapsed) → replace with `StrOrigin`. If `StrOrigin` is also empty → clear `Str`.

### Step 4: Apostrophe Normalization

| Character | Name | Becomes |
|-----------|------|---------|
| U+2018 | LEFT SINGLE QUOTATION MARK | `'` |
| U+2019 | RIGHT SINGLE QUOTATION MARK | `'` |
| U+00B4 | ACUTE ACCENT | `'` |
| U+02BC | MODIFIER LETTER APOSTROPHE | `'` |
| U+201B | SINGLE HIGH-REVERSED-9 QUOTATION MARK | `'` |
| U+FF07 | FULLWIDTH APOSTROPHE | `'` |

### Step 5: Invisible Character Cleanup

| Bucket | Action | Characters |
|--------|--------|------------|
| **Zs spaces** | Replace with regular space | NBSP U+00A0, en-space, em-space, thin space, etc. |
| **Safe invisible** | Delete entirely | 19 zero-width/bidi/control chars (ZWSP, BOM, soft hyphen, etc.) |
| **Grey zone** | Warn only, NO modification | ZWNJ U+200C, ZWJ U+200D |

**Excluded:** U+3000 ideographic space (CJK intentional).

### Step 6: Hyphen Normalization

| Character | Name | Becomes |
|-----------|------|---------|
| U+2010 | HYPHEN | `-` |
| U+2011 | NON-BREAKING HYPHEN | `-` |

En-dash, em-dash, minus sign are NOT touched (visually distinct).

### Step 7: Ellipsis Normalization (non-CJK only)

U+2026 `…` → `...` (three ASCII dots).

**Skipped for:** KOR, JPN, ZHO-CN, ZHO-TW (ellipsis is intentional in CJK).

### Step 8: Double-Escaped Entity Decode

Fixes entities that were escaped twice on disk. lxml decodes one layer on parse; Step 8 decodes the remaining layer.

| On disk (double-escaped) | In memory (after lxml) | After Step 8 |
|--------------------------|----------------------|--------------|
| `&amp;lt;` | `&lt;` | `<` |
| `&amp;gt;` | `&gt;` | `>` |
| `&amp;quot;` | `&quot;` | `"` |
| `&amp;apos;` | `&apos;` | `'` |
| `&amp;amp;desc;` | `&amp;desc;` | `&desc;` |
| `&amp;amp;nbsp;` | `&amp;nbsp;` | `&nbsp;` |

**NOT decoded:** Bare `&amp;` (could create broken entities).

**Order matters:** Step 1 runs FIRST and handles all `&lt;br/&gt;` patterns. Step 8 only sees remaining standalone `&lt;`/`&gt;`.

---

## Execution Paths

Two equivalent paths exist:

| Path | Used by | How |
|------|---------|-----|
| `run_all_postprocess(xml_path)` | Standalone postprocess | Multi-pass: parse once, run each step function, write once |
| `run_all_postprocess_on_tree(root)` | Fast folder merge (`_fast_folder_merge`) | Single-pass: one loop over all LocStr elements, all steps inline |

Both produce identical results.

---

## What Postprocess Does NOT Fix

| Pattern | Why |
|---------|-----|
| `&amp;gt` missing `;` (e.g. `&amp;gtil`) | Broken source data — can't safely distinguish entity from text |
| `;br/&amp;gt;` (partial corruption) | Broken source data — original `&lt;` already destroyed |
| Multiple consecutive `<br/><br/><br/>` | May be intentional |
| Leading/trailing `<br/>` | May be intentional |
| En-dash, em-dash | Visually distinct, may be intentional |
| ZWNJ / ZWJ | Linguistically meaningful in some languages |

---

*Last updated: 2026-03-13*
