"""Text normalisation, visible character counting, and newline handling."""

from __future__ import annotations

import html
import re

# ---------------------------------------------------------------------------
# Newline normalisation regexes (ported from QuickTranslate)
# ---------------------------------------------------------------------------

# HTML-escaped <br> variants: &lt;br/&gt;, &lt;br&gt;, &lt;BR/&gt;, etc.
_BR_ESCAPED_RE = re.compile(r'&lt;[Bb][Rr]\s*/?&gt;')

# <br> tag variants: <br>, <br/>, <br />, <BR>, <BR/>, <Br>, etc.
_BR_TAG_NL_RE = re.compile(r'<[Bb][Rr]\s*/?>')

# CRLF as XML entity combo: &#13;&#10; or &#xD;&#xA;
_CRLF_ENTITY_RE = re.compile(r'&#[Xx]0?[Dd];\s*&#[Xx]0?[Aa];|&#13;\s*&#10;')

# Individual hex entity references for LF and CR
_HEX_LF_RE = re.compile(r'&#[Xx]0?[Aa];')
_HEX_CR_RE = re.compile(r'&#[Xx]0?[Dd];')

# Any <br...> tag (for wrong-variant detection)
_BR_ANY_RE = re.compile(r'<br\s*/?\s*>', re.IGNORECASE)


# ---------------------------------------------------------------------------
# Newline normalisation functions (ported from QuickTranslate)
# ---------------------------------------------------------------------------

def normalize_newlines(text: str) -> str:
    """Normalize ALL newline representations to ``<br/>``.

    7-step pipeline covering every known variant:
    1. HTML-escaped ``&lt;br/&gt;`` tags
    2. Wrong ``<br>`` tag variants (case, spacing)
    3. CRLF XML entity combos (``&#13;&#10;``)
    4. Individual XML entities (``&#10;``, ``&#xA;``, etc.)
    5. Actual control characters (``\\r\\n``, ``\\r``, ``\\n``)
    6. Literal escape text (backslash-n/r as typed text)
    7. Unicode line break characters (NEL, LS, PS, VT, FF)
    """
    if not text:
        return text

    # Step 1: HTML-escaped <br> variants
    text = _BR_ESCAPED_RE.sub('<br/>', text)

    # Step 2: Wrong <br> tag variants → <br/>
    text = _BR_TAG_NL_RE.sub('<br/>', text)

    # Step 3: CRLF entity combos (before individual entities)
    text = _CRLF_ENTITY_RE.sub('<br/>', text)

    # Step 4: Individual XML entity references
    text = text.replace('&#10;', '<br/>')
    text = text.replace('&#13;', '<br/>')
    text = _HEX_LF_RE.sub('<br/>', text)
    text = _HEX_CR_RE.sub('<br/>', text)

    # Step 5: Actual control characters (CRLF first)
    text = text.replace('\r\n', '<br/>')
    text = text.replace('\r', '<br/>')
    text = text.replace('\n', '<br/>')

    # Step 6: Literal escape sequences (backslash + letter as text)
    text = text.replace('\\r\\n', '<br/>')
    text = text.replace('\\n', '<br/>')
    text = text.replace('\\r', '<br/>')

    # Step 7: Unicode line break characters
    text = text.replace('\u0085', '<br/>')   # NEL
    text = text.replace('\u2028', '<br/>')   # Line Separator
    text = text.replace('\u2029', '<br/>')   # Paragraph Separator
    text = text.replace('\x0b', '<br/>')     # Vertical Tab
    text = text.replace('\x0c', '<br/>')     # Form Feed

    return text


def has_wrong_newlines(text: str) -> bool:
    """Check if *text* contains any wrong newline representation.

    The only correct newline in XML language data is ``<br/>``.
    """
    if not text:
        return False

    if '\n' in text or '\r' in text:
        return True
    if '\\n' in text or '\\r' in text:
        return True
    if '\u2028' in text or '\u2029' in text:
        return True

    for m in _BR_ANY_RE.finditer(text):
        if m.group() != '<br/>':
            return True

    return False


def convert_linebreaks_for_xml(txt: str) -> str:
    """Convert Excel linebreaks to ``<br/>`` for XML storage.

    Handles: HTML-escaped ``&lt;br/&gt;`` (copy-paste from XML),
    actual ``\\n`` (Alt+Enter in Excel), literal ``\\\\n`` text.
    """
    if not txt:
        return txt
    txt = txt.replace('&lt;br/&gt;', '<br/>')
    txt = txt.replace('&lt;br /&gt;', '<br/>')
    txt = txt.replace('\n', '<br/>')
    txt = txt.replace('\\n', '<br/>')
    return txt


def br_to_newline(txt: str) -> str:
    """Convert ``<br/>`` (all case variants) to ``\\n`` for Excel display."""
    if not txt:
        return txt
    return _BR_TAG_NL_RE.sub('\n', txt)


# ---------------------------------------------------------------------------
# Normalisation (QuickTranslate-compatible)
# ---------------------------------------------------------------------------

def normalize_text(txt: str) -> str:
    """HTML-unescape, collapse whitespace, strip &desc; prefix."""
    txt = html.unescape(str(txt))
    txt = re.sub(r"\s+", " ", txt.strip())
    low = txt.lower()
    if low.startswith("&desc;"):
        txt = txt[6:].lstrip()
    elif low.startswith("&amp;desc;"):
        txt = txt[10:].lstrip()
    return txt


def normalize_nospace(txt: str) -> str:
    """Remove all whitespace from *already-normalised* text."""
    return re.sub(r"\s+", "", txt)


# ---------------------------------------------------------------------------
# Visible character counting (matches trianglelen.py reference)
# ---------------------------------------------------------------------------

_BR_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)
_SCALE_RE = re.compile(r"<Scale[^>]*>|</Scale>")
_COLOR_RE = re.compile(r"<color[^>]*>|</color>")
_PACOLOR_RE = re.compile(r"<PAColor[^>]*>|<PAOldColor>")
_STYLE_RE = re.compile(r"<Style:[^>]*>")
_BACKSLASH_N_RE = re.compile(r"\\n")
_CURLY_RE = re.compile(r"\{[^}]*\}")
_WHITESPACE_RE = re.compile(r"\s+")


def visible_char_count(text: str) -> int:
    """Return the number of 'visible' characters after stripping markup."""
    t = _BR_RE.sub("", text)
    t = _SCALE_RE.sub("", t)
    t = _COLOR_RE.sub("", t)
    t = _PACOLOR_RE.sub("", t)
    t = _STYLE_RE.sub("", t)
    t = _BACKSLASH_N_RE.sub("", t)
    t = _CURLY_RE.sub("", t)
    t = html.unescape(t)
    t = _WHITESPACE_RE.sub(" ", t).strip()
    return len(t)
