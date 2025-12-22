"""
TM Searcher - 5-Tier Cascade Search.

Extracted from tm_indexer.py during P37 refactoring.
"""

import numpy as np
from typing import List, Dict, Any, Optional

from loguru import logger

try:
    import faiss
    MODELS_AVAILABLE = True
except ImportError:
    MODELS_AVAILABLE = False

from server.tools.shared import get_embedding_engine, get_current_engine_name
from .utils import normalize_for_hash, normalize_for_embedding

# Default threshold for TM matching (92%)
DEFAULT_THRESHOLD = 0.92

# NPC threshold for Target verification (65%)
NPC_THRESHOLD = 0.65


class TMSearcher:
    """
    5-Tier Cascade TM Search.

    Tier 1: Perfect whole match (hash) -> Show if exists
    Tier 2: Whole embedding match (FAISS) -> Top 3 >=92%
    Tier 3: Perfect line match (hash) -> Show if exists
    Tier 4: Line embedding match (FAISS) -> Top 3 >=92%
    Tier 5: N-gram fallback -> Top 3 >=92%

    Usage:
        searcher = TMSearcher(indexes)
        results = searcher.search("query text")
    """

    def __init__(
        self,
        indexes: Dict[str, Any],
        model=None,
        threshold: float = DEFAULT_THRESHOLD
    ):
        """
        Initialize TMSearcher with loaded indexes.

        Args:
            indexes: Dict from TMIndexer.load_indexes()
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

    def _ensure_model_loaded(self):
        """Load embedding engine if not already loaded."""
        if self._engine is None or not self._engine.is_loaded:
            if not MODELS_AVAILABLE:
                raise RuntimeError("faiss not available")
            engine_name = get_current_engine_name()
            logger.info(f"Loading embedding engine: {engine_name}")
            self._engine = get_embedding_engine(engine_name)
            self._engine.load()
            logger.success(f"Embedding engine loaded: {self._engine.name}")

    @property
    def model(self):
        """Backward compatibility: return engine for code that uses self.model.encode()."""
        self._ensure_model_loaded()
        return self._engine

    def search(
        self,
        query: str,
        top_k: int = 3,
        threshold: float = None
    ) -> Dict[str, Any]:
        """
        Perform 5-Tier Cascade search.

        Args:
            query: Source text to search
            top_k: Max results for embedding tiers (default 3)
            threshold: Override default threshold

        Returns:
            Dict with tier, tier_name, results, perfect_match
        """
        if not query:
            return {"tier": 0, "tier_name": "empty", "results": [], "perfect_match": False}

        threshold = threshold or self.threshold
        query_normalized = normalize_for_hash(query)
        query_for_embedding = normalize_for_embedding(query)

        # TIER 1: Perfect Whole Match (Hash Lookup)
        if query_normalized in self.whole_lookup:
            match = self.whole_lookup[query_normalized]

            if "variations" in match:
                results = [{
                    "entry_id": var["entry_id"],
                    "source_text": var["source_text"],
                    "target_text": var["target_text"],
                    "string_id": var.get("string_id"),
                    "score": 1.0,
                    "match_type": "perfect_whole"
                } for var in match["variations"]]
            else:
                results = [{
                    "entry_id": match["entry_id"],
                    "source_text": match["source_text"],
                    "target_text": match["target_text"],
                    "string_id": match.get("string_id"),
                    "score": 1.0,
                    "match_type": "perfect_whole"
                }]

            return {"tier": 1, "tier_name": "perfect_whole", "perfect_match": True, "results": results}

        # TIER 2: Whole Embedding Match (FAISS)
        if self.whole_index and self.whole_mapping:
            self._ensure_model_loaded()

            query_embedding = self.model.encode([query_for_embedding], normalize=True, show_progress=False)
            query_embedding = np.array(query_embedding, dtype=np.float32)

            scores, indices = self.whole_index.search(query_embedding, min(top_k * 2, 20))

            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx < 0 or idx >= len(self.whole_mapping):
                    continue
                if score < threshold:
                    continue

                match = self.whole_mapping[idx]
                results.append({
                    "entry_id": match["entry_id"],
                    "source_text": match["source_text"],
                    "target_text": match["target_text"],
                    "string_id": match.get("string_id"),
                    "score": float(score),
                    "match_type": "whole_embedding"
                })

                if len(results) >= top_k:
                    break

            if results:
                return {"tier": 2, "tier_name": "whole_embedding", "perfect_match": False, "results": results}

        # TIER 3: Perfect Line Match (Hash Lookup)
        query_lines = query.split('\n')
        line_matches = []

        for i, line in enumerate(query_lines):
            line_normalized = normalize_for_hash(line)
            if not line_normalized:
                continue

            if line_normalized in self.line_lookup:
                match = self.line_lookup[line_normalized]
                line_matches.append({
                    "entry_id": match["entry_id"],
                    "source_line": match["source_line"],
                    "target_line": match["target_line"],
                    "string_id": match.get("string_id"),
                    "query_line_num": i,
                    "tm_line_num": match["line_num"],
                    "score": 1.0,
                    "match_type": "perfect_line"
                })

        if line_matches:
            return {"tier": 3, "tier_name": "perfect_line", "perfect_match": True, "results": line_matches}

        # TIER 4: Line Embedding Match (FAISS)
        if self.line_index and self.line_mapping and query_lines:
            self._ensure_model_loaded()

            line_results = []
            for i, line in enumerate(query_lines):
                line_for_embedding = normalize_for_embedding(line)
                if not line_for_embedding or len(line_for_embedding) < 3:
                    continue

                line_embedding = self.model.encode([line_for_embedding], normalize=True, show_progress=False)
                line_embedding = np.array(line_embedding, dtype=np.float32)

                scores, indices = self.line_index.search(line_embedding, min(top_k * 2, 20))

                for score, idx in zip(scores[0], indices[0]):
                    if idx < 0 or idx >= len(self.line_mapping):
                        continue
                    if score < threshold:
                        continue

                    match = self.line_mapping[idx]
                    line_results.append({
                        "entry_id": match["entry_id"],
                        "source_line": match["source_line"],
                        "target_line": match["target_line"],
                        "string_id": match.get("string_id"),
                        "query_line_num": i,
                        "tm_line_num": match["line_num"],
                        "score": float(score),
                        "match_type": "line_embedding"
                    })
                    break

            if line_results:
                line_results.sort(key=lambda x: x["score"], reverse=True)
                return {"tier": 4, "tier_name": "line_embedding", "perfect_match": False, "results": line_results[:top_k]}

        # TIER 5: N-gram Fallback
        results = self._ngram_search(query_normalized, top_k, threshold)
        if results:
            return {"tier": 5, "tier_name": "ngram_fallback", "perfect_match": False, "results": results}

        return {"tier": 0, "tier_name": "no_match", "perfect_match": False, "results": []}

    def _ngram_search(self, query: str, top_k: int, threshold: float, n: int = 3) -> List[Dict]:
        """N-gram based fallback search for Tier 5."""
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
                "entry_id": match["entry_id"],
                "source_text": match["source_text"],
                "target_text": match["target_text"],
                "score": score,
                "match_type": "ngram"
            })

        return results

    def _get_ngrams(self, text: str, n: int) -> set:
        """Generate character n-grams from text."""
        if len(text) < n:
            return set()
        return set(text[i:i+n] for i in range(len(text) - n + 1))

    def search_batch(self, queries: List[str], top_k: int = 3, threshold: float = None) -> List[Dict[str, Any]]:
        """Batch search for multiple queries."""
        return [self.search(q, top_k, threshold) for q in queries]

    def npc_check(
        self,
        user_target: str,
        tm_matches: List[Dict],
        threshold: float = None
    ) -> Dict[str, Any]:
        """
        NPC (Neil's Probabilistic Check) - Verify translation consistency.

        Checks if user's Target translation is consistent with TM Targets.
        """
        if not user_target or not tm_matches:
            return {
                "consistent": False, "best_match": None, "best_score": 0.0,
                "all_scores": [], "warning": "No target text or TM matches to check"
            }

        threshold = threshold or NPC_THRESHOLD
        user_target_normalized = normalize_for_embedding(user_target)

        if not user_target_normalized:
            return {
                "consistent": False, "best_match": None, "best_score": 0.0,
                "all_scores": [], "warning": "Empty target text after normalization"
            }

        self._ensure_model_loaded()

        user_embedding = self.model.encode([user_target_normalized], normalize=True, show_progress=False)
        user_embedding = np.array(user_embedding, dtype=np.float32)

        tm_targets = []
        for match in tm_matches:
            target = match.get("target_text") or match.get("target_line", "")
            if target:
                tm_targets.append((match, target))

        if not tm_targets:
            return {
                "consistent": False, "best_match": None, "best_score": 0.0,
                "all_scores": [], "warning": "No TM targets to compare against"
            }

        tm_target_texts = [normalize_for_embedding(t[1]) for t in tm_targets]
        tm_target_texts = [t if t else " " for t in tm_target_texts]

        tm_embeddings = self.model.encode(tm_target_texts, normalize=True, show_progress=False)
        tm_embeddings = np.array(tm_embeddings, dtype=np.float32)

        similarities = np.dot(tm_embeddings, user_embedding.T).flatten()

        best_idx = int(np.argmax(similarities))
        best_score = float(similarities[best_idx])
        best_match = tm_targets[best_idx][0]

        all_scores = [
            {"tm_target": tm_targets[i][1], "score": float(similarities[i]), "entry_id": tm_targets[i][0].get("entry_id")}
            for i in range(len(similarities))
        ]
        all_scores.sort(key=lambda x: x["score"], reverse=True)

        consistent = best_score >= threshold

        result = {
            "consistent": consistent, "best_match": best_match,
            "best_score": best_score, "all_scores": all_scores, "threshold": threshold
        }

        if not consistent:
            result["warning"] = f"Target translation may be inconsistent. Best TM match similarity: {best_score:.1%} (threshold: {threshold:.0%})"
        else:
            result["message"] = f"Translation consistent with TM. Best match: {best_score:.1%} similarity"

        return result

    def search_with_npc(
        self,
        source: str,
        user_target: str,
        top_k: int = 3,
        search_threshold: float = None,
        npc_threshold: float = None
    ) -> Dict[str, Any]:
        """Combined search + NPC check in one call."""
        search_result = self.search(source, top_k, search_threshold)

        if search_result["results"]:
            npc_result = self.npc_check(user_target, search_result["results"], npc_threshold)
        else:
            npc_result = {
                "consistent": None, "best_match": None, "best_score": 0.0,
                "all_scores": [], "message": "No TM matches found for NPC verification"
            }

        return {"search": search_result, "npc": npc_result}
