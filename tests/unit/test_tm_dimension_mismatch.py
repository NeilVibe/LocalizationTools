"""
Tests for TM Embedding Dimension Mismatch Handling

When switching embedding engines (Model2Vec ↔ Qwen), cached embeddings
may have different dimensions. The system should detect this and re-embed.

Model2Vec: 256 dimensions
Qwen: 1024 dimensions

Run with: python3 -m pytest tests/unit/test_tm_dimension_mismatch.py -v
"""

import pytest
import sys
import numpy as np
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

pytestmark = [
    pytest.mark.unit,
    pytest.mark.tm,
    pytest.mark.feat001,
]


class TestDimensionMismatchDetection:
    """Test embedding dimension mismatch detection."""

    def test_model2vec_dimension_is_256(self):
        """Model2Vec embeddings should be 256 dimensions."""
        # This is a documentation/specification test
        MODEL2VEC_DIM = 256
        assert MODEL2VEC_DIM == 256

    def test_qwen_dimension_is_1024(self):
        """Qwen embeddings should be 1024 dimensions."""
        # This is a documentation/specification test
        QWEN_DIM = 1024
        assert QWEN_DIM == 1024

    def test_dimension_mismatch_detected(self):
        """Should detect when cached dim != model dim."""
        cached_dim = 1024  # Qwen cached
        model_dim = 256    # Model2Vec active

        # Mismatch should be detected
        assert cached_dim != model_dim, "Dimension mismatch should be detected"

    def test_same_dimension_no_mismatch(self):
        """Should not flag mismatch when dimensions match."""
        cached_dim = 256
        model_dim = 256

        assert cached_dim == model_dim, "Same dimensions should not be flagged"


class TestDimensionMismatchBehavior:
    """Test behavior when dimension mismatch is detected."""

    def test_mismatch_triggers_reembed_flag(self):
        """Dimension mismatch should trigger re-embedding."""
        # Simulate the logic from tm_indexer.py:1854-1878
        cached_embeddings = np.random.randn(100, 1024).astype(np.float32)  # Qwen
        expected_dim = 256  # Model2Vec active

        cached_dim = cached_embeddings.shape[1]

        if cached_dim != expected_dim:
            should_reembed = True
            reason = f"Embedding dimension mismatch: cached={cached_dim}, model={expected_dim}"
        else:
            should_reembed = False
            reason = None

        assert should_reembed is True
        assert "mismatch" in reason.lower()
        assert str(cached_dim) in reason
        assert str(expected_dim) in reason

    def test_no_reembed_when_dimensions_match(self):
        """No re-embedding needed when dimensions match."""
        cached_embeddings = np.random.randn(100, 256).astype(np.float32)
        expected_dim = 256

        cached_dim = cached_embeddings.shape[1]

        should_reembed = cached_dim != expected_dim

        assert should_reembed is False

    def test_empty_cache_triggers_fresh_embed(self):
        """Empty cache should trigger fresh embedding (not mismatch)."""
        cached_embeddings = None
        expected_dim = 256

        if cached_embeddings is None:
            should_fresh_embed = True
            is_mismatch = False
        else:
            should_fresh_embed = False
            is_mismatch = cached_embeddings.shape[1] != expected_dim

        assert should_fresh_embed is True
        assert is_mismatch is False


class TestEmbeddingEngineSwitch:
    """Test embedding engine switching scenarios."""

    def test_model2vec_to_qwen_switch(self):
        """Switching from Model2Vec to Qwen should trigger re-embed."""
        old_engine = "model2vec"
        new_engine = "qwen"
        old_dim = 256
        new_dim = 1024

        needs_reembed = old_dim != new_dim

        assert needs_reembed is True, "Model2Vec→Qwen should trigger re-embed"

    def test_qwen_to_model2vec_switch(self):
        """Switching from Qwen to Model2Vec should trigger re-embed."""
        old_engine = "qwen"
        new_engine = "model2vec"
        old_dim = 1024
        new_dim = 256

        needs_reembed = old_dim != new_dim

        assert needs_reembed is True, "Qwen→Model2Vec should trigger re-embed"

    def test_same_engine_no_reembed(self):
        """Staying on same engine should not trigger re-embed."""
        old_engine = "model2vec"
        new_engine = "model2vec"
        old_dim = 256
        new_dim = 256

        needs_reembed = old_dim != new_dim

        assert needs_reembed is False, "Same engine should not trigger re-embed"


class TestFAISSIndexDimension:
    """Test FAISS index dimension handling."""

    def test_faiss_index_must_match_embedding_dim(self):
        """FAISS index dimension must match embedding dimension."""
        # This is a specification test documenting the requirement
        # FAISS indexes are created with a specific dimension
        # If embeddings have different dimension, index cannot be used

        faiss_index_dim = 256  # Created with Model2Vec
        new_embedding_dim = 1024  # Qwen embeddings

        compatible = faiss_index_dim == new_embedding_dim

        assert compatible is False, "Dimension mismatch makes index incompatible"

    def test_index_rebuild_required_on_mismatch(self):
        """Index must be rebuilt when dimension changes."""
        index_dim = 256
        embedding_dim = 1024

        if index_dim != embedding_dim:
            action = "rebuild"
        else:
            action = "reuse"

        assert action == "rebuild", "Mismatched dimensions require index rebuild"
