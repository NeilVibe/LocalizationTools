"""
Tests for TM Text Normalization

Tests the universal newline normalizer that handles all formats:
- TEXT files (escaped \\n)
- XML files (<br/>, &lt;br/&gt;)
- Various line endings

Run with: python3 -m pytest tests/unit/test_tm_normalizer.py -v
"""

import pytest
from server.tools.ldm.tm_indexer import (
    normalize_newlines_universal,
    normalize_for_hash,
    normalize_for_embedding,
)


class TestNormalizeNewlinesUniversal:
    """Test universal newline normalization."""

    def test_empty_string(self):
        """Empty string returns empty."""
        assert normalize_newlines_universal("") == ""
        assert normalize_newlines_universal(None) is None

    def test_no_newlines(self):
        """Text without newlines stays unchanged."""
        text = "저장하기"
        assert normalize_newlines_universal(text) == text

    def test_escaped_newlines(self):
        """TEXT format escaped \\n becomes actual newline."""
        text = "Line 1\\nLine 2\\nLine 3"
        expected = "Line 1\nLine 2\nLine 3"
        assert normalize_newlines_universal(text) == expected

    def test_xml_br_unescaped(self):
        """XML <br/> becomes newline."""
        text = "Line 1<br/>Line 2<br/>Line 3"
        expected = "Line 1\nLine 2\nLine 3"
        assert normalize_newlines_universal(text) == expected

    def test_xml_br_with_space(self):
        """XML <br /> with space becomes newline."""
        text = "Line 1<br />Line 2<br />Line 3"
        expected = "Line 1\nLine 2\nLine 3"
        assert normalize_newlines_universal(text) == expected

    def test_xml_br_escaped(self):
        """HTML-escaped &lt;br/&gt; becomes newline."""
        text = "Line 1&lt;br/&gt;Line 2&lt;br/&gt;Line 3"
        expected = "Line 1\nLine 2\nLine 3"
        assert normalize_newlines_universal(text) == expected

    def test_xml_br_escaped_with_space(self):
        """HTML-escaped &lt;br /&gt; with space becomes newline."""
        text = "Line 1&lt;br /&gt;Line 2&lt;br /&gt;Line 3"
        expected = "Line 1\nLine 2\nLine 3"
        assert normalize_newlines_universal(text) == expected

    def test_windows_line_endings(self):
        """Windows \\r\\n becomes \\n."""
        text = "Line 1\r\nLine 2\r\nLine 3"
        expected = "Line 1\nLine 2\nLine 3"
        assert normalize_newlines_universal(text) == expected

    def test_mac_line_endings(self):
        """Old Mac \\r becomes \\n."""
        text = "Line 1\rLine 2\rLine 3"
        expected = "Line 1\nLine 2\nLine 3"
        assert normalize_newlines_universal(text) == expected

    def test_mixed_formats(self):
        """Mixed formats all normalize to \\n."""
        text = "A\\nB<br/>C&lt;br/&gt;D\r\nE"
        expected = "A\nB\nC\nD\nE"
        assert normalize_newlines_universal(text) == expected

    def test_uppercase_br_tags(self):
        """Uppercase BR tags are handled."""
        text = "Line 1<BR/>Line 2<BR />Line 3"
        expected = "Line 1\nLine 2\nLine 3"
        assert normalize_newlines_universal(text) == expected

    def test_korean_multiline(self):
        """Korean multi-line text normalizes correctly."""
        text_escaped = "저장하기\\n취소하기\\n삭제하기"
        text_br = "저장하기<br/>취소하기<br/>삭제하기"
        expected = "저장하기\n취소하기\n삭제하기"

        assert normalize_newlines_universal(text_escaped) == expected
        assert normalize_newlines_universal(text_br) == expected

    def test_actual_newlines_preserved(self):
        """Already-normalized \\n stays as \\n."""
        text = "Line 1\nLine 2\nLine 3"
        assert normalize_newlines_universal(text) == text


class TestNormalizeForHash:
    """Test hash normalization for exact matching."""

    def test_lowercase(self):
        """Text is lowercased."""
        text = "SAVE FILE"
        result = normalize_for_hash(text)
        assert result == "save file"

    def test_whitespace_normalized(self):
        """Multiple spaces become single space."""
        text = "Save   the    file"
        result = normalize_for_hash(text)
        assert result == "save the file"

    def test_multiline_structure_preserved(self):
        """Newlines are preserved, whitespace per line normalized."""
        text = "Line  1\\nLine   2"
        result = normalize_for_hash(text)
        assert result == "line 1\nline 2"

    def test_mixed_format_normalizes(self):
        """Mixed newline formats all become \\n."""
        text = "A<br/>B\\nC"
        result = normalize_for_hash(text)
        assert result == "a\nb\nc"


class TestNormalizeForEmbedding:
    """Test embedding normalization."""

    def test_whitespace_collapsed(self):
        """All whitespace collapsed to single spaces."""
        text = "Line 1\\nLine 2"
        result = normalize_for_embedding(text)
        assert result == "Line 1 Line 2"

    def test_case_preserved(self):
        """Case is preserved for embeddings."""
        text = "SAVE the File"
        result = normalize_for_embedding(text)
        assert "SAVE" in result
        assert "File" in result

    def test_newlines_become_spaces(self):
        """Newlines become spaces in embedding text."""
        text = "저장하기<br/>취소하기"
        result = normalize_for_embedding(text)
        assert "\n" not in result
        assert "저장하기" in result
        assert "취소하기" in result


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_single_character(self):
        """Single character handled correctly."""
        assert normalize_newlines_universal("a") == "a"
        assert normalize_for_hash("A") == "a"
        assert normalize_for_embedding("a") == "a"

    def test_only_newlines(self):
        """Text with only newlines."""
        text = "\\n\\n\\n"
        result = normalize_newlines_universal(text)
        assert result == "\n\n\n"

    def test_consecutive_br_tags(self):
        """Consecutive <br/> tags."""
        text = "<br/><br/><br/>"
        result = normalize_newlines_universal(text)
        assert result == "\n\n\n"

    def test_leading_trailing_newlines(self):
        """Leading and trailing newlines preserved."""
        text = "\\nContent\\n"
        result = normalize_newlines_universal(text)
        assert result == "\nContent\n"

    def test_empty_lines(self):
        """Empty lines in middle preserved."""
        text = "Line 1\\n\\nLine 3"
        result = normalize_newlines_universal(text)
        assert result == "Line 1\n\nLine 3"

    def test_special_characters(self):
        """Special characters don't break normalization."""
        text = "Price: $100<br/>Total: €200"
        result = normalize_newlines_universal(text)
        assert result == "Price: $100\nTotal: €200"

    def test_numbers_preserved(self):
        """Numbers in text preserved."""
        text = "Item 1\\nItem 2\\nItem 3"
        result = normalize_newlines_universal(text)
        assert "1" in result
        assert "2" in result
        assert "3" in result


class TestPerformance:
    """Performance-related tests."""

    def test_large_text(self):
        """Large text normalizes without issues."""
        # Generate large text with 1000 lines
        lines = [f"Line {i}: 저장하기 확인 삭제" for i in range(1000)]
        text = "\\n".join(lines)

        result = normalize_newlines_universal(text)
        assert result.count("\n") == 999  # 1000 lines = 999 newlines

    def test_many_br_tags(self):
        """Many BR tags normalize efficiently."""
        lines = [f"Line {i}" for i in range(500)]
        text = "<br/>".join(lines)

        result = normalize_newlines_universal(text)
        assert result.count("\n") == 499
