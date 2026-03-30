"""
MegaIndex Helpers - Constants and utility functions shared across mixin modules.

Extracted from mega_index.py during ARCH-02 decomposition.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, List, Optional, Tuple

from loguru import logger


# =============================================================================
# Constants
# =============================================================================

# StrOrigin normalization patterns (from QACompiler base.py)
_BR_TAG_RE = re.compile(r"<br\s*/?>", flags=re.IGNORECASE)
_PLACEHOLDER_SUFFIX_RE = re.compile(r"\{([^#}]+)#[^}]+\}")
_WHITESPACE_RE = re.compile(r"\s+", flags=re.UNICODE)

# MDG config.py:192-201 — Language-to-audio-folder routing
# Latin-script languages -> English(US) audio
# Korean/Japanese/ZHO-TW -> Korean audio
# ZHO-CN -> Chinese(PRC) audio
LANG_TO_AUDIO = {
    "eng": "en", "fre": "en", "ger": "en", "spa-es": "en", "spa-mx": "en",
    "por-br": "en", "ita": "en", "rus": "en", "tur": "en", "pol": "en",
    "kor": "kr", "jpn": "kr", "zho-tw": "kr",
    "zho-cn": "zh",
}

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
    """Extract StringId from XML element — case-insensitive attrs AND value."""
    attrs = {k.lower(): v for k, v in elem.attrib.items()}
    val = attrs.get("stringid") or ""
    return val.strip().lower()


def _normalize_strorigin(text: str) -> str:
    """Normalize StrOrigin for reverse lookup: strip # suffixes, br->space, collapse ws, lowercase."""
    if not text:
        return ""
    text = _PLACEHOLDER_SUFFIX_RE.sub(r"{\1}", text)
    text = _BR_TAG_RE.sub(" ", text)
    text = _WHITESPACE_RE.sub(" ", text).strip()
    return text.lower()


def _get_export_key(filename: str) -> str:
    """Convert data filename to export lookup key (normalized stem)."""
    return filename.lower().replace(".xml", "").replace(".loc", "")


def _safe_parse_xml(xml_path: Path) -> Optional[Any]:
    """Parse XML file using the battle-tested sanitizer pipeline.

    Uses sanitize_and_parse() from xml_sanitizer.py which provides:
    - 5-stage sanitization (bad entities, seg newlines, attr escaping, tag repair)
    - Virtual ROOT wrapper for multi-root files
    - Dual-pass parsing (strict first, recovery fallback)
    - Control character removal

    Returns root element (the virtual ROOT wrapper) or None on failure.
    """
    try:
        from server.tools.ldm.services.xml_sanitizer import sanitize_and_parse

        return sanitize_and_parse(xml_path)
    except Exception as e:
        logger.warning(f"[MEGAINDEX] Error parsing {xml_path}: {e}")
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
    """Search element and children for KnowledgeKey — case-insensitive attrs AND value."""
    attrs = {k.lower(): v for k, v in elem.attrib.items()}
    val = attrs.get("knowledgekey") or attrs.get("rewardknowledgekey") or ""
    if val:
        return val.strip().lower()
    for child in elem:
        if child.tag in ("InspectData", "PageData"):
            continue
        cattrs = {k.lower(): v for k, v in child.attrib.items()}
        val = cattrs.get("knowledgekey") or cattrs.get("rewardknowledgekey") or ""
        if val:
            return val.strip().lower()
    return ""
