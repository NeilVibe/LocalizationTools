"""
Config shim for QuickTranslate module imports.

Creates a synthetic `config` module and injects it into sys.modules so that
QuickTranslate core modules (which do `import config` at module level) get
LocaNext-controlled paths instead of reading from settings.json / F: drive defaults.

CRITICAL: This shim MUST be injected BEFORE any `from core.*` import.
"""
from __future__ import annotations

import re
import sys
import types
from pathlib import Path

from loguru import logger


def create_config_shim(loc_path: str, export_path: str) -> types.ModuleType:
    """
    Create a synthetic config module with LocaNext-controlled paths.

    Sets all attributes that QuickTranslate core modules expect from `config`:
    LOC_FOLDER, EXPORT_FOLDER, SCRIPT_CATEGORIES, SCRIPT_EXCLUDE_SUBFOLDERS,
    LANGUAGE_NAMES, FUZZY_THRESHOLD_DEFAULT, SEQUENCER_FOLDER, SCRIPT_DIR,
    OUTPUT_FOLDER, SOURCE_FOLDER, get_failed_report_dir.

    Args:
        loc_path: Path to LOC folder containing languagedata_*.xml files.
        export_path: Path to EXPORT folder containing categorized .loc.xml files.

    Returns:
        A types.ModuleType configured as a QuickTranslate config replacement.
    """
    config = types.ModuleType("config")
    config.LOC_FOLDER = Path(loc_path)
    config.EXPORT_FOLDER = Path(export_path)
    config.SCRIPT_CATEGORIES = {"Sequencer", "Dialog"}
    config.SCRIPT_EXCLUDE_SUBFOLDERS = set()
    config.LANGUAGE_NAMES = {}
    config.FUZZY_THRESHOLD_DEFAULT = 0.85
    config.SEQUENCER_FOLDER = Path(export_path) / "Sequencer"
    config.SCRIPT_DIR = Path(loc_path).parent
    config.OUTPUT_FOLDER = Path("/tmp/quicktranslate_output")
    config.SOURCE_FOLDER = Path("/tmp/quicktranslate_source")

    # Matching modes (referenced by some QT modules)
    config.MATCHING_MODES = {
        "stringid_only": "StringID-Only (SCRIPT strings)",
        "strict": "StringID + StrOrigin (Strict)",
        "strorigin_only": "StrOrigin Only (non-script, fills duplicates)",
        "strorigin_descorigin": "StrOrigin + DescOrigin",
        "strorigin_filename": "StrOrigin + FileName (2-pass, export filepath)",
    }

    # Failed report directory factory
    config.get_failed_report_dir = lambda source_name: Path("/tmp/quicktranslate_reports")

    # Auto-discover language names from LOC folder
    if config.LOC_FOLDER.exists():
        for f in config.LOC_FOLDER.glob("languagedata_*.xml"):
            m = re.match(r"languagedata_(.+)\.xml", f.name, re.IGNORECASE)
            if m:
                code = m.group(1)
                config.LANGUAGE_NAMES[code.upper()] = code.upper()

    return config


def inject_config_shim(loc_path: str, export_path: str) -> types.ModuleType:
    """
    Create config shim and inject into sys.modules['config'].

    This bypasses Python's import resolution entirely, ensuring that any
    `import config` statement in QuickTranslate modules gets our synthetic module.

    Args:
        loc_path: Path to LOC folder.
        export_path: Path to EXPORT folder.

    Returns:
        The injected config module.
    """
    shim = create_config_shim(loc_path, export_path)
    sys.modules["config"] = shim
    logger.info(
        "Config shim injected: LOC_FOLDER={}, EXPORT_FOLDER={}",
        loc_path,
        export_path,
    )
    return shim


def reconfigure_paths(loc_path: str, export_path: str) -> None:
    """
    Update existing config shim paths for project switching.

    If no config shim exists yet, creates and injects one.
    Also clears source_scanner's cached language codes to prevent stale data.

    Args:
        loc_path: New LOC folder path.
        export_path: New EXPORT folder path.
    """
    config = sys.modules.get("config")
    if config is None or not isinstance(config, types.ModuleType):
        inject_config_shim(loc_path, export_path)
        return

    config.LOC_FOLDER = Path(loc_path)
    config.EXPORT_FOLDER = Path(export_path)
    config.SEQUENCER_FOLDER = Path(export_path) / "Sequencer"
    config.SCRIPT_DIR = Path(loc_path).parent

    # Re-discover language names from new LOC folder
    config.LANGUAGE_NAMES = {}
    if config.LOC_FOLDER.exists():
        for f in config.LOC_FOLDER.glob("languagedata_*.xml"):
            m = re.match(r"languagedata_(.+)\.xml", f.name, re.IGNORECASE)
            if m:
                code = m.group(1)
                config.LANGUAGE_NAMES[code.upper()] = code.upper()

    # Clear source_scanner's cached language codes (stale after path change)
    try:
        from core.source_scanner import clear_language_code_cache
        clear_language_code_cache()
    except (ImportError, AttributeError):
        pass  # source_scanner not yet imported or function doesn't exist

    logger.info(
        "Config paths reconfigured: LOC_FOLDER={}, EXPORT_FOLDER={}",
        loc_path,
        export_path,
    )
