"""
Dictionary Module

Dictionary creation, loading, and management for QuickSearch.
"""

import os
import pickle
from typing import List, Dict, Optional, Tuple, Callable
from dataclasses import dataclass, field

try:
    from core.xml_parser import parse_multiple_files, LocStrEntry
    from utils.language_utils import normalize_text, tokenize
    from config import get_dict_dir, GAMES, LANGUAGES
except ImportError:
    from .xml_parser import parse_multiple_files, LocStrEntry
    from ..utils.language_utils import normalize_text, tokenize
    from ..config import get_dict_dir, GAMES, LANGUAGES


@dataclass
class Dictionary:
    """A search dictionary with split and whole entries."""
    game: str
    language: str
    split_dict: Dict[str, List[Tuple[str, str]]] = field(default_factory=dict)
    whole_dict: Dict[str, List[Tuple[str, str]]] = field(default_factory=dict)
    stringid_lookup: Dict[str, Tuple[str, str]] = field(default_factory=dict)

    @property
    def total_entries(self) -> int:
        split_count = sum(len(v) for v in self.split_dict.values())
        whole_count = sum(len(v) for v in self.whole_dict.values())
        return split_count + whole_count

    @property
    def unique_sources(self) -> int:
        return len(self.split_dict) + len(self.whole_dict)


class DictionaryManager:
    """Manages multiple dictionaries."""

    def __init__(self):
        self.dictionaries: Dict[str, Dict[str, str]] = {game: {} for game in GAMES}
        self.active_dict: Optional[Tuple[str, str]] = None
        self.reference_dict: Optional[Tuple[str, str]] = None
        self._loaded_dicts: Dict[Tuple[str, str], Dictionary] = {}

    def scan_dictionaries(self) -> None:
        """Scan dictionary directory for available dictionaries."""
        dict_dir = get_dict_dir()

        for game in GAMES:
            self.dictionaries[game] = {}
            for lang in LANGUAGES:
                dict_path = os.path.join(dict_dir, f"{game}_{lang}.pkl")
                if os.path.exists(dict_path):
                    self.dictionaries[game][lang] = dict_path

    def get_available(self, game: str) -> List[str]:
        """Get available languages for a game."""
        return list(self.dictionaries.get(game, {}).keys())

    def load(self, game: str, lang: str) -> Optional[Dictionary]:
        """Load a dictionary."""
        key = (game, lang)

        if key in self._loaded_dicts:
            return self._loaded_dicts[key]

        dict_path = self.dictionaries.get(game, {}).get(lang)
        if not dict_path or not os.path.exists(dict_path):
            return None

        try:
            with open(dict_path, 'rb') as f:
                data = pickle.load(f)

            dictionary = Dictionary(
                game=game,
                language=lang,
                split_dict=data.get('split_dict', {}),
                whole_dict=data.get('whole_dict', {}),
                stringid_lookup=data.get('stringid_lookup', {})
            )

            self._loaded_dicts[key] = dictionary
            return dictionary

        except Exception:
            return None

    def set_active(self, game: str, lang: str) -> bool:
        """Set the active dictionary."""
        if self.load(game, lang):
            self.active_dict = (game, lang)
            return True
        return False

    def set_reference(self, game: str, lang: str) -> bool:
        """Set the reference dictionary."""
        if self.load(game, lang):
            self.reference_dict = (game, lang)
            return True
        return False

    def get_active(self) -> Optional[Dictionary]:
        """Get the active dictionary."""
        if self.active_dict:
            return self._loaded_dicts.get(self.active_dict)
        return None

    def get_reference(self) -> Optional[Dictionary]:
        """Get the reference dictionary."""
        if self.reference_dict:
            return self._loaded_dicts.get(self.reference_dict)
        return None

    def clear_reference(self) -> None:
        """Clear the reference dictionary."""
        self.reference_dict = None


def create_dictionary(
    source_files: List[str],
    game: str,
    language: str,
    progress_callback: Optional[Callable[[str], None]] = None
) -> Optional[Dictionary]:
    """
    Create a dictionary from source files.

    Args:
        source_files: List of XML/TXT files
        game: Game identifier (BDO, BDM, etc.)
        language: Language code (FR, DE, etc.)
        progress_callback: Optional callback for progress updates

    Returns:
        Dictionary object if successful
    """
    if progress_callback:
        progress_callback("Parsing source files...")

    # Parse files
    def progress_wrapper(msg: str, current: int, total: int):
        if progress_callback:
            progress_callback(f"{msg} ({current}/{total})")

    entries = parse_multiple_files(source_files, progress_wrapper)

    if not entries:
        return None

    if progress_callback:
        progress_callback(f"Processing {len(entries)} entries...")

    # Build dictionaries
    split_dict: Dict[str, List[Tuple[str, str]]] = {}
    whole_dict: Dict[str, List[Tuple[str, str]]] = {}
    stringid_lookup: Dict[str, Tuple[str, str]] = {}

    for entry in entries:
        ko = entry.str_origin
        fr = entry.str
        sid = entry.string_id

        if not ko or not fr:
            continue

        # Try to tokenize (split by newlines)
        ko_tokens = tokenize(ko)
        fr_tokens = tokenize(fr)

        if ko_tokens and len(ko_tokens) == len(fr_tokens):
            # Split entries
            for k_tok, f_tok in zip(ko_tokens, fr_tokens):
                if k_tok not in split_dict:
                    split_dict[k_tok] = []
                split_dict[k_tok].append((f_tok, sid))

                if sid:
                    stringid_lookup[sid] = (k_tok, f_tok)
        else:
            # Whole entries
            if ko not in whole_dict:
                whole_dict[ko] = []
            whole_dict[ko].append((fr, sid))

            if sid:
                stringid_lookup[sid] = (ko, fr)

    dictionary = Dictionary(
        game=game,
        language=language,
        split_dict=split_dict,
        whole_dict=whole_dict,
        stringid_lookup=stringid_lookup
    )

    if progress_callback:
        progress_callback(f"Created dictionary: {dictionary.unique_sources} unique sources")

    return dictionary


def save_dictionary(dictionary: Dictionary, output_path: Optional[str] = None) -> bool:
    """
    Save a dictionary to disk.

    Args:
        dictionary: Dictionary to save
        output_path: Optional custom path (default: dict_dir/GAME_LANG.pkl)

    Returns:
        True if successful
    """
    if output_path is None:
        dict_dir = get_dict_dir()
        output_path = os.path.join(dict_dir, f"{dictionary.game}_{dictionary.language}.pkl")

    try:
        data = {
            'split_dict': dictionary.split_dict,
            'whole_dict': dictionary.whole_dict,
            'stringid_lookup': dictionary.stringid_lookup
        }

        with open(output_path, 'wb') as f:
            pickle.dump(data, f)

        return True
    except Exception:
        return False


def load_dictionary(
    game: str,
    language: str,
    dict_path: Optional[str] = None
) -> Optional[Dictionary]:
    """
    Load a dictionary from disk.

    Args:
        game: Game identifier
        language: Language code
        dict_path: Optional custom path

    Returns:
        Dictionary object if successful
    """
    if dict_path is None:
        dict_dir = get_dict_dir()
        dict_path = os.path.join(dict_dir, f"{game}_{language}.pkl")

    if not os.path.exists(dict_path):
        return None

    try:
        with open(dict_path, 'rb') as f:
            data = pickle.load(f)

        return Dictionary(
            game=game,
            language=language,
            split_dict=data.get('split_dict', {}),
            whole_dict=data.get('whole_dict', {}),
            stringid_lookup=data.get('stringid_lookup', {})
        )
    except Exception:
        return None
