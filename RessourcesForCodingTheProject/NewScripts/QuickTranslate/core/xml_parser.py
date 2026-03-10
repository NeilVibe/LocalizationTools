"""
XML Sanitization and Parsing.

Battle-tested XML parsing with sanitization from LanguageDataExporter.
Handles common XML issues: bad entities, newlines in seg elements, control chars,
malformed tag structures.
"""

import re
from pathlib import Path
from typing import List

# Try lxml first (more robust), fallback to standard library
try:
    from lxml import etree as ET
    USING_LXML = True
except ImportError:
    from xml.etree import ElementTree as ET
    USING_LXML = False

# Regex for unescaped ampersands (not part of valid XML entities)
_bad_entity_re = re.compile(r'&(?!lt;|gt;|amp;|apos;|quot;|#)')

# Tag patterns for stack repair
_tag_open = re.compile(r"<([A-Za-z0-9_]+)(\s[^>]*)?>")
_tag_close = re.compile(r"</([A-Za-z0-9_]+)>")

# ── Centralized attribute name variants (import these instead of hardcoding) ──
STRINGID_ATTRS = ['StringId', 'StringID', 'stringid', 'STRINGID', 'Stringid', 'stringId']
STRORIGIN_ATTRS = ['StrOrigin', 'Strorigin', 'strorigin', 'STRORIGIN']
STR_ATTRS = ('Str', 'str', 'STR')
DESC_ATTRS = ['Desc', 'desc', 'DESC']
DESCORIGIN_ATTRS = ['DescOrigin', 'Descorigin', 'descorigin', 'DESCORIGIN']
LOCSTR_TAGS = ['LocStr', 'locstr', 'LOCSTR', 'LOCStr', 'Locstr']


def _fix_bad_entities(txt: str) -> str:
    """Fix unescaped ampersands by converting them to &amp;."""
    return _bad_entity_re.sub("&amp;", txt)


def _preprocess_newlines(raw: str) -> str:
    """Handle newlines in seg elements by converting to &lt;br/&gt;."""
    def repl(m: re.Match) -> str:
        # IMPORTANT: Replace \r\n BEFORE \n (otherwise \r\n becomes \r&lt;br/&gt;)
        inner = m.group(1).replace("\r\n", "&lt;br/&gt;").replace("\n", "&lt;br/&gt;")
        return f"<seg>{inner}</seg>"
    return re.sub(r"<seg>(.*?)</seg>", repl, raw, flags=re.DOTALL)


def _repair_tag_stack(raw: str) -> str:
    """
    Repair malformed XML tag structure.

    Handles:
    - Mismatched closing tags
    - Empty closing tags (</>)
    - Unclosed tags at end of file

    Ported from LanguageDataExporter's battle-tested implementation.
    """
    stack: List[str] = []
    out: List[str] = []

    for line in raw.splitlines():
        stripped = line.strip()

        # Check for opening tag
        mo = _tag_open.match(stripped)
        if mo:
            stack.append(mo.group(1))
            out.append(line)
            continue

        # Check for closing tag
        mc = _tag_close.match(stripped)
        if mc:
            if stack and stack[-1] == mc.group(1):
                stack.pop()
                out.append(line)
            else:
                # Mismatched closing tag - try to fix
                out.append(stack and f"</{stack.pop()}>" or line)
            continue

        # Check for empty closing tag (</>)
        if stripped.startswith("</>"):
            out.append(stack and line.replace("</>", f"</{stack.pop()}>") or line)
            continue

        out.append(line)

    # Close any unclosed tags at end
    while stack:
        out.append(f"</{stack.pop()}>")

    return "\n".join(out)


def sanitize_xml_content(raw: str) -> str:
    """
    Sanitize XML content to handle common issues.

    Handles:
    - Control characters (removes)
    - Unescaped ampersands
    - Newlines in seg elements
    - Unescaped < and & in attribute values
    - Malformed tag structures (mismatched, unclosed tags)
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

    # Repair malformed tag structure
    raw = _repair_tag_stack(raw)

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


import logging

_logger = logging.getLogger(__name__)


# ─── XML Load Test ────────────────────────────────────────────────────────────


def validate_xml_load(xml_path: Path) -> dict:
    """
    Industrial-grade XML load test. Verifies a file can be read, parsed, and
    contains valid LocStr data.

    Runs 4 checks in order:
      1. File readable (encoding, permissions, exists)
      2. Strict XML parse (no recovery — catches real corruption)
      3. Recovery XML parse (lxml recover=True — last resort)
      4. LocStr element presence (file has actual game data)

    Returns:
        {
            "ok": bool,              # True = file is healthy
            "file": str,             # Filename
            "file_size": int,        # Bytes
            "encoding_ok": bool,     # UTF-8 readable
            "strict_parse_ok": bool, # Parsed without recovery
            "recovery_parse_ok": bool,  # Parsed with recovery (only if strict fails)
            "locstr_count": int,     # Number of LocStr elements found
            "error": str | None,     # Human-readable error if not ok
            "stage": str,            # Which stage failed: "read", "strict_parse", "recovery_parse", "locstr", "ok"
        }
    """
    result = {
        "ok": False,
        "file": xml_path.name,
        "file_size": 0,
        "encoding_ok": False,
        "strict_parse_ok": False,
        "recovery_parse_ok": False,
        "locstr_count": 0,
        "error": None,
        "stage": "read",
    }

    # ── Stage 1: File readable ────────────────────────────────────────────
    try:
        raw = xml_path.read_text(encoding='utf-8')
        result["file_size"] = xml_path.stat().st_size
        result["encoding_ok"] = True
    except FileNotFoundError:
        result["error"] = f"File not found: {xml_path}"
        _logger.error(f"XML LOAD FAIL [{xml_path.name}]: file not found")
        return result
    except PermissionError:
        result["error"] = f"Permission denied: {xml_path}"
        _logger.error(f"XML LOAD FAIL [{xml_path.name}]: permission denied")
        return result
    except UnicodeDecodeError as e:
        result["error"] = f"Encoding error (not valid UTF-8): {e}"
        _logger.error(f"XML LOAD FAIL [{xml_path.name}]: encoding error — {e}")
        return result
    except Exception as e:
        result["error"] = f"Read error: {e}"
        _logger.error(f"XML LOAD FAIL [{xml_path.name}]: read error — {e}")
        return result

    # Empty file check
    if not raw.strip():
        result["error"] = "File is empty (0 bytes of content)"
        _logger.error(f"XML LOAD FAIL [{xml_path.name}]: file is empty")
        return result

    # ── Stage 2: Strict XML parse (no recovery, no sanitization) ────────
    result["stage"] = "strict_parse"

    if USING_LXML:
        # Try direct parse first — this is how a healthy XML file should load
        try:
            parser = ET.XMLParser(
                resolve_entities=False, load_dtd=False,
                no_network=True, huge_tree=True,
            )
            tree = ET.parse(str(xml_path), parser)
            root = tree.getroot()
            result["strict_parse_ok"] = True
        except (ET.XMLSyntaxError, Exception) as e:
            _logger.warning(
                f"XML LOAD WARN [{xml_path.name}]: strict parse failed — {e}. "
                f"Trying recovery mode..."
            )
            # ── Stage 3: Recovery parse (lxml recover=True) ───────────────
            result["stage"] = "recovery_parse"
            try:
                recovery_parser = ET.XMLParser(
                    resolve_entities=False, load_dtd=False,
                    no_network=True, recover=True, huge_tree=True,
                )
                tree = ET.parse(str(xml_path), recovery_parser)
                root = tree.getroot()
                result["recovery_parse_ok"] = True
                _logger.warning(
                    f"XML LOAD WARN [{xml_path.name}]: recovered with lxml recover=True. "
                    f"File has structural issues but is usable."
                )
            except Exception as e2:
                result["error"] = f"XML parse failed (even with recovery): {e2}"
                _logger.error(
                    f"XML LOAD FAIL [{xml_path.name}]: parse failed even with recovery — {e2}"
                )
                return result
    else:
        try:
            tree = ET.parse(str(xml_path))
            root = tree.getroot()
            result["strict_parse_ok"] = True
        except Exception as e:
            result["error"] = f"XML parse failed: {e}"
            _logger.error(f"XML LOAD FAIL [{xml_path.name}]: parse failed — {e}")
            return result

    # ── Stage 4: LocStr element check ─────────────────────────────────────
    result["stage"] = "locstr"
    locstr_elements = iter_locstr_elements(root)
    result["locstr_count"] = len(locstr_elements)

    if result["locstr_count"] == 0:
        result["error"] = "No LocStr elements found (file has no game data)"
        _logger.warning(f"XML LOAD WARN [{xml_path.name}]: no LocStr elements found")
        # This is a warning, not a hard failure — file parses fine, just no data
        result["ok"] = True  # Parseable, just empty
        result["stage"] = "ok"
        return result

    # ── All clear ─────────────────────────────────────────────────────────
    result["ok"] = True
    result["stage"] = "ok"
    if result["recovery_parse_ok"] and not result["strict_parse_ok"]:
        result["error"] = "File parsed only with recovery mode (has structural issues)"
    return result


def validate_xml_folder(folder_path: Path, log_callback=None) -> dict:
    """
    Run XML load test on all .xml files in a folder (recursive).

    Args:
        folder_path: Folder to scan
        log_callback: Optional callback(msg, level) for GUI logging

    Returns:
        {
            "total": int,
            "passed": int,
            "failed": int,
            "recovered": int,     # Parsed only with recovery mode
            "empty": int,         # Parsed but no LocStr elements
            "failures": [result_dict, ...],
            "recovered_files": [result_dict, ...],
        }
    """
    xml_files = sorted(folder_path.rglob("*.xml"))
    summary = {
        "total": len(xml_files),
        "passed": 0,
        "failed": 0,
        "recovered": 0,
        "empty": 0,
        "failures": [],
        "recovered_files": [],
    }

    for xml_path in xml_files:
        result = validate_xml_load(xml_path)

        if not result["ok"]:
            summary["failed"] += 1
            summary["failures"].append(result)
            if log_callback:
                log_callback(f"FAIL: {result['file']} — {result['error']}", 'error')
        elif result.get("recovery_parse_ok") and not result.get("strict_parse_ok"):
            summary["recovered"] += 1
            summary["recovered_files"].append(result)
            summary["passed"] += 1
            if log_callback:
                log_callback(f"WARN: {result['file']} — parsed with recovery only", 'warning')
        elif result["locstr_count"] == 0:
            summary["empty"] += 1
            summary["passed"] += 1
        else:
            summary["passed"] += 1

    # Summary log
    if summary["failed"] > 0:
        _logger.error(
            f"XML Load Test: {summary['failed']}/{summary['total']} files FAILED"
        )
    if summary["recovered"] > 0:
        _logger.warning(
            f"XML Load Test: {summary['recovered']}/{summary['total']} files needed recovery mode"
        )
    if summary["failed"] == 0 and summary["recovered"] == 0:
        _logger.info(
            f"XML Load Test: {summary['total']}/{summary['total']} files OK "
            f"({summary['empty']} empty, {summary['total'] - summary['empty']} with data)"
        )

    return summary


def get_attr(elem, attr_names: list) -> str:
    """Get attribute value trying multiple case variations. Returns '' if not found."""
    for name in attr_names:
        val = elem.get(name)
        if val is not None:
            return val
    return ''


def iter_locstr_elements(root: ET.Element) -> List:
    """
    Iterate over LocStr elements with case-insensitive tag matching.

    Tries: 'LocStr', 'locstr', 'LOCSTR' in order.

    Args:
        root: Root element to search

    Returns:
        List of LocStr elements found
    """
    elements = []
    for tag in LOCSTR_TAGS:
        elements.extend(root.iter(tag))
    return elements
