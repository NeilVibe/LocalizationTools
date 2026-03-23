# Internal config module replacing sys.modules['config'] shim.
# Origin: LocaNext-specific (replaces transfer_config_shim.py pattern)
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from loguru import logger


@dataclass
class MergeConfig:
    """Configuration for the merge package.

    Replaces the synthetic `config` module that QuickTranslate core modules
    previously accessed via sys.modules injection.
    """

    LOC_FOLDER: Path = field(default_factory=lambda: Path("/tmp/quicktranslate_loc"))
    EXPORT_FOLDER: Path = field(default_factory=lambda: Path("/tmp/quicktranslate_export"))
    SCRIPT_CATEGORIES: set = field(default_factory=lambda: {"Sequencer", "Dialog"})
    SCRIPT_EXCLUDE_SUBFOLDERS: set = field(default_factory=set)
    LANGUAGE_NAMES: dict = field(default_factory=dict)
    FUZZY_THRESHOLD_DEFAULT: float = 0.85
    SEQUENCER_FOLDER: Path | None = None
    SCRIPT_DIR: Path | None = None
    OUTPUT_FOLDER: Path = field(default_factory=lambda: Path("/tmp/quicktranslate_output"))
    SOURCE_FOLDER: Path = field(default_factory=lambda: Path("/tmp/quicktranslate_source"))
    get_failed_report_dir: Callable = field(
        default_factory=lambda: lambda source_name: Path("/tmp/quicktranslate_reports")
    )


_instance: MergeConfig | None = None


def configure(loc_path: str, export_path: str) -> MergeConfig:
    """Create and store the merge config instance.

    Auto-discovers LANGUAGE_NAMES from LOC folder glob pattern
    ``languagedata_*.xml``.

    Args:
        loc_path: Path to LOC folder containing languagedata_*.xml files.
        export_path: Path to EXPORT folder containing categorized .loc.xml files.

    Returns:
        The newly created MergeConfig instance.
    """
    global _instance

    loc = Path(loc_path)
    export = Path(export_path)

    language_names: dict[str, str] = {}
    if loc.exists():
        for f in loc.glob("languagedata_*.xml"):
            m = re.match(r"languagedata_(.+)\.xml", f.name, re.IGNORECASE)
            if m:
                code = m.group(1)
                language_names[code.upper()] = code.upper()

    _instance = MergeConfig(
        LOC_FOLDER=loc,
        EXPORT_FOLDER=export,
        SCRIPT_CATEGORIES={"Sequencer", "Dialog"},
        SCRIPT_EXCLUDE_SUBFOLDERS=set(),
        LANGUAGE_NAMES=language_names,
        FUZZY_THRESHOLD_DEFAULT=0.85,
        SEQUENCER_FOLDER=export / "Sequencer",
        SCRIPT_DIR=loc.parent,
        OUTPUT_FOLDER=Path("/tmp/quicktranslate_output"),
        SOURCE_FOLDER=Path("/tmp/quicktranslate_source"),
        get_failed_report_dir=lambda source_name: Path("/tmp/quicktranslate_reports"),
    )

    logger.info(
        "Merge config created: LOC_FOLDER={}, EXPORT_FOLDER={}",
        loc_path,
        export_path,
    )
    return _instance


def get_config() -> MergeConfig:
    """Return the current merge config instance.

    Raises:
        RuntimeError: If ``configure()`` has not been called yet.
    """
    if _instance is None:
        raise RuntimeError(
            "Merge config not initialized. Call configure(loc_path, export_path) first."
        )
    return _instance


def reconfigure(loc_path: str, export_path: str) -> None:
    """Update existing config paths for project switching.

    Re-discovers LANGUAGE_NAMES from the new LOC folder.

    Args:
        loc_path: New LOC folder path.
        export_path: New EXPORT folder path.
    """
    global _instance

    if _instance is None:
        configure(loc_path, export_path)
        return

    loc = Path(loc_path)
    export = Path(export_path)

    _instance.LOC_FOLDER = loc
    _instance.EXPORT_FOLDER = export
    _instance.SEQUENCER_FOLDER = export / "Sequencer"
    _instance.SCRIPT_DIR = loc.parent

    # Re-discover language names
    _instance.LANGUAGE_NAMES = {}
    if loc.exists():
        for f in loc.glob("languagedata_*.xml"):
            m = re.match(r"languagedata_(.+)\.xml", f.name, re.IGNORECASE)
            if m:
                code = m.group(1)
                _instance.LANGUAGE_NAMES[code.upper()] = code.upper()

    logger.info(
        "Merge config reconfigured: LOC_FOLDER={}, EXPORT_FOLDER={}",
        loc_path,
        export_path,
    )
