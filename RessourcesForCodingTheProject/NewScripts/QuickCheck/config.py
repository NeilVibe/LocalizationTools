"""
QuickCheck Configuration Module

Constants, settings, and configuration for the QuickCheck tool.
"""
from __future__ import annotations

import os
import sys
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass, field, asdict


# =============================================================================
# Application Constants
# =============================================================================

VERSION = "1.0.0"
APP_NAME = "QuickCheck"

# Supported file extensions
SUPPORTED_EXTENSIONS = ('.xml',)

# Source base constants (inherited from QuickSearch pattern)
SOURCE_BASE_KR = "kr_base"
SOURCE_BASE_ENG = "eng_base"

# Term match mode constants
MATCH_MODE_ISOLATED = "isolated"    # Word-boundary check (exact isolated matches only)
MATCH_MODE_SUBSTRING = "substring"  # Any occurrence — no isolation check


# =============================================================================
# Valid Language Codes
# Hard-coded set — QuickCheck is standalone, no LOC folder dependency.
# =============================================================================

VALID_CODES = {
    # Western European
    "ENG", "FRE", "GER", "SPA", "ITA", "POR",
    # Spanish/Portuguese regional variants
    "SPA-ES", "SPA-MX", "SPA-AR", "SPA-CO", "SPA-CL",
    "POR-BR", "POR-PT",
    # Eastern European
    "RUS", "POL", "CZE", "HUN", "ROM", "BUL", "HRV", "SLO", "SLK",
    # Nordic
    "NOR", "SWE", "DAN", "FIN",
    # Asian
    "JPN", "KOR", "ZHO", "ZHO-CN", "ZHO-TW", "THA", "VIE", "IND",
    # Middle East
    "ARA", "TUR", "HEB",
    # Other
    "DUT", "GRE", "UKR", "SRB",
}


# =============================================================================
# Default Settings Values
# =============================================================================

DEFAULT_MAX_TERM_LENGTH = 20
DEFAULT_MIN_OCCURRENCE = 2
DEFAULT_MAX_ISSUES_PER_TERM = 6
DEFAULT_FILTER_SENTENCES = True
DEFAULT_TERM_MATCH_MODE = MATCH_MODE_ISOLATED
OUTPUT_FOLDER_NAME = "CheckOutput"


# =============================================================================
# Settings Dataclass
# =============================================================================

@dataclass
class Settings:
    """Persisted user settings for QuickCheck."""
    # Glossary extraction parameters (for auto-extract mode)
    max_term_length: int = DEFAULT_MAX_TERM_LENGTH
    min_occurrence: int = DEFAULT_MIN_OCCURRENCE
    max_issues_per_term: int = DEFAULT_MAX_ISSUES_PER_TERM
    filter_sentences: bool = DEFAULT_FILTER_SENTENCES

    # Term check match mode
    term_match_mode: str = DEFAULT_TERM_MATCH_MODE


    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Settings:
        def _int(key: str, default: int) -> int:
            try:
                return int(data.get(key, default))
            except (TypeError, ValueError):
                return default

        return cls(
            max_term_length=_int("max_term_length", DEFAULT_MAX_TERM_LENGTH),
            min_occurrence=_int("min_occurrence", DEFAULT_MIN_OCCURRENCE),
            max_issues_per_term=_int("max_issues_per_term", DEFAULT_MAX_ISSUES_PER_TERM),
            filter_sentences=bool(data.get("filter_sentences", DEFAULT_FILTER_SENTENCES)),
            term_match_mode=MATCH_MODE_ISOLATED,  # Always isolated — substring hidden
        )


# =============================================================================
# Path Utilities
# =============================================================================

def get_base_dir() -> str:
    """Get the application base directory (next to exe or script)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def get_settings_path() -> str:
    return os.path.join(get_base_dir(), "qc_settings.json")


def get_output_dir() -> str:
    """Return the fixed CheckOutput directory next to the exe, auto-created."""
    out = os.path.join(get_base_dir(), OUTPUT_FOLDER_NAME)
    os.makedirs(out, exist_ok=True)
    return out


# =============================================================================
# Settings Management
# =============================================================================

_current_settings: Optional[Settings] = None


def load_settings() -> Settings:
    global _current_settings
    path = get_settings_path()
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                _current_settings = Settings.from_dict(json.load(f))
        else:
            _current_settings = Settings()
            save_settings(_current_settings)
    except Exception:
        _current_settings = Settings()
    return _current_settings


def save_settings(settings: Settings) -> bool:
    global _current_settings
    _current_settings = settings
    try:
        with open(get_settings_path(), "w", encoding="utf-8") as f:
            json.dump(settings.to_dict(), f, indent=2)
        return True
    except Exception:
        return False


def get_settings() -> Settings:
    if _current_settings is None:
        return load_settings()
    return _current_settings
