"""
AI Suggestions API endpoint -- translation suggestions via Ollama/Qwen3.

Exposes the AISuggestionService through a REST endpoint that returns
ranked translation suggestions with blended confidence scores.

Phase 17: AI Translation Suggestions (Plan 01)
"""

from __future__ import annotations

import json
from typing import Optional

from fastapi import APIRouter, Depends, Query
from loguru import logger

from server.utils.dependencies import get_current_active_user_async
from server.tools.ldm.services.ai_suggestion_service import get_ai_suggestion_service
from server.tools.ldm.services.category_service import categorize_by_stringid


router = APIRouter(tags=["LDM-AI-Suggestions"])


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/ai-suggestions/status")
async def get_ai_suggestions_status(
    current_user: dict = Depends(get_current_active_user_async),
):
    """Get AI suggestion service health (available, cache_size, model)."""
    service = get_ai_suggestion_service()
    return service.get_status()


@router.get("/ai-suggestions/{string_id}")
async def get_ai_suggestions(
    string_id: str,
    source_text: str = Query(..., max_length=2000, description="Source text to translate"),
    target_lang: str = Query(default="KR", max_length=10, description="Target language code"),
    context_before: Optional[str] = Query(default=None, description="JSON array of {source, target} pairs before"),
    context_after: Optional[str] = Query(default=None, description="JSON array of {source, target} pairs after"),
    current_user: dict = Depends(get_current_active_user_async),
):
    """Get AI translation suggestions for a string.

    Returns ranked translation suggestions with blended confidence scores.
    Never returns 500 for Ollama issues -- service handles all errors internally.

    Args:
        string_id: StringID of the row to get suggestions for.
        source_text: Source text to translate (required).
        target_lang: Target language code (default KR).
        context_before: JSON array of {source, target} pairs before this row.
        context_after: JSON array of {source, target} pairs after this row.

    Returns:
        JSON with suggestions array and status (generated|cached|unavailable|error).
    """
    # Determine entity type from StringID
    entity_type = categorize_by_stringid(string_id)

    # Build surrounding context from before/after params (max 2+2 = 4)
    surrounding_context = []
    if context_before:
        try:
            before_items = json.loads(context_before)
            if isinstance(before_items, list):
                surrounding_context.extend(before_items[:2])
        except (json.JSONDecodeError, TypeError):
            logger.debug(f"[AI Suggestions] Invalid context_before JSON for {string_id}")

    if context_after:
        try:
            after_items = json.loads(context_after)
            if isinstance(after_items, list):
                surrounding_context.extend(after_items[:2])
        except (json.JSONDecodeError, TypeError):
            logger.debug(f"[AI Suggestions] Invalid context_after JSON for {string_id}")

    service = get_ai_suggestion_service()
    result = await service.generate_suggestions(
        string_id=string_id,
        source_text=source_text,
        target_lang=target_lang,
        entity_type=entity_type,
        surrounding_context=surrounding_context,
    )

    return result
