"""
XML Parser Solution
===================
Parses any XML file, even broken/malformed ones.

Install: pip install lxml
"""

import re
from pathlib import Path
from lxml import etree


def parse_xml_safe(filepath):
    """
    Parse any XML file, even broken/malformed ones.

    Args:
        filepath: Path to XML file (string or Path)

    Returns:
        Root element of parsed XML
    """
    content = Path(filepath).read_text(encoding='utf-8')

    # Sanitize: remove control chars, fix unescaped &
    content = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', content)
    content = re.sub(r'&(?!lt;|gt;|amp;|apos;|quot;|#)', '&amp;', content)

    # Parse with recovery mode (continues despite errors)
    parser = etree.XMLParser(recover=True)
    return etree.fromstring(content.encode('utf-8'), parser)


# =============================================================================
# USAGE
# =============================================================================

if __name__ == "__main__":
    root = parse_xml_safe("your_file.xml")

    for elem in root.iter("YourTag"):
        print(elem.get("YourAttribute"))
