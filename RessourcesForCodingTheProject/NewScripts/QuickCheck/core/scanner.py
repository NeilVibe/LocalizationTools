"""
Language Scanner

Auto-detects language codes from folder/file structure.
Adapted from QuickTranslate/core/source_scanner.py — stripped to scan-only,
no transfer logic, uses hard-coded VALID_CODES from config.

Patterns supported:
  - FRE/              -> all XML files inside -> FRE
  - corrections_FRE/  -> all XML files inside -> FRE
  - patch_GER.xml     -> GER
  - languagedata_jpn.xml -> JPN
  - ZHO-CN/           -> ZHO-CN (hyphenated codes)

No substring matching: LaLaFRElala does NOT match.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import config

logger = logging.getLogger(__name__)


@dataclass
class ScanResult:
    """Result of scanning a folder for language-tagged files."""
    lang_files: Dict[str, List[Path]] = field(default_factory=dict)
    unrecognized: List[Path] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def total_files(self) -> int:
        return sum(len(files) for files in self.lang_files.values())

    @property
    def language_count(self) -> int:
        return len(self.lang_files)

    def get_languages(self) -> List[str]:
        return sorted(self.lang_files.keys())


def extract_language_suffix(name: str, valid_codes: set) -> Optional[str]:
    """
    Extract language code from a folder or file name (stem).

    Patterns supported:
    - FRE               -> FRE (standalone code, entire name)
    - ZHO-CN            -> ZHO-CN (standalone hyphenated code)
    - name_ZHO-CN       -> ZHO-CN (underscore + hyphenated)
    - name_FRE          -> FRE (underscore-prefixed)
    - languagedata_ger  -> GER (case-insensitive)

    NOT matched:
    - LaLaFRElala       -> None (code embedded, no boundary)

    Args:
        name: Folder name or file stem (without extension)
        valid_codes: Set of valid language codes (uppercase)

    Returns:
        Uppercase language code if found, None otherwise
    """
    if not name:
        return None

    # Strip extension if accidentally included
    if "." in name:
        name = Path(name).stem

    parts = name.split("_")

    # Standalone code: entire name is a valid code (e.g. "FRE", "ZHO-CN")
    if len(parts) == 1:
        upper = name.upper()
        if upper in valid_codes:
            return upper
        return None

    # Underscore-separated: check last part(s) for language code
    # Try hyphenated codes first (ZHO-CN, ZHO-TW): join last two parts with hyphen
    if len(parts) >= 2:
        hyphenated = f"{parts[-2]}-{parts[-1]}".upper()
        if hyphenated in valid_codes:
            return hyphenated

    # Try single last part (FRE, GER, JPN, etc.)
    suffix = parts[-1].upper()
    if suffix in valid_codes:
        return suffix

    return None


def scan_folder_for_languages(root: Path) -> ScanResult:
    """
    Scan a folder for language-tagged files/subfolders.

    Detection rules:
    1. Subfolder named as language code or with suffix (e.g., FRE/, corrections_FRE/):
       - ALL .xml files inside (recursive) are assigned to that language
    2. Direct .xml file with language name/suffix (e.g., patch_GER.xml):
       - That file is assigned to that language
    3. languagedata_XXX.xml pattern:
       - Standard language data file pattern (case-insensitive)

    Args:
        root: Path to folder to scan

    Returns:
        ScanResult with {lang_code: [list_of_xml_files]}
    """
    result = ScanResult()
    valid_codes = config.VALID_CODES

    if not root.exists():
        result.warnings.append(f"Folder does not exist: {root}")
        return result

    # Supported input file extensions
    LANG_EXTS = (".xml", ".xlsx")

    if not root.is_dir():
        # Single file mode
        if root.suffix.lower() in LANG_EXTS:
            lang = extract_language_suffix(root.stem, valid_codes)
            if lang:
                result.lang_files[lang] = [root]
            else:
                result.unrecognized.append(root)
        return result

    try:
        children = sorted(root.iterdir())
    except OSError as e:
        result.warnings.append(f"Cannot read folder: {e}")
        return result

    for child in children:
        if child.is_dir():
            lang = extract_language_suffix(child.name, valid_codes)
            if lang:
                # Collect ALL supported files inside (recursive) for this language
                lang_files = sorted(
                    f for f in child.rglob("*")
                    if f.is_file() and f.suffix.lower() in LANG_EXTS
                )
                if lang_files:
                    result.lang_files.setdefault(lang, []).extend(lang_files)
                    logger.debug(f"Folder {child.name}: {len(lang_files)} files -> {lang}")
                else:
                    result.warnings.append(
                        f"Folder '{child.name}' detected as {lang} but contains no supported files"
                    )
            else:
                result.unrecognized.append(child)

        elif child.is_file() and child.suffix.lower() in LANG_EXTS:
            lang = extract_language_suffix(child.stem, valid_codes)

            if lang:
                result.lang_files.setdefault(lang, []).append(child)
                logger.debug(f"File {child.name} -> {lang}")
            else:
                result.unrecognized.append(child)

    return result
