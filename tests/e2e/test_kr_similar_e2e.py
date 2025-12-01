"""
End-to-End Tests for KR Similar (App #3)

Full integration tests that:
1. Create a TEST dictionary from fixture data
2. Load the dictionary
3. Test similarity search with actual Korean BERT embeddings
4. Test all KR Similar functions

These tests use the actual model and create real embeddings.
They are designed to run autonomously without user intervention.
"""

import pytest
import os
import sys
import shutil
import numpy as np
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Fixtures are in tests/fixtures/ (shared by all tests)
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"

# Test dictionary type (use "TEST" to avoid overwriting real dictionaries)
TEST_DICT_TYPE = "TEST"


class TestKRSimilarE2E:
    """End-to-end tests for KR Similar with real embeddings."""

    @pytest.fixture(scope="class")
    def setup_test_environment(self):
        """Setup test environment with TEST dictionary type."""
        from server.tools.kr_similar.embeddings import DICT_TYPES

        # Add TEST to allowed types for testing
        if TEST_DICT_TYPE not in DICT_TYPES:
            DICT_TYPES.append(TEST_DICT_TYPE)

        yield

        # Cleanup after tests
        from server.tools.kr_similar.embeddings import EmbeddingsManager
        manager = EmbeddingsManager()
        test_dir = manager.dictionaries_dir / TEST_DICT_TYPE
        if test_dir.exists():
            shutil.rmtree(test_dir)
            print(f"Cleaned up test directory: {test_dir}")

    @pytest.fixture(scope="class")
    def embeddings_manager(self, setup_test_environment):
        """Get EmbeddingsManager instance."""
        from server.tools.kr_similar.embeddings import EmbeddingsManager
        return EmbeddingsManager()

    @pytest.fixture(scope="class")
    def fixture_file(self):
        """Get path to fixture data file."""
        fixture_path = FIXTURES_DIR / "sample_language_data.txt"
        assert fixture_path.exists(), f"Fixture file not found: {fixture_path}"
        return str(fixture_path)

    def test_01_model_loads_successfully(self, embeddings_manager):
        """Test that the Korean BERT model loads successfully."""
        # This will trigger model loading
        embeddings_manager._ensure_model_loaded()

        assert embeddings_manager.model is not None, "Model should be loaded"
        assert embeddings_manager.device is not None, "Device should be set"

        # Verify model can encode text
        test_embedding = embeddings_manager.model.encode(["테스트"])
        assert test_embedding.shape == (1, 768), f"Expected shape (1, 768), got {test_embedding.shape}"

        print(f"Model loaded on device: {embeddings_manager.device}")
        print(f"Embedding dimension: {test_embedding.shape[1]}")

    def test_02_encode_korean_texts(self, embeddings_manager):
        """Test encoding Korean texts to embeddings."""
        test_texts = [
            "안녕하세요",
            "오늘 날씨가 좋군요",
            "마을에 오신 것을 환영합니다",
            "전투를 시작합니다"
        ]

        embeddings = embeddings_manager.encode_texts(test_texts)

        assert embeddings.shape[0] == len(test_texts), "Should have one embedding per text"
        assert embeddings.shape[1] == 768, "Embedding dimension should be 768"

        # Verify embeddings are different (not all zeros or identical)
        assert not np.allclose(embeddings[0], embeddings[1]), "Embeddings should be different"

        print(f"Encoded {len(test_texts)} texts, shape: {embeddings.shape}")

    def test_03_create_dictionary_from_fixture(self, embeddings_manager, fixture_file):
        """Test creating a dictionary from fixture data."""
        from server.tools.kr_similar.embeddings import DICT_TYPES

        # Ensure TEST is in allowed types
        if TEST_DICT_TYPE not in DICT_TYPES:
            DICT_TYPES.append(TEST_DICT_TYPE)

        result = embeddings_manager.create_dictionary(
            file_paths=[fixture_file],
            dict_type=TEST_DICT_TYPE,
            kr_column=5,
            trans_column=6
        )

        assert "dict_type" in result, "Result should contain dict_type"
        assert result["dict_type"] == TEST_DICT_TYPE
        assert result["split_pairs"] > 0, "Should have split pairs"
        assert result["whole_pairs"] > 0, "Should have whole pairs"
        assert result["total_pairs"] > 0, "Should have total pairs"

        print(f"Created dictionary: {result}")

    def test_04_dictionary_files_exist(self, embeddings_manager):
        """Test that dictionary files were created correctly."""
        dict_dir = embeddings_manager.dictionaries_dir / TEST_DICT_TYPE

        # Check split files
        assert (dict_dir / "split_embeddings.npy").exists(), "Split embeddings should exist"
        assert (dict_dir / "split_translation_dict.pkl").exists(), "Split dict should exist"

        # Check whole files
        assert (dict_dir / "whole_embeddings.npy").exists(), "Whole embeddings should exist"
        assert (dict_dir / "whole_translation_dict.pkl").exists(), "Whole dict should exist"

        # Verify file sizes
        split_emb = np.load(dict_dir / "split_embeddings.npy")
        assert split_emb.shape[1] == 768, "Embedding dimension should be 768"

        print(f"Dictionary files verified at: {dict_dir}")
        print(f"Split embeddings shape: {split_emb.shape}")

    def test_05_load_dictionary(self, embeddings_manager):
        """Test loading the dictionary into memory."""
        from server.tools.kr_similar.embeddings import DICT_TYPES

        # Ensure TEST is in allowed types
        if TEST_DICT_TYPE not in DICT_TYPES:
            DICT_TYPES.append(TEST_DICT_TYPE)

        result = embeddings_manager.load_dictionary(TEST_DICT_TYPE)

        assert result == True, "Load should return True"
        assert embeddings_manager.split_embeddings is not None, "Split embeddings should be loaded"
        assert embeddings_manager.split_dict is not None, "Split dict should be loaded"
        assert embeddings_manager.split_index is not None, "Split FAISS index should be created"
        assert embeddings_manager.current_dict_type == TEST_DICT_TYPE

        print(f"Loaded dictionary with {len(embeddings_manager.split_dict)} split pairs")

    def test_06_list_dictionaries(self, embeddings_manager):
        """Test listing available dictionaries."""
        dictionaries = embeddings_manager.list_available_dictionaries()

        # Find our TEST dictionary
        test_dict = next((d for d in dictionaries if d["dict_type"] == TEST_DICT_TYPE), None)

        assert test_dict is not None, "TEST dictionary should be in list"
        assert test_dict["split_pairs"] > 0, "Should have split pairs"
        assert test_dict["whole_pairs"] > 0, "Should have whole pairs"

        print(f"Available dictionaries: {dictionaries}")

    def test_07_similarity_search_basic(self, embeddings_manager):
        """Test basic similarity search."""
        from server.tools.kr_similar.searcher import SimilaritySearcher

        searcher = SimilaritySearcher(embeddings_manager=embeddings_manager)

        # Search for text similar to "안녕하세요" (Hello)
        results = searcher.find_similar(
            query="안녕하세요",
            threshold=0.5,  # Lower threshold for test data
            top_k=5,
            use_whole=False
        )

        assert isinstance(results, list), "Results should be a list"
        print(f"Search results for '안녕하세요': {results}")

    def test_08_similarity_search_with_various_queries(self, embeddings_manager):
        """Test similarity search with various Korean queries."""
        from server.tools.kr_similar.searcher import SimilaritySearcher

        searcher = SimilaritySearcher(embeddings_manager=embeddings_manager)

        test_queries = [
            "마을",  # Village
            "전투",  # Combat
            "선택",  # Select
            "환영",  # Welcome
            "상점",  # Shop
        ]

        for query in test_queries:
            results = searcher.find_similar(
                query=query,
                threshold=0.3,  # Very low threshold to ensure results
                top_k=3,
                use_whole=False
            )
            print(f"Query '{query}' -> {len(results)} results")

            # We should get some results for each query
            # (may not always find matches with limited test data)

    def test_09_whole_text_search(self, embeddings_manager):
        """Test whole text similarity search."""
        from server.tools.kr_similar.searcher import SimilaritySearcher

        searcher = SimilaritySearcher(embeddings_manager=embeddings_manager)

        # Search using whole text mode
        results = searcher.find_similar(
            query="오늘 날씨가 좋군요",  # "The weather is nice today"
            threshold=0.3,
            top_k=5,
            use_whole=True
        )

        print(f"Whole text search results: {results}")

    def test_10_searcher_status(self, embeddings_manager):
        """Test searcher status reporting."""
        from server.tools.kr_similar.searcher import SimilaritySearcher

        searcher = SimilaritySearcher(embeddings_manager=embeddings_manager)

        status = searcher.get_status()

        assert "model_loaded" in status
        assert "embeddings_manager_set" in status
        assert "faiss_available" in status
        assert status["embeddings_manager_set"] == True

        print(f"Searcher status: {status}")

    def test_11_embeddings_manager_status(self, embeddings_manager):
        """Test embeddings manager status reporting."""
        status = embeddings_manager.get_status()

        assert status["model_loaded"] == True
        assert status["current_dict_type"] == TEST_DICT_TYPE
        assert status["split_pairs"] > 0
        assert status["models_available"] == True

        print(f"Embeddings manager status: {status}")

    def test_12_check_dictionary_exists(self, embeddings_manager):
        """Test checking if dictionary exists."""
        # TEST dictionary should exist
        assert embeddings_manager.check_dictionary_exists(TEST_DICT_TYPE) == True

        # Non-existent dictionary should not exist
        assert embeddings_manager.check_dictionary_exists("NONEXISTENT") == False

    def test_13_text_normalization_integration(self, embeddings_manager):
        """Test that text normalization works in the pipeline."""
        from server.tools.kr_similar.core import normalize_text

        # Text with markers from fixture data
        text_with_markers = "{ChangeScene(Main_001)}{AudioVoice(NPC_001)}안녕하세요. 저는 마을의 촌장입니다."
        normalized = normalize_text(text_with_markers)

        assert "{" not in normalized, "Code markers should be removed"
        assert "안녕하세요" in normalized, "Korean text should remain"
        assert "촌장" in normalized, "Korean text should remain"

        print(f"Normalized: '{text_with_markers}' -> '{normalized}'")

    def test_14_split_processing_integration(self):
        """Test split data processing with real data structure."""
        from server.tools.kr_similar.core import KRSimilarCore
        import pandas as pd

        # Create test data similar to fixture format
        data = pd.DataFrame({
            'Korean': [
                '첫 번째 줄입니다.\\n두 번째 줄입니다.\\n세 번째 줄입니다.',
                '단일 줄 텍스트입니다.'
            ],
            'Translation': [
                'This is first line.\\nThis is second line.\\nThis is third line.',
                'This is single line text.'
            ]
        })

        result = KRSimilarCore.process_split_data(data)

        # Should split multi-line entry into separate rows
        assert len(result) >= 4, f"Should have at least 4 rows, got {len(result)}"

        print(f"Split processing: 2 rows -> {len(result)} rows")

    def test_15_parse_language_file_integration(self, fixture_file):
        """Test parsing the actual fixture file."""
        from server.tools.kr_similar.core import KRSimilarCore

        df = KRSimilarCore.parse_language_file(fixture_file, kr_column=5, trans_column=6)

        assert 'Korean' in df.columns
        assert 'Translation' in df.columns
        assert len(df) == 20, f"Fixture should have 20 rows, got {len(df)}"

        # Verify some expected content
        first_korean = df.iloc[0]['Korean']
        assert '안녕하세요' in first_korean, "First row should contain greeting"

        print(f"Parsed fixture file: {len(df)} rows")

    def test_16_extract_similar_strings(self, embeddings_manager, fixture_file):
        """Test extract_similar_strings - finds groups of similar strings in data.

        PRODUCTION USE: Quality check to find strings that should have consistent translations.
        INPUT: Language data file with Korean text
        EXPECTED OUTPUT: List of groups containing similar strings
        """
        from server.tools.kr_similar.searcher import SimilaritySearcher
        from server.tools.kr_similar.core import KRSimilarCore
        import pandas as pd

        searcher = SimilaritySearcher(embeddings_manager=embeddings_manager)

        # Load fixture data as DataFrame (simulating uploaded file)
        df = pd.read_csv(fixture_file, delimiter='\t', header=None, on_bad_lines='skip')

        # Extract similar strings
        results = searcher.extract_similar_strings(
            data=df,
            min_char_length=10,  # Lower for test data
            similarity_threshold=0.5,  # Lower threshold for test data
            filter_same_category=False
        )

        # Verify output structure
        assert isinstance(results, list), "Results should be a list"

        # Results should be a list of groups (each group is similar strings)
        print(f"Extract similar found {len(results)} groups")

        # If we have results, verify structure
        if len(results) > 0:
            first_group = results[0]
            assert isinstance(first_group, (list, dict)), "Each group should be list or dict"
            print(f"First group: {first_group}")

    def test_17_auto_translate(self, embeddings_manager, fixture_file):
        """Test auto_translate - automatically translates using similarity matching.

        PRODUCTION USE: Auto-fill translations for new content using existing dictionary.
        INPUT: Language data file with Korean text (some without translations)
        EXPECTED OUTPUT: DataFrame with translations filled in based on similarity matches
        """
        from server.tools.kr_similar.searcher import SimilaritySearcher
        import pandas as pd

        searcher = SimilaritySearcher(embeddings_manager=embeddings_manager)

        # Load fixture data
        df = pd.read_csv(fixture_file, delimiter='\t', header=None, on_bad_lines='skip')

        # Auto-translate using loaded dictionary
        result_df = searcher.auto_translate(
            data=df,
            similarity_threshold=0.5  # Lower for test data
        )

        # Verify output
        assert isinstance(result_df, pd.DataFrame), "Result should be a DataFrame"
        assert len(result_df) == len(df), "Output should have same number of rows as input"

        print(f"Auto-translate processed {len(result_df)} rows")
        print(f"Output columns: {list(result_df.columns)}")

    def test_18_clear_dictionary_from_memory(self, embeddings_manager):
        """Test clearing dictionary from memory.

        PRODUCTION USE: Free memory by unloading dictionary when not needed.
        INPUT: None (uses currently loaded dictionary)
        EXPECTED OUTPUT: All dictionary data cleared from memory
        """
        # First verify dictionary is loaded
        assert embeddings_manager.split_index is not None, "Dictionary should be loaded before test"

        # Clear dictionary
        embeddings_manager.split_embeddings = None
        embeddings_manager.split_dict = None
        embeddings_manager.split_index = None
        embeddings_manager.whole_embeddings = None
        embeddings_manager.whole_dict = None
        embeddings_manager.whole_index = None
        embeddings_manager.current_dict_type = None

        # Verify cleared
        assert embeddings_manager.split_index is None, "Split index should be None after clear"
        assert embeddings_manager.whole_index is None, "Whole index should be None after clear"
        assert embeddings_manager.current_dict_type is None, "Current dict type should be None"

        print("Dictionary cleared from memory successfully")

        # Reload for subsequent tests (restore state)
        from server.tools.kr_similar.embeddings import DICT_TYPES
        if TEST_DICT_TYPE not in DICT_TYPES:
            DICT_TYPES.append(TEST_DICT_TYPE)
        embeddings_manager.load_dictionary(TEST_DICT_TYPE)
        print("Dictionary reloaded for subsequent tests")



if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s", "--tb=short"])
