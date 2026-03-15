"""Tests for text matching utilities and Korean detection.

Covers:
- normalize_text_for_match: HTML unescape, whitespace collapse, &desc; removal
- normalize_for_matching: same as above + lowercase
- normalize_nospace: remove all whitespace
- is_formula_text: Excel formula/error detection
- is_korean_text: Korean character detection (syllables + Jamo + Compat Jamo)
"""

from __future__ import annotations

import pytest


class TestNormalizeTextForMatch:
    """Tests for normalize_text_for_match (HTML unescape + whitespace collapse)."""

    def test_basic_whitespace_collapse(self):
        from server.tools.ldm.services.text_matching import normalize_text_for_match
        assert normalize_text_for_match("  Hello   World  ") == "Hello World"

    def test_html_unescape(self):
        from server.tools.ldm.services.text_matching import normalize_text_for_match
        assert normalize_text_for_match("test&amp;value") == "test&value"

    def test_html_unescape_lt_gt(self):
        from server.tools.ldm.services.text_matching import normalize_text_for_match
        assert normalize_text_for_match("&lt;tag&gt;") == "<tag>"

    def test_desc_removal(self):
        from server.tools.ldm.services.text_matching import normalize_text_for_match
        assert normalize_text_for_match("&desc;some text") == "some text"

    def test_desc_removal_case_insensitive(self):
        from server.tools.ldm.services.text_matching import normalize_text_for_match
        assert normalize_text_for_match("&Desc;some text") == "some text"

    def test_amp_desc_removal(self):
        from server.tools.ldm.services.text_matching import normalize_text_for_match
        # After HTML unescape, &amp;desc; becomes &desc;, then removed
        assert normalize_text_for_match("&amp;desc;stuff") == "stuff"

    def test_empty_string(self):
        from server.tools.ldm.services.text_matching import normalize_text_for_match
        assert normalize_text_for_match("") == ""

    def test_none_safe(self):
        from server.tools.ldm.services.text_matching import normalize_text_for_match
        assert normalize_text_for_match(None) == ""

    def test_whitespace_only(self):
        from server.tools.ldm.services.text_matching import normalize_text_for_match
        assert normalize_text_for_match("   ") == ""

    def test_tabs_and_newlines(self):
        from server.tools.ldm.services.text_matching import normalize_text_for_match
        assert normalize_text_for_match("hello\t\nworld") == "hello world"


class TestNormalizeForMatching:
    """Tests for normalize_for_matching (normalize + lowercase)."""

    def test_lowercase(self):
        from server.tools.ldm.services.text_matching import normalize_for_matching
        assert normalize_for_matching("  Hello   World  ") == "hello world"

    def test_html_unescape_lowercase(self):
        from server.tools.ldm.services.text_matching import normalize_for_matching
        assert normalize_for_matching("Test&amp;Value") == "test&value"

    def test_none_safe(self):
        from server.tools.ldm.services.text_matching import normalize_for_matching
        assert normalize_for_matching(None) == ""


class TestNormalizeNospace:
    """Tests for normalize_nospace (remove all whitespace)."""

    def test_basic(self):
        from server.tools.ldm.services.text_matching import normalize_nospace
        assert normalize_nospace("hello world") == "helloworld"

    def test_multiple_spaces(self):
        from server.tools.ldm.services.text_matching import normalize_nospace
        assert normalize_nospace("  hello   world  ") == "helloworld"

    def test_tabs_newlines(self):
        from server.tools.ldm.services.text_matching import normalize_nospace
        assert normalize_nospace("hello\t\nworld") == "helloworld"

    def test_empty(self):
        from server.tools.ldm.services.text_matching import normalize_nospace
        assert normalize_nospace("") == ""


class TestIsFormulaText:
    """Tests for is_formula_text (Excel formula/error detection)."""

    def test_equals_formula(self):
        from server.tools.ldm.services.text_matching import is_formula_text
        assert is_formula_text("=SUM(A1)") is not None

    def test_plus_formula(self):
        from server.tools.ldm.services.text_matching import is_formula_text
        assert is_formula_text("+SUM(A1)") is not None

    def test_at_formula(self):
        from server.tools.ldm.services.text_matching import is_formula_text
        assert is_formula_text("@SUM(A1)") is not None

    def test_normal_text(self):
        from server.tools.ldm.services.text_matching import is_formula_text
        assert is_formula_text("Normal text") is None

    def test_empty(self):
        from server.tools.ldm.services.text_matching import is_formula_text
        assert is_formula_text("") is None

    def test_none(self):
        from server.tools.ldm.services.text_matching import is_formula_text
        assert is_formula_text(None) is None

    def test_excel_error(self):
        from server.tools.ldm.services.text_matching import is_formula_text
        assert is_formula_text("#N/A") is not None

    def test_excel_ref_error(self):
        from server.tools.ldm.services.text_matching import is_formula_text
        assert is_formula_text("#REF!") is not None

    def test_array_formula(self):
        from server.tools.ldm.services.text_matching import is_formula_text
        assert is_formula_text("{=SUM(A1:A10)}") is not None

    def test_xlfn_function(self):
        from server.tools.ldm.services.text_matching import is_formula_text
        assert is_formula_text("_xlfn.CONCAT(A1,B1)") is not None

    def test_hyphen_not_formula(self):
        from server.tools.ldm.services.text_matching import is_formula_text
        # Hyphen prefix is NOT a formula indicator (common in game text)
        assert is_formula_text("-select") is None


class TestIsKoreanText:
    """Tests for is_korean_text (Korean character detection)."""

    def test_korean_syllables(self):
        from server.tools.ldm.services.korean_detection import is_korean_text
        assert is_korean_text("안녕하세요") is True

    def test_compat_jamo(self):
        from server.tools.ldm.services.korean_detection import is_korean_text
        assert is_korean_text("ㄱㄴㄷ") is True

    def test_jamo(self):
        from server.tools.ldm.services.korean_detection import is_korean_text
        # Jamo range U+1100-U+11FF
        assert is_korean_text("\u1100\u1161") is True

    def test_english_only(self):
        from server.tools.ldm.services.korean_detection import is_korean_text
        assert is_korean_text("Hello") is False

    def test_mixed_korean_english(self):
        from server.tools.ldm.services.korean_detection import is_korean_text
        assert is_korean_text("Hello 안녕") is True

    def test_empty_string(self):
        from server.tools.ldm.services.korean_detection import is_korean_text
        assert is_korean_text("") is False

    def test_none_safe(self):
        from server.tools.ldm.services.korean_detection import is_korean_text
        assert is_korean_text(None) is False

    def test_japanese_not_korean(self):
        from server.tools.ldm.services.korean_detection import is_korean_text
        assert is_korean_text("こんにちは") is False

    def test_chinese_not_korean(self):
        from server.tools.ldm.services.korean_detection import is_korean_text
        assert is_korean_text("你好") is False

    def test_numbers_not_korean(self):
        from server.tools.ldm.services.korean_detection import is_korean_text
        assert is_korean_text("12345") is False
