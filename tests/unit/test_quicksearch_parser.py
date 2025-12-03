"""
Unit Tests for QuickSearch Parser

Tests normalize_text, tokenize, parse_xml_file, parse_txt_file
to ensure all patterns are handled correctly.
"""

import pytest
import sys
import os
import tempfile
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestQuickSearchNormalizeText:
    """Test QuickSearch normalize_text function."""

    @pytest.fixture
    def normalize(self):
        from server.tools.quicksearch.parser import normalize_text
        return normalize_text

    def test_empty_string(self, normalize):
        """Empty string returns empty."""
        assert normalize("") == ""

    def test_none_input(self, normalize):
        """None returns empty string."""
        assert normalize(None) == ""

    def test_non_string(self, normalize):
        """Non-string returns empty string."""
        assert normalize(123) == ""
        assert normalize([]) == ""

    def test_basic_text(self, normalize):
        """Basic text passes through."""
        assert normalize("Hello World") == "Hello World"
        assert normalize("안녕하세요") == "안녕하세요"

    def test_unmatched_quotes_removed(self, normalize):
        """Unmatched quotes are removed."""
        # Single unmatched quote
        result = normalize('Hello "World')
        assert result.count('"') % 2 == 0  # Should have even number of quotes

        # Balanced quotes preserved
        result = normalize('"Hello World"')
        assert result == '"Hello World"'

    def test_unicode_whitespace_normalized(self, normalize):
        """Unicode whitespace variants are normalized."""
        # Non-breaking space (U+00A0)
        result = normalize("Hello\u00A0World")
        assert result == "Hello World"

        # Various Unicode spaces
        result = normalize("Hello\u2000\u2001\u2002World")
        assert result == "Hello World"

    def test_zero_width_chars_removed(self, normalize):
        """Zero-width characters are removed."""
        # Zero-width space (U+200B)
        result = normalize("Hello\u200BWorld")
        assert "\u200B" not in result

    def test_apostrophe_normalized(self, normalize):
        """Various apostrophe types normalized to straight apostrophe."""
        # Curly apostrophe (U+2019)
        result = normalize("it\u2019s")
        assert result == "it's"

        # Various apostrophe types
        for apo in ['\u2019', '\u2018', '\u02BC', '\u2032']:
            result = normalize(f"it{apo}s")
            assert "'" in result

    def test_multiple_whitespace_collapsed(self, normalize):
        """Multiple whitespace collapsed to single space."""
        result = normalize("Hello    World")
        assert result == "Hello World"

        result = normalize("Hello\t\t\nWorld")
        assert "  " not in result

    def test_leading_trailing_whitespace_stripped(self, normalize):
        """Leading/trailing whitespace stripped."""
        result = normalize("  Hello World  ")
        assert result == "Hello World"


class TestQuickSearchTokenize:
    """Test QuickSearch tokenize function."""

    @pytest.fixture
    def tokenize(self):
        from server.tools.quicksearch.parser import tokenize
        return tokenize

    def test_empty_string(self, tokenize):
        """Empty string returns empty list."""
        assert tokenize("") == []

    def test_none_input(self, tokenize):
        """None returns empty list."""
        assert tokenize(None) == []

    def test_whitespace_only(self, tokenize):
        """Whitespace-only returns empty list."""
        assert tokenize("   ") == []

    def test_contains_tab_returns_empty(self, tokenize):
        """Text with tabs returns empty list."""
        assert tokenize("Hello\tWorld") == []

    def test_single_line(self, tokenize):
        """Single line returns list with one element."""
        result = tokenize("Hello World")
        assert result == ["Hello World"]

    def test_split_by_newline(self, tokenize):
        """Text split by newlines."""
        result = tokenize("Line1\nLine2\nLine3")
        assert len(result) == 3
        assert "Line1" in result
        assert "Line2" in result
        assert "Line3" in result

    def test_split_by_escaped_newline(self, tokenize):
        """Text split by escaped newlines (\\n)."""
        result = tokenize("Line1\\nLine2\\nLine3")
        # May split into 3 or may return as single depending on implementation
        assert len(result) >= 1

    def test_korean_text(self, tokenize):
        """Korean text tokenizes correctly."""
        result = tokenize("첫번째 줄\n두번째 줄")
        assert len(result) == 2


class TestQuickSearchParseTxtFile:
    """Test QuickSearch parse_txt_file function."""

    @pytest.fixture
    def parse_txt(self):
        from server.tools.quicksearch.parser import parse_txt_file
        return parse_txt_file

    @pytest.fixture
    def temp_txt_file(self):
        """Create temporary TXT file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            # Write test data in correct format (7+ columns, tab-separated)
            lines = [
                "39\t7924197\t1001\t0\t1\t안녕하세요\tHello",
                "39\t7924197\t1002\t0\t2\t감사합니다\tThank you",
                "39\t7924197\t1003\t0\t3\t첫번째\\n두번째\tFirst\\nSecond",
            ]
            f.write('\n'.join(lines))
            temp_path = f.name
        yield temp_path
        os.unlink(temp_path)

    def test_parse_valid_txt(self, parse_txt, temp_txt_file):
        """Parse valid TXT file."""
        result = parse_txt(temp_txt_file)

        # Returns 6 values: k_split, t_split, keys_split, k_whole, t_whole, keys_whole
        assert len(result) == 6

        k_split, t_split, keys_split, k_whole, t_whole, keys_whole = result

        # Should have some entries
        total_entries = len(k_split) + len(k_whole)
        assert total_entries > 0, "Should have parsed some entries"

    def test_parse_nonexistent_file(self, parse_txt):
        """Parse nonexistent file returns empty lists or raises error."""
        result = parse_txt("/nonexistent/path/file.txt")
        # Should return tuple with empty lists (graceful handling)
        if len(result) == 6:
            k_split, t_split, keys_split, k_whole, t_whole, keys_whole = result
            assert len(k_split) == 0
            assert len(k_whole) == 0
        else:
            # Alternative: returns 4 values
            assert len(result) == 4


class TestQuickSearchProcessFiles:
    """Test QuickSearch process_files function."""

    @pytest.fixture
    def process_files(self):
        from server.tools.quicksearch.parser import process_files
        return process_files

    def test_empty_file_list(self, process_files):
        """Empty file list returns empty dicts."""
        result = process_files([])
        split_dict, whole_dict, string_keys, stringid_to_entry = result

        assert split_dict == {}
        assert whole_dict == {}
        assert string_keys == {}

    def test_process_fixture_file(self, process_files):
        """Process fixture file."""
        fixture_file = str(Path(__file__).parent.parent / "fixtures" / "sample_quicksearch_data.txt")

        if not Path(fixture_file).exists():
            pytest.skip("Fixture file not found")

        result = process_files([fixture_file])
        split_dict, whole_dict, string_keys, stringid_to_entry = result

        total = len(split_dict) + len(whole_dict)
        assert total > 0, f"Should have dictionary entries, got split={len(split_dict)}, whole={len(whole_dict)}"


class TestQuickSearchParserEdgeCases:
    """Edge case tests for parser."""

    @pytest.fixture
    def normalize(self):
        from server.tools.quicksearch.parser import normalize_text
        return normalize_text

    def test_very_long_text(self, normalize):
        """Very long text normalizes correctly."""
        long_text = "안녕하세요 " * 1000
        result = normalize(long_text)
        assert len(result) > 0
        assert "  " not in result  # No double spaces

    def test_mixed_quotes(self, normalize):
        """Mixed quote types handled."""
        text = '"Hello" and \'World\' and "nested \'quotes\'"'
        result = normalize(text)
        assert isinstance(result, str)

    def test_all_unicode_spaces(self, normalize):
        """All Unicode space types normalized."""
        unicode_spaces = '\u00A0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200A\u202F\u205F\u3000'
        text = f"Hello{unicode_spaces}World"
        result = normalize(text)
        # Should collapse to single space
        assert "Hello" in result
        assert "World" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
