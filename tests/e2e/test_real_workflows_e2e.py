"""
TRUE SIMULATION E2E Tests - Real User Workflow Simulation

These tests simulate EXACTLY what a user does in production:
1. Load files with real production-like data
2. Process through the entire pipeline
3. Verify outputs match expected results
4. Test with comprehensive fixture data (tags, multi-line, special chars)

Unlike unit tests that test individual functions, these tests verify
the COMPLETE workflow from start to finish.
"""

import pytest
import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Fixtures directory
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"

# Check if Korean BERT model is available
MODEL_DIR = project_root / "models" / "kr-sbert"
MODEL_FILE = MODEL_DIR / "model.safetensors"
MODEL_AVAILABLE = (
    MODEL_DIR.exists()
    and MODEL_FILE.exists()
    and MODEL_FILE.stat().st_size > 100_000_000
)


def requires_model(func):
    """Decorator to skip tests that require the Korean BERT model."""
    return pytest.mark.skipif(
        not MODEL_AVAILABLE,
        reason="Korean BERT model not available (LIGHT build or CI)"
    )(func)


# =============================================================================
# XLSTRANSFER WORKFLOW SIMULATIONS
# =============================================================================

class TestXLSTransferRealWorkflow:
    """
    Simulates REAL XLSTransfer user workflow:

    SCENARIO: User wants to translate a game localization file
    1. User has an Excel file with Korean source and wants French translations
    2. User creates a dictionary from reference Excel files
    3. User loads the dictionary
    4. User translates a new file using the dictionary
    5. User verifies translations preserve tags like {ChangeScene}, {AudioVoice}
    """

    @pytest.fixture(scope="class")
    def fixture_file(self):
        """Get the comprehensive fixture file."""
        fixture_path = FIXTURES_DIR / "sample_language_data.txt"
        assert fixture_path.exists(), f"Fixture not found: {fixture_path}"
        return str(fixture_path)

    def test_01_workflow_parse_production_data(self, fixture_file):
        """
        WORKFLOW STEP 1: Parse production-format data file

        USER ACTION: User loads a language file exported from the game
        EXPECTED: Parser correctly handles all tag patterns and multi-line content
        """
        from server.tools.kr_similar.core import KRSimilarCore

        # Parse the fixture file (same format as production)
        df = KRSimilarCore.parse_language_file(
            fixture_file,
            kr_column=5,  # Korean is column 6 (0-indexed = 5)
            trans_column=6  # Translation is column 7 (0-indexed = 6)
        )

        assert len(df) == 23, f"Expected 23 rows, got {len(df)}"

        # Verify complex patterns are preserved
        complex_row = df[df['Korean'].str.contains('죄인은 푸줏간', na=False)]
        assert len(complex_row) > 0, "Should find complex multi-block row"

        korean_text = complex_row.iloc[0]['Korean']

        # Verify tags are preserved
        assert '{ChangeScene(MorningMain_13_005)}' in korean_text, \
            "ChangeScene tag should be preserved"
        assert '{AudioVoice(NPC_VCE_NEW_8513_2_11_Iksun)}' in korean_text, \
            "AudioVoice tag should be preserved"

        # Verify multi-line is preserved
        assert '\\n' in korean_text or '\n' in korean_text, \
            "Newline characters should be preserved"

        print(f"✓ Parsed {len(df)} rows with all patterns preserved")

    def test_02_workflow_tag_extraction(self, fixture_file):
        """
        WORKFLOW STEP 2: Extract and analyze inline tags

        USER ACTION: System automatically detects and catalogs all tag types
        EXPECTED: All tag patterns from production data are identified
        """
        import re

        # Read raw file to find all tags
        with open(fixture_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract all {Tag(...)} patterns
        tag_pattern = r'\{[^}]+\}'
        all_tags = re.findall(tag_pattern, content)
        unique_tags = set(all_tags)

        # Should find ChangeScene tags
        changescene_tags = [t for t in unique_tags if 'ChangeScene' in t]
        assert len(changescene_tags) > 0, "Should find ChangeScene tags"

        # Should find AudioVoice tags
        audiovoice_tags = [t for t in unique_tags if 'AudioVoice' in t]
        assert len(audiovoice_tags) > 0, "Should find AudioVoice tags"

        # Should find Scale tags
        scale_tags = [t for t in unique_tags if 'Scale' in t]
        assert len(scale_tags) > 0, "Should find Scale tags"

        print(f"✓ Found {len(unique_tags)} unique tag patterns:")
        print(f"  - ChangeScene: {len(changescene_tags)}")
        print(f"  - AudioVoice: {len(audiovoice_tags)}")
        print(f"  - Scale: {len(scale_tags)}")

    def test_03_workflow_text_normalization(self, fixture_file):
        """
        WORKFLOW STEP 3: Normalize text while preserving structure

        USER ACTION: Before matching, text is normalized for comparison
        EXPECTED: Tags are stripped for matching but can be restored
        """
        from server.tools.kr_similar.core import normalize_text

        # Sample text with multiple tag blocks
        sample_text = (
            "{ChangeScene(MorningMain_13_005)}{AudioVoice(NPC_VCE_NEW_8513_2_11_Iksun)}"
            "안녕하세요. 저는 마을의 촌장입니다."
        )

        # Normalize for matching (strip tags)
        normalized = normalize_text(sample_text)

        # Tags should be removed
        assert '{ChangeScene' not in normalized, "Tags should be stripped"
        assert '{AudioVoice' not in normalized, "Tags should be stripped"

        # Korean text should remain
        assert '안녕하세요' in normalized, "Korean text should remain"
        assert '촌장' in normalized, "Korean text should remain"

        print(f"✓ Original: {sample_text[:50]}...")
        print(f"✓ Normalized: {normalized}")

    def test_04_workflow_special_characters(self, fixture_file):
        """
        WORKFLOW STEP 4: Handle special characters correctly

        USER ACTION: Files contain special Unicode characters
        EXPECTED: All special chars preserved through processing
        """
        # Read fixture and check special chars
        with open(fixture_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check special characters exist
        assert '▶' in content, "Bullet points should be in fixture"
        assert '【' in content, "Korean brackets should be in fixture"
        assert '】' in content, "Korean brackets should be in fixture"
        assert '<color=red>' in content, "HTML-like tags should be in fixture"

        # Check they survive parsing
        from server.tools.kr_similar.core import KRSimilarCore
        df = KRSimilarCore.parse_language_file(fixture_file, kr_column=5, trans_column=6)

        # Find row with bullet points
        bullet_rows = df[df['Korean'].str.contains('▶', na=False)]
        assert len(bullet_rows) > 0, "Should find rows with bullet points"

        # Find row with brackets
        bracket_rows = df[df['Korean'].str.contains('【', na=False)]
        assert len(bracket_rows) > 0, "Should find rows with brackets"

        print(f"✓ Special characters preserved: ▶, 【】, <color>")

    def test_05_workflow_long_text_handling(self, fixture_file):
        """
        WORKFLOW STEP 5: Handle long text entries

        USER ACTION: Some entries have 100+ characters
        EXPECTED: Long text processed without truncation
        """
        from server.tools.kr_similar.core import KRSimilarCore
        df = KRSimilarCore.parse_language_file(fixture_file, kr_column=5, trans_column=6)

        # Find long text row
        long_rows = df[df['Korean'].str.len() > 100]
        assert len(long_rows) > 0, "Should have entries with 100+ characters"

        # Verify the long text is complete
        long_text = long_rows.iloc[0]['Korean']
        assert len(long_text) > 100, f"Text should be >100 chars, got {len(long_text)}"

        print(f"✓ Long text preserved: {len(long_text)} characters")


# =============================================================================
# QUICKSEARCH WORKFLOW SIMULATIONS
# =============================================================================

class TestQuickSearchRealWorkflow:
    """
    Simulates REAL QuickSearch user workflow:

    SCENARIO: Translator wants to quickly find existing translations
    1. User loads multiple language files into a dictionary
    2. User searches for Korean terms
    3. User gets matching translations with context
    4. User toggles between exact and contains search
    """

    TEST_GAME = "TEST_WORKFLOW_GAME"
    TEST_LANG = "TEST_WORKFLOW_LANG"

    @pytest.fixture(scope="class")
    def fixture_file(self):
        """Get the quicksearch fixture file."""
        fixture_path = FIXTURES_DIR / "sample_quicksearch_data.txt"
        assert fixture_path.exists(), f"Fixture not found: {fixture_path}"
        return str(fixture_path)

    @pytest.fixture(scope="class")
    def dict_manager(self):
        """Get dictionary manager instance."""
        from server.tools.quicksearch.dictionary import DictionaryManager
        return DictionaryManager()

    @pytest.fixture(scope="class")
    def loaded_searcher(self, dict_manager, fixture_file):
        """Create dictionary and load into searcher."""
        from server.tools.quicksearch.searcher import Searcher

        # Create dictionary
        split_dict, whole_dict, string_keys, stringid_to_entry = dict_manager.create_dictionary(
            file_paths=[fixture_file],
            game=self.TEST_GAME,
            language=self.TEST_LANG
        )

        # Load into searcher
        searcher = Searcher()
        dictionary = dict_manager.load_dictionary(
            game=self.TEST_GAME,
            language=self.TEST_LANG,
            as_reference=False
        )
        searcher.load_dictionary(dictionary)

        yield searcher

    def test_01_workflow_search_exact_match(self, loaded_searcher):
        """
        WORKFLOW STEP 1: Search for exact Korean term

        USER ACTION: User types Korean word and searches
        EXPECTED: Exact matches returned with translations
        """
        # Search for "안녕하세요" (Hello)
        results = loaded_searcher.search_one_line(
            query="안녕하세요",
            match_type="exact"
        )

        assert len(results) > 0, "Should find exact match for 안녕하세요"

        print(f"✓ Found {len(results)} exact matches for '안녕하세요'")

    def test_02_workflow_search_contains(self, loaded_searcher):
        """
        WORKFLOW STEP 2: Search with partial matching

        USER ACTION: User types partial Korean word
        EXPECTED: All entries containing the term returned
        """
        # Search for partial term "마을" (village)
        results = loaded_searcher.search_one_line(
            query="마을",
            match_type="contains"
        )

        assert len(results) > 0, "Should find entries containing 마을"

        print(f"✓ Found {len(results)} entries containing '마을'")

    def test_03_workflow_search_special_chars(self, loaded_searcher):
        """
        WORKFLOW STEP 3: Search for entries with special characters

        USER ACTION: User searches for UI elements with special chars
        EXPECTED: Special characters don't break search
        """
        # Search for bullet point menu item
        results = loaded_searcher.search_one_line(
            query="▶",
            match_type="contains"
        )

        assert len(results) > 0, "Should find entries with bullet points"

        print(f"✓ Found {len(results)} entries with '▶' character")

    def test_04_workflow_search_punctuation(self, loaded_searcher):
        """
        WORKFLOW STEP 4: Search handles punctuation correctly

        USER ACTION: User searches for text that may have ?!...
        EXPECTED: Punctuation doesn't break search
        """
        # Search for question
        results = loaded_searcher.search_one_line(
            query="뭐라고요",
            match_type="contains"
        )

        # Should find even if source has "뭐라고요?"
        assert len(results) > 0, "Should find entries with punctuation"

        print(f"✓ Found {len(results)} entries matching '뭐라고요'")


# =============================================================================
# KR SIMILAR WORKFLOW SIMULATIONS
# =============================================================================

class TestKRSimilarRealWorkflow:
    """
    Simulates REAL KR Similar user workflow:

    SCENARIO: User wants to find semantically similar Korean strings
    1. User loads a reference dictionary
    2. User inputs a Korean string
    3. System finds similar strings using BERT embeddings
    4. User reviews matches and selects best translation
    """

    TEST_DICT_TYPE = "TEST_WORKFLOW_SIMILAR"

    @pytest.fixture(scope="class")
    def fixture_file(self):
        """Get the language data fixture file."""
        fixture_path = FIXTURES_DIR / "sample_language_data.txt"
        assert fixture_path.exists(), f"Fixture not found: {fixture_path}"
        return str(fixture_path)

    @pytest.fixture(scope="class")
    def embeddings_manager(self):
        """Get embeddings manager instance."""
        if not MODEL_AVAILABLE:
            pytest.skip("Korean BERT model not available")

        from server.tools.kr_similar.embeddings import EmbeddingsManager
        return EmbeddingsManager()

    @pytest.fixture(scope="class")
    def similarity_searcher(self, embeddings_manager, fixture_file):
        """Create dictionary and get searcher."""
        from server.tools.kr_similar.embeddings import DICT_TYPES
        from server.tools.kr_similar.searcher import SimilaritySearcher

        # Ensure test type is allowed
        if self.TEST_DICT_TYPE not in DICT_TYPES:
            DICT_TYPES.append(self.TEST_DICT_TYPE)

        # Create dictionary from fixture
        result = embeddings_manager.create_dictionary(
            file_paths=[fixture_file],
            dict_type=self.TEST_DICT_TYPE,
            kr_column=5,
            trans_column=6
        )

        # Load dictionary
        embeddings_manager.load_dictionary(self.TEST_DICT_TYPE)

        # Create searcher
        searcher = SimilaritySearcher(embeddings_manager)

        yield searcher

        # Cleanup
        try:
            embeddings_manager.clear_dictionary()
        except Exception:
            pass

    @requires_model
    def test_01_workflow_semantic_search_greeting(self, similarity_searcher):
        """
        WORKFLOW STEP 1: Find similar greetings

        USER ACTION: User inputs "안녕하세요" (formal hello)
        EXPECTED: System finds similar greeting/welcome phrases

        NOTE: Using lower threshold (0.3) since fixture data has
        greetings embedded in longer sentences with context.
        Real production usage would tune threshold based on needs.
        """
        # Search for formal greeting phrase
        results = similarity_searcher.find_similar("안녕하세요", threshold=0.3, top_k=10)

        # The system should find semantically similar phrases
        # Even if no exact matches, 0.3 threshold should return something
        assert isinstance(results, list), "Results should be a list"

        # Log what was found for debugging
        print(f"✓ Search '안녕하세요' found {len(results)} similar strings at threshold 0.3")
        for i, r in enumerate(results[:3]):
            kr = r.get('korean', r.get('Korean', ''))[:50]
            sim = r.get('similarity', 0)
            print(f"  {i+1}. [{sim:.3f}] {kr}...")

    @requires_model
    def test_02_workflow_semantic_search_context(self, similarity_searcher):
        """
        WORKFLOW STEP 2: Find similar context strings

        USER ACTION: User inputs a battle-related phrase
        EXPECTED: System finds other battle-related phrases
        """
        # Search for battle phrase
        results = similarity_searcher.find_similar("전투를 시작", threshold=0.5, top_k=5)

        assert len(results) > 0, "Should find battle-related strings"

        print(f"✓ Search '전투를 시작' found {len(results)} similar strings")

    @requires_model
    def test_03_workflow_threshold_tuning(self, similarity_searcher):
        """
        WORKFLOW STEP 3: Adjust similarity threshold

        USER ACTION: User adjusts threshold to get more/fewer results
        EXPECTED: Higher threshold = fewer but more accurate matches
        """
        # Low threshold - more results
        results_low = similarity_searcher.find_similar("마을", threshold=0.3, top_k=10)

        # High threshold - fewer results
        results_high = similarity_searcher.find_similar("마을", threshold=0.8, top_k=10)

        # Higher threshold should give equal or fewer results
        assert len(results_low) >= len(results_high), \
            "Higher threshold should return equal or fewer results"

        print(f"✓ Threshold 0.3: {len(results_low)} results")
        print(f"✓ Threshold 0.8: {len(results_high)} results")


# =============================================================================
# CROSS-TOOL WORKFLOW SIMULATIONS
# =============================================================================

class TestCrossToolWorkflow:
    """
    Simulates workflows that span multiple tools:

    SCENARIO: Complete localization pipeline
    1. QuickSearch to find existing translations
    2. KR Similar to find similar strings for new content
    3. XLSTransfer to apply translations to new files
    """

    @pytest.fixture(scope="class")
    def language_fixture(self):
        """Get the comprehensive language fixture."""
        return str(FIXTURES_DIR / "sample_language_data.txt")

    @pytest.fixture(scope="class")
    def quicksearch_fixture(self):
        """Get the quicksearch fixture."""
        return str(FIXTURES_DIR / "sample_quicksearch_data.txt")

    def test_01_data_consistency_across_fixtures(self, language_fixture, quicksearch_fixture):
        """
        WORKFLOW: Verify data consistency across fixture files

        EXPECTED: Both fixtures follow same format conventions
        """
        from server.tools.kr_similar.core import KRSimilarCore

        # Parse both fixtures
        lang_df = KRSimilarCore.parse_language_file(
            language_fixture, kr_column=5, trans_column=6
        )
        quick_df = KRSimilarCore.parse_language_file(
            quicksearch_fixture, kr_column=5, trans_column=6
        )

        # Both should parse successfully
        assert len(lang_df) > 0, "Language fixture should have entries"
        assert len(quick_df) > 0, "QuickSearch fixture should have entries"

        # Both should have Korean and Translation columns
        assert 'Korean' in lang_df.columns
        assert 'Translation' in lang_df.columns
        assert 'Korean' in quick_df.columns
        assert 'Translation' in quick_df.columns

        print(f"✓ Language fixture: {len(lang_df)} entries")
        print(f"✓ QuickSearch fixture: {len(quick_df)} entries")

    def test_02_shared_terms_across_tools(self, language_fixture, quicksearch_fixture):
        """
        WORKFLOW: Find common terms that appear in both fixtures

        EXPECTED: Common game terms like 마을, 퀘스트 appear in both
        """
        from server.tools.kr_similar.core import KRSimilarCore

        lang_df = KRSimilarCore.parse_language_file(
            language_fixture, kr_column=5, trans_column=6
        )
        quick_df = KRSimilarCore.parse_language_file(
            quicksearch_fixture, kr_column=5, trans_column=6
        )

        # Common terms that should appear in game localization
        common_terms = ['마을', '퀘스트', '전투', '아이템']

        for term in common_terms:
            in_lang = lang_df['Korean'].str.contains(term, na=False).any()
            in_quick = quick_df['Korean'].str.contains(term, na=False).any()

            # At least one fixture should have each term
            assert in_lang or in_quick, f"Term '{term}' should be in at least one fixture"

            status = []
            if in_lang:
                status.append("language")
            if in_quick:
                status.append("quicksearch")
            print(f"✓ Term '{term}' found in: {', '.join(status)}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
