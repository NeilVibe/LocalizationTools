"""
XML Parser Module

Battle-hardened XML sanitization and parsing for Crimson Desert game data.
Handles malformed XML, bad entities, unclosed tags, and other common issues.
"""

import os
import re
import logging
from pathlib import Path
from typing import Optional, Iterator, List

from lxml import etree as ET

log = logging.getLogger(__name__)


# =============================================================================
# REGEX PATTERNS
# =============================================================================

_BAD_ENTITY_RE = re.compile(r"&(?!(?:lt|gt|amp|apos|quot);)")
_TAG_OPEN_RE = re.compile(r"<([A-Za-z0-9_]+)(\s[^>/]*)?>")
_TAG_CLOSE_RE = re.compile(r"</\s*([A-Za-z0-9_]+)\s*>")
_CTRL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


# =============================================================================
# XML SANITIZATION (BATTLE-HARDENED)
# =============================================================================

def _patch_bad_entities(txt: str) -> str:
    """Replace unescaped ampersands with &amp;"""
    return _BAD_ENTITY_RE.sub("&amp;", txt)


def _patch_seg_breaks(txt: str) -> str:
    """Replace literal line breaks inside <seg> ... </seg> with escaped <br/>"""
    def repl(m: re.Match) -> str:
        inner = m.group(1).replace("\n", "&lt;br/&gt;").replace("\r\n", "&lt;br/&gt;")
        return f"<seg>{inner}</seg>"
    return re.sub(r"<seg>(.*?)</seg>", repl, txt, flags=re.DOTALL)


def _patch_unterminated_attr(txt: str) -> str:
    """Close un-terminated attribute values"""
    return re.sub(
        r'="[^"\n<>]*?(?:<|&)|="[^"]*?$',
        lambda m: m.group(0).rstrip("<&") + '"',
        txt,
    )


def _escape_inner_angles(raw: str) -> str:
    """Escape < and > inside attribute values"""
    raw = re.sub(
        r'="([^"]*<[^"]*)"',
        lambda m: '="' + m.group(1).replace("<", "&lt;") + '"',
        raw
    )
    return raw


def _escape_inner_ampersand(raw: str) -> str:
    """Escape & inside attribute values (not already part of entity)"""
    raw = re.sub(
        r'="([^"]*&[^ltgapoqu][^"]*)"',
        lambda m: '="' + m.group(1).replace("&", "&amp;") + '"',
        raw
    )
    return raw


def sanitize_xml(raw: str) -> str:
    """
    Multi-pass XML sanitization.

    Handles:
    - Control characters
    - Bad entity references
    - Line breaks inside <seg> tags
    - Unterminated attribute values
    - Angle brackets inside attribute values
    - Unmatched opening/closing tags

    Args:
        raw: Raw XML string

    Returns:
        Sanitized XML string
    """
    # Pass 1: Remove control characters
    raw = _CTRL_CHAR_RE.sub("", raw)

    # Pass 2: Fix bad entities
    raw = _patch_bad_entities(raw)

    # Pass 3: Handle <seg> breaks
    raw = _patch_seg_breaks(raw)

    # Pass 4: Fix unterminated attributes
    raw = _patch_unterminated_attr(raw)

    # Pass 5: Escape inner angles and ampersands
    raw = _escape_inner_angles(raw)
    raw = _escape_inner_ampersand(raw)

    # Pass 6: Tag stack repair for malformed XML
    tag_stack: List[str] = []
    fixed_lines: List[str] = []

    for line in raw.splitlines():
        s = line.strip()
        m_open = _TAG_OPEN_RE.match(s)
        m_close = _TAG_CLOSE_RE.match(s)

        if m_open and not s.endswith("/>"):
            tag_stack.append(m_open.group(1))
            fixed_lines.append(line)
            continue

        if s.startswith("</>"):
            if tag_stack:
                fixed_lines.append(f"</{tag_stack.pop()}>")
            continue

        if m_close:
            want = m_close.group(1)
            # Close any still-open tags that shouldn't be open
            while tag_stack and tag_stack[-1] != want:
                fixed_lines.append(f"</{tag_stack.pop()}>")
            if tag_stack:
                tag_stack.pop()
            fixed_lines.append(line)
            continue

        fixed_lines.append(line)

    # Close any remaining open tags
    while tag_stack:
        fixed_lines.append(f"</{tag_stack.pop()}>")

    return "\n".join(fixed_lines)


# =============================================================================
# XML PARSING
# =============================================================================

def parse_xml(path: Path) -> Optional[ET._Element]:
    """
    Parse XML file with dual-mode recovery.

    First attempts strict parsing, then falls back to sanitized parsing
    with recovery mode enabled.

    Args:
        path: Path to XML file

    Returns:
        Root element or None if parsing fails
    """
    try:
        raw = path.read_text("utf-8", errors="ignore")
    except Exception:
        log.exception("Failed to read %s", path)
        return None

    for mode, txt in (("strict", raw), ("sanitised", sanitize_xml(raw))):
        try:
            return ET.fromstring(
                f"<ROOT>{txt}</ROOT>",
                parser=ET.XMLParser(recover=(mode == "sanitised"), huge_tree=True),
            )
        except ET.XMLSyntaxError:
            continue

    log.warning("XML parse error → %s", path)
    return None


def parse_xml_string(xml_string: str) -> Optional[ET._Element]:
    """
    Parse XML string with dual-mode recovery.

    Args:
        xml_string: XML string to parse

    Returns:
        Root element or None if parsing fails
    """
    for mode, txt in (("strict", xml_string), ("sanitised", sanitize_xml(xml_string))):
        try:
            return ET.fromstring(
                f"<ROOT>{txt}</ROOT>",
                parser=ET.XMLParser(recover=(mode == "sanitised"), huge_tree=True),
            )
        except ET.XMLSyntaxError:
            continue

    return None


# =============================================================================
# FILE ITERATION
# =============================================================================

def iter_xml_files(
    root: Path,
    suffixes: tuple = (".xml",),
    recursive: bool = True
) -> Iterator[Path]:
    """
    Recursively iterate over XML files in a folder.

    Args:
        root: Root folder to search
        suffixes: File suffixes to include (default: .xml)
        recursive: Whether to search recursively

    Yields:
        Path objects for matching files
    """
    if not root.exists():
        return

    if recursive:
        for dp, _, files in os.walk(root):
            for fn in files:
                low = fn.lower()
                if any(low.endswith(suf) for suf in suffixes):
                    yield Path(dp) / fn
    else:
        for fn in root.iterdir():
            if fn.is_file():
                low = fn.name.lower()
                if any(low.endswith(suf) for suf in suffixes):
                    yield fn
