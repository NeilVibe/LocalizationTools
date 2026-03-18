"""
XML Parsing Utilities for DataListGenerator
============================================
Provides XML sanitization and parsing functions.

ADAPTED FROM QACompilerNEW: Full 5-pass sanitization pipeline.
"""

import re
from pathlib import Path
from typing import Optional, List

try:
    from lxml import etree as ET
    USING_LXML = True
except ImportError:
    import xml.etree.ElementTree as ET
    USING_LXML = False
    print("Note: Using standard XML parser. Install lxml for better performance.")


# =============================================================================
# XML SANITIZATION (EXACT COPY FROM QACompiler)
# =============================================================================

_bad_entity_re = re.compile(r'&(?!lt;|gt;|amp;|apos;|quot;)')


def _fix_bad_entities(txt: str) -> str:
    """Fix bad XML entities: &unknown → &amp;unknown"""
    return _bad_entity_re.sub("&amp;", txt)


def _preprocess_newlines(raw: str) -> str:
    """Escape newlines inside <seg> tags."""
    def repl(m: re.Match) -> str:
        inner = m.group(1).replace("\n", "&lt;br/&gt;").replace("\r\n", "&lt;br/&gt;")
        return f"<seg>{inner}</seg>"
    return re.sub(r"<seg>(.*?)</seg>", repl, raw, flags=re.DOTALL)


def sanitize_xml(raw: str) -> str:
    """
    Full XML sanitization pipeline (from QACompiler).

    5-pass process:
    1. Fix bad entities (&unknown → &amp;)
    2. Escape newlines in <seg> tags
    3. Escape < in attribute values
    4. Escape bad & in attribute values
    5. Tag stack repair (auto-close unclosed tags)
    """
    # Pass 1: Fix bad entities
    raw = _fix_bad_entities(raw)

    # Pass 2: Escape newlines in seg tags
    raw = _preprocess_newlines(raw)

    # Pass 3: Escape < in attribute values
    raw = re.sub(
        r'="([^"]*<[^"]*)"',
        lambda m: '="' + m.group(1).replace("<", "&lt;") + '"',
        raw
    )

    # Pass 4: Escape bad & in attribute values (not valid entities)
    raw = re.sub(
        r'="([^"]*&[^ltgapoqu][^"]*)"',
        lambda m: '="' + m.group(1).replace("&", "&amp;") + '"',
        raw
    )

    # Pass 5: Tag stack repair for malformed XML
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

    # Auto-close remaining unclosed tags
    while stack:
        out.append(f"</{stack.pop()}>")

    return "\n".join(out)


def parse_xml_file(path: Path) -> Optional[ET._Element]:
    """
    Parse XML file with full sanitization, return root element or None on error.

    Wraps content in a ROOT element to handle multiple top-level elements.
    Uses two-stage fallback: normal parse first, then recover mode.
    """
    try:
        raw = path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"  Error reading {path.name}: {e}")
        return None

    cleaned = sanitize_xml(raw)
    wrapped = f"<ROOT>\n{cleaned}\n</ROOT>"

    if USING_LXML:
        # Stage 1: Try normal parse with huge_tree
        try:
            return ET.fromstring(
                wrapped.encode("utf-8"),
                parser=ET.XMLParser(huge_tree=True)
            )
        except ET.XMLSyntaxError:
            pass

        # Stage 2: Fallback with recover mode
        try:
            return ET.fromstring(
                wrapped.encode("utf-8"),
                parser=ET.XMLParser(recover=True, huge_tree=True)
            )
        except ET.XMLSyntaxError as e:
            print(f"  Error parsing {path.name}: {e}")
            return None
    else:
        # Standard library fallback
        try:
            return ET.fromstring(wrapped)
        except Exception as e:
            print(f"  Error parsing {path.name}: {e}")
            return None


def iter_xml_files(folder: Path) -> List[Path]:
    """Get all XML files in folder (non-recursive)."""
    if not folder.exists():
        print(f"  WARNING: Folder not found: {folder}")
        return []
    return sorted([f for f in folder.glob("*.xml") if f.is_file()])
