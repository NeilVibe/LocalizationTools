"""
QWEN Embedding Validation Test Suite

Tests QWEN similarity scores against expected ranges to validate
the embedding model works correctly for pretranslation.

Run with: python3 tests/fixtures/pretranslation/test_qwen_validation.py

This will output a detailed report of actual vs expected scores.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

import numpy as np
from typing import List, Tuple, Dict
from dataclasses import dataclass

# Try to import required libraries
try:
    from sentence_transformers import SentenceTransformer
    import faiss
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Run: pip install sentence-transformers faiss-cpu")
    sys.exit(1)


@dataclass
class TestCase:
    """A single test case for similarity validation."""
    id: str
    category: str
    text1: str
    text2: str
    expected_min: float
    expected_max: float
    description: str


# =============================================================================
# TEST FIXTURES
# =============================================================================

KOREAN_TEST_CASES = [
    # IDENTICAL (should be 99-100%)
    TestCase(
        id="KO_IDENTICAL_001",
        category="identical",
        text1="저장하시겠습니까?",
        text2="저장하시겠습니까?",
        expected_min=0.99,
        expected_max=1.00,
        description="Identical Korean text"
    ),
    TestCase(
        id="KO_IDENTICAL_002",
        category="identical",
        text1="파일을 삭제합니다",
        text2="파일을 삭제합니다",
        expected_min=0.99,
        expected_max=1.00,
        description="Identical Korean sentence"
    ),

    # PUNCTUATION DIFFERENCE (should be 85-99%)
    TestCase(
        id="KO_PUNCT_001",
        category="punctuation_diff",
        text1="저장하시겠습니까?",
        text2="저장하시겠습니까",
        expected_min=0.85,
        expected_max=0.99,
        description="Question mark removed"
    ),
    TestCase(
        id="KO_PUNCT_002",
        category="punctuation_diff",
        text1="완료되었습니다!",
        text2="완료되었습니다",
        expected_min=0.85,
        expected_max=0.99,
        description="Exclamation mark removed"
    ),

    # WHITESPACE DIFFERENCE (should be 95-100%)
    TestCase(
        id="KO_SPACE_001",
        category="whitespace_diff",
        text1="파일을 저장합니다",
        text2="파일을  저장합니다",
        expected_min=0.95,
        expected_max=1.00,
        description="Extra space in middle"
    ),

    # ONE WORD DIFFERENCE (should be 70-90%)
    TestCase(
        id="KO_WORD_001",
        category="one_word_diff",
        text1="파일을 저장하시겠습니까?",
        text2="문서를 저장하시겠습니까?",
        expected_min=0.70,
        expected_max=0.92,
        description="파일→문서 (file→document)"
    ),
    TestCase(
        id="KO_WORD_002",
        category="one_word_diff",
        text1="게임을 시작합니다",
        text2="게임을 종료합니다",
        expected_min=0.65,
        expected_max=0.88,
        description="시작→종료 (start→end)"
    ),

    # SYNONYM (should be 75-92%)
    TestCase(
        id="KO_SYN_001",
        category="synonym",
        text1="저장하시겠습니까?",
        text2="저장할까요?",
        expected_min=0.75,
        expected_max=0.95,
        description="Formal vs casual save question"
    ),
    TestCase(
        id="KO_SYN_002",
        category="synonym",
        text1="취소하시겠습니까?",
        text2="취소할까요?",
        expected_min=0.75,
        expected_max=0.95,
        description="Formal vs casual cancel question"
    ),

    # FORMAL/INFORMAL (should be 70-90%)
    TestCase(
        id="KO_FORM_001",
        category="formal_informal",
        text1="저장하시겠습니까?",
        text2="저장할래?",
        expected_min=0.65,
        expected_max=0.90,
        description="Very formal vs very informal"
    ),

    # OPPOSITE MEANING (should be <80%, ideally <70%)
    TestCase(
        id="KO_OPP_001",
        category="opposite_action",
        text1="저장하시겠습니까?",
        text2="삭제하시겠습니까?",
        expected_min=0.50,
        expected_max=0.80,
        description="Save vs Delete"
    ),
    TestCase(
        id="KO_OPP_002",
        category="opposite_action",
        text1="시작",
        text2="종료",
        expected_min=0.40,
        expected_max=0.75,
        description="Start vs End (short)"
    ),

    # UNRELATED (should be <65%)
    TestCase(
        id="KO_UNREL_001",
        category="unrelated",
        text1="저장하시겠습니까?",
        text2="오늘 날씨가 좋습니다",
        expected_min=0.20,
        expected_max=0.65,
        description="Save dialog vs weather comment"
    ),
    TestCase(
        id="KO_UNREL_002",
        category="unrelated",
        text1="파일을 삭제합니다",
        text2="맛있는 음식을 먹었습니다",
        expected_min=0.20,
        expected_max=0.60,
        description="File deletion vs food comment"
    ),
]

ENGLISH_TEST_CASES = [
    # IDENTICAL
    TestCase(
        id="EN_IDENTICAL_001",
        category="identical",
        text1="Do you want to save?",
        text2="Do you want to save?",
        expected_min=0.99,
        expected_max=1.00,
        description="Identical English text"
    ),

    # CASE DIFFERENCE (should be 90-99%)
    TestCase(
        id="EN_CASE_001",
        category="case_diff",
        text1="Save the file",
        text2="save the file",
        expected_min=0.90,
        expected_max=1.00,
        description="Capitalization difference"
    ),

    # SLIGHT VARIATION (for NPC testing)
    TestCase(
        id="EN_VAR_001",
        category="slight_variation",
        text1="Save",
        text2="Save file",
        expected_min=0.60,
        expected_max=0.85,
        description="Short vs extended (NPC scenario)"
    ),
    TestCase(
        id="EN_VAR_002",
        category="slight_variation",
        text1="Save",
        text2="Save changes",
        expected_min=0.55,
        expected_max=0.80,
        description="Short vs extended with different word"
    ),
    TestCase(
        id="EN_VAR_003",
        category="slight_variation",
        text1="Cancel",
        text2="Cancel operation",
        expected_min=0.55,
        expected_max=0.85,
        description="Short vs extended cancel"
    ),

    # SYNONYM
    TestCase(
        id="EN_SYN_001",
        category="synonym",
        text1="Do you want to save?",
        text2="Would you like to save?",
        expected_min=0.80,
        expected_max=0.98,
        description="Want vs would like"
    ),

    # OPPOSITE
    TestCase(
        id="EN_OPP_001",
        category="opposite_action",
        text1="Save",
        text2="Delete",
        expected_min=0.40,
        expected_max=0.70,
        description="Save vs Delete (short)"
    ),
]

MULTILINE_TEST_CASES = [
    # SAME LINES, SAME ORDER
    TestCase(
        id="ML_SAME_001",
        category="multiline_same",
        text1="저장\n취소\n삭제",
        text2="저장\n취소\n삭제",
        expected_min=0.99,
        expected_max=1.00,
        description="Identical multiline"
    ),

    # SAME LINES, DIFFERENT ORDER
    TestCase(
        id="ML_ORDER_001",
        category="multiline_reorder",
        text1="저장\n취소\n삭제",
        text2="삭제\n취소\n저장",
        expected_min=0.75,
        expected_max=0.95,
        description="Same content, different order"
    ),

    # PARTIAL MATCH
    TestCase(
        id="ML_PARTIAL_001",
        category="multiline_partial",
        text1="저장\n취소\n삭제",
        text2="저장\n확인\n닫기",
        expected_min=0.60,
        expected_max=0.85,
        description="1 of 3 lines match"
    ),

    # SINGLE VS MULTILINE
    TestCase(
        id="ML_SINGLE_001",
        category="single_vs_multi",
        text1="저장",
        text2="저장\n취소\n삭제",
        expected_min=0.50,
        expected_max=0.80,
        description="Single word vs multiline containing it"
    ),
]

CODE_STRIP_TEST_CASES = [
    # Text that would have codes stripped before embedding
    TestCase(
        id="CODE_001",
        category="code_stripped",
        text1="안녕하세요",
        text2="안녕하세요",  # After stripping {ItemID:123}
        expected_min=0.99,
        expected_max=1.00,
        description="Same text after code strip"
    ),
    TestCase(
        id="CODE_002",
        category="code_stripped",
        text1="아이템을 획득했습니다",
        text2="아이템을 획득했습니다",  # After stripping codes
        expected_min=0.99,
        expected_max=1.00,
        description="Item obtained text"
    ),
]


# =============================================================================
# TEST RUNNER
# =============================================================================

class QWENValidator:
    """Validates QWEN embedding quality."""

    def __init__(self, model_name: str = "Qwen/Qwen3-Embedding-0.6B"):
        print(f"\n[Loading QWEN model: {model_name}]")
        print("(This may take 30-60 seconds on first run...)")
        self.model = SentenceTransformer(model_name)
        print("[Model loaded successfully]\n")

    def compute_similarity(self, text1: str, text2: str) -> float:
        """Compute cosine similarity between two texts."""
        embeddings = self.model.encode([text1, text2])
        embeddings = np.array(embeddings, dtype=np.float32)
        faiss.normalize_L2(embeddings)
        return float(np.dot(embeddings[0], embeddings[1]))

    def run_test_case(self, tc: TestCase) -> Dict:
        """Run a single test case and return results."""
        score = self.compute_similarity(tc.text1, tc.text2)

        in_range = tc.expected_min <= score <= tc.expected_max
        status = "PASS" if in_range else "FAIL"

        # Determine if this is a critical failure
        if not in_range:
            if score < tc.expected_min:
                deviation = tc.expected_min - score
                severity = "LOW" if deviation < 0.10 else "HIGH"
            else:
                deviation = score - tc.expected_max
                severity = "LOW" if deviation < 0.10 else "HIGH"
        else:
            severity = None
            deviation = 0

        return {
            "id": tc.id,
            "category": tc.category,
            "description": tc.description,
            "text1": tc.text1[:30] + "..." if len(tc.text1) > 30 else tc.text1,
            "text2": tc.text2[:30] + "..." if len(tc.text2) > 30 else tc.text2,
            "score": score,
            "expected_min": tc.expected_min,
            "expected_max": tc.expected_max,
            "status": status,
            "severity": severity,
            "deviation": deviation,
        }


def print_report(results: List[Dict], title: str):
    """Print formatted test results."""
    print(f"\n{'='*80}")
    print(f" {title}")
    print(f"{'='*80}\n")

    # Group by category
    categories = {}
    for r in results:
        cat = r["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(r)

    pass_count = 0
    fail_count = 0

    for cat, cat_results in categories.items():
        print(f"\n--- {cat.upper()} ---\n")
        print(f"{'ID':<18} {'Score':>7} {'Expected':>12} {'Status':>8} {'Description'}")
        print("-" * 80)

        for r in cat_results:
            expected_str = f"{r['expected_min']:.0%}-{r['expected_max']:.0%}"
            status_marker = "✓" if r["status"] == "PASS" else "✗"

            if r["status"] == "PASS":
                pass_count += 1
            else:
                fail_count += 1

            print(f"{r['id']:<18} {r['score']:>6.1%} {expected_str:>12} {status_marker:>8} {r['description']}")

    # Summary
    total = pass_count + fail_count
    print(f"\n{'='*80}")
    print(f" SUMMARY: {pass_count}/{total} passed ({pass_count/total*100:.1f}%)")
    print(f"{'='*80}\n")

    return pass_count, fail_count


def print_threshold_analysis(results: List[Dict]):
    """Analyze results to suggest optimal thresholds."""
    print("\n" + "="*80)
    print(" THRESHOLD ANALYSIS")
    print("="*80 + "\n")

    # Group scores by what they should/shouldn't match
    should_match_92 = []  # Should match at 92% threshold
    should_match_85 = []  # Should match at 85% threshold
    should_not_match = []  # Should NOT match

    for r in results:
        cat = r["category"]
        score = r["score"]

        if cat in ["identical", "punctuation_diff", "whitespace_diff", "case_diff"]:
            should_match_92.append((r["id"], score))
        elif cat in ["synonym", "formal_informal", "one_word_diff", "slight_variation"]:
            should_match_85.append((r["id"], score))
        elif cat in ["opposite_action", "unrelated"]:
            should_not_match.append((r["id"], score))

    # Analyze 92% threshold
    if should_match_92:
        scores = [s[1] for s in should_match_92]
        min_score = min(scores)
        print(f"At 92% threshold (exact/near-exact):")
        print(f"  - Lowest score in group: {min_score:.1%}")
        print(f"  - Would {'PASS' if min_score >= 0.92 else 'FAIL'} all at 92%")
        print(f"  - Recommended: {'92% OK' if min_score >= 0.92 else f'Lower to {min_score*100:.0f}%'}")
        print()

    # Analyze 85% threshold
    if should_match_85:
        scores = [s[1] for s in should_match_85]
        min_score = min(scores)
        print(f"At 85% threshold (semantic matches):")
        print(f"  - Lowest score in group: {min_score:.1%}")
        print(f"  - Would {'PASS' if min_score >= 0.85 else 'FAIL'} all at 85%")
        print(f"  - Recommended: {'85% OK' if min_score >= 0.85 else f'Lower to {min_score*100:.0f}%'}")
        print()

    # Analyze false positives
    if should_not_match:
        scores = [s[1] for s in should_not_match]
        max_score = max(scores)
        print(f"False positive risk (opposite/unrelated):")
        print(f"  - Highest score in group: {max_score:.1%}")
        print(f"  - Safe threshold: >{max_score*100:.0f}% to avoid false matches")
        print()

    # NPC Analysis
    npc_cases = [r for r in results if r["category"] == "slight_variation"]
    if npc_cases:
        scores = [r["score"] for r in npc_cases]
        print(f"NPC threshold analysis (short variations):")
        print(f"  - Score range: {min(scores):.1%} - {max(scores):.1%}")
        print(f"  - 80% threshold would: {'FAIL some valid variations' if min(scores) < 0.80 else 'PASS all'}")
        print(f"  - RECOMMENDATION: Lower NPC to 60-65%")


def main():
    """Run all validation tests."""
    print("\n" + "#"*80)
    print("#" + " "*30 + "QWEN VALIDATION SUITE" + " "*27 + "#")
    print("#"*80)

    validator = QWENValidator()

    all_results = []

    # Run Korean tests
    print("\nRunning Korean test cases...")
    for tc in KOREAN_TEST_CASES:
        result = validator.run_test_case(tc)
        all_results.append(result)

    # Run English tests
    print("Running English test cases...")
    for tc in ENGLISH_TEST_CASES:
        result = validator.run_test_case(tc)
        all_results.append(result)

    # Run Multiline tests
    print("Running multiline test cases...")
    for tc in MULTILINE_TEST_CASES:
        result = validator.run_test_case(tc)
        all_results.append(result)

    # Run Code strip tests
    print("Running code strip test cases...")
    for tc in CODE_STRIP_TEST_CASES:
        result = validator.run_test_case(tc)
        all_results.append(result)

    # Print reports
    korean_results = [r for r in all_results if r["id"].startswith("KO_")]
    english_results = [r for r in all_results if r["id"].startswith("EN_")]
    multiline_results = [r for r in all_results if r["id"].startswith("ML_")]
    code_results = [r for r in all_results if r["id"].startswith("CODE_")]

    print_report(korean_results, "KOREAN TEST RESULTS")
    print_report(english_results, "ENGLISH TEST RESULTS")
    print_report(multiline_results, "MULTILINE TEST RESULTS")
    print_report(code_results, "CODE STRIP TEST RESULTS")

    # Overall summary
    total_pass, total_fail = 0, 0
    for results in [korean_results, english_results, multiline_results, code_results]:
        p = sum(1 for r in results if r["status"] == "PASS")
        f = sum(1 for r in results if r["status"] == "FAIL")
        total_pass += p
        total_fail += f

    print("\n" + "="*80)
    print(" OVERALL RESULTS")
    print("="*80)
    print(f"\n  Total: {total_pass + total_fail} test cases")
    print(f"  Passed: {total_pass} ({total_pass/(total_pass+total_fail)*100:.1f}%)")
    print(f"  Failed: {total_fail}")

    # Threshold analysis
    print_threshold_analysis(all_results)

    # Failures detail
    failures = [r for r in all_results if r["status"] == "FAIL"]
    if failures:
        print("\n" + "="*80)
        print(" FAILURE DETAILS")
        print("="*80 + "\n")
        for f in failures:
            print(f"  {f['id']}: {f['score']:.1%} (expected {f['expected_min']:.0%}-{f['expected_max']:.0%})")
            print(f"    Text1: {f['text1']}")
            print(f"    Text2: {f['text2']}")
            print()

    print("\n" + "#"*80)
    print("#" + " "*30 + "END OF REPORT" + " "*35 + "#")
    print("#"*80 + "\n")

    return total_fail == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
