"""
Mock data generator for MegaIndex test fixtures.

Generates ALL XML files, DDS/WEM stubs, and localization data needed to
populate every one of MegaIndex's 35 dictionaries. Idempotent -- re-running
produces identical output.

Usage:
    python tools/generate_mega_index_mockdata.py              # generate only
    python tools/generate_mega_index_mockdata.py --validate   # generate + validate

Quick task: w79-megaindex-mock-data-generator
"""

from __future__ import annotations

import argparse
import struct
import sys
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from PIL import Image

from lxml import etree
from loguru import logger


# =============================================================================
# Registry Definitions (Single Source of Truth)
# =============================================================================


@dataclass
class KnowledgeDef:
    strkey: str
    name_kr: str
    desc_kr: str
    ui_texture: str
    group_key: str = ""
    extra_attrs: Dict[str, str] = field(default_factory=dict)
    devmemo: str = ""


@dataclass
class CharDef:
    strkey: str
    name_kr: str
    name_eng: str
    desc_kr: str
    desc_eng: str
    knowledge_key: str
    source_file: str
    extra_attrs: Dict[str, str] = field(default_factory=dict)


@dataclass
class ItemDef:
    strkey: str
    name_kr: str
    name_eng: str
    desc_kr: str
    desc_eng: str
    knowledge_key: str
    source_file: str
    group_key: str = ""
    extra_attrs: Dict[str, str] = field(default_factory=dict)


@dataclass
class RegionDef:
    strkey: str
    knowledge_key: str
    node_type: str
    world_position: str
    faction: str  # which faction this belongs to
    polygon: str
    display_name: str = ""  # for RegionInfo D16


@dataclass
class SkillDef:
    strkey: str
    name_kr: str
    name_eng: str
    desc_kr: str
    desc_eng: str
    source_file: str
    extra_attrs: Dict[str, str] = field(default_factory=dict)


@dataclass
class GimmickDef:
    strkey: str
    group_strkey: str
    group_name_kr: str
    name_kr: str
    name_eng: str
    desc_kr: str
    desc_eng: str
    seal_desc_kr: str = ""
    seal_desc_eng: str = ""
    source_file: str = "gimmickinfo_showcase.staticinfo.xml"


@dataclass
class AudioDef:
    event_name: str
    stringid: str
    strorigin_kr: str
    str_eng: str
    export_subdir: str
    export_file: str


@dataclass
class FactionDef:
    strkey: str
    name_kr: str
    knowledge_key: str
    region_strkeys: List[str] = field(default_factory=list)


@dataclass
class FactionGroupDef:
    strkey: str
    group_name_kr: str
    knowledge_key: str
    faction_strkeys: List[str] = field(default_factory=list)


@dataclass
class KnowledgeGroupDef:
    strkey: str
    group_name_kr: str
    member_strkeys: List[str] = field(default_factory=list)


@dataclass
class ItemGroupDef:
    strkey: str
    group_name_kr: str
    parent_strkey: str
    item_strkeys: List[str] = field(default_factory=list)


# =============================================================================
# Central Registry -- ALL entity data defined ONCE here
# =============================================================================

# --- Knowledge entries (30 existing + verbatim from XML) ---

KNOWLEDGE: List[KnowledgeDef] = [
    # CHARACTER KNOWLEDGE (5)
    KnowledgeDef(
        strkey="Knowledge_ElderVaron", name_kr="장로 바론",
        desc_kr="고대 봉인의 수호자이자 현자의 결사 창립 멤버.<br/>수천 년간 봉인된 도서관을 지켜온 현자.<br/>그의 지혜는 세계의 균형을 유지하는 열쇠이다.",
        ui_texture="character_varon", group_key="KnowledgeGroup_Character",
        extra_attrs={"isDefault": "False", "CharacterKey": "Character_ElderVaron", "QuestKey": "Quest_SealedLibrary_Main"},
        devmemo="[NPC] 메인 퀘스트 NPC, 봉인 도서관 수호자",
    ),
    KnowledgeDef(
        strkey="Knowledge_ShadowKira", name_kr="그림자 암살자 키라",
        desc_kr="어둠의 교단에서 훈련받은 전설적인 암살자.<br/>그림자 속에서 움직이며 흔적을 남기지 않는다.",
        ui_texture="character_kira", group_key="KnowledgeGroup_Character",
        extra_attrs={"isDefault": "False", "CharacterKey": "Character_ShadowKira"},
    ),
    KnowledgeDef(
        strkey="Knowledge_Grimjaw", name_kr="대장장이 그림죠",
        desc_kr="드워프 종족 최고의 대장장이.<br/>검은별 대검을 비롯한 전설적인 무기들을 단조했다.<br/>현재 봉인된 도서관 근처에서 은둔 중이다.",
        ui_texture="character_grimjaw", group_key="KnowledgeGroup_Character",
        extra_attrs={"isDefault": "False", "CharacterKey": "Character_Grimjaw"},
    ),
    KnowledgeDef(
        strkey="Knowledge_Lune", name_kr="정찰병 루네",
        desc_kr="봉인된 도서관으로 가는 길을 안내하는 엘프 정찰병.<br/>숲의 모든 비밀을 꿰뚫고 있으며<br/>장로 바론의 가장 신뢰하는 동료이다.",
        ui_texture="character_lune", group_key="KnowledgeGroup_Character",
        extra_attrs={"isDefault": "False", "CharacterKey": "Character_Lune"},
    ),
    KnowledgeDef(
        strkey="Knowledge_Drakmar", name_kr="마법사 드라크마르",
        desc_kr="봉인된 도서관의 고대 문서를 해독하는 학자 마법사.<br/>성스러운 방패 마법의 전문가이며<br/>장로 바론의 오른팔 역할을 한다.",
        ui_texture="character_drakmar", group_key="KnowledgeGroup_Character",
        extra_attrs={"isDefault": "False", "CharacterKey": "Character_Drakmar"},
        devmemo="[NPC] 학자 마법사, 고대 문서 해독 전문가",
    ),
    # SKILL KNOWLEDGE (3)
    KnowledgeDef(
        strkey="Knowledge_SacredFlame", name_kr="성스러운 불꽃",
        desc_kr="현자의 결사에서 전승되는 신성한 화염 마법.<br/>어둠의 존재를 정화하는 힘을 지닌다.",
        ui_texture="skill_0001", group_key="KnowledgeGroup_Skill",
        extra_attrs={"isDefault": "True", "LearnApplySkillKey": "Skill_SacredFlame", "CharacterKey": "Character_ElderVaron"},
    ),
    KnowledgeDef(
        strkey="Knowledge_ShadowStrike", name_kr="그림자 일격",
        desc_kr="어둠의 힘을 응축하여 적에게 치명적인 일격을 가한다.<br/>그림자 암살자만이 사용할 수 있는 비전 기술.",
        ui_texture="skill_0002", group_key="KnowledgeGroup_Skill",
        extra_attrs={"isDefault": "True", "LearnApplySkillKey": "Skill_ShadowStrike", "CharacterKey": "Character_ShadowKira"},
    ),
    KnowledgeDef(
        strkey="Knowledge_HolyShield", name_kr="성스러운 방패",
        desc_kr="신성한 빛으로 아군을 보호하는 방어 마법.<br/>모든 어둠의 공격을 일정 시간 무효화한다.",
        ui_texture="skill_0003", group_key="KnowledgeGroup_Skill",
        extra_attrs={"isDefault": "True", "LearnApplySkillKey": "Skill_HolyShield", "CharacterKey": "Character_Grimjaw"},
    ),
    # REGION KNOWLEDGE (10)
    KnowledgeDef(
        strkey="Knowledge_MistForest", name_kr="안개의 숲",
        desc_kr="고대의 안개가 끊이지 않는 신비로운 숲.<br/>숲 속에는 정체를 알 수 없는 생물들이 서식하며<br/>길을 잃기 쉬워 정찰병 루네의 안내가 필수적이다.",
        ui_texture="region_mist_forest", group_key="KnowledgeGroup_Region",
        extra_attrs={"isDefault": "False", "RegionKey": "Region_MistForest"},
    ),
    KnowledgeDef(
        strkey="Knowledge_SealedLibrary", name_kr="봉인된 도서관",
        desc_kr="고대 현자들이 금지된 지식을 봉인한 장소.<br/>강력한 마법 결계로 보호되어 있으며<br/>오직 현자의 결사만이 출입할 수 있다.",
        ui_texture="region_sealed_library", group_key="KnowledgeGroup_Region",
        extra_attrs={"isDefault": "False", "RegionKey": "Region_SealedLibrary"},
        devmemo="[REGION] 메인 던전, 봉인 결계 핵심 장소",
    ),
    KnowledgeDef(
        strkey="Knowledge_BlackstarVillage", name_kr="흑성 마을",
        desc_kr="모험가들의 거점이 되는 평화로운 마을.<br/>검은별 광석이 처음 발견된 곳이며<br/>대장장이 그림죠의 대장간이 있다.",
        ui_texture="region_blackstar_village", group_key="KnowledgeGroup_Region",
        extra_attrs={"isDefault": "False", "RegionKey": "Region_BlackstarVillage"},
    ),
    KnowledgeDef(
        strkey="Knowledge_DragonTomb", name_kr="용의 무덤",
        desc_kr="태고의 용이 잠든 위험한 무덤.<br/>고대의 보물이 잠들어 있지만<br/>강력한 수호 마법이 침입자를 막고 있다.",
        ui_texture="region_dragon_tomb", group_key="KnowledgeGroup_Region",
        extra_attrs={"isDefault": "False", "RegionKey": "Region_DragonTomb"},
    ),
    KnowledgeDef(
        strkey="Knowledge_SageTower", name_kr="현자의 탑",
        desc_kr="세계의 균형을 지키는 현자들의 탑.<br/>현자의 결사 본부이자<br/>장로 바론이 수련하던 신성한 장소이다.",
        ui_texture="region_sage_tower", group_key="KnowledgeGroup_Region",
        extra_attrs={"isDefault": "False", "RegionKey": "Region_SageTower"},
    ),
    KnowledgeDef(
        strkey="Knowledge_DarkCultHQ", name_kr="어둠의 교단 본부",
        desc_kr="어둠의 세력이 모이는 비밀 요새.<br/>그림자 암살자 키라가 훈련받은 곳이며<br/>봉인된 도서관을 향한 음모가 꾸며지는 곳이다.",
        ui_texture="region_dark_cult_hq", group_key="KnowledgeGroup_Region",
        extra_attrs={"isDefault": "False", "RegionKey": "Region_DarkCultHQ"},
    ),
    KnowledgeDef(
        strkey="Knowledge_WindCanyon", name_kr="바람의 협곡",
        desc_kr="거센 바람이 몰아치는 깊은 협곡.<br/>고대의 바람 정령들이 서식하며<br/>숙련된 모험가만이 통과할 수 있다.",
        ui_texture="region_wind_canyon", group_key="KnowledgeGroup_Region",
        extra_attrs={"isDefault": "False", "RegionKey": "Region_WindCanyon"},
    ),
    KnowledgeDef(
        strkey="Knowledge_ForgottenFortress", name_kr="잊힌 요새",
        desc_kr="세월 속에 잊힌 고대의 요새.<br/>한때 현자의 결사의 전초기지였으나<br/>지금은 어둠의 세력이 점령하고 있다.",
        ui_texture="region_forgotten_fortress", group_key="KnowledgeGroup_Region",
        extra_attrs={"isDefault": "False", "RegionKey": "Region_ForgottenFortress"},
    ),
    KnowledgeDef(
        strkey="Knowledge_MoonlightLake", name_kr="달빛 호수",
        desc_kr="달빛에 비추어 빛나는 신성한 호수.<br/>치유의 힘을 지닌 물이 솟아나며<br/>역병 치료제의 핵심 재료를 채취할 수 있다.",
        ui_texture="region_moonlight_lake", group_key="KnowledgeGroup_Region",
        extra_attrs={"isDefault": "False", "RegionKey": "Region_MoonlightLake"},
    ),
    KnowledgeDef(
        strkey="Knowledge_VolcanicZone", name_kr="화산 지대",
        desc_kr="용암이 흐르는 위험한 화산 지대.<br/>검은별 광석의 또 다른 산지이며<br/>극한의 환경 속에서만 발견되는 희귀 광물이 있다.",
        ui_texture="region_volcanic_zone", group_key="KnowledgeGroup_Region",
        extra_attrs={"isDefault": "False", "RegionKey": "Region_VolcanicZone"},
    ),
    # FACTION KNOWLEDGE (2)
    KnowledgeDef(
        strkey="Knowledge_SageOrder", name_kr="현자의 결사",
        desc_kr="세계의 균형을 수호하기 위해 설립된 비밀 조직.<br/>장로 바론이 이끄는 현자들의 연합체이다.",
        ui_texture="region_0001", group_key="KnowledgeGroup_Faction",
        extra_attrs={"isDefault": "False", "FactionKey": "Faction_SageOrder", "CharacterKey": "Character_ElderVaron"},
    ),
    KnowledgeDef(
        strkey="Knowledge_DarkCult", name_kr="어둠의 교단",
        desc_kr="금지된 어둠의 힘을 숭배하는 비밀 교단.<br/>봉인된 도서관의 지식을 탈취하려 한다.",
        ui_texture="region_0002", group_key="KnowledgeGroup_Faction",
        extra_attrs={"isDefault": "False", "FactionKey": "Faction_DarkCult", "CharacterKey": "Character_ShadowKira"},
    ),
    # ITEM KNOWLEDGE (5)
    KnowledgeDef(
        strkey="Knowledge_BlackstarSword", name_kr="검은별 대검",
        desc_kr="전설의 대장장이 그림죠가 검은별 광석으로 단조한 대검.<br/>어둠을 베는 힘과 빛을 담는 힘을 동시에 지닌다.",
        ui_texture="item_blackstar_sword", group_key="KnowledgeGroup_Item",
        extra_attrs={"isDefault": "False", "ItemKey": "Item_BlackstarSword", "CharacterKey": "Character_Grimjaw"},
    ),
    KnowledgeDef(
        strkey="Knowledge_SageStaff", name_kr="현자의 지팡이",
        desc_kr="장로 바론이 소유한 고대 마법 지팡이.<br/>대장장이 그림죠가 제작한 것으로<br/>성스러운 불꽃의 힘을 증폭시킨다.",
        ui_texture="item_0001", group_key="KnowledgeGroup_Item",
        extra_attrs={"isDefault": "False", "ItemKey": "Item_SageStaff", "CharacterKey": "Character_ElderVaron"},
    ),
    KnowledgeDef(
        strkey="Knowledge_ShadowDagger", name_kr="그림자 단검",
        desc_kr="어둠의 교단에서 제작된 저주받은 단검.<br/>그림자 속에서 빛나며<br/>일격에 치명적인 독을 주입한다.",
        ui_texture="item_0002", group_key="KnowledgeGroup_Item",
        extra_attrs={"isDefault": "False", "ItemKey": "Item_ShadowDagger", "CharacterKey": "Character_ShadowKira"},
    ),
    KnowledgeDef(
        strkey="Knowledge_PlagueCure", name_kr="역병 치료제",
        desc_kr="그림자 역병을 치료하는 희귀한 물약.<br/>다섯 지역 모두의 재료가 필요하며<br/>드라크마르만이 유일한 제조법을 알고 있다.",
        ui_texture="item_plague_cure", group_key="KnowledgeGroup_Item",
        extra_attrs={"isDefault": "False", "ItemKey": "Item_PlagueCure", "CharacterKey": "Character_Drakmar"},
    ),
    KnowledgeDef(
        strkey="Knowledge_SealScroll", name_kr="봉인의 두루마리",
        desc_kr="봉인된 도서관의 출입 권한을 부여하는 고대 두루마리.<br/>현자의 결사의 문장이 새겨져 있으며<br/>정찰병 루네가 보관하고 있다.",
        ui_texture="item_0003", group_key="KnowledgeGroup_Item",
        extra_attrs={"isDefault": "False", "ItemKey": "Item_SealScroll", "CharacterKey": "Character_Lune"},
    ),
    # NEW MAP NODE KNOWLEDGE (4)
    KnowledgeDef(
        strkey="Knowledge_TradingPost", name_kr="교역소",
        desc_kr="여러 지역의 상인들이 모여드는 교역 중심지.<br/>봉인된 도서관과 흑성 마을 사이에 위치하여<br/>모험가들의 보급 거점으로 활용되고 있다.",
        ui_texture="region_0001", group_key="KnowledgeGroup_Region",
        extra_attrs={"Key": "KNOW_030", "KnowledgeName": "교역소", "KnowledgeType": "Region", "RegionKey": "Region_TradingPost"},
    ),
    KnowledgeDef(
        strkey="Knowledge_AncientTemple", name_kr="고대 신전",
        desc_kr="잊힌 신들에게 바쳐진 고대 신전.<br/>현자의 결사가 비밀리에 관리하고 있으며<br/>성스러운 불꽃의 원천이 이곳에 잠들어 있다고 전해진다.",
        ui_texture="region_0002", group_key="KnowledgeGroup_Region",
        extra_attrs={"Key": "KNOW_031", "KnowledgeName": "고대 신전", "KnowledgeType": "Region", "RegionKey": "Region_AncientTemple"},
    ),
    KnowledgeDef(
        strkey="Knowledge_Watchtower", name_kr="감시탑",
        desc_kr="어둠의 교단의 움직임을 감시하기 위한 전초 기지.<br/>정찰병 루네가 자주 방문하는 곳으로<br/>안개의 숲과 화산 지대를 한눈에 조망할 수 있다.",
        ui_texture="region_fortress", group_key="KnowledgeGroup_Region",
        extra_attrs={"Key": "KNOW_032", "KnowledgeName": "감시탑", "KnowledgeType": "Region", "RegionKey": "Region_Watchtower"},
        devmemo="[REGION] 전초 기지, 정찰병 루네 활동 거점",
    ),
    KnowledgeDef(
        strkey="Knowledge_MiningCamp", name_kr="광산 캠프",
        desc_kr="검은별 금속을 채굴하는 광산 캠프.<br/>대장장이 그림죠가 이곳에서 채굴된 광석으로<br/>전설적인 무기를 제작한다.",
        ui_texture="region_0001", group_key="KnowledgeGroup_Region",
        extra_attrs={"Key": "KNOW_033", "KnowledgeName": "광산 캠프", "KnowledgeType": "Region", "RegionKey": "Region_MiningCamp"},
    ),
]

# --- Characters (5 existing, verbatim) ---

CHARACTERS: List[CharDef] = [
    CharDef(
        strkey="Character_ElderVaron",
        name_kr="장로 바론", name_eng="Elder Varon",
        desc_kr="봉인된 도서관의 수호자인 장로 바론은 300년이 넘는 세월 동안 고대의 지식을 지켜왔다.<br/>그는 현자의 결사를 이끌며, 성스러운 불꽃의 비밀을 후대에 전수하고 있다.<br/>최근 어둠의 교단이 봉인된 도서관을 노리고 있다는 소문이 돌고 있어, 바론은 경계를 늦추지 않고 있다.",
        desc_eng="Elder Varon has guarded ancient knowledge in the Sealed Library for over 300 years.",
        knowledge_key="Knowledge_ElderVaron",
        source_file="characterinfo_showcase.staticinfo.xml",
        extra_attrs={"Key": "CHAR_001", "CharacterType": "NPC", "Level": "85", "Job": "Sage", "Race": "Human",
                     "Gender": "Male", "Age": "347", "Title": "봉인의 수호자",
                     "UITextureName": "character_varon", "VoicePath": "audio/characters/elder_varon_greeting.wem",
                     "KnowledgeKey": "Knowledge_ElderVaron", "FactionKey": "Faction_SageOrder",
                     "RegionKey": "Region_SealedLibrary", "ItemKey": "Item_SageStaff", "SkillKey": "Skill_SacredFlame"},
    ),
    CharDef(
        strkey="Character_ShadowKira",
        name_kr="그림자 암살자 키라", name_eng="Shadow Assassin Kira",
        desc_kr="어둠의 교단의 최정예 암살자인 키라는 봉인된 도서관의 비밀을 노린다.<br/>그녀의 그림자 일격은 한 번의 공격으로 적을 제압할 수 있는 치명적인 기술이다.<br/>장로 바론과는 오랜 숙적 관계이며, 두 사람의 대결은 게임의 핵심 스토리라인을 이끈다.",
        desc_eng="Kira is the Dark Cult's elite assassin who targets the secrets of the Sealed Library.",
        knowledge_key="Knowledge_ShadowKira",
        source_file="characterinfo_showcase.staticinfo.xml",
        extra_attrs={"Key": "CHAR_002", "CharacterType": "Boss", "Level": "90", "Job": "Assassin", "Race": "Human",
                     "Gender": "Female", "Title": "어둠의 칼날",
                     "UITextureName": "character_kira", "VoicePath": "audio/characters/shadow_kira_taunt.wem",
                     "KnowledgeKey": "Knowledge_ShadowKira", "FactionKey": "Faction_DarkCult",
                     "RegionKey": "Region_SealedLibrary", "ItemKey": "Item_ShadowDagger", "SkillKey": "Skill_ShadowStrike"},
    ),
    CharDef(
        strkey="Character_Grimjaw",
        name_kr="대장장이 그림죠", name_eng="Blacksmith Grimjaw",
        desc_kr="전설의 검은별 금속을 다룰 수 있는 유일한 대장장이.<br/>현자의 결사에 소속되어 있으며, 장로 바론의 현자의 지팡이도 그가 제작한 것이다.<br/>최근 어둠의 교단이 검은별 금속을 노리고 있어 경계를 늦추지 않고 있다.",
        desc_eng="The only blacksmith capable of working legendary Blackstar metal.",
        knowledge_key="Knowledge_Grimjaw",
        source_file="characterinfo_showcase.staticinfo.xml",
        extra_attrs={"Key": "CHAR_003", "CharacterType": "NPC", "Level": "60", "Job": "Blacksmith", "Race": "Dwarf",
                     "Gender": "Male", "Title": "검은별의 장인",
                     "UITextureName": "character_grimjaw", "VoicePath": "audio/characters/grimjaw_forge.wem",
                     "KnowledgeKey": "Knowledge_Grimjaw", "FactionKey": "Faction_SageOrder",
                     "ItemKey": "Item_BlackstarSword", "RegionKey": "Region_BlackstarVillage", "SkillKey": "Skill_HolyShield"},
    ),
    CharDef(
        strkey="Character_Lune",
        name_kr="정찰병 루네", name_eng="Scout Lune",
        desc_kr="봉인된 도서관으로 가는 위험한 길을 안내하는 엘프 정찰병.<br/>숲의 모든 길을 꿰뚫고 있으며, 어둠의 교단의 움직임을 감시하고 있다.<br/>장로 바론을 깊이 존경하며, 그의 명령이라면 어떤 위험도 감수한다.",
        desc_eng="An elf scout who guides travelers through the dangerous path to the Sealed Library.",
        knowledge_key="Knowledge_Lune",
        source_file="characterinfo_showcase.staticinfo.xml",
        extra_attrs={"Key": "CHAR_004", "CharacterType": "NPC", "Level": "45", "Job": "Scout", "Race": "Elf",
                     "Gender": "Female", "Title": "숲의 안내자",
                     "UITextureName": "character_lune", "VoicePath": "audio/characters/lune_whisper.wem",
                     "KnowledgeKey": "Knowledge_Lune", "FactionKey": "Faction_SageOrder",
                     "RegionKey": "Region_SealedLibrary", "ItemKey": "Item_SealScroll", "SkillKey": "Skill_SacredFlame"},
    ),
    CharDef(
        strkey="Character_Drakmar",
        name_kr="마법사 드라크마르", name_eng="Sorcerer Drakmar",
        desc_kr="봉인된 도서관의 고대 문서를 해독하는 학자 마법사.<br/>성스러운 방패 마법으로 도서관의 방어를 담당하며, 장로 바론의 오른팔 역할을 한다.<br/>최근 금지된 지식에 대한 연구를 시작하여 현자의 결사 내에서 논란이 되고 있다.",
        desc_eng="A scholar sorcerer who deciphers ancient documents in the Sealed Library.",
        knowledge_key="Knowledge_Drakmar",
        source_file="characterinfo_showcase.staticinfo.xml",
        extra_attrs={"Key": "CHAR_005", "CharacterType": "NPC", "Level": "75", "Job": "Sorcerer", "Race": "Human",
                     "Gender": "Male", "Title": "고대 문서의 해독자",
                     "UITextureName": "character_drakmar", "VoicePath": "audio/characters/drakmar_chant.wem",
                     "KnowledgeKey": "Knowledge_Drakmar", "FactionKey": "Faction_SageOrder",
                     "SkillKey": "Skill_HolyShield", "ItemKey": "Item_PlagueCure", "RegionKey": "Region_SageTower"},
    ),
]

# --- Items (5 existing, verbatim) ---

ITEMS: List[ItemDef] = [
    ItemDef(
        strkey="Item_SageStaff",
        name_kr="현자의 지팡이", name_eng="Sage Staff",
        desc_kr="장로 바론이 수백 년간 사용해온 고대의 지팡이.<br/>성스러운 불꽃을 증폭시키는 힘이 깃들어 있으며, 대장장이 그림죠가 제작한 명작이다.",
        desc_eng="An ancient staff wielded by Elder Varon for centuries.",
        knowledge_key="Knowledge_SacredFlame",
        source_file="iteminfo_showcase.staticinfo.xml",
        group_key="ItemGroup_Weapon",
        extra_attrs={"Key": "Item_SageStaff", "Grade": "5", "RequireLevel": "80", "AttackPower": "450",
                     "CharacterKey": "CHAR_001", "UITextureName": "item_sage_staff"},
    ),
    ItemDef(
        strkey="Item_ShadowDagger",
        name_kr="어둠의 단검", name_eng="Shadow Dagger",
        desc_kr="그림자 암살자 키라의 상징적인 무기.<br/>어둠의 교단에서 제작한 이 단검은 그림자 일격의 위력을 극대화시킨다.",
        desc_eng="The signature weapon of Shadow Assassin Kira.",
        knowledge_key="Knowledge_ShadowStrike",
        source_file="iteminfo_showcase.staticinfo.xml",
        group_key="ItemGroup_Weapon",
        extra_attrs={"Key": "Item_ShadowDagger", "Grade": "5", "RequireLevel": "85", "AttackPower": "380",
                     "CharacterKey": "CHAR_002", "UITextureName": "item_dark_dagger"},
    ),
    ItemDef(
        strkey="Item_BlackstarSword",
        name_kr="검은별 대검", name_eng="Blackstar Sword",
        desc_kr="대장장이 그림죠의 필생의 역작.<br/>전설의 검은별 금속으로 제작되었으며, 이 검을 들 자격이 있는 모험가는 아직 나타나지 않았다.",
        desc_eng="The masterwork of Blacksmith Grimjaw, forged from legendary Blackstar metal.",
        knowledge_key="Knowledge_BlackstarSword",
        source_file="iteminfo_showcase.staticinfo.xml",
        group_key="ItemGroup_Weapon",
        extra_attrs={"Key": "Item_BlackstarSword", "Grade": "6", "RequireLevel": "90", "AttackPower": "620",
                     "CharacterKey": "CHAR_003", "UITextureName": "item_blackstar_sword_v2"},
    ),
    ItemDef(
        strkey="Item_PlagueCure",
        name_kr="역병 치료제", name_eng="Plague Cure",
        desc_kr="봉인된 도서관 주변에 퍼진 역병을 치료하는 약.<br/>현자의 결사의 연금술사가 제조한 것으로, 어둠의 교단의 저주를 정화하는 효과가 있다.",
        desc_eng="A medicine that cures the plague around the Sealed Library.",
        knowledge_key="",
        source_file="iteminfo_showcase.staticinfo.xml",
        group_key="ItemGroup_Consumable",
        extra_attrs={"Key": "Item_PlagueCure", "Grade": "3", "RequireLevel": "30", "ItemType": "Consumable",
                     "RegionKey": "Region_SealedLibrary", "UITextureName": "item_plague_cure_v2"},
    ),
    ItemDef(
        strkey="Item_SealScroll",
        name_kr="봉인의 두루마리", name_eng="Seal Scroll",
        desc_kr="봉인된 도서관의 봉인을 유지하기 위한 고대 두루마리.<br/>장로 바론이 직접 작성한 것으로, 어둠의 힘을 차단하는 마법이 새겨져 있다.",
        desc_eng="An ancient scroll that maintains the seal of the Sealed Library.",
        knowledge_key="Knowledge_SealedLibrary",
        source_file="iteminfo_showcase.staticinfo.xml",
        group_key="ItemGroup_Quest",
        extra_attrs={"Key": "Item_SealScroll", "Grade": "4", "ItemType": "Quest",
                     "FactionKey": "Faction_SageOrder", "UITextureName": "item_seal_scroll"},
    ),
]

# --- Skills (3 existing, DO NOT touch the XML file) ---

SKILLS: List[SkillDef] = [
    SkillDef(
        strkey="Skill_SacredFlame",
        name_kr="성스러운 불꽃", name_eng="Sacred Flame",
        desc_kr="현자의 결사에서 전승되는 신성한 화염 마법.<br/>어둠의 존재를 정화하는 힘을 지닌다.<br/>사용 시 주변의 그림자를 소멸시킨다.",
        desc_eng="A sacred flame spell passed down by the Sage Order.",
        source_file="skillinfo_showcase.staticinfo.xml",
    ),
    SkillDef(
        strkey="Skill_ShadowStrike",
        name_kr="그림자 일격", name_eng="Shadow Strike",
        desc_kr="어둠의 힘을 응축하여 적에게 치명적인 일격을 가한다.<br/>그림자 암살자만이 사용할 수 있는 비전 기술.<br/>대상의 방어력을 무시하고 급소를 공격한다.",
        desc_eng="A lethal shadow strike technique exclusive to shadow assassins.",
        source_file="skillinfo_showcase.staticinfo.xml",
    ),
    SkillDef(
        strkey="Skill_HolyShield",
        name_kr="성스러운 방패", name_eng="Holy Shield",
        desc_kr="신성한 빛으로 아군을 보호하는 방어 마법.<br/>모든 어둠의 공격을 일정 시간 무효화한다.<br/>봉인된 도서관의 고대 방어 마법에서 유래했다.",
        desc_eng="A divine shield that protects allies from dark attacks.",
        source_file="skillinfo_showcase.staticinfo.xml",
    ),
]

# --- Regions (14 existing, preserve exact positions) ---

REGIONS: List[RegionDef] = [
    RegionDef(strkey="Region_SealedLibrary", knowledge_key="Knowledge_SealedLibrary", node_type="Dungeon", world_position="350,0,150", faction="Faction_SageOrder", polygon="310,110;390,110;400,150;380,190;320,190;300,150", display_name="봉인된 도서관 (1층)"),
    RegionDef(strkey="Region_SageTower", knowledge_key="Knowledge_SageTower", node_type="Main", world_position="400,0,450", faction="Faction_SageOrder", polygon="360,410;440,410;450,450;430,490;370,490;350,450", display_name="현자의 탑 (최상층)"),
    RegionDef(strkey="Region_BlackstarVillage", knowledge_key="Knowledge_BlackstarVillage", node_type="Town", world_position="500,0,300", faction="Faction_SageOrder", polygon="460,260;540,260;550,300;540,340;460,340;450,300"),
    RegionDef(strkey="Region_MistForest", knowledge_key="Knowledge_MistForest", node_type="Wilderness", world_position="150,0,200", faction="Faction_SageOrder", polygon="110,160;190,160;200,200;180,240;120,240;100,200"),
    RegionDef(strkey="Region_MoonlightLake", knowledge_key="Knowledge_MoonlightLake", node_type="Sub", world_position="100,0,400", faction="Faction_SageOrder", polygon="60,360;140,360;150,400;130,440;70,440;50,400", display_name="달빛 호수 (치유의 샘)"),
    RegionDef(strkey="Region_TradingPost", knowledge_key="Knowledge_TradingPost", node_type="Town", world_position="250,0,350", faction="Faction_SageOrder", polygon="210,310;290,310;300,350;280,390;220,390;200,350"),
    RegionDef(strkey="Region_AncientTemple", knowledge_key="Knowledge_AncientTemple", node_type="Dungeon", world_position="500,0,500", faction="Faction_SageOrder", polygon="460,460;540,460;550,500;530,540;470,540;450,500", display_name="고대 신전 (심층부)"),
    RegionDef(strkey="Region_Watchtower", knowledge_key="Knowledge_Watchtower", node_type="Fortress", world_position="450,0,100", faction="Faction_SageOrder", polygon="410,60;490,60;500,100;480,140;420,140;400,100", display_name="감시탑 (최상층)"),
    RegionDef(strkey="Region_DarkCultHQ", knowledge_key="Knowledge_DarkCultHQ", node_type="Fortress", world_position="650,0,200", faction="Faction_DarkCult", polygon="610,160;690,160;700,200;680,240;620,240;600,200"),
    RegionDef(strkey="Region_DragonTomb", knowledge_key="Knowledge_DragonTomb", node_type="Dungeon", world_position="200,0,500", faction="Faction_DarkCult", polygon="160,460;240,460;250,500;230,540;170,540;150,500"),
    RegionDef(strkey="Region_WindCanyon", knowledge_key="Knowledge_WindCanyon", node_type="Wilderness", world_position="300,0,650", faction="Faction_DarkCult", polygon="260,610;340,610;350,650;330,690;270,690;250,650"),
    RegionDef(strkey="Region_ForgottenFortress", knowledge_key="Knowledge_ForgottenFortress", node_type="Fortress", world_position="600,0,550", faction="Faction_DarkCult", polygon="560,510;640,510;650,550;630,590;570,590;550,550"),
    RegionDef(strkey="Region_VolcanicZone", knowledge_key="Knowledge_VolcanicZone", node_type="Wilderness", world_position="750,0,450", faction="Faction_DarkCult", polygon="710,410;790,410;800,450;780,490;720,490;700,450"),
    RegionDef(strkey="Region_MiningCamp", knowledge_key="Knowledge_MiningCamp", node_type="Sub", world_position="700,0,600", faction="Faction_DarkCult", polygon="660,560;740,560;750,600;730,640;670,640;650,600"),
]

# --- Factions (2) ---

FACTIONS: List[FactionDef] = [
    FactionDef(
        strkey="Faction_SageOrder", name_kr="현자의 결사",
        knowledge_key="Knowledge_SageOrder",
        region_strkeys=[r.strkey for r in REGIONS if r.faction == "Faction_SageOrder"],
    ),
    FactionDef(
        strkey="Faction_DarkCult", name_kr="어둠의 교단",
        knowledge_key="Knowledge_DarkCult",
        region_strkeys=[r.strkey for r in REGIONS if r.faction == "Faction_DarkCult"],
    ),
]

FACTION_GROUPS: List[FactionGroupDef] = [
    FactionGroupDef(
        strkey="FactionGroup_World", group_name_kr="세계",
        knowledge_key="",
        faction_strkeys=["Faction_SageOrder", "Faction_DarkCult"],
    ),
]

# --- Gimmicks (3) ---

GIMMICKS: List[GimmickDef] = [
    GimmickDef(
        strkey="Gimmick_Seal01_Active", group_strkey="GimmickGroup_Seal01",
        group_name_kr="봉인 장치 1",
        name_kr="봉인 장치 1", name_eng="Seal Device 1",
        desc_kr="활성화된 봉인 장치", desc_eng="Active seal device",
        seal_desc_kr="이 봉인은 현자의 불꽃으로만 해제할 수 있습니다.",
        seal_desc_eng="This seal can only be broken with the Sacred Flame.",
    ),
    GimmickDef(
        strkey="Gimmick_Trap01_Poison", group_strkey="GimmickGroup_Trap01",
        group_name_kr="함정 장치 1",
        name_kr="독 함정", name_eng="Poison Trap",
        desc_kr="독을 뿌리는 함정", desc_eng="A trap that sprays poison",
    ),
    GimmickDef(
        strkey="GimmickGroup_Door01", group_strkey="GimmickGroup_Door01",
        group_name_kr="봉인된 문",
        name_kr="봉인된 문", name_eng="Sealed Door",
        desc_kr="", desc_eng="",
    ),
]

# --- Audio Events (10, 2 per character) ---

AUDIO_EVENTS: List[AudioDef] = [
    AudioDef("play_varon_greeting_01", "DLG_VARON_01", "봉인된 도서관에 오신 것을 환영합니다.", "Welcome to the Sealed Library.", "Dialog/QuestDialog", "questdialog_showcase"),
    AudioDef("play_varon_farewell_01", "DLG_VARON_02", "성스러운 불꽃이 그대를 인도하리라.", "May the Sacred Flame guide you.", "Dialog/QuestDialog", "questdialog_showcase"),
    AudioDef("play_kira_taunt_01", "DLG_KIRA_01", "네 화살은 빗나갔어.", "Your arrow missed.", "Dialog/QuestDialog", "questdialog_showcase"),
    AudioDef("play_kira_threat_01", "DLG_KIRA_02", "어둠의 힘 앞에 무릎을 꿇어라.", "Kneel before the power of darkness.", "Dialog/QuestDialog", "questdialog_showcase"),
    AudioDef("play_grimjaw_forge_01", "DLG_GRIMJAW_01", "검은별 대검은 내 필생의 역작이야.", "The Blackstar Sword is my life's masterwork.", "Dialog/QuestDialog", "questdialog_showcase"),
    AudioDef("play_grimjaw_quest_01", "DLG_GRIMJAW_02", "좋은 금속이 필요하다면 화산 지대로 가거라.", "If you need fine metal, head to the Volcanic Zone.", "Dialog/QuestDialog", "questdialog_showcase"),
    AudioDef("play_lune_whisper_01", "DLG_LUNE_01", "숲의 목소리를 들어봐.", "Listen to the voice of the forest.", "Dialog/QuestDialog", "questdialog_showcase"),
    AudioDef("play_lune_scout_01", "DLG_LUNE_02", "어둠의 교단이 움직이고 있어.", "The Dark Cult is on the move.", "Dialog/QuestDialog", "questdialog_showcase"),
    AudioDef("play_drakmar_chant_01", "DLG_DRAKMAR_01", "고대의 문자가 진실을 말하고 있다.", "The ancient script speaks the truth.", "Dialog/QuestDialog", "questdialog_showcase"),
    AudioDef("play_drakmar_warning_01", "DLG_DRAKMAR_02", "금지된 지식에는 대가가 따른다.", "Forbidden knowledge comes at a price.", "Dialog/QuestDialog", "questdialog_showcase"),
]

# --- Knowledge Groups ---

KNOWLEDGE_GROUPS: List[KnowledgeGroupDef] = [
    KnowledgeGroupDef(
        strkey="KnowledgeGroup_Character", group_name_kr="캐릭터",
        member_strkeys=["Knowledge_ElderVaron", "Knowledge_ShadowKira", "Knowledge_Grimjaw", "Knowledge_Lune", "Knowledge_Drakmar"],
    ),
    KnowledgeGroupDef(
        strkey="KnowledgeGroup_Skill", group_name_kr="스킬",
        member_strkeys=["Knowledge_SacredFlame", "Knowledge_ShadowStrike", "Knowledge_HolyShield"],
    ),
    KnowledgeGroupDef(
        strkey="KnowledgeGroup_Region", group_name_kr="지역",
        member_strkeys=[k.strkey for k in KNOWLEDGE if k.group_key == "KnowledgeGroup_Region"],
    ),
    KnowledgeGroupDef(
        strkey="KnowledgeGroup_Faction", group_name_kr="세력",
        member_strkeys=["Knowledge_SageOrder", "Knowledge_DarkCult"],
    ),
    KnowledgeGroupDef(
        strkey="KnowledgeGroup_Item", group_name_kr="아이템",
        member_strkeys=["Knowledge_BlackstarSword", "Knowledge_SageStaff", "Knowledge_ShadowDagger", "Knowledge_PlagueCure", "Knowledge_SealScroll"],
    ),
]

# --- Item Groups ---

ITEM_GROUPS: List[ItemGroupDef] = [
    ItemGroupDef(strkey="ItemGroup_Weapon", group_name_kr="무기", parent_strkey="", item_strkeys=["Item_SageStaff", "Item_ShadowDagger", "Item_BlackstarSword"]),
    ItemGroupDef(strkey="ItemGroup_Consumable", group_name_kr="소모품", parent_strkey="", item_strkeys=["Item_PlagueCure"]),
    ItemGroupDef(strkey="ItemGroup_Quest", group_name_kr="퀘스트", parent_strkey="", item_strkeys=["Item_SealScroll"]),
]


# =============================================================================
# Helper: Collect ALL StringIds for localization
# =============================================================================

def _derive_stringid_short(strkey: str, prefix: str) -> str:
    """Derive short StringId key from a strkey, e.g. 'Character_ElderVaron' -> 'ELDERVARON'."""
    parts = strkey.split("_", 1)
    return parts[1].upper() if len(parts) > 1 else strkey.upper()


def collect_all_stringids() -> List[Tuple[str, str, str]]:
    """Collect (StringId, StrOrigin_KR, Str_ENG) for all entities.

    Returns a deterministically-ordered list.
    """
    entries: List[Tuple[str, str, str]] = []

    # Characters: name + desc
    for c in CHARACTERS:
        short = _derive_stringid_short(c.strkey, "CHAR")
        entries.append((f"CHAR_{short}_NAME", c.name_kr, c.name_eng))
        entries.append((f"CHAR_{short}_DESC", c.desc_kr, c.desc_eng))

    # Items: name + desc
    for item in ITEMS:
        short = _derive_stringid_short(item.strkey, "ITEM")
        entries.append((f"ITEM_{short}_NAME", item.name_kr, item.name_eng))
        entries.append((f"ITEM_{short}_DESC", item.desc_kr, item.desc_eng))

    # Skills: name + desc
    for s in SKILLS:
        short = _derive_stringid_short(s.strkey, "SKILL")
        entries.append((f"SKILL_{short}_NAME", s.name_kr, s.name_eng))
        entries.append((f"SKILL_{short}_DESC", s.desc_kr, s.desc_eng))

    # Gimmicks: name + desc (skip empty)
    for g in GIMMICKS:
        short = _derive_stringid_short(g.strkey, "GIMMICK")
        if g.name_kr:
            entries.append((f"GIMMICK_{short}_NAME", g.name_kr, g.name_eng))
        if g.desc_kr:
            entries.append((f"GIMMICK_{short}_DESC", g.desc_kr, g.desc_eng))
        if g.seal_desc_kr:
            entries.append((f"GIMMICK_{short}_SEAL", g.seal_desc_kr, g.seal_desc_eng))

    # Knowledge: name + desc
    for k in KNOWLEDGE:
        short = _derive_stringid_short(k.strkey, "KNOW")
        entries.append((f"KNOW_{short}_NAME", k.name_kr, k.name_kr))  # KR=KR for knowledge
        entries.append((f"KNOW_{short}_DESC", k.desc_kr, k.desc_kr))

    # Audio dialog lines
    for a in AUDIO_EVENTS:
        entries.append((a.stringid, a.strorigin_kr, a.str_eng))

    return entries


# =============================================================================
# XML Generation Helpers
# =============================================================================


def _make_xml_tree(root_tag: str) -> etree._Element:
    """Create an XML root element with the given tag."""
    return etree.Element(root_tag)


def _write_xml(root: etree._Element, path: Path) -> None:
    """Write XML element to file with declaration and pretty printing."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tree = etree.ElementTree(root)
    tree.write(
        str(path),
        xml_declaration=True,
        encoding="UTF-8",
        pretty_print=True,
    )
    logger.debug(f"  Wrote: {path}")


# =============================================================================
# Generator Functions
# =============================================================================


def generate_knowledgeinfo(root_dir: Path) -> None:
    """Generate knowledgeinfo_showcase.staticinfo.xml with KnowledgeGroupInfo wrappers."""
    xml_root = _make_xml_tree("KnowledgeInfoList")

    # Build lookup: group_key -> list of knowledge defs
    group_members: Dict[str, List[KnowledgeDef]] = {}
    ungrouped: List[KnowledgeDef] = []
    for k in KNOWLEDGE:
        if k.group_key:
            group_members.setdefault(k.group_key, []).append(k)
        else:
            ungrouped.append(k)

    # Write groups in order
    for kg in KNOWLEDGE_GROUPS:
        group_elem = etree.SubElement(xml_root, "KnowledgeGroupInfo")
        group_elem.set("StrKey", kg.strkey)
        group_elem.set("GroupName", kg.group_name_kr)

        members = group_members.get(kg.strkey, [])
        for k in members:
            ki = etree.SubElement(group_elem, "KnowledgeInfo")
            ki.set("StrKey", k.strkey)
            ki.set("Name", k.name_kr)
            ki.set("KnowledgeGroupKey", k.group_key)
            ki.set("UITextureName", k.ui_texture)
            ki.set("Desc", k.desc_kr)
            for attr_name, attr_val in k.extra_attrs.items():
                ki.set(attr_name, attr_val)
            if k.devmemo:
                ki.set("DevMemo", k.devmemo)
            # Add LevelData child for skill knowledge (preserve existing)
            if k.strkey == "Knowledge_SacredFlame":
                ld = etree.SubElement(ki, "LevelData")
                ld.set("Level", "1")
                ld.set("Learnable", "True")
                ld.set("RequiredLevel", "10")
                ld.set("ManaCost", "25")

    # Write ungrouped
    for k in ungrouped:
        ki = etree.SubElement(xml_root, "KnowledgeInfo")
        ki.set("StrKey", k.strkey)
        ki.set("Name", k.name_kr)
        ki.set("UITextureName", k.ui_texture)
        ki.set("Desc", k.desc_kr)
        for attr_name, attr_val in k.extra_attrs.items():
            ki.set(attr_name, attr_val)
        if k.devmemo:
            ki.set("DevMemo", k.devmemo)

    out_path = root_dir / "StaticInfo" / "knowledgeinfo" / "knowledgeinfo_showcase.staticinfo.xml"
    _write_xml(xml_root, out_path)
    logger.info(f"  Generated knowledgeinfo with {len(KNOWLEDGE)} entries, {len(KNOWLEDGE_GROUPS)} groups")


def generate_iteminfo(root_dir: Path) -> None:
    """Generate iteminfo_showcase.staticinfo.xml with ItemGroupInfo wrappers."""
    xml_root = _make_xml_tree("ItemInfoList")

    # Index items by strkey
    item_by_strkey = {item.strkey: item for item in ITEMS}

    for ig in ITEM_GROUPS:
        group_elem = etree.SubElement(xml_root, "ItemGroupInfo")
        group_elem.set("StrKey", ig.strkey)
        group_elem.set("GroupName", ig.group_name_kr)
        group_elem.set("ParentStrKey", ig.parent_strkey)

        for isk in ig.item_strkeys:
            item = item_by_strkey.get(isk)
            if not item:
                continue
            ii = etree.SubElement(group_elem, "ItemInfo")
            ii.set("StrKey", item.strkey)
            ii.set("ItemName", item.name_kr)
            ii.set("ItemDesc", item.desc_kr)
            if item.knowledge_key:
                ii.set("KnowledgeKey", item.knowledge_key)
            for attr_name, attr_val in item.extra_attrs.items():
                ii.set(attr_name, attr_val)

    out_path = root_dir / "StaticInfo" / "iteminfo" / "iteminfo_showcase.staticinfo.xml"
    _write_xml(xml_root, out_path)
    logger.info(f"  Generated iteminfo with {len(ITEMS)} items, {len(ITEM_GROUPS)} groups")


def generate_factioninfo(root_dir: Path) -> None:
    """Generate FactionInfo.staticinfo.xml with FactionGroup > Faction > FactionNode nesting."""
    xml_root = _make_xml_tree("FactionInfoList")

    # Index regions
    region_by_strkey = {r.strkey: r for r in REGIONS}
    # Index knowledge for Korean names
    know_by_strkey = {k.strkey: k for k in KNOWLEDGE}

    for fg in FACTION_GROUPS:
        fg_elem = etree.SubElement(xml_root, "FactionGroup")
        fg_elem.set("StrKey", fg.strkey)
        fg_elem.set("GroupName", fg.group_name_kr)
        fg_elem.set("KnowledgeKey", fg.knowledge_key)

        for f_strkey in fg.faction_strkeys:
            faction = next((f for f in FACTIONS if f.strkey == f_strkey), None)
            if not faction:
                continue
            f_elem = etree.SubElement(fg_elem, "Faction")
            f_elem.set("StrKey", faction.strkey)
            f_elem.set("Name", faction.name_kr)
            f_elem.set("KnowledgeKey", faction.knowledge_key)

            for r_strkey in faction.region_strkeys:
                region = region_by_strkey.get(r_strkey)
                if not region:
                    continue
                n_elem = etree.SubElement(f_elem, "FactionNode")
                n_elem.set("StrKey", region.strkey)
                n_elem.set("KnowledgeKey", region.knowledge_key)
                n_elem.set("Type", region.node_type)
                n_elem.set("WorldPosition", region.world_position)
                # Add Korean/English names from knowledge for backward compat
                k = know_by_strkey.get(region.knowledge_key)
                if k:
                    n_elem.set("NameKR", k.name_kr)
                poly_elem = etree.SubElement(n_elem, "Polygon")
                poly_elem.set("Points", region.polygon)

    # D16: RegionInfo entries
    for region in REGIONS:
        if region.display_name:
            ri = etree.SubElement(xml_root, "RegionInfo")
            ri.set("KnowledgeKey", region.knowledge_key)
            ri.set("DisplayName", region.display_name)

    out_path = root_dir / "StaticInfo" / "factioninfo" / "FactionInfo.staticinfo.xml"
    _write_xml(xml_root, out_path)
    logger.info(f"  Generated factioninfo with {len(FACTIONS)} factions, {len(REGIONS)} regions, {len(FACTION_GROUPS)} groups")


def generate_gimmickinfo(root_dir: Path) -> None:
    """Generate gimmickinfo_showcase.staticinfo.xml with 3 GimmickGroupInfo entries."""
    xml_root = _make_xml_tree("GimmickInfoList")

    # Group gimmicks by group_strkey
    groups_seen: Set[str] = set()
    gimmick_by_group: Dict[str, List[GimmickDef]] = {}
    for g in GIMMICKS:
        gimmick_by_group.setdefault(g.group_strkey, []).append(g)

    for group_strkey, members in gimmick_by_group.items():
        first = members[0]
        gg = etree.SubElement(xml_root, "GimmickGroupInfo")
        gg.set("StrKey", group_strkey)
        gg.set("GimmickName", first.group_name_kr)

        # If the gimmick IS the group (GimmickGroup_Door01), skip inner GimmickInfo
        if group_strkey == first.strkey:
            continue

        for g in members:
            gi = etree.SubElement(gg, "GimmickInfo")
            gi.set("StrKey", g.strkey)
            gi.set("GimmickName", g.name_kr)
            gi.set("Desc", g.desc_kr)
            if g.seal_desc_kr:
                sd = etree.SubElement(gi, "SealData")
                sd.set("Desc", g.seal_desc_kr)

    out_path = root_dir / "StaticInfo" / "gimmickinfo" / "gimmickinfo_showcase.staticinfo.xml"
    _write_xml(xml_root, out_path)
    logger.info(f"  Generated gimmickinfo with {len(GIMMICKS)} gimmick entries")


def generate_loc_xmls(root_dir: Path) -> None:
    """Generate languagedata_KOR.xml and languagedata_ENG.xml with all StringIds."""
    all_stringids = collect_all_stringids()

    # KOR: StrOrigin
    kor_root = _make_xml_tree("LanguageData")
    for sid, strorigin, _ in all_stringids:
        ls = etree.SubElement(kor_root, "LocStr")
        ls.set("StringId", sid)
        ls.set("StrOrigin", strorigin)
        ls.set("Str", strorigin)  # KOR Str = same as StrOrigin

    kor_path = root_dir / "loc" / "languagedata_KOR.xml"
    _write_xml(kor_root, kor_path)
    logger.info(f"  Generated languagedata_KOR.xml with {len(all_stringids)} entries")

    # ENG: Str
    eng_root = _make_xml_tree("LanguageData")
    for sid, _, str_eng in all_stringids:
        ls = etree.SubElement(eng_root, "LocStr")
        ls.set("StringId", sid)
        ls.set("Str", str_eng)

    eng_path = root_dir / "loc" / "languagedata_ENG.xml"
    _write_xml(eng_root, eng_path)
    logger.info(f"  Generated languagedata_ENG.xml with {len(all_stringids)} entries")


def generate_export_xmls(root_dir: Path) -> None:
    """Generate export__/ directory with event XMLs and .loc.xml files."""
    export_dir = root_dir / "export__"

    # --- Dialog events (questdialog_showcase) ---
    dialog_dir = export_dir / "Dialog" / "QuestDialog"

    # Event XML
    evt_root = _make_xml_tree("DialogList")
    for a in AUDIO_EVENTS:
        d = etree.SubElement(evt_root, "Dialog")
        d.set("SoundEventName", a.event_name)
        d.set("StringId", a.stringid)
    _write_xml(evt_root, dialog_dir / "questdialog_showcase.xml")

    # Dialog .loc.xml
    loc_root = _make_xml_tree("LanguageData")
    for a in AUDIO_EVENTS:
        ls = etree.SubElement(loc_root, "LocStr")
        ls.set("StringId", a.stringid)
        ls.set("StrOrigin", a.strorigin_kr)
    _write_xml(loc_root, dialog_dir / "questdialog_showcase.loc.xml")
    logger.info(f"  Generated dialog export with {len(AUDIO_EVENTS)} events")

    # --- Entity export XMLs (for C6/C7 bridge) ---
    # Group: (export_subdir, source_file_stem, entity_stringids)
    entity_exports: List[Tuple[str, str, List[Tuple[str, str, str]]]] = []

    # Characters
    char_sids = []
    for c in CHARACTERS:
        short = _derive_stringid_short(c.strkey, "CHAR")
        char_sids.append((f"CHAR_{short}_NAME", c.name_kr, c.name_eng))
        char_sids.append((f"CHAR_{short}_DESC", c.desc_kr, c.desc_eng))
    entity_exports.append(("Character", "characterinfo_showcase.staticinfo", char_sids))

    # Items
    item_sids = []
    for item in ITEMS:
        short = _derive_stringid_short(item.strkey, "ITEM")
        item_sids.append((f"ITEM_{short}_NAME", item.name_kr, item.name_eng))
        item_sids.append((f"ITEM_{short}_DESC", item.desc_kr, item.desc_eng))
    entity_exports.append(("Item", "iteminfo_showcase.staticinfo", item_sids))

    # Skills
    skill_sids = []
    for s in SKILLS:
        short = _derive_stringid_short(s.strkey, "SKILL")
        skill_sids.append((f"SKILL_{short}_NAME", s.name_kr, s.name_eng))
        skill_sids.append((f"SKILL_{short}_DESC", s.desc_kr, s.desc_eng))
    entity_exports.append(("Skill", "skillinfo_showcase.staticinfo", skill_sids))

    # Gimmicks
    gimmick_sids = []
    for g in GIMMICKS:
        short = _derive_stringid_short(g.strkey, "GIMMICK")
        if g.name_kr:
            gimmick_sids.append((f"GIMMICK_{short}_NAME", g.name_kr, g.name_eng))
        if g.desc_kr:
            gimmick_sids.append((f"GIMMICK_{short}_DESC", g.desc_kr, g.desc_eng))
    entity_exports.append(("Gimmick", "gimmickinfo_showcase.staticinfo", gimmick_sids))

    for subdir, file_stem, sids in entity_exports:
        entity_dir = export_dir / subdir

        # Event XML (with EventName+StringId so D11 picks them up)
        evt_root = _make_xml_tree("ExportData")
        for sid, _, _ in sids:
            entry = etree.SubElement(evt_root, "Entry")
            entry.set("StringId", sid)
        _write_xml(evt_root, entity_dir / f"{file_stem}.xml")

        # .loc.xml (with StringId+StrOrigin for D17/D18 and C6/C7 bridge)
        loc_root = _make_xml_tree("LanguageData")
        for sid, strorigin, _ in sids:
            ls = etree.SubElement(loc_root, "LocStr")
            ls.set("StringId", sid)
            ls.set("StrOrigin", strorigin)
        _write_xml(loc_root, entity_dir / f"{file_stem}.loc.xml")
        logger.info(f"  Generated {subdir} export with {len(sids)} StringIds")


def generate_dds_stubs(root_dir: Path) -> None:
    """Generate valid .dds files openable by Pillow for all UITextureName values."""
    dds_dir = root_dir / "texture" / "image"
    dds_dir.mkdir(parents=True, exist_ok=True)

    # Collect all unique texture names
    textures: Set[str] = set()
    for k in KNOWLEDGE:
        if k.ui_texture:
            textures.add(k.ui_texture.lower())

    for tex_name in sorted(textures):
        dds_path = dds_dir / f"{tex_name}.dds"
        # Generate unique color from name hash so textures are visually distinguishable
        h = hash(tex_name) & 0xFFFFFF
        color = ((h >> 16) & 0xFF, (h >> 8) & 0xFF, h & 0xFF, 255)
        img = Image.new("RGBA", (64, 64), color)
        img.save(str(dds_path), format="DDS")
    logger.info(f"  Generated {len(textures)} valid DDS files in texture/image/")


def generate_wem_stubs(root_dir: Path) -> None:
    """Generate valid WAV-content .wem files for all audio events in all language folders."""
    lang_folders = [
        "English(US)",
        "Korean",
        "Chinese(PRC)",
    ]

    for lang_folder in lang_folders:
        wem_dir = root_dir / "sound" / "windows" / lang_folder
        wem_dir.mkdir(parents=True, exist_ok=True)

        for a in AUDIO_EVENTS:
            wem_path = wem_dir / f"{a.event_name}.wem"
            _create_wav_content(wem_path, duration_ms=100, sample_rate=22050)

    total = len(AUDIO_EVENTS) * len(lang_folders)
    logger.info(f"  Generated {total} WEM stubs across {len(lang_folders)} language folders")


def _create_wav_content(output_path: Path, duration_ms: int = 100, sample_rate: int = 22050) -> None:
    """Create a minimal valid WAV file at the given path."""
    num_samples = int(sample_rate * duration_ms / 1000)
    with wave.open(str(output_path), 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)  # 16-bit
        wav.setframerate(sample_rate)
        samples = struct.pack(f'<{num_samples}h', *([0] * num_samples))
        wav.writeframes(samples)


# =============================================================================
# Validation
# =============================================================================


def validate(root: Path) -> None:
    """Run MegaIndex.build() against generated data, assert all 35 dicts non-empty."""
    # Add project root to path
    project_root = root.parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    from unittest.mock import patch

    from server.tools.ldm.services.mega_index import MegaIndex

    mock_paths = {
        "knowledge_folder": root / "StaticInfo" / "knowledgeinfo",
        "character_folder": root / "StaticInfo" / "characterinfo",
        "faction_folder": root / "StaticInfo" / "factioninfo",
        "texture_folder": root / "texture" / "image",
        "audio_folder": root / "sound" / "windows" / "English(US)",
        "export_folder": root / "export__",
        "loc_folder": root / "loc",
    }

    with patch("server.tools.ldm.services.mega_index.get_perforce_path_service") as mock_svc:
        mock_svc.return_value.get_all_resolved.return_value = mock_paths
        idx = MegaIndex()
        idx.build()

    # Assert all 35 dicts with expected minimum counts
    checks = [
        ("D1  knowledge_by_strkey", idx.knowledge_by_strkey, 25),
        ("D2  character_by_strkey", idx.character_by_strkey, 5),
        ("D3  item_by_strkey", idx.item_by_strkey, 5),
        ("D4  region_by_strkey", idx.region_by_strkey, 10),
        ("D5  faction_by_strkey", idx.faction_by_strkey, 2),
        ("D6  faction_group_by_strkey", idx.faction_group_by_strkey, 1),
        ("D7  skill_by_strkey", idx.skill_by_strkey, 3),
        ("D8  gimmick_by_strkey", idx.gimmick_by_strkey, 3),
        ("D9  dds_by_stem", idx.dds_by_stem, 15),
        ("D10 wem_by_event", idx.wem_by_event, 10),
        ("D11 event_to_stringid", idx.event_to_stringid, 10),
        ("D12 stringid_to_strorigin", idx.stringid_to_strorigin, 40),
        ("D13 stringid_to_translations", idx.stringid_to_translations, 40),
        ("D14 item_group_hierarchy", idx.item_group_hierarchy, 2),
        ("D15 knowledge_group_hierarchy", idx.knowledge_group_hierarchy, 2),
        ("D16 region_display_names", idx.region_display_names, 3),
        ("D17 export_file_stringids", idx.export_file_stringids, 4),
        ("D18 ordered_export_index", idx.ordered_export_index, 4),
        ("D19 strkey_to_devmemo", idx.strkey_to_devmemo, 2),
        ("D20 event_to_export_path", idx.event_to_export_path, 10),
        ("D21 event_to_xml_order", idx.event_to_xml_order, 10),
        ("R1  name_kr_to_strkeys", idx.name_kr_to_strkeys, 10),
        ("R2  knowledge_key_to_entities", idx.knowledge_key_to_entities, 5),
        ("R3  stringid_to_event", idx.stringid_to_event, 10),
        ("R4  ui_texture_to_strkeys", idx.ui_texture_to_strkeys, 10),
        ("R5  source_file_to_strkeys", idx.source_file_to_strkeys, 3),
        ("R6  strorigin_to_stringids", idx.strorigin_to_stringids, 20),
        ("R7  group_key_to_items", idx.group_key_to_items, 2),
        ("C1  strkey_to_image_path", idx.strkey_to_image_path, 10),
        ("C2  strkey_to_audio_path", idx.strkey_to_audio_path, 0),
        ("C3  stringid_to_audio_path", idx.stringid_to_audio_path, 10),
        ("C4  event_to_script_kr", idx.event_to_script_kr, 10),
        ("C5  event_to_script_eng", idx.event_to_script_eng, 10),
        ("C6  entity_strkey_to_stringids", idx.entity_strkey_to_stringids, 5),
        ("C7  stringid_to_entity", idx.stringid_to_entity, 5),
    ]

    failures = []
    for label, d, min_count in checks:
        actual = len(d)
        status = "PASS" if actual >= min_count else "FAIL"
        if status == "FAIL":
            failures.append(f"{label}: expected >= {min_count}, got {actual}")
        print(f"  {status} {label}: {actual} entries (min: {min_count})")

    if failures:
        print(f"\nFAILED {len(failures)} checks:")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    else:
        print(f"\nALL 35 DICTS VALIDATED. Build time: {idx._build_time:.3f}s")


# =============================================================================
# Main
# =============================================================================


def main() -> None:
    """Generate all mock data files into tests/fixtures/mock_gamedata/."""
    root = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "mock_gamedata"
    logger.info(f"Generating mock data in: {root}")

    generate_knowledgeinfo(root)
    generate_iteminfo(root)
    generate_factioninfo(root)
    generate_gimmickinfo(root)
    generate_loc_xmls(root)
    generate_export_xmls(root)
    generate_dds_stubs(root)
    generate_wem_stubs(root)

    logger.info("Generation complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate MegaIndex mock data fixtures")
    parser.add_argument("--validate", action="store_true", help="Run MegaIndex.build() validation after generation")
    args = parser.parse_args()

    main()

    if args.validate:
        root = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "mock_gamedata"
        validate(root)
