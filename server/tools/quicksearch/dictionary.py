"""
QuickSearch Dictionary Manager

Handles dictionary creation, loading, saving, and management.
"""

import pickle
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from loguru import logger

from . import parser


# Available games and languages
GAMES = ['BDO', 'BDM', 'BDC', 'CD']
LANGUAGES = ['DE', 'IT', 'PL', 'EN', 'ES', 'SP', 'FR', 'ID', 'JP', 'PT', 'RU', 'TR', 'TH', 'TW', 'CH']


class DictionaryManager:
    """
    Manages QuickSearch dictionaries.

    Handles:
    - Creating dictionaries from files
    - Loading existing dictionaries
    - Saving dictionaries to disk
    - Listing available dictionaries
    """

    def __init__(self, base_dir: str = "server/data/quicksearch_dictionaries"):
        """
        Initialize dictionary manager.

        Args:
            base_dir: Base directory for storing dictionaries
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

        # Currently loaded dictionary
        self.current_dict = None
        self.current_game = None
        self.current_language = None

        # Reference dictionary (optional)
        self.reference_dict = None
        self.reference_game = None
        self.reference_language = None

        logger.info(f"DictionaryManager initialized with base_dir={self.base_dir}")

    def get_dictionary_path(self, game: str, language: str) -> Path:
        """
        Get path to dictionary file for a game/language combination.

        Args:
            game: Game code (BDO, BDM, BDC, CD)
            language: Language code (EN, FR, etc.)

        Returns:
            Path to dictionary pickle file
        """
        dict_dir = self.base_dir / game / language
        dict_dir.mkdir(parents=True, exist_ok=True)
        return dict_dir / "dictionary.pkl"

    def create_dictionary(
        self,
        file_paths: List[str],
        game: str,
        language: str
    ) -> Tuple[Dict, Dict, Dict]:
        """
        Create dictionary from files.

        Args:
            file_paths: List of file paths to process
            game: Game code (BDO, BDM, BDC, CD)
            language: Language code (EN, FR, etc.)

        Returns:
            Tuple of (split_dict, whole_dict, string_keys, stringid_to_entry)
        """
        logger.info(f"Creating dictionary for {game}-{language} from {len(file_paths)} files")

        # Process files
        split_dict, whole_dict, string_keys, stringid_to_entry = parser.process_files(file_paths)

        # Add creation date
        creation_date = datetime.now().strftime("%m/%d %H:%M")

        # Package dictionary (EXACT SAME FORMAT as original QuickSearch0818.py)
        dictionary = {
            'split_dict': split_dict,
            'whole_dict': whole_dict,
            'string_keys': string_keys,  # Preserve original format
            'creation_date': creation_date
        }

        # Save dictionary
        dict_path = self.get_dictionary_path(game, language)
        with open(dict_path, 'wb') as f:
            pickle.dump(dictionary, f)

        logger.success(f"Dictionary saved: {dict_path}")
        logger.success(f"Split pairs: {len(split_dict)}, Whole pairs: {len(whole_dict)}, Total: {len(split_dict) + len(whole_dict)}")

        return split_dict, whole_dict, string_keys, stringid_to_entry

    def load_dictionary(
        self,
        game: str,
        language: str,
        as_reference: bool = False
    ) -> Dict:
        """
        Load dictionary from disk.

        Args:
            game: Game code (BDO, BDM, BDC, CD)
            language: Language code (EN, FR, etc.)
            as_reference: Load as reference dictionary (default: False)

        Returns:
            Dictionary object with split_dict, whole_dict, etc.

        Raises:
            FileNotFoundError: If dictionary doesn't exist
        """
        dict_path = self.get_dictionary_path(game, language)

        if not dict_path.exists():
            raise FileNotFoundError(f"Dictionary not found: {game}-{language} at {dict_path}")

        logger.info(f"Loading dictionary: {game}-{language} from {dict_path}")

        with open(dict_path, 'rb') as f:
            dictionary = pickle.load(f)

        if as_reference:
            self.reference_dict = dictionary
            self.reference_game = game
            self.reference_language = language
            logger.success(f"Reference dictionary loaded: {game}-{language}")
        else:
            self.current_dict = dictionary
            self.current_game = game
            self.current_language = language
            logger.success(f"Main dictionary loaded: {game}-{language}")

        # Also load stringid_to_entry if not present (for backward compatibility)
        if 'stringid_to_entry' not in dictionary:
            # Rebuild from string_keys if available
            string_keys = dictionary.get('string_keys', {})
            stringid_to_entry = {}
            for korean, string_id in string_keys.get('split', []):
                if string_id and korean in dictionary['split_dict']:
                    for translation, sid in dictionary['split_dict'][korean]:
                        if sid == string_id:
                            stringid_to_entry[string_id] = (korean, translation)
                            break
            for korean, string_id in string_keys.get('whole', []):
                if string_id and korean in dictionary['whole_dict']:
                    for translation, sid in dictionary['whole_dict'][korean]:
                        if sid == string_id:
                            stringid_to_entry[string_id] = (korean, translation)
                            break
            dictionary['stringid_to_entry'] = stringid_to_entry

        pairs_count = len(dictionary.get('split_dict', {})) + len(dictionary.get('whole_dict', {}))
        logger.info(f"Dictionary contains {pairs_count} total pairs")

        return dictionary

    def dictionary_exists(self, game: str, language: str) -> bool:
        """
        Check if dictionary exists for a game/language combination.

        Args:
            game: Game code (BDO, BDM, BDC, CD)
            language: Language code (EN, FR, etc.)

        Returns:
            True if dictionary exists, False otherwise
        """
        dict_path = self.get_dictionary_path(game, language)
        return dict_path.exists()

    def list_available_dictionaries(self) -> List[Dict]:
        """
        List all available dictionaries.

        Returns:
            List of dictionary info dicts with:
            - game
            - language
            - creation_date
            - pairs_count
            - file_size
        """
        dictionaries = []

        for game in GAMES:
            for language in LANGUAGES:
                dict_path = self.get_dictionary_path(game, language)

                if dict_path.exists():
                    try:
                        # Load dictionary to get metadata
                        with open(dict_path, 'rb') as f:
                            dictionary = pickle.load(f)

                        pairs_count = len(dictionary.get('split_dict', {})) + len(dictionary.get('whole_dict', {}))
                        file_size = dict_path.stat().st_size

                        dictionaries.append({
                            'game': game,
                            'language': language,
                            'creation_date': dictionary.get('creation_date', 'Unknown'),
                            'pairs_count': pairs_count,
                            'file_size': file_size
                        })
                    except Exception as e:
                        logger.warning(f"Failed to load dictionary {game}-{language}: {e}")

        logger.info(f"Found {len(dictionaries)} available dictionaries")
        return dictionaries

    def get_current_dictionary(self) -> Optional[Dict]:
        """
        Get currently loaded main dictionary.

        Returns:
            Current dictionary or None
        """
        return self.current_dict

    def get_reference_dictionary(self) -> Optional[Dict]:
        """
        Get currently loaded reference dictionary.

        Returns:
            Reference dictionary or None
        """
        return self.reference_dict

    def unload_reference(self):
        """Unload reference dictionary."""
        self.reference_dict = None
        self.reference_game = None
        self.reference_language = None
        logger.info("Reference dictionary unloaded")

    def get_dictionary_info(self, game: str, language: str) -> Optional[Dict]:
        """
        Get info about a specific dictionary without loading it.

        Args:
            game: Game code
            language: Language code

        Returns:
            Dictionary info or None if doesn't exist
        """
        if not self.dictionary_exists(game, language):
            return None

        dict_path = self.get_dictionary_path(game, language)

        try:
            with open(dict_path, 'rb') as f:
                dictionary = pickle.load(f)

            pairs_count = len(dictionary.get('split_dict', {})) + len(dictionary.get('whole_dict', {}))

            return {
                'game': game,
                'language': language,
                'creation_date': dictionary.get('creation_date', 'Unknown'),
                'pairs_count': pairs_count,
                'file_size': dict_path.stat().st_size
            }
        except Exception as e:
            logger.error(f"Failed to get dictionary info for {game}-{language}: {e}")
            return None
