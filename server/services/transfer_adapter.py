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
