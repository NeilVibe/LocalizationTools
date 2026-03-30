"""
MegaIndex Data Entry Schemas - Frozen dataclasses for all 10 entity types.

These schemas define the shape of data that MegaIndex populates from XML parsing.
All are frozen (immutable) and use slots for memory efficiency. They serve as the
contract between XML parsers (Plan 03) and the MegaIndex dictionaries.

Phase 45: MegaIndex Foundation Infrastructure (Plan 01)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from loguru import logger


# =============================================================================
# Core Entity Schemas
# =============================================================================


@dataclass(frozen=True, slots=True)
class KnowledgeEntry:
    """Knowledge entity from KnowledgeInfo XML -- maps StrKey to entity metadata."""

    strkey: str = ""
    name: str = ""  # Korean display name
    desc: str = ""  # Korean description
    ui_texture_name: str = ""  # UITextureName (for DDS lookup)
    group_key: str = ""  # KnowledgeGroupKey
    source_file: str = ""  # XML filename


@dataclass(frozen=True, slots=True)
class CharacterEntry:
    """Character entity from CharacterInfo XML."""

    strkey: str = ""
    name: str = ""  # CharacterName (Korean)
    desc: str = ""  # CharacterDesc
    knowledge_key: str = ""  # KnowledgeKey or RewardKnowledgeKey
    use_macro: str = ""  # Race/Gender (e.g., "Macro_NPC_Human_Male")
    age: str = ""  # Age (e.g., "Adult")
    job: str = ""  # Job (e.g., "Job_Scholar")
    ui_icon_path: str = ""  # UIIconPath fallback
    source_file: str = ""


@dataclass(frozen=True, slots=True)
class ItemEntry:
    """Item entity from KnowledgeInfo XML with optional InspectKnowledge."""

    strkey: str = ""
    name: str = ""  # ItemName (Korean)
    desc: str = ""  # ItemDesc
    knowledge_key: str = ""  # KnowledgeKey
    group_key: str = ""  # Parent ItemGroupInfo StrKey
    source_file: str = ""
    inspect_entries: Tuple[Tuple[str, str, str, str], ...] = ()  # (desc, k_name, k_desc, k_src)


@dataclass(frozen=True, slots=True)
class RegionEntry:
    """Region/FactionNode entity from factioninfo XML with world position."""

    strkey: str = ""
    name: str = ""  # Display name (from KnowledgeInfo or Name attr)
    desc: str = ""  # Description
    knowledge_key: str = ""
    world_position: Optional[Tuple[float, float, float]] = None  # (x, y, z)
    node_type: str = ""  # Main, Sub, etc.
    parent_strkey: str = ""  # Parent FactionNode StrKey
    source_file: str = ""
    display_name: str = ""  # RegionInfo.DisplayName (if different from name)


@dataclass(frozen=True, slots=True)
class FactionEntry:
    """Faction entity from factioninfo XML."""

    strkey: str = ""
    name: str = ""
    knowledge_key: str = ""
    group_strkey: str = ""  # Parent FactionGroup
    source_file: str = ""
    node_strkeys: Tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class FactionGroupEntry:
    """Faction group container from factioninfo XML."""

    strkey: str = ""
    group_name: str = ""
    knowledge_key: str = ""
    source_file: str = ""
    faction_strkeys: Tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SkillEntry:
    """Skill entity from skillinfo XML."""

    strkey: str = ""
    name: str = ""
    desc: str = ""
    learn_knowledge_key: str = ""
    source_file: str = ""


@dataclass(frozen=True, slots=True)
class GimmickEntry:
    """Gimmick entity from gimmickinfo XML."""

    strkey: str = ""
    name: str = ""
    desc: str = ""
    seal_desc: str = ""
    source_file: str = ""


@dataclass(frozen=True, slots=True)
class QuestEntry:
    """Quest entity from quest XMLs."""

    strkey: str = ""
    name: str = ""  # Quest Name (Korean)
    desc: str = ""  # Quest description
    quest_type: str = ""  # "main", "faction", "challenge", "minigame"
    quest_subtype: str = ""  # "daily", "region", "politics", "others" (faction quests only)
    faction_key: str = ""  # Associated faction StrKey (for faction quests)
    source_file: str = ""


# =============================================================================
# Group/Tree Node Schemas
# =============================================================================


@dataclass(frozen=True, slots=True)
class ItemGroupNode:
    """Item group hierarchy node from ItemGroupInfo XML."""

    strkey: str = ""
    group_name: str = ""  # Korean group name
    parent_strkey: str = ""  # "" if root
    child_strkeys: Tuple[str, ...] = ()  # Child groups
    item_strkeys: Tuple[str, ...] = ()  # Direct items in this group


@dataclass(frozen=True, slots=True)
class KnowledgeGroupNode:
    """Knowledge group hierarchy node from KnowledgeGroupInfo XML."""

    strkey: str = ""
    group_name: str = ""
    child_strkeys: Tuple[str, ...] = ()  # Knowledge entries in this group


# =============================================================================
# Schema Registry (for dynamic type access)
# =============================================================================

SCHEMA_REGISTRY = {
    "knowledge": KnowledgeEntry,
    "character": CharacterEntry,
    "item": ItemEntry,
    "region": RegionEntry,
    "faction": FactionEntry,
    "faction_group": FactionGroupEntry,
    "skill": SkillEntry,
    "gimmick": GimmickEntry,
    "quest": QuestEntry,
    "item_group": ItemGroupNode,
    "knowledge_group": KnowledgeGroupNode,
}

logger.debug(f"[MEGAINDEX] {len(SCHEMA_REGISTRY)} entity schemas registered")
