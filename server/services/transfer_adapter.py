"""
Transfer Adapter - QuickTranslate module import wrapper for LocaNext.

Imports QuickTranslate's Sacred Script core modules via sys.path injection,
making them available as a LocaNext service. NEVER copies or modifies Sacred
Script code -- only imports and wraps.

Usage:
    from server.services.transfer_adapter import TransferAdapter

    adapter = TransferAdapter(loc_path="/path/to/loc", export_path="/path/to/export")
    qt = adapter.qt_modules
    qt["transfer_folder_to_folder"](source, target, ...)
"""
from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger

from server.services.transfer_config_shim import inject_config_shim, reconfigure_paths

# Match mode constants mapping LocaNext UI labels to QuickTranslate internals
MATCH_MODES = {
    "stringid_only": "StringID Only (case-insensitive, SCRIPT/ALL filter)",
    "strict": "StringID + StrOrigin (strict 2-key with nospace fallback)",
    "strorigin_filename": "StrOrigin + FileName 2PASS (3-tuple then 2-tuple)",
}

# QuickTranslate root path (relative to project root)
QT_ROOT = str(
    Path(__file__).resolve().parent.parent.parent
    / "RessourcesForCodingTheProject"
    / "NewScripts"
    / "QuickTranslate"
)

# Module-level cache for imported QT functions
_qt_modules: dict | None = None


def init_quicktranslate(loc_path: str, export_path: str) -> dict:
    """
    Initialize QuickTranslate module imports with LocaNext-controlled paths.

    1. Injects config shim into sys.modules['config']
    2. Adds QuickTranslate root to sys.path[0]
    3. Imports core modules and caches function references

    Args:
        loc_path: Path to LOC folder containing languagedata_*.xml files.
        export_path: Path to EXPORT folder with categorized .loc.xml files.

    Returns:
        Dict mapping function names to callable references from QT core modules.
    """
    global _qt_modules

    # Step 1: Inject config shim (MUST happen before any QT import)
    inject_config_shim(loc_path, export_path)

    # Step 2: Add QuickTranslate root to sys.path
    if QT_ROOT not in sys.path:
        sys.path.insert(0, QT_ROOT)

    # Step 3: Import core modules (now safe -- config is in sys.modules)
    from core.xml_transfer import (
        transfer_folder_to_folder,
        merge_corrections_to_xml,
        merge_corrections_stringid_only,
    )
    from core.postprocess import run_all_postprocess
    from core.source_scanner import scan_source_for_languages
    from core.language_loader import (
        discover_language_files,
        build_translation_lookup,
        build_stringid_to_category,
        build_stringid_to_subfolder,
        build_stringid_to_filepath,
    )

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

    logger.info("QuickTranslate modules loaded from {}", QT_ROOT)
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
) -> dict:
    """Execute a transfer operation using QuickTranslate's engine.

    Wraps QuickTranslate's ``transfer_folder_to_folder()`` with LocaNext-friendly
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

    # Ensure config shim is current for this project's paths
    reconfigure_paths(target_path, export_path)

    # Lazy-initialize QuickTranslate if not yet loaded
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

    # Delegate to QuickTranslate's all-in-one orchestrator
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
    High-level adapter for QuickTranslate operations.

    Manages config shim lifecycle and provides access to QT module functions.
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

        Updates the config shim and clears stale caches.

        Args:
            loc_path: New LOC folder path.
            export_path: New EXPORT folder path.
        """
        self._loc_path = loc_path
        self._export_path = export_path
        reconfigure_paths(loc_path, export_path)

    @property
    def qt_modules(self) -> dict:
        """Get QuickTranslate module function references."""
        return self._modules

    @property
    def loc_path(self) -> str:
        """Current LOC folder path."""
        return self._loc_path

    @property
    def export_path(self) -> str:
        """Current EXPORT folder path."""
        return self._export_path
