"""
Tests for the TM leverage statistics API endpoint.

GET /api/ldm/files/{file_id}/leverage returns per-file leverage stats:
exact, fuzzy, new counts and percentages.

Uses mocked TMSearcher.search_batch to return controlled results.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_search_result(score: float, perfect: bool = False):
    """Build a single TMSearcher result dict."""
    return {
        "tier": 1 if perfect else 2,
        "tier_name": "perfect_whole" if perfect else "whole_embedding",
        "perfect_match": perfect,
        "results": [{
            "entry_id": 1,
            "source_text": "src",
            "target_text": "tgt",
            "score": score,
            "match_type": "perfect_whole" if perfect else "whole_embedding",
        }] if score > 0 else [],
    }


def _no_match_result():
    """Build a no-match TMSearcher result."""
    return {
        "tier": 0,
        "tier_name": "no_match",
        "perfect_match": False,
        "results": [],
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestLeverageEndpoint:
    """Test the leverage statistics calculation logic."""

    @pytest.mark.asyncio
    async def test_leverage_counts(self):
        """Leverage endpoint returns correct exact/fuzzy/new counts."""
        from server.tools.ldm.routes.tm_leverage import _compute_leverage

        # 5 rows: 2 exact (score>=1.0), 1 fuzzy (0.75<=score<1.0), 2 new (no match)
        batch_results = [
            _make_search_result(1.0, perfect=True),   # exact
            _make_search_result(1.0, perfect=True),   # exact
            _make_search_result(0.85),                  # fuzzy
            _no_match_result(),                         # new
            _no_match_result(),                         # new
        ]

        stats = _compute_leverage(batch_results, total=5)

        assert stats["exact"] == 2
        assert stats["fuzzy"] == 1
        assert stats["new"] == 2
        assert stats["total"] == 5
        assert stats["exact_pct"] == pytest.approx(40.0)
        assert stats["fuzzy_pct"] == pytest.approx(20.0)
        assert stats["new_pct"] == pytest.approx(40.0)

    @pytest.mark.asyncio
    async def test_leverage_zero_rows(self):
        """Leverage with 0 rows returns all counts as 0."""
        from server.tools.ldm.routes.tm_leverage import _compute_leverage

        stats = _compute_leverage([], total=0)

        assert stats["exact"] == 0
        assert stats["fuzzy"] == 0
        assert stats["new"] == 0
        assert stats["total"] == 0
        assert stats["exact_pct"] == 0.0
        assert stats["fuzzy_pct"] == 0.0
        assert stats["new_pct"] == 0.0

    @pytest.mark.asyncio
    async def test_leverage_all_exact(self):
        """All rows have exact matches."""
        from server.tools.ldm.routes.tm_leverage import _compute_leverage

        batch_results = [_make_search_result(1.0, perfect=True) for _ in range(3)]
        stats = _compute_leverage(batch_results, total=3)

        assert stats["exact"] == 3
        assert stats["fuzzy"] == 0
        assert stats["new"] == 0
        assert stats["exact_pct"] == pytest.approx(100.0)

    @pytest.mark.asyncio
    async def test_leverage_all_new(self):
        """All rows have no matches (all new)."""
        from server.tools.ldm.routes.tm_leverage import _compute_leverage

        batch_results = [_no_match_result() for _ in range(4)]
        stats = _compute_leverage(batch_results, total=4)

        assert stats["exact"] == 0
        assert stats["fuzzy"] == 0
        assert stats["new"] == 4
        assert stats["new_pct"] == pytest.approx(100.0)

    @pytest.mark.asyncio
    async def test_leverage_no_active_tms(self):
        """When no active TMs exist, all rows are 'new'."""
        from server.tools.ldm.routes.tm_leverage import _compute_leverage_no_tm

        stats = _compute_leverage_no_tm(total=10)

        assert stats["exact"] == 0
        assert stats["fuzzy"] == 0
        assert stats["new"] == 10
        assert stats["total"] == 10
        assert stats["new_pct"] == pytest.approx(100.0)

    @pytest.mark.asyncio
    async def test_fuzzy_threshold_boundary(self):
        """Score exactly at 0.75 counts as fuzzy, below is new."""
        from server.tools.ldm.routes.tm_leverage import _compute_leverage

        batch_results = [
            _make_search_result(0.75),   # fuzzy (at boundary)
            _make_search_result(0.74),   # new (below boundary)
        ]
        # Score 0.74 has results but score < 0.75 => new
        stats = _compute_leverage(batch_results, total=2)

        assert stats["fuzzy"] == 1
        assert stats["new"] == 1
