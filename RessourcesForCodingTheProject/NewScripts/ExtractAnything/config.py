"""ExtractAnything – global constants, settings persistence, paths."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

VERSION = "1.0.0"

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Script / exe directory
# ---------------------------------------------------------------------------
if getattr(sys, "frozen", False):
    SCRIPT_DIR = Path(sys.executable).parent
else:
    SCRIPT_DIR = Path(__file__).parent

SETTINGS_FILE = SCRIPT_DIR / "extractanything_settings.json"
PATH_FILTER_FILE = SCRIPT_DIR / "path_filter_rules.json"

# ---------------------------------------------------------------------------
# XML tag / attribute variants (case-insensitive matching)
# ---------------------------------------------------------------------------
LOCSTR_TAGS = ("LocStr", "locstr", "LOCSTR", "LOCStr", "Locstr")
STRINGID_ATTRS = ("StringId", "StringID", "stringid", "STRINGID", "Stringid", "stringId")
STRORIGIN_ATTRS = ("StrOrigin", "Strorigin", "strorigin", "STRORIGIN")
STR_ATTRS = ("Str", "str", "STR")
SOUNDEVENT_ATTRS = (
    "SoundEventName", "soundeventname", "Soundeventname",
    "SOUNDEVENTNAME", "EventName", "eventname", "EVENTNAME",
)

# ---------------------------------------------------------------------------
# Category / subfolder constants
# ---------------------------------------------------------------------------
SCRIPT_CATEGORIES = {"Sequencer", "Dialog"}
EXCLUDE_SUBFOLDERS = {"narrationdialog"}

# ---------------------------------------------------------------------------
# Comparison modes (Diff tab)
# ---------------------------------------------------------------------------
COMPARE_MODES = [
    "Full (all attributes)",
    "StrOrigin + StringID",
    "StrOrigin + StringID + Str",
    "StringID + Str",
    "StrOrigin Diff",
]

# Category filter options (Diff tab)
CATEGORY_FILTERS = [
    "All (no filter)",
    "SCRIPT only",
    "NON-SCRIPT only",
]

# ---------------------------------------------------------------------------
# Excel header variants (case-insensitive matching in readers)
# ---------------------------------------------------------------------------
STRINGID_HEADERS = {"stringid", "string_id", "sid"}
STRORIGIN_HEADERS = {"strorigin", "str_origin", "origin"}
STR_HEADERS = {"str", "text", "translation"}
EVENTNAME_HEADERS = {"eventname", "event_name", "event"}

# ---------------------------------------------------------------------------
# Mutable module-level paths (mutated via update_settings)
# ---------------------------------------------------------------------------
LOC_FOLDER: Path | None = None
EXPORT_FOLDER: Path | None = None
OUTPUT_DIR: Path = SCRIPT_DIR / "Output"

# ---------------------------------------------------------------------------
# Settings persistence
# ---------------------------------------------------------------------------
def _load_settings() -> dict:
    """Load settings from JSON. Returns empty dict on failure."""
    if not SETTINGS_FILE.exists():
        return {}
    try:
        return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Failed to load settings: %s", exc)
        return {}


def _save_settings(data: dict) -> None:
    """Write settings dict to JSON."""
    try:
        SETTINGS_FILE.write_text(
            json.dumps(data, indent=2, default=str), encoding="utf-8"
        )
    except Exception as exc:
        logger.warning("Failed to save settings: %s", exc)


def update_settings(
    *,
    loc_folder: Path | str | None = None,
    export_folder: Path | str | None = None,
) -> None:
    """Mutate module globals and persist to disk."""
    global LOC_FOLDER, EXPORT_FOLDER
    data = _load_settings()

    if loc_folder is not None:
        LOC_FOLDER = Path(loc_folder)
        data["loc_folder"] = str(LOC_FOLDER)
    if export_folder is not None:
        EXPORT_FOLDER = Path(export_folder)
        data["export_folder"] = str(EXPORT_FOLDER)

    _save_settings(data)
    logger.info("Settings updated → %s", SETTINGS_FILE)


def init_settings() -> None:
    """Load persisted settings into module globals at startup."""
    global LOC_FOLDER, EXPORT_FOLDER
    data = _load_settings()

    loc = data.get("loc_folder")
    if loc and Path(loc).is_dir():
        LOC_FOLDER = Path(loc)

    exp = data.get("export_folder")
    if exp and Path(exp).is_dir():
        EXPORT_FOLDER = Path(exp)


# ---------------------------------------------------------------------------
# Path filter persistence
# ---------------------------------------------------------------------------
def load_path_filter_rules() -> list[str]:
    """Load included paths from JSON. Returns empty list on failure."""
    if not PATH_FILTER_FILE.exists():
        return []
    try:
        data = json.loads(PATH_FILTER_FILE.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
        return []
    except Exception as exc:
        logger.warning("Failed to load path filter rules: %s", exc)
        return []


def save_path_filter_rules(paths: list[str]) -> None:
    """Save included paths to JSON."""
    try:
        PATH_FILTER_FILE.write_text(
            json.dumps(paths, indent=2), encoding="utf-8"
        )
    except Exception as exc:
        logger.warning("Failed to save path filter rules: %s", exc)
