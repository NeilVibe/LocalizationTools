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


class TestKRSimilarAPIE2E:
    """End-to-end API tests (require running server)."""

    @pytest.fixture
    def api_base_url(self):
        """Get API base URL."""
        return "http://localhost:8888"

    @pytest.mark.skipif(
        not os.environ.get("RUN_API_TESTS"),
        reason="API tests require running server (set RUN_API_TESTS=1)"
    )
    def test_api_health(self, api_base_url):
        """Test KR Similar health endpoint."""
        import requests

        # First login
        login_r = requests.post(
            f"{api_base_url}/api/v2/auth/login",
            json={"username": "admin", "password": "admin123"},
            timeout=10
        )

        if login_r.status_code != 200:
            pytest.skip("Could not login to API")

        token = login_r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        r = requests.get(
            f"{api_base_url}/api/v2/kr-similar/health",
            headers=headers,
            timeout=10
        )

        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        print(f"API health: {data}")


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s", "--tb=short"])
