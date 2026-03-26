"""
MegaIndex Helpers - Constants and utility functions shared across mixin modules.

Extracted from mega_index.py during ARCH-02 decomposition.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, List, Optional, Tuple

from loguru import logger
from lxml import etree


# =============================================================================
# Constants
# =============================================================================

# Case-insensitive StringId attribute extraction (from STRINGID_AUDIO_CHAIN.md)
STRINGID_ATTRS = ["StringId", "StringID", "stringid"]

# StrOrigin normalization patterns (from QACompiler base.py)
_BR_TAG_RE = re.compile(r"<br\s*/?>", flags=re.IGNORECASE)
_PLACEHOLDER_SUFFIX_RE = re.compile(r"\{([^#}]+)#[^}]+\}")
_WHITESPACE_RE = re.compile(r"\s+", flags=re.UNICODE)

# Entity type -> dict attribute mapping for generic access
_ENTITY_TYPE_MAP = {
    "knowledge": "knowledge_by_strkey",
    "character": "character_by_strkey",
    "item": "item_by_strkey",
    "region": "region_by_strkey",
    "faction": "faction_by_strkey",
    "faction_group": "faction_group_by_strkey",
    "skill": "skill_by_strkey",
    "gimmick": "gimmick_by_strkey",
}


# =============================================================================
# Helpers
# =============================================================================


def _get_stringid(elem: Any) -> str:
    """Extract StringId from XML element with case-insensitive attr matching."""
    for attr in STRINGID_ATTRS:
        val = elem.get(attr)
        if val:
            return val
    return ""


def _normalize_strorigin(text: str) -> str:
    """Normalize StrOrigin for reverse lookup: strip # suffixes, br->space, collapse ws."""
    if not text:
        return ""
    text = _PLACEHOLDER_SUFFIX_RE.sub(r"{\1}", text)
    text = _BR_TAG_RE.sub(" ", text)
    text = _WHITESPACE_RE.sub(" ", text).strip()
    return text


def _get_export_key(filename: str) -> str:
    """Convert data filename to export lookup key (normalized stem)."""
    return filename.lower().replace(".xml", "").replace(".loc", "")


def _safe_parse_xml(xml_path: Path) -> Optional[Any]:
    """Parse XML file with error handling. Returns root element or None."""
    try:
        tree = etree.parse(str(xml_path))
        return tree.getroot()
    except etree.XMLSyntaxError:
        try:
            tree = etree.parse(
                str(xml_path), parser=etree.XMLParser(recover=True, huge_tree=True)
            )
            return tree.getroot()
        except Exception:
            logger.warning(f"[MEGAINDEX] Failed to parse XML: {xml_path}")
            return None
    except Exception as e:
        logger.warning(f"[MEGAINDEX] Error reading {xml_path}: {e}")
        return None


def _parse_world_position(wp_str: str) -> Optional[Tuple[float, float, float]]:
    """Parse WorldPosition string to (x, y, z) tuple."""
    if not wp_str:
        return None
    try:
        parts = wp_str.strip("()").split(",")
        if len(parts) == 3:
            return (
                float(parts[0].strip()),
                float(parts[1].strip()),
                float(parts[2].strip()),
            )
    except (ValueError, IndexError):
        pass
    return None


def _find_knowledge_key(elem: Any) -> str:
    """Search element and direct children for KnowledgeKey or RewardKnowledgeKey."""
    for attr in ("KnowledgeKey", "RewardKnowledgeKey"):
        val = elem.get(attr) or ""
        if val:
            return val
    for child in elem:
        if child.tag in ("InspectData", "PageData"):
            continue
        for attr in ("KnowledgeKey", "RewardKnowledgeKey"):
            val = child.get(attr) or ""
            if val:
                return val
    return ""
