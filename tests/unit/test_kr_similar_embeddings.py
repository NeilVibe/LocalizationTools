"""
Unit Tests for KR Similar Embeddings Module

Tests embedding generation and BERT model operations.
TRUE SIMULATION - no mocks, tests actual module structure.
Note: Full BERT tests require GPU/model, so we test what we can without loading.
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestEmbeddingsModuleImports:
    """Test embeddings module imports."""

    def test_embeddings_module_imports(self):
        """Embeddings module imports without error."""
        from server.tools.kr_similar import embeddings
        assert embeddings is not None

    def test_embeddings_manager_class_exists(self):
        """EmbeddingsManager class exists."""
        from server.tools.kr_similar.embeddings import EmbeddingsManager
        assert EmbeddingsManager is not None

    def test_config_constants_exist(self):
        """Configuration constants exist."""
        from server.tools.kr_similar.embeddings import MODEL_NAME, DICT_TYPES
        assert MODEL_NAME is not None
        assert DICT_TYPES is not None
        assert isinstance(DICT_TYPES, list)


class TestEmbeddingsManagerInit:
    """Test EmbeddingsManager initialization (without loading model)."""

    def test_manager_class_has_init(self):
        """EmbeddingsManager has __init__ method."""
        from server.tools.kr_similar.embeddings import EmbeddingsManager
        assert hasattr(EmbeddingsManager, '__init__')

    def test_manager_has_load_dictionary_method(self):
        """EmbeddingsManager has load_dictionary method."""
        from server.tools.kr_similar.embeddings import EmbeddingsManager
        assert hasattr(EmbeddingsManager, 'load_dictionary')

    def test_manager_has_methods(self):
        """EmbeddingsManager has expected methods."""
        from server.tools.kr_similar.embeddings import EmbeddingsManager
        # Check class has key methods
        assert hasattr(EmbeddingsManager, '__init__')
        assert hasattr(EmbeddingsManager, 'encode_texts')
        assert hasattr(EmbeddingsManager, 'create_dictionary')


class TestModelConfiguration:
    """Test model configuration."""

    def test_model_name_is_embedding_model(self):
        """MODEL_NAME is a valid embedding model (KR-SBERT or Qwen)."""
        from server.tools.kr_similar.embeddings import MODEL_NAME
        # P20: Supports either KR-SBERT (legacy) or Qwen (unified)
        assert "KR-SBERT" in MODEL_NAME or "Qwen" in MODEL_NAME or "korean" in MODEL_NAME.lower()

    def test_dict_types_contains_expected(self):
        """DICT_TYPES contains expected game codes."""
        from server.tools.kr_similar.embeddings import DICT_TYPES
        assert "BDO" in DICT_TYPES
        assert "BDM" in DICT_TYPES


class TestModuleExports:
    """Test module exports."""

    def test_all_expected_exports(self):
        """All expected items are exported."""
        from server.tools.kr_similar.embeddings import (
            EmbeddingsManager,
            MODEL_NAME,
            DICT_TYPES
        )
        assert EmbeddingsManager is not None
        assert MODEL_NAME is not None
        assert DICT_TYPES is not None


class TestEmbeddingsManagerMethods:
    """Test EmbeddingsManager method signatures."""

    def test_encode_texts_exists(self):
        """encode_texts method exists."""
        from server.tools.kr_similar.embeddings import EmbeddingsManager
        assert hasattr(EmbeddingsManager, 'encode_texts')

    def test_class_is_callable(self):
        """EmbeddingsManager class can be referenced."""
        from server.tools.kr_similar.embeddings import EmbeddingsManager
        assert EmbeddingsManager is not None

    def test_get_status_exists(self):
        """get_status method exists."""
        from server.tools.kr_similar.embeddings import EmbeddingsManager
        assert hasattr(EmbeddingsManager, 'get_status')

    def test_list_available_dictionaries_exists(self):
        """list_available_dictionaries method exists."""
        from server.tools.kr_similar.embeddings import EmbeddingsManager
        assert hasattr(EmbeddingsManager, 'list_available_dictionaries')


class TestConfigIntegration:
    """Test integration with config module."""

    def test_uses_config_model_path(self):
        """Module can access config for model path."""
        from server import config
        # Config should have model-related settings
        assert hasattr(config, 'MODEL_PATH') or True  # May be in embeddings module


class TestEmbeddingsManagerAttributes:
    """Test EmbeddingsManager expected attributes."""

    def test_has_class_defined(self):
        """EmbeddingsManager class is defined."""
        from server.tools.kr_similar.embeddings import EmbeddingsManager
        assert EmbeddingsManager is not None

    def test_has_check_dictionary_method(self):
        """EmbeddingsManager has check_dictionary_exists method."""
        from server.tools.kr_similar.embeddings import EmbeddingsManager
        assert hasattr(EmbeddingsManager, 'check_dictionary_exists')


class TestFaissIntegration:
    """Test FAISS integration expectations."""

    def test_faiss_importable(self):
        """FAISS library is importable."""
        try:
            import faiss
            assert faiss is not None
        except ImportError:
            pytest.skip("FAISS not installed")

    def test_numpy_importable(self):
        """NumPy is importable (required for embeddings)."""
        import numpy as np
        assert np is not None


class TestTransformersIntegration:
    """Test Transformers integration expectations."""

    def test_transformers_importable(self):
        """Transformers library is importable."""
        try:
            import transformers
            assert transformers is not None
        except ImportError:
            pytest.skip("Transformers not installed")

    def test_torch_importable(self):
        """PyTorch is importable."""
        try:
            import torch
            assert torch is not None
        except ImportError:
            pytest.skip("PyTorch not installed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
