"""Pydantic v2 schemas for Skill Codex API responses."""

from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel


class SkillCardResponse(BaseModel):
    strkey: str
    name_kr: str
    name_translated: str = ""
    desc_kr: str = ""
    image_urls: List[str] = []
    source_file: str = ""


class SkillDetailResponse(SkillCardResponse):
    learn_knowledge_key: str = ""
    knowledge_pass_0: list = []
    knowledge_pass_1: list = []
    knowledge_pass_2: list = []
    related_entities: list = []


class SkillListResponse(BaseModel):
    items: List[SkillCardResponse]
    total: int
