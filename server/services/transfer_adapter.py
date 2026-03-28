"""
Transfer Adapter - Merge module wrapper for LocaNext.

Imports merge logic from server.services.merge (internalized QuickTranslate
core modules). No sys.path injection or importlib hacks.

Usage:
    from server.services.transfer_adapter import execute_transfer, MATCH_MODES
"""
from __future__ import annotations

from pathlib import Path

from loguru import logger

from server.services.merge._config import (
    configure as _merge_configure,
    reconfigure as _merge_reconfigure,
    get_config as _merge_get_config,
)
from server.services.merge import (
    transfer_folder_to_folder,
    merge_corrections_to_xml,
    merge_corrections_stringid_only,
    run_all_postprocess,
    scan_source_for_languages,
    discover_language_files,
    build_translation_lookup,
    build_stringid_to_category,
    build_stringid_to_subfolder,
    build_stringid_to_filepath,
)

# Match mode constants mapping LocaNext UI labels to QuickTranslate internals
MATCH_MODES = {
    "stringid_only": "StringID Only (case-insensitive, SCRIPT/ALL filter)",
    "strict": "StringID + StrOrigin (strict 2-key with nospace fallback)",
    "strorigin_filename": "StrOrigin + FileName 2PASS (3-tuple then 2-tuple)",
}

# Module-level cache for imported QT functions
_qt_modules: dict | None = None


def init_quicktranslate(loc_path: str, export_path: str) -> dict:
    """
    Initialize merge module imports with LocaNext-controlled paths.

    1. Configures the merge package with project paths
    2. Builds function reference dict from internalized modules

    Args:
        loc_path: Path to LOC folder containing languagedata_*.xml files.
        export_path: Path to EXPORT folder with categorized .loc.xml files.

    Returns:
        Dict mapping function names to callable references from merge modules.
    """
    global _qt_modules

    # Step 1: Configure the merge package with project paths
    _merge_configure(loc_path, export_path)

    # Step 2: Build function reference dict from internalized modules
    _qt_modules = {
        "transfer_folder_to_folder": transfer_folder_to_folder,
        "merge_corrections_to_xml": merge_corrections_to_xml,
        "merge_corrections_stringid_only": merge_corrections_stringid_only,
        "run_all_postprocess": run_all_postprocess,
        "scan_source_for_languages": scan_source_for_languages,
        "discover_language_files": discover_language_files,
        "build_translation_lookup": build_translation_lookup,
        "build_stringid_to_category": build_stringid_to_category,
        "build_stringid_to_subfolder": build_stringid_to_subfolder,
        "build_stringid_to_filepath": build_stringid_to_filepath,
    }

    logger.info("Merge modules loaded from server.services.merge")
    return _qt_modules


def get_qt_modules() -> dict:
    """
    Get cached QuickTranslate module references.

    Raises:
        RuntimeError: If init_quicktranslate() has not been called yet.

    Returns:
        Dict mapping function names to callable references.
    """
    if _qt_modules is None:
        raise RuntimeError("init_quicktranslate() not called")
    return _qt_modules


def execute_transfer(
    source_path: str,
    target_path: str,
    export_path: str,
    match_mode: str = "strict",
    only_untranslated: bool = False,
    stringid_all_categories: bool = False,
    dry_run: bool = False,
    progress_callback=None,
    log_callback=None,
    ignore_spaces: bool = False,
    ignore_punctuation: bool = False,
) -> dict:
    """Execute a transfer operation using the merge engine.

    Wraps ``transfer_folder_to_folder()`` with LocaNext-friendly
    parameters.  Handles config reconfiguration, lookup map building, and error
    handling so callers only need to provide simple string paths and flags.

    Args:
        source_path: Path to folder containing correction files (XML/Excel).
        target_path: Path to LOC folder with languagedata_\\*.xml files.
        export_path: Path to EXPORT folder with category subfolders.
        match_mode: ``"stringid_only"`` | ``"strict"`` | ``"strorigin_filename"``.
        only_untranslated: If True, skip entries that already have translations.
        stringid_all_categories: If True (StringID mode), match ALL categories
            not just SCRIPT.
        dry_run: If True, compute matches but don't write files.
        progress_callback: Optional ``callable(progress_pct: float, message: str)``.
        log_callback: Optional ``callable(message: str)``.

    Returns:
        Dict with merge results (matched, skipped, errors, etc.).
    """
    global _qt_modules

    if match_mode not in MATCH_MODES:
        raise ValueError(
            f"Unknown match_mode '{match_mode}'. Must be one of: {list(MATCH_MODES.keys())}"
        )

    # Ensure config is current for this project's paths
    _merge_reconfigure(target_path, export_path)

    # Lazy-initialize if not yet loaded
    if _qt_modules is None:
        init_quicktranslate(target_path, export_path)

    qt = get_qt_modules()

    # Build lookup maps based on match mode
    stringid_to_category = None
    stringid_to_subfolder = None
    stringid_to_filepath = None

    try:
        if match_mode == "stringid_only":
            try:
                stringid_to_category = qt["build_stringid_to_category"](Path(export_path))
            except Exception as exc:
                logger.warning("build_stringid_to_category failed ({}), proceeding without", exc)
            try:
                stringid_to_subfolder = qt["build_stringid_to_subfolder"](Path(export_path))
            except Exception as exc:
                logger.warning("build_stringid_to_subfolder failed ({}), proceeding without", exc)
        elif match_mode == "strorigin_filename":
            try:
                stringid_to_filepath = qt["build_stringid_to_filepath"](Path(export_path))
            except Exception as exc:
                logger.warning("build_stringid_to_filepath failed ({}), proceeding without", exc)
    except Exception as exc:
        logger.error("Failed to build lookup maps: {}", exc)

    # Delegate to the merge engine's all-in-one orchestrator
    try:
        result = qt["transfer_folder_to_folder"](
            source_folder=Path(source_path),
            target_folder=Path(target_path),
            stringid_to_category=stringid_to_category,
            stringid_to_subfolder=stringid_to_subfolder,
            stringid_to_filepath=stringid_to_filepath,
            match_mode=match_mode,
            dry_run=dry_run,
            progress_callback=progress_callback,
            log_callback=log_callback,
            only_untranslated=only_untranslated,
            stringid_all_categories=stringid_all_categories,
            ignore_spaces=ignore_spaces,
            ignore_punctuation=ignore_punctuation,
        )
    except Exception as exc:
        logger.error("transfer_folder_to_folder failed: {}", exc)
        result = {
            "match_mode": match_mode,
            "errors": [str(exc)],
            "total_matched": 0,
            "total_updated": 0,
        }

    return result


class TransferAdapter:
    """
    High-level adapter for merge operations.

    Manages config lifecycle and provides access to merge module functions.
    Supports path reconfiguration for project switching.
    """

    def __init__(self, loc_path: str, export_path: str) -> None:
        """
        Initialize adapter with project paths.

        Args:
            loc_path: Path to LOC folder containing languagedata_*.xml files.
            export_path: Path to EXPORT folder with categorized .loc.xml files.
        """
        self._loc_path = loc_path
        self._export_path = export_path
        self._modules = init_quicktranslate(loc_path, export_path)

    def reconfigure(self, loc_path: str, export_path: str) -> None:
        """
        Reconfigure paths for a different project.

        Updates the merge config and clears stale caches.

        Args:
            loc_path: New LOC folder path.
            export_path: New EXPORT folder path.
        """
        self._loc_path = loc_path
        self._export_path = export_path
        _merge_reconfigure(loc_path, export_path)

    @property
    def qt_modules(self) -> dict:
        """Get merge module function references."""
        return self._modules

    @property
    def loc_path(self) -> str:
        """Current LOC folder path."""
        return self._loc_path

    @property
    def export_path(self) -> str:
        """Current EXPORT folder path."""
        return self._export_path


# ---------------------------------------------------------------------------
# Multi-language folder merge (Plan 03 - XFER-07)
# ---------------------------------------------------------------------------


def _ensure_qt_initialized(target_path: str, export_path: str) -> dict:
    """Ensure merge modules are initialized, initializing if needed."""
    global _qt_modules
    if _qt_modules is None:
        return init_quicktranslate(target_path, export_path)
    _merge_reconfigure(target_path, export_path)
    return _qt_modules


def scan_source_languages(
    source_path: str,
    target_path: str | None = None,
) -> dict:
    """
    Scan a source folder for language-tagged files/subfolders.

    Wraps scan_source_for_languages() and converts the
    SourceScanResult dataclass to a plain dict for JSON serialization.

    Args:
        source_path: Path to source folder to scan.
        target_path: Optional LOC folder path for language code discovery.
            If provided, config.LOC_FOLDER is set to this path so the scanner
            can auto-detect valid language codes from languagedata_*.xml files.
            If omitted, uses source_path (may miss codes if source has no
            languagedata files).

    Returns:
        {
            "languages": {"FRE": [str_paths], "ENG": [str_paths], ...},
            "total_files": int,
            "language_count": int,
            "unrecognized": [str_paths],
            "warnings": [str],
        }
    """
    loc_dir = target_path or source_path
    qt = _ensure_qt_initialized(loc_dir, loc_dir)
    scanner = qt["scan_source_for_languages"]

    scan_result = scanner(Path(source_path))

    # Convert SourceScanResult to plain dict (Path -> str for JSON)
    languages = {}
    for lang_code, files in scan_result.lang_files.items():
        languages[lang_code] = [str(f) for f in files]

    return {
        "languages": languages,
        "total_files": scan_result.total_files,
        "language_count": scan_result.language_count,
        "unrecognized": [str(p) for p in scan_result.unrecognized],
        "warnings": list(scan_result.warnings),
    }


def execute_multi_language_transfer(
    source_path: str,
    target_path: str,
    export_path: str,
    match_mode: str = "strict",
    only_untranslated: bool = False,
    stringid_all_categories: bool = False,
    dry_run: bool = False,
    progress_callback=None,
    log_callback=None,
    ignore_spaces: bool = False,
    ignore_punctuation: bool = False,
) -> dict:
    """
    Execute multi-language transfer: scan source, merge each language.

    Wraps transfer_folder_to_folder which already handles
    multi-language internally via scan_source_for_languages. The wrapper adds:
    - Pre-scan for UI preview (language list before merge)
    - Per-language result breakdown extracted from file_results
    - LocaNext-friendly dict structure

    Args:
        source_path: Folder containing correction files (subfolders per language).
        target_path: LOC folder with languagedata_*.xml target files.
        export_path: EXPORT folder for category/filepath lookups.
        match_mode: "stringid_only" | "strict" | "strorigin_filename"
        only_untranslated: If True, only merge entries where target Str is empty.
        stringid_all_categories: If True, StringID-Only matches ALL categories.
        dry_run: If True, compute matches but do not write files.
        progress_callback: Optional progress reporting callable.
        log_callback: Optional log message callable.

    Returns:
        {
            "scan": {scan_source_languages result},
            "per_language": {"FRE": {"matched": N, ...}, "ENG": {...}},
            "total_matched": int,
            "total_skipped": int,
            "total_errors": int,
        }
    """
    qt = _ensure_qt_initialized(target_path, export_path)

    # Step 1: Pre-scan for UI preview data (pass target_path for language code discovery)
    scan_data = scan_source_languages(source_path, target_path=target_path)

    if scan_data["total_files"] == 0:
        return {
            "scan": scan_data,
            "per_language": {},
            "total_matched": 0,
            "total_skipped": 0,
            "total_errors": 0,
        }

    # Step 2: Build category/filepath maps if needed
    stringid_to_category = None
    stringid_to_subfolder = None
    stringid_to_filepath = None

    if match_mode == "stringid_only":
        try:
            stringid_to_category = qt["build_stringid_to_category"](Path(export_path))
        except Exception as exc:
            logger.warning("build_stringid_to_category failed ({}), proceeding without", exc)
        try:
            stringid_to_subfolder = qt["build_stringid_to_subfolder"](Path(export_path))
        except Exception as exc:
            logger.warning("build_stringid_to_subfolder failed ({}), proceeding without", exc)
    elif match_mode == "strorigin_filename":
        try:
            stringid_to_filepath = qt["build_stringid_to_filepath"](Path(export_path))
        except Exception as exc:
            logger.warning("build_stringid_to_filepath failed ({}), proceeding without", exc)

    # Step 3: Call transfer_folder_to_folder (handles multi-lang internally)
    try:
        raw_result = qt["transfer_folder_to_folder"](
            source_folder=Path(source_path),
            target_folder=Path(target_path),
            stringid_to_category=stringid_to_category,
            stringid_to_subfolder=stringid_to_subfolder,
            stringid_to_filepath=stringid_to_filepath,
            match_mode=match_mode,
            dry_run=dry_run,
            progress_callback=progress_callback,
            log_callback=log_callback,
            only_untranslated=only_untranslated,
            stringid_all_categories=stringid_all_categories,
            ignore_spaces=ignore_spaces,
            ignore_punctuation=ignore_punctuation,
        )
    except Exception as exc:
        logger.error("transfer_folder_to_folder failed: {}", exc)
        return {
            "scan": scan_data,
            "per_language": {},
            "total_matched": 0,
            "total_skipped": 0,
            "total_errors": 1,
        }

    # Step 4: Extract per-language breakdown from file_results
    # file_results is keyed by target file path; extract language from filename
    per_language: dict = {}
    file_results = raw_result.get("file_results", {})

    for file_key, file_data in file_results.items():
        # Extract language code from target filename (e.g., languagedata_FRE.xml -> FRE)
        fname = Path(file_key).stem
        lang = None
        if fname.lower().startswith("languagedata_"):
            lang = fname[13:].upper()
        elif "_" in fname:
            lang = fname.split("_")[-1].upper()

        if not lang:
            lang = "UNKNOWN"

        if lang not in per_language:
            per_language[lang] = {
                "matched": 0,
                "updated": 0,
                "not_found": 0,
                "skipped": 0,
                "errors": 0,
            }

        entry = per_language[lang]
        if isinstance(file_data, dict):
            entry["matched"] += file_data.get("matched", 0)
            entry["updated"] += file_data.get("updated", 0)
            entry["not_found"] += file_data.get("not_found", 0)
            entry["skipped"] += (
                file_data.get("skipped_translated", 0)
                + file_data.get("skipped_non_script", 0)
                + file_data.get("skipped_excluded", 0)
                + file_data.get("skipped_empty_strorigin", 0)
            )
            entry["errors"] += len(file_data.get("errors", []))

    # If no file_results were returned but we have aggregate totals, create
    # a single "ALL" language entry from raw_result totals.
    if not per_language and raw_result.get("total_matched", 0) > 0:
        per_language["ALL"] = {
            "matched": raw_result.get("total_matched", 0),
            "updated": raw_result.get("total_updated", 0),
            "not_found": raw_result.get("total_not_found", 0),
            "skipped": raw_result.get("total_skipped", 0),
            "errors": len(raw_result.get("errors", [])),
        }

    total_matched = raw_result.get("total_matched", 0)
    total_skipped = raw_result.get("total_skipped", 0)
    total_errors = len(raw_result.get("errors", []))

    return {
        "scan": scan_data,
        "per_language": per_language,
        "total_matched": total_matched,
        "total_skipped": total_skipped,
        "total_errors": total_errors,
    }
