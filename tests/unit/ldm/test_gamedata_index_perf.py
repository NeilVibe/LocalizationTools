"""Performance tests for GameData indexing -- 5000+ entities budget validation.

Phase 29: Multi-Tier Indexing (Plan 02, Task 2)

Validates:
- IDX-05: 5000+ entity index build completes in <3 seconds
- Search latency: <50ms per query after build
- AC detection latency: <10ms for 1000-char text
- br-tag line splitting produces correct line_lookup entries
"""

from __future__ import annotations

import random
import string
import time
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

from server.tools.ldm.indexing.gamedata_indexer import GameDataIndexer
from server.tools.ldm.indexing.gamedata_searcher import GameDataSearcher


def _random_word(length: int = 8) -> str:
    """Generate a random word-like token."""
    return "".join(random.choices(string.ascii_lowercase, k=length))


def _random_desc(min_len: int = 10, max_len: int = 80, br_chance: float = 0.2) -> str:
    """Generate random description, optionally with <br/> tags."""
    words = [_random_word(random.randint(3, 10)) for _ in range(random.randint(3, 15))]
    text = " ".join(words)[:max_len]
    if random.random() < br_chance:
        # Insert a <br/> in the middle
        mid = len(text) // 2
        text = text[:mid] + "<br/>" + text[mid:]
    return text


def generate_synthetic_entities(count: int = 5000) -> List[Dict[str, Any]]:
    """Generate realistic gamedata entities for perf testing.

    Mix of entity types with varied name/desc lengths:
    - 40% ItemInfo (name 5-20 chars, desc 10-80 chars with occasional <br/>)
    - 20% CharacterInfo (name 5-25 chars, no desc)
    - 20% SkillInfo (name 5-15 chars, desc 20-60 chars)
    - 10% QuestInfo (name 10-30 chars, desc 30-100 chars with <br/>)
    - 10% RegionInfo (name 5-20 chars, desc 20-50 chars)
    """
    random.seed(42)  # Reproducible

    tags_config = [
        ("ItemInfo", "ItemName", "ItemDesc", 0.4, (5, 20), (10, 80), 0.2),
        ("CharacterInfo", "CharacterName", None, 0.2, (5, 25), None, 0.0),
        ("SkillInfo", "SkillName", "SkillDesc", 0.2, (5, 15), (20, 60), 0.1),
        ("QuestInfo", "QuestName", "QuestDesc", 0.1, (10, 30), (30, 100), 0.4),
        ("RegionInfo", "RegionName", "RegionDesc", 0.1, (5, 20), (20, 50), 0.15),
    ]

    entities: List[Dict[str, Any]] = []
    for i in range(count):
        # Pick type by cumulative distribution
        r = random.random()
        cumulative = 0.0
        for tag, name_attr, desc_attr, prob, name_range, desc_range, br_chance in tags_config:
            cumulative += prob
            if r <= cumulative:
                break

        name_len = random.randint(name_range[0], name_range[1])
        entity_name = f"{tag[:4]}_{_random_word(name_len)}_{i}"

        entity_desc = ""
        if desc_attr and desc_range:
            entity_desc = _random_desc(desc_range[0], desc_range[1], br_chance)

        entities.append({
            "entity_name": entity_name,
            "entity_desc": entity_desc,
            "node_id": f"perf_r{i}",
            "tag": tag,
            "file_path": f"/mock/perf_{tag.lower()}.xml",
            "attributes": {
                name_attr: entity_name,
                "Key": f"key_{i}",
                "StrKey": f"strkey_{i}",
            },
        })

    return entities


# Mock the embedding engine to avoid loading real model
def _mock_embedding_engine():
    """Create a mock embedding engine for perf tests."""
    import numpy as np

    engine = MagicMock()
    engine.dimension = 256
    engine.is_loaded = True
    engine.name = "mock-perf"

    def _encode(texts, normalize=True, show_progress=False):
        if isinstance(texts, str):
            texts = [texts]
        vecs = np.random.RandomState(42).randn(len(texts), 256).astype(np.float32)
        if normalize:
            norms = np.linalg.norm(vecs, axis=1, keepdims=True)
            norms = np.where(norms == 0, 1, norms)
            vecs = vecs / norms
        return vecs

    engine.encode = _encode
    engine.load = MagicMock()
    return engine


@pytest.fixture(autouse=True)
def mock_embedding():
    """Mock embedding engine for all perf tests."""
    mock_engine = _mock_embedding_engine()
    with patch(
        "server.tools.ldm.indexing.gamedata_indexer.get_embedding_engine",
        return_value=mock_engine,
    ), patch(
        "server.tools.ldm.indexing.gamedata_indexer.get_current_engine_name",
        return_value="mock-perf",
    ), patch(
        "server.tools.ldm.indexing.gamedata_searcher.get_embedding_engine",
        return_value=mock_engine,
    ), patch(
        "server.tools.ldm.indexing.gamedata_searcher.get_current_engine_name",
        return_value="mock-perf",
    ):
        yield mock_engine


class TestIndexBuildPerformance:
    """Test index build performance with 5000+ entities."""

    def test_index_build_5000_entities(self):
        """IDX-05: Build indexes for 5000 entities in under 3000ms."""
        indexer = GameDataIndexer()
        entities = generate_synthetic_entities(5000)

        start = time.monotonic()
        result = indexer.build_indexes(entities)
        elapsed_ms = (time.monotonic() - start) * 1000

        assert elapsed_ms < 3000, f"Build took {elapsed_ms:.0f}ms (budget: 3000ms)"
        assert result["entity_count"] == 5000
        assert result["whole_lookup_count"] >= 4000  # 3 keys per entity but dedup
        assert result["ac_terms_count"] > 0

    def test_index_build_produces_whole_lookup(self):
        """Whole lookup should have entries for name + Key + StrKey per entity."""
        indexer = GameDataIndexer()
        entities = generate_synthetic_entities(5000)
        result = indexer.build_indexes(entities)

        # Each entity adds up to 3 keys (name, Key, StrKey)
        assert result["whole_lookup_count"] >= 4000

    def test_index_build_produces_ac_automaton(self):
        """AC automaton should detect entities in sample text."""
        indexer = GameDataIndexer()
        entities = generate_synthetic_entities(5000)
        indexer.build_indexes(entities)

        # Pick some entity names and embed in text
        sample_names = [e["entity_name"] for e in entities[:5]]
        text = " and ".join(sample_names) + " in the story"

        searcher = GameDataSearcher(indexer.indexes)
        detected = searcher.detect_entities(text)

        assert len(detected) >= 3, f"Expected at least 3 detections, got {len(detected)}"

    def test_index_build_line_lookup_with_br_tags(self):
        """Entities with <br/>-separated descriptions produce line_lookup entries."""
        indexer = GameDataIndexer()

        # Create entities with known br-tag descriptions
        entities = [
            {
                "entity_name": f"TestItem_{i}",
                "entity_desc": f"First line of item {i}<br/>Second line of item {i}",
                "node_id": f"br_r{i}",
                "tag": "ItemInfo",
                "file_path": "/mock/br_test.xml",
                "attributes": {"ItemName": f"TestItem_{i}"},
            }
            for i in range(100)
        ]

        result = indexer.build_indexes(entities)

        # Each entity has 2 lines -> at least 100 line_lookup entries (some dedup possible)
        assert result["line_lookup_count"] >= 100, (
            f"Expected >= 100 line_lookup entries, got {result['line_lookup_count']}"
        )


class TestSearchPerformance:
    """Test search latency after 5000-entity build."""

    def test_search_latency_after_5000_build(self):
        """Each search query completes in under 50ms."""
        indexer = GameDataIndexer()
        entities = generate_synthetic_entities(5000)
        indexer.build_indexes(entities)

        searcher = GameDataSearcher(indexer.indexes)

        # 10 random queries -- search by entity name (should hit tier 1)
        for _ in range(10):
            entity = random.choice(entities)
            start = time.monotonic()
            result = searcher.search(entity["entity_name"])
            elapsed_ms = (time.monotonic() - start) * 1000

            assert elapsed_ms < 50, f"Search took {elapsed_ms:.0f}ms (budget: 50ms)"
            assert result["tier"] >= 1, "Should find a match"

    def test_ac_detect_latency(self):
        """AC detection scans text in under 10ms."""
        indexer = GameDataIndexer()
        entities = generate_synthetic_entities(5000)
        indexer.build_indexes(entities)

        searcher = GameDataSearcher(indexer.indexes)

        # Build long text with embedded entity names
        sample_names = [e["entity_name"] for e in random.sample(entities, 20)]
        text = " and then ".join(sample_names) + " appeared in the story"

        start = time.monotonic()
        detected = searcher.detect_entities(text)
        elapsed_ms = (time.monotonic() - start) * 1000

        assert elapsed_ms < 10, f"Detect took {elapsed_ms:.0f}ms (budget: 10ms)"
        assert len(detected) >= 10, f"Expected >= 10 detections, got {len(detected)}"
