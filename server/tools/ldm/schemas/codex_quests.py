"""Pydantic v2 schemas for Quest Codex API responses."""

from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel


class QuestCardResponse(BaseModel):
    strkey: str
    name_kr: str
    name_translated: str = ""
    desc_kr: str = ""
    quest_type: str = ""  # main, faction, challenge, minigame
    quest_subtype: str = ""  # daily, region, politics, others
    faction_key: str = ""
    image_urls: List[str] = []
    source_file: str = ""


class QuestDetailResponse(QuestCardResponse):
    knowledge_pass_0: list = []
    knowledge_pass_1: list = []
    knowledge_pass_2: list = []
    related_entities: list = []


class QuestTypeItem(BaseModel):
    quest_type: str
    count: int


class QuestTypeResponse(BaseModel):
    types: List[QuestTypeItem]
    total_quests: int


class QuestListResponse(BaseModel):
    items: List[QuestCardResponse]
    total: int
    type_filter: Optional[str] = None
    subtype_filter: Optional[str] = None
