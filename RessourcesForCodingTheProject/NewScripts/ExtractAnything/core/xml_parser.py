"""Centralised XML sanitisation, parsing, attribute helpers, and write-back."""

import logging
import os
import re
import stat
from pathlib import Path
from typing import List, Optional

try:
    from lxml import etree

    USING_LXML = True
except ImportError:
    from xml.etree import ElementTree as etree  # type: ignore[no-redef]

    USING_LXML = False

from .. import config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Sanitisation regexes (preserves <br/> tags)
# ---------------------------------------------------------------------------
_CONTROL_CHARS_RE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')
_BAD_AMP = re.compile(r"&(?!(?:amp|lt|gt|apos|quot|#\d+|#x[0-9a-fA-F]+);)")
_ATTR_WITH_LT = re.compile(r'="([^"]*<[^"]*)"')
_ATTR_DANGEROUS_LT = re.compile(r"<(?![bB][rR]\s*/?>)")

# Tag stack repair patterns
_TAG_OPEN = re.compile(r"<([A-Za-z0-9_]+)(\s[^>]*)?>")
_TAG_CLOSE = re.compile(r"</([A-Za-z0-9_]+)>")

# Seg newline preprocessing
_SEG_RE = re.compile(r"<seg>(.*?)</seg>", re.DOTALL)


def _escape_attr_lt(m: re.Match) -> str:
    content = _ATTR_DANGEROUS_LT.sub("&lt;", m.group(1))
    return '="' + content + '"'


def _preprocess_newlines(raw: str) -> str:
    """Convert real newlines inside ``<seg>`` elements to ``&lt;br/&gt;``."""
    def _repl(m: re.Match) -> str:
        inner = m.group(1).replace("\r\n", "&lt;br/&gt;").replace("\n", "&lt;br/&gt;")
        return f"<seg>{inner}</seg>"
    return _SEG_RE.sub(_repl, raw)


def _repair_tag_stack(raw: str) -> str:
    """Repair malformed XML tag structure.

    Handles mismatched closing tags, empty ``</>`` closers,
    and unclosed tags at EOF.
    """
    stack: List[str] = []
    out: List[str] = []

    for line in raw.splitlines():
        stripped = line.strip()

        mo = _TAG_OPEN.match(stripped)
        if mo:
            stack.append(mo.group(1))
            out.append(line)
            continue

        mc = _TAG_CLOSE.match(stripped)
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


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def sanitize_xml(raw: str) -> str:
    """Fix common XML issues while preserving ``<br/>`` tags.

    Pipeline (ported from QuickTranslate):
    1. Strip control characters
    2. Preprocess newlines inside ``<seg>`` elements
    3. Fix unescaped ``&`` entities
    4. Escape bare ``<`` in attribute values (preserving ``<br/>``)
    5. Repair malformed tag structure
    """
    # Step 1: Strip control characters (NUL, BEL, BS, etc.)
    raw = _CONTROL_CHARS_RE.sub('', raw)

    # Step 2: Fix unescaped ampersands (before newline preprocessing — matches QT order)
    raw = _BAD_AMP.sub("&amp;", raw)

    # Step 3: Convert real newlines in <seg> to &lt;br/&gt;
    raw = _preprocess_newlines(raw)

    # Step 4: Escape bare < in attribute values (preserve <br/>)
    raw = _ATTR_WITH_LT.sub(_escape_attr_lt, raw)

    # Step 5: Repair tag stack (mismatched/unclosed tags, </>)
    raw = _repair_tag_stack(raw)

    return raw


def read_xml_raw(xml_path: Path) -> Optional[str]:
    """Read XML file as text with 3-step encoding fallback."""
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return xml_path.read_text(encoding=enc)
        except (UnicodeDecodeError, ValueError):
            continue
    logger.warning("Cannot decode %s", xml_path)
    return None


def parse_root_from_string(raw: str):
    """Parse sanitised raw XML string -> root element (languagedata files)."""
    clean = sanitize_xml(raw)
    if USING_LXML:
        parser = etree.XMLParser(
            resolve_entities=False, load_dtd=False,
            no_network=True, recover=True, huge_tree=True,
        )
        root = etree.fromstring(clean.encode("utf-8"), parser)
    else:
        root = etree.fromstring(clean)
    return root


def parse_root_from_file(xml_path: Path):
    """Parse export .loc.xml directly from file (no sanitisation)."""
    if USING_LXML:
        parser = etree.XMLParser(
            resolve_entities=False, load_dtd=False,
            no_network=True, recover=True, huge_tree=True,
        )
        tree = etree.parse(str(xml_path), parser)
    else:
        tree = etree.parse(str(xml_path))
    return tree.getroot()


def parse_tree_from_string(raw: str):
    """Parse sanitised raw XML -> (tree, root) for in-place modification."""
    import io

    clean = sanitize_xml(raw)
    if USING_LXML:
        parser = etree.XMLParser(
            resolve_entities=False, load_dtd=False,
            no_network=True, recover=True, huge_tree=True,
        )
        tree = etree.parse(io.BytesIO(clean.encode("utf-8")), parser)
    else:
        tree = etree.parse(io.StringIO(clean))
    return tree, tree.getroot()


def parse_tree_from_file(xml_path: Path):
    """Parse export/target XML directly -> (tree, root) for in-place modification."""
    if USING_LXML:
        parser = etree.XMLParser(
            resolve_entities=False, load_dtd=False,
            no_network=True, recover=True, huge_tree=True,
        )
        tree = etree.parse(str(xml_path), parser)
    else:
        tree = etree.parse(str(xml_path))
    return tree, tree.getroot()


def iter_locstr(root) -> list:
    """Return all LocStr elements from *root* (any tag-case variant)."""
    elements = []
    for tag in config.LOCSTR_TAGS:
        elements.extend(root.iter(tag))
    return elements


def get_attr(elem, variants: tuple) -> tuple[Optional[str], Optional[str]]:
    """Return (attr_name, value) from *elem* for the first matching variant."""
    for name in variants:
        val = elem.get(name)
        if val is not None:
            return name, val
    return None, None


def get_attr_value(attrs: dict, variants: tuple) -> str:
    """Return value from *attrs* dict for the first matching variant, or ''."""
    for name in variants:
        val = attrs.get(name)
        if val is not None:
            return val
    return ""


def write_xml_tree(tree, xml_path: Path) -> None:
    """Write an lxml/stdlib tree back to disk (no XML declaration).

    Handles read-only files by temporarily adding the write permission.
    """
    try:
        current_mode = os.stat(xml_path).st_mode
        if not current_mode & stat.S_IWRITE:
            os.chmod(xml_path, current_mode | stat.S_IWRITE)
            logger.debug("Made %s writable", xml_path.name)
    except Exception as exc:
        logger.warning("Could not check/set write permission on %s: %s", xml_path.name, exc)

    if USING_LXML:
        tree.write(
            str(xml_path), encoding="utf-8",
            xml_declaration=False, pretty_print=True,
        )
    else:
        tree.write(str(xml_path), encoding="utf-8", xml_declaration=False)
