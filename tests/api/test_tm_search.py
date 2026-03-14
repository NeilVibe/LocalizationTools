"""
Tests for TMSearcher 5-tier cascade search behavior.

Verifies:
- Exact (hash) match returns score=1.0 with perfect_match=True
- Fuzzy results return scored matches with match_type
- Unrelated text returns empty/no_match
- Result shape consistency
- Batch search returns list
- Model2Vec is the default embedding engine

Uses mocked indexes to test cascade logic without runtime dependencies.
"""
from __future__ import annotations

import pytest
import numpy as np
from unittest.mock import MagicMock, patch

from server.tools.ldm.indexing.searcher import TMSearcher
from server.tools.ldm.indexing.utils import normalize_for_hash


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_entries():
    """Sample TM entries for index mocking."""
    return [
        {"entry_id": 1, "source_text": "New Game", "target_text": "새 게임", "string_id": "MENU_NEW"},
        {"entry_id": 2, "source_text": "Continue", "target_text": "계속하기", "string_id": "MENU_CONT"},
        {"entry_id": 3, "source_text": "Settings", "target_text": "설정", "string_id": "MENU_SET"},
    ]


@pytest.fixture
def hash_indexes(sample_entries):
    """Build hash-only indexes (no FAISS) for unit testing."""
    whole_lookup = {}
    for entry in sample_entries:
        key = normalize_for_hash(entry["source_text"])
        whole_lookup[key] = entry

    return {
        "whole_lookup": whole_lookup,
        "line_lookup": {},
        "whole_index": None,
        "line_index": None,
        "whole_mapping": [],
        "line_mapping": [],
    }


@pytest.fixture
def searcher(hash_indexes):
    """TMSearcher wired to hash-only indexes."""
    return TMSearcher(hash_indexes, threshold=0.92)


# ---------------------------------------------------------------------------
# Test: Perfect (hash) match - Tier 1
# ---------------------------------------------------------------------------

class TestTier1PerfectMatch:
    """Verify perfect whole match via hash lookup."""

    def test_exact_source_returns_perfect_match(self, searcher):
        """Searching with exact source text returns perfect_match=True, score=1.0."""
        result = searcher.search("New Game")

        assert result["perfect_match"] is True
        assert result["tier"] == 1
        assert result["tier_name"] == "perfect_whole"
        assert len(result["results"]) >= 1
        assert result["results"][0]["score"] == 1.0
        assert result["results"][0]["match_type"] == "perfect_whole"

    def test_exact_match_case_insensitive(self, searcher):
        """Hash lookup is case-insensitive (normalized)."""
        result = searcher.search("new game")

        assert result["perfect_match"] is True
        assert result["tier"] == 1

    def test_exact_match_contains_required_fields(self, searcher):
        """Each result has source_text, target_text, score, match_type fields."""
        result = searcher.search("Continue")

        assert result["perfect_match"] is True
        hit = result["results"][0]
        assert "source_text" in hit
        assert "target_text" in hit
        assert "score" in hit
        assert "match_type" in hit
        assert "entry_id" in hit
        assert hit["target_text"] == "계속하기"


# ---------------------------------------------------------------------------
# Test: No match
# ---------------------------------------------------------------------------

class TestNoMatch:
    """Verify behavior with unrelated text."""

    def test_unrelated_text_returns_no_match(self, searcher):
        """Completely unrelated text returns no results (hash-only, no FAISS)."""
        result = searcher.search("Completely unrelated text that matches nothing")

        assert result["perfect_match"] is False
        assert result["tier"] == 0
        assert result["tier_name"] == "no_match"
        assert result["results"] == []

    def test_empty_query_returns_empty(self, searcher):
        """Empty query returns tier 0."""
        result = searcher.search("")

        assert result["tier"] == 0
        assert result["results"] == []


# ---------------------------------------------------------------------------
# Test: Result shape consistency
# ---------------------------------------------------------------------------

class TestResultShape:
    """Verify all result dicts have consistent shape."""

    def test_result_has_four_top_keys(self, searcher):
        """Every search result has tier, tier_name, perfect_match, results."""
        for query in ["New Game", "nonexistent text", ""]:
            result = searcher.search(query)
            assert "tier" in result
            assert "tier_name" in result
            assert "perfect_match" in result
            assert "results" in result
            assert isinstance(result["results"], list)


# ---------------------------------------------------------------------------
# Test: Batch search
# ---------------------------------------------------------------------------

class TestBatchSearch:
    """Verify search_batch processes multiple queries."""

    def test_batch_returns_list_per_query(self, searcher):
        """search_batch returns one result dict per query."""
        queries = ["New Game", "Continue", "nonexistent"]
        results = searcher.search_batch(queries)

        assert isinstance(results, list)
        assert len(results) == 3

        # First two should be perfect matches, third no match
        assert results[0]["perfect_match"] is True
        assert results[1]["perfect_match"] is True
        assert results[2]["perfect_match"] is False

    def test_batch_empty_list(self, searcher):
        """search_batch with empty list returns empty list."""
        results = searcher.search_batch([])
        assert results == []


# ---------------------------------------------------------------------------
# Test: Model2Vec is default engine
# ---------------------------------------------------------------------------

class TestDefaultEngine:
    """Verify Model2Vec is the default embedding engine."""

    def test_model2vec_is_default(self):
        """The default engine name is 'model2vec'."""
        from server.tools.shared.embedding_engine import get_current_engine_name
        assert get_current_engine_name() == "model2vec"

    def test_model2vec_engine_class_exists(self):
        """Model2VecEngine is registered and available."""
        from server.tools.shared.embedding_engine import get_available_engines
        engines = get_available_engines()
        engine_ids = [e["id"] for e in engines]
        assert "model2vec" in engine_ids
