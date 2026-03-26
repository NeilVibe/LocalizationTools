"""
AC Context Searcher - 3-Tier Cascade for Korean TM text.

Provides context-aware TM suggestions when a translator selects a row.
Uses Aho-Corasick for fast substring matching and character n-gram Jaccard
for fuzzy matching of Korean text.

Tier 1: Whole AC match -- source contains a whole TM entry as substring
Tier 2: Line AC match -- source contains a line TM entry as substring
Tier 3: Char n-gram Jaccard fuzzy -- n={2,3,4,5}, space-stripped Korean, >= 62%

Usage:
    from server.tools.ldm.indexing.context_searcher import ContextSearcher

    searcher = ContextSearcher(indexes)  # indexes from TMIndexer.load_indexes()
    result = searcher.search("source text to find context for")
"""

from typing import Dict, Any, Set, Tuple

from loguru import logger

from .utils import normalize_for_hash


class ContextSearcher:
    """3-Tier AC Context Search for Korean TM text.

    Constructor takes indexes dict from TMIndexer.load_indexes() (which includes
    whole_automaton and line_automaton built by _build_ac_automatons).
    """

    CONTEXT_THRESHOLD = 0.62  # 62% Jaccard threshold for fuzzy tier

    def __init__(self, indexes: Dict[str, Any]):
        self.whole_automaton = indexes.get("whole_automaton")
        self.line_automaton = indexes.get("line_automaton")
        self.whole_lookup = indexes.get("whole_lookup", {})
        self.line_lookup = indexes.get("line_lookup", {})

    def search(self, source_text: str, max_results: int = 10) -> Dict[str, Any]:
        """Run 3-tier cascade on source_text.

        Returns:
            Dict with keys: results (list), tier_counts (dict), total (int)
        """
        if not source_text or not source_text.strip():
            return {
                "results": [],
                "tier_counts": {"whole": 0, "line": 0, "fuzzy": 0},
                "total": 0,
            }

        normalized = normalize_for_hash(source_text)
        seen_entry_ids: set = set()

        # Tier 1: Whole AC scan
        whole_results = self._tier1_whole_ac(normalized, seen_entry_ids)

        # Tier 2: Line AC scan
        line_results = self._tier2_line_ac(normalized, seen_entry_ids)

        # Tier 3: Fuzzy n-gram Jaccard
        fuzzy_results = self._tier3_fuzzy_jaccard(normalized, seen_entry_ids)

        # Combine: tier-1 first, tier-2 next, tier-3 last
        # Within each tier, already sorted by score desc
        all_results = whole_results + line_results + fuzzy_results

        # Apply max_results limit
        all_results = all_results[:max_results]

        return {
            "results": all_results,
            "tier_counts": {
                "whole": len(whole_results),
                "line": len(line_results),
                "fuzzy": len(fuzzy_results),
            },
            "total": len(all_results),
        }

    # =========================================================================
    # Tier 1: Whole AC Match
    # =========================================================================

    def _tier1_whole_ac(self, normalized: str, seen_entry_ids: set) -> list:
        """Scan with whole_automaton for substring matches."""
        if not self.whole_automaton:
            return []

        results = []
        for end_idx, (idx, key) in self.whole_automaton.iter(normalized):
            if key not in self.whole_lookup:
                continue

            match = self.whole_lookup[key]
            entries = self._extract_entries_from_match(match)

            for entry in entries:
                eid = entry["entry_id"]
                if eid in seen_entry_ids:
                    continue
                seen_entry_ids.add(eid)
                results.append({
                    "source_text": entry.get("source_text", key),
                    "target_text": entry.get("target_text", ""),
                    "entry_id": eid,
                    "score": 1.0,
                    "tier": "whole",
                    "match_type": "ac_whole",
                })

        # Sort by entry_id for stable ordering (all score=1.0)
        results.sort(key=lambda r: r["entry_id"])
        return results

    # =========================================================================
    # Tier 2: Line AC Match
    # =========================================================================

    def _tier2_line_ac(self, normalized: str, seen_entry_ids: set) -> list:
        """Scan with line_automaton for line substring matches."""
        if not self.line_automaton:
            return []

        results = []
        for end_idx, (idx, key) in self.line_automaton.iter(normalized):
            if key not in self.line_lookup:
                continue

            match = self.line_lookup[key]
            eid = match["entry_id"]
            if eid in seen_entry_ids:
                continue
            seen_entry_ids.add(eid)

            results.append({
                "source_text": match.get("source_line", key),
                "target_text": match.get("target_line", ""),
                "entry_id": eid,
                "score": 1.0,
                "tier": "line",
                "match_type": "ac_line",
            })

        results.sort(key=lambda r: r["entry_id"])
        return results

    # =========================================================================
    # Tier 3: Fuzzy Character N-gram Jaccard
    # =========================================================================

    def _tier3_fuzzy_jaccard(self, normalized: str, seen_entry_ids: set) -> list:
        """Fuzzy match via multi-n-gram Jaccard similarity."""
        if not self.whole_lookup:
            return []

        source_stripped = normalized.replace(" ", "")
        if len(source_stripped) < 2:
            return []

        source_ngrams = self._get_multi_ngrams(source_stripped)
        if not source_ngrams:
            return []

        results = []
        for key, match in self.whole_lookup.items():
            entries = self._extract_entries_from_match(match)

            # Skip if all entries already seen
            unseen_entries = [e for e in entries if e["entry_id"] not in seen_entry_ids]
            if not unseen_entries:
                continue

            key_stripped = key.replace(" ", "")
            if len(key_stripped) < 2:
                continue

            key_ngrams = self._get_multi_ngrams(key_stripped)
            if not key_ngrams:
                continue

            score = self._jaccard_similarity(source_ngrams, key_ngrams)

            if score >= self.CONTEXT_THRESHOLD:
                for entry in unseen_entries:
                    seen_entry_ids.add(entry["entry_id"])
                    results.append({
                        "source_text": entry.get("source_text", key),
                        "target_text": entry.get("target_text", ""),
                        "entry_id": entry["entry_id"],
                        "score": round(score, 4),
                        "tier": "fuzzy",
                        "match_type": "ngram_jaccard",
                    })

        # Sort by score descending
        results.sort(key=lambda r: r["score"], reverse=True)
        return results

    # =========================================================================
    # Helpers
    # =========================================================================

    def _extract_entries_from_match(self, match: dict) -> list:
        """Extract individual entries from a whole_lookup match.

        Handles both single-entry and variations-based matches.
        """
        if "variations" in match:
            return match["variations"]
        return [match]

    def _get_multi_ngrams(self, text: str, ns: Tuple[int, ...] = (2, 3, 4, 5)) -> Set[str]:
        """Generate union of character n-grams for each n value.

        Args:
            text: Input text (should be space-stripped for Korean)
            ns: Tuple of n values for n-gram extraction

        Returns:
            Set of all n-grams across all n values
        """
        result: set = set()
        for n in ns:
            if len(text) >= n:
                for i in range(len(text) - n + 1):
                    result.add(text[i:i + n])
        return result

    @staticmethod
    def _jaccard_similarity(set_a: set, set_b: set) -> float:
        """Compute Jaccard similarity: |intersection| / |union|."""
        if not set_a or not set_b:
            return 0.0
        intersection = len(set_a & set_b)
        union = len(set_a | set_b)
        return intersection / union if union > 0 else 0.0
