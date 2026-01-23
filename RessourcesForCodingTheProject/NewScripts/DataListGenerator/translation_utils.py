"""
Translation Utilities for FactionListGenerator
================================================
Provides functions to load and use LOC language data for translation lookups.

Based on patterns from:
- QACompilerNEW/system_localizer.py (LOC loading)
- LanguageDataExporter/exporter/xml_parser.py (XML parsing)
"""

import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Try lxml first (more robust), fallback to standard library
try:
    from lxml import etree as ET
    USING_LXML = True
except ImportError:
    from xml.etree import ElementTree as ET
    USING_LXML = False

logger = logging.getLogger(__name__)


# =============================================================================
# XML SANITIZATION (from QACompiler - battle-tested)
# =============================================================================

_bad_entity_re = re.compile(r'&(?!lt;|gt;|amp;|apos;|quot;)')


def _fix_bad_entities(txt: str) -> str:
    """Fix unescaped ampersands."""
    return _bad_entity_re.sub("&amp;", txt)


def _preprocess_newlines(raw: str) -> str:
    """Handle newlines in seg elements."""
    def repl(m: re.Match) -> str:
        inner = m.group(1).replace("\n", "&lt;br/&gt;").replace("\r\n", "&lt;br/&gt;")
        return f"<seg>{inner}</seg>"
    return re.sub(r"<seg>(.*?)</seg>", repl, raw, flags=re.DOTALL)


def sanitize_xml_content(raw: str) -> str:
    """
    Sanitize XML content to handle common issues.

    Uses QACompiler's battle-tested sanitization:
    - Fix unescaped ampersands
    - Handle newlines in segments
    - Fix < and & in attribute values
    - Remove invalid control characters
    """
    # Remove invalid XML characters (control chars except tab, newline, carriage return)
    raw = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', raw)

    # Fix entities
    raw = _fix_bad_entities(raw)
    raw = _preprocess_newlines(raw)

    # Fix < and & in attribute values
    raw = re.sub(r'="([^"]*<[^"]*)"',
                 lambda m: '="' + m.group(1).replace("<", "&lt;") + '"', raw)
    raw = re.sub(r'="([^"]*&[^ltgapoqu][^"]*)"',
                 lambda m: '="' + m.group(1).replace("&", "&amp;") + '"', raw)

    return raw


# =============================================================================
# LANGUAGE FILE DISCOVERY
# =============================================================================

def discover_language_files(loc_folder: Path) -> Dict[str, Path]:
    """
    Find all languagedata_*.xml files in the LOC folder.

    Args:
        loc_folder: Path to the LOC folder containing languagedata_*.xml files

    Returns:
        Dictionary mapping language code to file path:
        {"eng": Path(...), "fre": Path(...), "zho-cn": Path(...)}
    """
    if not loc_folder.exists():
        logger.error(f"LOC folder not found: {loc_folder}")
        return {}

    lang_files = {}

    # Pattern: languagedata_XXX.xml or languagedata_XXX-YY.xml
    for xml_file in loc_folder.glob("languagedata_*.xml"):
        # Extract language code from filename
        # languagedata_eng.xml -> eng
        # languagedata_zho-cn.xml -> zho-cn
        match = re.match(r'languagedata_(.+)\.xml', xml_file.name, re.IGNORECASE)
        if match:
            lang_code = match.group(1).lower()
            lang_files[lang_code] = xml_file
            logger.debug(f"Found language file: {lang_code} -> {xml_file}")

    logger.info(f"Discovered {len(lang_files)} language files in {loc_folder}")
    return lang_files


# =============================================================================
# LANGUAGE TABLE LOADING
# =============================================================================

def load_language_table(xml_path: Path) -> Dict[str, str]:
    """
    Load StrOrigin -> Str mapping from a single language file.

    Args:
        xml_path: Path to a languagedata_*.xml file

    Returns:
        Dictionary mapping Korean (StrOrigin) to translated text (Str):
        {"몬스터": "Monster", "검": "Sword", ...}
    """
    if not xml_path.exists():
        logger.error(f"Language file not found: {xml_path}")
        return {}

    try:
        # Read and sanitize content
        content = xml_path.read_text(encoding='utf-8')
        content = sanitize_xml_content(content)

        # Parse XML
        if USING_LXML:
            wrapped = f"<ROOT>\n{content}\n</ROOT>"
            try:
                root = ET.fromstring(
                    wrapped.encode("utf-8"),
                    parser=ET.XMLParser(huge_tree=True)
                )
            except ET.XMLSyntaxError:
                root = ET.fromstring(
                    wrapped.encode("utf-8"),
                    parser=ET.XMLParser(recover=True, huge_tree=True)
                )
        else:
            root = ET.fromstring(content)

        table: Dict[str, str] = {}

        # Find all LocStr elements
        for loc_str in root.iter('LocStr'):
            str_origin = loc_str.get('StrOrigin') or ''
            str_value = loc_str.get('Str') or ''

            if str_origin and str_value:
                table[str_origin] = str_value

        logger.info(f"Loaded {len(table)} entries from {xml_path.name}")
        return table

    except Exception as e:
        logger.error(f"Error loading {xml_path}: {e}")
        return {}


def load_all_language_tables(
    loc_folder: Path,
    progress_callback=None
) -> Dict[str, Dict[str, str]]:
    """
    Load translation tables for ALL languages.

    Args:
        loc_folder: Path to LOC folder
        progress_callback: Optional callback(current, total, message)

    Returns:
        Dictionary of dictionaries:
        {
            "eng": {"몬스터": "Monster", "검": "Sword", ...},
            "fre": {"몬스터": "Monstre", "검": "Épée", ...},
            ...
        }
    """
    lang_files = discover_language_files(loc_folder)

    if not lang_files:
        logger.error("No language files found!")
        return {}

    all_tables: Dict[str, Dict[str, str]] = {}
    total = len(lang_files)

    for idx, (lang_code, xml_path) in enumerate(lang_files.items()):
        if progress_callback:
            progress_callback(idx + 1, total, f"Loading {lang_code.upper()}...")

        table = load_language_table(xml_path)
        if table:
            all_tables[lang_code] = table

    logger.info(f"Loaded {len(all_tables)} language tables")
    return all_tables


# =============================================================================
# TRANSLATION FUNCTIONS
# =============================================================================

def translate_list(
    korean_items: List[str],
    lang_table: Dict[str, str]
) -> List[Tuple[str, str]]:
    """
    Translate a list of Korean strings using the provided language table.

    Args:
        korean_items: List of Korean strings to translate
        lang_table: {korean_text: translated_text} mapping

    Returns:
        List of (source, target) tuples:
        [("몬스터", "Monster"), ("검", "Sword"), ...]

        If translation not found, target will be "NO_TRANSLATION"
    """
    results: List[Tuple[str, str]] = []

    for korean in korean_items:
        korean_clean = korean.strip() if korean else ""

        if not korean_clean:
            continue

        # Look up translation
        translation = lang_table.get(korean_clean)

        if translation:
            results.append((korean_clean, translation))
        else:
            results.append((korean_clean, "NO_TRANSLATION"))

    return results


def get_translation_stats(
    korean_items: List[str],
    lang_table: Dict[str, str]
) -> Dict[str, int]:
    """
    Get translation statistics for a list of items.

    Args:
        korean_items: List of Korean strings
        lang_table: Translation table

    Returns:
        {
            "total": 100,
            "translated": 85,
            "missing": 15,
            "percent": 85.0
        }
    """
    total = 0
    translated = 0

    for korean in korean_items:
        korean_clean = korean.strip() if korean else ""
        if not korean_clean:
            continue

        total += 1
        if korean_clean in lang_table:
            translated += 1

    missing = total - translated
    percent = (translated / total * 100) if total > 0 else 0.0

    return {
        "total": total,
        "translated": translated,
        "missing": missing,
        "percent": round(percent, 1)
    }
