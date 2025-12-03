"""
Unit Tests for QuickSearch Dictionary Module

Tests dictionary manager initialization and operations.
TRUE SIMULATION - no mocks, real file operations.
"""

import pytest
import sys
import tempfile
import shutil
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestDictionaryManagerInit:
    """Test DictionaryManager initialization."""

    def test_init_with_default_path(self):
        """DictionaryManager initializes with default path."""
        from server.tools.quicksearch.dictionary import DictionaryManager
        manager = DictionaryManager()
        assert manager is not None
        assert manager.base_dir is not None

    def test_init_with_custom_path(self):
        """DictionaryManager initializes with custom path."""
        from server.tools.quicksearch.dictionary import DictionaryManager
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = DictionaryManager(base_dir=tmpdir)
            assert manager.base_dir == Path(tmpdir)

    def test_init_creates_directory(self):
        """DictionaryManager creates base directory if needed."""
        from server.tools.quicksearch.dictionary import DictionaryManager
        with tempfile.TemporaryDirectory() as tmpdir:
            new_path = Path(tmpdir) / "new_dict_dir"
            manager = DictionaryManager(base_dir=str(new_path))
            assert new_path.exists()

    def test_init_state_is_empty(self):
        """Initial state has no loaded dictionaries."""
        from server.tools.quicksearch.dictionary import DictionaryManager
        manager = DictionaryManager()
        assert manager.current_dict is None
        assert manager.current_game is None
        assert manager.current_language is None
        assert manager.reference_dict is None


class TestDictionaryPath:
    """Test dictionary path generation."""

    def test_get_dictionary_path_format(self):
        """Dictionary path has correct format."""
        from server.tools.quicksearch.dictionary import DictionaryManager
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = DictionaryManager(base_dir=tmpdir)
            path = manager.get_dictionary_path("BDO", "EN")
            assert path == Path(tmpdir) / "BDO" / "EN" / "dictionary.pkl"

    def test_get_dictionary_path_creates_dirs(self):
        """get_dictionary_path creates intermediate directories."""
        from server.tools.quicksearch.dictionary import DictionaryManager
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = DictionaryManager(base_dir=tmpdir)
            path = manager.get_dictionary_path("BDM", "FR")
            # Directory should be created
            assert path.parent.exists()


class TestDictionaryExists:
    """Test dictionary existence checking."""

    def test_dictionary_exists_false_for_new(self):
        """dictionary_exists returns False for non-existent."""
        from server.tools.quicksearch.dictionary import DictionaryManager
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = DictionaryManager(base_dir=tmpdir)
            assert manager.dictionary_exists("BDO", "EN") is False

    def test_dictionary_exists_true_after_create(self):
        """dictionary_exists returns True after dictionary created."""
        from server.tools.quicksearch.dictionary import DictionaryManager
        import pickle

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = DictionaryManager(base_dir=tmpdir)
            # Create a dummy dictionary file
            path = manager.get_dictionary_path("BDO", "EN")
            with open(path, 'wb') as f:
                pickle.dump({'split_dict': {}, 'whole_dict': {}}, f)

            assert manager.dictionary_exists("BDO", "EN") is True


class TestGameAndLanguageConstants:
    """Test game and language constants."""

    def test_games_list_exists(self):
        """GAMES constant exists."""
        from server.tools.quicksearch.dictionary import GAMES
        assert isinstance(GAMES, list)
        assert len(GAMES) > 0

    def test_games_contains_expected(self):
        """GAMES contains expected game codes."""
        from server.tools.quicksearch.dictionary import GAMES
        assert 'BDO' in GAMES
        assert 'BDM' in GAMES
        assert 'BDC' in GAMES
        assert 'CD' in GAMES

    def test_languages_list_exists(self):
        """LANGUAGES constant exists."""
        from server.tools.quicksearch.dictionary import LANGUAGES
        assert isinstance(LANGUAGES, list)
        assert len(LANGUAGES) > 0

    def test_languages_contains_expected(self):
        """LANGUAGES contains expected language codes."""
        from server.tools.quicksearch.dictionary import LANGUAGES
        assert 'EN' in LANGUAGES
        assert 'FR' in LANGUAGES
        assert 'DE' in LANGUAGES
        assert 'JP' in LANGUAGES


class TestGetCurrentDictionary:
    """Test getting current dictionary."""

    def test_get_current_dictionary_initially_none(self):
        """get_current_dictionary returns None initially."""
        from server.tools.quicksearch.dictionary import DictionaryManager
        manager = DictionaryManager()
        assert manager.get_current_dictionary() is None

    def test_get_reference_dictionary_initially_none(self):
        """get_reference_dictionary returns None initially."""
        from server.tools.quicksearch.dictionary import DictionaryManager
        manager = DictionaryManager()
        assert manager.get_reference_dictionary() is None


class TestUnloadReference:
    """Test unloading reference dictionary."""

    def test_unload_reference_clears_state(self):
        """unload_reference clears reference state."""
        from server.tools.quicksearch.dictionary import DictionaryManager
        manager = DictionaryManager()
        # Set some reference data
        manager.reference_dict = {'test': 'data'}
        manager.reference_game = 'BDO'
        manager.reference_language = 'EN'

        manager.unload_reference()

        assert manager.reference_dict is None
        assert manager.reference_game is None
        assert manager.reference_language is None


class TestListAvailableDictionaries:
    """Test listing available dictionaries."""

    def test_list_empty_when_none_exist(self):
        """list_available_dictionaries returns empty list for empty dir."""
        from server.tools.quicksearch.dictionary import DictionaryManager
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = DictionaryManager(base_dir=tmpdir)
            result = manager.list_available_dictionaries()
            assert result == []

    def test_list_returns_list(self):
        """list_available_dictionaries returns a list."""
        from server.tools.quicksearch.dictionary import DictionaryManager
        manager = DictionaryManager()
        result = manager.list_available_dictionaries()
        assert isinstance(result, list)


class TestGetDictionaryInfo:
    """Test getting dictionary info."""

    def test_get_info_returns_none_for_nonexistent(self):
        """get_dictionary_info returns None for non-existent dictionary."""
        from server.tools.quicksearch.dictionary import DictionaryManager
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = DictionaryManager(base_dir=tmpdir)
            result = manager.get_dictionary_info("BDO", "EN")
            assert result is None

    def test_get_info_returns_dict_for_existing(self):
        """get_dictionary_info returns info dict for existing dictionary."""
        from server.tools.quicksearch.dictionary import DictionaryManager
        import pickle

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = DictionaryManager(base_dir=tmpdir)
            # Create a dummy dictionary
            path = manager.get_dictionary_path("BDO", "EN")
            with open(path, 'wb') as f:
                pickle.dump({
                    'split_dict': {'korean1': [('english1', 'id1')]},
                    'whole_dict': {},
                    'creation_date': '12/01 10:00'
                }, f)

            result = manager.get_dictionary_info("BDO", "EN")
            assert result is not None
            assert result['game'] == 'BDO'
            assert result['language'] == 'EN'
            assert 'pairs_count' in result
            assert 'file_size' in result


class TestLoadDictionary:
    """Test loading dictionaries."""

    def test_load_raises_for_nonexistent(self):
        """load_dictionary raises FileNotFoundError for non-existent."""
        from server.tools.quicksearch.dictionary import DictionaryManager
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = DictionaryManager(base_dir=tmpdir)
            with pytest.raises(FileNotFoundError):
                manager.load_dictionary("BDO", "EN")

    def test_load_sets_current_dictionary(self):
        """load_dictionary sets current_dict state."""
        from server.tools.quicksearch.dictionary import DictionaryManager
        import pickle

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = DictionaryManager(base_dir=tmpdir)
            # Create dictionary
            path = manager.get_dictionary_path("BDO", "EN")
            test_dict = {
                'split_dict': {'test': [('translation', 'id1')]},
                'whole_dict': {},
                'string_keys': {'split': [], 'whole': []},
                'creation_date': '12/01 10:00'
            }
            with open(path, 'wb') as f:
                pickle.dump(test_dict, f)

            manager.load_dictionary("BDO", "EN")

            assert manager.current_dict is not None
            assert manager.current_game == "BDO"
            assert manager.current_language == "EN"

    def test_load_as_reference(self):
        """load_dictionary with as_reference=True sets reference state."""
        from server.tools.quicksearch.dictionary import DictionaryManager
        import pickle

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = DictionaryManager(base_dir=tmpdir)
            # Create dictionary
            path = manager.get_dictionary_path("BDM", "FR")
            test_dict = {
                'split_dict': {},
                'whole_dict': {},
                'string_keys': {'split': [], 'whole': []},
                'creation_date': '12/01 10:00'
            }
            with open(path, 'wb') as f:
                pickle.dump(test_dict, f)

            manager.load_dictionary("BDM", "FR", as_reference=True)

            assert manager.reference_dict is not None
            assert manager.reference_game == "BDM"
            assert manager.reference_language == "FR"


class TestModuleExports:
    """Test module exports."""

    def test_dictionary_manager_importable(self):
        """DictionaryManager is importable."""
        from server.tools.quicksearch.dictionary import DictionaryManager
        assert DictionaryManager is not None

    def test_games_importable(self):
        """GAMES constant is importable."""
        from server.tools.quicksearch.dictionary import GAMES
        assert GAMES is not None

    def test_languages_importable(self):
        """LANGUAGES constant is importable."""
        from server.tools.quicksearch.dictionary import LANGUAGES
        assert LANGUAGES is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
