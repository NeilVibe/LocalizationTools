"""
Full Logic Validation Test Suite

Tests:
1. QWEN with LONGER phrases (sentences, paragraphs)
2. XLS Transfer logic (code preservation, newline adaptation)
3. KR Similar logic (structure adaptation, triangle markers)

Run with: python3 tests/fixtures/pretranslation/test_full_logic_validation.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

import numpy as np
from typing import List, Dict, Tuple
from dataclasses import dataclass

try:
    from sentence_transformers import SentenceTransformer
    import faiss
except ImportError as e:
    print(f"Missing dependency: {e}")
    sys.exit(1)

# Import XLS Transfer and KR Similar logic
try:
    from server.tools.xlstransfer.core import simple_number_replace, clean_text
    from server.tools.kr_similar.core import adapt_structure
    XLS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: XLS Transfer not available: {e}")
    XLS_AVAILABLE = False

try:
    from server.tools.kr_similar.core import adapt_structure
    KR_SIMILAR_AVAILABLE = True
except ImportError as e:
    print(f"Warning: KR Similar not available: {e}")
    KR_SIMILAR_AVAILABLE = False


# =============================================================================
# PART 1: LONGER PHRASE TESTS (QWEN)
# =============================================================================

LONG_PHRASE_TESTS = [
    # Full sentences - Korean
    {
        "id": "LONG_KO_001",
        "text1": "이 파일을 저장하시겠습니까? 저장하지 않으면 변경사항이 손실됩니다.",
        "text2": "이 파일을 저장하시겠습니까? 저장하지 않으면 변경사항이 손실됩니다.",
        "expected_min": 0.99,
        "expected_max": 1.00,
        "description": "Identical long Korean sentence"
    },
    {
        "id": "LONG_KO_002",
        "text1": "이 파일을 저장하시겠습니까? 저장하지 않으면 변경사항이 손실됩니다.",
        "text2": "이 파일을 저장할까요? 저장하지 않으면 변경사항이 사라집니다.",
        "expected_min": 0.85,
        "expected_max": 0.98,
        "description": "Similar long Korean (formal vs casual, synonyms)"
    },
    {
        "id": "LONG_KO_003",
        "text1": "게임을 종료하시겠습니까? 저장하지 않은 진행 상황은 모두 잃게 됩니다.",
        "text2": "게임을 시작하시겠습니까? 새로운 모험이 당신을 기다립니다.",
        "expected_min": 0.50,
        "expected_max": 0.75,
        "description": "Different long Korean (exit vs start game)"
    },

    # Full sentences - English
    {
        "id": "LONG_EN_001",
        "text1": "Are you sure you want to delete this file? This action cannot be undone.",
        "text2": "Are you sure you want to delete this file? This action cannot be undone.",
        "expected_min": 0.99,
        "expected_max": 1.00,
        "description": "Identical long English sentence"
    },
    {
        "id": "LONG_EN_002",
        "text1": "Are you sure you want to delete this file? This action cannot be undone.",
        "text2": "Do you really want to remove this file? This operation is irreversible.",
        "expected_min": 0.80,
        "expected_max": 0.95,
        "description": "Similar long English (synonyms throughout)"
    },
    {
        "id": "LONG_EN_003",
        "text1": "Welcome to the game! Press any key to start your adventure.",
        "text2": "Game over. Your final score is displayed above.",
        "expected_min": 0.40,
        "expected_max": 0.70,
        "description": "Different long English (welcome vs game over)"
    },

    # Paragraph-length text
    {
        "id": "PARA_001",
        "text1": "안녕하세요, 모험가님! 오늘의 퀘스트가 준비되어 있습니다. 마을 광장에서 NPC를 만나 새로운 임무를 받아보세요.",
        "text2": "안녕하세요, 모험가님! 오늘의 퀘스트가 준비되어 있습니다. 마을 광장에서 NPC를 만나 새로운 임무를 받아보세요.",
        "expected_min": 0.99,
        "expected_max": 1.00,
        "description": "Identical paragraph"
    },
    {
        "id": "PARA_002",
        "text1": "안녕하세요, 모험가님! 오늘의 퀘스트가 준비되어 있습니다. 마을 광장에서 NPC를 만나 새로운 임무를 받아보세요.",
        "text2": "반갑습니다, 용사님! 오늘의 미션이 대기 중입니다. 성문 앞에서 경비병을 만나 새로운 의뢰를 확인하세요.",
        "expected_min": 0.70,
        "expected_max": 0.90,
        "description": "Similar paragraph (different words, same structure)"
    },

    # Multi-line dialogue
    {
        "id": "DIALOG_001",
        "text1": "▶안녕하세요.\n▶무엇을 도와드릴까요?\n▶감사합니다.",
        "text2": "▶안녕하세요.\n▶무엇을 도와드릴까요?\n▶감사합니다.",
        "expected_min": 0.99,
        "expected_max": 1.00,
        "description": "Identical dialogue with triangle markers"
    },
    {
        "id": "DIALOG_002",
        "text1": "▶안녕하세요.\n▶무엇을 도와드릴까요?\n▶감사합니다.",
        "text2": "▶안녕.\n▶뭐 필요해?\n▶고마워.",
        "expected_min": 0.70,
        "expected_max": 0.90,
        "description": "Similar dialogue (formal vs casual)"
    },

    # Text with codes (should test stripping)
    {
        "id": "CODE_LONG_001",
        "text1": "{ItemID:12345}축하합니다! 레어 아이템을 획득했습니다.",
        "text2": "축하합니다! 레어 아이템을 획득했습니다.",
        "expected_min": 0.85,
        "expected_max": 1.00,
        "description": "Text with vs without item code"
    },
    {
        "id": "CODE_LONG_002",
        "text1": "<PAColor>경고!</PAColor> 체력이 낮습니다. 포션을 사용하세요.",
        "text2": "경고! 체력이 낮습니다. 포션을 사용하세요.",
        "expected_min": 0.85,
        "expected_max": 1.00,
        "description": "Text with vs without color tags"
    },
]


# =============================================================================
# PART 2: XLS TRANSFER LOGIC TESTS
# =============================================================================

XLS_TRANSFER_TESTS = [
    # Code preservation tests
    {
        "id": "XLS_CODE_001",
        "original": "{ItemID:123}안녕하세요",
        "translated": "Hello",
        "expected": "{ItemID:123}Hello",
        "description": "Simple code preservation"
    },
    {
        "id": "XLS_CODE_002",
        "original": "{ChangeScene()}{AudioVoice()}대화 시작",
        "translated": "Dialogue starts",
        "expected": "{ChangeScene()}{AudioVoice()}Dialogue starts",
        "description": "Multiple codes preservation"
    },
    {
        "id": "XLS_CODE_003",
        "original": "<PAColor>경고!<PAOldColor>",
        "translated": "Warning!",
        "expected": "<PAColor>Warning!<PAOldColor>",
        "description": "Color tag preservation"
    },
    {
        "id": "XLS_CODE_004",
        "original": "{Code1}{Code2}{Code3}텍스트 내용",
        "translated": "Text content",
        "expected": "{Code1}{Code2}{Code3}Text content",
        "description": "Three codes preservation"
    },
    {
        "id": "XLS_CODE_005",
        "original": "코드 없는 텍스트",
        "translated": "Text without codes",
        "expected": "Text without codes",
        "description": "No codes - pass through"
    },
]


# =============================================================================
# PART 3: KR SIMILAR LOGIC TESTS
# =============================================================================

KR_SIMILAR_TESTS = [
    # Structure adaptation tests
    {
        "id": "KR_STRUCT_001",
        "korean": "안녕하세요.\n좋은 아침입니다.",
        "translation": "Hello. Good morning.",
        "expected_lines": 2,
        "description": "2-line Korean to 2-line translation"
    },
    {
        "id": "KR_STRUCT_002",
        "korean": "저장\n취소\n삭제",
        "translation": "Save Cancel Delete",
        "expected_lines": 3,
        "description": "3-line Korean to single-line translation (should split)"
    },
    {
        "id": "KR_STRUCT_003",
        "korean": "한 줄 텍스트",
        "translation": "Single line text",
        "expected_lines": 1,
        "description": "Single line stays single"
    },
]


# =============================================================================
# TEST RUNNER
# =============================================================================

class FullLogicValidator:
    def __init__(self):
        print("\n[Loading QWEN model...]")
        self.model = SentenceTransformer("Qwen/Qwen3-Embedding-0.6B")
        print("[Model loaded]\n")

    def compute_similarity(self, text1: str, text2: str) -> float:
        embeddings = self.model.encode([text1, text2])
        embeddings = np.array(embeddings, dtype=np.float32)
        faiss.normalize_L2(embeddings)
        return float(np.dot(embeddings[0], embeddings[1]))


def run_long_phrases(validator: FullLogicValidator) -> Tuple[int, int]:
    """Test QWEN with longer phrases."""
    print("\n" + "="*80)
    print(" PART 1: LONGER PHRASE TESTS (QWEN)")
    print("="*80 + "\n")

    passed = 0
    failed = 0

    print(f"{'ID':<15} {'Score':>7} {'Expected':>12} {'Status':>8} {'Description'}")
    print("-"*80)

    for test in LONG_PHRASE_TESTS:
        score = validator.compute_similarity(test["text1"], test["text2"])
        in_range = test["expected_min"] <= score <= test["expected_max"]
        status = "✓" if in_range else "✗"

        if in_range:
            passed += 1
        else:
            failed += 1

        expected_str = f"{test['expected_min']:.0%}-{test['expected_max']:.0%}"
        print(f"{test['id']:<15} {score:>6.1%} {expected_str:>12} {status:>8} {test['description'][:35]}")

    print(f"\nLong phrase tests: {passed}/{passed+failed} passed")
    return passed, failed


def run_xls_transfer_logic() -> Tuple[int, int]:
    """Test XLS Transfer code preservation."""
    print("\n" + "="*80)
    print(" PART 2: XLS TRANSFER LOGIC TESTS")
    print("="*80 + "\n")

    if not XLS_AVAILABLE:
        print("XLS Transfer module not available - skipping")
        return 0, 0

    passed = 0
    failed = 0

    print(f"{'ID':<15} {'Status':>8} {'Description'}")
    print("-"*80)

    for test in XLS_TRANSFER_TESTS:
        try:
            result = simple_number_replace(test["original"], test["translated"])
            is_correct = result == test["expected"]
            status = "✓" if is_correct else "✗"

            if is_correct:
                passed += 1
            else:
                failed += 1

            print(f"{test['id']:<15} {status:>8} {test['description']}")
            if not is_correct:
                print(f"   Expected: {test['expected']}")
                print(f"   Got:      {result}")
        except Exception as e:
            failed += 1
            print(f"{test['id']:<15} {'ERROR':>8} {test['description']}")
            print(f"   Error: {e}")

    print(f"\nXLS Transfer tests: {passed}/{passed+failed} passed")
    return passed, failed


def run_kr_similar_logic() -> Tuple[int, int]:
    """Test KR Similar structure adaptation."""
    print("\n" + "="*80)
    print(" PART 3: KR SIMILAR LOGIC TESTS")
    print("="*80 + "\n")

    if not KR_SIMILAR_AVAILABLE:
        print("KR Similar module not available - skipping")
        return 0, 0

    passed = 0
    failed = 0

    print(f"{'ID':<15} {'Status':>8} {'Description'}")
    print("-"*80)

    for test in KR_SIMILAR_TESTS:
        try:
            result = adapt_structure(test["korean"], test["translation"])
            result_lines = len(result.split('\n'))
            is_correct = result_lines == test["expected_lines"]
            status = "✓" if is_correct else "✗"

            if is_correct:
                passed += 1
            else:
                failed += 1

            print(f"{test['id']:<15} {status:>8} {test['description']}")
            if not is_correct:
                print(f"   Expected lines: {test['expected_lines']}")
                print(f"   Got lines: {result_lines}")
                print(f"   Result: {repr(result)}")
        except Exception as e:
            failed += 1
            print(f"{test['id']:<15} {'ERROR':>8} {test['description']}")
            print(f"   Error: {e}")

    print(f"\nKR Similar tests: {passed}/{passed+failed} passed")
    return passed, failed


def run_combined_scenarios(validator: FullLogicValidator) -> Tuple[int, int]:
    """Test realistic combined scenarios."""
    print("\n" + "="*80)
    print(" PART 4: COMBINED REALISTIC SCENARIOS")
    print("="*80 + "\n")

    # Simulate real pretranslation workflow
    scenarios = [
        {
            "id": "REAL_001",
            "description": "TM exact match scenario",
            "tm_source": "파일을 저장하시겠습니까?",
            "tm_target": "Do you want to save the file?",
            "input_source": "파일을 저장하시겠습니까?",
            "expected_tier": 1,  # Perfect match
        },
        {
            "id": "REAL_002",
            "description": "TM semantic match scenario",
            "tm_source": "파일을 저장하시겠습니까?",
            "tm_target": "Do you want to save the file?",
            "input_source": "문서를 저장하시겠습니까?",  # 파일→문서
            "expected_tier": 2,  # Embedding match
        },
        {
            "id": "REAL_003",
            "description": "Code preservation scenario",
            "tm_source": "아이템 획득",
            "tm_target": "Item obtained",
            "input_source": "{ItemID:999}아이템 획득",
            "expected_has_code": True,
        },
    ]

    passed = 0
    failed = 0

    for scenario in scenarios:
        print(f"\n--- {scenario['id']}: {scenario['description']} ---")

        # Calculate similarity
        similarity = validator.compute_similarity(
            scenario["tm_source"],
            scenario["input_source"]
        )

        print(f"TM Source:    {scenario['tm_source']}")
        print(f"Input Source: {scenario['input_source']}")
        print(f"Similarity:   {similarity:.1%}")

        if "expected_tier" in scenario:
            if scenario["expected_tier"] == 1 and similarity >= 0.99:
                print(f"Result: ✓ Would match Tier 1 (perfect)")
                passed += 1
            elif scenario["expected_tier"] == 2 and 0.72 <= similarity < 0.99:
                print(f"Result: ✓ Would match Tier 2 (embedding) at 72%+ threshold")
                passed += 1
            else:
                print(f"Result: ✗ Unexpected tier behavior")
                failed += 1

        if "expected_has_code" in scenario:
            if XLS_AVAILABLE:
                # Strip code from input, check TM match, then re-add code
                clean_input = scenario["input_source"]
                # Simple code strip for test
                import re
                clean_input = re.sub(r'\{[^}]+\}', '', clean_input)
                sim = validator.compute_similarity(scenario["tm_source"], clean_input)
                print(f"After code strip similarity: {sim:.1%}")
                if sim >= 0.99:
                    print(f"Result: ✓ Would match after code stripping")
                    passed += 1
                else:
                    print(f"Result: ✗ Code stripping didn't help")
                    failed += 1

    print(f"\nCombined scenarios: {passed}/{passed+failed} passed")
    return passed, failed


def main():
    print("\n" + "#"*80)
    print("#" + " "*25 + "FULL LOGIC VALIDATION SUITE" + " "*26 + "#")
    print("#"*80)

    validator = FullLogicValidator()

    total_passed = 0
    total_failed = 0

    # Part 1: Long phrases
    p, f = run_long_phrases(validator)
    total_passed += p
    total_failed += f

    # Part 2: XLS Transfer
    p, f = run_xls_transfer_logic()
    total_passed += p
    total_failed += f

    # Part 3: KR Similar
    p, f = run_kr_similar_logic()
    total_passed += p
    total_failed += f

    # Part 4: Combined scenarios
    p, f = run_combined_scenarios(validator)
    total_passed += p
    total_failed += f

    # Final summary
    print("\n" + "="*80)
    print(" FINAL SUMMARY")
    print("="*80)
    total = total_passed + total_failed
    print(f"\n  Total tests: {total}")
    print(f"  Passed: {total_passed} ({total_passed/total*100:.1f}%)" if total > 0 else "  No tests run")
    print(f"  Failed: {total_failed}")
    print("\n" + "#"*80 + "\n")

    return total_failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
