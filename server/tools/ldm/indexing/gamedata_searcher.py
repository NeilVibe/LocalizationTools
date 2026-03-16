"""GameData Searcher -- 6-Tier Cascade search for gamedata entities.

Adapted from TMSearcher (searcher.py). Adds Tier 0 (Aho-Corasick) and adapts
result schema for gamedata (node_id, tag instead of entry_id).

Tier 0: Aho-Corasick entity detection (O(n) multi-pattern match)
Tier 1: Perfect whole match (hash) -- exact entity name, Key, or StrKey
Tier 2: Whole embedding match (FAISS HNSW) -- semantic on name+desc
Tier 3: Perfect line match (hash) -- exact desc line after br-split
Tier 4: Line embedding match (FAISS HNSW) -- semantic on desc lines
Tier 5: N-gram fallback -- Jaccard trigram on entity names

Phase 29: Multi-Tier Indexing (Plan 01)
"""

from __future__ import annotations

import numpy as np
from typing import Any, Dict, List, Optional

from loguru import logger

try:
    import faiss  # noqa: F401
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False

from server.tools.shared import get_embedding_engine, get_current_engine_name
from server.tools.ldm.indexing.utils import (
    normalize_for_hash,
    normalize_for_embedding,
    normalize_newlines_universal,
)
from server.utils.qa_helpers import is_isolated


# Default threshold for gamedata matching (92%)
DEFAULT_THRESHOLD = 0.92


class GameDataSearcher:
    """6-Tier Cascade search for gamedata entities.

    Adapted from TMSearcher. Adds Tier 0 (Aho-Corasick) and adapts
    result schema for gamedata (node_id, tag instead of entry_id).

    Usage:
        searcher = GameDataSearcher(indexes)
        results = searcher.search("query text")
        entities = searcher.detect_entities("text with entity names")
    """

    DEFAULT_THRESHOLD = DEFAULT_THRESHOLD

    def __init__(
        self,
        indexes: Dict[str, Any],
        model=None,
        threshold: float = DEFAULT_THRESHOLD,
    ):
        """Initialize with indexes dict from GameDataIndexer.build_indexes().

        Args:
            indexes: Dict containing whole_lookup, line_lookup, whole_index, etc.
            model: EmbeddingEngine instance (will load default if None)
            threshold: Similarity threshold (default 0.92)
        """
        self.indexes = indexes
        self.threshold = threshold
        self._engine = model

        self.whole_lookup = indexes.get("whole_lookup", {})
        self.line_lookup = indexes.get("line_lookup", {})
        self.whole_index = indexes.get("whole_index")
        self.line_index = indexes.get("line_index")
        self.whole_mapping = indexes.get("whole_mapping", [])
        self.line_mapping = indexes.get("line_mapping", [])
        self.ac_automaton = indexes.get("ac_automaton")

    def _ensure_model_loaded(self):
        """Load embedding engine if not already loaded."""
        if self._engine is None or not self._engine.is_loaded:
            if not FAISS_AVAILABLE:
                raise RuntimeError("faiss not available")
            engine_name = get_current_engine_name()
            logger.info(f"[GameDataSearcher] Loading embedding engine: {engine_name}")
            self._engine = get_embedding_engine(engine_name)
            self._engine.load()
            logger.success(f"[GameDataSearcher] Embedding engine loaded: {self._engine.name}")

    @property
    def model(self):
        """Return engine for code that uses self.model.encode()."""
        self._ensure_model_loaded()
        return self._engine

    # =========================================================================
    # Main Search (6-Tier Cascade)
    # =========================================================================

    def search(
        self,
        query: str,
        top_k: int = 5,
        threshold: float = None,
    ) -> Dict[str, Any]:
        """Perform 6-Tier Cascade search.

        Args:
            query: Text to search for
            top_k: Max results for embedding tiers
            threshold: Override default threshold

        Returns:
            Dict with tier, tier_name, results, perfect_match.
            Each result: {entity_name, entity_desc, node_id, tag, file_path, score, match_type}
        """
        if not query:
            return {"tier": 0, "tier_name": "empty", "results": [], "perfect_match": False}

        threshold = threshold if threshold is not None else self.threshold
        query_normalized = normalize_for_hash(query)
        query_for_embedding = normalize_for_embedding(query)

        # TIER 1: Perfect Whole Match (Hash Lookup)
        # Finds exact name, Key, or StrKey matches
        if query_normalized in self.whole_lookup:
            match = self.whole_lookup[query_normalized]
            result = self._format_whole_result(match, "perfect_whole")
            return {
                "tier": 1,
                "tier_name": "perfect_whole",
                "perfect_match": True,
                "results": [result],
            }

        # TIER 2: Whole Embedding Match (FAISS)
        if FAISS_AVAILABLE and self.whole_index and self.whole_mapping:
            try:
                self._ensure_model_loaded()
            except RuntimeError as e:
                logger.warning(f"[GameDataSearcher] Tier 2 skipped — {e}")
                self.whole_index = None  # Disable for remaining tiers

            query_embedding = self.model.encode(
                [query_for_embedding], normalize=True, show_progress=False
            )
            query_embedding = np.array(query_embedding, dtype=np.float32)

            scores, indices = self.whole_index.search(
                query_embedding, min(top_k * 2, 20)
            )

            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx < 0 or idx >= len(self.whole_mapping):
                    continue
                if score < threshold:
                    continue

                match = self.whole_mapping[idx]
                results.append(self._format_whole_result(match, "whole_embedding", float(score)))

                if len(results) >= top_k:
                    break

            if results:
                return {
                    "tier": 2,
                    "tier_name": "whole_embedding",
                    "perfect_match": False,
                    "results": results,
                }

        # TIER 3: Perfect Line Match (Hash Lookup)
        # Use normalize_newlines_universal to handle both <br/> and \n in query
        normalized_query = normalize_newlines_universal(query)
        query_lines = normalized_query.split("\n")
        line_matches = []

        for i, line in enumerate(query_lines):
            line_normalized = normalize_for_hash(line)
            if not line_normalized:
                continue

            if line_normalized in self.line_lookup:
                match = self.line_lookup[line_normalized]
                line_matches.append({
                    "entity_name": match["entity_name"],
                    "entity_desc": match.get("entity_desc", ""),
                    "node_id": match["node_id"],
                    "tag": match["tag"],
                    "file_path": match.get("file_path", ""),
                    "score": 1.0,
                    "match_type": "perfect_line",
                    "source_line": match.get("source_line", ""),
                    "query_line_num": i,
                    "line_num": match.get("line_num", 0),
                })

        if line_matches:
            return {
                "tier": 3,
                "tier_name": "perfect_line",
                "perfect_match": True,
                "results": line_matches,
            }

        # TIER 4: Line Embedding Match (FAISS)
        if FAISS_AVAILABLE and self.line_index and self.line_mapping and query_lines:
            try:
                self._ensure_model_loaded()
            except RuntimeError as e:
                logger.warning(f"[GameDataSearcher] Tier 4 skipped — {e}")
                self.line_index = None

            line_results = []
            for i, line in enumerate(query_lines):
                line_for_embedding = normalize_for_embedding(line)
                if not line_for_embedding or len(line_for_embedding) < 3:
                    continue

                line_embedding = self.model.encode(
                    [line_for_embedding], normalize=True, show_progress=False
                )
                line_embedding = np.array(line_embedding, dtype=np.float32)

                scores, indices = self.line_index.search(
                    line_embedding, min(top_k * 2, 20)
                )

                for score, idx in zip(scores[0], indices[0]):
                    if idx < 0 or idx >= len(self.line_mapping):
                        continue
                    if score < threshold:
                        continue

                    match = self.line_mapping[idx]
                    line_results.append({
                        "entity_name": match["entity_name"],
                        "entity_desc": match.get("entity_desc", ""),
                        "node_id": match["node_id"],
                        "tag": match["tag"],
                        "file_path": match.get("file_path", ""),
                        "score": float(score),
                        "match_type": "line_embedding",
                        "source_line": match.get("source_line", ""),
                        "query_line_num": i,
                        "line_num": match.get("line_num", 0),
                    })
                    break

            if line_results:
                line_results.sort(key=lambda x: x["score"], reverse=True)
                return {
                    "tier": 4,
                    "tier_name": "line_embedding",
                    "perfect_match": False,
                    "results": line_results[:top_k],
                }

        # TIER 5: N-gram Fallback
        results = self._ngram_search(query_normalized, top_k, threshold)
        if results:
            return {
                "tier": 5,
                "tier_name": "ngram_fallback",
                "perfect_match": False,
                "results": results,
            }

        return {"tier": 0, "tier_name": "no_match", "perfect_match": False, "results": []}

    # =========================================================================
    # Tier 0: Entity Detection (Aho-Corasick)
    # =========================================================================

    def detect_entities(self, text: str) -> List[Dict[str, Any]]:
        """Tier 0: Aho-Corasick scan for entity names in text.

        Uses ac_automaton.iter(text) pattern from GlossaryService.detect_entities.
        Returns list of {term, start, end, node_id, tag, entity_name}.
        Uses is_isolated() from qa_helpers for word boundary check.
        """
        if not text or self.ac_automaton is None:
            return []

        results = []
        for end_index, (pattern_id, original_term, node_id, tag) in self.ac_automaton.iter(text):
            start_index = end_index - len(original_term) + 1
            end_pos = end_index + 1

            # Word boundary check (critical for Korean compound words)
            if is_isolated(text, start_index, end_pos):
                results.append({
                    "term": original_term,
                    "start": start_index,
                    "end": end_pos,
                    "node_id": node_id,
                    "tag": tag,
                    "entity_name": original_term,
                })

        return results

    # =========================================================================
    # N-gram Fallback (Tier 5)
    # =========================================================================

    def _ngram_search(
        self, query: str, top_k: int, threshold: float, n: int = 3
    ) -> List[Dict[str, Any]]:
        """Jaccard trigram search. Same logic as TMSearcher._ngram_search.

        Adapted result schema: entity_name, entity_desc, node_id, tag.
        """
        if not query or len(query) < n:
            return []

        query_ngrams = self._get_ngrams(query, n)
        if not query_ngrams:
            return []

        scores = []
        for normalized_text, match in self.whole_lookup.items():
            if not normalized_text or len(normalized_text) < n:
                continue

            candidate_ngrams = self._get_ngrams(normalized_text, n)
            if not candidate_ngrams:
                continue

            intersection = len(query_ngrams & candidate_ngrams)
            union = len(query_ngrams | candidate_ngrams)
            score = intersection / union if union > 0 else 0

            if score >= threshold:
                scores.append((score, match))

        scores.sort(key=lambda x: x[0], reverse=True)

        results = []
        for score, match in scores[:top_k]:
            results.append({
                "entity_name": match["entity_name"],
                "entity_desc": match.get("entity_desc", ""),
                "node_id": match["node_id"],
                "tag": match["tag"],
                "file_path": match.get("file_path", ""),
                "score": score,
                "match_type": "ngram",
            })

        return results

    def _get_ngrams(self, text: str, n: int) -> set:
        """Generate character n-grams from text."""
        if len(text) < n:
            return set()
        return set(text[i : i + n] for i in range(len(text) - n + 1))

    # =========================================================================
    # Helpers
    # =========================================================================

    @staticmethod
    def _format_whole_result(
        match: Dict[str, Any], match_type: str, score: float = 1.0
    ) -> Dict[str, Any]:
        """Format a whole_lookup/mapping match into result dict."""
        return {
            "entity_name": match["entity_name"],
            "entity_desc": match.get("entity_desc", ""),
            "node_id": match["node_id"],
            "tag": match["tag"],
            "file_path": match.get("file_path", ""),
            "score": score,
            "match_type": match_type,
        }

    def search_batch(
        self, queries: List[str], top_k: int = 5, threshold: float = None
    ) -> List[Dict[str, Any]]:
        """Batch search for multiple queries."""
        return [self.search(q, top_k, threshold) for q in queries]
