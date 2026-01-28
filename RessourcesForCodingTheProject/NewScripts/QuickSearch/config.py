"""
QuickSearch Configuration Module

Constants, settings, and configuration management for the QuickSearch tool.
"""

import os
import sys
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass, field, asdict

# =============================================================================
# Application Constants
# =============================================================================

VERSION = "1.0.0"
APP_NAME = "QuickSearch"

# Available games and languages
GAMES = ['BDO', 'BDM', 'BDC', 'CD']
LANGUAGES = ['DE', 'IT', 'PL', 'EN', 'ES', 'SP', 'FR', 'ID', 'JP', 'PT', 'RU', 'TR', 'TH', 'TW', 'CH']

# File types
SUPPORTED_EXTENSIONS = ('.xml', '.txt', '.tsv')

# =============================================================================
# Source Base Constants
# =============================================================================

SOURCE_BASE_KR = "kr_base"
SOURCE_BASE_ENG = "eng_base"

# =============================================================================
# Default Settings
# =============================================================================

DEFAULT_FONT_FAMILY = 'Arial'
DEFAULT_FONT_SIZE = 10
DEFAULT_GLOSSARY_LENGTH = 15
DEFAULT_MIN_OCCURRENCE = 2

# Colors
DEFAULT_COLORS = {
    'korean': '#000000',
    'translation': '#000000',
    'reference': '#000000'
}

DEFAULT_STYLES = {
    'korean': '',
    'translation': '',
    'reference': ''
}


# =============================================================================
# UI Languages
# =============================================================================

UI_LANGUAGES = {
    'English': {
        'language_select': "Language Selection",
        'settings_title': "Settings",
        'create_dict': "Create Dictionary",
        'load_dict': "Load Dictionary",
        'reference_off': "REFERENCE OFF",
        'settings': "Settings",
        'search': "Search",
        'contains': "Contains",
        'exact_match': "Exact Match",
        'load_more': "Load More Results",
        'one_line': "One Line",
        'multi_line': "Multi Line",
        'source_base': "Source Base",
        'kr_base': "KR BASE - Korean StrOrigin as source (default)",
        'eng_base': "ENG BASE - English via StringID matching",
        'select_target': "Select Target XML/TXT Files",
        'select_eng': "Select English XML File (for ENG BASE)",
        'start_check': "Start Check",
        'line_check_title': "Line Check Configuration",
        'term_check_title': "Term Check Configuration",
        'source_data': "Source Data",
        'check_mode': "Check Mode",
        'self_check': "Source against Self",
        'external_check': "Source against External Glossary",
        'external_glossary': "External Glossary Data",
        'select_files': "Select Files",
        'select_folder': "Select Folder",
        'no_data_selected': "No data selected",
    },
    '한국어': {
        'language_select': "언어 선택",
        'settings_title': "설정",
        'create_dict': "사전 생성",
        'load_dict': "사전 불러오기",
        'reference_off': "참조 OFF",
        'settings': "설정",
        'search': "검색",
        'contains': "포함",
        'exact_match': "정확히 일치",
        'load_more': "더 보기",
        'one_line': "일반 검색",
        'multi_line': "멀티 검색",
        'source_base': "소스 기준",
        'kr_base': "KR BASE - 한국어 StrOrigin 사용 (기본값)",
        'eng_base': "ENG BASE - StringID로 영어 매칭",
        'select_target': "타겟 XML/TXT 파일 선택",
        'select_eng': "영어 XML 파일 선택 (ENG BASE용)",
        'start_check': "체크 시작",
        'line_check_title': "라인 체크 설정",
        'term_check_title': "용어 체크 설정",
        'source_data': "소스 데이터",
        'check_mode': "체크 모드",
        'self_check': "자체 데이터 체크",
        'external_check': "외부 글로서리 체크",
        'external_glossary': "외부 글로서리 데이터",
        'select_files': "파일 선택",
        'select_folder': "폴더 선택",
        'no_data_selected': "선택된 데이터 없음",
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
    colors: Dict[str, str] = field(default_factory=lambda: DEFAULT_COLORS.copy())
    styles: Dict[str, str] = field(default_factory=lambda: DEFAULT_STYLES.copy())
    glossary_length: int = DEFAULT_GLOSSARY_LENGTH
    min_occurrence: int = DEFAULT_MIN_OCCURRENCE
    filter_sentences: bool = True

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
            colors=data.get('colors', DEFAULT_COLORS.copy()),
            styles=data.get('styles', DEFAULT_STYLES.copy()),
            glossary_length=data.get('glossary_length', DEFAULT_GLOSSARY_LENGTH),
            min_occurrence=data.get('min_occurrence', DEFAULT_MIN_OCCURRENCE),
            filter_sentences=data.get('filter_sentences', True),
        )


# =============================================================================
# Utility Functions
# =============================================================================

def get_base_dir() -> str:
    """Get the base directory for the application."""
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller EXE
        return os.path.dirname(sys.executable)
    else:
        # Running as script
        return os.path.dirname(os.path.abspath(__file__))


def get_settings_path() -> str:
    """Get the path to the settings file."""
    return os.path.join(get_base_dir(), 'qs_settings.json')


def get_dict_dir() -> str:
    """Get the directory for dictionary files."""
    dict_dir = os.path.join(get_base_dir(), 'dictionaries')
    os.makedirs(dict_dir, exist_ok=True)
    return dict_dir


def get_output_dir() -> str:
    """Get the directory for output files."""
    output_dir = os.path.join(get_base_dir(), 'output')
    os.makedirs(output_dir, exist_ok=True)
    return output_dir


# =============================================================================
# Settings Management
# =============================================================================

_current_settings: Optional[Settings] = None


def load_settings() -> Settings:
    """Load settings from file or create defaults."""
    global _current_settings

    settings_path = get_settings_path()

    try:
        if os.path.exists(settings_path):
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
            json.dump(settings.to_dict(), f, indent=2)
        return True
    except Exception:
        return False


def get_settings() -> Settings:
    """Get current settings, loading if necessary."""
    global _current_settings
    if _current_settings is None:
        return load_settings()
    return _current_settings


def get_ui_text(key: str, language: Optional[str] = None) -> str:
    """Get UI text in the specified or current language."""
    if language is None:
        language = get_settings().ui_language

    lang_dict = UI_LANGUAGES.get(language, UI_LANGUAGES['English'])
    return lang_dict.get(key, UI_LANGUAGES['English'].get(key, key))
