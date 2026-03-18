"""
XML Parser Module
=================
Battle-tested XML sanitization and parsing for localization data.
COPIED from MapDataGenerator/QACompilerNEW pattern - proven to work.
"""

import os
import re
import logging
from pathlib import Path
from typing import Optional, Iterator, List

from lxml import etree as ET

log = logging.getLogger(__name__)


# =============================================================================
# XML SANITIZATION (BATTLE-TESTED)
# =============================================================================

_bad_entity_re = re.compile(r'&(?!lt;|gt;|amp;|apos;|quot;)')


def _fix_bad_entities(txt: str) -> str:
    """Fix unescaped & characters."""
    return _bad_entity_re.sub("&amp;", txt)


def _preprocess_newlines(raw: str) -> str:
    """Handle newlines inside <seg> tags."""
    def repl(m: re.Match) -> str:
        inner = m.group(1).replace("\n", "&lt;br/&gt;").replace("\r\n", "&lt;br/&gt;")
        return f"<seg>{inner}</seg>"
    return re.sub(r"<seg>(.*?)</seg>", repl, raw, flags=re.DOTALL)


def sanitize_xml(raw: str) -> str:
    """
    Battle-tested XML sanitization.

    Handles:
    - Bad entity references (& not followed by entity name)
    - Newlines inside <seg> tags
    - < and & inside attribute values
    - Malformed closing tags (</>)
    - Mismatched tag pairs

    Does NOT try to fix unterminated attributes - let lxml recover handle that.
    """
    # Step 1: Fix bad entities
    raw = _fix_bad_entities(raw)

    # Step 2: Handle <seg> newlines
    raw = _preprocess_newlines(raw)

    # Step 3: Escape < inside attribute values
    raw = re.sub(r'="([^"]*<[^"]*)"',
                 lambda m: '="' + m.group(1).replace("<", "&lt;") + '"', raw)

    # Step 4: Escape & inside attribute values (but not valid entities)
    raw = re.sub(r'="([^"]*&[^ltgapoqu][^"]*)"',
                 lambda m: '="' + m.group(1).replace("&", "&amp;") + '"', raw)

    # Step 5: Tag stack repair for malformed XML
    tag_open = re.compile(r"<([A-Za-z0-9_]+)(\s[^>]*)?>")
    tag_close = re.compile(r"</([A-Za-z0-9_]+)>")
    stack: List[str] = []
    out: List[str] = []

    for line in raw.splitlines():
        stripped = line.strip()
        mo = tag_open.match(stripped)
        if mo:
            stack.append(mo.group(1))
            out.append(line)
            continue
        mc = tag_close.match(stripped)
        if mc:
            if stack and stack[-1] == mc.group(1):
                stack.pop()
                out.append(line)
            else:
                out.append(stack and f"</{stack.pop()}>" or line)
            continue
        if stripped.startswith("</>"):
            out.append(stack and line.replace("</>", f"</{stack.pop()}>") or line)
            continue
        out.append(line)

    while stack:
        out.append(f"</{stack.pop()}>")

    return "\n".join(out)


# =============================================================================
# XML PARSING
# =============================================================================

def parse_xml(path: Path) -> Optional[ET._Element]:
    """
    Parse XML file with sanitization and recovery.

    Strategy:
    1. Read file
    2. Sanitize with battle-tested regex
    3. Wrap in <ROOT> element
    4. Try strict parsing
    5. If fails, try recovery mode
    """
    try:
        raw = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        log.exception("Failed to read %s", path)
        return None

    cleaned = sanitize_xml(raw)
    wrapped = f"<ROOT>\n{cleaned}\n</ROOT>"

    # Try strict parsing first
    try:
        root = ET.fromstring(
            wrapped.encode("utf-8"),
            parser=ET.XMLParser(huge_tree=True)
        )
        return root
    except ET.XMLSyntaxError:
        pass

    # Fallback to recovery mode
    try:
        root = ET.fromstring(
            wrapped.encode("utf-8"),
            parser=ET.XMLParser(recover=True, huge_tree=True)
        )
        log.debug("Parsed %s with recovery mode", path.name)
        return root
    except ET.XMLSyntaxError:
        log.warning("XML parse error -> %s", path)
        return None


def parse_xml_string(xml_string: str) -> Optional[ET._Element]:
    """Parse XML string with sanitization and recovery."""
    cleaned = sanitize_xml(xml_string)
    wrapped = f"<ROOT>\n{cleaned}\n</ROOT>"

    try:
        return ET.fromstring(
            wrapped.encode("utf-8"),
            parser=ET.XMLParser(huge_tree=True)
        )
    except ET.XMLSyntaxError:
        pass

    try:
        return ET.fromstring(
            wrapped.encode("utf-8"),
            parser=ET.XMLParser(recover=True, huge_tree=True)
        )
    except ET.XMLSyntaxError:
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
