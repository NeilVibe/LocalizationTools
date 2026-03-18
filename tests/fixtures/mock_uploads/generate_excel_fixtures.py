#!/usr/bin/env python3
"""Generate EU 14-column Excel upload fixtures for API E2E testing.

EU 14-column format:
StrOrigin | ENG | Str | Correction | Text State | STATUS | COMMENT | MEMO1 | MEMO2 | Category | FileName | StringID | DescOrigin | Desc

Uses xlsxwriter for writing (project convention).
"""
from __future__ import annotations

import os
import xlsxwriter

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

EU_HEADERS = [
    "StrOrigin", "ENG", "Str", "Correction", "Text State",
    "STATUS", "COMMENT", "MEMO1", "MEMO2", "Category",
    "FileName", "StringID", "DescOrigin", "Desc",
]

STATUSES = ["New", "Reviewed", "Approved", "In Progress", "Final"]
TEXT_STATES = ["Current", "Modified", "New", "Deprecated"]
CATEGORIES = ["Items", "Characters", "Skills", "Quests", "UI", "System"]
FILENAMES = [
    "iteminfo_weapon.staticinfo.xml",
    "iteminfo_armor.staticinfo.xml",
    "characterinfo.staticinfo.xml",
    "skillinfo.staticinfo.xml",
    "questinfo.staticinfo.xml",
]


def _write_headers(ws: xlsxwriter.Workbook.worksheet_class) -> None:
    for col, h in enumerate(EU_HEADERS):
        ws.write(0, col, h)


def generate_sample() -> None:
    """eu_14col_sample.xlsx: 50 rows of mixed entity data."""
    path = os.path.join(OUTPUT_DIR, "eu_14col_sample.xlsx")
    wb = xlsxwriter.Workbook(path)
    ws = wb.add_worksheet("Sheet1")
    _write_headers(ws)

    items_kr = [
        ("검은별의 장검", "Blackstar Longsword"),
        ("카란다의 날개", "Karanda's Wing"),
        ("크자카의 단검", "Kzarka's Dagger"),
        ("누베르의 방패", "Nouver's Shield"),
        ("쿠툼의 갑옷", "Kutum's Armor"),
        ("오가의 반지", "Ogre's Ring"),
        ("바실리스크의 허리띠", "Basilisk's Belt"),
        ("시크리드의 목걸이", "Sicrid's Necklace"),
        ("투발라의 귀걸이", "Tuvala Earring"),
        ("나르실란의 검", "Narsilan Sword"),
    ]
    chars_kr = [
        ("장로 바론", "Elder Varon"),
        ("전사 키라", "Warrior Kira"),
        ("마법사 드라크마르", "Sorcerer Drakmar"),
        ("정찰병 루네", "Scout Rune"),
        ("대장장이 그림죠", "Blacksmith Grimjo"),
        ("상인 하나", "Merchant Hana"),
        ("현자 미르", "Sage Mir"),
        ("궁수 세라", "Archer Sera"),
        ("치유사 유라", "Healer Yura"),
        ("기사 카엘", "Knight Kael"),
    ]
    skills_kr = [
        ("회전 베기", "Spinning Slash"),
        ("폭풍 찌르기", "Storm Thrust"),
        ("마력 폭발", "Mana Explosion"),
        ("그림자 도약", "Shadow Leap"),
        ("신성 방패", "Holy Shield"),
        ("연속 사격", "Rapid Fire"),
        ("독안개", "Poison Fog"),
        ("분노의 일격", "Fury Strike"),
        ("치유의 빛", "Healing Light"),
        ("대지 진동", "Earth Tremor"),
    ]
    quests_kr = [
        ("잃어버린 보물을 찾아서", "In Search of Lost Treasure"),
        ("마을의 위기", "Crisis in the Village"),
        ("고대 유적 탐험", "Ancient Ruins Expedition"),
        ("용의 둥지", "Dragon's Nest"),
        ("어둠의 숲 정화", "Purifying the Dark Forest"),
        ("전쟁의 서막", "Prelude to War"),
        ("비밀 통로 발견", "Secret Passage Discovery"),
        ("마왕의 부활", "Demon King's Revival"),
        ("영웅의 귀환", "Return of the Hero"),
        ("최후의 결전", "Final Battle"),
    ]
    ui_kr = [
        ("저장하시겠습니까?", "Do you want to save?"),
        ("취소", "Cancel"),
        ("확인", "Confirm"),
        ("설정", "Settings"),
        ("로그아웃", "Logout"),
        ("접속 중...", "Connecting..."),
        ("오류가 발생했습니다", "An error occurred"),
        ("데이터를 불러오는 중", "Loading data"),
        ("변경 사항이 저장되었습니다", "Changes saved"),
        ("삭제하시겠습니까?", "Are you sure you want to delete?"),
    ]

    all_data = (
        [(kr, en, "Items", "iteminfo_weapon.staticinfo.xml", f"SID_ITEM_{i+1:04d}") for i, (kr, en) in enumerate(items_kr)]
        + [(kr, en, "Characters", "characterinfo.staticinfo.xml", f"SID_CHAR_{i+1:04d}") for i, (kr, en) in enumerate(chars_kr)]
        + [(kr, en, "Skills", "skillinfo.staticinfo.xml", f"SID_SKILL_{i+1:04d}") for i, (kr, en) in enumerate(skills_kr)]
        + [(kr, en, "Quests", "questinfo.staticinfo.xml", f"SID_QUEST_{i+1:04d}") for i, (kr, en) in enumerate(quests_kr)]
        + [(kr, en, "UI", "iteminfo_armor.staticinfo.xml", f"SID_UI_{i+1:04d}") for i, (kr, en) in enumerate(ui_kr)]
    )

    for row_idx, (kr, en, cat, fname, sid) in enumerate(all_data, start=1):
        status = STATUSES[row_idx % len(STATUSES)]
        text_state = TEXT_STATES[row_idx % len(TEXT_STATES)]
        ws.write(row_idx, 0, kr)            # StrOrigin
        ws.write(row_idx, 1, en)            # ENG
        ws.write(row_idx, 2, en)            # Str (translated)
        ws.write(row_idx, 3, "")            # Correction
        ws.write(row_idx, 4, text_state)    # Text State
        ws.write(row_idx, 5, status)        # STATUS
        ws.write(row_idx, 6, "")            # COMMENT
        ws.write(row_idx, 7, "")            # MEMO1
        ws.write(row_idx, 8, "")            # MEMO2
        ws.write(row_idx, 9, cat)           # Category
        ws.write(row_idx, 10, fname)        # FileName
        ws.write(row_idx, 11, sid)          # StringID
        ws.write(row_idx, 12, "")           # DescOrigin
        ws.write(row_idx, 13, "")           # Desc

    wb.close()
    print(f"Created {path} ({len(all_data)} rows)")


def generate_korean() -> None:
    """eu_14col_korean.xlsx: 30 rows with Korean source, English translation."""
    path = os.path.join(OUTPUT_DIR, "eu_14col_korean.xlsx")
    wb = xlsxwriter.Workbook(path)
    ws = wb.add_worksheet("Sheet1")
    _write_headers(ws)

    # Korean source text with Jamo, CJK chars, special Korean punctuation
    entries = [
        ("용감한 기사의 검", "Brave Knight's Sword", "Items", "SID_KR_0001"),
        ("ㅎㅏㄴ글 조합 테스트", "Hangul Jamo Test", "System", "SID_KR_0002"),
        ("신비로운 마법의 지팡이", "Mysterious Magic Staff", "Items", "SID_KR_0003"),
        ("전설의 용사 이야기", "Tale of the Legendary Hero", "Quests", "SID_KR_0004"),
        ("ㅋㅋㅋ 재미있는 NPC 대사", "LOL Funny NPC Dialogue", "Characters", "SID_KR_0005"),
        ("강력한 스킬: 폭풍의 일격", "Powerful Skill: Storm Strike", "Skills", "SID_KR_0006"),
        ("ㄱㄴㄷㄹㅁㅂㅅㅇ 자음 테스트", "Consonant Jamo Test", "System", "SID_KR_0007"),
        ("ㅏㅓㅗㅜㅡㅣ 모음 테스트", "Vowel Jamo Test", "System", "SID_KR_0008"),
        ("마을 이장님의 부탁", "Village Chief's Request", "Quests", "SID_KR_0009"),
        ("고급 회복 물약 제조법", "Advanced Healing Potion Recipe", "Items", "SID_KR_0010"),
        ("어둠의 숲에서 살아남기", "Surviving the Dark Forest", "Quests", "SID_KR_0011"),
        ("전투력 향상 비법", "Combat Power Enhancement Secret", "Skills", "SID_KR_0012"),
        ("유니크 장비: 천상의 갑옷", "Unique Gear: Celestial Armor", "Items", "SID_KR_0013"),
        ("길드 마스터의 시험", "Guild Master's Trial", "Quests", "SID_KR_0014"),
        ("ㅎㅎ 히든 퀘스트 발견！", "Haha Hidden Quest Found!", "Quests", "SID_KR_0015"),
        ("초월 강화 시스템", "Transcendence Enhancement System", "System", "SID_KR_0016"),
        ("불꽃의 마법사 스킬트리", "Fire Mage Skill Tree", "Skills", "SID_KR_0017"),
        ("무역 상인의 비밀 거래", "Merchant's Secret Deal", "Characters", "SID_KR_0018"),
        ("ㅁㅁ 미확인 아이템", "Unidentified Item", "Items", "SID_KR_0019"),
        ("전설의 대장장이를 만나다", "Meeting the Legendary Blacksmith", "Quests", "SID_KR_0020"),
        ("빙결 마법: 절대영도", "Frost Magic: Absolute Zero", "Skills", "SID_KR_0021"),
        ("고대 문명의 유산", "Legacy of Ancient Civilization", "Quests", "SID_KR_0022"),
        ("기운 회복 포션", "Stamina Recovery Potion", "Items", "SID_KR_0023"),
        ("정령왕의 축복", "Spirit King's Blessing", "Skills", "SID_KR_0024"),
        ("사막의 오아시스 탐험", "Desert Oasis Expedition", "Quests", "SID_KR_0025"),
        ("ㅇㅇ 동의함", "Agreed", "UI", "SID_KR_0026"),
        ("용사여, 일어나라！", "Rise, Hero!", "Characters", "SID_KR_0027"),
        ("최종 보스: 어둠의 군주", "Final Boss: Lord of Darkness", "Characters", "SID_KR_0028"),
        ("특수 효과: 번개 속성", "Special Effect: Lightning Element", "Skills", "SID_KR_0029"),
        ("게임 종료？ 정말이에요？", "Quit Game? Are you sure?", "UI", "SID_KR_0030"),
    ]

    for row_idx, (kr, en, cat, sid) in enumerate(entries, start=1):
        status = STATUSES[row_idx % len(STATUSES)]
        text_state = TEXT_STATES[row_idx % len(TEXT_STATES)]
        ws.write(row_idx, 0, kr)
        ws.write(row_idx, 1, en)
        ws.write(row_idx, 2, en)
        ws.write(row_idx, 3, "")
        ws.write(row_idx, 4, text_state)
        ws.write(row_idx, 5, status)
        ws.write(row_idx, 6, "")
        ws.write(row_idx, 7, "")
        ws.write(row_idx, 8, "")
        ws.write(row_idx, 9, cat)
        ws.write(row_idx, 10, "characterinfo.staticinfo.xml")
        ws.write(row_idx, 11, sid)
        ws.write(row_idx, 12, "")
        ws.write(row_idx, 13, "")

    wb.close()
    print(f"Created {path} ({len(entries)} rows)")


def generate_brtags() -> None:
    """eu_14col_brtags.xlsx: 25 rows with <br/> multiline content."""
    path = os.path.join(OUTPUT_DIR, "eu_14col_brtags.xlsx")
    wb = xlsxwriter.Workbook(path)
    ws = wb.add_worksheet("Sheet1")
    _write_headers(ws)

    # At least 10 rows with 2+ br-tags, all 25 rows have at least 1
    entries = [
        ("전사의 검<br/>공격력 +50", "Warrior's Sword<br/>ATK +50", "SID_BR_0001"),
        ("마법사의 지팡이<br/>마력 +30<br/>주문 속도 +10%", "Mage Staff<br/>Magic +30<br/>Cast Speed +10%", "SID_BR_0002"),
        ("궁수의 활<br/>명중률 +20<br/>치명타 +5%", "Archer's Bow<br/>Accuracy +20<br/>Crit +5%", "SID_BR_0003"),
        ("치유의 물약<br/>체력 500 회복", "Healing Potion<br/>Restores 500 HP", "SID_BR_0004"),
        ("회전 베기 스킬<br/>범위 공격<br/>쿨타임 10초<br/>소모 MP 50", "Spinning Slash<br/>AoE Attack<br/>CD 10s<br/>Cost 50 MP", "SID_BR_0005"),
        ("신성한 방패<br/>방어력 +100<br/>마법 저항 +20", "Holy Shield<br/>DEF +100<br/>Magic Resist +20", "SID_BR_0006"),
        ("고대의 반지<br/>전체 능력치 +5", "Ancient Ring<br/>All Stats +5", "SID_BR_0007"),
        ("독안개 스킬<br/>지속 피해<br/>이동 속도 감소<br/>해독제로 해제", "Poison Fog<br/>DoT Damage<br/>Move Speed Reduction<br/>Cured by Antidote", "SID_BR_0008"),
        ("전설의 갑옷<br/>방어력 +200", "Legendary Armor<br/>DEF +200", "SID_BR_0009"),
        ("분노의 일격<br/>적 기절<br/>추가 피해 200%", "Fury Strike<br/>Stun Enemy<br/>Extra Damage 200%", "SID_BR_0010"),
        ("회복 마법<br/>아군 전체 치유<br/>부활 효과 포함<br/>쿨타임 60초", "Recovery Magic<br/>Heal All Allies<br/>Includes Revive<br/>CD 60s", "SID_BR_0011"),
        ("마왕의 저주<br/>공격력 감소 50%", "Demon Lord's Curse<br/>ATK Decrease 50%", "SID_BR_0012"),
        ("용의 브레스<br/>화염 피해<br/>범위 공격<br/>방어 무시", "Dragon Breath<br/>Fire Damage<br/>AoE<br/>Ignores Defense", "SID_BR_0013"),
        ("텔레포트<br/>지정 위치로 순간이동", "Teleport<br/>Instant move to target location", "SID_BR_0014"),
        ("강화 주문서<br/>성공 확률 30%<br/>실패 시 파괴", "Enhancement Scroll<br/>30% Success Rate<br/>Destroyed on Failure", "SID_BR_0015"),
        ("연금술 제조법<br/>재료: 허브 x5<br/>재료: 물 x3<br/>제작 시간: 10분", "Alchemy Recipe<br/>Material: Herb x5<br/>Material: Water x3<br/>Craft Time: 10min", "SID_BR_0016"),
        ("길드 공지<br/>이번 주 길드전 안내", "Guild Notice<br/>This Week's GvG Info", "SID_BR_0017"),
        ("퀘스트 보상<br/>경험치 10000<br/>금화 500<br/>아이템 상자 1개", "Quest Reward<br/>EXP 10000<br/>Gold 500<br/>Item Box x1", "SID_BR_0018"),
        ("NPC 대사<br/>용사여, 조심하시오!", "NPC Dialogue<br/>Hero, be careful!", "SID_BR_0019"),
        ("시스템 메시지<br/>서버 점검 안내<br/>점검 시간: 04:00-06:00", "System Message<br/>Server Maintenance<br/>Time: 04:00-06:00", "SID_BR_0020"),
        ("장비 설명<br/>착용 조건: 레벨 50 이상<br/>직업 제한: 전사", "Equipment Desc<br/>Requirement: Level 50+<br/>Class: Warrior", "SID_BR_0021"),
        ("업적 달성<br/>처음으로 보스를 처치했습니다!<br/>보상: 칭호 획득", "Achievement<br/>Defeated a boss for the first time!<br/>Reward: Title Earned", "SID_BR_0022"),
        ("펫 정보<br/>이름: 꼬마 용<br/>특기: 아이템 줍기<br/>레벨: 1", "Pet Info<br/>Name: Baby Dragon<br/>Skill: Item Pickup<br/>Level: 1", "SID_BR_0023"),
        ("경매장 안내<br/>등록 수수료 5%", "Auction House<br/>Listing Fee 5%", "SID_BR_0024"),
        ("주의사항<br/>이 작업은 되돌릴 수 없습니다<br/>정말 진행하시겠습니까?", "Warning<br/>This action cannot be undone<br/>Are you sure you want to proceed?", "SID_BR_0025"),
    ]

    for row_idx, (kr, en, sid) in enumerate(entries, start=1):
        status = STATUSES[row_idx % len(STATUSES)]
        text_state = TEXT_STATES[row_idx % len(TEXT_STATES)]
        cat = CATEGORIES[row_idx % len(CATEGORIES)]
        fname = FILENAMES[row_idx % len(FILENAMES)]
        ws.write(row_idx, 0, kr)
        ws.write(row_idx, 1, en)
        ws.write(row_idx, 2, en)
        ws.write(row_idx, 3, "")
        ws.write(row_idx, 4, text_state)
        ws.write(row_idx, 5, status)
        ws.write(row_idx, 6, "")
        ws.write(row_idx, 7, "")
        ws.write(row_idx, 8, "")
        ws.write(row_idx, 9, cat)
        ws.write(row_idx, 10, fname)
        ws.write(row_idx, 11, sid)
        ws.write(row_idx, 12, "")
        ws.write(row_idx, 13, "")

    wb.close()
    print(f"Created {path} ({len(entries)} rows)")


if __name__ == "__main__":
    generate_sample()
    generate_korean()
    generate_brtags()
    print("All Excel fixtures generated.")
