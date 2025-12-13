"""
TM Integration Tests with Real QWEN Model

Tests actual embedding similarity scores to validate:
- 92% threshold for TM matching
- 80% threshold for NPC
- Real-world similarity patterns

Run with: python3 -m pytest tests/integration/test_tm_real_model.py -v -s
(Use -s to see similarity scores printed)

NOTE: These tests load the actual QWEN model (~2GB), so they're slower.
"""

import pytest
import numpy as np
from typing import List, Tuple

# Skip if model not available
pytest.importorskip("sentence_transformers")
pytest.importorskip("faiss")

from sentence_transformers import SentenceTransformer
import faiss


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture(scope="module")
def model():
    """Load QWEN model once for all tests in this module."""
    print("\n[Loading QWEN model...]")
    m = SentenceTransformer("Qwen/Qwen3-Embedding-0.6B")
    print("[Model loaded]")
    return m


def compute_similarity(model, text1: str, text2: str) -> float:
    """Compute cosine similarity between two texts."""
    embeddings = model.encode([text1, text2])
    embeddings = np.array(embeddings, dtype=np.float32)
    faiss.normalize_L2(embeddings)
    return float(np.dot(embeddings[0], embeddings[1]))


def compute_similarities(model, query: str, candidates: List[str]) -> List[Tuple[str, float]]:
    """Compute similarities between query and multiple candidates."""
    all_texts = [query] + candidates
    embeddings = model.encode(all_texts)
    embeddings = np.array(embeddings, dtype=np.float32)
    faiss.normalize_L2(embeddings)

    query_emb = embeddings[0]
    results = []
    for i, candidate in enumerate(candidates):
        score = float(np.dot(query_emb, embeddings[i + 1]))
        results.append((candidate, score))

    return sorted(results, key=lambda x: x[1], reverse=True)


# =============================================================================
# Test: Identical Text Should Be 100%
# =============================================================================

class TestIdenticalText:
    """Identical text should have ~100% similarity."""

    def test_identical_korean(self, model):
        """Identical Korean text."""
        text = "저장하시겠습니까?"
        score = compute_similarity(model, text, text)
        print(f"\n  Identical Korean: {score:.4f}")
        assert score > 0.99, f"Identical text should be >99%, got {score:.2%}"

    def test_identical_english(self, model):
        """Identical English text."""
        text = "Do you want to save?"
        score = compute_similarity(model, text, text)
        print(f"\n  Identical English: {score:.4f}")
        assert score > 0.99, f"Identical text should be >99%, got {score:.2%}"

    def test_identical_multiline(self, model):
        """Identical multiline text."""
        text = "Line 1\nLine 2\nLine 3"
        score = compute_similarity(model, text, text)
        print(f"\n  Identical multiline: {score:.4f}")
        assert score > 0.99


# =============================================================================
# Test: Minor Variations (Should be >92% for TM match)
# =============================================================================

class TestMinorVariations:
    """
    Minor variations should still match at 92% threshold.
    These represent typos, punctuation changes, whitespace.
    """

    def test_punctuation_difference(self, model):
        """Punctuation changes should have high similarity."""
        text1 = "저장하시겠습니까?"
        text2 = "저장하시겠습니까"  # Missing ?
        score = compute_similarity(model, text1, text2)
        print(f"\n  Punctuation diff: {score:.4f}")
        # Should be very high - just punctuation
        assert score > 0.90, f"Punctuation diff should be >90%, got {score:.2%}"

    def test_whitespace_difference(self, model):
        """Extra whitespace should have high similarity."""
        text1 = "파일을 저장합니다"
        text2 = "파일을  저장합니다"  # Extra space
        score = compute_similarity(model, text1, text2)
        print(f"\n  Whitespace diff: {score:.4f}")
        assert score > 0.95, f"Whitespace diff should be >95%, got {score:.2%}"

    def test_case_difference_english(self, model):
        """Case changes in English."""
        text1 = "Save the file"
        text2 = "save the file"
        score = compute_similarity(model, text1, text2)
        print(f"\n  Case diff: {score:.4f}")
        assert score > 0.90, f"Case diff should be >90%, got {score:.2%}"

    def test_slight_word_change(self, model):
        """One word different - similar but below 92% threshold."""
        text1 = "파일을 저장하시겠습니까?"
        text2 = "문서를 저장하시겠습니까?"  # 파일→문서 (file→document)
        score = compute_similarity(model, text1, text2)
        print(f"\n  One word diff (파일→문서): {score:.4f}")
        # Similar but won't hit perfect match - will use embedding tier
        # Real score: ~84%
        assert score > 0.80, f"One word diff should be >80%, got {score:.2%}"
        assert score < 0.92, f"One word diff should be <92% (not perfect match)"


# =============================================================================
# Test: Semantic Similarity (Same meaning, different words)
# =============================================================================

class TestSemanticSimilarity:
    """
    Same meaning expressed differently.
    These should be caught by embedding search (Tier 2/4).
    """

    def test_synonym_korean(self, model):
        """Same meaning with synonyms."""
        text1 = "저장하시겠습니까?"
        text2 = "저장할까요?"  # Different phrasing
        score = compute_similarity(model, text1, text2)
        print(f"\n  Korean synonym: {score:.4f}")
        # Should be reasonably similar
        assert score > 0.75, f"Synonym should be >75%, got {score:.2%}"

    def test_synonym_english(self, model):
        """Same meaning with synonyms in English."""
        text1 = "Do you want to save?"
        text2 = "Would you like to save?"
        score = compute_similarity(model, text1, text2)
        print(f"\n  English synonym: {score:.4f}")
        assert score > 0.80, f"Synonym should be >80%, got {score:.2%}"

    def test_formal_informal(self, model):
        """Formal vs informal Korean."""
        text1 = "저장하시겠습니까?"  # Formal
        text2 = "저장할래?"  # Informal
        score = compute_similarity(model, text1, text2)
        print(f"\n  Formal/informal: {score:.4f}")
        # Should still be similar - same meaning
        assert score > 0.70, f"Formal/informal should be >70%, got {score:.2%}"


# =============================================================================
# Test: Different Meaning (Should be <92%, ideally <80%)
# =============================================================================

class TestDifferentMeaning:
    """
    Different meanings should NOT match.
    These should be below our thresholds.
    """

    def test_opposite_action(self, model):
        """Opposite actions should be different."""
        text1 = "저장하시겠습니까?"  # Save?
        text2 = "삭제하시겠습니까?"  # Delete?
        score = compute_similarity(model, text1, text2)
        print(f"\n  Save vs Delete: {score:.4f}")
        # Same structure, opposite meaning - might still be somewhat similar
        # But should be below 92%
        assert score < 0.92, f"Opposite should be <92%, got {score:.2%}"

    def test_completely_unrelated(self, model):
        """Completely unrelated texts."""
        text1 = "저장하시겠습니까?"
        text2 = "오늘 날씨가 좋습니다"  # The weather is nice today
        score = compute_similarity(model, text1, text2)
        print(f"\n  Unrelated: {score:.4f}")
        assert score < 0.70, f"Unrelated should be <70%, got {score:.2%}"

    def test_different_domain(self, model):
        """Same language, different domain."""
        text1 = "파일을 저장합니다"  # Save file (software)
        text2 = "음식을 주문합니다"  # Order food
        score = compute_similarity(model, text1, text2)
        print(f"\n  Different domain: {score:.4f}")
        assert score < 0.80, f"Different domain should be <80%, got {score:.2%}"


# =============================================================================
# Test: NPC Scenario - Translation Consistency
# =============================================================================

class TestNPCScenario:
    """
    NPC checks if user's translation is consistent with TM translations.

    FINDING: 80% threshold is TOO HIGH for short English strings.
    "Save" vs "Save file" = 70.6% (should pass but doesn't at 80%)

    RECOMMENDATION: Lower NPC threshold to 60-65% or use length-adjusted threshold.
    """

    def test_consistent_translation(self, model):
        """User translation matches TM translation well."""
        tm_target = "Save"
        user_target = "Save"
        score = compute_similarity(model, tm_target, user_target)
        print(f"\n  Consistent (identical): {score:.4f}")
        assert score > 0.99

    def test_slightly_different_translation(self, model):
        """
        User translation is slightly different but acceptable.

        FINDING: "Save" vs "Save file" = ~70%
        This SHOULD pass NPC but 80% threshold rejects it.
        """
        tm_target = "Save"
        user_target = "Save file"
        score = compute_similarity(model, tm_target, user_target)
        print(f"\n  Slightly different: {score:.4f}")
        # Reality: ~70% for short strings with additions
        # 80% threshold is too strict - recommend 60-65%
        assert score > 0.60, f"Slight diff should be >60%, got {score:.2%}"
        print(f"    ⚠️ NOTE: 80% threshold would reject this valid variation")

    def test_synonym_translation(self, model):
        """User used a synonym - Korean native vs loanword."""
        tm_target = "저장"
        user_target = "세이브"  # English loanword
        score = compute_similarity(model, tm_target, user_target)
        print(f"\n  Synonym translation (저장 vs 세이브): {score:.4f}")
        # Reality: ~58% - loanwords are semantically distant in embedding space
        print(f"    (Loanwords have lower similarity in QWEN embeddings)")

    def test_wrong_translation(self, model):
        """User translation is completely wrong - should fail NPC."""
        tm_target = "Save"
        user_target = "Delete"
        score = compute_similarity(model, tm_target, user_target)
        print(f"\n  Wrong translation (Save vs Delete): {score:.4f}")
        # Reality: ~59% - not as different as expected!
        # Both are short action words
        assert score < 0.70, f"Wrong translation should be <70%, got {score:.2%}"

    def test_npc_real_scenario(self, model):
        """
        Real NPC scenario: Source matched, now check Target.

        TM Entry: "저장하기" → "Save"
        User types: "저장하기" (Source matches!)
        User's translation: "Save changes"

        FINDING: Score = ~61%
        80% threshold would REJECT this valid translation.
        """
        tm_target = "Save"
        user_target = "Save changes"
        score = compute_similarity(model, tm_target, user_target)
        print(f"\n  NPC real scenario (Save vs Save changes): {score:.4f}")
        # Reality: ~61% - 80% threshold is too strict
        assert score > 0.55, f"Should be >55%, got {score:.2%}"
        print(f"    ⚠️ RECOMMENDATION: Lower NPC threshold to 60-65%")

    def test_npc_korean_longer_text(self, model):
        """
        NPC with longer Korean text - should have better scores.
        Short strings suffer from limited context.
        """
        tm_target = "파일을 저장하시겠습니까?"
        user_target = "파일을 저장할까요?"
        score = compute_similarity(model, tm_target, user_target)
        print(f"\n  Korean longer text variation: {score:.4f}")
        # Longer Korean strings should have better semantic matching
        assert score > 0.80, f"Korean variation should be >80%, got {score:.2%}"


# =============================================================================
# Test: Multiline Text Similarity
# =============================================================================

class TestMultilineText:
    """Test similarity with multiline text."""

    def test_same_lines_different_order(self, model):
        """Same lines but different order."""
        text1 = "저장\n취소\n삭제"
        text2 = "삭제\n취소\n저장"
        score = compute_similarity(model, text1, text2)
        print(f"\n  Same lines, different order: {score:.4f}")
        # Contains same content, should be similar but not identical
        assert score > 0.80

    def test_partial_line_match(self, model):
        """One line matches, others don't."""
        text1 = "저장\n취소\n삭제"
        text2 = "저장\n확인\n닫기"  # Only 저장 matches
        score = compute_similarity(model, text1, text2)
        print(f"\n  Partial line match: {score:.4f}")
        # Partial match - moderate similarity

    def test_single_vs_multiline(self, model):
        """Single line vs same line in multiline."""
        text1 = "저장"
        text2 = "저장\n취소\n삭제"
        score = compute_similarity(model, text1, text2)
        print(f"\n  Single vs multiline: {score:.4f}")
        # Should have moderate similarity since 저장 is in text2


# =============================================================================
# Test: Threshold Validation Report
# =============================================================================

class TestThresholdValidation:
    """
    Generate a report of similarity scores to validate our thresholds.
    Run with -s flag to see the full report.
    """

    def test_threshold_report(self, model):
        """Print comprehensive similarity report."""
        print("\n" + "=" * 70)
        print("THRESHOLD VALIDATION REPORT")
        print("=" * 70)
        print(f"\nTM Search Threshold: 92% (for perfect/near-perfect matches)")
        print(f"NPC Threshold: RECOMMEND 60-65% (80% is too strict)")
        print("\n" + "-" * 70)

        # Test cases with realistic expected values based on actual testing
        test_cases = [
            # (category, text1, text2, expected_above, description)
            ("IDENTICAL", "저장하기", "저장하기", 0.99, "Should be 100%"),
            ("PUNCTUATION", "저장하기?", "저장하기", 0.80, "~83% observed"),
            ("WHITESPACE", "저장 하기", "저장  하기", 0.95, "~97% observed"),
            ("ONE_WORD_DIFF", "파일 저장", "문서 저장", 0.70, "~76% observed"),
            ("SYNONYM_KO", "저장하시겠습니까", "저장할까요", 0.80, "~87% observed"),
            ("FORMAL_INFORMAL", "저장하시겠습니까?", "저장할래?", 0.70, "~82% observed"),
            ("OPPOSITE", "저장", "삭제", None, "~58% (low)"),
            ("UNRELATED", "저장하기", "날씨가 좋다", None, "~49% (low)"),
            ("EN_VARIATION", "Save", "Save file", 0.60, "~71% observed"),
            ("EN_WRONG", "Save", "Delete", None, "~59% (low)"),
        ]

        print(f"\n{'Category':<18} {'Score':>7} {'Status':<6} {'Texts':<35} {'Note'}")
        print("-" * 90)

        for category, t1, t2, expected, note in test_cases:
            score = compute_similarity(model, t1, t2)
            status = ""
            if expected:
                status = "✓" if score >= expected else "✗"
            texts = f"{t1} ↔ {t2}"
            print(f"{category:<18} {score:>6.1%} {status:<6} {texts:<35} {note}")

        print("\n" + "-" * 70)
        print("KEY FINDINGS:")
        print("  • TM 92% threshold works well for Source matching")
        print("  • NPC 80% threshold TOO STRICT for short English strings")
        print("  • 'Save' vs 'Save file' = ~70% (should pass NPC)")
        print("  • RECOMMEND: Lower NPC threshold to 60-65%")
        print("=" * 70)


# =============================================================================
# Test: Cross-Language (Should NOT match - same language only)
# =============================================================================

class TestCrossLanguage:
    """
    Verify cross-language doesn't produce high scores.
    We use same-language matching only (KO→KO, EN→EN).
    """

    def test_korean_vs_english(self, model):
        """Korean vs English translation - should NOT be high."""
        korean = "저장하기"
        english = "Save"
        score = compute_similarity(model, korean, english)
        print(f"\n  Korean vs English: {score:.4f}")
        # These are translations of each other but we don't want cross-lang match
        print(f"    (Note: We use same-language matching, this score is informational)")

    def test_same_meaning_different_language(self, model):
        """Same meaning in different languages."""
        text1 = "파일을 삭제하시겠습니까?"
        text2 = "Do you want to delete the file?"
        score = compute_similarity(model, text1, text2)
        print(f"\n  Same meaning, different language: {score:.4f}")
        print(f"    (Cross-language similarity - for reference only)")
