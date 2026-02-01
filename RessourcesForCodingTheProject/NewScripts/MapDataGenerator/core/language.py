"""
Language Module

Multi-language LOC (localization) support for 13 languages.
Handles loading language tables from LanguageData_*.xml files.
"""

import logging
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Ensure parent directory is in sys.path for PyInstaller compatibility
sys.path.insert(0, str(Path(__file__).parent.parent))

from .xml_parser import parse_xml, iter_xml_files
from utils.filters import normalize_placeholders, is_good_translation

log = logging.getLogger(__name__)


# =============================================================================
# LANGUAGE TABLE TYPE
# =============================================================================

# Type alias for language table
# {normalized_korean: [(translation, stringid), ...]}
LanguageTable = Dict[str, List[Tuple[str, str]]]

# Type alias for all languages
# {lang_code: LanguageTable}
AllLanguageTables = Dict[str, LanguageTable]


# =============================================================================
# LANGUAGE LOADING
# =============================================================================

def load_language_tables(
    folder: Path,
    progress_callback: Optional[callable] = None
) -> AllLanguageTables:
    """
    Load all non-Korean language tables with normalized placeholder keys.

    Stores ALL translations for each Korean text to support duplicate resolution.
    When the same Korean text appears in multiple files with different context-specific
    translations, we preserve all of them for later disambiguation.

    File pattern: LanguageData_[CODE].xml
    Languages: eng, fre, ger, spa, por, ita, rus, tur, pol, zho-cn, zho-tw, jpn

    Args:
        folder: Path to language data folder
        progress_callback: Optional callback for progress updates

    Returns:
        {lang_code: {normalized_korean: [(translation, stringid), ...]}}

    Note: The list preserves all translations for a given Korean text.
          Good translations (no Korean) are sorted to the front.
    """
    tables: AllLanguageTables = {}
    files_processed = 0

    # Collect all language files
    lang_files = []
    for path in iter_xml_files(folder):
        stem = path.stem.lower()
        if stem.startswith("languagedata_"):
            # Skip Korean file
            if stem.endswith("kor"):
                continue
            lang_files.append(path)

    total_files = len(lang_files)
    log.info("Found %d language files to process", total_files)

    for path in lang_files:
        stem = path.stem.lower()
        # Extract language code: languagedata_eng -> eng
        lang = stem.split("_", 1)[1]

        if progress_callback:
            progress_callback(f"Loading {lang.upper()}... ({files_processed + 1}/{total_files})")

        root_el = parse_xml(path)
        if root_el is None:
            log.warning("Failed to parse %s", path)
            continue

        # Initialize or get existing table for this language
        tbl: LanguageTable = tables.get(lang, {})

        for loc in root_el.iter("LocStr"):
            origin = loc.get("StrOrigin") or ""
            tr = loc.get("Str") or ""
            sid = loc.get("StringId") or ""

            if not origin:
                continue

            normalized_origin = normalize_placeholders(origin)

            # Store ALL translations for this Korean text
            if normalized_origin not in tbl:
                tbl[normalized_origin] = []

            # Add this translation (avoid exact duplicates)
            entry = (tr, sid)
            if entry not in tbl[normalized_origin]:
                tbl[normalized_origin].append(entry)

        # Sort each list: good translations first, then bad ones
        for key in tbl:
            tbl[key].sort(key=lambda x: (0 if is_good_translation(x[0]) else 1))

        tables[lang] = tbl
        files_processed += 1
        log.info("  Loaded %s: %d entries", lang.upper(), len(tbl))

    log.info("Loaded %d language tables", len(tables))
    return tables


def load_single_language(
    folder: Path,
    lang_code: str,
    progress_callback: Optional[callable] = None
) -> LanguageTable:
    """
    Load a single language table.

    Args:
        folder: Path to language data folder
        lang_code: Language code (e.g., 'eng', 'fre')
        progress_callback: Optional callback for progress updates

    Returns:
        {normalized_korean: [(translation, stringid), ...]}
    """
    tbl: LanguageTable = {}

    # Find matching files
    pattern = f"languagedata_{lang_code}.xml"
    files_found = 0

    for path in iter_xml_files(folder):
        if path.stem.lower() == f"languagedata_{lang_code.lower()}":
            files_found += 1

            if progress_callback:
                progress_callback(f"Loading {lang_code.upper()}...")

            root_el = parse_xml(path)
            if root_el is None:
                continue

            for loc in root_el.iter("LocStr"):
                origin = loc.get("StrOrigin") or ""
                tr = loc.get("Str") or ""
                sid = loc.get("StringId") or ""

                if not origin:
                    continue

                normalized_origin = normalize_placeholders(origin)

                if normalized_origin not in tbl:
                    tbl[normalized_origin] = []

                entry = (tr, sid)
                if entry not in tbl[normalized_origin]:
                    tbl[normalized_origin].append(entry)

    # Sort: good translations first
    for key in tbl:
        tbl[key].sort(key=lambda x: (0 if is_good_translation(x[0]) else 1))

    log.info("Loaded %s: %d entries from %d files", lang_code.upper(), len(tbl), files_found)
    return tbl


# =============================================================================
# TRANSLATION LOOKUP
# =============================================================================

def get_translation(
    korean_text: str,
    lang_table: LanguageTable,
    default: str = ""
) -> Tuple[str, str]:
    """
    Get translation for Korean text.

    Returns the first (best) translation from the language table.
    Good translations (no Korean) are returned first.

    Args:
        korean_text: Korean source text
        lang_table: Language table to search
        default: Default value if not found

    Returns:
        (translation, stringid) tuple
    """
    if not korean_text:
        return (default, "")

    normalized = normalize_placeholders(korean_text)
    candidates = lang_table.get(normalized, [])

    if candidates:
        return candidates[0]

    return (default, "")


def get_all_translations(
    korean_text: str,
    lang_table: LanguageTable
) -> List[Tuple[str, str]]:
    """
    Get all translations for Korean text.

    Useful when there are duplicate Korean texts with different translations
    in different contexts.

    Args:
        korean_text: Korean source text
        lang_table: Language table to search

    Returns:
        List of (translation, stringid) tuples
    """
    if not korean_text:
        return []

    normalized = normalize_placeholders(korean_text)
    return lang_table.get(normalized, [])


def get_translation_by_stringid(
    stringid: str,
    lang_table: LanguageTable
) -> Optional[str]:
    """
    Get translation by StringID.

    Searches through all entries to find the one with matching StringID.
    This is slower than Korean text lookup but useful for exact matching.

    Args:
        stringid: StringID to find
        lang_table: Language table to search

    Returns:
        Translation text or None if not found
    """
    if not stringid:
        return None

    for entries in lang_table.values():
        for translation, sid in entries:
            if sid == stringid:
                return translation

    return None


# =============================================================================
# LANGUAGE TABLE MANAGER (WITH LAZY LOADING)
# =============================================================================

class LanguageManager:
    """
    Manages language tables for the application.

    Provides lazy loading - only English and Korean loaded initially.
    Other languages loaded on-demand when first requested.
    """

    # Languages to preload at startup
    PRELOAD_LANGUAGES = ['eng', 'kor']

    def __init__(self, loc_folder: Optional[Path] = None):
        self._loc_folder: Optional[Path] = loc_folder
        self._tables: AllLanguageTables = {}
        self._loaded_languages: set = set()

    def set_folder(self, folder: Path) -> None:
        """Set the localization folder and clear cache."""
        self._loc_folder = folder
        self._tables = {}
        self._loaded_languages = set()

    def preload_essential(self, progress_callback: Optional[callable] = None) -> bool:
        """
        Load only essential languages (English and Korean) for fast startup.

        Args:
            progress_callback: Optional progress callback

        Returns:
            True if successful
        """
        if self._loc_folder is None:
            return False

        success = True
        for lang_code in self.PRELOAD_LANGUAGES:
            if progress_callback:
                lang_name = lang_code.upper()
                if lang_code == 'eng':
                    lang_name = 'English'
                elif lang_code == 'kor':
                    lang_name = 'Korean'
                progress_callback(f"Loading {lang_name}...")

            tbl = load_single_language(self._loc_folder, lang_code, None)
            if tbl:
                self._tables[lang_code.lower()] = tbl
                self._loaded_languages.add(lang_code.lower())
            else:
                success = False

        return success

    def load_all(self, progress_callback: Optional[callable] = None) -> bool:
        """
        Load all language tables (for backward compatibility).

        Args:
            progress_callback: Optional progress callback

        Returns:
            True if successful
        """
        if self._loc_folder is None:
            return False

        self._tables = load_language_tables(self._loc_folder, progress_callback)
        self._loaded_languages = set(self._tables.keys())
        return bool(self._tables)

    def load_language(
        self,
        lang_code: str,
        progress_callback: Optional[callable] = None
    ) -> bool:
        """
        Load a single language table (lazy loading).

        Args:
            lang_code: Language code
            progress_callback: Optional progress callback

        Returns:
            True if successful
        """
        if self._loc_folder is None:
            return False

        # Already loaded?
        if lang_code.lower() in self._loaded_languages:
            return True

        tbl = load_single_language(self._loc_folder, lang_code, progress_callback)
        if tbl:
            self._tables[lang_code.lower()] = tbl
            self._loaded_languages.add(lang_code.lower())
            return True
        return False

    def get_table(self, lang_code: str) -> LanguageTable:
        """
        Get language table for a language code.

        If not loaded yet, will load on-demand (lazy loading).

        Args:
            lang_code: Language code

        Returns:
            Language table (empty dict if not found)
        """
        lang_code_lower = lang_code.lower()

        # Check if already loaded
        if lang_code_lower in self._loaded_languages:
            return self._tables.get(lang_code_lower, {})

        # Lazy load
        if self._loc_folder is not None:
            log.info("Lazy loading language: %s", lang_code)
            self.load_language(lang_code)

        return self._tables.get(lang_code_lower, {})

    def is_language_loaded(self, lang_code: str) -> bool:
        """Check if a specific language is loaded."""
        return lang_code.lower() in self._loaded_languages

    def get_translation(
        self,
        korean_text: str,
        lang_code: str,
        default: str = ""
    ) -> str:
        """
        Get translation for Korean text.

        Args:
            korean_text: Korean source text
            lang_code: Target language code
            default: Default value if not found

        Returns:
            Translation text
        """
        tbl = self.get_table(lang_code)  # This will lazy load if needed
        translation, _ = get_translation(korean_text, tbl, default)
        return translation if translation else default

    @property
    def is_loaded(self) -> bool:
        """Check if essential language tables are loaded."""
        return 'eng' in self._loaded_languages or 'kor' in self._loaded_languages

    @property
    def available_languages(self) -> List[str]:
        """Get list of loaded language codes."""
        return list(self._loaded_languages)
