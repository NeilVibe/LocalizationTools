"""
XML Sanitization and Parsing.

Battle-tested XML parsing with sanitization from LanguageDataExporter.
Handles common XML issues: bad entities, newlines in seg elements, control chars.
"""

import re
from pathlib import Path

# Try lxml first (more robust), fallback to standard library
try:
    from lxml import etree as ET
    USING_LXML = True
except ImportError:
    from xml.etree import ElementTree as ET
    USING_LXML = False

# Regex for unescaped ampersands (not part of valid XML entities)
_bad_entity_re = re.compile(r'&(?!lt;|gt;|amp;|apos;|quot;)')


def _fix_bad_entities(txt: str) -> str:
    """Fix unescaped ampersands by converting them to &amp;."""
    return _bad_entity_re.sub("&amp;", txt)


def _preprocess_newlines(raw: str) -> str:
    """Handle newlines in seg elements by converting to &lt;br/&gt;."""
    def repl(m: re.Match) -> str:
        inner = m.group(1).replace("\n", "&lt;br/&gt;").replace("\r\n", "&lt;br/&gt;")
        return f"<seg>{inner}</seg>"
    return re.sub(r"<seg>(.*?)</seg>", repl, raw, flags=re.DOTALL)


def sanitize_xml_content(raw: str) -> str:
    """
    Sanitize XML content to handle common issues.

    Handles:
    - Control characters (removes)
    - Unescaped ampersands
    - Newlines in seg elements
    - Unescaped < and & in attribute values
    """
    # Remove control characters
    raw = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', raw)

    # Fix bad entities
    raw = _fix_bad_entities(raw)

    # Handle newlines in seg elements
    raw = _preprocess_newlines(raw)

    # Fix unescaped < in attribute values
    raw = re.sub(r'="([^"]*<[^"]*)"',
                 lambda m: '="' + m.group(1).replace("<", "&lt;") + '"', raw)

    # Fix unescaped & in attribute values (not part of entities)
    raw = re.sub(r'="([^"]*&[^ltgapoqu][^"]*)"',
                 lambda m: '="' + m.group(1).replace("&", "&amp;") + '"', raw)

    return raw


def parse_xml_file(xml_path: Path) -> ET.Element:
    """
    Parse XML file with sanitization and recovery mode.

    Args:
        xml_path: Path to the XML file

    Returns:
        Root element of parsed XML (wrapped in ROOT if using lxml)

    Raises:
        ET.XMLSyntaxError: If parsing fails even with recovery mode
    """
    content = xml_path.read_text(encoding='utf-8')
    content = sanitize_xml_content(content)

    if USING_LXML:
        wrapped = f"<ROOT>\n{content}\n</ROOT>"
        try:
            return ET.fromstring(
                wrapped.encode("utf-8"),
                parser=ET.XMLParser(huge_tree=True)
            )
        except ET.XMLSyntaxError:
            # Try recovery mode for badly formed XML
            return ET.fromstring(
                wrapped.encode("utf-8"),
                parser=ET.XMLParser(recover=True, huge_tree=True)
            )
    else:
        return ET.fromstring(content)
