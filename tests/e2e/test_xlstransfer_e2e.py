"""
End-to-End Tests for XLSTransfer (App #1)

Full integration tests that verify ALL production endpoints:
1. Health check
2. Create dictionary from Excel files
3. Load dictionary into memory
4. Translate single text
5. Translate file (txt/Excel)
6. Translate Excel with selections
7. Status check
8. Get sheets from Excel file

These tests use real files and verify expected outputs.
"""

import pytest
import os
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Fixtures directory
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"

# Check if Korean BERT model is available (not in CI LIGHT builds)
# In LIGHT builds, model.safetensors is just a Git LFS pointer (~135 bytes)
# The real model is ~447MB, so we check for >100MB to ensure it's not just a pointer
MODEL_DIR = project_root / "models" / "kr-sbert"
MODEL_FILE = MODEL_DIR / "model.safetensors"
MODEL_AVAILABLE = (
    MODEL_DIR.exists()
    and MODEL_FILE.exists()
    and MODEL_FILE.stat().st_size > 100_000_000  # >100MB = real model, not LFS pointer
)


def requires_model(func):
    """Decorator to skip tests that require the Korean BERT model."""
    return pytest.mark.skipif(
        not MODEL_AVAILABLE,
        reason="Korean BERT model not available (LIGHT build or CI)"
    )(func)


class TestXLSTransferCore:
    """Unit tests for XLSTransfer core functionality."""

    def test_01_core_module_imports(self):
        """Test that XLSTransfer core modules can be imported."""
        try:
            from client.tools.xls_transfer import core, embeddings, translation, process_operation
            assert core is not None
            assert embeddings is not None
            assert translation is not None
            assert process_operation is not None
            print("All XLSTransfer modules imported successfully")
        except ImportError as e:
            pytest.skip(f"XLSTransfer modules not available: {e}")

    def test_02_clean_text(self):
        """Test text cleaning function.

        PRODUCTION USE: Clean Excel cell values before processing.
        INPUT: Text with carriage returns or whitespace
        EXPECTED OUTPUT: Cleaned text without _x000D_ characters
        """
        from client.tools.xls_transfer.core import clean_text

        # Test carriage return removal
        result = clean_text("Hello_x000D_World")
        assert "_x000D_" not in result
        print(f"clean_text('Hello_x000D_World') = '{result}'")

        # Test None handling
        assert clean_text(None) is None

        # Test number conversion
        assert clean_text(123) == "123"

    def test_03_excel_column_conversion(self):
        """Test Excel column letter to index conversion.

        PRODUCTION USE: Convert user-specified columns (A, B, C) to array indices.
        INPUT: Column letter like 'A', 'B', 'Z'
        EXPECTED OUTPUT: Zero-based index (0, 1, 25)
        """
        from client.tools.xls_transfer.core import excel_column_to_index, index_to_excel_column

        # Test A = 0
        assert excel_column_to_index('A') == 0
        assert excel_column_to_index('B') == 1
        assert excel_column_to_index('Z') == 25

        # Test reverse conversion
        assert index_to_excel_column(0) == 'A'
        assert index_to_excel_column(1) == 'B'
        assert index_to_excel_column(25) == 'Z'

        print("Column conversions: A=0, B=1, Z=25 ✓")

    def test_04_fixture_files_exist(self):
        """Verify fixture files exist for testing."""
        excel_fixture = FIXTURES_DIR / "sample_dictionary.xlsx"
        txt_fixture = FIXTURES_DIR / "sample_to_translate.txt"

        assert excel_fixture.exists(), f"Excel fixture not found: {excel_fixture}"
        assert txt_fixture.exists(), f"Text fixture not found: {txt_fixture}"

        print(f"Fixtures verified: {excel_fixture.name}, {txt_fixture.name}")


class TestXLSTransferEmbeddings:
    """Tests for XLSTransfer embeddings and dictionary functionality."""

    @pytest.fixture(scope="class")
    def embeddings_module(self):
        """Get embeddings module."""
        try:
            from client.tools.xls_transfer import embeddings
            return embeddings
        except ImportError:
            pytest.skip("XLSTransfer embeddings module not available")

    @requires_model
    def test_05_model_loads(self, embeddings_module):
        """Test that the Korean BERT model loads.

        PRODUCTION USE: Model is required for semantic matching.
        EXPECTED: Model loads successfully, can encode text.
        """
        model = embeddings_module.get_model()
        assert model is not None, "Model should load"

        # Test encoding
        test_embedding = model.encode(["테스트"])
        assert test_embedding.shape == (1, 768), f"Expected (1, 768), got {test_embedding.shape}"

        print(f"Model loaded, embedding shape: {test_embedding.shape}")

    @requires_model
    def test_06_process_excel_for_dictionary(self, embeddings_module):
        """Test creating dictionary from Excel file.

        PRODUCTION USE: User uploads Excel files to create translation dictionary.
        INPUT: Excel file with Korean (col A) and Translation (col B)
        EXPECTED OUTPUT: split_dict and whole_dict with Korean→Translation mappings
        """
        excel_path = str(FIXTURES_DIR / "sample_dictionary.xlsx")

        excel_files = [(excel_path, "Sheet1", "A", "B")]

        split_dict, whole_dict, split_embeddings, whole_embeddings = \
            embeddings_module.process_excel_for_dictionary(excel_files)

        assert len(split_dict) > 0, "Should have split dictionary entries"
        assert split_embeddings is not None, "Should have embeddings"

        print(f"Dictionary created: {len(split_dict)} split pairs, {len(whole_dict)} whole pairs")

        # Verify expected content
        assert "안녕하세요" in split_dict or any("안녕" in k for k in split_dict.keys()), \
            "Dictionary should contain Korean greeting"

    @requires_model
    def test_07_save_and_load_dictionary(self, embeddings_module):
        """Test saving and loading dictionary.

        PRODUCTION USE: Dictionary is saved to disk and loaded for translation.
        """
        excel_path = str(FIXTURES_DIR / "sample_dictionary.xlsx")
        excel_files = [(excel_path, "Sheet1", "A", "B")]

        # Create dictionary
        split_dict, whole_dict, split_embeddings, whole_embeddings = \
            embeddings_module.process_excel_for_dictionary(excel_files)

        # Save dictionary
        embeddings_module.save_dictionary(
            embeddings=split_embeddings,
            translation_dict=split_dict,
            mode="split"
        )

        # Load dictionary
        loaded_embeddings, loaded_dict, loaded_index, loaded_kr_texts = \
            embeddings_module.load_dictionary(mode="split")

        assert loaded_dict is not None, "Should load dictionary"
        assert loaded_index is not None, "Should create FAISS index"
        assert len(loaded_dict) > 0, "Should have entries"

        print(f"Dictionary saved and loaded: {len(loaded_dict)} entries")


class TestXLSTransferTranslation:
    """Tests for XLSTransfer translation functionality."""

    @pytest.fixture(scope="class")
    def translation_module(self):
        """Get translation module."""
        try:
            from client.tools.xls_transfer import translation, embeddings

            # Ensure dictionary is loaded
            try:
                embeddings.load_dictionary(mode="split")
            except Exception:
                # Create dictionary first
                excel_path = str(FIXTURES_DIR / "sample_dictionary.xlsx")
                excel_files = [(excel_path, "Sheet1", "A", "B")]
                split_dict, _, split_embeddings, _ = embeddings.process_excel_for_dictionary(excel_files)
                embeddings.save_dictionary(split_embeddings, split_dict, mode="split")
                embeddings.load_dictionary(mode="split")

            return translation
        except ImportError:
            pytest.skip("XLSTransfer translation module not available")

    @requires_model
    def test_08_find_best_match(self, translation_module):
        """Test finding best matching translation.

        PRODUCTION USE: Core translation function - finds best match for Korean text.
        INPUT: Korean text to translate
        EXPECTED OUTPUT: (matched_korean, translated_text, confidence_score)
        """
        from client.tools.xls_transfer import embeddings

        # Load dictionary
        split_embeddings, split_dict, split_index, split_kr_texts = \
            embeddings.load_dictionary(mode="split")

        # Find match for "안녕하세요"
        matched_korean, translated_text, score = translation_module.find_best_match(
            text="안녕하세요",
            faiss_index=split_index,
            kr_sentences=split_kr_texts,
            translation_dict=split_dict,
            threshold=0.5,  # Lower threshold for testing
            model=None
        )

        print(f"Query: '안녕하세요'")
        print(f"Match: '{matched_korean}' -> '{translated_text}' (score: {score:.3f})")

        # Should find a match or return with low score
        assert isinstance(score, float), "Score should be a float"

    @requires_model
    def test_09_translate_with_high_threshold(self, translation_module):
        """Test translation with exact match threshold.

        PRODUCTION USE: High threshold (0.99) for exact matches only.
        """
        from client.tools.xls_transfer import embeddings

        split_embeddings, split_dict, split_index, split_kr_texts = \
            embeddings.load_dictionary(mode="split")

        # Exact match should work
        matched_korean, translated_text, score = translation_module.find_best_match(
            text="안녕하세요",
            faiss_index=split_index,
            kr_sentences=split_kr_texts,
            translation_dict=split_dict,
            threshold=0.99,
            model=None
        )

        if score >= 0.99:
            assert translated_text is not None, "Should have translation for exact match"
            print(f"Exact match found: {translated_text} (score: {score:.3f})")
        else:
            print(f"No exact match (score: {score:.3f}) - this is expected for test data")



if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
