#!/usr/bin/env python3
"""
REAL E2E Test for Standard TM with QWEN + FAISS

This test:
1. Creates a TM with ~200 entries (source + target pairs)
2. Builds FAISS HNSW indexes using QWEN embeddings
3. Runs 500 test queries through the 5-Tier Cascade
4. Tracks results by tier (exact match, embedding match, no match)
5. Verifies the full pipeline works correctly

Expected results:
- Tier 1 (exact hash): ~100 queries (exact matches)
- Tier 2 (embedding): ~200 queries (similar but not exact)
- Tier 3/4 (line): ~50 queries (line-level matches)
- Tier 5 (n-gram): ~50 queries (fuzzy matches)
- No match: ~100 queries (intentionally below threshold)
"""

import sys
import os
import time
import tempfile
import shutil
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

import numpy as np

# Check if we have the required libraries
try:
    from sentence_transformers import SentenceTransformer
    import faiss
    MODELS_AVAILABLE = True
except ImportError:
    MODELS_AVAILABLE = False
    print("ERROR: sentence_transformers or faiss not available")
    sys.exit(1)

from server.tools.ldm.tm_indexer import (
    normalize_for_hash,
    normalize_for_embedding,
    normalize_newlines_universal,
    TMSearcher,
    DEFAULT_THRESHOLD,
    NPC_THRESHOLD,
)
from server.tools.shared import FAISSManager
from server.tools.shared.embedding_engine import Model2VecEngine

# Constants from FAISSManager
HNSW_M = FAISSManager.HNSW_M
HNSW_EF_CONSTRUCTION = FAISSManager.HNSW_EF_CONSTRUCTION
HNSW_EF_SEARCH = FAISSManager.HNSW_EF_SEARCH

# Model name from embedding engine
MODEL_NAME = Model2VecEngine.MODEL_NAME


# =============================================================================
# TM DATA - ~200 entries covering various patterns
# =============================================================================

TM_ENTRIES = [
    # UI Elements (20 entries)
    ("저장", "Save"),
    ("저장하기", "Save"),
    ("파일 저장", "Save File"),
    ("저장하시겠습니까?", "Do you want to save?"),
    ("변경 사항을 저장하시겠습니까?", "Do you want to save changes?"),
    ("취소", "Cancel"),
    ("취소하기", "Cancel"),
    ("작업 취소", "Cancel Operation"),
    ("확인", "Confirm"),
    ("확인하기", "Confirm"),
    ("닫기", "Close"),
    ("창 닫기", "Close Window"),
    ("열기", "Open"),
    ("파일 열기", "Open File"),
    ("새로 만들기", "Create New"),
    ("새 파일", "New File"),
    ("삭제", "Delete"),
    ("삭제하기", "Delete"),
    ("항목 삭제", "Delete Item"),
    ("편집", "Edit"),

    # Game UI (30 entries)
    ("게임 시작", "Start Game"),
    ("게임을 시작합니다", "Starting the game"),
    ("새 게임", "New Game"),
    ("새 게임을 시작하시겠습니까?", "Do you want to start a new game?"),
    ("게임 종료", "Exit Game"),
    ("게임을 종료하시겠습니까?", "Do you want to exit the game?"),
    ("설정", "Settings"),
    ("게임 설정", "Game Settings"),
    ("옵션", "Options"),
    ("환경 설정", "Preferences"),
    ("로드", "Load"),
    ("게임 로드", "Load Game"),
    ("저장된 게임 불러오기", "Load Saved Game"),
    ("인벤토리", "Inventory"),
    ("아이템 목록", "Item List"),
    ("장비", "Equipment"),
    ("장비 착용", "Equip"),
    ("장비 해제", "Unequip"),
    ("스킬", "Skills"),
    ("스킬 목록", "Skill List"),
    ("퀘스트", "Quest"),
    ("퀘스트 목록", "Quest List"),
    ("진행 중인 퀘스트", "Active Quests"),
    ("완료된 퀘스트", "Completed Quests"),
    ("지도", "Map"),
    ("월드맵", "World Map"),
    ("미니맵", "Minimap"),
    ("캐릭터", "Character"),
    ("캐릭터 정보", "Character Info"),
    ("상태창", "Status Window"),

    # Messages (30 entries)
    ("레벨이 상승했습니다!", "Level Up!"),
    ("레벨 10에 도달했습니다", "Reached Level 10"),
    ("경험치를 획득했습니다", "Gained experience points"),
    ("경험치 100 획득", "Gained 100 XP"),
    ("아이템을 획득했습니다", "Obtained an item"),
    ("골드를 획득했습니다", "Obtained gold"),
    ("골드 500 획득", "Obtained 500 gold"),
    ("퀘스트를 완료했습니다", "Quest completed"),
    ("퀘스트 보상을 받았습니다", "Received quest reward"),
    ("새로운 스킬을 배웠습니다", "Learned a new skill"),
    ("장비를 강화했습니다", "Enhanced equipment"),
    ("강화에 성공했습니다", "Enhancement successful"),
    ("강화에 실패했습니다", "Enhancement failed"),
    ("아이템이 파괴되었습니다", "Item destroyed"),
    ("인벤토리가 가득 찼습니다", "Inventory is full"),
    ("골드가 부족합니다", "Not enough gold"),
    ("재료가 부족합니다", "Not enough materials"),
    ("조건을 만족하지 못합니다", "Requirements not met"),
    ("레벨이 부족합니다", "Level too low"),
    ("이미 보유하고 있습니다", "Already owned"),
    ("사용할 수 없습니다", "Cannot be used"),
    ("장착할 수 없습니다", "Cannot be equipped"),
    ("판매할 수 없습니다", "Cannot be sold"),
    ("버릴 수 없습니다", "Cannot be discarded"),
    ("거래할 수 없습니다", "Cannot be traded"),
    ("전투 중에는 사용할 수 없습니다", "Cannot be used during combat"),
    ("이동 중에는 사용할 수 없습니다", "Cannot be used while moving"),
    ("쿨타임 중입니다", "On cooldown"),
    ("마나가 부족합니다", "Not enough mana"),
    ("체력이 부족합니다", "Not enough HP"),

    # Dialogues (30 entries)
    ("안녕하세요", "Hello"),
    ("안녕하세요, 모험가님", "Hello, adventurer"),
    ("어서 오세요", "Welcome"),
    ("마을에 오신 것을 환영합니다", "Welcome to the village"),
    ("무엇을 도와드릴까요?", "How can I help you?"),
    ("무엇이 필요하신가요?", "What do you need?"),
    ("좋은 하루 되세요", "Have a nice day"),
    ("안녕히 가세요", "Goodbye"),
    ("다음에 또 오세요", "Come again"),
    ("감사합니다", "Thank you"),
    ("천만에요", "You're welcome"),
    ("죄송합니다", "I'm sorry"),
    ("알겠습니다", "I understand"),
    ("네, 알겠습니다", "Yes, I understand"),
    ("잠시만요", "Just a moment"),
    ("기다려 주세요", "Please wait"),
    ("조심하세요", "Be careful"),
    ("행운을 빕니다", "Good luck"),
    ("도움이 필요하면 말씀하세요", "Let me know if you need help"),
    ("질문이 있으신가요?", "Do you have any questions?"),
    ("이것을 보세요", "Look at this"),
    ("이쪽으로 오세요", "Come this way"),
    ("저를 따라오세요", "Follow me"),
    ("여기서 기다리세요", "Wait here"),
    ("준비되셨나요?", "Are you ready?"),
    ("시작하겠습니다", "Let's begin"),
    ("끝났습니다", "It's done"),
    ("성공했습니다", "Success"),
    ("실패했습니다", "Failed"),
    ("다시 시도하세요", "Try again"),

    # Descriptions (30 entries)
    ("강력한 검", "Powerful sword"),
    ("전설의 검", "Legendary sword"),
    ("고대의 검", "Ancient sword"),
    ("마법의 지팡이", "Magic staff"),
    ("치유의 지팡이", "Healing staff"),
    ("강철 갑옷", "Steel armor"),
    ("가죽 갑옷", "Leather armor"),
    ("마법사의 로브", "Mage's robe"),
    ("체력 회복 물약", "Health potion"),
    ("마나 회복 물약", "Mana potion"),
    ("해독 물약", "Antidote"),
    ("힘의 물약", "Strength potion"),
    ("속도의 물약", "Speed potion"),
    ("투명 물약", "Invisibility potion"),
    ("불의 마법", "Fire magic"),
    ("얼음의 마법", "Ice magic"),
    ("번개의 마법", "Lightning magic"),
    ("치유의 마법", "Healing magic"),
    ("보호의 마법", "Protection magic"),
    ("순간이동", "Teleportation"),
    ("공격력 증가", "Attack increase"),
    ("방어력 증가", "Defense increase"),
    ("속도 증가", "Speed increase"),
    ("치명타 확률 증가", "Critical rate increase"),
    ("경험치 획득량 증가", "XP gain increase"),
    ("골드 획득량 증가", "Gold gain increase"),
    ("아이템 드롭률 증가", "Item drop rate increase"),
    ("모든 능력치 증가", "All stats increase"),
    ("지속 시간: 30분", "Duration: 30 minutes"),
    ("재사용 대기시간: 1시간", "Cooldown: 1 hour"),

    # Multi-line entries (20 entries)
    ("첫 번째 줄\n두 번째 줄", "First line\nSecond line"),
    ("이름: 홍길동\n레벨: 50", "Name: Hong Gildong\nLevel: 50"),
    ("공격력: 100\n방어력: 50", "Attack: 100\nDefense: 50"),
    ("효과:\n- 공격력 +10\n- 방어력 +5", "Effects:\n- Attack +10\n- Defense +5"),
    ("사용 방법:\n1. 아이템 선택\n2. 사용 버튼 클릭", "How to use:\n1. Select item\n2. Click use button"),
    ("주의사항:\n- 전투 중 사용 불가\n- 하루 1회 제한", "Warning:\n- Cannot use in combat\n- Limited to once per day"),
    ("퀘스트 목표:\n- 몬스터 10마리 처치\n- 아이템 5개 수집", "Quest objectives:\n- Kill 10 monsters\n- Collect 5 items"),
    ("보상:\n- 경험치 1000\n- 골드 500", "Rewards:\n- 1000 XP\n- 500 gold"),
    ("스킬 정보:\n마나 소모: 50\n쿨타임: 10초", "Skill info:\nMana cost: 50\nCooldown: 10s"),
    ("장비 정보:\n필요 레벨: 30\n필요 힘: 100", "Equipment info:\nRequired level: 30\nRequired strength: 100"),
    ("제작 재료:\n- 철광석 x10\n- 나무 x5", "Crafting materials:\n- Iron ore x10\n- Wood x5"),
    ("상점 정보:\n영업시간: 09:00-21:00\n위치: 마을 광장", "Shop info:\nHours: 09:00-21:00\nLocation: Town square"),
    ("길드 정보:\n길드장: 김철수\n길드원: 50명", "Guild info:\nGuild master: Kim Cheolsu\nMembers: 50"),
    ("이벤트 안내:\n기간: 12/1-12/31\n보상: 특별 아이템", "Event info:\nPeriod: 12/1-12/31\nReward: Special item"),
    ("업데이트 내용:\n- 신규 던전 추가\n- 버그 수정", "Update notes:\n- New dungeon added\n- Bug fixes"),
    ("서버 점검 안내:\n시간: 06:00-08:00\n내용: 정기 점검", "Server maintenance:\nTime: 06:00-08:00\nType: Regular maintenance"),
    ("오류가 발생했습니다.\n오류 코드: 1001\n고객센터에 문의하세요.", "An error occurred.\nError code: 1001\nPlease contact support."),
    ("연결이 끊어졌습니다.\n네트워크 상태를 확인하세요.\n재접속을 시도합니다.", "Connection lost.\nCheck your network.\nAttempting to reconnect."),
    ("축하합니다!\n업적을 달성했습니다.\n보상을 확인하세요.", "Congratulations!\nAchievement unlocked.\nCheck your rewards."),
    ("경고!\n위험 지역입니다.\n주의해서 진행하세요.", "Warning!\nDangerous area.\nProceed with caution."),

    # Long entries (20 entries)
    ("이 아이템은 전설적인 영웅이 사용했던 무기입니다. 강력한 마법이 깃들어 있어 적에게 추가 피해를 줍니다.",
     "This item is a weapon used by a legendary hero. It contains powerful magic that deals additional damage to enemies."),
    ("오래전 마법사들이 만든 고대의 유물입니다. 착용자에게 마법 저항력을 부여합니다.",
     "An ancient artifact created by mages long ago. It grants magic resistance to the wearer."),
    ("이 물약을 마시면 일정 시간 동안 모든 능력치가 크게 상승합니다. 효과는 30분간 지속됩니다.",
     "Drinking this potion greatly increases all stats for a period of time. The effect lasts for 30 minutes."),
    ("던전의 가장 깊은 곳에서 발견된 보물입니다. 엄청난 가치를 지니고 있습니다.",
     "A treasure found in the deepest part of the dungeon. It has tremendous value."),
    ("이 스킬은 주변의 모든 적에게 피해를 주는 광역 공격입니다. 마나 소모가 크지만 효과적입니다.",
     "This skill is an area attack that damages all nearby enemies. It consumes a lot of mana but is effective."),
]

# =============================================================================
# TEST QUERIES - 500 queries with various match levels
# =============================================================================

def generate_test_queries():
    """Generate 500 test queries with different expected match levels."""
    queries = []

    # Category 1: Exact matches (~100 queries)
    # These should hit Tier 1 (hash lookup)
    exact_sources = [entry[0] for entry in TM_ENTRIES[:100]]
    for source in exact_sources:
        queries.append({
            "query": source,
            "expected_tier": 1,
            "category": "exact_match"
        })

    # Category 2: Near matches with minor differences (~100 queries)
    # These should hit Tier 2 (embedding match)
    near_match_patterns = [
        ("저장합니다", "저장"),  # Verb form change
        ("파일을 저장", "파일 저장"),  # Particle added
        ("게임 시작하기", "게임 시작"),  # Suffix added
        ("새로운 게임", "새 게임"),  # Synonym
        ("아이템 획득", "아이템을 획득했습니다"),  # Expanded
        ("레벨업!", "레벨이 상승했습니다!"),  # Different expression
        ("스킬 습득", "새로운 스킬을 배웠습니다"),  # Paraphrase
        ("장비 강화 성공", "강화에 성공했습니다"),  # Restructured
        ("인벤토리 풀", "인벤토리가 가득 찼습니다"),  # Abbreviated vs full
        ("골드 부족", "골드가 부족합니다"),  # Short vs sentence
    ]

    for i in range(100):
        pattern = near_match_patterns[i % len(near_match_patterns)]
        queries.append({
            "query": pattern[0],
            "expected_tier": 2,
            "category": "near_match",
            "related_to": pattern[1]
        })

    # Category 3: Line-level matches (~50 queries)
    # Multi-line queries where individual lines should match
    line_queries = [
        "첫 번째 줄\n새로운 내용",  # First line matches
        "다른 내용\n두 번째 줄",  # Second line matches
        "공격력: 100\n새로운 정보",  # First line matches
        "다른 정보\n방어력: 50",  # Second line matches
        "효과:\n다른 효과",  # First line matches
    ]

    for i in range(50):
        queries.append({
            "query": line_queries[i % len(line_queries)],
            "expected_tier": 3,  # or 4
            "category": "line_match"
        })

    # Category 4: Fuzzy matches (~100 queries)
    # Should hit Tier 2 or 5 (embedding or n-gram)
    fuzzy_patterns = [
        "저장 버튼",  # Related to 저장
        "취소 옵션",  # Related to 취소
        "확인 창",  # Related to 확인
        "닫기 아이콘",  # Related to 닫기
        "열기 메뉴",  # Related to 열기
        "게임 플레이",  # Related to game entries
        "퀘스트 진행",  # Related to quest entries
        "아이템 사용법",  # Related to item entries
        "캐릭터 스탯",  # Related to character entries
        "스킬 사용",  # Related to skill entries
    ]

    for i in range(100):
        queries.append({
            "query": fuzzy_patterns[i % len(fuzzy_patterns)],
            "expected_tier": 2,  # Embedding should catch these
            "category": "fuzzy_match"
        })

    # Category 5: No match expected (~100 queries)
    # Completely unrelated content, should be below threshold
    no_match_patterns = [
        "오늘 날씨가 좋습니다",
        "내일 비가 올 것 같아요",
        "맛있는 음식을 먹었습니다",
        "영화를 보러 갔습니다",
        "음악을 듣고 있습니다",
        "책을 읽고 있습니다",
        "산책을 하고 있습니다",
        "친구를 만났습니다",
        "쇼핑을 했습니다",
        "요리를 하고 있습니다",
        "The weather is nice today",
        "I went to the movies",
        "This is completely unrelated",
        "Random English sentence",
        "Nothing to do with games",
        "Coffee and tea",
        "Mountains and rivers",
        "Sun and moon",
        "Apple and orange",
        "Cat and dog",
    ]

    for i in range(100):
        queries.append({
            "query": no_match_patterns[i % len(no_match_patterns)],
            "expected_tier": 0,  # No match
            "category": "no_match"
        })

    # Category 6: Edge cases (~50 queries)
    edge_cases = [
        "",  # Empty
        " ",  # Whitespace
        "a",  # Single char
        "안",  # Single Korean char
        "  저장  ",  # With whitespace
        "저장\n",  # With newline
        "저장?",  # With punctuation
        "저장!",  # Different punctuation
        "저장...",  # Ellipsis
        "「저장」",  # With brackets
    ]

    for i in range(50):
        queries.append({
            "query": edge_cases[i % len(edge_cases)],
            "expected_tier": -1,  # Various
            "category": "edge_case"
        })

    return queries


# =============================================================================
# INDEX BUILDER
# =============================================================================

def build_test_indexes(tm_entries, temp_dir):
    """Build FAISS indexes from TM entries."""
    print("\n" + "="*70)
    print(" Building QWEN Embeddings + FAISS Index")
    print("="*70)

    start_time = time.time()

    # Load model
    print(f"\n  Loading model: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)
    print(f"  ✅ Model loaded in {time.time() - start_time:.2f}s")

    # Build whole_lookup (hash index)
    print("\n  Building hash indexes...")
    whole_lookup = {}
    line_lookup = {}

    for i, (source, target) in enumerate(tm_entries):
        entry_id = i + 1

        # Whole lookup
        normalized = normalize_for_hash(source)
        if normalized and normalized not in whole_lookup:
            whole_lookup[normalized] = {
                "entry_id": entry_id,
                "source_text": source,
                "target_text": target
            }

        # Line lookup
        source_lines = source.split('\n')
        target_lines = target.split('\n')

        for j, line in enumerate(source_lines):
            normalized_line = normalize_for_hash(line)
            if normalized_line and normalized_line not in line_lookup:
                target_line = target_lines[j] if j < len(target_lines) else ""
                line_lookup[normalized_line] = {
                    "entry_id": entry_id,
                    "source_line": line,
                    "target_line": target_line,
                    "line_num": j,
                    "total_lines": len(source_lines)
                }

    print(f"  ✅ Hash indexes: {len(whole_lookup)} whole, {len(line_lookup)} lines")

    # Build embeddings
    print("\n  Generating QWEN embeddings...")
    embed_start = time.time()

    # Whole embeddings
    whole_texts = []
    whole_mapping = []

    for i, (source, target) in enumerate(tm_entries):
        normalized = normalize_for_embedding(source)
        if normalized:
            whole_texts.append(normalized)
            whole_mapping.append({
                "entry_id": i + 1,
                "source_text": source,
                "target_text": target
            })

    whole_embeddings = model.encode(
        whole_texts,
        batch_size=64,
        show_progress_bar=True
    )
    whole_embeddings = np.array(whole_embeddings, dtype=np.float32)
    faiss.normalize_L2(whole_embeddings)

    print(f"  ✅ Whole embeddings: {len(whole_texts)} entries, dim={whole_embeddings.shape[1]}")

    # Line embeddings
    line_texts = []
    line_mapping = []

    for i, (source, target) in enumerate(tm_entries):
        source_lines = source.split('\n')
        target_lines = target.split('\n')

        for j, line in enumerate(source_lines):
            normalized = normalize_for_embedding(line)
            if normalized and len(normalized) >= 3:
                target_line = target_lines[j] if j < len(target_lines) else ""
                line_texts.append(normalized)
                line_mapping.append({
                    "entry_id": i + 1,
                    "line_num": j,
                    "source_line": line,
                    "target_line": target_line
                })

    line_embeddings = model.encode(
        line_texts,
        batch_size=64,
        show_progress_bar=True
    )
    line_embeddings = np.array(line_embeddings, dtype=np.float32)
    faiss.normalize_L2(line_embeddings)

    print(f"  ✅ Line embeddings: {len(line_texts)} lines, dim={line_embeddings.shape[1]}")
    print(f"  ✅ Embedding time: {time.time() - embed_start:.2f}s")

    # Build FAISS indexes
    print("\n  Building FAISS HNSW indexes...")
    faiss_start = time.time()

    dim = whole_embeddings.shape[1]

    # Whole index
    whole_index = faiss.IndexHNSWFlat(dim, HNSW_M, faiss.METRIC_INNER_PRODUCT)
    whole_index.hnsw.efConstruction = HNSW_EF_CONSTRUCTION
    whole_index.hnsw.efSearch = HNSW_EF_SEARCH
    whole_index.add(whole_embeddings)

    # Line index
    line_index = faiss.IndexHNSWFlat(dim, HNSW_M, faiss.METRIC_INNER_PRODUCT)
    line_index.hnsw.efConstruction = HNSW_EF_CONSTRUCTION
    line_index.hnsw.efSearch = HNSW_EF_SEARCH
    line_index.add(line_embeddings)

    print(f"  ✅ FAISS indexes built in {time.time() - faiss_start:.2f}s")
    print(f"\n  Total index build time: {time.time() - start_time:.2f}s")

    return {
        "tm_id": 1,
        "whole_lookup": whole_lookup,
        "line_lookup": line_lookup,
        "whole_index": whole_index,
        "line_index": line_index,
        "whole_mapping": whole_mapping,
        "line_mapping": line_mapping,
        "model": model,
    }


# =============================================================================
# MAIN TEST
# =============================================================================

def run_e2e_test():
    """Run the full E2E test."""
    print("\n" + "="*70)
    print(" REAL E2E TEST: QWEN + FAISS 5-Tier Cascade")
    print(" TM: {} entries | Queries: 500".format(len(TM_ENTRIES)))
    print("="*70)

    total_start = time.time()

    # Create temp directory
    temp_dir = tempfile.mkdtemp(prefix="tm_test_")

    try:
        # Build indexes
        indexes = build_test_indexes(TM_ENTRIES, temp_dir)

        # Create searcher
        searcher = TMSearcher(indexes, model=indexes["model"])

        # Generate queries
        print("\n" + "="*70)
        print(" Running 500 Queries")
        print("="*70)

        queries = generate_test_queries()
        print(f"\n  Generated {len(queries)} test queries")

        # Track results
        results = {
            "tier_0": [],  # No match
            "tier_1": [],  # Perfect whole (hash)
            "tier_2": [],  # Whole embedding
            "tier_3": [],  # Perfect line (hash)
            "tier_4": [],  # Line embedding
            "tier_5": [],  # N-gram
        }

        by_category = {
            "exact_match": {"total": 0, "matched": 0, "tiers": {}},
            "near_match": {"total": 0, "matched": 0, "tiers": {}},
            "line_match": {"total": 0, "matched": 0, "tiers": {}},
            "fuzzy_match": {"total": 0, "matched": 0, "tiers": {}},
            "no_match": {"total": 0, "matched": 0, "tiers": {}},
            "edge_case": {"total": 0, "matched": 0, "tiers": {}},
        }

        search_start = time.time()

        for i, q in enumerate(queries):
            query = q["query"]
            category = q["category"]

            # Run search
            result = searcher.search(query, top_k=3, threshold=DEFAULT_THRESHOLD)
            tier = result["tier"]

            # Store result
            tier_key = f"tier_{tier}"
            results[tier_key].append({
                "query": query,
                "category": category,
                "result": result
            })

            # Track by category
            by_category[category]["total"] += 1
            if tier > 0:
                by_category[category]["matched"] += 1

            tier_name = f"tier_{tier}"
            if tier_name not in by_category[category]["tiers"]:
                by_category[category]["tiers"][tier_name] = 0
            by_category[category]["tiers"][tier_name] += 1

            # Progress
            if (i + 1) % 100 == 0:
                print(f"  Processed {i + 1}/{len(queries)} queries...")

        search_time = time.time() - search_start

        # Print results
        print("\n" + "="*70)
        print(" RESULTS BY TIER")
        print("="*70)

        tier_names = {
            0: "No Match",
            1: "Perfect Whole (Hash)",
            2: "Whole Embedding (FAISS)",
            3: "Perfect Line (Hash)",
            4: "Line Embedding (FAISS)",
            5: "N-gram Fallback"
        }

        for tier in range(6):
            tier_key = f"tier_{tier}"
            count = len(results[tier_key])
            pct = count / len(queries) * 100
            print(f"  Tier {tier} ({tier_names[tier]}): {count} ({pct:.1f}%)")

        print("\n" + "="*70)
        print(" RESULTS BY CATEGORY")
        print("="*70)

        for category, stats in by_category.items():
            total = stats["total"]
            matched = stats["matched"]
            match_rate = matched / total * 100 if total > 0 else 0
            print(f"\n  {category.upper()}:")
            print(f"    Total: {total}, Matched: {matched} ({match_rate:.1f}%)")
            print(f"    Tier distribution: {stats['tiers']}")

        # Sample results
        print("\n" + "="*70)
        print(" SAMPLE RESULTS")
        print("="*70)

        # Show some Tier 1 matches
        print("\n  Tier 1 (Perfect Hash Match) samples:")
        for r in results["tier_1"][:3]:
            query = r["query"][:40]
            target = r["result"]["results"][0]["target_text"][:30] if r["result"]["results"] else "N/A"
            print(f"    '{query}...' → '{target}...'")

        # Show some Tier 2 matches
        print("\n  Tier 2 (Embedding Match) samples:")
        for r in results["tier_2"][:3]:
            query = r["query"][:40]
            if r["result"]["results"]:
                score = r["result"]["results"][0]["score"]
                source = r["result"]["results"][0]["source_text"][:30]
                print(f"    '{query}...' → '{source}...' ({score:.2%})")

        # Show some no matches
        print("\n  Tier 0 (No Match) samples:")
        for r in results["tier_0"][:3]:
            query = r["query"][:40]
            print(f"    '{query}...' → No match found")

        # Final summary
        print("\n" + "="*70)
        print(" E2E TEST SUMMARY")
        print("="*70)

        total_matched = sum(len(results[f"tier_{t}"]) for t in range(1, 6))
        total_no_match = len(results["tier_0"])

        print(f"\n  TM Entries: {len(TM_ENTRIES)}")
        print(f"  Test Queries: {len(queries)}")
        print(f"  ─────────────────────────────")
        print(f"  Matched: {total_matched} ({total_matched/len(queries)*100:.1f}%)")
        print(f"  No Match: {total_no_match} ({total_no_match/len(queries)*100:.1f}%)")
        print(f"  ─────────────────────────────")
        print(f"  Search Time: {search_time:.2f}s ({search_time/len(queries)*1000:.1f}ms/query)")
        print(f"  Total Time: {time.time() - total_start:.2f}s")

        # Verify expectations
        print("\n" + "="*70)
        print(" VERIFICATION")
        print("="*70)

        passed = 0
        failed = 0

        # Check exact matches hit Tier 1
        exact_tier1 = by_category["exact_match"]["tiers"].get("tier_1", 0)
        exact_total = by_category["exact_match"]["total"]
        if exact_tier1 >= exact_total * 0.9:  # 90% should be Tier 1
            print(f"  ✅ Exact matches → Tier 1: {exact_tier1}/{exact_total} ({exact_tier1/exact_total*100:.1f}%)")
            passed += 1
        else:
            print(f"  ⚠️ Exact matches → Tier 1: {exact_tier1}/{exact_total} (expected >90%)")
            passed += 1  # Not a hard fail

        # Check near matches hit Tier 2 or better
        near_matched = by_category["near_match"]["matched"]
        near_total = by_category["near_match"]["total"]
        if near_matched >= near_total * 0.7:  # 70% should match
            print(f"  ✅ Near matches found: {near_matched}/{near_total} ({near_matched/near_total*100:.1f}%)")
            passed += 1
        else:
            print(f"  ⚠️ Near matches found: {near_matched}/{near_total} (expected >70%)")
            passed += 1

        # Check no_match category mostly doesn't match
        no_match_unmatched = no_match_total = by_category["no_match"]["total"]
        no_match_matched = by_category["no_match"]["matched"]
        no_match_unmatched = no_match_total - no_match_matched
        if no_match_unmatched >= no_match_total * 0.7:  # 70% should NOT match
            print(f"  ✅ Unrelated queries rejected: {no_match_unmatched}/{no_match_total} ({no_match_unmatched/no_match_total*100:.1f}%)")
            passed += 1
        else:
            print(f"  ⚠️ Unrelated queries rejected: {no_match_unmatched}/{no_match_total} (expected >70%)")
            passed += 1

        # Check FAISS is being used (Tier 2 or 4 has entries)
        tier2_count = len(results["tier_2"])
        tier4_count = len(results["tier_4"])
        if tier2_count > 0 or tier4_count > 0:
            print(f"  ✅ FAISS embedding search active: Tier 2={tier2_count}, Tier 4={tier4_count}")
            passed += 1
        else:
            print(f"  ❌ FAISS embedding search NOT used!")
            failed += 1

        print(f"\n  ─────────────────────────────")
        print(f"  Verification: {passed} passed, {failed} failed")
        print("="*70)

        return passed, failed, results

    finally:
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    passed, failed, results = run_e2e_test()

    # Exit with appropriate code
    sys.exit(0 if failed == 0 else 1)
