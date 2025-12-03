"""
Unit Tests for XLSTransfer Additional Modules

Tests modules with low coverage:
- excel_utils.py
- config.py
- file operations
"""

import pytest
import sys
import os
import tempfile
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestXLSTransferConfig:
    """Test XLSTransfer config module."""

    def test_config_imports(self):
        """Config module imports without error."""
        from server.tools.xlstransfer import config
        assert config is not None

    def test_config_has_required_constants(self):
        """Config has required constants."""
        from server.tools.xlstransfer import config

        # Check essential constants exist
        assert hasattr(config, 'MODEL_NAME')
        assert hasattr(config, 'CODE_PATTERNS')
        assert hasattr(config, 'DEFAULT_FAISS_THRESHOLD')

    def test_model_name_is_korean_bert(self):
        """Model name is Korean BERT (not multilingual)."""
        from server.tools.xlstransfer import config

        # Must be Korean-specific model
        assert 'KR-SBERT' in config.MODEL_NAME or 'korean' in config.MODEL_NAME.lower()
        # Must NOT be generic multilingual
        assert 'paraphrase-multilingual' not in config.MODEL_NAME

    def test_faiss_threshold_valid_range(self):
        """FAISS threshold is in valid range."""
        from server.tools.xlstransfer import config
        assert 0.0 <= config.DEFAULT_FAISS_THRESHOLD <= 1.0
        assert config.MIN_FAISS_THRESHOLD <= config.MAX_FAISS_THRESHOLD

    def test_code_patterns_are_regexes(self):
        """Code patterns are valid regex patterns."""
        from server.tools.xlstransfer import config
        import re

        for pattern in config.CODE_PATTERNS:
            # Should be compilable regex
            compiled = re.compile(pattern)
            assert compiled is not None


class TestXLSTransferCore:
    """Test XLSTransfer core utilities."""

    @pytest.fixture
    def core(self):
        from server.tools.xlstransfer import core
        return core

    def test_clean_text_removes_carriage_return(self, core):
        """clean_text removes _x000D_ pattern."""
        result = core.clean_text("Hello_x000D_World")
        assert "_x000D_" not in result
        assert "HelloWorld" in result or "Hello" in result

    def test_clean_text_handles_none(self, core):
        """clean_text handles None input."""
        result = core.clean_text(None)
        assert result is None

    def test_clean_text_handles_numbers(self, core):
        """clean_text converts numbers to strings."""
        result = core.clean_text(123)
        assert result == "123"

        result = core.clean_text(3.14)
        assert "3.14" in result

    def test_excel_column_conversion_round_trip(self, core):
        """Column index converts to letter and back."""
        for i in range(26):
            letter = core.index_to_excel_column(i)
            back = core.excel_column_to_index(letter)
            assert back == i, f"Round trip failed for index {i}"

    def test_excel_column_a_to_z(self, core):
        """A-Z columns convert correctly."""
        assert core.excel_column_to_index('A') == 0
        assert core.excel_column_to_index('B') == 1
        assert core.excel_column_to_index('Z') == 25

        assert core.index_to_excel_column(0) == 'A'
        assert core.index_to_excel_column(25) == 'Z'

    def test_excel_column_lowercase(self, core):
        """Lowercase letters convert correctly."""
        assert core.excel_column_to_index('a') == 0
        assert core.excel_column_to_index('z') == 25

    def test_convert_cell_value_numbers(self, core):
        """convert_cell_value handles numeric strings."""
        assert core.convert_cell_value("123") == 123.0
        assert core.convert_cell_value("3.14") == 3.14

    def test_convert_cell_value_text(self, core):
        """convert_cell_value preserves text."""
        assert core.convert_cell_value("Hello") == "Hello"
        assert core.convert_cell_value("123abc") == "123abc"

    def test_count_newlines(self, core):
        """count_newlines counts correctly."""
        assert core.count_newlines("Hello") == 0
        assert core.count_newlines("Hello\nWorld") == 1
        assert core.count_newlines("Line1\\nLine2\\nLine3") == 2

    def test_normalize_newlines(self, core):
        """normalize_newlines converts correctly."""
        result = core.normalize_newlines("Hello\nWorld")
        assert "\\n" in result


class TestXLSTransferExcelUtils:
    """Test XLSTransfer Excel utilities."""

    @pytest.fixture
    def excel_utils(self):
        from server.tools.xlstransfer import excel_utils
        return excel_utils

    def test_module_imports(self, excel_utils):
        """Excel utils module imports."""
        assert excel_utils is not None

    def test_has_required_functions(self, excel_utils):
        """Module has required functions."""
        # Check for essential functions
        assert hasattr(excel_utils, 'get_sheets_from_file') or hasattr(excel_utils, 'get_sheet_names')


class TestXLSTransferAnalyzeCodePatterns:
    """Test code pattern analysis."""

    @pytest.fixture
    def analyze(self):
        try:
            from server.tools.xlstransfer.core import analyze_code_patterns
            return analyze_code_patterns
        except ImportError:
            pytest.skip("analyze_code_patterns not available")

    def test_basic_code_pattern(self, analyze):
        """Basic code pattern detected."""
        result = analyze("{Code}Hello")
        assert 'start_codes' in result
        assert len(result['start_codes']) > 0

    def test_multiple_codes_pattern(self, analyze):
        """Multiple codes pattern detected."""
        result = analyze("{Tag1}{Tag2}{Tag3}Hello")
        assert 'start_codes' in result
        assert 'next_levels' in result

    def test_pacolor_pattern(self, analyze):
        """PAColor pattern detected."""
        result = analyze("<PAColor>Hello<PAOldColor>")
        # Should detect PAColor
        assert 'start_codes' in result

    def test_no_codes(self, analyze):
        """No codes returns empty start_codes."""
        result = analyze("Plain text without codes")
        assert 'start_codes' in result
        assert len(result['start_codes']) == 0

    def test_production_pattern(self, analyze):
        """Production pattern (ChangeScene + AudioVoice) detected."""
        result = analyze("{ChangeScene(Main_001)}{AudioVoice(NPC_001)}Hello")
        assert 'start_codes' in result
        assert len(result['start_codes']) > 0


class TestXLSTransferFindCodePatterns:
    """Test find_code_patterns_in_text."""

    @pytest.fixture
    def find_patterns(self):
        try:
            from server.tools.xlstransfer.core import find_code_patterns_in_text
            return find_code_patterns_in_text
        except ImportError:
            pytest.skip("find_code_patterns_in_text not available")

    def test_find_single_code(self, find_patterns):
        """Find single code pattern."""
        result = find_patterns("{ItemID}Hello")
        assert len(result) > 0

    def test_find_multiple_codes(self, find_patterns):
        """Find multiple code patterns."""
        result = find_patterns("{Code1}Hello{Code2}World")
        assert len(result) >= 2

    def test_find_no_codes(self, find_patterns):
        """No codes returns empty list."""
        result = find_patterns("Plain text")
        assert result == []


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
