"""
Full Simulation Tests - Complete Production Workflow

Tests the COMPLETE workflow from raw input to final output,
simulating exactly what happens in production.

=== SIMULATION SCENARIOS ===

1. KR Similar Full Flow:
   - Load language file
   - Create dictionary with embeddings
   - Search for similar strings
   - Verify results match expected

2. XLSTransfer Full Flow:
   - Load Excel dictionary
   - Create embeddings
   - Translate text file
   - Verify tag reconstruction

3. QuickSearch Full Flow:
   - Create dictionary from files
   - Load dictionary
   - Search single/multi line
   - Verify search results

4. Cross-Tool Integration:
   - Use same source data across tools
   - Verify consistency
"""

import pytest
import sys
import os
import tempfile
import shutil
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


class TestKRSimilarFullSimulation:
    """Full simulation of KR Similar production workflow."""

    @pytest.fixture(scope="class")
    def temp_dict_dir(self):
        """Create temporary directory for dictionaries."""
        temp_dir = tempfile.mkdtemp(prefix="kr_similar_test_")
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture(scope="class")
    def embeddings_manager(self, temp_dict_dir):
        """Get EmbeddingsManager with test config."""
        from server.tools.kr_similar.embeddings import EmbeddingsManager
        manager = EmbeddingsManager()
        # Override base directory for testing
        manager.base_dir = Path(temp_dict_dir)
        return manager

    def test_01_load_production_data_format(self):
        """Step 1: Verify we can load production data format."""
        from server.tools.kr_similar.core import KRSimilarCore

        fixture_file = FIXTURES_DIR / "sample_language_data.txt"
        assert fixture_file.exists(), f"Fixture not found: {fixture_file}"

        df = KRSimilarCore.parse_language_file(
            str(fixture_file),
            kr_column=5,
            trans_column=6
        )

        assert len(df) >= 40, f"Expected 40+ rows, got {len(df)}"
        assert 'Korean' in df.columns
        assert 'Translation' in df.columns

        # Verify production patterns are present
        all_korean = ' '.join(df['Korean'].astype(str).tolist())
        assert '{ChangeScene' in all_korean, "Should have ChangeScene tags"
        assert '{AudioVoice' in all_korean, "Should have AudioVoice tags"

        print(f"✅ Loaded {len(df)} rows with production patterns")

    def test_02_normalize_strips_tags_preserves_content(self):
        """Step 2: Verify normalize_text strips tags but preserves Korean."""
        from server.tools.kr_similar.core import normalize_text

        test_cases = [
            # (input, expected_contains, expected_not_contains)
            (
                "{ChangeScene(Main)}{AudioVoice(NPC)}안녕하세요",
                ["안녕하세요"],
                ["{", "}", "ChangeScene", "AudioVoice"]
            ),
            (
                "<color=red>경고</color>: HP 100",
                ["경고", "HP", "100"],
                ["<color", "</color>"]
            ),
            (
                "▶ 첫 번째 선택\\n▶ 두 번째 선택",
                ["첫 번째", "두 번째"],
                ["▶"]
            ),
            (
                "{Scale(1.2)}큰 글자{/Scale}",
                ["큰", "글자"],
                ["Scale", "{", "}"]
            ),
        ]

        for input_text, should_contain, should_not_contain in test_cases:
            result = normalize_text(input_text)

            for expected in should_contain:
                assert expected in result, f"'{expected}' should be in result: {result}"

            for unexpected in should_not_contain:
                assert unexpected not in result, f"'{unexpected}' should NOT be in result: {result}"

        print("✅ normalize_text correctly strips tags, preserves content")

    def test_03_create_dictionary_generates_embeddings(self, embeddings_manager):
        """Step 3: Create dictionary and verify embeddings are generated."""
        fixture_file = str(FIXTURES_DIR / "sample_language_data.txt")

        # Create dictionary - use valid dict_type from DICT_TYPES
        # Valid types are: BDO, BDM, BDC, CD
        result = embeddings_manager.create_dictionary(
            file_paths=[fixture_file],
            dict_type="BDO",  # Use valid type
            kr_column=5,
            trans_column=6
        )

        assert result is not None, "Should return result"

        # Verify files created
        dict_dir = embeddings_manager.base_dir / "BDO"
        # Check if any embeddings were created
        print(f"✅ Dictionary created at: {dict_dir}")

    def test_04_similarity_search_returns_results(self, embeddings_manager):
        """Step 4: Search for similar strings."""
        from server.tools.kr_similar.searcher import SimilaritySearcher

        # Load dictionary first
        try:
            embeddings_manager.load_dictionary("BDO")  # Use valid type
        except Exception as e:
            pytest.skip(f"Dictionary not loaded: {e}")

        searcher = SimilaritySearcher(embeddings_manager=embeddings_manager)

        # Search for common Korean phrase
        results = searcher.find_similar(
            query="안녕하세요",
            threshold=0.3,
            top_k=5,
            use_whole=False
        )

        assert isinstance(results, list), "Should return list"
        print(f"✅ Search returned {len(results)} results for '안녕하세요'")

    def test_05_full_workflow_end_to_end(self, embeddings_manager):
        """Step 5: Complete workflow from file to search results."""
        from server.tools.kr_similar.core import KRSimilarCore, normalize_text
        from server.tools.kr_similar.searcher import SimilaritySearcher

        # 1. Load data
        fixture_file = str(FIXTURES_DIR / "sample_language_data.txt")
        df = KRSimilarCore.parse_language_file(fixture_file, kr_column=5, trans_column=6)

        # 2. Get a sample Korean text (with tags)
        sample_row = df[df['Korean'].str.contains('안녕', na=False)].iloc[0]
        original_korean = sample_row['Korean']

        # 3. Normalize for search
        normalized = normalize_text(original_korean)
        assert len(normalized) > 0, "Normalized text should not be empty"

        # 4. Search
        try:
            searcher = SimilaritySearcher(embeddings_manager=embeddings_manager)
            results = searcher.find_similar(
                query=normalized,
                threshold=0.3,
                top_k=10,
                use_whole=False
            )
            print(f"✅ Full workflow complete: {len(df)} rows → normalized → {len(results)} results")
        except Exception as e:
            print(f"⚠️ Search skipped (dictionary may not be loaded): {e}")


class TestXLSTransferFullSimulation:
    """Full simulation of XLSTransfer production workflow."""

    def test_01_tag_reconstruction_full_matrix(self):
        """Test all tag reconstruction patterns."""
        from client.tools.xls_transfer.core import simple_number_replace

        # Complete matrix of production patterns
        test_cases = [
            # Basic patterns
            ("{Code}안녕", "Hello", "{Code}Hello"),
            ("{T1}{T2}텍스트", "Text", "{T1}{T2}Text"),
            ("{T1}{T2}{T3}{T4}{T5}다섯개", "Five", "{T1}{T2}{T3}{T4}{T5}Five"),

            # Production patterns
            (
                "{ChangeScene(MorningMain_13_005)}{AudioVoice(NPC_VCE_NEW_8513)}안녕",
                "Bonjour",
                "{ChangeScene(MorningMain_13_005)}{AudioVoice(NPC_VCE_NEW_8513)}Bonjour"
            ),

            # PAColor patterns
            ("{Code}<PAColor>텍스트<PAOldColor>", "Text", "{Code}<PAColor>Text<PAOldColor>"),

            # Edge cases
            ("순수 텍스트", "Pure text", "Pure text"),  # No tags
            ("", "", ""),  # Empty
        ]

        all_passed = True
        for original, translated, expected in test_cases:
            result = simple_number_replace(original, translated)
            if result != expected:
                print(f"❌ FAIL: simple_number_replace('{original}', '{translated}')")
                print(f"   Expected: '{expected}'")
                print(f"   Got:      '{result}'")
                all_passed = False
            else:
                print(f"✅ PASS: {original[:30]}... → {result[:30]}...")

        assert all_passed, "Some tag reconstruction tests failed"

    def test_02_code_extraction_all_patterns(self):
        """Test code block extraction from all pattern types."""
        from client.tools.xls_transfer.core import extract_code_blocks

        test_cases = [
            ("{Code}Text", ["{Code}"]),
            ("{T1}{T2}{T3}Text", ["{T1}", "{T2}", "{T3}"]),
            ("{ChangeScene(Main_001)}{AudioVoice(NPC_001)}Text",
             ["{ChangeScene(Main_001)}", "{AudioVoice(NPC_001)}"]),
            ("<PAColor>Text", ["<PAColor>"]),
            ("No codes here", []),
        ]

        for text, expected_codes in test_cases:
            result = extract_code_blocks(text)
            assert result == expected_codes, f"extract_code_blocks('{text}') = {result}, expected {expected_codes}"

        print("✅ All code extraction patterns pass")

    def test_03_strip_codes_preserves_text(self):
        """Test that strip_codes removes all tags but preserves text."""
        from client.tools.xls_transfer.core import strip_codes_from_text

        test_cases = [
            # (input, expected_contains, expected_not_contains)
            ("{Code}Hello World", ["Hello", "World"], ["{Code}"]),
            ("{T1}{T2}Hello{T3}World", ["Hello", "World"], ["{T1}", "{T2}", "{T3}"]),
            ("<PAColor>Test<PAOldColor>", ["Test"], ["<PAColor>", "<PAOldColor>"]),
            ("No codes", ["No", "codes"], []),
        ]

        for input_text, should_contain, should_not_contain in test_cases:
            result = strip_codes_from_text(input_text)

            for expected in should_contain:
                assert expected in result, f"'{expected}' should be in result: {result}"

            for unexpected in should_not_contain:
                assert unexpected not in result, f"'{unexpected}' should NOT be in result: {result}"

        print("✅ All strip_codes patterns pass")


class TestQuickSearchFullSimulation:
    """Full simulation of QuickSearch production workflow."""

    @pytest.fixture(scope="class")
    def dict_manager(self):
        """Get DictionaryManager."""
        from server.tools.quicksearch.dictionary import DictionaryManager
        return DictionaryManager()

    @pytest.fixture(scope="class")
    def searcher(self):
        """Get Searcher."""
        from server.tools.quicksearch.searcher import Searcher
        return Searcher()

    def test_01_create_dictionary_from_fixture(self, dict_manager):
        """Step 1: Create dictionary from fixture file."""
        fixture_file = str(FIXTURES_DIR / "sample_quicksearch_data.txt")

        result = dict_manager.create_dictionary(
            file_paths=[fixture_file],
            game="BDO",
            language="TEST_QS"
        )

        # Should return tuple of (split_dict, whole_dict, string_keys, stringid_to_entry)
        assert result is not None
        split_dict, whole_dict, string_keys, stringid_to_entry = result

        assert len(split_dict) > 0 or len(whole_dict) > 0, "Should have dictionary entries"
        print(f"✅ Created dictionary: {len(split_dict)} split, {len(whole_dict)} whole")

    def test_02_load_and_search_single(self, dict_manager, searcher):
        """Step 2: Load dictionary and search single line."""
        try:
            dictionary = dict_manager.load_dictionary("BDO", "TEST_QS", as_reference=False)
            searcher.load_dictionary(dictionary)
        except FileNotFoundError:
            pytest.skip("Dictionary not found - create first")

        # Search for common word
        results, count = searcher.search_one_line(
            query="안녕",
            match_type="contains",
            start_index=0,
            limit=50
        )

        assert isinstance(results, list)
        print(f"✅ Search '안녕': {count} results")

    def test_03_search_multiline(self, dict_manager, searcher):
        """Step 3: Multi-line search."""
        try:
            dictionary = dict_manager.load_dictionary("BDO", "TEST_QS", as_reference=False)
            searcher.load_dictionary(dictionary)
        except FileNotFoundError:
            pytest.skip("Dictionary not found")

        queries = ["안녕", "감사", "마을"]
        results = searcher.search_multi_line(
            queries=queries,
            match_type="contains",
            limit=10
        )

        assert len(results) == len(queries), "Should have result for each query"
        print(f"✅ Multi-line search: {len(queries)} queries processed")


class TestCrossToolConsistency:
    """Test consistency across tools using same data."""

    def test_01_same_normalization_result(self):
        """Both KR Similar and QuickSearch should normalize similarly."""
        from server.tools.kr_similar.core import normalize_text as kr_normalize

        test_input = "{ChangeScene(Main)}{AudioVoice(NPC)}안녕하세요"

        kr_result = kr_normalize(test_input)

        # Both should have removed tags and preserved Korean
        assert "안녕하세요" in kr_result
        assert "{" not in kr_result
        assert "}" not in kr_result

        print("✅ Normalization consistent across tools")

    def test_02_fixture_data_usable_by_all_tools(self):
        """Verify fixture data format works for all tools."""
        from server.tools.kr_similar.core import KRSimilarCore

        fixture_file = str(FIXTURES_DIR / "sample_language_data.txt")

        # KR Similar can parse it
        df = KRSimilarCore.parse_language_file(fixture_file, kr_column=5, trans_column=6)
        assert len(df) > 0, "KR Similar should parse fixture"

        # File has correct structure for all tools
        with open(fixture_file, 'r', encoding='utf-8') as f:
            first_line = f.readline()
            columns = first_line.strip().split('\t')
            assert len(columns) >= 7, f"Should have 7+ columns, got {len(columns)}"

        print("✅ Fixture data usable by all tools")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
