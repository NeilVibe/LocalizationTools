"""
XML Parsing Utilities for DataListGenerator
============================================
Provides XML sanitization and parsing functions.
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


def sanitize_xml(raw: str) -> str:
    """Remove illegal XML characters that can cause parse errors."""
    return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', raw)


def parse_xml_file(path: Path) -> Optional[ET._Element]:
    """Parse XML file, return root element or None on error.

    Wraps content in a ROOT element to handle multiple top-level elements.
    """
    try:
        raw = path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"  Error reading {path.name}: {e}")
        return None

    cleaned = sanitize_xml(raw)
    wrapped = f"<ROOT>\n{cleaned}\n</ROOT>"

    try:
        if USING_LXML:
            parser = ET.XMLParser(huge_tree=True, recover=True)
            return ET.fromstring(wrapped.encode("utf-8"), parser=parser)
        else:
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
