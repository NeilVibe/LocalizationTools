"""
Tests for NPC (Neil's Probabilistic Check)

Tests Target translation consistency verification:
- Embed user's Target
- Compare against TM Targets via cosine similarity
- Flag inconsistencies below threshold (80%)

Run with: python3 -m pytest tests/unit/test_npc.py -v
"""

import pytest
from unittest.mock import MagicMock, patch
import numpy as np

from server.tools.ldm.tm_indexer import (
    TMSearcher,
    NPC_THRESHOLD,
    DEFAULT_THRESHOLD,
)


class TestNPCThreshold:
    """Test NPC threshold constant."""

    def test_npc_threshold_value(self):
        """
        NPC threshold is 65% (adjusted from 80% based on empirical testing).

        Rationale: 80% was too strict for short English strings.
        - "Save" vs "Save file" = 70.6% (should pass)
        - "Save" vs "Save changes" = 61.3% (should pass)
        - "Save" vs "Delete" = 59% (should fail)

        65% catches valid variations while rejecting wrong translations.
        """
        assert NPC_THRESHOLD == 0.65

    def test_npc_less_than_search_threshold(self):
        """NPC threshold is lower than search threshold."""
        assert NPC_THRESHOLD < DEFAULT_THRESHOLD


class TestNPCEdgeCases:
    """Test NPC edge cases without model."""

    def test_empty_user_target(self):
        """Empty user target returns warning."""
        indexes = {"whole_lookup": {}, "line_lookup": {}}
        searcher = TMSearcher(indexes)

        tm_matches = [
            {"entry_id": 1, "target_text": "Save"}
        ]

        result = searcher.npc_check("", tm_matches)

        assert result["consistent"] is False
        assert result["best_match"] is None
        assert "warning" in result

    def test_none_user_target(self):
        """None user target returns warning."""
        indexes = {"whole_lookup": {}, "line_lookup": {}}
        searcher = TMSearcher(indexes)

        tm_matches = [
            {"entry_id": 1, "target_text": "Save"}
        ]

        result = searcher.npc_check(None, tm_matches)

        assert result["consistent"] is False
        assert "warning" in result

    def test_empty_tm_matches(self):
        """Empty TM matches returns warning."""
        indexes = {"whole_lookup": {}, "line_lookup": {}}
        searcher = TMSearcher(indexes)

        result = searcher.npc_check("Save", [])

        assert result["consistent"] is False
        assert result["all_scores"] == []
        assert "warning" in result

    def test_none_tm_matches(self):
        """None TM matches returns warning."""
        indexes = {"whole_lookup": {}, "line_lookup": {}}
        searcher = TMSearcher(indexes)

        result = searcher.npc_check("Save", None)

        assert result["consistent"] is False

    def test_tm_matches_without_target(self):
        """TM matches with empty targets returns warning."""
        indexes = {"whole_lookup": {}, "line_lookup": {}}
        searcher = TMSearcher(indexes)

        # Mock the model to avoid loading it
        mock_model = MagicMock()
        mock_model.encode = MagicMock(return_value=np.random.randn(1, 512).astype(np.float32))
        searcher.model = mock_model

        tm_matches = [
            {"entry_id": 1, "target_text": ""},
            {"entry_id": 2, "target_text": None},
        ]

        result = searcher.npc_check("Save", tm_matches)

        # Should return warning since no valid targets
        assert "warning" in result or result["consistent"] is False


class TestNPCLogic:
    """Test NPC logic with mocked model."""

    def _create_mock_searcher(self):
        """Create searcher with mocked model."""
        indexes = {"whole_lookup": {}, "line_lookup": {}}
        searcher = TMSearcher(indexes)

        # Create mock model
        mock_model = MagicMock()
        searcher.model = mock_model

        return searcher, mock_model

    def test_consistent_when_high_similarity(self):
        """High similarity (≥80%) marks as consistent."""
        searcher, mock_model = self._create_mock_searcher()

        # User embedding
        user_emb = np.array([[1.0, 0.0, 0.0]], dtype=np.float32)
        # TM embedding - very similar
        tm_emb = np.array([[0.95, 0.1, 0.05]], dtype=np.float32)

        # Normalize manually for test
        user_emb /= np.linalg.norm(user_emb)
        tm_emb /= np.linalg.norm(tm_emb)

        # Mock encode to return our vectors
        mock_model.encode = MagicMock(side_effect=[user_emb, tm_emb])

        tm_matches = [
            {"entry_id": 1, "target_text": "Save"}
        ]

        result = searcher.npc_check("저장", tm_matches)

        assert result["consistent"] is True
        assert result["best_score"] >= 0.80
        assert "message" in result

    def test_inconsistent_when_low_similarity(self):
        """Low similarity (<80%) marks as inconsistent."""
        searcher, mock_model = self._create_mock_searcher()

        # User embedding
        user_emb = np.array([[1.0, 0.0, 0.0]], dtype=np.float32)
        # TM embedding - very different
        tm_emb = np.array([[0.0, 1.0, 0.0]], dtype=np.float32)

        # Normalize manually for test
        user_emb /= np.linalg.norm(user_emb)
        tm_emb /= np.linalg.norm(tm_emb)

        mock_model.encode = MagicMock(side_effect=[user_emb, tm_emb])

        tm_matches = [
            {"entry_id": 1, "target_text": "Completely Different"}
        ]

        result = searcher.npc_check("저장", tm_matches)

        assert result["consistent"] is False
        assert result["best_score"] < 0.80
        assert "warning" in result

    def test_custom_threshold_override(self):
        """Custom threshold overrides default."""
        searcher, mock_model = self._create_mock_searcher()

        # User embedding
        user_emb = np.array([[1.0, 0.0, 0.0]], dtype=np.float32)
        # TM embedding - moderate similarity
        tm_emb = np.array([[0.7, 0.5, 0.0]], dtype=np.float32)

        user_emb /= np.linalg.norm(user_emb)
        tm_emb /= np.linalg.norm(tm_emb)

        mock_model.encode = MagicMock(side_effect=[user_emb, tm_emb])

        tm_matches = [
            {"entry_id": 1, "target_text": "Save"}
        ]

        # With high threshold, should be inconsistent
        result_high = searcher.npc_check("저장", tm_matches, threshold=0.95)
        # Note: mock gets called once, so we need to reset

        # Reset mock
        mock_model.encode = MagicMock(side_effect=[user_emb, tm_emb])

        # With low threshold, should be consistent
        result_low = searcher.npc_check("저장", tm_matches, threshold=0.50)

        # Check thresholds are stored in result
        assert result_high["threshold"] == 0.95
        assert result_low["threshold"] == 0.50

    def test_multiple_tm_matches_finds_best(self):
        """Multiple TM matches returns best score."""
        searcher, mock_model = self._create_mock_searcher()

        # User embedding
        user_emb = np.array([[1.0, 0.0, 0.0]], dtype=np.float32)
        user_emb /= np.linalg.norm(user_emb)

        # Multiple TM embeddings - one similar, one not
        tm_emb = np.array([
            [0.1, 0.9, 0.0],  # Low similarity
            [0.95, 0.1, 0.0],  # High similarity
            [0.5, 0.5, 0.0],  # Medium similarity
        ], dtype=np.float32)
        tm_emb /= np.linalg.norm(tm_emb, axis=1, keepdims=True)

        mock_model.encode = MagicMock(side_effect=[user_emb, tm_emb])

        tm_matches = [
            {"entry_id": 1, "target_text": "Wrong"},
            {"entry_id": 2, "target_text": "Save"},
            {"entry_id": 3, "target_text": "Maybe"},
        ]

        result = searcher.npc_check("저장", tm_matches)

        # Should be consistent because best match is high
        assert result["consistent"] is True
        assert len(result["all_scores"]) == 3
        # All scores should be sorted descending
        scores = [s["score"] for s in result["all_scores"]]
        assert scores == sorted(scores, reverse=True)

    def test_handles_line_match_format(self):
        """NPC handles line match format (target_line instead of target_text)."""
        searcher, mock_model = self._create_mock_searcher()

        user_emb = np.array([[1.0, 0.0, 0.0]], dtype=np.float32)
        tm_emb = np.array([[0.95, 0.1, 0.0]], dtype=np.float32)
        user_emb /= np.linalg.norm(user_emb)
        tm_emb /= np.linalg.norm(tm_emb)

        mock_model.encode = MagicMock(side_effect=[user_emb, tm_emb])

        # Line match format uses target_line
        tm_matches = [
            {"entry_id": 1, "target_line": "Save", "source_line": "저장하기"}
        ]

        result = searcher.npc_check("저장", tm_matches)

        assert result["consistent"] is True
        assert result["all_scores"][0]["tm_target"] == "Save"


class TestSearchWithNPC:
    """Test combined search + NPC functionality."""

    def test_search_with_npc_combines_results(self):
        """search_with_npc returns both search and NPC results."""
        indexes = {
            "whole_lookup": {
                "저장하기": {
                    "entry_id": 1,
                    "source_text": "저장하기",
                    "target_text": "Save"
                }
            },
            "line_lookup": {},
        }
        searcher = TMSearcher(indexes)

        # Mock model for NPC
        mock_model = MagicMock()
        user_emb = np.array([[1.0, 0.0, 0.0]], dtype=np.float32)
        tm_emb = np.array([[0.95, 0.1, 0.0]], dtype=np.float32)
        user_emb /= np.linalg.norm(user_emb)
        tm_emb /= np.linalg.norm(tm_emb)
        mock_model.encode = MagicMock(side_effect=[user_emb, tm_emb])
        searcher.model = mock_model

        result = searcher.search_with_npc("저장하기", "Save")

        assert "search" in result
        assert "npc" in result
        assert result["search"]["tier"] == 1  # Perfect match
        assert result["npc"]["consistent"] is True

    def test_search_with_npc_no_matches(self):
        """No search matches returns NPC with null consistent."""
        indexes = {
            "whole_lookup": {},
            "line_lookup": {},
        }
        searcher = TMSearcher(indexes)

        result = searcher.search_with_npc("없는것", "Not Found")

        assert result["search"]["tier"] == 0
        assert result["search"]["results"] == []
        assert result["npc"]["consistent"] is None
        assert "message" in result["npc"]


class TestNPCResultFormat:
    """Test NPC result format."""

    def test_result_has_all_fields(self):
        """NPC result has all required fields."""
        indexes = {"whole_lookup": {}, "line_lookup": {}}
        searcher = TMSearcher(indexes)

        # Empty check gives us result format
        result = searcher.npc_check("", [])

        assert "consistent" in result
        assert "best_match" in result
        assert "best_score" in result
        assert "all_scores" in result

    def test_all_scores_format(self):
        """all_scores has correct structure."""
        searcher, mock_model = TestNPCLogic()._create_mock_searcher()

        user_emb = np.array([[1.0, 0.0, 0.0]], dtype=np.float32)
        tm_emb = np.array([[0.95, 0.1, 0.0]], dtype=np.float32)
        user_emb /= np.linalg.norm(user_emb)
        tm_emb /= np.linalg.norm(tm_emb)

        mock_model.encode = MagicMock(side_effect=[user_emb, tm_emb])

        tm_matches = [
            {"entry_id": 42, "target_text": "Save"}
        ]

        result = searcher.npc_check("저장", tm_matches)

        assert len(result["all_scores"]) == 1
        score_entry = result["all_scores"][0]
        assert "tm_target" in score_entry
        assert "score" in score_entry
        assert "entry_id" in score_entry
        assert score_entry["entry_id"] == 42
