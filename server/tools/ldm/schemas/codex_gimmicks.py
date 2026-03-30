"""Pydantic v2 schemas for Gimmick Codex API responses."""

from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel


class GimmickCardResponse(BaseModel):
    strkey: str
    name_kr: str
    name_translated: str = ""
    desc_kr: str = ""
    seal_desc: str = ""
    image_urls: List[str] = []
    source_file: str = ""


class GimmickDetailResponse(GimmickCardResponse):
    knowledge_pass_0: list = []
    knowledge_pass_1: list = []
    knowledge_pass_2: list = []
    related_entities: list = []


class GimmickListResponse(BaseModel):
    items: List[GimmickCardResponse]
    total: int
