#!/usr/bin/env python3
"""Generate the Mock Gamedata Universe for LocaNext v3.0 testing.

Deterministic generator (seed=42) that creates a full StaticInfo folder tree
with realistic XML files, DDS texture stubs, and WEM audio stubs.

All cross-references are guaranteed valid by construction:
- Knowledge entries generated FIRST
- Entities reference knowledge via lookup tables
- SkillTree nodes use StrKey (NOT numeric Key)
- Skills use LearnKnowledgeKey (NOT KnowledgeKey)

Usage:
    python tests/fixtures/mock_gamedata/generate_mock_universe.py
"""
from __future__ import annotations

import random
import shutil
import struct
from pathlib import Path

from lxml import etree

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SEED = 42
OUTPUT_DIR = Path(__file__).parent
STATIC_DIR = OUTPUT_DIR / "StaticInfo"
TEXTURES_DIR = OUTPUT_DIR / "textures"
AUDIO_DIR = OUTPUT_DIR / "audio"

# Template files for binary stubs
DDS_TEMPLATE = TEXTURES_DIR / "character_varon.dds"
WEM_TEMPLATE = AUDIO_DIR / "varon_greeting.wem"

# ---------------------------------------------------------------------------
# Korean text corpus
# ---------------------------------------------------------------------------
KR_CHAR_NAMES = [
    "장로 바론", "전사 키라", "마법사 드라크마르", "정찰병 루네", "대장장이 그림조",
    "상인 하나", "현자 미르", "궁수 세라", "치유사 유라", "기사 카엘",
    "도적 진", "음유시인 아리아", "마녀 노르나", "수호자 벨리온", "연금술사 코르",
    "사냥꾼 타카", "검투사 렉스", "주술사 오카", "무희 리나", "학자 에이든",
    "용기사 드레이크", "암살자 실바", "성기사 루미아", "광전사 그론", "소환사 에바",
    "마검사 카이", "해적 모건", "수도승 첸", "사령술사 다크", "점술사 비안카",
    "방랑자 로이", "대마법사 아크", "용병 크롬", "제사장 노바", "탐험가 마르코",
]

KR_CHAR_DESCS = [
    "오래된 마을의 수호자.<br/>전쟁을 피해 은둔 중이다.",
    "북부 전초기지에서 온 용맹한 전사.<br/>검은별의 비밀을 추적하고 있다.",
    "고대의 지식을 탐구하는 마법사.<br/>금지된 마법의 위험성을 경고한다.",
    "숲의 길을 아는 정찰병.<br/>위험한 지역을 안전하게 안내한다.",
    "전설적인 무기를 만드는 장인.<br/>검은별 금속의 비밀을 알고 있다.",
    "떠돌이 상인으로 희귀한 물건을 취급한다.",
    "고대 문헌을 해독하는 현자.<br/>잊혀진 언어를 유일하게 읽을 수 있다.",
    "정밀한 활솜씨로 유명한 궁수.<br/>백발백중의 실력을 자랑한다.",
    "신성한 힘으로 부상자를 치유한다.<br/>전장의 수호천사로 불린다.",
    "왕국의 정예 기사단 출신.<br/>명예를 위해 싸운다.",
    "어둠 속에서 활동하는 도적.<br/>정보 수집에 능하다.",
    "전설의 노래를 부르는 음유시인.<br/>그의 노래에는 마법이 깃들어 있다.",
    "금지된 마법을 연구하는 마녀.<br/>위험하지만 강력한 동맹이다.",
    "성벽을 지키는 수호자.<br/>어떤 적도 뚫지 못하는 방어를 자랑한다.",
    "다양한 약물을 제조하는 연금술사.<br/>치료제부터 독약까지 만들 수 있다.",
    "산야를 누비는 노련한 사냥꾼.<br/>야생 동물의 습성을 꿰뚫고 있다.",
    "투기장의 챔피언인 검투사.<br/>관중들의 열광적인 지지를 받는다.",
    "정령과 교감하는 주술사.<br/>자연의 힘을 다룬다.",
    "매혹적인 춤으로 적을 현혹시키는 무희.<br/>춤에는 전투 기술이 숨겨져 있다.",
    "방대한 지식을 가진 학자.<br/>모든 것을 기록하는 습관이 있다.",
    "용을 타고 하늘을 나는 기사.<br/>하늘의 패권을 장악하고 있다.",
    "그림자처럼 움직이는 암살자.<br/>표적은 결코 벗어날 수 없다.",
    "빛의 힘으로 악을 물리치는 성기사.<br/>정의를 위해 헌신한다.",
    "분노의 힘으로 싸우는 광전사.<br/>전투에서 두려움을 모른다.",
    "이계의 존재를 소환하는 마법사.<br/>소환수와 정신적 유대를 맺는다.",
    "마법과 검술을 동시에 구사한다.<br/>두 가지 전투 스타일을 자유롭게 전환한다.",
    "바다를 누비는 해적 선장.<br/>보물 지도를 소유하고 있다.",
    "내면의 기를 수련하는 수도승.<br/>맨손으로 강철을 부순다.",
    "죽은 자의 영혼을 다루는 사령술사.<br/>금기시되는 마법을 사용한다.",
    "별의 움직임으로 미래를 읽는다.<br/>예언의 정확도는 놀라울 정도이다.",
    "정해진 곳 없이 세계를 떠도는 방랑자.<br/>다양한 경험으로 지혜를 얻었다.",
    "마법 탑의 최고 마법사.<br/>마법의 근원을 연구하고 있다.",
    "돈을 위해 싸우는 용병.<br/>의뢰만 완수하면 누구든 고용할 수 있다.",
    "신전의 제사장.<br/>신의 뜻을 전하는 사제이다.",
    "미지의 땅을 탐험하는 모험가.<br/>발견의 기쁨을 위해 산다.",
]

KR_ITEM_TEMPLATES = [
    ("검", "무기"), ("도끼", "무기"), ("창", "무기"), ("활", "무기"), ("단검", "무기"),
    ("지팡이", "무기"), ("석궁", "무기"), ("해머", "무기"), ("낫", "무기"), ("채찍", "무기"),
    ("투구", "방어구"), ("갑옷", "방어구"), ("장갑", "방어구"), ("신발", "방어구"), ("방패", "방어구"),
    ("물약", "소비"), ("주문서", "소비"), ("음식", "소비"), ("폭탄", "소비"), ("부적", "소비"),
    ("반지", "장신구"), ("목걸이", "장신구"), ("귀걸이", "장신구"), ("팔찌", "장신구"), ("벨트", "장신구"),
]

KR_ITEM_PREFIXES = [
    "철", "강철", "미스릴", "아다만", "오리칼쿰",
    "화염", "냉기", "번개", "독", "신성",
    "고대", "전설", "마법", "저주받은", "축복받은",
    "용사", "영웅", "현자", "암흑", "황금",
    "룬", "별빛", "달빛", "태양", "그림자",
]

KR_ITEM_DESCS = [
    "전투에서 유용한 {type}.<br/>장인이 정성껏 제작했다.",
    "강력한 힘이 깃든 {type}.<br/>사용자에게 특별한 능력을 부여한다.",
    "고대 유적에서 발견된 {type}.",
    "희귀한 재료로 만들어진 {type}.<br/>그 가치를 아는 자만이 사용할 수 있다.",
    "전장에서 검증된 {type}.<br/>수많은 전투를 함께한 동반자이다.",
]

KR_SKILL_NAMES = [
    "강타", "회전 베기", "돌진", "방어 자세", "기합",
    "화염구", "냉기 화살", "번개 낙뢰", "치유의 빛", "보호막",
    "은신", "급소 공격", "독침", "연막탄", "추적",
    "소환: 정령", "강화 마법", "저주", "해제", "부활",
    "연타", "관통 사격", "광역 폭발", "집중", "분노 폭발",
    "공중 강습", "지면 강타", "돌풍 베기", "얼음 감옥", "불꽃 폭풍",
    "그림자 이동", "독안개", "생명 흡수", "마나 흡수", "시간 정지",
    "용의 숨결", "성스러운 일격", "암흑 파동", "바람의 칼날", "대지의 힘",
    "번개 연쇄", "빙결 폭풍", "화염 벽", "치유의 비", "수호의 결계",
    "질풍 연무", "천둥 강타", "극대 마법", "환영 분신", "최후의 일격",
    "폭풍 사격", "연속 자상", "회복 명상", "전투 함성", "축복의 기도",
]

KR_SKILL_DESCS = [
    "강력한 일격을 가한다.<br/>적에게 큰 피해를 준다.",
    "회전하며 주변의 적을 공격한다.",
    "전방으로 돌진하여 적을 밀어낸다.<br/>이동과 공격을 동시에 수행한다.",
    "방어 태세를 취하여 받는 피해를 줄인다.",
    "정신을 집중하여 능력치를 일시적으로 상승시킨다.<br/>집중력이 높을수록 효과가 크다.",
    "불타는 화염구를 발사한다.<br/>범위 피해를 입힌다.",
    "얼음 화살을 발사하여 적을 감속시킨다.",
    "하늘에서 번개를 떨어뜨린다.<br/>높은 확률로 기절시킨다.",
    "신성한 빛으로 아군을 치유한다.",
    "마법 보호막을 생성하여 피해를 흡수한다.<br/>지속 시간 동안 피해를 대신 받는다.",
    "그림자 속에 몸을 숨긴다.<br/>이동 속도가 감소하지만 적에게 발견되지 않는다.",
    "적의 약점을 정확히 공격한다.<br/>치명타 확률이 크게 증가한다.",
    "독이 묻은 침을 발사한다.",
    "연막탄을 던져 시야를 가린다.<br/>적의 명중률을 크게 감소시킨다.",
    "표적을 추적하여 이동 속도를 상승시킨다.",
    "정령을 소환하여 함께 전투한다.<br/>소환된 정령은 일정 시간 후 사라진다.",
    "아군에게 강화 마법을 부여한다.",
    "적에게 저주를 걸어 능력치를 감소시킨다.<br/>중첩 가능하다.",
    "부정적인 효과를 해제한다.",
    "쓰러진 아군을 부활시킨다.<br/>부활 후 일정 시간 무적 상태이다.",
]

KR_REGION_NAMES = [
    "검은별 마을", "광명의 전초기지", "용의 둥지", "고대 유적지",
    "수정 동굴", "폭풍의 성", "어둠의 숲", "불사의 탑",
    "황혼의 항구", "잊혀진 사원", "전사의 평원", "마법사의 탑",
    "드워프 광산", "엘프의 숲", "해적의 은신처", "용암 지대",
]

KR_REGION_DESCS = [
    "오래된 역사를 가진 마을.<br/>평화롭지만 위험이 도사리고 있다.",
    "전략적 요충지에 위치한 전초기지.<br/>끊임없는 경계가 필요하다.",
    "고대 용이 잠들어 있는 곳.<br/>용의 보물이 숨겨져 있다는 소문이 있다.",
    "잊혀진 문명의 흔적이 남아 있는 유적지.",
    "아름다운 수정으로 가득한 동굴.<br/>귀중한 광물이 채굴된다.",
    "바람이 끊이지 않는 성.<br/>난공불락의 요새로 알려져 있다.",
    "빛이 닿지 않는 어두운 숲.<br/>위험한 마물들이 서식한다.",
    "죽지 않는 마법사가 지배하는 탑.<br/>들어가면 살아 돌아오기 힘들다.",
    "황혼 무렵 가장 아름다운 항구.<br/>많은 상인들이 모여든다.",
    "신들이 버린 고대의 사원.<br/>아직도 신비한 힘이 남아 있다.",
    "수많은 전투가 벌어진 평원.<br/>전사들의 영혼이 떠돌고 있다.",
    "마법 연구의 중심지인 탑.<br/>입장하려면 마법 능력이 필요하다.",
    "드워프들이 오랫동안 파 온 광산.<br/>깊은 곳에는 알 수 없는 것이 도사린다.",
    "엘프 종족이 대대로 지켜온 성스러운 숲.",
    "해적들의 비밀 근거지.<br/>보물과 위험이 공존하는 곳이다.",
    "끝없이 용암이 흐르는 위험한 지대.<br/>강력한 화염 생물이 서식한다.",
]

KR_GIMMICK_NAMES = [
    "봉인된 문", "보물 상자", "고대 봉인", "비밀 통로", "함정 장치",
    "마법 제단", "수정 기둥", "전이 장치", "마법진", "석상",
    "보물함", "잠긴 금고", "신비한 오벨리스크", "마력 샘", "고대 비석",
    "용의 석상", "제단", "마법 거울", "봉인 장치", "비밀 서가",
    "파괴된 기계", "잠자는 골렘", "저주받은 방패", "불의 제단", "얼음 기둥",
    "고대 레버", "신비한 연못", "전쟁 깃발", "무너진 다리", "마법 수정구",
]

KR_GIMMICK_DESCS = [
    "고대 봉인이 걸려 있다.<br/>열쇠가 필요하다.",
    "오래된 보물이 잠들어 있는 상자.<br/>함정이 설치되어 있을 수 있다.",
    "강력한 마법으로 봉인된 장치.<br/>특별한 주문이 필요하다.",
    "벽 뒤에 숨겨진 비밀 통로.<br/>자세히 살펴보면 발견할 수 있다.",
    "바닥에 설치된 함정.<br/>밟으면 화살이 발사된다.",
]

# English equivalents for item types
ITEM_TYPE_MAP = {
    "무기": "Weapon",
    "방어구": "Armor",
    "소비": "Consumable",
    "장신구": "Accessory",
}

GRADES = ["Common", "Common", "Common", "Uncommon", "Uncommon", "Rare", "Epic", "Legendary"]

JOBS = [
    "Elder", "Warrior", "Sorcerer", "Scout", "Blacksmith",
    "Merchant", "Sage", "Archer", "Healer", "Knight",
    "Rogue", "Bard", "Witch", "Guardian", "Alchemist",
    "Hunter", "Gladiator", "Shaman", "Dancer", "Scholar",
    "Dragon Knight", "Assassin", "Paladin", "Berserker", "Summoner",
    "Spellsword", "Pirate", "Monk", "Necromancer", "Fortune Teller",
    "Wanderer", "Archmage", "Mercenary", "Priest", "Explorer",
]

RACES = ["Human", "Human", "Human", "Elf", "Elf", "Dwarf", "Dwarf", "Beastkin", "Undead", "Demon"]
GENDERS = ["Male", "Female"]

REGION_TYPES = ["Main", "Sub", "Dungeon", "Town", "Fortress", "Wilderness"]


# ---------------------------------------------------------------------------
# Cross-Reference Registry
# ---------------------------------------------------------------------------
class CrossRefRegistry:
    """Track all generated keys for cross-reference validation."""

    def __init__(self) -> None:
        self.knowledge_strkeys: set[str] = set()
        self.item_knowledge_refs: list[tuple[str, str]] = []  # (item_strkey, knowledge_key)
        self.char_knowledge_refs: list[tuple[str, str]] = []
        self.skill_knowledge_refs: list[tuple[str, str]] = []  # uses LearnKnowledgeKey
        self.skilltree_skill_refs: list[tuple[str, str]] = []  # (node_id, skill_strkey)
        self.faction_knowledge_refs: list[tuple[str, str]] = []
        self.texture_refs: list[tuple[str, str]] = []  # (knowledge_strkey, texture_name)
        self.skill_strkeys: set[str] = set()

    def validate(self) -> None:
        """Assert all cross-references resolve."""
        errors = []

        for item_sk, know_key in self.item_knowledge_refs:
            if know_key not in self.knowledge_strkeys:
                errors.append(f"Item {item_sk} -> missing knowledge {know_key}")

        for char_sk, know_key in self.char_knowledge_refs:
            if know_key not in self.knowledge_strkeys:
                errors.append(f"Character {char_sk} -> missing knowledge {know_key}")

        for skill_sk, know_key in self.skill_knowledge_refs:
            if know_key not in self.knowledge_strkeys:
                errors.append(f"Skill {skill_sk} -> missing knowledge {know_key}")

        for node_id, skill_sk in self.skilltree_skill_refs:
            if skill_sk not in self.skill_strkeys:
                errors.append(f"SkillNode {node_id} -> missing skill {skill_sk}")

        for node_sk, know_key in self.faction_knowledge_refs:
            if know_key not in self.knowledge_strkeys:
                errors.append(f"FactionNode {node_sk} -> missing knowledge {know_key}")

        if errors:
            raise AssertionError(
                f"Cross-reference validation failed with {len(errors)} errors:\n"
                + "\n".join(errors[:20])
            )


# ---------------------------------------------------------------------------
# XML Writer
# ---------------------------------------------------------------------------
def write_xml(root: etree._Element, path: Path) -> None:
    """Write XML element tree to file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tree = etree.ElementTree(root)
    tree.write(
        str(path),
        encoding="utf-8",
        xml_declaration=True,
        pretty_print=True,
    )


# ---------------------------------------------------------------------------
# Binary stub creators
# ---------------------------------------------------------------------------
def create_dds_stub(path: Path) -> None:
    """Create minimal valid DDS file by copying template or generating."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if DDS_TEMPLATE.exists():
        shutil.copy2(DDS_TEMPLATE, path)
    else:
        # Fallback: generate 1152-byte DDS
        header = bytearray(128)
        header[0:4] = b"DDS "
        struct.pack_into("<I", header, 4, 124)  # dwSize
        struct.pack_into("<I", header, 8, 0x1007)  # dwFlags
        struct.pack_into("<I", header, 12, 64)  # dwHeight
        struct.pack_into("<I", header, 16, 64)  # dwWidth
        struct.pack_into("<I", header, 20, 256)  # dwPitchOrLinearSize
        struct.pack_into("<I", header, 76, 32)  # ddspf.dwSize
        pixel_data = b"\x00" * 1024
        path.write_bytes(bytes(header) + pixel_data)


def create_wem_stub(path: Path) -> None:
    """Create minimal valid WEM/RIFF file by copying template or generating."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if WEM_TEMPLATE.exists():
        shutil.copy2(WEM_TEMPLATE, path)
    else:
        # Fallback: generate minimal RIFF/WAVE
        sample_rate = 22050
        num_samples = 11025
        data = struct.pack("<H", 0) * num_samples
        fmt_chunk = struct.pack("<4sIHHIIHH",
                                b"fmt ", 16, 1, 1, sample_rate,
                                sample_rate * 2, 2, 16)
        data_chunk = b"data" + struct.pack("<I", len(data)) + data
        riff_size = 4 + len(fmt_chunk) + len(data_chunk)
        header = b"RIFF" + struct.pack("<I", riff_size) + b"WAVE"
        path.write_bytes(header + fmt_chunk + data_chunk)


# ---------------------------------------------------------------------------
# Knowledge Generator
# ---------------------------------------------------------------------------
def generate_knowledge(
    registry: CrossRefRegistry,
    rng: random.Random,
    char_count: int,
    item_count: int,
    region_count: int,
    skill_knowledge_count: int,
) -> dict[str, list[dict]]:
    """Generate knowledge entries for all entity types.

    Returns dict mapping category to list of knowledge dicts.
    Each dict: {strkey, name, desc, ui_texture}
    """
    knowledge: dict[str, list[dict]] = {
        "character": [],
        "item": [],
        "region": [],
        "contents": [],
    }

    # Character knowledge
    for i in range(char_count):
        name = KR_CHAR_NAMES[i % len(KR_CHAR_NAMES)]
        desc = KR_CHAR_DESCS[i % len(KR_CHAR_DESCS)]
        suffix = f"_{i:03d}" if i >= len(KR_CHAR_NAMES) else ""
        strkey = f"KNOW_CHAR_{i + 1:04d}"
        texture = f"character_{i + 1:04d}"
        entry = {"strkey": strkey, "name": name + suffix, "desc": desc, "ui_texture": texture}
        knowledge["character"].append(entry)
        registry.knowledge_strkeys.add(strkey)
        registry.texture_refs.append((strkey, texture))

    # Item knowledge
    for i in range(item_count):
        prefix = KR_ITEM_PREFIXES[i % len(KR_ITEM_PREFIXES)]
        template = KR_ITEM_TEMPLATES[i % len(KR_ITEM_TEMPLATES)]
        name = f"{prefix} {template[0]}"
        desc_template = KR_ITEM_DESCS[i % len(KR_ITEM_DESCS)]
        desc = desc_template.format(type=template[0])
        strkey = f"KNOW_ITEM_{i + 1:04d}"
        texture = f"item_{i + 1:04d}"
        entry = {"strkey": strkey, "name": name, "desc": desc, "ui_texture": texture}
        knowledge["item"].append(entry)
        registry.knowledge_strkeys.add(strkey)
        registry.texture_refs.append((strkey, texture))

    # Region knowledge
    for i in range(region_count):
        name = KR_REGION_NAMES[i % len(KR_REGION_NAMES)]
        desc = KR_REGION_DESCS[i % len(KR_REGION_DESCS)]
        strkey = f"KNOW_REGION_{i + 1:04d}"
        texture = f"region_{i + 1:04d}"
        entry = {"strkey": strkey, "name": name, "desc": desc, "ui_texture": texture}
        knowledge["region"].append(entry)
        registry.knowledge_strkeys.add(strkey)
        registry.texture_refs.append((strkey, texture))

    # Skill/contents knowledge
    for i in range(skill_knowledge_count):
        name = KR_SKILL_NAMES[i % len(KR_SKILL_NAMES)]
        desc = KR_SKILL_DESCS[i % len(KR_SKILL_DESCS)]
        strkey = f"KNOW_SKILL_{i + 1:04d}"
        texture = f"skill_{i + 1:04d}"
        entry = {"strkey": strkey, "name": name, "desc": desc, "ui_texture": texture}
        knowledge["contents"].append(entry)
        registry.knowledge_strkeys.add(strkey)
        registry.texture_refs.append((strkey, texture))

    return knowledge


def write_knowledge_xml(knowledge: dict[str, list[dict]]) -> None:
    """Write 4 knowledge XML files."""
    for category, entries in knowledge.items():
        root = etree.Element("KnowledgeInfoList")
        for entry in entries:
            el = etree.SubElement(root, "KnowledgeInfo")
            el.set("StrKey", entry["strkey"])
            el.set("Name", entry["name"])
            el.set("Desc", entry["desc"])
            el.set("UITextureName", entry["ui_texture"])
        path = STATIC_DIR / "knowledgeinfo" / f"knowledgeinfo_{category}.staticinfo.xml"
        write_xml(root, path)


# ---------------------------------------------------------------------------
# Item Generator
# ---------------------------------------------------------------------------
def generate_items(
    registry: CrossRefRegistry,
    rng: random.Random,
    knowledge_items: list[dict],
    total_count: int,
) -> dict[str, list[etree._Element]]:
    """Generate items across 4 category files."""
    categories = {
        "weapon": [],
        "armor": [],
        "consumable": [],
        "accessory": [],
    }

    category_list = list(categories.keys())

    for i in range(total_count):
        # Determine category
        template_idx = i % len(KR_ITEM_TEMPLATES)
        kr_type = KR_ITEM_TEMPLATES[template_idx][1]
        en_type = ITEM_TYPE_MAP[kr_type]
        cat = en_type.lower()

        key = 10001 + i
        prefix = KR_ITEM_PREFIXES[i % len(KR_ITEM_PREFIXES)]
        kr_template = KR_ITEM_TEMPLATES[template_idx]
        item_name = f"{prefix} {kr_template[0]}"
        strkey = f"STR_ITEM_{i + 1:04d}"

        # Map to knowledge
        know_idx = i % len(knowledge_items)
        knowledge_key = knowledge_items[know_idx]["strkey"]

        desc_template = KR_ITEM_DESCS[i % len(KR_ITEM_DESCS)]
        item_desc = desc_template.format(type=kr_template[0])
        grade = GRADES[rng.randint(0, len(GRADES) - 1)]

        el = etree.Element("ItemInfo")
        el.set("Key", str(key))
        el.set("StrKey", strkey)
        el.set("ItemName", item_name)
        el.set("ItemDesc", item_desc)
        el.set("ItemType", en_type)
        el.set("Grade", grade)
        el.set("KnowledgeKey", knowledge_key)

        categories[cat].append(el)
        registry.item_knowledge_refs.append((strkey, knowledge_key))

    return categories


def write_items_xml(categories: dict[str, list[etree._Element]]) -> None:
    """Write 4 item XML files."""
    for cat_name, items in categories.items():
        root = etree.Element("ItemInfoList")
        for item_el in items:
            root.append(item_el)
        path = STATIC_DIR / "iteminfo" / f"iteminfo_{cat_name}.staticinfo.xml"
        write_xml(root, path)


# ---------------------------------------------------------------------------
# Character Generator
# ---------------------------------------------------------------------------
def generate_characters(
    registry: CrossRefRegistry,
    rng: random.Random,
    knowledge_chars: list[dict],
    total_count: int,
) -> dict[str, list[etree._Element]]:
    """Generate characters across 3 files."""
    categories = {
        "npc": [],
        "npc_shop": [],
        "monster": [],
    }

    for i in range(total_count):
        name = KR_CHAR_NAMES[i % len(KR_CHAR_NAMES)]
        suffix = f"_{i:03d}" if i >= len(KR_CHAR_NAMES) else ""
        en_name = f"Character_{i + 1:04d}"
        strkey = f"STR_CHAR_{i + 1:04d}"

        know_idx = i % len(knowledge_chars)
        knowledge_key = knowledge_chars[know_idx]["strkey"]

        job = JOBS[i % len(JOBS)]
        race = RACES[rng.randint(0, len(RACES) - 1)]
        gender = GENDERS[rng.randint(0, 1)]
        age = rng.randint(15, 500)

        el = etree.Element("CharacterInfo")
        el.set("StrKey", strkey)
        el.set("CharacterName", en_name)
        el.set("KnowledgeKey", knowledge_key)
        el.set("Gender", gender)
        el.set("Age", str(age))
        el.set("Job", job)
        el.set("Race", race)

        # Distribute across categories
        if i < 8:
            categories["npc_shop"].append(el)
        elif i < 22:
            categories["monster"].append(el)
        else:
            categories["npc"].append(el)

        registry.char_knowledge_refs.append((strkey, knowledge_key))

    return categories


def write_characters_xml(categories: dict[str, list[etree._Element]]) -> None:
    """Write 3 character XML files."""
    for cat_name, chars in categories.items():
        root = etree.Element("CharacterInfoList")
        for char_el in chars:
            root.append(char_el)
        path = STATIC_DIR / "characterinfo" / f"characterinfo_{cat_name}.staticinfo.xml"
        write_xml(root, path)


# ---------------------------------------------------------------------------
# Skill Generator
# ---------------------------------------------------------------------------
def generate_skills(
    registry: CrossRefRegistry,
    rng: random.Random,
    knowledge_skills: list[dict],
    total_count: int,
) -> list[dict]:
    """Generate skills. Returns list of skill dicts for SkillTree reference."""
    skills = []

    root = etree.Element("SkillInfoList")

    for i in range(total_count):
        key = 15001 + i
        name = KR_SKILL_NAMES[i % len(KR_SKILL_NAMES)]
        suffix = f"_{i // len(KR_SKILL_NAMES)}" if i >= len(KR_SKILL_NAMES) else ""
        # StrKey uses English-style naming (matching real data pattern)
        strkey = f"Skill_{i + 1:04d}_{name.replace(' ', '_')}"
        desc = KR_SKILL_DESCS[i % len(KR_SKILL_DESCS)]

        know_idx = i % len(knowledge_skills)
        learn_knowledge_key = knowledge_skills[know_idx]["strkey"]

        el = etree.SubElement(root, "SkillInfo")
        el.set("Key", str(key))
        el.set("StrKey", strkey)
        el.set("SkillName", name + suffix)
        el.set("SkillDesc", desc)
        el.set("LearnKnowledgeKey", learn_knowledge_key)

        skills.append({"key": key, "strkey": strkey, "name": name + suffix})
        registry.skill_strkeys.add(strkey)
        registry.skill_knowledge_refs.append((strkey, learn_knowledge_key))

    path = STATIC_DIR / "skillinfo" / "skillinfo_pc.staticinfo.xml"
    write_xml(root, path)
    return skills


# ---------------------------------------------------------------------------
# Skill Tree Generator
# ---------------------------------------------------------------------------
def generate_skill_trees(
    registry: CrossRefRegistry,
    rng: random.Random,
    skills: list[dict],
    tree_count: int,
) -> None:
    """Generate SkillTree XML with SkillNode children referencing SkillInfo.StrKey."""
    root = etree.Element("SkillTreeInfoList")

    tree_names = ["전사 스킬", "마법사 스킬", "궁수 스킬", "도적 스킬", "치유사 스킬",
                  "소환사 스킬", "기사 스킬", "암살자 스킬"]

    skills_per_tree = len(skills) // tree_count
    skill_idx = 0

    for t in range(tree_count):
        tree_el = etree.SubElement(root, "SkillTreeInfo")
        tree_el.set("Key", str(t + 1))
        tree_el.set("StrKey", f"TREE_{t + 1:03d}")
        tree_el.set("CharacterKey", f"CHAR_CLASS_{t + 1:03d}")
        tree_el.set("UIPageName", tree_names[t % len(tree_names)])

        # Add skill nodes
        node_count = skills_per_tree if t < tree_count - 1 else len(skills) - skill_idx
        for n in range(node_count):
            if skill_idx >= len(skills):
                break
            skill = skills[skill_idx]
            node_el = etree.SubElement(tree_el, "SkillNode")
            node_el.set("NodeId", str(n + 1))
            # SkillKey = SkillInfo.StrKey (NOT numeric Key!)
            node_el.set("SkillKey", skill["strkey"])
            node_el.set("ParentNodeId", str(max(0, n)))
            # UIPositionXY for tree layout
            row = n // 4
            col = n % 4
            node_el.set("UIPositionXY", f"{col * 100},{row * 80}")

            registry.skilltree_skill_refs.append((f"TREE_{t + 1}_NODE_{n + 1}", skill["strkey"]))
            skill_idx += 1

    path = STATIC_DIR / "skillinfo" / "SkillTreeInfo.staticinfo.xml"
    write_xml(root, path)


# ---------------------------------------------------------------------------
# Faction / Region Generator
# ---------------------------------------------------------------------------
def generate_factions(
    registry: CrossRefRegistry,
    rng: random.Random,
    knowledge_regions: list[dict],
    node_count: int,
) -> list[dict]:
    """Generate FactionInfo with FactionNode hierarchy and WorldPosition."""
    root = etree.Element("FactionNodeDataList")

    # Create faction groups
    faction_group = etree.SubElement(root, "FactionGroup")
    faction_group.set("GroupName", "모험의 대륙")
    faction_group.set("StrKey", "FGRP_MAIN")

    faction = etree.SubElement(faction_group, "Faction")
    faction.set("Name", "검은별 세력")
    faction.set("StrKey", "FAC_BLACKSTAR")

    nodes = []
    # Generate spatially distributed nodes
    positions_used: list[tuple[float, float]] = []

    for i in range(node_count):
        know_idx = i % len(knowledge_regions)
        knowledge_key = knowledge_regions[know_idx]["strkey"]
        strkey = f"FNODE_{i + 1:04d}"

        # Generate position with minimum separation
        while True:
            x = rng.uniform(500, 5000)
            z = rng.uniform(500, 5000)
            # Check minimum separation from existing nodes
            too_close = False
            for px, pz in positions_used:
                if ((x - px) ** 2 + (z - pz) ** 2) ** 0.5 < 100:
                    too_close = True
                    break
            if not too_close:
                break

        positions_used.append((x, z))

        node_el = etree.SubElement(faction, "FactionNode")
        node_el.set("StrKey", strkey)
        node_el.set("KnowledgeKey", knowledge_key)
        node_el.set("WorldPosition", f"{x:.1f},0,{z:.1f}")
        node_el.set("Type", REGION_TYPES[i % len(REGION_TYPES)])

        nodes.append({"strkey": strkey, "x": x, "z": z, "knowledge_key": knowledge_key})
        registry.faction_knowledge_refs.append((strkey, knowledge_key))

    path = STATIC_DIR / "factioninfo" / "FactionInfo.staticinfo.xml"
    write_xml(root, path)

    return nodes


def generate_waypoints(
    rng: random.Random,
    nodes: list[dict],
) -> None:
    """Generate NodeWaypointInfo connecting adjacent FactionNodes."""
    root = etree.Element("NodeWaypointInfoList")

    # Connect sequential pairs of nodes
    for i in range(len(nodes) - 1):
        from_node = nodes[i]
        to_node = nodes[i + 1]

        wp_el = etree.SubElement(root, "NodeWaypointInfo")
        wp_el.set("FromNodeKey", from_node["strkey"])
        wp_el.set("ToNodeKey", to_node["strkey"])

        # Generate 2-4 intermediate waypoints between nodes
        num_waypoints = rng.randint(2, 4)
        for w in range(num_waypoints):
            t = (w + 1) / (num_waypoints + 1)
            wx = from_node["x"] + t * (to_node["x"] - from_node["x"])
            wz = from_node["z"] + t * (to_node["z"] - from_node["z"])
            # Add some random deviation
            wx += rng.uniform(-20, 20)
            wz += rng.uniform(-20, 20)

            pos_el = etree.SubElement(wp_el, "WorldPosition")
            pos_el.set("X", f"{wx:.1f}")
            pos_el.set("Y", "0")
            pos_el.set("Z", f"{wz:.1f}")

    path = STATIC_DIR / "factioninfo" / "NodeWaypointInfo" / "NodeWaypointInfo.staticinfo.xml"
    write_xml(root, path)


# ---------------------------------------------------------------------------
# Gimmick Generator
# ---------------------------------------------------------------------------
def generate_gimmicks(
    rng: random.Random,
    total_count: int,
) -> None:
    """Generate gimmicks across 3 folders with SealData children."""
    folders = {
        "Background": ("Door", []),
        "Item": ("Chest", []),
        "Puzzle": ("Seal", []),
    }

    folder_keys = list(folders.keys())

    for i in range(total_count):
        folder = folder_keys[i % len(folder_keys)]
        _, gimmick_list = folders[folder]

        name = KR_GIMMICK_NAMES[i % len(KR_GIMMICK_NAMES)]
        desc = KR_GIMMICK_DESCS[i % len(KR_GIMMICK_DESCS)]
        strkey = f"GIMM_{i + 1:04d}"
        group_strkey = f"GGRP_{i + 1:04d}"

        gimmick_list.append({
            "strkey": strkey,
            "group_strkey": group_strkey,
            "name": name,
            "desc": desc,
        })

    # Write XML for each folder
    for folder_name, (type_name, gimmick_list) in folders.items():
        root = etree.Element("GimmickGroupInfoList")

        for gimmick in gimmick_list:
            group_el = etree.SubElement(root, "GimmickGroupInfo")
            group_el.set("StrKey", gimmick["group_strkey"])
            group_el.set("GimmickName", gimmick["name"])

            info_el = etree.SubElement(group_el, "GimmickInfo")
            info_el.set("StrKey", gimmick["strkey"])
            info_el.set("GimmickName", gimmick["name"])

            seal_el = etree.SubElement(info_el, "SealData")
            seal_el.set("Desc", gimmick["desc"])

        path = (
            STATIC_DIR
            / "gimmickinfo"
            / folder_name
            / f"GimmickInfo_{folder_name}_{type_name}.staticinfo.xml"
        )
        write_xml(root, path)


# ---------------------------------------------------------------------------
# Binary Stub Generator
# ---------------------------------------------------------------------------
def generate_binary_stubs(
    registry: CrossRefRegistry,
    knowledge: dict[str, list[dict]],
    char_count: int,
) -> None:
    """Generate DDS stubs for all UITextureNames and WEM stubs for voice characters."""
    # DDS stubs: one per UITextureName in KnowledgeInfo
    all_textures: set[str] = set()
    for category, entries in knowledge.items():
        for entry in entries:
            texture = entry["ui_texture"]
            all_textures.add(texture)

    for texture in sorted(all_textures):
        dds_path = TEXTURES_DIR / f"{texture}.dds"
        if not dds_path.exists():
            create_dds_stub(dds_path)

    # WEM stubs: one per voice-acted character (first 15+)
    voice_count = min(char_count, 18)  # 18 voice-acted characters
    for i in range(voice_count):
        wem_name = f"character_{i + 1:04d}_voice.wem"
        wem_path = AUDIO_DIR / wem_name
        if not wem_path.exists():
            create_wem_stub(wem_path)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    """Generate the complete mock gamedata universe."""
    rng = random.Random(SEED)

    # Volume targets
    ITEM_COUNT = 125
    CHAR_COUNT = 38
    SKILL_COUNT = 56
    KNOWLEDGE_CHAR_COUNT = 36
    KNOWLEDGE_ITEM_COUNT = 30
    KNOWLEDGE_REGION_COUNT = 14
    KNOWLEDGE_SKILL_COUNT = 12
    REGION_NODE_COUNT = 14
    GIMMICK_COUNT = 27
    SKILL_TREE_COUNT = 6

    print(f"Generating Mock Gamedata Universe (seed={SEED})...")
    print(f"  Items: {ITEM_COUNT}")
    print(f"  Characters: {CHAR_COUNT}")
    print(f"  Skills: {SKILL_COUNT}")
    print(f"  Knowledge: {KNOWLEDGE_CHAR_COUNT + KNOWLEDGE_ITEM_COUNT + KNOWLEDGE_REGION_COUNT + KNOWLEDGE_SKILL_COUNT}")
    print(f"  Regions: {REGION_NODE_COUNT}")
    print(f"  Gimmicks: {GIMMICK_COUNT}")
    print(f"  Skill Trees: {SKILL_TREE_COUNT}")

    registry = CrossRefRegistry()

    # Step 1: Generate Knowledge FIRST
    print("\n[1/8] Generating Knowledge entries...")
    knowledge = generate_knowledge(
        registry, rng,
        char_count=KNOWLEDGE_CHAR_COUNT,
        item_count=KNOWLEDGE_ITEM_COUNT,
        region_count=KNOWLEDGE_REGION_COUNT,
        skill_knowledge_count=KNOWLEDGE_SKILL_COUNT,
    )
    write_knowledge_xml(knowledge)
    total_knowledge = sum(len(v) for v in knowledge.values())
    print(f"  -> {total_knowledge} knowledge entries across 4 files")

    # Step 2: Generate Items
    print("[2/8] Generating Items...")
    item_categories = generate_items(registry, rng, knowledge["item"], ITEM_COUNT)
    write_items_xml(item_categories)
    total_items = sum(len(v) for v in item_categories.values())
    print(f"  -> {total_items} items across 4 files")

    # Step 3: Generate Characters
    print("[3/8] Generating Characters...")
    char_categories = generate_characters(registry, rng, knowledge["character"], CHAR_COUNT)
    write_characters_xml(char_categories)
    total_chars = sum(len(v) for v in char_categories.values())
    print(f"  -> {total_chars} characters across 3 files")

    # Step 4: Generate Skills
    print("[4/8] Generating Skills...")
    skills = generate_skills(registry, rng, knowledge["contents"], SKILL_COUNT)
    print(f"  -> {len(skills)} skills in 1 file")

    # Step 5: Generate Skill Trees
    print("[5/8] Generating Skill Trees...")
    generate_skill_trees(registry, rng, skills, SKILL_TREE_COUNT)
    print(f"  -> {SKILL_TREE_COUNT} skill trees")

    # Step 6: Generate Factions/Regions
    print("[6/8] Generating Factions/Regions...")
    nodes = generate_factions(registry, rng, knowledge["region"], REGION_NODE_COUNT)
    generate_waypoints(rng, nodes)
    print(f"  -> {len(nodes)} faction nodes + waypoints")

    # Step 7: Generate Gimmicks
    print("[7/8] Generating Gimmicks...")
    generate_gimmicks(rng, GIMMICK_COUNT)
    print(f"  -> {GIMMICK_COUNT} gimmicks across 3 folders")

    # Step 8: Generate Binary Stubs
    print("[8/8] Generating Binary Stubs...")
    generate_binary_stubs(registry, knowledge, CHAR_COUNT)
    dds_count = len(list(TEXTURES_DIR.glob("*.dds")))
    wem_count = len(list(AUDIO_DIR.glob("*.wem")))
    print(f"  -> {dds_count} DDS stubs, {wem_count} WEM stubs")

    # Validate cross-references
    print("\nValidating cross-references...")
    registry.validate()
    print("  -> All cross-references valid!")

    # Summary
    print(f"\nGeneration complete!")
    print(f"  Knowledge: {total_knowledge}")
    print(f"  Items: {total_items}")
    print(f"  Characters: {total_chars}")
    print(f"  Skills: {len(skills)}")
    print(f"  Skill Trees: {SKILL_TREE_COUNT}")
    print(f"  Faction Nodes: {len(nodes)}")
    print(f"  Gimmicks: {GIMMICK_COUNT}")
    print(f"  DDS Stubs: {dds_count}")
    print(f"  WEM Stubs: {wem_count}")
    xml_count = len(list(STATIC_DIR.rglob("*.xml")))
    print(f"  XML Files: {xml_count}")


if __name__ == "__main__":
    main()
