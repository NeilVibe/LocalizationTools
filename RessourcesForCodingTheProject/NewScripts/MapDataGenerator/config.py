"""
MapDataGenerator Configuration Module

Constants, settings, and configuration management for the MapDataGenerator tool.

Supports configurable drive letter and branch via settings.json:
{
    "drive_letter": "D",  // Default is "F"
    "branch": "cd_beta"   // Default is "mainline"
}
"""

import os
import sys
import json
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, field, asdict
from pathlib import Path

log = logging.getLogger(__name__)


# =============================================================================
# Application Constants
# =============================================================================

VERSION = "2.0.0"
APP_NAME = "MapDataGenerator"


# =============================================================================
# Base Directory Detection
# =============================================================================

def get_base_dir() -> Path:
    """Get the base directory for the application."""
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller EXE
        return Path(sys.executable).parent
    else:
        # Running as script
        return Path(__file__).parent


# =============================================================================
# Drive Letter Configuration (loaded from settings.json)
# =============================================================================

def _load_drive_letter() -> str:
    """Load drive letter from settings.json.

    Returns:
        Drive letter (single character, default "F")
    """
    settings_file = get_base_dir() / "settings.json"

    if not settings_file.exists():
        return "F"

    try:
        with open(settings_file, 'r', encoding='utf-8') as f:
            settings = json.load(f)

        drive = settings.get('drive_letter', 'F')
        if isinstance(drive, str) and len(drive) == 1 and drive.isalpha():
            return drive.upper()
        else:
            log.warning("Invalid drive_letter in settings.json: '%s'. Using F:", drive)
            return "F"
    except Exception as e:
        log.warning("Error reading settings.json: %s. Using F:", e)
        return "F"


def _apply_drive_letter(path_str: str, drive_letter: str) -> str:
    """Replace default F: drive with configured drive letter."""
    if path_str.startswith("F:") or path_str.startswith("f:"):
        return f"{drive_letter}:{path_str[2:]}"
    return path_str


# Load drive letter at module import
_DRIVE_LETTER = _load_drive_letter()
if _DRIVE_LETTER != 'F':
    log.info("MapDataGenerator: Using drive %s:", _DRIVE_LETTER)


# =============================================================================
# Branch Configuration (loaded from settings.json)
# =============================================================================

KNOWN_BRANCHES = ["mainline", "cd_beta", "cd_alpha", "cd_lambda"]


def _load_branch() -> str:
    """Load branch name from settings.json.

    Returns:
        Branch name (default "mainline")
    """
    settings_file = get_base_dir() / "settings.json"

    if not settings_file.exists():
        return "mainline"

    try:
        with open(settings_file, 'r', encoding='utf-8') as f:
            settings = json.load(f)

        branch = settings.get('branch', 'mainline')
        if isinstance(branch, str) and branch.strip():
            return branch.strip()
        else:
            log.warning("Invalid branch in settings.json: '%s'. Using mainline", branch)
            return "mainline"
    except Exception as e:
        log.warning("Error reading settings.json for branch: %s. Using mainline", e)
        return "mainline"


def _apply_branch(path_str: str, branch: str) -> str:
    """Replace 'mainline' with the configured branch name in a path string."""
    return path_str.replace("mainline", branch)


# Load branch at module import
_BRANCH = _load_branch()
if _BRANCH != 'mainline':
    log.info("MapDataGenerator: Using branch %s", _BRANCH)


# =============================================================================
# Available Languages (14 total)
# =============================================================================

LANGUAGES = [
    ('eng', 'English'),
    ('fre', 'French'),
    ('ger', 'German'),
    ('spa-es', 'Spanish (Spain)'),
    ('spa-mx', 'Spanish (Mexico)'),
    ('por-br', 'Portuguese (Brazil)'),
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
# Default Path Templates (F: drive, mainline branch)
# =============================================================================

_PATH_TEMPLATES = {
    'faction_folder':    r"F:\perforce\cd\mainline\resource\GameData\StaticInfo\factioninfo",
    'loc_folder':        r"F:\perforce\cd\mainline\resource\GameData\stringtable\loc",
    'knowledge_folder':  r"F:\perforce\cd\mainline\resource\GameData\StaticInfo\knowledgeinfo",
    'waypoint_folder':   r"F:\perforce\cd\mainline\resource\GameData\StaticInfo\factioninfo\NodeWaypointInfo",
    'texture_folder':    r"F:\perforce\common\mainline\commonresource\ui\texture\image",
    'character_folder':  r"F:\perforce\cd\mainline\resource\GameData\StaticInfo\characterinfo",
    'audio_folder':      r"F:\perforce\cd\mainline\resource\sound\windows\English(US)",
    'audio_folder_kr':   r"F:\perforce\cd\mainline\resource\sound\windows\Korean",
    'audio_folder_zh':   r"F:\perforce\cd\mainline\resource\sound\windows\Chinese(PRC)",
    'export_folder':     r"F:\perforce\cd\mainline\resource\GameData\stringtable\export__",
}


def generate_default_paths(drive: str, branch: str) -> dict:
    """Rebuild all default paths from templates with the given drive and branch.

    Args:
        drive: Drive letter (single character, e.g. "F")
        branch: Branch name (e.g. "mainline", "cd_beta")

    Returns:
        Dict with keys matching _PATH_TEMPLATES, values are resolved path strings.
    """
    result = {}
    for key, template in _PATH_TEMPLATES.items():
        path = _apply_drive_letter(template, drive)
        path = _apply_branch(path, branch)
        result[key] = path
    return result


# =============================================================================
# Default Paths (drive + branch configurable via settings.json)
# =============================================================================

_default_paths = generate_default_paths(_DRIVE_LETTER, _BRANCH)

DEFAULT_FACTION_FOLDER = _default_paths['faction_folder']
DEFAULT_LOC_FOLDER = _default_paths['loc_folder']
DEFAULT_KNOWLEDGE_FOLDER = _default_paths['knowledge_folder']
DEFAULT_WAYPOINT_FOLDER = _default_paths['waypoint_folder']
DEFAULT_TEXTURE_FOLDER = _default_paths['texture_folder']
DEFAULT_CHARACTER_FOLDER = _default_paths['character_folder']
DEFAULT_AUDIO_FOLDER_EN = _default_paths['audio_folder']
DEFAULT_AUDIO_FOLDER_KR = _default_paths['audio_folder_kr']
DEFAULT_AUDIO_FOLDER_ZH = _default_paths['audio_folder_zh']
DEFAULT_EXPORT_FOLDER = _default_paths['export_folder']


# =============================================================================
# Lazy Language Loading Config
# =============================================================================

# Languages to load immediately (essential for startup)
PRELOAD_LANGUAGES = ['eng', 'kor']

# All other languages loaded on-demand when selected
LAZY_LANGUAGES = ['fre', 'ger', 'spa-es', 'spa-mx', 'por-br', 'ita', 'rus', 'tur', 'pol', 'zho-cn', 'zho-tw', 'jpn']


# =============================================================================
# Data Mode
# =============================================================================

DATA_MODES = ['map', 'character', 'item', 'audio']
DEFAULT_MODE = 'map'


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
THUMBNAIL_SIZE = (768, 768)  # Large display by default
MAX_INLINE_IMAGE_SIZE = (1024, 1024)  # Maximum display size before scaling


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
        'mode_map': 'MAP',
        'mode_character': 'CHARACTER',
        'mode_item': 'ITEM',
        'mode_audio': 'AUDIO',
        'event_name': 'Event Name',
        'script_line': 'Script Line',
        'script_line_kor': 'Script (KOR)',
        'script_line_eng': 'Script (ENG)',
        'duration': 'Duration',
        'play': 'Play',
        'stop': 'Stop',
        'cleanup': 'Cleanup',
        'audio_player': 'Audio Player',
        'character_folder': 'CharacterInfo Folder',
        'select_mode': 'Select Mode',
        'group': 'Group',
        'verified_entries': 'Verified Entries',
        'skipped_no_image': 'Skipped (no image)',
        'loading_language': 'Loading language...',
        # CHARACTER mode columns
        'use_macro': 'Race/Gender',
        'age': 'Age',
        'job': 'Job',
        # ITEM mode columns
        'string_id': 'StringID',
        # Cell copy feedback
        'copied': 'Copied',
        'selected_cell': 'Selected',
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
        'mode_map': '맵',
        'mode_character': '캐릭터',
        'mode_item': '아이템',
        'mode_audio': '오디오',
        'event_name': '이벤트명',
        'script_line': '스크립트 라인',
        'script_line_kor': '스크립트 (한국어)',
        'script_line_eng': '스크립트 (영어)',
        'duration': '길이',
        'play': '재생',
        'stop': '정지',
        'cleanup': '정리',
        'audio_player': '오디오 플레이어',
        'character_folder': '캐릭터 정보 폴더',
        'select_mode': '모드 선택',
        'group': '그룹',
        'verified_entries': '확인된 항목',
        'skipped_no_image': '건너뜀 (이미지 없음)',
        'loading_language': '언어 불러오는 중...',
        # CHARACTER mode columns
        'use_macro': '종족/성별',
        'age': '나이',
        'job': '직업',
        # ITEM mode columns
        'string_id': 'StringID',
        # Cell copy feedback
        'copied': '복사됨',
        'selected_cell': '선택됨',
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

    # Branch
    branch: str = 'mainline'

    # Paths (can be overridden)
    faction_folder: str = DEFAULT_FACTION_FOLDER
    loc_folder: str = DEFAULT_LOC_FOLDER
    knowledge_folder: str = DEFAULT_KNOWLEDGE_FOLDER
    waypoint_folder: str = DEFAULT_WAYPOINT_FOLDER
    texture_folder: str = DEFAULT_TEXTURE_FOLDER
    character_folder: str = DEFAULT_CHARACTER_FOLDER
    audio_folder: str = DEFAULT_AUDIO_FOLDER_EN
    export_folder: str = DEFAULT_EXPORT_FOLDER

    # Search settings
    search_limit: int = DEFAULT_SEARCH_LIMIT
    fuzzy_threshold: float = FUZZY_THRESHOLD

    # Current mode (map, character, item)
    current_mode: str = DEFAULT_MODE

    # Window state
    window_geometry: str = "1600x1000"

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
            branch=data.get('branch', 'mainline'),
            faction_folder=data.get('faction_folder', DEFAULT_FACTION_FOLDER),
            loc_folder=data.get('loc_folder', DEFAULT_LOC_FOLDER),
            knowledge_folder=data.get('knowledge_folder', DEFAULT_KNOWLEDGE_FOLDER),
            waypoint_folder=data.get('waypoint_folder', DEFAULT_WAYPOINT_FOLDER),
            texture_folder=data.get('texture_folder', DEFAULT_TEXTURE_FOLDER),
            character_folder=data.get('character_folder', DEFAULT_CHARACTER_FOLDER),
            audio_folder=data.get('audio_folder', DEFAULT_AUDIO_FOLDER_EN),
            export_folder=data.get('export_folder', DEFAULT_EXPORT_FOLDER),
            search_limit=data.get('search_limit', DEFAULT_SEARCH_LIMIT),
            fuzzy_threshold=data.get('fuzzy_threshold', FUZZY_THRESHOLD),
            current_mode=data.get('current_mode', DEFAULT_MODE),
            window_geometry=data.get('window_geometry', "1600x1000"),
        )


# =============================================================================
# Utility Functions
# =============================================================================

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
                log.info("Loaded settings from %s", settings_path)
        else:
            _current_settings = Settings()
            save_settings(_current_settings)
            log.info("Created default settings at %s", settings_path)
    except Exception as e:
        log.warning("Failed to load settings from %s: %s", settings_path, e)
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
        log.info("Saved settings to %s", settings_path)
        return True
    except Exception as e:
        log.error("Failed to save settings to %s: %s", settings_path, e)
        return False


def get_settings() -> Settings:
    """Get current settings, loading if necessary."""
    if _current_settings is None:
        return load_settings()
    return _current_settings


def update_branch(new_branch: str):
    """Update branch and recalculate all default paths. Called from GUI.

    Args:
        new_branch: Branch name (e.g., 'mainline', 'cd_beta').
    """
    global _BRANCH
    global DEFAULT_FACTION_FOLDER, DEFAULT_LOC_FOLDER, DEFAULT_KNOWLEDGE_FOLDER
    global DEFAULT_WAYPOINT_FOLDER, DEFAULT_TEXTURE_FOLDER, DEFAULT_CHARACTER_FOLDER
    global DEFAULT_AUDIO_FOLDER_EN, DEFAULT_AUDIO_FOLDER_KR, DEFAULT_AUDIO_FOLDER_ZH
    global DEFAULT_EXPORT_FOLDER

    _BRANCH = new_branch

    # Recalculate all default paths
    new_paths = generate_default_paths(_DRIVE_LETTER, _BRANCH)
    DEFAULT_FACTION_FOLDER = new_paths['faction_folder']
    DEFAULT_LOC_FOLDER = new_paths['loc_folder']
    DEFAULT_KNOWLEDGE_FOLDER = new_paths['knowledge_folder']
    DEFAULT_WAYPOINT_FOLDER = new_paths['waypoint_folder']
    DEFAULT_TEXTURE_FOLDER = new_paths['texture_folder']
    DEFAULT_CHARACTER_FOLDER = new_paths['character_folder']
    DEFAULT_AUDIO_FOLDER_EN = new_paths['audio_folder']
    DEFAULT_AUDIO_FOLDER_KR = new_paths['audio_folder_kr']
    DEFAULT_AUDIO_FOLDER_ZH = new_paths['audio_folder_zh']
    DEFAULT_EXPORT_FOLDER = new_paths['export_folder']

    # Update current settings
    settings = get_settings()
    settings.branch = new_branch
    settings.faction_folder = DEFAULT_FACTION_FOLDER
    settings.loc_folder = DEFAULT_LOC_FOLDER
    settings.knowledge_folder = DEFAULT_KNOWLEDGE_FOLDER
    settings.waypoint_folder = DEFAULT_WAYPOINT_FOLDER
    settings.texture_folder = DEFAULT_TEXTURE_FOLDER
    settings.character_folder = DEFAULT_CHARACTER_FOLDER
    settings.audio_folder = DEFAULT_AUDIO_FOLDER_EN
    settings.export_folder = DEFAULT_EXPORT_FOLDER
    save_settings(settings)

    log.info("Branch updated to: %s", new_branch)


def get_ui_text(key: str, language: Optional[str] = None) -> str:
    """Get UI text in the specified or current language."""
    if language is None:
        language = get_settings().ui_language

    lang_dict = UI_LANGUAGES.get(language, UI_LANGUAGES['English'])
    return lang_dict.get(key, UI_LANGUAGES['English'].get(key, key))
