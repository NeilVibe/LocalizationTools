"""
XML Post-Processing Pipeline.

Runs cleanup passes on XML files AFTER transfer operations.
Each cleanup function is independent and can be added/removed easily.

Current cleanup steps (run in order):
  1. cleanup_wrong_newlines  - Normalize ALL newlines to <br/>
  2. cleanup_empty_strorigin - Clear Str when StrOrigin is empty

Usage:
    from core.postprocess import run_all_postprocess
    fixed = run_all_postprocess(xml_path)
"""

import os
import re
import stat
import logging
from pathlib import Path

# Try lxml first (more robust), fallback to standard library
try:
    from lxml import etree
    USING_LXML = True
except ImportError:
    from xml.etree import ElementTree as etree
    USING_LXML = False

logger = logging.getLogger(__name__)

# LocStr tag variants (case-insensitive matching)
_LOCSTR_TAGS = ['LocStr', 'locstr', 'LOCSTR', 'LOCStr', 'Locstr']

# Str attribute variants
_STR_ATTRS = ('Str', 'str', 'STR')

# StrOrigin attribute variants
_STRORIGIN_ATTRS = ('StrOrigin', 'Strorigin', 'strorigin', 'STRORIGIN')

# --- Compiled regex patterns for newline normalization ---

# <br> tag variants: <br>, <br/>, <br />, <BR>, <BR/>, <Br>, etc.
_BR_TAG_RE = re.compile(r'<[Bb][Rr]\s*/?>')

# HTML-escaped <br> variants: &lt;br/&gt;, &lt;br&gt;, &lt;BR/&gt;, etc.
_BR_ESCAPED_RE = re.compile(r'&lt;[Bb][Rr]\s*/?&gt;')

# CRLF as XML entity combo: &#13;&#10; or &#xD;&#xA; (with optional whitespace between)
_CRLF_ENTITY_RE = re.compile(r'&#[Xx]0?[Dd];\s*&#[Xx]0?[Aa];|&#13;\s*&#10;')

# Individual hex entity references for LF and CR
_HEX_LF_RE = re.compile(r'&#[Xx]0?[Aa];')
_HEX_CR_RE = re.compile(r'&#[Xx]0?[Dd];')


def _normalize_newlines(text: str) -> str:
    """
    Normalize ALL newline representations to <br/>.

    <br/> is the ONLY correct newline format in XML language data.
    This function handles every known newline variant:

    Escaped HTML tags:
        &lt;br/&gt;, &lt;br&gt;, &lt;BR/&gt;, etc.

    Wrong <br> tag variants:
        <br>, <BR/>, <BR>, <br />, <BR />, <Br/>, <bR/>, mixed case

    XML numeric entity references:
        &#10;, &#13;, &#xA;, &#xa;, &#x0A;, &#xD;, &#xd;, &#x0D;

    Actual control characters:
        \\r\\n (CRLF), \\r (CR), \\n (LF)

    Literal escape text:
        Backslash-n, backslash-r, backslash-r-backslash-n

    Unicode line break characters:
        NEL (U+0085), Line Separator (U+2028), Paragraph Separator (U+2029),
        Vertical Tab (U+000B), Form Feed (U+000C)

    Args:
        text: Attribute value (after XML parser decoding)

    Returns:
        Text with all newlines normalized to <br/>
    """
    if not text:
        return text

    # Step 1: Unescape HTML-escaped <br> variants (from double-escaping)
    # &lt;br/&gt; → <br/>,  &lt;br&gt; → <br/>,  &lt;BR/&gt; → <br/>
    text = _BR_ESCAPED_RE.sub('<br/>', text)

    # Step 2: Normalize all <br> tag variants to <br/>
    # <br> → <br/>,  <BR/> → <br/>,  <br /> → <br/>,  <Br> → <br/>
    # Note: <br/> → <br/> (no-op, correct form stays correct)
    text = _BR_TAG_RE.sub('<br/>', text)

    # Step 3: Replace CRLF entity combos FIRST (before individual entities)
    # &#13;&#10; → <br/>,  &#xD;&#xA; → <br/>
    text = _CRLF_ENTITY_RE.sub('<br/>', text)

    # Step 4: Replace individual XML entity references
    # &#10; → <br/>,  &#13; → <br/>
    text = text.replace('&#10;', '<br/>')
    text = text.replace('&#13;', '<br/>')
    # &#xA; &#xa; &#x0A; &#x0a; → <br/>
    text = _HEX_LF_RE.sub('<br/>', text)
    # &#xD; &#xd; &#x0D; &#x0d; → <br/>
    text = _HEX_CR_RE.sub('<br/>', text)

    # Step 5: Replace actual control characters (CRLF combo first!)
    text = text.replace('\r\n', '<br/>')
    text = text.replace('\r', '<br/>')
    text = text.replace('\n', '<br/>')

    # Step 6: Replace literal escape sequences (backslash + letter as text)
    text = text.replace('\\r\\n', '<br/>')
    text = text.replace('\\n', '<br/>')
    text = text.replace('\\r', '<br/>')

    # Step 7: Unicode line break characters
    text = text.replace('\u0085', '<br/>')   # NEL (Next Line)
    text = text.replace('\u2028', '<br/>')   # Line Separator
    text = text.replace('\u2029', '<br/>')   # Paragraph Separator
    text = text.replace('\x0b', '<br/>')     # Vertical Tab
    text = text.replace('\x0c', '<br/>')     # Form Feed

    return text


def _parse_xml(xml_path: Path):
    """Parse XML file, returns (tree, root). Shared by all postprocess functions."""
    if USING_LXML:
        parser = etree.XMLParser(
            resolve_entities=False, load_dtd=False,
            no_network=True, recover=True,
        )
        tree = etree.parse(str(xml_path), parser)
    else:
        tree = etree.parse(str(xml_path))
    return tree, tree.getroot()


def _write_xml(tree, xml_path: Path):
    """Write XML tree back to file. Shared by all postprocess functions."""
    try:
        current_mode = os.stat(xml_path).st_mode
        if not current_mode & stat.S_IWRITE:
            os.chmod(xml_path, current_mode | stat.S_IWRITE)
    except Exception:
        pass

    if USING_LXML:
        tree.write(str(xml_path), encoding="utf-8", xml_declaration=False, pretty_print=True)
    else:
        tree.write(str(xml_path), encoding="utf-8", xml_declaration=False)


def _iter_locstr(root):
    """Iterate all LocStr elements (case-insensitive tag matching)."""
    elements = []
    for tag in _LOCSTR_TAGS:
        elements.extend(root.iter(tag))
    return elements


def _get_attr(loc, attr_variants):
    """Get attribute name and value from element, trying multiple case variants."""
    for attr_name in attr_variants:
        val = loc.get(attr_name)
        if val is not None:
            return attr_name, val
    return None, None


# ─── Cleanup Step 1: Normalize newlines ─────────────────────────────────────


def cleanup_wrong_newlines_on_tree(root) -> int:
    """
    Normalize all wrong newline representations to <br/> in parsed tree.

    Scans Str and StrOrigin attributes of all LocStr elements.

    Args:
        root: Parsed XML root element

    Returns:
        Number of attributes fixed
    """
    fixed = 0
    for loc in _iter_locstr(root):
        for attr_variants in (_STR_ATTRS, _STRORIGIN_ATTRS):
            attr_name, val = _get_attr(loc, attr_variants)
            if val is not None:
                normalized = _normalize_newlines(val)
                if normalized != val:
                    loc.set(attr_name, normalized)
                    fixed += 1
    return fixed


# ─── Cleanup Step 2: Empty StrOrigin enforcement ────────────────────────────


def cleanup_empty_strorigin_on_tree(root) -> int:
    """
    Clear Str on any element where StrOrigin is empty.

    Golden rule: if StrOrigin is empty, Str MUST be empty too.

    Args:
        root: Parsed XML root element

    Returns:
        Number of entries cleaned (Str cleared)
    """
    cleaned = 0
    for loc in _iter_locstr(root):
        _, origin = _get_attr(loc, _STRORIGIN_ATTRS)
        origin = (origin or "").strip()

        _, str_val = _get_attr(loc, _STR_ATTRS)
        str_val = (str_val or "").strip()

        if not origin and str_val:
            loc.set("Str", "")
            cleaned += 1
    return cleaned


# ─── Public API: Standalone functions (backward-compatible) ──────────────────


def cleanup_wrong_newlines(xml_path: Path, dry_run: bool = False) -> int:
    """
    Post-process: normalize all wrong newline representations to <br/>.

    <br/> is the ONLY correct newline format in XML language data.

    Args:
        xml_path: Path to XML file
        dry_run: If True, count but don't write

    Returns:
        Number of attributes fixed
    """
    try:
        tree, root = _parse_xml(xml_path)
        fixed = cleanup_wrong_newlines_on_tree(root)

        if fixed > 0 and not dry_run:
            _write_xml(tree, xml_path)
            logger.info(f"Normalized {fixed} wrong newlines in {xml_path.name}")

        return fixed
    except Exception as e:
        logger.error(f"Error normalizing newlines in {xml_path}: {e}")
        return 0


def cleanup_empty_strorigin(xml_path: Path, dry_run: bool = False) -> int:
    """
    Post-process: clear Str on any element where StrOrigin is empty.

    Golden rule: if StrOrigin is empty, Str MUST be empty too.

    Args:
        xml_path: Path to XML file
        dry_run: If True, count but don't write

    Returns:
        Number of entries cleaned (Str cleared)
    """
    try:
        tree, root = _parse_xml(xml_path)
        cleaned = cleanup_empty_strorigin_on_tree(root)

        if cleaned > 0 and not dry_run:
            _write_xml(tree, xml_path)
            logger.info(f"Cleaned {cleaned} entries with empty StrOrigin in {xml_path.name}")

        return cleaned
    except Exception as e:
        logger.error(f"Error cleaning empty StrOrigin in {xml_path}: {e}")
        return 0


# ─── Unified Runner ─────────────────────────────────────────────────────────


def run_all_postprocess(xml_path: Path, dry_run: bool = False) -> dict:
    """
    Run ALL postprocess cleanup steps on an XML file.

    Single parse, all cleanups, single write. Efficient and atomic.

    Current steps (in order):
      1. cleanup_wrong_newlines  - Normalize ALL newlines to <br/>
      2. cleanup_empty_strorigin - Clear Str when StrOrigin is empty

    Args:
        xml_path: Path to XML file
        dry_run: If True, count but don't write

    Returns:
        Dict with counts per cleanup step, e.g.:
        {"newlines_fixed": 5, "empty_strorigin_cleaned": 2, "total_fixes": 7}
    """
    result = {
        "newlines_fixed": 0,
        "empty_strorigin_cleaned": 0,
        "total_fixes": 0,
    }

    try:
        tree, root = _parse_xml(xml_path)

        # Step 1: Normalize newlines (run FIRST so text is clean for later steps)
        result["newlines_fixed"] = cleanup_wrong_newlines_on_tree(root)

        # Step 2: Empty StrOrigin enforcement
        result["empty_strorigin_cleaned"] = cleanup_empty_strorigin_on_tree(root)

        result["total_fixes"] = result["newlines_fixed"] + result["empty_strorigin_cleaned"]

        # Write once if anything changed
        if result["total_fixes"] > 0 and not dry_run:
            _write_xml(tree, xml_path)

            if result["newlines_fixed"] > 0:
                logger.info(
                    f"Post-process: normalized {result['newlines_fixed']} "
                    f"wrong newlines in {xml_path.name}"
                )
            if result["empty_strorigin_cleaned"] > 0:
                logger.info(
                    f"Post-process: cleared Str on {result['empty_strorigin_cleaned']} "
                    f"entries with empty StrOrigin in {xml_path.name}"
                )

        return result
    except Exception as e:
        logger.error(f"Error in postprocess for {xml_path}: {e}")
        return result
