"""
Translator Merge Service -- merge corrections into target rows.

Ported from QuickTranslate core/xml_transfer.py merge logic.

Match modes (strict priority order in cascade):
1. strict       -- StringID + StrOrigin both match
2. stringid_only -- StringID matches, StrOrigin may differ
3. strorigin_only -- StrOrigin matches, StringID may differ
4. fuzzy         -- Model2Vec similarity above threshold

Skip guards (applied to source corrections):
1. Korean text   -- target is Korean (untranslated)
2. No translation -- target is "no translation"
3. Formula       -- target starts with =, +, @
4. Text integrity -- broken linebreaks, encoding artifacts (via is_formula_text)
5. Empty source  -- source (StrOrigin) is empty
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from loguru import logger

from server.tools.ldm.services.korean_detection import is_korean_text
from server.tools.ldm.services.postprocess import postprocess_rows
from server.tools.ldm.services.text_matching import (
    is_formula_text,
    normalize_for_matching,
    normalize_nospace,
    normalize_text_for_match,
)
from server.tools.shared.embedding_engine import get_embedding_engine

# "No translation" pattern (whitespace-collapsed, case-insensitive)
_WS_RE = re.compile(r"\s+")


def _is_no_translation(value: str) -> bool:
    """Return True if value is exactly 'no translation' (case-insensitive)."""
    if not value:
        return False
    return _WS_RE.sub(" ", value.strip()).lower() == "no translation"


@dataclass
class MergeResult:
    """Result of a merge operation."""

    matched: int = 0
    skipped: int = 0
    total: int = 0
    match_type_counts: dict = field(default_factory=lambda: {
        "strict": 0,
        "stringid_only": 0,
        "strorigin_only": 0,
        "fuzzy": 0,
    })
    updated_rows: list[dict] = field(default_factory=list)


class TranslatorMergeService:
    """Merge corrections from source rows into target rows.

    Ported from QuickTranslate's xml_transfer.py merge engine.
    """

    # -----------------------------------------------------------------
    # Skip guards -- filter source rows into valid corrections
    # -----------------------------------------------------------------

    def parse_corrections(self, source_rows: list[dict]) -> list[dict]:
        """Extract valid corrections from source rows, applying all 5 skip guards.

        Guards (order matters):
          1. Empty target (no correction value)
          2. Empty source / StrOrigin (golden rule)
          3. Korean target text (untranslated)
          4. "no translation" target
          5. Formula / garbage target

        Returns list of correction dicts with keys:
          string_id, str_origin, corrected
        """
        corrections: list[dict] = []

        for row in source_rows:
            target = (row.get("target") or "").strip()
            source = (row.get("source") or "").strip()
            string_id = (row.get("string_id") or "").strip()

            # Guard 1: empty target -- nothing to transfer
            if not target:
                continue

            # Guard 2: empty source (golden rule)
            if not source:
                continue

            # Guard 3: Korean target text (untranslated)
            if is_korean_text(target):
                logger.debug("Skip Korean target: StringID=%s", string_id)
                continue

            # Guard 4: "no translation"
            if _is_no_translation(target):
                logger.debug("Skip 'no translation': StringID=%s", string_id)
                continue

            # Guard 5: formula / garbage
            if is_formula_text(target):
                logger.debug("Skip formula target: StringID=%s", string_id)
                continue

            corrections.append({
                "string_id": string_id,
                "str_origin": source,
                "corrected": target,
            })

        return corrections

    # -----------------------------------------------------------------
    # Lookup building -- one per match mode
    # -----------------------------------------------------------------

    def _build_lookups(
        self,
        corrections: list[dict],
        match_mode: str,
    ) -> tuple[dict, Optional[dict]]:
        """Build lookup dicts for the given match mode.

        Returns (lookup, lookup_nospace) tuple.
        Ported from QuickTranslate _build_correction_lookups().
        """
        if match_mode == "strict":
            # Key: (string_id_lower, normalized_strorigin)
            lookup: dict = defaultdict(list)
            lookup_ns: dict = defaultdict(list)
            for i, c in enumerate(corrections):
                sid = c["string_id"].lower()
                origin = normalize_text_for_match(c.get("str_origin", ""))
                origin_ns = normalize_nospace(origin)
                lookup[(sid, origin)].append((c["corrected"], i))
                lookup_ns[(sid, origin_ns)].append((c["corrected"], i))
            return dict(lookup), dict(lookup_ns)

        if match_mode == "stringid_only":
            lookup = {}
            for c in corrections:
                sid = c["string_id"].lower()
                lookup[sid] = c
            return lookup, None

        if match_mode == "strorigin_only":
            lookup = {}
            lookup_ns = {}
            for c in corrections:
                origin = normalize_for_matching(c.get("str_origin", ""))
                if not origin:
                    continue
                origin_ns = normalize_nospace(origin)
                lookup[origin] = c
                lookup_ns[origin_ns] = c
            return lookup, lookup_ns

        return {}, None

    # -----------------------------------------------------------------
    # Per-row matching
    # -----------------------------------------------------------------

    def _find_strict_match(
        self,
        target_row: dict,
        lookup: dict,
        lookup_ns: Optional[dict],
    ) -> Optional[str]:
        """Try strict match: StringID + StrOrigin."""
        sid = (target_row.get("string_id") or "").lower()
        source = normalize_text_for_match(target_row.get("source", ""))
        key = (sid, source)
        entries = lookup.get(key)
        if entries:
            return entries[0][0]  # corrected text
        # Fallback: nospace
        if lookup_ns:
            key_ns = (sid, normalize_nospace(source))
            entries = lookup_ns.get(key_ns)
            if entries:
                return entries[0][0]
        return None

    def _find_stringid_match(
        self,
        target_row: dict,
        lookup: dict,
    ) -> Optional[str]:
        """Try StringID-only match."""
        sid = (target_row.get("string_id") or "").lower()
        c = lookup.get(sid)
        if c:
            return c["corrected"]
        return None

    def _find_strorigin_match(
        self,
        target_row: dict,
        lookup: dict,
        lookup_ns: Optional[dict],
    ) -> Optional[str]:
        """Try StrOrigin-only match."""
        source = normalize_for_matching(target_row.get("source", ""))
        c = lookup.get(source)
        if c:
            return c["corrected"]
        # Fallback: nospace
        if lookup_ns:
            source_ns = normalize_nospace(source)
            c = lookup_ns.get(source_ns)
            if c:
                return c["corrected"]
        return None

    # -----------------------------------------------------------------
    # Fuzzy matching via Model2Vec + FAISS
    # -----------------------------------------------------------------

    def _apply_fuzzy_matches(
        self,
        unmatched_targets: list[dict],
        corrections: list[dict],
        threshold: float = 0.85,
    ) -> list[tuple[dict, str]]:
        """Find fuzzy matches using embedding similarity.

        Returns list of (target_row, corrected_text) tuples.
        """
        if not unmatched_targets or not corrections:
            return []

        try:
            import faiss
        except ImportError:
            logger.warning("faiss not installed -- fuzzy matching disabled")
            return []

        engine = get_embedding_engine()

        # Encode correction source texts
        correction_sources = [c.get("str_origin", "") for c in corrections]
        target_sources = [t.get("source", "") for t in unmatched_targets]

        corr_embeddings = engine.encode(correction_sources, normalize=True)
        target_embeddings = engine.encode(target_sources, normalize=True)

        # Build FAISS index (cosine similarity via inner product on normalized vectors)
        dim = corr_embeddings.shape[1]
        index = faiss.IndexFlatIP(dim)
        index.add(corr_embeddings.astype(np.float32))

        # Search
        scores, indices = index.search(
            target_embeddings.astype(np.float32), 1
        )

        matches: list[tuple[dict, str]] = []
        for i, (score_arr, idx_arr) in enumerate(zip(scores, indices)):
            score = float(score_arr[0])
            idx = int(idx_arr[0])
            if score >= threshold and idx >= 0:
                matches.append((unmatched_targets[i], corrections[idx]["corrected"]))

        return matches

    # -----------------------------------------------------------------
    # Main entry point
    # -----------------------------------------------------------------

    def merge_files(
        self,
        source_rows: list[dict],
        target_rows: list[dict],
        match_mode: str = "cascade",
        threshold: float = 0.85,
        is_cjk: bool = False,
    ) -> MergeResult:
        """Merge corrections from source into target rows.

        Args:
            source_rows: Rows containing corrections (from source file).
            target_rows: Rows to merge into (from target file).
            match_mode: One of "strict", "stringid_only", "strorigin_only",
                        "fuzzy", or "cascade" (default).
            threshold: Fuzzy match similarity threshold (0.0 - 1.0).
            is_cjk: CJK language flag for postprocess pipeline.

        Returns:
            MergeResult with matched/skipped counts and updated rows.
        """
        result = MergeResult(total=len(target_rows))

        # Step 1: Parse corrections (apply skip guards)
        corrections = self.parse_corrections(source_rows)
        result.skipped = len(source_rows) - len(corrections)

        if not corrections:
            return result

        # Step 2: Match based on mode
        if match_mode == "cascade":
            self._merge_cascade(target_rows, corrections, threshold, result)
        elif match_mode == "strict":
            self._merge_single_mode(target_rows, corrections, "strict", result)
        elif match_mode == "stringid_only":
            self._merge_single_mode(target_rows, corrections, "stringid_only", result)
        elif match_mode == "strorigin_only":
            self._merge_single_mode(target_rows, corrections, "strorigin_only", result)
        elif match_mode == "fuzzy":
            self._merge_fuzzy_only(target_rows, corrections, threshold, result)
        else:
            logger.warning("Unknown match_mode=%s, defaulting to cascade", match_mode)
            self._merge_cascade(target_rows, corrections, threshold, result)

        # Step 3: Postprocess all updated rows
        if result.updated_rows:
            result.updated_rows, _stats = postprocess_rows(
                result.updated_rows, is_cjk=is_cjk
            )

        return result

    def _merge_single_mode(
        self,
        target_rows: list[dict],
        corrections: list[dict],
        mode: str,
        result: MergeResult,
    ) -> None:
        """Run a single match mode on all target rows."""
        lookup, lookup_ns = self._build_lookups(corrections, mode)

        for target in target_rows:
            matched_text: Optional[str] = None

            if mode == "strict":
                matched_text = self._find_strict_match(target, lookup, lookup_ns)
            elif mode == "stringid_only":
                matched_text = self._find_stringid_match(target, lookup)
            elif mode == "strorigin_only":
                matched_text = self._find_strorigin_match(target, lookup, lookup_ns)

            if matched_text is not None:
                updated = dict(target)
                updated["target"] = matched_text
                result.updated_rows.append(updated)
                result.matched += 1
                result.match_type_counts[mode] += 1

    def _merge_cascade(
        self,
        target_rows: list[dict],
        corrections: list[dict],
        threshold: float,
        result: MergeResult,
    ) -> None:
        """Cascade: strict > stringid_only > strorigin_only > fuzzy. First match wins."""
        strict_lookup, strict_ns = self._build_lookups(corrections, "strict")
        stringid_lookup, _ = self._build_lookups(corrections, "stringid_only")
        strorigin_lookup, strorigin_ns = self._build_lookups(corrections, "strorigin_only")

        unmatched: list[dict] = []

        for target in target_rows:
            # Try strict first
            matched_text = self._find_strict_match(target, strict_lookup, strict_ns)
            if matched_text is not None:
                updated = dict(target)
                updated["target"] = matched_text
                result.updated_rows.append(updated)
                result.matched += 1
                result.match_type_counts["strict"] += 1
                continue

            # Try stringid_only
            matched_text = self._find_stringid_match(target, stringid_lookup)
            if matched_text is not None:
                updated = dict(target)
                updated["target"] = matched_text
                result.updated_rows.append(updated)
                result.matched += 1
                result.match_type_counts["stringid_only"] += 1
                continue

            # Try strorigin_only
            matched_text = self._find_strorigin_match(
                target, strorigin_lookup, strorigin_ns
            )
            if matched_text is not None:
                updated = dict(target)
                updated["target"] = matched_text
                result.updated_rows.append(updated)
                result.matched += 1
                result.match_type_counts["strorigin_only"] += 1
                continue

            # Collect for fuzzy
            unmatched.append(target)

        # Fuzzy pass on remaining unmatched
        if unmatched:
            fuzzy_matches = self._apply_fuzzy_matches(
                unmatched, corrections, threshold
            )
            for target, corrected in fuzzy_matches:
                updated = dict(target)
                updated["target"] = corrected
                result.updated_rows.append(updated)
                result.matched += 1
                result.match_type_counts["fuzzy"] += 1

    def _merge_fuzzy_only(
        self,
        target_rows: list[dict],
        corrections: list[dict],
        threshold: float,
        result: MergeResult,
    ) -> None:
        """Fuzzy-only mode."""
        fuzzy_matches = self._apply_fuzzy_matches(
            target_rows, corrections, threshold
        )
        for target, corrected in fuzzy_matches:
            updated = dict(target)
            updated["target"] = corrected
            result.updated_rows.append(updated)
            result.matched += 1
            result.match_type_counts["fuzzy"] += 1
