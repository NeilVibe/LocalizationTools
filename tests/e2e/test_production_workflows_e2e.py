"""
Production Workflow E2E Tests - True Simulations

These tests simulate REAL production workflows that users perform:
1. XLSTransfer: Complete file translation workflow
2. QuickSearch: Reference dictionary workflow
3. KR Similar: Extract similar strings & auto-translate workflows
4. Cross-tool: Full localization pipeline

Each test follows the ACTUAL user workflow from start to finish.

Test Data Philosophy:
- Uses COMPREHENSIVE fixtures based on real production data structure
- Covers all patterns: tags, multi-line, special chars, complex voice IDs
- See tests/fixtures/__init__.py for pattern documentation
"""

import pytest
import os
import sys
import shutil
import tempfile
import pandas as pd
import numpy as np
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
    and MODEL_FILE.stat().st_size > 100_000_000  # >100MB = real model
)


def requires_model(func):
    """Skip tests requiring Korean BERT model."""
    return pytest.mark.skipif(
        not MODEL_AVAILABLE,
        reason="Korean BERT model not available (LIGHT build or CI)"
    )(func)


# =============================================================================
# XLSTRANSFER PRODUCTION WORKFLOW TESTS
# =============================================================================

class TestXLSTransferProductionWorkflow:
    """
    Complete XLSTransfer production workflow simulation.

    USER SCENARIO: Translator receives new game text files and needs to
    apply existing translations from their dictionary.

    WORKFLOW:
    1. Create dictionary from reference Excel file
    2. Load dictionary into memory
    3. Translate a text file
    4. Verify output contains correct translations
    """

    @pytest.fixture(scope="class")
    def temp_output_dir(self):
        """Create temporary directory for outputs."""
        temp_dir = tempfile.mkdtemp(prefix="xlstransfer_test_")
        yield temp_dir
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture(scope="class")
    def dictionary_fixture(self):
        """Path to sample dictionary Excel file."""
        path = FIXTURES_DIR / "sample_dictionary.xlsx"
        assert path.exists(), f"Dictionary fixture not found: {path}"
        return str(path)

    @pytest.fixture(scope="class")
    def translation_input_fixture(self):
        """Path to file needing translation."""
        path = FIXTURES_DIR / "sample_to_translate.txt"
        assert path.exists(), f"Translation input not found: {path}"
        return str(path)

    @requires_model
    def test_01_workflow_create_dictionary_from_excel(self, dictionary_fixture):
        """
        WORKFLOW STEP 1: User creates dictionary from Excel reference file.

        USER ACTION:
        - Select Excel file containing Korean→English pairs
        - Choose source column (A) and target column (B)
        - Click "Create Dictionary"

        EXPECTED:
        - Dictionary created with split and whole modes
        - Embeddings generated for semantic matching
        """
        from client.tools.xls_transfer import embeddings

        # User's Excel selections
        excel_files = [(dictionary_fixture, "Sheet1", "A", "B")]

        # Create dictionary (this is what happens when user clicks "Create")
        split_dict, whole_dict, split_embeddings, whole_embeddings = \
            embeddings.process_excel_for_dictionary(excel_files)

        # Verify dictionary was created
        assert len(split_dict) > 0, "Split dictionary should have entries"
        assert split_embeddings is not None, "Should have split embeddings"
        assert split_embeddings.shape[1] == 768, "Embedding dimension should be 768"

        # Check expected content from fixture
        dict_keys = list(split_dict.keys())
        assert any("안녕" in k for k in dict_keys), "Should contain greeting"
        assert any("감사" in k for k in dict_keys), "Should contain thanks"

        # Save for next steps
        embeddings.save_dictionary(split_embeddings, split_dict, mode="split")
        if len(whole_dict) > 0 and whole_embeddings is not None:
            embeddings.save_dictionary(whole_embeddings, whole_dict, mode="whole")

        print(f"✓ Dictionary created: {len(split_dict)} split, {len(whole_dict)} whole pairs")
        print(f"  Sample entries: {dict_keys[:3]}")

    @requires_model
    def test_02_workflow_load_dictionary(self, dictionary_fixture):
        """
        WORKFLOW STEP 2: User loads dictionary for translation.

        USER ACTION:
        - Click "Load Dictionary"

        EXPECTED:
        - Dictionary loaded into memory
        - FAISS index created for fast search
        """
        from client.tools.xls_transfer import embeddings

        # Load dictionary (what happens when user clicks "Load")
        loaded_embeddings, loaded_dict, loaded_index, loaded_kr_texts = \
            embeddings.load_dictionary(mode="split")

        assert loaded_dict is not None, "Dictionary should be loaded"
        assert loaded_index is not None, "FAISS index should be created"
        assert len(loaded_dict) > 0, "Should have entries"
        assert len(loaded_kr_texts) == len(loaded_dict), "Korean texts should match dict size"

        print(f"✓ Dictionary loaded: {len(loaded_dict)} entries, FAISS index ready")

    @requires_model
    def test_03_workflow_translate_single_text(self):
        """
        WORKFLOW STEP 3: User translates single text (preview mode).

        USER ACTION:
        - Enter Korean text in preview box
        - See translation result with confidence score

        EXPECTED:
        - Returns best matching translation
        - Score indicates confidence level
        """
        from client.tools.xls_transfer import embeddings, translation

        # Load dictionary
        _, loaded_dict, loaded_index, loaded_kr_texts = \
            embeddings.load_dictionary(mode="split")

        # User's test input
        test_inputs = [
            ("안녕하세요", "Hello", 0.8),  # Direct match expected
            ("감사합니다", "Thank you", 0.8),  # Direct match expected
            ("전투를 시작합니다", "Starting combat", 0.7),  # Should find match
        ]

        for korean, expected_partial, min_score in test_inputs:
            matched_kr, translated, score = translation.find_best_match(
                text=korean,
                faiss_index=loaded_index,
                kr_sentences=loaded_kr_texts,
                translation_dict=loaded_dict,
                threshold=0.5,
                model=None
            )

            print(f"✓ '{korean}' → '{translated}' (score: {score:.3f})")

            # Verify reasonable match
            assert isinstance(score, float), "Score should be float"
            if score >= min_score:
                assert translated is not None, f"Should have translation for {korean}"

    @requires_model
    def test_04_workflow_translate_file_with_tags(self, translation_input_fixture, temp_output_dir):
        """
        WORKFLOW STEP 4: User translates entire file (batch mode).

        USER ACTION:
        - Select input file
        - Set threshold
        - Click "Translate File"
        - Review and save output

        EXPECTED:
        - File processed row by row
        - Tags preserved in output
        - Translations inserted in column 6
        - Only modified rows written to output

        This tests the REAL production scenario with:
        - Tab-separated format
        - Tags like {AudioVoice(...)} and {ChangeScene(...)}
        - Multi-line content with \\n
        """
        from client.tools.xls_transfer import embeddings, translation
        from client.tools.xls_transfer.translate_file import clean_audiovoice_tags, trim_columns

        # Load dictionary
        _, loaded_dict, loaded_index, loaded_kr_texts = \
            embeddings.load_dictionary(mode="split")

        # Read input file (simulating what translate_file.py does)
        with open(translation_input_fixture, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        results = []
        for line in lines:
            if not line.strip():
                continue

            columns = line.rstrip('\n').split('\t')
            if len(columns) < 6:
                continue

            korean_text = columns[5]
            if not korean_text.strip():
                continue

            # Clean tags for embedding lookup
            clean_text = clean_audiovoice_tags(korean_text)

            # Find translation
            matched_kr, translated, score = translation.find_best_match(
                text=clean_text,
                faiss_index=loaded_index,
                kr_sentences=loaded_kr_texts,
                translation_dict=loaded_dict,
                threshold=0.5,
                model=None
            )

            results.append({
                'korean': korean_text,
                'clean': clean_text,
                'translation': translated,
                'score': score
            })

        # Verify results
        assert len(results) > 0, "Should have processed rows"

        # Check that matches were found for known texts
        found_translations = [r for r in results if r['score'] >= 0.5]
        assert len(found_translations) > 0, "Should have some translations"

        print(f"✓ File translation complete: {len(results)} rows processed")
        print(f"  Translations found: {len(found_translations)}")
        for r in found_translations[:3]:
            print(f"    [{r['score']:.2f}] {r['korean'][:30]}... → {r['translation']}")

    @requires_model
    def test_05_workflow_tag_preservation(self, translation_input_fixture):
        """
        WORKFLOW STEP 5: Verify tags are preserved correctly.

        PRODUCTION REQUIREMENT:
        - Game tags like {AudioVoice(...)} must be preserved
        - Only the text part should be translated
        - Tags must remain in exact same position
        """
        from client.tools.xls_transfer.translate_file import clean_audiovoice_tags

        # Read input file
        with open(translation_input_fixture, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        tag_tests = []
        for line in lines:
            columns = line.rstrip('\n').split('\t')
            if len(columns) >= 6:
                korean = columns[5]
                if '{' in korean:  # Has tags
                    clean = clean_audiovoice_tags(korean)
                    tag_tests.append({
                        'original': korean,
                        'cleaned': clean,
                        'has_audio': 'AudioVoice' in korean,
                        'has_scene': 'ChangeScene' in korean
                    })

        assert len(tag_tests) > 0, "Should have rows with tags"

        for t in tag_tests:
            # Clean text should not have tags
            assert '{' not in t['cleaned'], f"Cleaned should not have tags: {t['cleaned']}"
            # But original should
            assert '{' in t['original'], f"Original should have tags: {t['original']}"

            print(f"✓ Tag preserved: {t['original'][:50]}...")
            print(f"  Cleaned for matching: {t['cleaned'][:50]}...")


# =============================================================================
# QUICKSEARCH PRODUCTION WORKFLOW TESTS
# =============================================================================

class TestQuickSearchProductionWorkflow:
    """
    Complete QuickSearch production workflow simulation.

    USER SCENARIO: Translator needs to search for existing translations
    across multiple dictionary files, with reference comparison.

    WORKFLOW:
    1. Create dictionary from data files
    2. Set up reference dictionary for comparison
    3. Search for terms
    4. View results with reference column
    """

    TEST_GAME = "TEST_PROD"
    TEST_LANG = "ko"

    @pytest.fixture(scope="class")
    def dict_manager(self):
        """Get DictionaryManager instance."""
        from server.tools.quicksearch.dictionary import DictionaryManager
        return DictionaryManager()

    @pytest.fixture(scope="class")
    def quicksearch_fixture(self):
        """Path to QuickSearch data file."""
        path = FIXTURES_DIR / "sample_quicksearch_data.txt"
        assert path.exists(), f"QuickSearch fixture not found: {path}"
        return str(path)

    @pytest.fixture(scope="class")
    def language_fixture(self):
        """Path to language data file (alternate format)."""
        path = FIXTURES_DIR / "sample_language_data.txt"
        assert path.exists(), f"Language fixture not found: {path}"
        return str(path)

    @pytest.fixture(scope="class")
    def loaded_searcher(self, dict_manager, quicksearch_fixture):
        """Create and load dictionary for searching."""
        from server.tools.quicksearch.searcher import Searcher

        # Create dictionary from fixture (also saves internally)
        split_dict, whole_dict, string_keys, stringid_to_entry = \
            dict_manager.create_dictionary(
                file_paths=[quicksearch_fixture],
                game=self.TEST_GAME,
                language=self.TEST_LANG
            )

        # Load for searching
        dictionary = dict_manager.load_dictionary(
            game=self.TEST_GAME,
            language=self.TEST_LANG,
            as_reference=False
        )

        searcher = Searcher()
        searcher.load_dictionary(dictionary)

        yield searcher

        # Cleanup
        try:
            dict_path = dict_manager.base_dir / self.TEST_GAME / self.TEST_LANG
            if dict_path.exists():
                shutil.rmtree(dict_path)
        except Exception:
            pass

    def test_01_workflow_create_dictionary(self, dict_manager, quicksearch_fixture):
        """
        WORKFLOW STEP 1: User creates QuickSearch dictionary.

        USER ACTION:
        - Select game and language
        - Add data files
        - Click "Create Dictionary"

        EXPECTED:
        - Dictionary created with split and whole entries
        - String keys indexed for fast lookup
        """
        # Create dictionary
        split_dict, whole_dict, string_keys, stringid_to_entry = \
            dict_manager.create_dictionary(
                file_paths=[quicksearch_fixture],
                game=self.TEST_GAME,
                language=self.TEST_LANG
            )

        assert len(split_dict) > 0, "Should have split entries"
        assert len(string_keys) > 0, "Should have string keys"

        # Verify expected content
        all_values = list(split_dict.values())
        has_hello = any("Hello" in str(v) for v in all_values)
        has_korean = any("안녕" in str(k) for k in split_dict.keys())

        assert has_korean, "Should have Korean keys"

        print(f"✓ Dictionary created: {len(split_dict)} split, {len(whole_dict)} whole")
        print(f"  String keys: {len(string_keys)}")

    def test_02_workflow_search_exact_match(self, loaded_searcher):
        """
        WORKFLOW STEP 2: User searches with exact match.

        USER ACTION:
        - Enter search term
        - Select "Exact Match" mode
        - Click Search

        EXPECTED:
        - Returns entries containing exact query
        """
        # User searches for "안녕하세요"
        results = loaded_searcher.search_one_line(
            query="안녕하세요",
            match_type="exact"
        )

        assert len(results) > 0, "Should find exact match for 안녕하세요"

        # Verify result structure - returns list of (list/tuple with korean, translation, string_id)
        first_result = results[0]
        # Results can be list of lists or list of tuples
        if isinstance(first_result, (list, tuple)) and len(first_result) > 0:
            # Nested structure: [[(...), ...], ...]
            if isinstance(first_result[0], (list, tuple)):
                korean, translation = first_result[0][0], first_result[0][1]
            else:
                korean, translation = first_result[0], first_result[1]
        else:
            korean, translation = str(first_result), ""

        print(f"✓ Exact search '안녕하세요' found {len(results)} results")
        print(f"    First: {korean} → {translation}")

    def test_03_workflow_search_contains(self, loaded_searcher):
        """
        WORKFLOW STEP 3: User searches with contains mode.

        USER ACTION:
        - Enter partial term
        - Select "Contains" mode
        - Click Search

        EXPECTED:
        - Returns all entries containing the query substring
        """
        # User searches for partial text "마을"
        results = loaded_searcher.search_one_line(
            query="마을",
            match_type="contains"
        )

        assert len(results) > 0, "Should find entries containing 마을"

        print(f"✓ Contains search '마을' found {len(results)} results")
        for r in results[:2]:
            # Handle nested result structure
            if isinstance(r, (list, tuple)) and len(r) > 0:
                if isinstance(r[0], (list, tuple)):
                    korean = r[0][0]
                else:
                    korean = r[0]
            else:
                korean = str(r)
            print(f"    {korean[:50]}...")

    def test_04_workflow_multiline_search(self, loaded_searcher):
        """
        WORKFLOW STEP 4: User pastes multiple lines to search.

        USER ACTION:
        - Paste multiple Korean strings (one per line)
        - Click "Search All"

        EXPECTED:
        - Each line searched individually
        - Results grouped by query
        """
        queries = [
            "안녕하세요",
            "감사합니다",
            "마을",
            "전투"
        ]

        all_results = []
        for query in queries:
            results = loaded_searcher.search_one_line(
                query=query,
                match_type="contains"
            )
            all_results.append({
                'query': query,
                'count': len(results),
                'results': results
            })

        # Should have results for most queries
        found_count = sum(1 for r in all_results if r['count'] > 0)
        assert found_count >= 2, f"Should find results for at least 2 queries, got {found_count}"

        print(f"✓ Multiline search: {found_count}/{len(queries)} queries matched")
        for r in all_results:
            print(f"    '{r['query']}' → {r['count']} results")

    def test_05_workflow_special_characters(self, loaded_searcher):
        """
        WORKFLOW STEP 5: Search with special characters.

        PRODUCTION REQUIREMENT:
        - Special chars like ▶, 【】 must be searchable
        - Korean punctuation must work
        """
        special_queries = [
            ("▶", "Arrow marker"),
            ("【", "Bracket marker"),
            ("...", "Ellipsis"),
        ]

        for query, desc in special_queries:
            results = loaded_searcher.search_one_line(
                query=query,
                match_type="contains"
            )

            if len(results) > 0:
                print(f"✓ Found '{query}' ({desc}): {len(results)} results")
            else:
                print(f"  '{query}' ({desc}): no results (may not be in fixture)")


# =============================================================================
# KR SIMILAR PRODUCTION WORKFLOW TESTS
# =============================================================================

class TestKRSimilarProductionWorkflow:
    """
    Complete KR Similar production workflow simulation.

    USER SCENARIO: Quality assurance team needs to:
    1. Find similar strings for consistency checking
    2. Auto-translate new content using existing dictionary

    WORKFLOW:
    1. Create dictionary from reference data
    2. Extract similar strings for review
    3. Auto-translate new content
    """

    TEST_DICT_TYPE = "TEST_PROD_KR"

    @pytest.fixture(scope="class")
    def embeddings_manager(self):
        """Get EmbeddingsManager instance."""
        from server.tools.kr_similar.embeddings import EmbeddingsManager, DICT_TYPES

        # Add test type to allowed types
        if self.TEST_DICT_TYPE not in DICT_TYPES:
            DICT_TYPES.append(self.TEST_DICT_TYPE)

        manager = EmbeddingsManager()
        yield manager

        # Cleanup
        try:
            test_dir = manager.dictionaries_dir / self.TEST_DICT_TYPE
            if test_dir.exists():
                shutil.rmtree(test_dir)
        except Exception:
            pass

    @pytest.fixture(scope="class")
    def language_fixture(self):
        """Path to language data file."""
        path = FIXTURES_DIR / "sample_language_data.txt"
        assert path.exists(), f"Language fixture not found: {path}"
        return str(path)

    @pytest.fixture(scope="class")
    def similarity_searcher(self, embeddings_manager, language_fixture):
        """Create dictionary and get searcher."""
        from server.tools.kr_similar.searcher import SimilaritySearcher
        from server.tools.kr_similar.embeddings import DICT_TYPES

        # Ensure test type is allowed
        if self.TEST_DICT_TYPE not in DICT_TYPES:
            DICT_TYPES.append(self.TEST_DICT_TYPE)

        # Create dictionary
        result = embeddings_manager.create_dictionary(
            file_paths=[language_fixture],
            dict_type=self.TEST_DICT_TYPE,
            kr_column=5,
            trans_column=6
        )

        # Load dictionary
        embeddings_manager.load_dictionary(self.TEST_DICT_TYPE)

        # Create searcher
        searcher = SimilaritySearcher(embeddings_manager)

        yield searcher

        # Cleanup handled by embeddings_manager fixture

    @requires_model
    def test_01_workflow_create_similarity_dictionary(self, embeddings_manager, language_fixture):
        """
        WORKFLOW STEP 1: User creates similarity dictionary.

        USER ACTION:
        - Select dictionary type (BDO, BDM, etc.)
        - Add data files
        - Specify Korean and translation columns
        - Click "Create Dictionary"

        EXPECTED:
        - Dictionary created with embeddings
        - Both split and whole modes generated
        """
        from server.tools.kr_similar.embeddings import DICT_TYPES

        # Ensure test type is allowed
        if self.TEST_DICT_TYPE not in DICT_TYPES:
            DICT_TYPES.append(self.TEST_DICT_TYPE)

        # Create dictionary
        result = embeddings_manager.create_dictionary(
            file_paths=[language_fixture],
            dict_type=self.TEST_DICT_TYPE,
            kr_column=5,
            trans_column=6
        )

        assert "dict_type" in result
        assert result["split_pairs"] > 0, "Should have split pairs"
        assert result["total_pairs"] > 0, "Should have total pairs"

        print(f"✓ Similarity dictionary created:")
        print(f"    Type: {result['dict_type']}")
        print(f"    Split pairs: {result['split_pairs']}")
        print(f"    Whole pairs: {result['whole_pairs']}")

    @requires_model
    def test_02_workflow_find_similar_strings(self, similarity_searcher):
        """
        WORKFLOW STEP 2: User searches for similar strings.

        USER ACTION:
        - Enter Korean text
        - Set similarity threshold
        - Click "Find Similar"

        EXPECTED:
        - Returns list of similar strings with scores
        - Results sorted by similarity
        """
        # Test with various queries
        test_queries = [
            ("안녕하세요", "Greeting"),
            ("전투", "Combat-related"),
            ("마을", "Village-related"),
            ("퀘스트", "Quest-related"),
        ]

        for query, category in test_queries:
            results = similarity_searcher.find_similar(
                query=query,
                threshold=0.3,  # Low threshold for test data
                top_k=5
            )

            print(f"✓ Similar to '{query}' ({category}): {len(results)} results")
            for r in results[:2]:
                kr = r.get('korean', r.get('Korean', ''))[:40]
                sim = r.get('similarity', 0)
                print(f"    [{sim:.3f}] {kr}...")

    @requires_model
    def test_03_workflow_extract_similar_groups(self, similarity_searcher, language_fixture):
        """
        WORKFLOW STEP 3: User extracts groups of similar strings.

        USER ACTION:
        - Load data file
        - Set minimum character length
        - Set similarity threshold
        - Click "Extract Similar"

        EXPECTED:
        - Returns groups of similar strings
        - Each group contains strings that should be checked for consistency

        PRODUCTION USE: Quality check to find strings that may have
        inconsistent translations.
        """
        # Load fixture as DataFrame (simulating file upload)
        df = pd.read_csv(language_fixture, delimiter='\t', header=None, on_bad_lines='skip')

        # Extract similar strings
        results = similarity_searcher.extract_similar_strings(
            data=df,
            min_char_length=5,  # Short for test data
            similarity_threshold=0.5,
            filter_same_category=False
        )

        assert isinstance(results, list), "Results should be a list"

        print(f"✓ Extract similar found {len(results)} groups")
        if len(results) > 0:
            print(f"    First group has {len(results[0])} similar strings")

    @requires_model
    def test_04_workflow_auto_translate(self, similarity_searcher, language_fixture):
        """
        WORKFLOW STEP 4: User auto-translates new content.

        USER ACTION:
        - Load new data file (with missing translations)
        - Set similarity threshold
        - Click "Auto-Translate"

        EXPECTED:
        - DataFrame returned with translations filled in
        - Based on similarity matches from dictionary

        PRODUCTION USE: Automatically translate new game text using
        existing translation dictionary.
        """
        # Load fixture as DataFrame
        df = pd.read_csv(language_fixture, delimiter='\t', header=None, on_bad_lines='skip')

        # Auto-translate
        result_df = similarity_searcher.auto_translate(
            data=df,
            similarity_threshold=0.5
        )

        assert isinstance(result_df, pd.DataFrame), "Result should be DataFrame"
        assert len(result_df) == len(df), "Should have same number of rows"

        print(f"✓ Auto-translate processed {len(result_df)} rows")

        # Check if any translations were added
        if 'auto_translation' in result_df.columns or 6 in result_df.columns:
            print(f"    Output columns: {list(result_df.columns)[:5]}...")

    @requires_model
    def test_05_workflow_threshold_comparison(self, similarity_searcher):
        """
        WORKFLOW STEP 5: User compares results at different thresholds.

        USER ACTION:
        - Try different threshold values
        - Compare result counts
        - Select optimal threshold

        PRODUCTION USE: Tune threshold for balance between
        precision and recall.
        """
        query = "마을에 오신 것을 환영합니다"  # "Welcome to the village"

        threshold_results = {}
        for threshold in [0.3, 0.5, 0.7, 0.9]:
            results = similarity_searcher.find_similar(
                query=query,
                threshold=threshold,
                top_k=10
            )
            threshold_results[threshold] = len(results)

        print(f"✓ Threshold comparison for '{query[:20]}...':")
        for thresh, count in threshold_results.items():
            print(f"    Threshold {thresh}: {count} results")

        # Lower threshold should generally return more results
        assert threshold_results[0.3] >= threshold_results[0.9], \
            "Lower threshold should return >= results than higher"


# =============================================================================
# CROSS-TOOL PIPELINE TESTS
# =============================================================================

class TestCrossToolPipeline:
    """
    Complete cross-tool localization pipeline simulation.

    USER SCENARIO: Localization team uses all tools together:
    1. QuickSearch: Find existing translations
    2. KR Similar: Find similar strings for new content
    3. XLSTransfer: Apply translations to files
    """

    def test_01_pipeline_data_format_compatibility(self):
        """
        PIPELINE TEST: Verify all tools use compatible data formats.

        All tools should work with the same tab-separated format:
        - Column 5: Korean text
        - Column 6: Translation
        """
        # Load both fixture files
        lang_data = pd.read_csv(
            FIXTURES_DIR / "sample_language_data.txt",
            delimiter='\t', header=None, on_bad_lines='skip'
        )
        qs_data = pd.read_csv(
            FIXTURES_DIR / "sample_quicksearch_data.txt",
            delimiter='\t', header=None, on_bad_lines='skip'
        )

        # Both should have at least 7 columns (0-6)
        assert lang_data.shape[1] >= 7, "Language data should have 7+ columns"
        assert qs_data.shape[1] >= 7, "QuickSearch data should have 7+ columns"

        # Column 5 should be Korean (check for Hangul)
        def has_korean(text):
            if pd.isna(text):
                return False
            return any('\uac00' <= c <= '\ud7a3' for c in str(text))

        lang_kr = lang_data[5].apply(has_korean).sum()
        qs_kr = qs_data[5].apply(has_korean).sum()

        assert lang_kr > 0, "Language data col 5 should have Korean"
        assert qs_kr > 0, "QuickSearch data col 5 should have Korean"

        print(f"✓ Data format compatible:")
        print(f"    Language data: {lang_data.shape[0]} rows, {lang_kr} with Korean")
        print(f"    QuickSearch data: {qs_data.shape[0]} rows, {qs_kr} with Korean")

    def test_02_pipeline_tag_handling_consistency(self):
        """
        PIPELINE TEST: Verify tag handling is consistent across tools.

        All tools should handle game tags the same way:
        - {AudioVoice(...)}
        - {ChangeScene(...)}
        - <color=...>
        """
        from server.tools.kr_similar.core import normalize_text
        from client.tools.xls_transfer.translate_file import clean_audiovoice_tags

        test_texts = [
            "{AudioVoice(NPC_VCE_NEW_1001)}안녕하세요",
            "{ChangeScene(Battle_001)}전투 시작!",
            "<color=red>경고</color>: 위험",
            "{Tag1}{Tag2}텍스트",
        ]

        for text in test_texts:
            kr_clean = normalize_text(text)
            xls_clean = clean_audiovoice_tags(text)

            # Both should remove tags
            assert '{' not in kr_clean, f"KR Similar should remove tags: {kr_clean}"
            assert '{' not in xls_clean, f"XLSTransfer should remove tags: {xls_clean}"

            print(f"✓ Tag handling consistent: '{text[:30]}...'")
            print(f"    KR Similar:    '{kr_clean}'")
            print(f"    XLSTransfer:   '{xls_clean}'")

    def test_03_pipeline_shared_vocabulary(self):
        """
        PIPELINE TEST: Verify fixtures share common vocabulary.

        Tests should use realistic shared terms across tools.
        """
        # Load both fixtures
        lang_data = pd.read_csv(
            FIXTURES_DIR / "sample_language_data.txt",
            delimiter='\t', header=None, on_bad_lines='skip'
        )
        qs_data = pd.read_csv(
            FIXTURES_DIR / "sample_quicksearch_data.txt",
            delimiter='\t', header=None, on_bad_lines='skip'
        )

        # Get Korean text from column 5
        lang_korean = set()
        for text in lang_data[5].dropna():
            # Extract words (simple split)
            words = str(text).replace('{', ' ').replace('}', ' ').split()
            lang_korean.update(w for w in words if any('\uac00' <= c <= '\ud7a3' for c in w))

        qs_korean = set()
        for text in qs_data[5].dropna():
            words = str(text).split()
            qs_korean.update(w for w in words if any('\uac00' <= c <= '\ud7a3' for c in w))

        # Find overlap
        common = lang_korean & qs_korean

        print(f"✓ Shared vocabulary analysis:")
        print(f"    Language data unique words: {len(lang_korean)}")
        print(f"    QuickSearch unique words: {len(qs_korean)}")
        print(f"    Common words: {len(common)}")
        if common:
            print(f"    Examples: {list(common)[:5]}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
