"""
Unit tests for QuickSearch QA Tools

Tests the 5 QA tool functions from server/tools/quicksearch/qa_tools.py:
1. extract_glossary
2. line_check
3. term_check
4. pattern_sequence_check
5. character_count_check
"""

import os
import tempfile
import pytest
from pathlib import Path

from server.tools.quicksearch import qa_tools
from server.tools.quicksearch.qa_tools import HAS_LXML

# Skip decorator for tests requiring lxml
requires_lxml = pytest.mark.skipif(not HAS_LXML, reason="lxml not installed")


# =============================================================================
# TEST FIXTURES
# =============================================================================

@pytest.fixture
def temp_xml_file():
    """Create a temporary XML file with LocStr entries."""
    content = '''<?xml version="1.0" encoding="utf-8"?>
<LanguageData>
    <LocStr StringId="TEST_001" StrOrigin="전투" Str="Combat"/>
    <LocStr StringId="TEST_002" StrOrigin="전투력" Str="Combat Power"/>
    <LocStr StringId="TEST_003" StrOrigin="아이템" Str="Item"/>
    <LocStr StringId="TEST_004" StrOrigin="아이템 획득" Str="Item Obtained"/>
    <LocStr StringId="TEST_005" StrOrigin="레벨" Str="Level"/>
    <LocStr StringId="TEST_006" StrOrigin="경험치" Str="Experience"/>
    <LocStr StringId="TEST_007" StrOrigin="스킬" Str="Skill"/>
    <LocStr StringId="TEST_008" StrOrigin="전투" Str="Battle"/>
    <LocStr StringId="TEST_009" StrOrigin="체력 {value} 회복" Str="Recover {value} HP"/>
    <LocStr StringId="TEST_010" StrOrigin="체력 {value} 회복" Str="Recover HP"/>
</LanguageData>
'''
    with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as f:
        f.write(content)
        f.flush()
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def temp_txt_file():
    """Create a temporary TXT file with tab-separated entries."""
    # Format: col0-col4 are StringID components, col5=Korean, col6=Translation
    lines = [
        "File1\tSection1\tID1\t0\t0\t전투\tCombat",
        "File1\tSection1\tID2\t0\t0\t전투력\tCombat Power",
        "File1\tSection1\tID3\t0\t0\t아이템\tItem",
        "File1\tSection1\tID4\t0\t0\t레벨\tLevel",
        "File1\tSection1\tID5\t0\t0\t경험치\tExperience",
        "File1\tSection1\tID6\t0\t0\t전투\tBattle",
    ]
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write('\n'.join(lines))
        f.flush()
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def temp_xml_with_patterns():
    """Create XML file with code patterns for pattern check testing."""
    content = '''<?xml version="1.0" encoding="utf-8"?>
<LanguageData>
    <LocStr StringId="PAT_001" StrOrigin="체력 {hp} 회복" Str="Recover {hp} HP"/>
    <LocStr StringId="PAT_002" StrOrigin="{name}님의 스킬" Str="{name}'s Skill"/>
    <LocStr StringId="PAT_003" StrOrigin="{a}와 {b} 사용" Str="Use {a}"/>
    <LocStr StringId="PAT_004" StrOrigin="경험치 획득" Str="Gain Experience"/>
</LanguageData>
'''
    with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as f:
        f.write(content)
        f.flush()
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def temp_xml_with_symbols():
    """Create XML file with special symbols for character count testing."""
    content = '''<?xml version="1.0" encoding="utf-8"?>
<LanguageData>
    <LocStr StringId="SYM_001" StrOrigin="{value}골드 획득" Str="Obtained {value} gold"/>
    <LocStr StringId="SYM_002" StrOrigin="{{item}} 사용" Str="{item} used"/>
    <LocStr StringId="SYM_003" StrOrigin="일반 텍스트" Str="Normal text"/>
    <LocStr StringId="SYM_004" StrOrigin="{a}{b}{c}" Str="{a}{b}"/>
</LanguageData>
'''
    with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as f:
        f.write(content)
        f.flush()
        yield f.name
    os.unlink(f.name)


# =============================================================================
# HELPER FUNCTION TESTS
# =============================================================================

class TestHelperFunctions:
    """Test helper functions in qa_tools module."""

    def test_is_korean_with_korean(self):
        """Test is_korean returns True for Korean text."""
        assert qa_tools.is_korean("전투") == True
        assert qa_tools.is_korean("안녕하세요") == True
        assert qa_tools.is_korean("한글") == True

    def test_is_korean_without_korean(self):
        """Test is_korean returns False for non-Korean text."""
        assert qa_tools.is_korean("Combat") == False
        assert qa_tools.is_korean("Hello") == False
        assert qa_tools.is_korean("123") == False

    def test_is_korean_with_mixed(self):
        """Test is_korean returns True for mixed Korean/English."""
        assert qa_tools.is_korean("전투 Combat") == True
        assert qa_tools.is_korean("Level 레벨") == True

    def test_is_sentence(self):
        """Test is_sentence detection."""
        assert qa_tools.is_sentence("This is a sentence.") == True
        assert qa_tools.is_sentence("Is this a question?") == True
        assert qa_tools.is_sentence("Wow!") == True
        assert qa_tools.is_sentence("전투력") == False
        assert qa_tools.is_sentence("Combat Power") == False

    def test_has_punctuation(self):
        """Test has_punctuation detection."""
        assert qa_tools.has_punctuation("Hello, World!") == True
        assert qa_tools.has_punctuation("test.txt") == True
        assert qa_tools.has_punctuation("전투") == False
        assert qa_tools.has_punctuation("Combat") == False
        assert qa_tools.has_punctuation("말줄임표…") == True

    def test_extract_code_patterns(self):
        """Test code pattern extraction."""
        assert qa_tools.extract_code_patterns("체력 {hp} 회복") == {"{hp}"}
        assert qa_tools.extract_code_patterns("{a} and {b}") == {"{a}", "{b}"}
        assert qa_tools.extract_code_patterns("no patterns") == set()
        assert qa_tools.extract_code_patterns("") == set()


# =============================================================================
# EXTRACT ALL PAIRS TESTS
# =============================================================================

class TestExtractAllPairs:
    """Test extract_all_pairs_from_files function."""

    @requires_lxml
    def test_extract_from_xml(self, temp_xml_file):
        """Test extraction from XML file."""
        pairs = qa_tools.extract_all_pairs_from_files([temp_xml_file])
        assert len(pairs) >= 8
        assert ("전투", "Combat") in pairs

    def test_extract_from_txt(self, temp_txt_file):
        """Test extraction from TXT file."""
        pairs = qa_tools.extract_all_pairs_from_files([temp_txt_file])
        assert len(pairs) >= 5
        assert ("전투", "Combat") in pairs

    def test_extract_empty_list(self):
        """Test extraction with empty file list."""
        pairs = qa_tools.extract_all_pairs_from_files([])
        assert pairs == []


# =============================================================================
# GLOSSARY FILTER TESTS
# =============================================================================

class TestGlossaryFilter:
    """Test glossary_filter function."""

    def test_basic_filtering(self):
        """Test basic glossary filtering."""
        pairs = [
            ("전투", "Combat"),
            ("전투력 상승 효과 증가 아이템", "Combat Power Increase Effect Item"),  # Too long (15 chars)
            ("아이템", "Item"),
            ("경험치.", "Experience."),  # Has punctuation
        ]
        filtered = qa_tools.glossary_filter(pairs, length_threshold=10, filter_sentences=False)
        assert len(filtered) == 2
        assert ("전투", "Combat") in filtered
        assert ("아이템", "Item") in filtered

    def test_sentence_filtering(self):
        """Test sentence filtering."""
        pairs = [
            ("전투", "Combat"),
            ("완료되었습니다.", "Completed."),
            ("계속할까요?", "Continue?"),
        ]
        filtered = qa_tools.glossary_filter(pairs, length_threshold=20, filter_sentences=True)
        assert len(filtered) == 1
        assert ("전투", "Combat") in filtered

    def test_min_occurrence_filter(self):
        """Test minimum occurrence filtering."""
        pairs = [
            ("전투", "Combat"),
            ("전투", "Battle"),
            ("전투", "Fight"),
            ("아이템", "Item"),
        ]
        filtered = qa_tools.glossary_filter(pairs, length_threshold=20, filter_sentences=False, min_occurrence=2)
        # Only "전투" should pass (3 occurrences)
        korean_terms = [kr for kr, _ in filtered]
        assert all(kr == "전투" for kr in korean_terms)


# =============================================================================
# EXTRACT GLOSSARY TESTS
# =============================================================================

class TestExtractGlossary:
    """Test extract_glossary function."""

    @requires_lxml
    def test_extract_glossary_basic(self, temp_xml_file):
        """Test basic glossary extraction."""
        result = qa_tools.extract_glossary(
            file_paths=[temp_xml_file],
            filter_sentences=True,
            glossary_length_threshold=15,
            min_occurrence=1,
            sort_method="alphabetical"
        )

        assert "glossary" in result
        assert "total_candidates" in result
        assert "total_terms" in result
        assert "files_processed" in result
        assert result["files_processed"] == 1

    def test_extract_glossary_empty_files(self):
        """Test extraction with no files."""
        result = qa_tools.extract_glossary(
            file_paths=[],
            filter_sentences=True,
            glossary_length_threshold=15,
            min_occurrence=1
        )

        assert result["total_terms"] == 0
        assert result["files_processed"] == 0


# =============================================================================
# LINE CHECK TESTS
# =============================================================================

class TestLineCheck:
    """Test line_check function."""

    @requires_lxml
    def test_line_check_finds_inconsistencies(self, temp_xml_file):
        """Test that line check finds inconsistent translations."""
        result = qa_tools.line_check(
            file_paths=[temp_xml_file],
            filter_sentences=True,
            glossary_length_threshold=15
        )

        assert "inconsistent_entries" in result
        assert "inconsistent_count" in result
        assert "files_processed" in result

        # "전투" has both "Combat" and "Battle" translations
        inconsistent_sources = [e["source"] for e in result["inconsistent_entries"]]
        assert "전투" in inconsistent_sources

    def test_line_check_no_files(self):
        """Test line check with empty files."""
        result = qa_tools.line_check(file_paths=[])
        assert result["inconsistent_count"] == 0


# =============================================================================
# TERM CHECK TESTS
# =============================================================================

class TestTermCheck:
    """Test term_check function."""

    @requires_lxml
    def test_term_check_basic(self, temp_xml_file):
        """Test basic term check."""
        result = qa_tools.term_check(
            file_paths=[temp_xml_file],
            filter_sentences=True,
            glossary_length_threshold=15,
            max_issues_per_term=10
        )

        assert "issues" in result
        assert "terms_checked" in result
        assert "issues_count" in result
        assert "files_processed" in result

    def test_term_check_empty(self):
        """Test term check with no files."""
        result = qa_tools.term_check(file_paths=[])
        assert result["issues_count"] == 0


# =============================================================================
# PATTERN CHECK TESTS
# =============================================================================

class TestPatternCheck:
    """Test pattern_sequence_check function."""

    @requires_lxml
    def test_pattern_check_finds_mismatches(self, temp_xml_with_patterns):
        """Test that pattern check finds mismatched patterns."""
        result = qa_tools.pattern_sequence_check(file_paths=[temp_xml_with_patterns])

        assert "mismatches" in result
        assert "mismatch_count" in result
        assert "files_processed" in result

        # PAT_003 has {a} and {b} in source but only {a} in translation
        mismatch_ids = [m.get("locstr_id", "") for m in result["mismatches"]]
        assert any("PAT_003" in mid for mid in mismatch_ids)

    @requires_lxml
    def test_pattern_check_matching_patterns(self, temp_xml_file):
        """Test pattern check with matching patterns."""
        result = qa_tools.pattern_sequence_check(file_paths=[temp_xml_file])

        # TEST_009 has matching {value} patterns
        # TEST_010 has mismatched patterns ({value} vs none)
        assert "mismatches" in result

    def test_pattern_check_empty(self):
        """Test pattern check with no files."""
        result = qa_tools.pattern_sequence_check(file_paths=[])
        assert result["mismatch_count"] == 0


# =============================================================================
# CHARACTER COUNT CHECK TESTS
# =============================================================================

class TestCharacterCountCheck:
    """Test character_count_check function."""

    @requires_lxml
    def test_character_count_bdo_symbols(self, temp_xml_with_symbols):
        """Test character count with BDO symbol set."""
        result = qa_tools.character_count_check(
            file_paths=[temp_xml_with_symbols],
            symbol_set="BDO"  # { and }
        )

        assert "mismatches" in result
        assert "mismatch_count" in result
        assert "symbols_checked" in result
        assert result["symbols_checked"] == ["{", "}"]

        # SYM_002 has {{ vs { (mismatch)
        # SYM_004 has {a}{b}{c} vs {a}{b} (mismatch)
        assert result["mismatch_count"] >= 1

    @requires_lxml
    def test_character_count_custom_symbols(self, temp_xml_with_symbols):
        """Test character count with custom symbols."""
        result = qa_tools.character_count_check(
            file_paths=[temp_xml_with_symbols],
            symbols=["{", "}", "골"]  # Custom symbols
        )

        assert "symbols_checked" in result
        assert "{" in result["symbols_checked"]
        assert "}" in result["symbols_checked"]
        assert "골" in result["symbols_checked"]

    def test_character_count_empty(self):
        """Test character count with no files."""
        result = qa_tools.character_count_check(file_paths=[])
        assert result["mismatch_count"] == 0


# =============================================================================
# AHOCORASICK AVAILABILITY TEST
# =============================================================================

class TestAhocorasickAvailability:
    """Test Aho-Corasick module availability."""

    def test_ahocorasick_imported(self):
        """Test that ahocorasick module is available."""
        # This tests that the optional dependency is installed
        assert qa_tools.HAS_AHOCORASICK == True, "ahocorasick should be installed for optimal performance"


# =============================================================================
# INTEGRATION-LIKE TESTS
# =============================================================================

class TestQAToolsIntegration:
    """Integration-like tests for QA tools workflow."""

    @requires_lxml
    def test_full_qa_workflow(self, temp_xml_file):
        """Test running all QA tools on same file."""
        # Extract glossary
        glossary_result = qa_tools.extract_glossary(
            file_paths=[temp_xml_file],
            min_occurrence=1
        )
        assert glossary_result["total_terms"] >= 0

        # Line check
        line_result = qa_tools.line_check(file_paths=[temp_xml_file])
        assert "inconsistent_entries" in line_result

        # Term check
        term_result = qa_tools.term_check(file_paths=[temp_xml_file])
        assert "issues" in term_result

        # Pattern check
        pattern_result = qa_tools.pattern_sequence_check(file_paths=[temp_xml_file])
        assert "mismatches" in pattern_result

        # Character count
        char_result = qa_tools.character_count_check(file_paths=[temp_xml_file])
        assert "mismatches" in char_result

    @requires_lxml
    def test_mixed_file_types(self, temp_xml_file, temp_txt_file):
        """Test processing mixed XML and TXT files."""
        pairs = qa_tools.extract_all_pairs_from_files([temp_xml_file, temp_txt_file])
        assert len(pairs) >= 10  # Combined entries from both files
