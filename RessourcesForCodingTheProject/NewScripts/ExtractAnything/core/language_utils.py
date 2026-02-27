"""Language code detection and LOC folder discovery.

Provides suffix-based language detection (like QuickTranslate's source_scanner)
with a cached valid-codes set auto-discovered from the LOC folder.
"""

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

_LANG_SUFFIX_RE = re.compile(
    r"[_-]([a-zA-Z]{2,6}(?:-[a-zA-Z]{2,6})?)(?:\.(?:xml|xlsx?))?$"
)

# Hardcoded fallback codes (common game localization languages)
_FALLBACK_CODES: set[str] = {
    "ENG", "KR", "FRE", "GER", "SPA", "ITA", "RUS", "POR", "JPN",
    "CHI", "ZHO", "ZH-CN", "ZH-TW", "ZHO-CN", "ZHO-TW", "POL",
    "TUR", "ARA", "THA", "VIE", "IND", "CZE", "DUT", "RUM", "HUN",
    "UKR", "BRA",
}

# Module-level cache
_cached_valid_codes: set[str] | None = None
_cached_loc_folder: Path | None = None


def discover_valid_codes(loc_folder: Path) -> dict[str, Path]:
    """Scan *loc_folder* for ``languagedata_*.xml`` -> {UPPER_CODE: path}."""
    codes: dict[str, Path] = {}
    if not loc_folder or not loc_folder.is_dir():
        return codes
    for f in sorted(loc_folder.iterdir()):
        if f.is_file() and f.name.lower().startswith("languagedata_") and f.suffix.lower() == ".xml":
            parts = f.stem.split("_", 1)
            if len(parts) == 2:
                code = parts[1].upper()
                codes[code] = f
    return codes


def get_valid_codes(loc_folder: Path | None = None) -> set[str]:
    """Return the set of valid language codes.

    Auto-discovers from LOC folder (cached) + hardcoded fallbacks.
    Call :func:`invalidate_code_cache` when the LOC folder changes.
    """
    global _cached_valid_codes, _cached_loc_folder

    if _cached_valid_codes is not None and _cached_loc_folder == loc_folder:
        return _cached_valid_codes

    codes = set(_FALLBACK_CODES)

    if loc_folder and loc_folder.is_dir():
        discovered = discover_valid_codes(loc_folder)
        codes.update(discovered.keys())
        logger.debug("Auto-discovered %d codes from LOC: %s", len(discovered), sorted(discovered))

    _cached_valid_codes = codes
    _cached_loc_folder = loc_folder
    logger.debug("Valid language codes (%d): %s", len(codes), sorted(codes))
    return codes


def invalidate_code_cache() -> None:
    """Clear the cached valid codes (call when LOC folder changes)."""
    global _cached_valid_codes, _cached_loc_folder
    _cached_valid_codes = None
    _cached_loc_folder = None


def extract_language_from_filename(name: str, valid_codes: set[str] | None = None) -> str:
    """Best-effort language code from filename, or 'UNKNOWN'."""
    m = _LANG_SUFFIX_RE.search(name)
    if m:
        candidate = m.group(1).upper()
        if valid_codes is None or candidate in valid_codes:
            return candidate
    return "UNKNOWN"


def extract_language_suffix(name: str, valid_codes: set[str]) -> str | None:
    """Extract language suffix from a filename using known valid codes.

    Handles ``file_ENG.xml``, ``file_ZH-TW.xml``, and folder names like ``FRE/``.
    Returns the uppercase code or *None*.
    """
    if not name:
        return None

    # Remove extension if present
    stem = Path(name).stem if "." in name else name

    # Standalone code: entire name is a valid code (e.g. "FRE", "ZHO-CN")
    if stem.upper() in valid_codes:
        return stem.upper()

    parts = stem.rsplit("_", 2)

    # Try last 2 parts joined as hyphenated (e.g. ZH-TW from file_ZH_TW)
    if len(parts) >= 3:
        candidate = f"{parts[-2]}-{parts[-1]}".upper()
        if candidate in valid_codes:
            return candidate

    # Try last part
    if len(parts) >= 2:
        candidate = parts[-1].upper()
        if candidate in valid_codes:
            return candidate

    return None


def count_xml_files(folder: Path) -> int:
    """Quick count of XML files in a folder (non-recursive)."""
    if not folder or not folder.is_dir():
        return 0
    return sum(1 for f in folder.iterdir() if f.is_file() and f.suffix.lower() == ".xml")


def count_loc_xml_files(folder: Path) -> int:
    """Quick count of .loc.xml files (recursive) in an EXPORT folder."""
    if not folder or not folder.is_dir():
        return 0
    return sum(1 for _ in folder.rglob("*.loc.xml"))
