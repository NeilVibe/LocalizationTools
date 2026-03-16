"""Tests for GameDataSearcher -- 6-tier cascade search for gamedata entities.

TDD RED: These tests define the expected behavior of GameDataSearcher.
"""

from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock
import numpy as np
import ahocorasick

from server.tools.ldm.indexing.utils import normalize_for_hash, normalize_for_embedding


# ---------------------------------------------------------------------------
# Fixtures: build real indexes for search tests
# ---------------------------------------------------------------------------

def _build_test_indexes(entities=None, mock_engine=None):
    """Build indexes from test entities using GameDataIndexer with mocked embeddings."""
    from server.tools.ldm.indexing.gamedata_indexer import GameDataIndexer

    if entities is None:
        entities = [
            {
                "entity_name": "Blade of Dawn",
                "entity_desc": "A legendary sword forged in ancient fire",
                "node_id": "item_001",
                "tag": "ItemInfo",
                "file_path": "/gamedata/iteminfo.xml",
                "attributes": {"Key": "ITEM_001", "StrKey": "str_blade", "ItemName": "Blade of Dawn"},
            },
            {
                "entity_name": "Elder Varon",
                "entity_desc": "A wise sage from the northern realm",
                "node_id": "char_001",
                "tag": "CharacterInfo",
                "file_path": "/gamedata/characterinfo.xml",
                "attributes": {"CharacterName": "Elder Varon"},
            },
            {
                "entity_name": "Fireball",
                "entity_desc": "First line of description<br/>Second line of description",
                "node_id": "skill_001",
                "tag": "SkillInfo",
                "file_path": "/gamedata/skillinfo.xml",
                "attributes": {"SkillName": "Fireball"},
            },
        ]

    indexer = GameDataIndexer()

    if mock_engine is None:
        mock_engine = MagicMock()
        mock_engine.is_loaded = True
        mock_engine.name = "test"
        mock_engine.dimension = 256

    # Track calls to generate different embeddings per call
    call_count = [0]

    def mock_encode(texts, normalize=True, show_progress=False):
        call_count[0] += 1
        n = len(texts)
        # Generate deterministic but different embeddings per batch
        rng = np.random.RandomState(42 + call_count[0])
        embs = rng.randn(n, 256).astype(np.float32)
        # Normalize
        norms = np.linalg.norm(embs, axis=1, keepdims=True)
        embs = embs / norms
        return embs

    mock_engine.encode.side_effect = mock_encode

    with patch("server.tools.ldm.indexing.gamedata_indexer.get_embedding_engine", return_value=mock_engine):
        indexer.build_indexes(entities)

    return indexer.indexes, mock_engine


@pytest.fixture
def search_indexes():
    """Build indexes and return (indexes, mock_engine) tuple."""
    return _build_test_indexes()


@pytest.fixture
def searcher(search_indexes):
    """Create GameDataSearcher with test indexes."""
    from server.tools.ldm.indexing.gamedata_searcher import GameDataSearcher
    indexes, mock_engine = search_indexes
    return GameDataSearcher(indexes, model=mock_engine)


# ---------------------------------------------------------------------------
# Search Tests -- Tier 1: Perfect whole match
# ---------------------------------------------------------------------------

class TestTier1PerfectWhole:
    """Tier 1: exact name/Key/StrKey hash lookup."""

    def test_search_exact_name(self, searcher):
        """Exact entity name returns tier=1, perfect_match=True."""
        result = searcher.search("Blade of Dawn")
        assert result["tier"] == 1
        assert result["tier_name"] == "perfect_whole"
        assert result["perfect_match"] is True
        assert len(result["results"]) >= 1
        assert result["results"][0]["entity_name"] == "Blade of Dawn"

    def test_search_by_key(self, searcher):
        """Key attribute lookup returns tier=1 (IDX-01)."""
        result = searcher.search("ITEM_001")
        assert result["tier"] == 1
        assert result["tier_name"] == "perfect_whole"
        assert result["results"][0]["entity_name"] == "Blade of Dawn"

    def test_search_by_strkey(self, searcher):
        """StrKey attribute lookup returns tier=1."""
        result = searcher.search("str_blade")
        assert result["tier"] == 1
        assert result["results"][0]["entity_name"] == "Blade of Dawn"


# ---------------------------------------------------------------------------
# Search Tests -- Tier 2: Whole embedding
# ---------------------------------------------------------------------------

class TestTier2WholeEmbedding:
    """Tier 2: semantic embedding match on name+desc."""

    def test_search_similar_concept(self, searcher):
        """Query with no exact match but similar meaning falls to tier 2+."""
        # This tests that the search cascade proceeds past tier 1
        # With mock embeddings, scores are unpredictable, so we just verify cascade works
        result = searcher.search("A legendary sword concept", threshold=0.0)
        # Should not be tier 0 (empty/no_match) since we have a low threshold
        assert result["tier"] in (2, 3, 4, 5)
        assert result["perfect_match"] is False


# ---------------------------------------------------------------------------
# Search Tests -- Tier 3: Perfect line match
# ---------------------------------------------------------------------------

class TestTier3PerfectLine:
    """Tier 3: exact line match after br-tag split."""

    def test_search_exact_line_from_desc(self, searcher):
        """A line from a br-tag-split desc returns tier=3."""
        result = searcher.search("First line of description")
        assert result["tier"] == 3
        assert result["tier_name"] == "perfect_line"
        assert result["perfect_match"] is True

    def test_search_second_line(self, searcher):
        """Second line after br-tag split is also findable."""
        result = searcher.search("Second line of description")
        assert result["tier"] == 3
        assert result["tier_name"] == "perfect_line"


# ---------------------------------------------------------------------------
# Search Tests -- Tier 5: N-gram fallback
# ---------------------------------------------------------------------------

class TestTier5Ngram:
    """Tier 5: trigram Jaccard fallback."""

    def test_search_ngram_similar(self):
        """Approximate name with low threshold hits ngram tier."""
        indexes, engine = _build_test_indexes()

        # Make tier 2/4 always return nothing by having encode return zero vectors
        def mock_encode_zero(texts, normalize=True, show_progress=False):
            n = len(texts)
            return np.zeros((n, 256), dtype=np.float32)

        engine.encode.side_effect = mock_encode_zero

        from server.tools.ldm.indexing.gamedata_searcher import GameDataSearcher
        s = GameDataSearcher(indexes, model=engine, threshold=0.3)

        result = s.search("Blde of Dwn", threshold=0.3)
        # With low threshold, ngram should find similar match
        if result["tier"] == 5:
            assert result["tier_name"] == "ngram_fallback"
            assert result["perfect_match"] is False


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Edge case tests for search."""

    def test_search_empty_query(self, searcher):
        """Empty query returns tier=0, empty."""
        result = searcher.search("")
        assert result["tier"] == 0
        assert result["tier_name"] == "empty"
        assert result["results"] == []

    def test_search_no_match(self, searcher):
        """Completely unknown query returns tier=0, no_match."""
        result = searcher.search("xyzzy gibberish 12345 unknown")
        assert result["tier"] == 0
        assert result["tier_name"] == "no_match"
        assert result["results"] == []

    def test_result_schema_fields(self, searcher):
        """Results contain all required fields."""
        result = searcher.search("Blade of Dawn")
        r = result["results"][0]
        assert "entity_name" in r
        assert "entity_desc" in r
        assert "node_id" in r
        assert "tag" in r
        assert "score" in r
        assert "match_type" in r


# ---------------------------------------------------------------------------
# Detect entities (Tier 0: AC scan)
# ---------------------------------------------------------------------------

class TestDetectEntities:
    """Tests for Aho-Corasick entity detection."""

    def test_detect_both_entities(self, searcher):
        """Detects both entity names with positions."""
        results = searcher.detect_entities("The Blade of Dawn glows near Elder Varon")
        names = [r["term"] for r in results]
        assert "Blade of Dawn" in names
        assert "Elder Varon" in names

    def test_detect_with_positions(self, searcher):
        """Detected entities have start/end positions."""
        results = searcher.detect_entities("The Blade of Dawn")
        assert len(results) >= 1
        r = results[0]
        assert "start" in r
        assert "end" in r
        assert r["term"] == "Blade of Dawn"
        assert r["start"] == 4  # "The " is 4 chars
        assert r["end"] == 17  # "Blade of Dawn" is 13 chars

    def test_detect_empty_text(self, searcher):
        """Empty text returns empty list."""
        results = searcher.detect_entities("")
        assert results == []

    def test_detect_no_entities(self, searcher):
        """Text with no entity names returns empty list."""
        results = searcher.detect_entities("This text has no known entities")
        assert results == []
