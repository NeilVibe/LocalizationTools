"""
Postprocess Pipeline -- 8-step cleanup for translated text values.

Ported from QuickTranslate core/postprocess.py.

Runs cleanup passes on text values AFTER transfer/merge operations.
Each step is independent. Pipeline runs all 8 steps in order on Str/Desc
values only (never on StrOrigin/DescOrigin).

Steps:
  1. newlines         - Normalize ALL newlines to <br/>
  2. empty_strorigin  - Clear target when source is empty
  3. no_translation   - Replace "no translation" with empty string
  4. apostrophes      - Normalize curly/fancy apostrophes to ASCII
  5. invisible_chars  - NBSP -> space, zero-width chars deleted
  6. hyphens          - Unicode hyphens -> ASCII hyphen-minus
  7. ellipsis         - Unicode ellipsis -> three dots (non-CJK only)
  8. double_escaped   - Decode double-escaped entities
"""

from __future__ import annotations

import re
import logging
import unicodedata

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Step 1: Newline normalization
# ---------------------------------------------------------------------------

# <br> tag variants: <br>, <br/>, <br />, <BR>, etc.
_BR_TAG_RE = re.compile(r'</?[Bb][Rr]\s*/?>')

# HTML-escaped <br> variants: &lt;br/&gt;, &lt;br&gt;, etc.
_BR_ESCAPED_RE = re.compile(r'&lt;/?[Bb][Rr]\s*/?&gt;')

# CRLF as XML entity combo
_CRLF_ENTITY_RE = re.compile(r'&#[Xx]0?[Dd];\s*&#[Xx]0?[Aa];|&#13;\s*&#10;')

# Individual hex entity references for LF and CR
_HEX_LF_RE = re.compile(r'&#[Xx]0?[Aa];')
_HEX_CR_RE = re.compile(r'&#[Xx]0?[Dd];')


def _normalize_newlines(text: str) -> str:
    """Normalize ALL newline representations to <br/>.

    <br/> is the ONLY correct newline format in XML language data.
    """
    if not text:
        return text

    # HTML-escaped <br> variants
    text = _BR_ESCAPED_RE.sub('<br/>', text)
    # All <br> tag variants to <br/>
    text = _BR_TAG_RE.sub('<br/>', text)
    # CRLF entity combos first
    text = _CRLF_ENTITY_RE.sub('<br/>', text)
    # Individual XML entity references
    text = text.replace('&#10;', '<br/>')
    text = text.replace('&#13;', '<br/>')
    text = _HEX_LF_RE.sub('<br/>', text)
    text = _HEX_CR_RE.sub('<br/>', text)
    # Actual control characters (CRLF combo first)
    text = text.replace('\r\n', '<br/>')
    text = text.replace('\r', '<br/>')
    text = text.replace('\n', '<br/>')
    # Literal escape sequences
    text = text.replace('\\r\\n', '<br/>')
    text = text.replace('\\n', '<br/>')
    text = text.replace('\\r', '<br/>')
    # Unicode line break characters
    text = text.replace('\u0085', '<br/>')
    text = text.replace('\u2028', '<br/>')
    text = text.replace('\u2029', '<br/>')
    text = text.replace('\x0b', '<br/>')
    text = text.replace('\x0c', '<br/>')

    return text


# ---------------------------------------------------------------------------
# Step 2: Empty source enforcement
# ---------------------------------------------------------------------------


def _enforce_empty_strorigin(text: str, source: str | None) -> str:
    """If source is empty, target must be empty too.

    When source is None, step is skipped (source not applicable).
    When source is "" or whitespace-only, target is cleared.
    """
    if source is None:
        return text
    if not source.strip():
        return ""
    return text


# ---------------------------------------------------------------------------
# Step 3: "No translation" removal
# ---------------------------------------------------------------------------

_WHITESPACE_RE = re.compile(r'\s+')


def _remove_no_translation(text: str) -> str:
    """Replace 'no translation' with empty string."""
    normalized = _WHITESPACE_RE.sub(' ', text.strip()).lower()
    if normalized == 'no translation':
        return ""
    return text


# ---------------------------------------------------------------------------
# Step 4: Apostrophe normalization
# ---------------------------------------------------------------------------

_APOSTROPHE_TABLE = str.maketrans({
    '\u2018': "'",  # LEFT SINGLE QUOTATION MARK
    '\u2019': "'",  # RIGHT SINGLE QUOTATION MARK
    '\u00B4': "'",  # ACUTE ACCENT
    '\u02BC': "'",  # MODIFIER LETTER APOSTROPHE
    '\u201B': "'",  # SINGLE HIGH-REVERSED-9 QUOTATION MARK
    '\uFF07': "'",  # FULLWIDTH APOSTROPHE
})


def _normalize_apostrophes(text: str) -> str:
    """Normalize curly/fancy apostrophes to standard ASCII apostrophe."""
    return text.translate(_APOSTROPHE_TABLE)


# ---------------------------------------------------------------------------
# Step 5: Invisible character cleanup
# ---------------------------------------------------------------------------

# Bucket 2 -- safe invisible chars to delete entirely
_SAFE_INVISIBLE_DELETE = frozenset({
    '\u200b',   # Zero-width space
    '\ufeff',   # BOM / zero-width no-break space
    '\u200e',   # Left-to-right mark
    '\u200f',   # Right-to-left mark
    '\u2060',   # Word joiner
    '\u00ad',   # Soft hyphen
    '\u2061',   # Function application
    '\u2062',   # Invisible times
    '\u2063',   # Invisible separator
    '\u2064',   # Invisible plus
    '\u034f',   # Combining grapheme joiner
    '\u061c',   # Arabic letter mark
    '\u180e',   # Mongolian vowel separator
    '\u2066',   # Left-to-right isolate
    '\u2067',   # Right-to-left isolate
    '\u2068',   # First strong isolate
    '\u2069',   # Pop directional isolate
    '\u202a',   # Left-to-right embedding
    '\u202b',   # Right-to-left embedding
    '\u202c',   # Pop directional formatting
    '\u202d',   # Left-to-right override
    '\u202e',   # Right-to-left override
})


def _cleanup_invisible_chars(text: str) -> str:
    """Clean invisible characters.

    Bucket 1 (Zs spaces like NBSP): replace with regular space.
    Bucket 2 (safe invisible like zero-width space, BOM): delete.
    """
    if not text:
        return text

    chars = []
    changed = False
    for ch in text:
        if ch in _SAFE_INVISIBLE_DELETE:
            changed = True
            # Delete (skip)
        elif ch != ' ' and ch != '\u3000' and unicodedata.category(ch) == 'Zs':
            # Zs space -> regular space (U+3000 ideographic space excluded for CJK)
            chars.append(' ')
            changed = True
        else:
            chars.append(ch)

    if not changed:
        return text
    return ''.join(chars)


# ---------------------------------------------------------------------------
# Step 6: Hyphen normalization
# ---------------------------------------------------------------------------

_HYPHEN_TABLE = str.maketrans({
    '\u2010': "-",  # HYPHEN
    '\u2011': "-",  # NON-BREAKING HYPHEN
})


def _normalize_hyphens(text: str) -> str:
    """Normalize Unicode hyphen lookalikes to ASCII hyphen-minus.

    Only U+2010 and U+2011. en/em dashes are NOT touched.
    """
    return text.translate(_HYPHEN_TABLE)


# ---------------------------------------------------------------------------
# Step 7: Ellipsis normalization (non-CJK only)
# ---------------------------------------------------------------------------


def _normalize_ellipsis(text: str) -> str:
    """Replace Unicode horizontal ellipsis (U+2026) with three ASCII dots."""
    return text.replace('\u2026', '...')


# ---------------------------------------------------------------------------
# Step 8: Safe double-escaped entity decode
# ---------------------------------------------------------------------------

_SAFE_AMP_ENTITIES_RE = re.compile(
    r'&amp;(desc|nbsp|ensp|emsp|thinsp|hellip|bull|middot|lrm|rlm);',
    re.IGNORECASE,
)


def _decode_safe_entities(text: str) -> str:
    """Safely decode double-escaped XML entities.

    Decodes:
      - &amp;desc; -> &desc; (and other known named entities)
      - &lt; / &gt; -> < / >
      - &quot; -> "
      - &apos; -> '

    NOT decoded: &amp; alone (could create broken entities).
    """
    text = _SAFE_AMP_ENTITIES_RE.sub(lambda m: f'&{m.group(1)};', text)
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    text = text.replace('&quot;', '"')
    text = text.replace('&apos;', "'")
    return text


# ---------------------------------------------------------------------------
# Pipeline definition -- steps in exact execution order
# ---------------------------------------------------------------------------

# Each entry is (step_name, step_function)
# Step functions take (text: str) -> str, except step 2 which needs source
POSTPROCESS_STEPS: list[tuple[str, callable]] = [
    ("newlines", _normalize_newlines),
    ("empty_strorigin", _enforce_empty_strorigin),
    ("no_translation", _remove_no_translation),
    ("apostrophes", _normalize_apostrophes),
    ("invisible_chars", _cleanup_invisible_chars),
    ("hyphens", _normalize_hyphens),
    ("ellipsis", _normalize_ellipsis),
    ("double_escaped", _decode_safe_entities),
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def postprocess_value(
    value: str,
    source: str | None = None,
    is_cjk: bool = False,
) -> tuple[str, dict[str, int]]:
    """Run all 8 postprocess steps on a single text value.

    Args:
        value: The translated text to clean up (Str or Desc).
        source: The source text (StrOrigin or DescOrigin) -- used by step 2.
                None means source not applicable (step 2 skipped).
                Empty string means source IS empty (target cleared).
        is_cjk: If True, skip ellipsis normalization (step 7).

    Returns:
        Tuple of (cleaned_value, stats_dict) where stats_dict tracks
        how many changes each step made (0 or 1 per step).
    """
    stats: dict[str, int] = {name: 0 for name, _ in POSTPROCESS_STEPS}

    if not value and not isinstance(value, str):
        return "", stats
    if value == "":
        return "", stats

    result = value
    for name, step_fn in POSTPROCESS_STEPS:
        # Step 2 needs source text
        if name == "empty_strorigin":
            new_result = step_fn(result, source)
        # Step 7: skip for CJK
        elif name == "ellipsis" and is_cjk:
            continue
        else:
            new_result = step_fn(result)

        if new_result != result:
            stats[name] += 1
        result = new_result

    return result, stats


def postprocess_rows(
    rows: list[dict],
    is_cjk: bool = False,
) -> tuple[list[dict], dict[str, int]]:
    """Run postprocess pipeline on a batch of row dicts.

    Operates on the "target" field only. Source field is used for step 2
    (empty source enforcement) but never modified.

    Args:
        rows: List of dicts with at least "source" and "target" keys.
        is_cjk: If True, skip ellipsis normalization.

    Returns:
        Tuple of (processed_rows, aggregate_stats).
    """
    aggregate_stats: dict[str, int] = {name: 0 for name, _ in POSTPROCESS_STEPS}

    for row in rows:
        if "target" not in row:
            continue

        source = row.get("source", "")
        cleaned, stats = postprocess_value(
            row["target"],
            source=source,
            is_cjk=is_cjk,
        )
        row["target"] = cleaned

        for key, count in stats.items():
            aggregate_stats[key] += count

    return rows, aggregate_stats
