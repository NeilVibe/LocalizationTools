"""
Context API endpoints -- entity context by string_id or raw text.

Provides REST API for looking up rich entity context (characters, locations,
images, audio) using GlossaryService detection + MapDataService media lookups.

Phase 5.1: Contextual Intelligence & QA Engine (Plan 03)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from loguru import logger

from server.utils.dependencies import get_current_active_user_async
from server.tools.ldm.services.context_service import get_context_service


router = APIRouter(tags=["LDM-Context"])


# =============================================================================
# Request/Response Models
# =============================================================================


class DetectRequest(BaseModel):
    """Request body for text-based entity detection."""
    text: str = Field(..., description="Text to scan for entities")


class DetectedEntityResponse(BaseModel):
    """A single detected entity in text."""
    term: str
    start: int
    end: int
    type: str


class EntityResponse(BaseModel):
    """A resolved entity with metadata and media."""
    name: str
    entity_type: str
    strkey: str
    knowledge_key: str
    source_file: str
    image: Optional[Dict[str, Any]] = None
    audio: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = {}


class EntityContextResponse(BaseModel):
    """Full entity context response."""
    entities: List[EntityResponse] = []
    detected_in_text: List[DetectedEntityResponse] = []
    string_id_context: Dict[str, Any] = {}


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/context/status")
async def get_context_status(
    current_user: dict = Depends(get_current_active_user_async),
):
    """Get context service status (glossary + mapdata)."""
    service = get_context_service()
    return service.get_status()


@router.get("/context/{string_id}", response_model=EntityContextResponse)
async def get_context_by_string_id(
    string_id: str,
    source_text: str = Query(default="", description="Source text for entity detection"),
    current_user: dict = Depends(get_current_active_user_async),
):
    """Get entity context for a string_id.

    Combines direct StringID media lookup with entity detection from source_text.
    Returns empty context (not error) when services are not loaded.
    """
    service = get_context_service()
    result = service.resolve_context_for_row(string_id, source_text)
    return EntityContextResponse(**result.to_dict())


@router.post("/context/detect", response_model=EntityContextResponse)
async def detect_entities_in_text(
    request: DetectRequest,
    current_user: dict = Depends(get_current_active_user_async),
):
    """Detect entities in raw text and return their context.

    Scans text using GlossaryService AC automaton, resolves media for each
    detected entity via MapDataService.
    """
    service = get_context_service()
    result = service.resolve_context(request.text)
    return EntityContextResponse(**result.to_dict())
