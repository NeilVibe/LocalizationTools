"""
MapDataGenerator Configuration Module

Constants, settings, and configuration management for the MapDataGenerator tool.
"""

import os
import sys
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass, field, asdict
from pathlib import Path


# =============================================================================
# Application Constants
# =============================================================================

VERSION = "1.0.0"
APP_NAME = "MapDataGenerator"


# =============================================================================
# Available Languages (13 total)
# =============================================================================

LANGUAGES = [
    ('eng', 'English'),
    ('fre', 'French'),
    ('ger', 'German'),
    ('spa', 'Spanish'),
    ('por', 'Portuguese'),
    ('ita', 'Italian'),
    ('rus', 'Russian'),
    ('tur', 'Turkish'),
    ('pol', 'Polish'),
    ('zho-cn', 'Chinese (Simplified)'),
    ('zho-tw', 'Chinese (Traditional)'),
    ('jpn', 'Japanese'),
    ('kor', 'Korean'),
]

LANGUAGE_CODES = [code for code, _ in LANGUAGES]
LANGUAGE_NAMES = {code: name for code, name in LANGUAGES}


# =============================================================================
# Default Paths (can be overridden via settings.json)
# =============================================================================

DEFAULT_FACTION_FOLDER = r"F:\perforce\cd\mainline\resource\GameData\StaticInfo\factioninfo"
DEFAULT_LOC_FOLDER = r"F:\perforce\cd\mainline\resource\GameData\stringtable\loc"
DEFAULT_KNOWLEDGE_FOLDER = r"F:\perforce\cd\mainline\resource\GameData\StaticInfo\knowledgeinfo"
DEFAULT_WAYPOINT_FOLDER = r"F:\perforce\cd\mainline\resource\GameData\StaticInfo\factioninfo\NodeWaypointInfo"
DEFAULT_TEXTURE_FOLDER = r"F:\perforce\cd\mainline\resource\GameData\Textures"


# =============================================================================
# File Patterns
# =============================================================================

LANGUAGE_FILE_PATTERN = "languagedata_{code}.xml"
FACTION_NODE_PATTERN = "*.xml"
KNOWLEDGE_INFO_PATTERN = "*.xml"


# =============================================================================
# Search Settings
# =============================================================================

DEFAULT_SEARCH_LIMIT = 100
FUZZY_THRESHOLD = 0.6


# =============================================================================
# Image Cache Settings
# =============================================================================

IMAGE_CACHE_SIZE = 50
THUMBNAIL_SIZE = (128, 128)


# =============================================================================
# Default Settings
# =============================================================================

DEFAULT_FONT_FAMILY = 'Malgun Gothic'
DEFAULT_FONT_SIZE = 10

DEFAULT_COLORS = {
    'node_default': 'crimson',
    'node_selected': 'blue',
    'node_highlighted': 'gold',
    'route_default': 'royalblue',
}


# =============================================================================
# UI Languages
# =============================================================================

UI_LANGUAGES = {
    'English': {
        'file': 'File',
        'load_data': 'Load Data',
        'settings': 'Settings',
        'exit': 'Exit',
        'search': 'Search',
        'search_placeholder': 'Enter search term...',
        'contains': 'Contains',
        'exact': 'Exact',
        'fuzzy': 'Fuzzy',
        'language': 'Language',
        'results': 'Results',
        'no_results': 'No results found',
        'loading': 'Loading...',
        'ready': 'Ready',
        'name_kr': 'Name (KR)',
        'name_tr': 'Name (Translated)',
        'description': 'Description',
        'position': 'Position',
        'strkey': 'StrKey',
        'image': 'Image',
        'map': 'Map',
        'load_more': 'Load More',
        'error': 'Error',
        'select_folder': 'Select Folder',
    },
    '한국어': {
        'file': '파일',
        'load_data': '데이터 불러오기',
        'settings': '설정',
        'exit': '종료',
        'search': '검색',
        'search_placeholder': '검색어 입력...',
        'contains': '포함',
        'exact': '정확히',
        'fuzzy': '유사',
        'language': '언어',
        'results': '결과',
        'no_results': '결과 없음',
        'loading': '불러오는 중...',
        'ready': '준비',
        'name_kr': '이름 (한국어)',
        'name_tr': '이름 (번역)',
        'description': '설명',
        'position': '위치',
        'strkey': 'StrKey',
        'image': '이미지',
        'map': '지도',
        'load_more': '더 보기',
        'error': '오류',
        'select_folder': '폴더 선택',
    }
}


# =============================================================================
# Settings Dataclass
# =============================================================================

@dataclass
class Settings:
    """Application settings with defaults."""
    font_family: str = DEFAULT_FONT_FAMILY
    font_size: int = DEFAULT_FONT_SIZE
    ui_language: str = 'English'
    selected_language: str = 'eng'  # Translation language
    colors: Dict[str, str] = field(default_factory=lambda: DEFAULT_COLORS.copy())

    # Paths (can be overridden)
    faction_folder: str = DEFAULT_FACTION_FOLDER
    loc_folder: str = DEFAULT_LOC_FOLDER
    knowledge_folder: str = DEFAULT_KNOWLEDGE_FOLDER
    waypoint_folder: str = DEFAULT_WAYPOINT_FOLDER
    texture_folder: str = DEFAULT_TEXTURE_FOLDER

    # Search settings
    search_limit: int = DEFAULT_SEARCH_LIMIT
    fuzzy_threshold: float = FUZZY_THRESHOLD

    # Window state
    window_geometry: str = "1200x800"

    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Settings':
        """Create Settings from dictionary."""
        return cls(
            font_family=data.get('font_family', DEFAULT_FONT_FAMILY),
            font_size=data.get('font_size', DEFAULT_FONT_SIZE),
            ui_language=data.get('ui_language', 'English'),
            selected_language=data.get('selected_language', 'eng'),
            colors=data.get('colors', DEFAULT_COLORS.copy()),
            faction_folder=data.get('faction_folder', DEFAULT_FACTION_FOLDER),
            loc_folder=data.get('loc_folder', DEFAULT_LOC_FOLDER),
            knowledge_folder=data.get('knowledge_folder', DEFAULT_KNOWLEDGE_FOLDER),
            waypoint_folder=data.get('waypoint_folder', DEFAULT_WAYPOINT_FOLDER),
            texture_folder=data.get('texture_folder', DEFAULT_TEXTURE_FOLDER),
            search_limit=data.get('search_limit', DEFAULT_SEARCH_LIMIT),
            fuzzy_threshold=data.get('fuzzy_threshold', FUZZY_THRESHOLD),
            window_geometry=data.get('window_geometry', "1200x800"),
        )


# =============================================================================
# Utility Functions
# =============================================================================

def get_base_dir() -> Path:
    """Get the base directory for the application."""
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller EXE
        return Path(sys.executable).parent
    else:
        # Running as script
        return Path(__file__).parent


def get_settings_path() -> Path:
    """Get the path to the settings file."""
    return get_base_dir() / 'mdg_settings.json'


def get_log_dir() -> Path:
    """Get the directory for log files."""
    log_dir = get_base_dir() / 'logs'
    log_dir.mkdir(exist_ok=True)
    return log_dir


def get_cache_dir() -> Path:
    """Get the directory for cache files."""
    cache_dir = get_base_dir() / 'cache'
    cache_dir.mkdir(exist_ok=True)
    return cache_dir


# =============================================================================
# Settings Management
# =============================================================================

_current_settings: Optional[Settings] = None


def load_settings() -> Settings:
    """Load settings from file or create defaults."""
    global _current_settings

    settings_path = get_settings_path()

    try:
        if settings_path.exists():
            with open(settings_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                _current_settings = Settings.from_dict(data)
        else:
            _current_settings = Settings()
            save_settings(_current_settings)
    except Exception:
        _current_settings = Settings()

    return _current_settings


def save_settings(settings: Settings) -> bool:
    """Save settings to file."""
    global _current_settings
    _current_settings = settings

    settings_path = get_settings_path()

    try:
        with open(settings_path, 'w', encoding='utf-8') as f:
            json.dump(settings.to_dict(), f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def get_settings() -> Settings:
    """Get current settings, loading if necessary."""
    if _current_settings is None:
        return load_settings()
    return _current_settings


def get_ui_text(key: str, language: Optional[str] = None) -> str:
    """Get UI text in the specified or current language."""
    if language is None:
        language = get_settings().ui_language

    lang_dict = UI_LANGUAGES.get(language, UI_LANGUAGES['English'])
    return lang_dict.get(key, UI_LANGUAGES['English'].get(key, key))
