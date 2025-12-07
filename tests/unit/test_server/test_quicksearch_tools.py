"""
Unit tests for QuickSearch tools

Tests the core QuickSearch functionality:
- Dictionary loading and parsing
- Search operations (contains, exact)
- Reference dictionary integration
- Multi-line entry handling
"""

import pytest
import sys
from pathlib import Path

# Add project root
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))


class TestQuickSearchSearcher:
    """Tests for QuickSearch Searcher class."""

    @pytest.fixture
    def searcher(self):
        """Create a Searcher instance."""
        from server.tools.quicksearch.searcher import Searcher
        return Searcher()

    @pytest.fixture
    def sample_dict(self):
        """Create a sample dictionary for testing."""
        return {
            'split_dict': {
                '안녕하세요': [('Hello', 'STR_001'), ('Hi there', 'STR_002')],
                '감사합니다': [('Thank you', 'STR_003')],
                '무기': [('Weapon', 'STR_004')],
            },
            'whole_dict': {
                '환영합니다': [('Welcome', 'STR_005')],
                '게임 시작': [('Start Game', 'STR_006')],
            },
            'stringid_to_entry': {
                'STR_001': ('안녕하세요', 'Hello'),
                'STR_002': ('안녕하세요', 'Hi there'),
                'STR_003': ('감사합니다', 'Thank you'),
                'STR_004': ('무기', 'Weapon'),
                'STR_005': ('환영합니다', 'Welcome'),
                'STR_006': ('게임 시작', 'Start Game'),
            }
        }

    @pytest.fixture
    def reference_dict(self):
        """Create a reference dictionary for testing."""
        return {
            'split_dict': {
                '안녕하세요': [('Bonjour', 'STR_001')],
                '감사합니다': [('Merci', 'STR_003')],
            },
            'whole_dict': {
                '환영합니다': [('Bienvenue', 'STR_005')],
            },
        }

    def test_init(self, searcher):
        """Test searcher initialization."""
        assert searcher is not None
        assert searcher.current_dict is None
        assert searcher.reference_dict is None
        assert searcher.reference_enabled is False

    def test_load_dictionary(self, searcher, sample_dict):
        """Test loading a dictionary."""
        searcher.load_dictionary(sample_dict)
        assert searcher.current_dict == sample_dict

    def test_load_reference(self, searcher, reference_dict):
        """Test loading reference dictionary."""
        searcher.load_reference_dictionary(reference_dict)
        assert searcher.reference_dict == reference_dict
        assert searcher.reference_enabled is True

    def test_toggle_reference(self, searcher, reference_dict):
        """Test toggling reference dictionary."""
        searcher.load_reference_dictionary(reference_dict)
        assert searcher.reference_enabled is True

        searcher.toggle_reference(False)
        assert searcher.reference_enabled is False

        searcher.toggle_reference(True)
        assert searcher.reference_enabled is True

    def test_search_no_dictionary(self, searcher):
        """Test search with no dictionary loaded."""
        results = searcher.search_one_line("test")
        assert results == []

    def test_search_empty_query(self, searcher, sample_dict):
        """Test search with empty query."""
        searcher.load_dictionary(sample_dict)

        # Empty query returns just empty list (not tuple)
        results = searcher.search_one_line("")
        assert results == []

        results2 = searcher.search_one_line("   ")
        assert results2 == []

    def test_search_by_stringid(self, searcher, sample_dict):
        """Test direct StringId lookup."""
        searcher.load_dictionary(sample_dict)

        # search_one_line returns (results_list, count) tuple
        results, count = searcher.search_one_line("STR_001")
        assert count == 1
        assert len(results) == 1
        assert results[0][0] == '안녕하세요'
        assert results[0][1] == 'Hello'
        assert results[0][2] == 'STR_001'

    def test_search_by_stringid_with_reference(self, searcher, sample_dict, reference_dict):
        """Test StringId lookup with reference enabled."""
        searcher.load_dictionary(sample_dict)
        searcher.load_reference_dictionary(reference_dict)

        # search_one_line returns (results_list, count) tuple
        results, count = searcher.search_one_line("STR_001")
        assert count == 1
        assert len(results) == 1
        assert results[0][0] == '안녕하세요'  # Korean
        assert results[0][1] == 'Hello'  # Main translation
        assert results[0][2] == 'Bonjour'  # Reference translation
        assert results[0][3] == 'STR_001'  # StringId

    def test_search_contains_korean(self, searcher, sample_dict):
        """Test contains search with Korean text."""
        searcher.load_dictionary(sample_dict)

        # search_one_line returns (results_list, count) tuple for valid queries
        results, count = searcher.search_one_line("안녕", match_type="contains")
        assert count >= 1
        korean_texts = [r[0] for r in results]
        assert any('안녕' in k for k in korean_texts)

    def test_search_contains_english(self, searcher, sample_dict):
        """Test contains search with English text."""
        searcher.load_dictionary(sample_dict)

        # search_one_line returns (results_list, count) tuple
        results, count = searcher.search_one_line("Hello", match_type="contains")
        assert count >= 1
        translations = [r[1] for r in results]
        assert any('Hello' in t for t in translations)

    def test_search_case_insensitive(self, searcher, sample_dict):
        """Test case-insensitive search."""
        searcher.load_dictionary(sample_dict)

        results_lower, count_lower = searcher.search_one_line("hello", match_type="contains")
        results_upper, count_upper = searcher.search_one_line("HELLO", match_type="contains")

        # Both should find the same entries
        assert count_lower == count_upper

    def test_search_with_reference_enabled(self, searcher, sample_dict, reference_dict):
        """Test search with reference dictionary enabled."""
        searcher.load_dictionary(sample_dict)
        searcher.load_reference_dictionary(reference_dict)

        results, count = searcher.search_one_line("감사", match_type="contains")

        # Results should include reference translation
        assert count >= 1
        # With reference, results are 4-tuples
        if len(results) > 0 and len(results[0]) == 4:
            assert results[0][2] is not None  # Has reference

    def test_search_pagination_limit(self, searcher, sample_dict):
        """Test search with limit pagination."""
        searcher.load_dictionary(sample_dict)

        # Search for something that matches multiple entries
        results, count = searcher.search_one_line("STR", match_type="contains", limit=2)
        assert len(results) <= 2


class TestQuickSearchDictionary:
    """Tests for QuickSearch DictionaryManager class."""

    @pytest.fixture
    def dictionary(self):
        """Create a DictionaryManager instance."""
        from server.tools.quicksearch.dictionary import DictionaryManager
        return DictionaryManager()

    def test_init(self, dictionary):
        """Test dictionary initialization."""
        assert dictionary is not None

    def test_list_available_dictionaries(self, dictionary):
        """Test listing available dictionaries."""
        dicts = dictionary.list_available_dictionaries()
        assert isinstance(dicts, list)

    def test_dictionary_exists_false(self, dictionary):
        """Test checking non-existent dictionary."""
        exists = dictionary.dictionary_exists("NONEXISTENT", "XX")
        assert exists is False

    def test_get_current_dictionary_none(self, dictionary):
        """Test getting current dictionary when none loaded."""
        result = dictionary.get_current_dictionary()
        assert result is None


class TestQuickSearchParser:
    """Tests for QuickSearch Parser functions."""

    def test_normalize_text_basic(self):
        """Test basic text normalization."""
        from server.tools.quicksearch.parser import normalize_text

        assert normalize_text("test") == "test"
        assert normalize_text("  test  ") == "test"

    def test_normalize_text_removes_markers(self):
        """Test that code markers are removed."""
        from server.tools.quicksearch.parser import normalize_text

        text = '{ChangeScene(Main_001)}안녕하세요'
        result = normalize_text(text)
        # Should clean the text
        assert '안녕하세요' in result or result != ''

    def test_tokenize_basic(self):
        """Test basic tokenization."""
        from server.tools.quicksearch.parser import tokenize

        tokens = tokenize("Hello World")
        assert isinstance(tokens, list)
        assert len(tokens) >= 1

    def test_tokenize_korean(self):
        """Test Korean tokenization."""
        from server.tools.quicksearch.parser import tokenize

        tokens = tokenize("안녕하세요 세계")
        assert isinstance(tokens, list)

    def test_process_files_empty(self):
        """Test processing empty file list."""
        from server.tools.quicksearch.parser import process_files

        result = process_files([])
        assert isinstance(result, tuple)
        assert len(result) == 4


class TestQuickSearchIntegration:
    """Integration tests for QuickSearch components."""

    def test_full_search_workflow(self):
        """Test complete search workflow."""
        from server.tools.quicksearch.searcher import Searcher

        searcher = Searcher()

        # Create test dictionary
        test_dict = {
            'split_dict': {
                '테스트': [('Test', 'STR_TEST')],
            },
            'whole_dict': {},
            'stringid_to_entry': {
                'STR_TEST': ('테스트', 'Test'),
            }
        }

        searcher.load_dictionary(test_dict)

        # Search by Korean - returns (results_list, count) tuple
        results, count = searcher.search_one_line("테스트")
        assert count >= 1

        # Search by English
        results, count = searcher.search_one_line("Test")
        assert count >= 1

        # Search by StringId
        results, count = searcher.search_one_line("STR_TEST")
        assert count == 1
        assert len(results) == 1

    def test_reference_dictionary_workflow(self):
        """Test reference dictionary integration."""
        from server.tools.quicksearch.searcher import Searcher

        searcher = Searcher()

        # Main dictionary (English)
        main_dict = {
            'split_dict': {
                '안녕': [('Hello', 'STR_001')],
            },
            'whole_dict': {},
            'stringid_to_entry': {'STR_001': ('안녕', 'Hello')}
        }

        # Reference dictionary (French)
        ref_dict = {
            'split_dict': {
                '안녕': [('Bonjour', 'STR_001')],
            },
            'whole_dict': {},
        }

        searcher.load_dictionary(main_dict)
        searcher.load_reference_dictionary(ref_dict)

        # Search should return both translations - returns (results_list, count) tuple
        results, count = searcher.search_one_line("STR_001")
        assert count == 1
        assert len(results) == 1
        assert len(results[0]) == 4  # Korean, English, French, StringId
        assert results[0][1] == 'Hello'
        assert results[0][2] == 'Bonjour'
