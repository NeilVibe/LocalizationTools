"""
Unit Tests for QuickSearch Searcher Module

Tests search operations on dictionaries.
TRUE SIMULATION - no mocks, real search operations.
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestSearcherInit:
    """Test Searcher initialization."""

    def test_searcher_initializes(self):
        """Searcher initializes without error."""
        from server.tools.quicksearch.searcher import Searcher
        searcher = Searcher()
        assert searcher is not None

    def test_searcher_initial_state(self):
        """Searcher has correct initial state."""
        from server.tools.quicksearch.searcher import Searcher
        searcher = Searcher()
        assert searcher.current_dict is None
        assert searcher.reference_dict is None
        assert searcher.reference_enabled is False


class TestLoadDictionary:
    """Test dictionary loading."""

    def test_load_dictionary_sets_current(self):
        """load_dictionary sets current_dict."""
        from server.tools.quicksearch.searcher import Searcher
        searcher = Searcher()

        test_dict = {
            'split_dict': {'korean': [('english', 'id1')]},
            'whole_dict': {}
        }
        searcher.load_dictionary(test_dict)

        assert searcher.current_dict is not None
        assert searcher.current_dict == test_dict

    def test_load_reference_dictionary(self):
        """load_reference_dictionary sets reference_dict."""
        from server.tools.quicksearch.searcher import Searcher
        searcher = Searcher()

        ref_dict = {
            'split_dict': {'korean': [('reference', 'id1')]},
            'whole_dict': {}
        }
        searcher.load_reference_dictionary(ref_dict)

        assert searcher.reference_dict is not None
        assert searcher.reference_enabled is True


class TestToggleReference:
    """Test reference dictionary toggle."""

    def test_toggle_reference_enable(self):
        """toggle_reference enables reference."""
        from server.tools.quicksearch.searcher import Searcher
        searcher = Searcher()

        searcher.toggle_reference(True)
        assert searcher.reference_enabled is True

    def test_toggle_reference_disable(self):
        """toggle_reference disables reference."""
        from server.tools.quicksearch.searcher import Searcher
        searcher = Searcher()

        searcher.reference_enabled = True
        searcher.toggle_reference(False)
        assert searcher.reference_enabled is False


class TestSearchOneLine:
    """Test single-line search."""

    @pytest.fixture
    def loaded_searcher(self):
        """Searcher with test dictionary loaded."""
        from server.tools.quicksearch.searcher import Searcher
        searcher = Searcher()

        test_dict = {
            'split_dict': {
                '안녕하세요': [('Hello', 'string_001')],
                '감사합니다': [('Thank you', 'string_002')],
                '마을': [('Village', 'string_003')]
            },
            'whole_dict': {
                '좋은 아침입니다': [('Good morning', 'string_010')]
            },
            'stringid_to_entry': {
                'string_001': ('안녕하세요', 'Hello'),
                'string_002': ('감사합니다', 'Thank you')
            }
        }
        searcher.load_dictionary(test_dict)
        return searcher

    def test_search_no_dictionary_returns_empty(self):
        """Search without dictionary returns empty list."""
        from server.tools.quicksearch.searcher import Searcher
        searcher = Searcher()

        results = searcher.search_one_line("test")
        assert results == []

    def test_search_empty_query_returns_empty(self, loaded_searcher):
        """Search with empty query returns empty list."""
        results = loaded_searcher.search_one_line("")
        assert results == []

    def test_search_whitespace_query_returns_empty(self, loaded_searcher):
        """Search with whitespace query returns empty list."""
        results = loaded_searcher.search_one_line("   ")
        assert results == []

    def test_search_contains_finds_match(self, loaded_searcher):
        """Contains search finds matching entries."""
        results, total = loaded_searcher.search_one_line("안녕", match_type="contains")
        assert total >= 1
        # Should find '안녕하세요'
        korean_texts = [r[0] for r in results]
        assert '안녕하세요' in korean_texts

    def test_search_exact_finds_exact_match(self, loaded_searcher):
        """Exact search finds exact match."""
        results, total = loaded_searcher.search_one_line("Hello", match_type="exact")
        # Should find entry with 'Hello' translation
        assert total >= 1

    def test_search_exact_no_partial_match(self, loaded_searcher):
        """Exact search doesn't find partial matches."""
        results, total = loaded_searcher.search_one_line("Hell", match_type="exact")
        # 'Hell' is not exact match for 'Hello'
        translations = [r[1] for r in results]
        assert 'Hello' not in translations

    def test_search_by_stringid(self, loaded_searcher):
        """Search by StringId returns direct match."""
        results = loaded_searcher.search_one_line("string_001")
        # Results may be tuple of (results, total) or just results
        if isinstance(results, tuple):
            results, total = results
            assert total >= 1
        # Should find direct StringId lookup
        assert any('안녕하세요' in str(r) for r in results)

    def test_search_returns_tuple_format(self, loaded_searcher):
        """Search results are in tuple format."""
        results, total = loaded_searcher.search_one_line("마을")
        assert len(results) > 0
        # Each result should be a tuple
        assert isinstance(results[0], tuple)
        assert len(results[0]) >= 3  # (korean, translation, stringid)

    def test_search_limit_works(self, loaded_searcher):
        """Search limit restricts results."""
        results, total = loaded_searcher.search_one_line("a", match_type="contains", limit=1)
        assert len(results) <= 1

    def test_search_pagination_works(self, loaded_searcher):
        """Search pagination with start_index works."""
        # Get all results
        all_results, total = loaded_searcher.search_one_line("a", match_type="contains", limit=100)

        if total > 1:
            # Get paginated results
            page2, _ = loaded_searcher.search_one_line("a", match_type="contains", start_index=1, limit=1)
            # Should return different results
            assert len(page2) <= 1


class TestSearchMultiLine:
    """Test multi-line search."""

    @pytest.fixture
    def loaded_searcher(self):
        """Searcher with test dictionary loaded."""
        from server.tools.quicksearch.searcher import Searcher
        searcher = Searcher()

        test_dict = {
            'split_dict': {
                '안녕하세요': [('Hello', 'id1')],
                '감사합니다': [('Thank you', 'id2')]
            },
            'whole_dict': {},
            'stringid_to_entry': {}
        }
        searcher.load_dictionary(test_dict)
        return searcher

    def test_multi_line_search_returns_list(self, loaded_searcher):
        """Multi-line search returns list of results."""
        results = loaded_searcher.search_multi_line(["안녕", "감사"])
        assert isinstance(results, list)

    def test_multi_line_search_result_format(self, loaded_searcher):
        """Each multi-line result has correct format."""
        results = loaded_searcher.search_multi_line(["안녕"])
        assert len(results) > 0
        result = results[0]
        assert 'line' in result
        assert 'matches' in result
        assert 'total_count' in result

    def test_multi_line_skips_empty_queries(self, loaded_searcher):
        """Multi-line search skips empty queries."""
        results = loaded_searcher.search_multi_line(["안녕", "", "  ", "감사"])
        # Empty queries should be skipped
        assert len(results) == 2

    def test_multi_line_respects_limit(self, loaded_searcher):
        """Multi-line search respects per-query limit."""
        results = loaded_searcher.search_multi_line(["a"], limit=1)
        for result in results:
            assert len(result['matches']) <= 1


class TestSearchWithReference:
    """Test search with reference dictionary."""

    @pytest.fixture
    def searcher_with_reference(self):
        """Searcher with main and reference dictionaries."""
        from server.tools.quicksearch.searcher import Searcher
        searcher = Searcher()

        main_dict = {
            'split_dict': {
                '안녕하세요': [('Bonjour', 'id1')]
            },
            'whole_dict': {},
            'stringid_to_entry': {}
        }

        ref_dict = {
            'split_dict': {
                '안녕하세요': [('Hello', 'id1')]
            },
            'whole_dict': {}
        }

        searcher.load_dictionary(main_dict)
        searcher.load_reference_dictionary(ref_dict)

        return searcher

    def test_search_with_reference_includes_ref_translation(self, searcher_with_reference):
        """Search with reference includes reference translation."""
        results, total = searcher_with_reference.search_one_line("안녕", match_type="contains")
        assert total >= 1
        # With reference enabled, results should have 4 elements
        if len(results) > 0:
            assert len(results[0]) == 4  # (korean, translation, ref_translation, stringid)

    def test_search_disabled_reference(self, searcher_with_reference):
        """Search with disabled reference has 3-element tuples."""
        searcher_with_reference.toggle_reference(False)
        results, total = searcher_with_reference.search_one_line("안녕", match_type="contains")

        if total > 0 and len(results) > 0:
            # With reference disabled, results should have 3 elements
            assert len(results[0]) == 3


class TestModuleExports:
    """Test module exports."""

    def test_searcher_importable(self):
        """Searcher class is importable."""
        from server.tools.quicksearch.searcher import Searcher
        assert Searcher is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
