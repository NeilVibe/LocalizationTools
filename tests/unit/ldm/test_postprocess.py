"""Tests for the 8-step postprocess pipeline.

Covers:
- Each step individually
- Full pipeline order
- CJK ellipsis skip
- br-tag roundtrip
- Source text never modified
- postprocess_rows batch function
"""

from __future__ import annotations

import pytest

from server.tools.ldm.services.postprocess import (
    postprocess_value,
    postprocess_rows,
    POSTPROCESS_STEPS,
)


class TestPostprocessStepOrder:
    """Verify the pipeline has exactly 8 steps in correct order."""

    def test_has_8_steps(self):
        assert len(POSTPROCESS_STEPS) == 8

    def test_step_names_in_order(self):
        names = [name for name, _ in POSTPROCESS_STEPS]
        assert names == [
            "newlines",
            "empty_strorigin",
            "no_translation",
            "apostrophes",
            "invisible_chars",
            "hyphens",
            "ellipsis",
            "double_escaped",
        ]


class TestStep1Newlines:
    """Step 1: Normalize all newline representations to <br/>."""

    def test_crlf(self):
        result, _ = postprocess_value("line1\r\nline2")
        assert result == "line1<br/>line2"

    def test_lf(self):
        result, _ = postprocess_value("line1\nline2")
        assert result == "line1<br/>line2"

    def test_cr(self):
        result, _ = postprocess_value("line1\rline2")
        assert result == "line1<br/>line2"

    def test_literal_backslash_n(self):
        result, _ = postprocess_value("line1\\nline2")
        assert result == "line1<br/>line2"

    def test_html_escaped_br(self):
        result, _ = postprocess_value("line1&lt;br/&gt;line2")
        assert result == "line1<br/>line2"

    def test_wrong_br_variant(self):
        result, _ = postprocess_value("line1<BR>line2")
        assert result == "line1<br/>line2"

    def test_correct_br_unchanged(self):
        result, _ = postprocess_value("line1<br/>line2")
        assert result == "line1<br/>line2"


class TestStep2EmptyStrorigin:
    """Step 2: If source is empty, target becomes empty."""

    def test_empty_source_clears_target(self):
        result, _ = postprocess_value("some text", source="")
        assert result == ""

    def test_whitespace_source_clears_target(self):
        result, _ = postprocess_value("some text", source="   ")
        assert result == ""

    def test_nonempty_source_keeps_target(self):
        result, _ = postprocess_value("some text", source="source text")
        assert result == "some text"


class TestStep3NoTranslation:
    """Step 3: 'no translation' -> '' (case-insensitive)."""

    def test_exact_match(self):
        result, _ = postprocess_value("no translation", source="source")
        assert result == ""

    def test_case_insensitive(self):
        result, _ = postprocess_value("NO TRANSLATION", source="source")
        assert result == ""

    def test_whitespace_collapsed(self):
        result, _ = postprocess_value("  no   translation  ", source="source")
        assert result == ""

    def test_normal_text_unchanged(self):
        result, _ = postprocess_value("normal text", source="source")
        assert result == "normal text"

    def test_partial_match_unchanged(self):
        result, _ = postprocess_value("there is no translation here", source="source")
        assert result == "there is no translation here"


class TestStep4Apostrophes:
    """Step 4: Curly quotes -> ASCII apostrophe."""

    def test_left_single_quote(self):
        result, _ = postprocess_value("it\u2018s")
        assert result == "it's"

    def test_right_single_quote(self):
        result, _ = postprocess_value("it\u2019s")
        assert result == "it's"

    def test_acute_accent(self):
        result, _ = postprocess_value("it\u00B4s")
        assert result == "it's"


class TestStep5InvisibleChars:
    """Step 5: NBSP -> space, zero-width chars deleted."""

    def test_nbsp_to_space(self):
        result, _ = postprocess_value("hello\u00a0world")
        assert result == "hello world"

    def test_zero_width_space_deleted(self):
        result, _ = postprocess_value("hel\u200blo")
        assert result == "hello"

    def test_bom_deleted(self):
        result, _ = postprocess_value("\ufeffhello")
        assert result == "hello"


class TestStep6Hyphens:
    """Step 6: Unicode hyphens -> ASCII hyphen."""

    def test_unicode_hyphen(self):
        result, _ = postprocess_value("some\u2010text")
        assert result == "some-text"

    def test_non_breaking_hyphen(self):
        result, _ = postprocess_value("some\u2011text")
        assert result == "some-text"

    def test_ascii_hyphen_unchanged(self):
        result, _ = postprocess_value("some-text")
        assert result == "some-text"

    def test_en_dash_unchanged(self):
        # en-dash (U+2013) and em-dash (U+2014) are NOT normalized
        result, _ = postprocess_value("some\u2013text")
        assert result == "some\u2013text"


class TestStep7Ellipsis:
    """Step 7: Ellipsis normalization (skip for CJK)."""

    def test_unicode_ellipsis_to_dots_non_cjk(self):
        result, _ = postprocess_value("wait\u2026")
        assert result == "wait..."

    def test_three_dots_unchanged(self):
        result, _ = postprocess_value("wait...")
        assert result == "wait..."

    def test_cjk_keeps_unicode_ellipsis(self):
        result, _ = postprocess_value("wait\u2026", is_cjk=True)
        assert result == "wait\u2026"


class TestStep8DoubleEscaped:
    """Step 8: Double-escaped entities decoded."""

    def test_amp_amp(self):
        # &amp;desc; -> &desc; (safe entity decode)
        result, _ = postprocess_value("&amp;desc;stuff")
        assert result == "&desc;stuff"

    def test_lt_gt(self):
        result, _ = postprocess_value("&lt;tag&gt;")
        assert result == "<tag>"

    def test_quot(self):
        result, _ = postprocess_value("&quot;hello&quot;")
        assert result == '"hello"'

    def test_apos(self):
        result, _ = postprocess_value("&apos;hello&apos;")
        assert result == "'hello'"


class TestBrTagRoundtrip:
    """br-tag must survive the full pipeline intact."""

    def test_br_tag_survives_all_steps(self):
        result, _ = postprocess_value("line1<br/>line2<br/>line3")
        assert result == "line1<br/>line2<br/>line3"

    def test_br_tag_with_special_chars(self):
        result, _ = postprocess_value("hello\u00a0world<br/>next\u2019s line")
        assert result == "hello world<br/>next's line"

    def test_br_tag_cjk_mode(self):
        result, _ = postprocess_value("line1<br/>line2", is_cjk=True)
        assert result == "line1<br/>line2"


class TestSourceNeverModified:
    """Source text is only used for checking, never modified."""

    def test_source_not_in_output(self):
        # When source is "original" and value is "target",
        # step 2 should NOT copy source into result
        result, _ = postprocess_value("target text", source="original source")
        assert result == "target text"

    def test_empty_source_clears_but_returns_empty(self):
        result, _ = postprocess_value("target text", source="")
        assert result == ""


class TestPostprocessRows:
    """Test batch postprocess_rows function."""

    def test_basic_batch(self):
        rows = [
            {"source": "src1", "target": "hello\u2019s"},
            {"source": "src2", "target": "line1\nline2"},
        ]
        result, stats = postprocess_rows(rows)
        assert result[0]["target"] == "hello's"
        assert result[1]["target"] == "line1<br/>line2"

    def test_source_not_modified(self):
        rows = [{"source": "src\u2019s", "target": "tgt\u2019s"}]
        result, _ = postprocess_rows(rows)
        assert result[0]["source"] == "src\u2019s"  # source unchanged
        assert result[0]["target"] == "tgt's"  # target cleaned

    def test_empty_source_clears_target(self):
        rows = [{"source": "", "target": "some text"}]
        result, _ = postprocess_rows(rows)
        assert result[0]["target"] == ""

    def test_cjk_mode(self):
        rows = [{"source": "src", "target": "wait\u2026"}]
        result, _ = postprocess_rows(rows, is_cjk=True)
        assert result[0]["target"] == "wait\u2026"

    def test_empty_list(self):
        result, stats = postprocess_rows([])
        assert result == []

    def test_stats_tracking(self):
        rows = [
            {"source": "src", "target": "hello\nworld"},
            {"source": "src", "target": "it\u2019s"},
        ]
        _, stats = postprocess_rows(rows)
        assert stats["newlines"] >= 1
        assert stats["apostrophes"] >= 1

    def test_missing_target_key(self):
        rows = [{"source": "src"}]
        result, _ = postprocess_rows(rows)
        assert result[0] == {"source": "src"}  # unchanged, no target key


class TestPostprocessValueStats:
    """Verify stats dict tracks which steps made changes."""

    def test_stats_keys(self):
        _, stats = postprocess_value("hello\n\u2019world")
        assert "newlines" in stats
        assert "apostrophes" in stats

    def test_no_changes_stats(self):
        _, stats = postprocess_value("plain text")
        # All stats should be 0 or absent
        total = sum(stats.values())
        assert total == 0

    def test_empty_input(self):
        result, stats = postprocess_value("")
        assert result == ""
        assert sum(stats.values()) == 0
