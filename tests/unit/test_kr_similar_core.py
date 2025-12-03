"""
Unit Tests for KR Similar Core Module

Tests text normalization and structure adaptation functions.
TRUE SIMULATION - no mocks, real regex and string operations.
"""

import pytest
import sys
import pandas as pd
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestNormalizeText:
    """Test normalize_text function."""

    def test_normalize_simple_text(self):
        """Simple text passes through unchanged."""
        from server.tools.kr_similar.core import normalize_text
        result = normalize_text("안녕하세요")
        assert result == "안녕하세요"

    def test_normalize_removes_changescene(self):
        """ChangeScene tags are removed."""
        from server.tools.kr_similar.core import normalize_text
        result = normalize_text("{ChangeScene(Main)}안녕하세요")
        assert "ChangeScene" not in result
        assert "안녕하세요" in result

    def test_normalize_removes_audiovoice(self):
        """AudioVoice tags are removed."""
        from server.tools.kr_similar.core import normalize_text
        result = normalize_text("{AudioVoice(NPC_123)}테스트")
        assert "AudioVoice" not in result
        assert "테스트" in result

    def test_normalize_removes_multiple_tags(self):
        """Multiple tags are removed."""
        from server.tools.kr_similar.core import normalize_text
        text = "{ChangeScene(Main)}{AudioVoice(NPC)}안녕하세요"
        result = normalize_text(text)
        assert "{" not in result
        assert "}" not in result
        assert "안녕하세요" in result

    def test_normalize_removes_scale_tags(self):
        """Scale HTML tags are removed."""
        from server.tools.kr_similar.core import normalize_text
        result = normalize_text("<Scale=1.2>큰 글자</Scale>")
        assert "Scale" not in result
        assert "큰" in result or "글자" in result

    def test_normalize_removes_color_tags(self):
        """Color HTML tags are removed."""
        from server.tools.kr_similar.core import normalize_text
        result = normalize_text("<color=#FF0000>빨간색</color>")
        assert "color" not in result
        assert "빨간색" in result

    def test_normalize_removes_pacolor_tags(self):
        """PAColor opening tags are removed."""
        from server.tools.kr_similar.core import normalize_text
        result = normalize_text("<PAColor=#FFFFFF>텍스트")
        assert "<PAColor" not in result
        assert "텍스트" in result

    def test_normalize_removes_paoldcolor(self):
        """PAOldColor tag is removed."""
        from server.tools.kr_similar.core import normalize_text
        result = normalize_text("<PAOldColor>텍스트")
        assert "PAOldColor" not in result

    def test_normalize_removes_triangles(self):
        """Triangle markers are removed."""
        from server.tools.kr_similar.core import normalize_text
        result = normalize_text("▶항목 1▶항목 2")
        assert "▶" not in result

    def test_normalize_removes_style_tags(self):
        """Style opening tags are removed."""
        from server.tools.kr_similar.core import normalize_text
        result = normalize_text("<Style:Bold>굵은 글씨")
        assert "<Style" not in result
        assert "굵은" in result

    def test_normalize_collapses_whitespace(self):
        """Multiple spaces collapse to single space."""
        from server.tools.kr_similar.core import normalize_text
        result = normalize_text("안녕    하세요")
        assert "    " not in result
        assert result == "안녕 하세요"

    def test_normalize_strips_whitespace(self):
        """Leading/trailing whitespace is stripped."""
        from server.tools.kr_similar.core import normalize_text
        result = normalize_text("  안녕하세요  ")
        assert result == "안녕하세요"

    def test_normalize_handles_nan(self):
        """NaN/None values return empty string."""
        from server.tools.kr_similar.core import normalize_text
        import pandas as pd
        assert normalize_text(pd.NA) == ''
        assert normalize_text(None) == ''

    def test_normalize_handles_empty_string(self):
        """Empty string returns empty string."""
        from server.tools.kr_similar.core import normalize_text
        assert normalize_text("") == ""

    def test_normalize_handles_non_string(self):
        """Non-string values return empty string."""
        from server.tools.kr_similar.core import normalize_text
        assert normalize_text(123) == ''
        # Lists and other non-string types return empty
        assert normalize_text({'key': 'value'}) == ''

    def test_normalize_complex_mixed_content(self):
        """Complex mixed content is normalized."""
        from server.tools.kr_similar.core import normalize_text
        text = "{ChangeScene(MorningMain_13_005)}{AudioVoice(NPC_VCE_NEW_8513_2_11_Iksun)}<color=#FFCC00>안녕하세요</color> 감사합니다"
        result = normalize_text(text)
        assert "ChangeScene" not in result
        assert "AudioVoice" not in result
        assert "color" not in result
        assert "안녕하세요" in result
        assert "감사합니다" in result


class TestAdaptStructure:
    """Test adapt_structure function."""

    def test_adapt_single_line(self):
        """Single line text is preserved."""
        from server.tools.kr_similar.core import adapt_structure
        result = adapt_structure("안녕하세요", "Hello")
        assert result == "Hello"

    def test_adapt_preserves_line_count(self):
        """Line count matches original."""
        from server.tools.kr_similar.core import adapt_structure
        kr_text = "첫 번째 줄\\n두 번째 줄\\n세 번째 줄"
        translation = "First line. Second line. Third line."
        result = adapt_structure(kr_text, translation)
        assert result.count("\\n") == 2  # 3 lines = 2 line breaks

    def test_adapt_empty_translation(self):
        """Empty translation returns empty lines."""
        from server.tools.kr_similar.core import adapt_structure
        result = adapt_structure("한국어\\n텍스트", "")
        assert "\\n" in result

    def test_adapt_handles_empty_lines(self):
        """Empty lines in original are preserved."""
        from server.tools.kr_similar.core import adapt_structure
        kr_text = "첫 줄\\n\\n세 번째"
        translation = "First line. Third line."
        result = adapt_structure(kr_text, translation)
        lines = result.split("\\n")
        assert len(lines) == 3


class TestKRSimilarCoreClass:
    """Test KRSimilarCore class."""

    def test_class_instantiation(self):
        """Class can be instantiated."""
        from server.tools.kr_similar.core import KRSimilarCore
        core = KRSimilarCore()
        assert core is not None

    def test_normalize_static_method(self):
        """Static normalize method works."""
        from server.tools.kr_similar.core import KRSimilarCore
        result = KRSimilarCore.normalize("{Tag}텍스트")
        assert "{" not in result
        assert "텍스트" in result

    def test_adapt_structure_static_method(self):
        """Static adapt_structure method works."""
        from server.tools.kr_similar.core import KRSimilarCore
        result = KRSimilarCore.adapt_structure("한국어", "English")
        assert result == "English"

    def test_parse_language_file_exists(self):
        """parse_language_file method exists."""
        from server.tools.kr_similar.core import KRSimilarCore
        assert hasattr(KRSimilarCore, 'parse_language_file')
        assert callable(KRSimilarCore.parse_language_file)

    def test_process_split_data_exists(self):
        """process_split_data method exists."""
        from server.tools.kr_similar.core import KRSimilarCore
        assert hasattr(KRSimilarCore, 'process_split_data')
        assert callable(KRSimilarCore.process_split_data)


class TestProcessSplitData:
    """Test process_split_data function."""

    def test_split_multiline_entries(self):
        """Multi-line entries are split correctly."""
        from server.tools.kr_similar.core import KRSimilarCore
        import pandas as pd

        data = pd.DataFrame({
            'Korean': ['첫 줄\\n두 번째 줄'],
            'Translation': ['Line 1\\nLine 2']
        })
        result = KRSimilarCore.process_split_data(data)
        assert len(result) == 2

    def test_split_preserves_single_line(self):
        """Single-line entries are kept as single row."""
        from server.tools.kr_similar.core import KRSimilarCore
        import pandas as pd

        data = pd.DataFrame({
            'Korean': ['한국어'],
            'Translation': ['Korean']
        })
        result = KRSimilarCore.process_split_data(data)
        assert len(result) == 1

    def test_split_skips_empty_lines(self):
        """Empty Korean lines are skipped."""
        from server.tools.kr_similar.core import KRSimilarCore
        import pandas as pd

        data = pd.DataFrame({
            'Korean': ['내용\\n\\n더 내용'],
            'Translation': ['Content\\n\\nMore content']
        })
        result = KRSimilarCore.process_split_data(data)
        # Empty line is skipped
        assert len(result) == 2

    def test_split_handles_mismatched_lines(self):
        """Mismatched line counts are handled."""
        from server.tools.kr_similar.core import KRSimilarCore
        import pandas as pd

        data = pd.DataFrame({
            'Korean': ['한 줄'],
            'Translation': ['Line 1\\nLine 2']  # Different line count
        })
        result = KRSimilarCore.process_split_data(data)
        # Mismatched entries are skipped
        assert len(result) == 0


class TestModuleExports:
    """Test module exports."""

    def test_normalize_text_importable(self):
        """normalize_text is importable."""
        from server.tools.kr_similar.core import normalize_text
        assert callable(normalize_text)

    def test_adapt_structure_importable(self):
        """adapt_structure is importable."""
        from server.tools.kr_similar.core import adapt_structure
        assert callable(adapt_structure)

    def test_krsimilarcore_importable(self):
        """KRSimilarCore is importable."""
        from server.tools.kr_similar.core import KRSimilarCore
        assert KRSimilarCore is not None


class TestEdgeCases:
    """Test edge cases and special inputs."""

    def test_normalize_only_tags(self):
        """String with only tags returns empty."""
        from server.tools.kr_similar.core import normalize_text
        result = normalize_text("{Tag1}{Tag2}{Tag3}")
        assert result == ""

    def test_normalize_nested_braces(self):
        """Nested braces are handled."""
        from server.tools.kr_similar.core import normalize_text
        result = normalize_text("{Outer{Inner}}텍스트")
        # Should handle this gracefully
        assert "텍스트" in result

    def test_normalize_unicode_content(self):
        """Unicode content is preserved."""
        from server.tools.kr_similar.core import normalize_text
        text = "한글 + 日本語 + العربية"
        result = normalize_text(text)
        assert "한글" in result
        assert "日本語" in result
        assert "العربية" in result

    def test_normalize_numbers_preserved(self):
        """Numbers in text are preserved."""
        from server.tools.kr_similar.core import normalize_text
        result = normalize_text("123개의 아이템")
        assert "123" in result

    def test_adapt_very_long_translation(self):
        """Very long translation is handled."""
        from server.tools.kr_similar.core import adapt_structure
        kr_text = "짧은\\n텍스트"
        translation = "This is a very long translation that should be split across multiple lines when adapted to match the Korean structure. " * 5
        result = adapt_structure(kr_text, translation)
        assert "\\n" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
