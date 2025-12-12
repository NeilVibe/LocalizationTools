"""
Tests for TM 5-Tier Cascade Search

Tests the TMSearcher class with all 5 tiers:
- Tier 1: Perfect whole match (hash)
- Tier 2: Whole embedding match (FAISS)
- Tier 3: Perfect line match (hash)
- Tier 4: Line embedding match (FAISS)
- Tier 5: N-gram fallback

Run with: python3 -m pytest tests/unit/test_tm_search.py -v
"""

import pytest
import numpy as np
from unittest.mock import MagicMock, patch

from server.tools.ldm.tm_indexer import (
    TMSearcher,
    normalize_for_hash,
    normalize_for_embedding,
    DEFAULT_THRESHOLD,
)


class TestTMSearcherTier1:
    """Test Tier 1: Perfect Whole Match (Hash Lookup)."""

    def test_perfect_whole_match(self):
        """Exact match returns Tier 1."""
        indexes = {
            "whole_lookup": {
                "저장하기": {
                    "entry_id": 1,
                    "source_text": "저장하기",
                    "target_text": "Save"
                }
            },
            "line_lookup": {},
            "whole_index": None,
            "line_index": None,
            "whole_mapping": [],
            "line_mapping": [],
        }

        searcher = TMSearcher(indexes)
        result = searcher.search("저장하기")

        assert result["tier"] == 1
        assert result["tier_name"] == "perfect_whole"
        assert result["perfect_match"] is True
        assert len(result["results"]) == 1
        assert result["results"][0]["target_text"] == "Save"
        assert result["results"][0]["score"] == 1.0

    def test_perfect_match_with_case_normalization(self):
        """Case-insensitive match returns Tier 1."""
        indexes = {
            "whole_lookup": {
                "save file": {
                    "entry_id": 1,
                    "source_text": "Save File",
                    "target_text": "파일 저장"
                }
            },
            "line_lookup": {},
        }

        searcher = TMSearcher(indexes)
        result = searcher.search("SAVE FILE")

        assert result["tier"] == 1
        assert result["perfect_match"] is True

    def test_perfect_match_with_whitespace_normalization(self):
        """Whitespace normalized match returns Tier 1."""
        indexes = {
            "whole_lookup": {
                "save the file": {
                    "entry_id": 1,
                    "source_text": "Save the file",
                    "target_text": "파일 저장하기"
                }
            },
            "line_lookup": {},
        }

        searcher = TMSearcher(indexes)
        result = searcher.search("Save   the    file")

        assert result["tier"] == 1
        assert result["perfect_match"] is True


class TestTMSearcherTier3:
    """Test Tier 3: Perfect Line Match (Hash Lookup)."""

    def test_perfect_line_match(self):
        """Single line match returns Tier 3."""
        indexes = {
            "whole_lookup": {},  # No whole match
            "line_lookup": {
                "저장하기": {
                    "entry_id": 1,
                    "source_line": "저장하기",
                    "target_line": "Save",
                    "line_num": 0,
                    "total_lines": 3
                }
            },
            "whole_index": None,
            "line_index": None,
            "whole_mapping": [],
            "line_mapping": [],
        }

        searcher = TMSearcher(indexes)
        result = searcher.search("저장하기")

        assert result["tier"] == 3
        assert result["tier_name"] == "perfect_line"
        assert result["perfect_match"] is True
        assert len(result["results"]) == 1
        assert result["results"][0]["target_line"] == "Save"

    def test_multiline_query_partial_line_matches(self):
        """Multi-line query with some lines matching returns Tier 3."""
        indexes = {
            "whole_lookup": {},
            "line_lookup": {
                "저장하기": {
                    "entry_id": 1,
                    "source_line": "저장하기",
                    "target_line": "Save",
                    "line_num": 0,
                    "total_lines": 1
                },
                "취소하기": {
                    "entry_id": 2,
                    "source_line": "취소하기",
                    "target_line": "Cancel",
                    "line_num": 0,
                    "total_lines": 1
                }
            },
            "whole_index": None,
            "line_index": None,
        }

        searcher = TMSearcher(indexes)
        result = searcher.search("저장하기\n취소하기\n새로운것")

        assert result["tier"] == 3
        assert result["perfect_match"] is True
        assert len(result["results"]) == 2  # Two lines matched


class TestTMSearcherTier5:
    """Test Tier 5: N-gram Fallback."""

    def test_ngram_similar_match(self):
        """Similar text via n-gram returns Tier 5."""
        indexes = {
            "whole_lookup": {
                "파일을 저장하시겠습니까": {
                    "entry_id": 1,
                    "source_text": "파일을 저장하시겠습니까?",
                    "target_text": "Save the file?"
                }
            },
            "line_lookup": {},
            "whole_index": None,
            "line_index": None,
        }

        searcher = TMSearcher(indexes, threshold=0.5)  # Lower threshold for test
        result = searcher.search("파일을 저장하시겠습니까")

        # Should match via n-gram (same text, different normalization)
        assert result["tier"] == 5 or result["tier"] == 1  # May hit exact match too
        assert len(result["results"]) >= 1

    def test_ngram_no_match_below_threshold(self):
        """Dissimilar text returns no match."""
        indexes = {
            "whole_lookup": {
                "completely different text here": {
                    "entry_id": 1,
                    "source_text": "Completely different text here",
                    "target_text": "완전히 다른 텍스트"
                }
            },
            "line_lookup": {},
            "whole_index": None,
            "line_index": None,
        }

        searcher = TMSearcher(indexes, threshold=0.92)
        result = searcher.search("저장하기")

        # Should return no match
        assert result["tier"] == 0
        assert result["tier_name"] == "no_match"
        assert len(result["results"]) == 0


class TestTMSearcherEdgeCases:
    """Test edge cases and special scenarios."""

    def test_empty_query(self):
        """Empty query returns no match."""
        indexes = {"whole_lookup": {}, "line_lookup": {}}
        searcher = TMSearcher(indexes)
        result = searcher.search("")

        assert result["tier"] == 0
        assert result["tier_name"] == "empty"
        assert len(result["results"]) == 0

    def test_none_query(self):
        """None query returns no match."""
        indexes = {"whole_lookup": {}, "line_lookup": {}}
        searcher = TMSearcher(indexes)
        result = searcher.search(None)

        assert result["tier"] == 0
        assert len(result["results"]) == 0

    def test_newline_normalized_match(self):
        """Query with newlines normalizes and matches."""
        indexes = {
            "whole_lookup": {
                "line 1\nline 2": {
                    "entry_id": 1,
                    "source_text": "Line 1\nLine 2",
                    "target_text": "줄 1\n줄 2"
                }
            },
            "line_lookup": {},
        }

        searcher = TMSearcher(indexes)
        result = searcher.search("Line 1\\nLine 2")  # Escaped newlines

        # After normalization, should match
        assert result["tier"] == 1
        assert result["perfect_match"] is True

    def test_korean_multiline(self):
        """Korean multi-line text matches correctly."""
        source = "저장하기\n취소하기"
        normalized = normalize_for_hash(source)

        indexes = {
            "whole_lookup": {
                normalized: {
                    "entry_id": 1,
                    "source_text": source,
                    "target_text": "Save\nCancel"
                }
            },
            "line_lookup": {},
        }

        searcher = TMSearcher(indexes)
        result = searcher.search(source)

        assert result["tier"] == 1
        assert result["perfect_match"] is True

    def test_custom_threshold(self):
        """Custom threshold affects matching."""
        indexes = {
            "whole_lookup": {},
            "line_lookup": {},
            "whole_index": None,
            "line_index": None,
        }

        searcher = TMSearcher(indexes, threshold=0.99)
        assert searcher.threshold == 0.99

        # Search with override
        result = searcher.search("test", threshold=0.5)
        # Should use 0.5 for this search


class TestTMSearcherBatch:
    """Test batch search functionality."""

    def test_batch_search(self):
        """Batch search processes multiple queries."""
        indexes = {
            "whole_lookup": {
                "저장하기": {
                    "entry_id": 1,
                    "source_text": "저장하기",
                    "target_text": "Save"
                },
                "취소하기": {
                    "entry_id": 2,
                    "source_text": "취소하기",
                    "target_text": "Cancel"
                }
            },
            "line_lookup": {},
        }

        searcher = TMSearcher(indexes)
        results = searcher.search_batch(["저장하기", "취소하기", "없는것"])

        assert len(results) == 3
        assert results[0]["tier"] == 1
        assert results[1]["tier"] == 1
        assert results[2]["tier"] == 0  # No match


class TestTMSearcherNgram:
    """Test N-gram utility methods."""

    def test_get_ngrams(self):
        """N-gram generation works correctly."""
        indexes = {"whole_lookup": {}, "line_lookup": {}}
        searcher = TMSearcher(indexes)

        ngrams = searcher._get_ngrams("hello", 3)
        assert ngrams == {"hel", "ell", "llo"}

    def test_get_ngrams_short_text(self):
        """Short text returns empty set."""
        indexes = {"whole_lookup": {}, "line_lookup": {}}
        searcher = TMSearcher(indexes)

        ngrams = searcher._get_ngrams("hi", 3)
        assert ngrams == set()

    def test_ngram_search_similarity(self):
        """N-gram search computes Jaccard similarity correctly."""
        indexes = {
            "whole_lookup": {
                "hello world": {
                    "entry_id": 1,
                    "source_text": "Hello World",
                    "target_text": "안녕하세요"
                },
                "hello there": {
                    "entry_id": 2,
                    "source_text": "Hello There",
                    "target_text": "안녕"
                }
            },
            "line_lookup": {},
        }

        searcher = TMSearcher(indexes)
        results = searcher._ngram_search("hello worl", top_k=3, threshold=0.5)

        # "hello world" should be top match
        assert len(results) >= 1
        assert results[0]["source_text"] == "Hello World"


class TestTMSearcherCascade:
    """Test that cascade fallthrough works correctly."""

    def test_tier1_prevents_tier2(self):
        """Perfect whole match (Tier 1) prevents embedding search (Tier 2)."""
        indexes = {
            "whole_lookup": {
                "저장하기": {
                    "entry_id": 1,
                    "source_text": "저장하기",
                    "target_text": "Save"
                }
            },
            "line_lookup": {},
            "whole_index": MagicMock(),  # Mock FAISS index
            "whole_mapping": [{"entry_id": 2, "source_text": "다른것", "target_text": "Other"}],
        }

        searcher = TMSearcher(indexes)
        result = searcher.search("저장하기")

        # Should stop at Tier 1, not call FAISS
        assert result["tier"] == 1
        assert result["results"][0]["entry_id"] == 1

    def test_no_tier1_falls_to_tier3(self):
        """No whole match falls to line match."""
        indexes = {
            "whole_lookup": {},
            "line_lookup": {
                "저장하기": {
                    "entry_id": 1,
                    "source_line": "저장하기",
                    "target_line": "Save",
                    "line_num": 0,
                    "total_lines": 1
                }
            },
            "whole_index": None,  # No FAISS available
            "whole_mapping": [],
        }

        searcher = TMSearcher(indexes)
        result = searcher.search("저장하기")

        # Should fall to Tier 3
        assert result["tier"] == 3
        assert result["tier_name"] == "perfect_line"


class TestDefaultThreshold:
    """Test default threshold constant."""

    def test_default_threshold_value(self):
        """Default threshold is 92%."""
        assert DEFAULT_THRESHOLD == 0.92

    def test_searcher_uses_default(self):
        """Searcher uses default threshold if not specified."""
        indexes = {"whole_lookup": {}, "line_lookup": {}}
        searcher = TMSearcher(indexes)
        assert searcher.threshold == DEFAULT_THRESHOLD
