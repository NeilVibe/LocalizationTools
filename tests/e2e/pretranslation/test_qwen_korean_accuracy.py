#!/usr/bin/env python3
"""
QWEN Korean Accuracy Test

Tests how well QWEN handles Korean semantic similarity.
This is critical since the production data is Korean → French/Other.

Test categories:
1. Identical Korean text
2. Korean with punctuation differences
3. Korean verb form variations (하다/합니다/했습니다)
4. Korean honorific variations (요/습니다)
5. Korean synonym pairs
6. Korean word order variations
7. Korean abbreviations vs full forms
8. Korean with particles added/removed
9. Korean completely different meanings
10. Real production patterns from game localization
"""

import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    MODELS_AVAILABLE = True
except ImportError:
    MODELS_AVAILABLE = False
    print("ERROR: sentence_transformers not available")
    sys.exit(1)

MODEL_NAME = "Qwen/Qwen3-Embedding-0.6B"


def cosine_similarity(emb1, emb2):
    """Calculate cosine similarity between two embeddings."""
    return np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))


# =============================================================================
# KOREAN TEST CASES
# =============================================================================

KOREAN_TEST_CASES = {
    # Category 1: Identical (should be 100%)
    "identical": [
        ("저장하시겠습니까?", "저장하시겠습니까?", "Identical question"),
        ("게임을 시작합니다", "게임을 시작합니다", "Identical statement"),
        ("아이템을 획득했습니다", "아이템을 획득했습니다", "Identical past tense"),
        ("안녕하세요", "안녕하세요", "Identical greeting"),
        ("레벨이 상승했습니다", "레벨이 상승했습니다", "Identical level up"),
    ],

    # Category 2: Punctuation differences (should be >95%)
    "punctuation": [
        ("저장하시겠습니까?", "저장하시겠습니까", "Question mark removed"),
        ("완료되었습니다!", "완료되었습니다", "Exclamation removed"),
        ("로딩중...", "로딩중", "Ellipsis removed"),
        ("확인!", "확인", "Short with exclamation"),
        ("게임 시작?", "게임 시작", "Space + question mark"),
    ],

    # Category 3: Verb form variations (Korean specific)
    "verb_forms": [
        ("저장하다", "저장합니다", "Plain → Formal"),
        ("저장했다", "저장했습니다", "Past plain → Past formal"),
        ("시작하다", "시작합니다", "Start verb forms"),
        ("완료하다", "완료했습니다", "Complete verb forms"),
        ("획득하다", "획득했습니다", "Obtain verb forms"),
        ("사용하다", "사용합니다", "Use verb forms"),
        ("삭제하다", "삭제합니다", "Delete verb forms"),
    ],

    # Category 4: Honorific variations
    "honorifics": [
        ("저장해요", "저장합니다", "Casual → Formal"),
        ("시작해요", "시작합니다", "Start casual/formal"),
        ("감사해요", "감사합니다", "Thanks casual/formal"),
        ("알겠어요", "알겠습니다", "Understand casual/formal"),
        ("기다려요", "기다려 주세요", "Wait casual/polite"),
    ],

    # Category 5: Synonym pairs (same meaning, different words)
    "synonyms": [
        ("저장", "세이브", "Save Korean/English loan"),
        ("취소", "캔슬", "Cancel Korean/English loan"),
        ("시작", "스타트", "Start Korean/English loan"),
        ("종료", "끝", "End formal/casual"),
        ("확인", "체크", "Confirm/Check"),
        ("삭제", "지우기", "Delete formal/casual"),
        ("설정", "세팅", "Settings Korean/English"),
        ("불러오기", "로드", "Load Korean/English"),
    ],

    # Category 6: Word order / structure variations
    "structure": [
        ("파일을 저장합니다", "저장합니다 파일을", "Object-verb swap"),
        ("게임을 시작하시겠습니까?", "시작하시겠습니까 게임을?", "Question reorder"),
        ("아이템 획득", "획득한 아이템", "Noun phrase reorder"),
        ("레벨 상승", "상승한 레벨", "Level up reorder"),
    ],

    # Category 7: Abbreviations vs full forms
    "abbreviations": [
        ("경험치", "경험 포인트", "XP short/long"),
        ("레벨", "레벨 수치", "Level short/long"),
        ("공격력", "공격 능력치", "Attack short/long"),
        ("방어력", "방어 능력치", "Defense short/long"),
        ("HP", "체력", "HP English/Korean"),
        ("MP", "마나", "MP English/Korean"),
    ],

    # Category 8: Particles added/removed
    "particles": [
        ("아이템을 획득", "아이템 획득", "Object particle removed"),
        ("게임이 시작", "게임 시작", "Subject particle removed"),
        ("레벨이 상승", "레벨 상승", "Subject particle removed"),
        ("퀘스트를 완료", "퀘스트 완료", "Object particle removed"),
        ("스킬을 습득", "스킬 습득", "Object particle removed"),
    ],

    # Category 9: Opposite/different meanings (should be LOW)
    "opposite": [
        ("저장", "삭제", "Save vs Delete"),
        ("시작", "종료", "Start vs End"),
        ("성공", "실패", "Success vs Failure"),
        ("획득", "소모", "Obtain vs Consume"),
        ("증가", "감소", "Increase vs Decrease"),
        ("공격", "방어", "Attack vs Defense"),
        ("열기", "닫기", "Open vs Close"),
    ],

    # Category 10: Completely unrelated (should be very LOW)
    "unrelated": [
        ("저장하시겠습니까?", "날씨가 좋습니다", "Save vs Weather"),
        ("게임 시작", "맛있는 음식", "Game vs Food"),
        ("레벨 상승", "파란 하늘", "Level up vs Blue sky"),
        ("아이템 획득", "친구를 만났습니다", "Item vs Friend"),
        ("퀘스트 완료", "음악을 듣습니다", "Quest vs Music"),
    ],

    # Category 11: Real game localization patterns
    "game_patterns": [
        # Similar game messages
        ("아이템을 획득했습니다", "아이템을 얻었습니다", "Item obtained variations"),
        ("골드를 획득했습니다", "골드를 얻었습니다", "Gold obtained variations"),
        ("경험치를 획득했습니다", "경험치를 얻었습니다", "XP obtained variations"),

        # Quest messages
        ("퀘스트를 완료했습니다", "퀘스트 완료!", "Quest complete variations"),
        ("새로운 퀘스트", "신규 퀘스트", "New quest variations"),

        # Status messages
        ("인벤토리가 가득 찼습니다", "가방이 꽉 찼습니다", "Inventory full variations"),
        ("골드가 부족합니다", "돈이 부족합니다", "Not enough gold variations"),

        # UI elements
        ("장비 착용", "장비 장착", "Equip variations"),
        ("장비 해제", "장비 탈착", "Unequip variations"),
    ],

    # Category 12: Multi-line Korean
    "multiline": [
        ("첫 번째\n두 번째", "첫 번째\n두 번째", "Identical multiline"),
        ("효과:\n- 공격력 증가", "효과:\n- 공격력 상승", "Similar multiline"),
        ("이름: 홍길동\n레벨: 50", "이름: 홍길동\n레벨: 50", "Stats multiline"),
    ],
}


def run_korean_accuracy_test():
    """Run comprehensive Korean accuracy test."""
    print("\n" + "="*70)
    print(" QWEN KOREAN ACCURACY TEST")
    print(" Testing semantic similarity for Korean text")
    print("="*70)

    # Load model
    print(f"\n  Loading model: {MODEL_NAME}")
    start = time.time()
    model = SentenceTransformer(MODEL_NAME)
    print(f"  ✅ Model loaded in {time.time() - start:.2f}s")

    # Results tracking
    all_results = {}
    category_stats = {}

    for category, test_cases in KOREAN_TEST_CASES.items():
        print(f"\n" + "="*70)
        print(f" Category: {category.upper()}")
        print("="*70)

        scores = []
        results = []

        for text1, text2, description in test_cases:
            # Get embeddings
            emb1 = model.encode(text1)
            emb2 = model.encode(text2)

            # Calculate similarity
            sim = cosine_similarity(emb1, emb2)
            scores.append(sim)

            # Determine if this is expected behavior
            if category in ["identical"]:
                expected = ">99%"
                status = "✅" if sim > 0.99 else "❌"
            elif category in ["punctuation", "particles"]:
                expected = ">95%"
                status = "✅" if sim > 0.95 else "⚠️" if sim > 0.90 else "❌"
            elif category in ["verb_forms", "honorifics", "game_patterns"]:
                expected = ">85%"
                status = "✅" if sim > 0.85 else "⚠️" if sim > 0.75 else "❌"
            elif category in ["synonyms", "abbreviations"]:
                expected = ">75%"
                status = "✅" if sim > 0.75 else "⚠️" if sim > 0.65 else "❌"
            elif category in ["structure"]:
                expected = ">70%"
                status = "✅" if sim > 0.70 else "⚠️" if sim > 0.60 else "❌"
            elif category in ["opposite"]:
                expected = "<70%"
                status = "✅" if sim < 0.70 else "⚠️" if sim < 0.80 else "❌"
            elif category in ["unrelated"]:
                expected = "<50%"
                status = "✅" if sim < 0.50 else "⚠️" if sim < 0.60 else "❌"
            elif category in ["multiline"]:
                expected = "varies"
                status = "✅" if sim > 0.90 else "⚠️"
            else:
                expected = "varies"
                status = "✅"

            results.append({
                "text1": text1,
                "text2": text2,
                "description": description,
                "similarity": sim,
                "status": status,
                "expected": expected,
            })

            print(f"  {status} {sim:.1%} | {description}")
            print(f"      '{text1[:25]}...' vs '{text2[:25]}...'")

        # Category stats
        avg_score = sum(scores) / len(scores) if scores else 0
        min_score = min(scores) if scores else 0
        max_score = max(scores) if scores else 0

        category_stats[category] = {
            "count": len(scores),
            "avg": avg_score,
            "min": min_score,
            "max": max_score,
            "results": results,
        }

        print(f"\n  Summary: avg={avg_score:.1%}, min={min_score:.1%}, max={max_score:.1%}")

        all_results[category] = results

    # Final summary
    print("\n" + "="*70)
    print(" KOREAN ACCURACY SUMMARY")
    print("="*70)

    print("\n  Category                    | Avg    | Min    | Max    | Expected")
    print("  " + "-"*68)

    expected_ranges = {
        "identical": (">99%", 0.99),
        "punctuation": (">95%", 0.95),
        "verb_forms": (">85%", 0.85),
        "honorifics": (">85%", 0.85),
        "synonyms": (">75%", 0.75),
        "abbreviations": (">75%", 0.75),
        "particles": (">95%", 0.95),
        "structure": (">70%", 0.70),
        "opposite": ("<70%", 0.70),
        "unrelated": ("<50%", 0.50),
        "game_patterns": (">85%", 0.85),
        "multiline": (">90%", 0.90),
    }

    passed = 0
    failed = 0

    for category, stats in category_stats.items():
        exp_str, exp_val = expected_ranges.get(category, ("varies", 0))

        if category in ["opposite", "unrelated"]:
            # For these, lower is better
            meets_expectation = stats["avg"] < exp_val
        else:
            meets_expectation = stats["avg"] >= exp_val

        status = "✅" if meets_expectation else "❌"
        if meets_expectation:
            passed += 1
        else:
            failed += 1

        print(f"  {status} {category:25} | {stats['avg']:.1%} | {stats['min']:.1%} | {stats['max']:.1%} | {exp_str}")

    # Threshold recommendations
    print("\n" + "="*70)
    print(" THRESHOLD RECOMMENDATIONS FOR KOREAN")
    print("="*70)

    # Calculate based on results
    verb_avg = category_stats.get("verb_forms", {}).get("avg", 0)
    synonym_avg = category_stats.get("synonyms", {}).get("avg", 0)
    opposite_max = category_stats.get("opposite", {}).get("max", 0)
    unrelated_max = category_stats.get("unrelated", {}).get("max", 0)

    print(f"\n  Verb form variations average: {verb_avg:.1%}")
    print(f"  Synonym pairs average: {synonym_avg:.1%}")
    print(f"  Opposite meanings max: {opposite_max:.1%}")
    print(f"  Unrelated text max: {unrelated_max:.1%}")

    # Safe threshold is above opposite meanings but catches verb forms
    safe_threshold = max(opposite_max + 0.05, 0.70)
    aggressive_threshold = min(verb_avg - 0.05, 0.90)

    print(f"\n  Recommended thresholds:")
    print(f"    Conservative (fewer false positives): {safe_threshold:.0%}")
    print(f"    Aggressive (more matches): {aggressive_threshold:.0%}")
    print(f"    Current default: 92%")

    if safe_threshold > 0.92:
        print(f"\n  ⚠️ WARNING: Current 92% threshold may miss valid Korean variations!")
        print(f"     Consider lowering to {safe_threshold:.0%} for Korean text")

    print("\n" + "="*70)
    print(f" FINAL RESULT: {passed}/{passed+failed} categories passed")
    print("="*70)

    return passed, failed, category_stats


if __name__ == "__main__":
    passed, failed, stats = run_korean_accuracy_test()
    sys.exit(0 if failed <= 2 else 1)  # Allow some failures
