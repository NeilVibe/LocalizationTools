"""
XML Sanitizer -- Battle-tested XML sanitization and parsing for GameData.

GRAFTED from MapDataGenerator/core/xml_parser.py (QACompilerNEW pattern).
5-stage sanitization + virtual root wrapper + dual-pass parsing.

Stages:
  0. Remove invalid control characters
  1. Fix bad entity references (& not followed by entity name)
  2. Handle newlines inside <seg> tags
  3. Escape < inside attribute values
  4. Escape & inside attribute values (but not valid entities)
  5. Tag stack repair for malformed XML (mismatched/empty closing tags)
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional, List

from lxml import etree as ET
from loguru import logger


# =============================================================================
# XML SANITIZATION (EXACT COPY FROM MDG/QACompilerNEW - BATTLE-TESTED)
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
    Battle-tested XML sanitization from QACompilerNEW.

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
# MAIN ENTRY POINT: sanitize + virtual root + dual-pass parse
# =============================================================================

def sanitize_and_parse(path: Path) -> Optional[ET._Element]:
    """Read, sanitize, wrap in virtual root, dual-pass parse.

    Returns ROOT wrapper element or None on failure.
    Callers iterate ``list(root)`` to get top-level entities.

    Strategy (same as MDG/QACompilerNEW):
    1. Read file (UTF-8, ignore errors)
    2. Remove invalid control characters (Stage 0)
    3. Run 5-stage sanitization
    4. Wrap in <ROOT> virtual element
    5. Try strict parsing
    6. If fails, try recovery mode
    """
    try:
        raw = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        logger.exception(f"Failed to read {path}")
        return None

    # Stage 0: Remove invalid control chars
    raw = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', raw)

    cleaned = sanitize_xml(raw)
    wrapped = f"<ROOT>\n{cleaned}\n</ROOT>"

    # Pass 1: Strict
    try:
        return ET.fromstring(wrapped.encode("utf-8"), parser=ET.XMLParser(huge_tree=True))
    except ET.XMLSyntaxError:
        pass

    # Pass 2: Recovery
    try:
        root = ET.fromstring(wrapped.encode("utf-8"), parser=ET.XMLParser(recover=True, huge_tree=True))
        logger.debug(f"Parsed {path.name} with recovery mode")
        return root
    except Exception:
        logger.error(f"Failed to parse {path.name} even in recovery mode")
        return None
