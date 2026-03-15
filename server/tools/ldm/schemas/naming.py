"""Naming coherence schemas -- request/response models for naming endpoints.

Phase 21: AI Naming Coherence + Placeholders (Plan 01)
"""

from __future__ import annotations

from typing import List

from pydantic import BaseModel


# =============================================================================
# Similar Names
# =============================================================================


class NamingSimilarItem(BaseModel):
    """A single similar entity name from FAISS search."""

    name: str
    strkey: str
    similarity: float
    entity_type: str


class NamingSimilarResponse(BaseModel):
    """Response for similar names endpoint."""

    items: List[NamingSimilarItem]
    count: int


# =============================================================================
# AI Naming Suggestions
# =============================================================================


class NamingSuggestionItem(BaseModel):
    """A single AI-generated naming suggestion."""

    name: str
    confidence: float
    reasoning: str


class NamingSuggestionResponse(BaseModel):
    """Response for naming suggestions endpoint."""

    suggestions: List[NamingSuggestionItem]
    status: str = "ok"
    similar_names: List[NamingSimilarItem] = []
