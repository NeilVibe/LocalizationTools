"""
Tests for TranslatorMergeService -- merge engine with 4 match modes + skip guards.

Ported from QuickTranslate's xml_transfer.py logic.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from server.tools.ldm.services.translator_merge import (
    MergeResult,
    TranslatorMergeService,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _row(string_id: str, source: str, target: str = "") -> dict:
    """Build a row dict matching the DB schema."""
    return {
        "id": hash(string_id) % 10000,
        "file_id": 1,
        "string_id": string_id,
        "source": source,
        "target": target,
        "status": "pending",
    }


def _source_row(string_id: str, source: str, target: str) -> dict:
    """Build a source (correction) row."""
    return _row(string_id, source, target)


# ---------------------------------------------------------------------------
# Skip guard tests
# ---------------------------------------------------------------------------


class TestSkipGuards:
    """All 5 skip guards prevent bad corrections from entering the merge."""

    def test_skip_korean(self):
        """Source row where target is Korean text -> skipped."""
        svc = TranslatorMergeService()
        corrections = svc.parse_corrections([
            _source_row("UI_KR", "건너뛰기", "건너뛰기 처리"),
        ])
        assert len(corrections) == 0

    def test_skip_no_translation(self):
        """Source row where target is 'no translation' -> skipped."""
        svc = TranslatorMergeService()
        corrections = svc.parse_corrections([
            _source_row("UI_NT", "번역없음", "no translation"),
            _source_row("UI_NT2", "번역없음", "No  Translation"),
        ])
        assert len(corrections) == 0

    def test_skip_formula(self):
        """Source row where target starts with = -> skipped."""
        svc = TranslatorMergeService()
        corrections = svc.parse_corrections([
            _source_row("UI_F", "공식", "=SUM(A1:B2)"),
        ])
        assert len(corrections) == 0

    def test_skip_empty_source(self):
        """Source row where source is empty -> skipped (golden rule)."""
        svc = TranslatorMergeService()
        corrections = svc.parse_corrections([
            _source_row("UI_E", "", "SomeValue"),
        ])
        assert len(corrections) == 0

    def test_skip_empty_target(self):
        """Source row where target is empty -> skipped (no correction)."""
        svc = TranslatorMergeService()
        corrections = svc.parse_corrections([
            _source_row("UI_ET", "원본", ""),
        ])
        assert len(corrections) == 0

    def test_valid_correction_passes(self):
        """A normal correction passes all guards."""
        svc = TranslatorMergeService()
        corrections = svc.parse_corrections([
            _source_row("UI_OK", "확인", "OK"),
        ])
        assert len(corrections) == 1
        assert corrections[0]["string_id"] == "UI_OK"
        assert corrections[0]["corrected"] == "OK"


# ---------------------------------------------------------------------------
# Match mode tests
# ---------------------------------------------------------------------------


class TestStrictMatch:
    """Strict mode: StringID + StrOrigin both must match."""

    def test_strict_match(self):
        """Source row matches target with same StringID AND source."""
        svc = TranslatorMergeService()
        source_rows = [_source_row("UI_OK", "확인", "OK")]
        target_rows = [_row("UI_OK", "확인")]

        result = svc.merge_files(source_rows, target_rows, match_mode="strict")

        assert isinstance(result, MergeResult)
        assert result.matched == 1
        assert len(result.updated_rows) == 1
        assert result.updated_rows[0]["target"] == "OK"

    def test_strict_no_match_different_source(self):
        """Strict mode does NOT match when StrOrigin differs."""
        svc = TranslatorMergeService()
        source_rows = [_source_row("UI_OK", "확인 버튼", "OK Button")]
        target_rows = [_row("UI_OK", "확인")]

        result = svc.merge_files(source_rows, target_rows, match_mode="strict")

        assert result.matched == 0


class TestStringIdOnlyMatch:
    """StringID-only mode: matches on StringID regardless of StrOrigin."""

    def test_stringid_only_match(self):
        """Source row matches target with same StringID but different source."""
        svc = TranslatorMergeService()
        source_rows = [_source_row("UI_OK", "확인 버튼", "OK Button")]
        target_rows = [_row("UI_OK", "확인")]

        result = svc.merge_files(source_rows, target_rows, match_mode="stringid_only")

        assert result.matched == 1
        assert result.updated_rows[0]["target"] == "OK Button"


class TestStrOriginMatch:
    """StrOrigin-only mode: matches on source text regardless of StringID."""

    def test_strorigin_match(self):
        """Source row matches target with same source but different StringID."""
        svc = TranslatorMergeService()
        source_rows = [_source_row("NEW_ID", "확인", "OK")]
        target_rows = [_row("OLD_ID", "확인")]

        result = svc.merge_files(source_rows, target_rows, match_mode="strorigin_only")

        assert result.matched == 1
        assert result.updated_rows[0]["target"] == "OK"


class TestFuzzyMatch:
    """Fuzzy mode: uses Model2Vec similarity to find matches."""

    def _mock_engine(self):
        """Create a mock embedding engine that returns predetermined embeddings."""
        engine = MagicMock()
        engine.dimension = 256

        def fake_encode(texts, normalize=True, show_progress=False):
            """Return embeddings that make specific pairs similar."""
            embeddings = []
            for text in texts:
                # Generate deterministic but distinct embeddings
                np.random.seed(hash(text) % 2**31)
                emb = np.random.randn(256).astype(np.float32)
                # Make "게임을 시작합니다" and "게임 시작합니다" very similar
                if "게임" in text and "시작" in text:
                    np.random.seed(42)
                    emb = np.random.randn(256).astype(np.float32)
                    # Add tiny noise for non-identical text
                    if "을 " in text:
                        emb += np.random.randn(256).astype(np.float32) * 0.01
                norm = np.linalg.norm(emb)
                if norm > 0:
                    emb = emb / norm
                embeddings.append(emb)
            return np.array(embeddings, dtype=np.float32)

        engine.encode = fake_encode
        engine.is_loaded = True
        engine.load = MagicMock()
        return engine

    @patch("server.tools.ldm.services.translator_merge.get_embedding_engine")
    def test_fuzzy_match(self, mock_get_engine):
        """Fuzzy match finds similar (not identical) source text above threshold."""
        mock_get_engine.return_value = self._mock_engine()
        svc = TranslatorMergeService()

        source_rows = [_source_row("UI_FUZZY_SRC", "게임을 시작합니다", "Start the Game")]
        target_rows = [_row("UI_FUZZY_TGT", "게임 시작합니다")]

        result = svc.merge_files(source_rows, target_rows, match_mode="fuzzy", threshold=0.85)

        assert result.matched == 1
        assert result.updated_rows[0]["target"] == "Start the Game"
        assert result.match_type_counts.get("fuzzy", 0) >= 1


# ---------------------------------------------------------------------------
# Cascade priority test
# ---------------------------------------------------------------------------


class TestCascadePriority:
    """Cascade mode: strict > strorigin_only > fuzzy. First match wins."""

    def test_priority_strict_wins(self):
        """When both strict and strorigin match the same target, strict result is used."""
        svc = TranslatorMergeService()
        source_rows = [
            _source_row("UI_OK", "확인", "OK Strict"),
            _source_row("OTHER_ID", "확인", "OK StrOrigin"),
        ]
        target_rows = [_row("UI_OK", "확인")]

        result = svc.merge_files(source_rows, target_rows, match_mode="cascade")

        assert result.matched == 1
        assert result.updated_rows[0]["target"] == "OK Strict"
        assert result.match_type_counts.get("strict", 0) == 1

    def test_cascade_falls_through(self):
        """When strict fails, cascade tries strorigin_only."""
        svc = TranslatorMergeService()
        source_rows = [
            _source_row("DIFFERENT_ID", "확인", "OK via StrOrigin"),
        ]
        target_rows = [_row("UI_OK", "확인")]

        result = svc.merge_files(source_rows, target_rows, match_mode="cascade")

        assert result.matched == 1
        assert result.updated_rows[0]["target"] == "OK via StrOrigin"
        assert result.match_type_counts.get("strorigin_only", 0) == 1


# ---------------------------------------------------------------------------
# MergeResult counts
# ---------------------------------------------------------------------------


class TestMergeResultCounts:

    def test_merge_result_counts(self):
        """MergeResult has matched, skipped, total counts."""
        svc = TranslatorMergeService()
        source_rows = [
            _source_row("UI_OK", "확인", "OK"),
            _source_row("UI_KR", "한국어", "한국어 텍스트"),  # Korean target -> skipped
        ]
        target_rows = [
            _row("UI_OK", "확인"),
            _row("UI_UNMATCHED", "일치없음"),
        ]

        result = svc.merge_files(source_rows, target_rows, match_mode="strict")

        assert result.total == 2
        assert result.matched == 1
        assert result.skipped >= 1  # At least the Korean one was skipped


# ---------------------------------------------------------------------------
# Postprocess integration
# ---------------------------------------------------------------------------


class TestPostprocessIntegration:

    def test_postprocess_applied(self):
        """Merged values pass through postprocess pipeline (curly quotes -> ASCII)."""
        svc = TranslatorMergeService()
        # Use a curly apostrophe that postprocess should fix
        source_rows = [_source_row("UI_APOS", "테스트", "it\u2019s working")]
        target_rows = [_row("UI_APOS", "테스트")]

        result = svc.merge_files(source_rows, target_rows, match_mode="strict")

        assert result.matched == 1
        # Curly apostrophe (U+2019) should be normalized to ASCII apostrophe
        assert result.updated_rows[0]["target"] == "it's working"
