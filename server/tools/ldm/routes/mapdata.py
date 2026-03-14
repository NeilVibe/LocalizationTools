"""
MapData Context endpoints - image/audio context by string_id.

Provides REST API for looking up image and audio context associated
with translation grid rows, and configuring branch/drive settings.

Phase 5: Visual Polish and Integration (Plan 01)
"""

from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from loguru import logger

from server.utils.dependencies import get_current_active_user_async
from server.tools.ldm.services.mapdata_service import (
    get_mapdata_service,
    KNOWN_BRANCHES,
)

router = APIRouter(tags=["LDM"])


# =============================================================================
# Response Models
# =============================================================================

class ImageContextResponse(BaseModel):
    texture_name: str
    dds_path: str
    thumbnail_url: str
    has_image: bool


class AudioContextResponse(BaseModel):
    event_name: str
    wem_path: str
    script_kr: str
    script_eng: str
    duration_seconds: Optional[float] = None


class CombinedContextResponse(BaseModel):
    string_id: str
    image: Optional[ImageContextResponse] = None
    audio: Optional[AudioContextResponse] = None


class ConfigureRequest(BaseModel):
    branch: str = Field(..., description="Perforce branch name")
    drive: str = Field(..., min_length=1, max_length=1, description="Drive letter")


class StatusResponse(BaseModel):
    loaded: bool
    branch: str
    drive: str
    image_count: int
    audio_count: int
    known_branches: list[str]


class ConfigureResponse(BaseModel):
    success: bool
    branch: str
    drive: str
    message: str


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/mapdata/image/{string_id}", response_model=ImageContextResponse)
async def get_image_context(
    string_id: str,
    current_user: dict = Depends(get_current_active_user_async),
):
    """Get image context (texture name, DDS path, thumbnail) for a string_id."""
    service = get_mapdata_service()
    result = service.get_image_context(string_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"No image context for '{string_id}'")
    return ImageContextResponse(**result.to_dict())


@router.get("/mapdata/audio/{string_id}", response_model=AudioContextResponse)
async def get_audio_context(
    string_id: str,
    current_user: dict = Depends(get_current_active_user_async),
):
    """Get audio context (event name, WEM path, script text) for a string_id."""
    service = get_mapdata_service()
    result = service.get_audio_context(string_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"No audio context for '{string_id}'")
    return AudioContextResponse(**result.to_dict())


@router.get("/mapdata/context/{string_id}", response_model=CombinedContextResponse)
async def get_combined_context(
    string_id: str,
    current_user: dict = Depends(get_current_active_user_async),
):
    """Get both image and audio context for a string_id.

    Returns 200 even if one or both are missing (fields will be null).
    """
    service = get_mapdata_service()
    image = service.get_image_context(string_id)
    audio = service.get_audio_context(string_id)

    return CombinedContextResponse(
        string_id=string_id,
        image=ImageContextResponse(**image.to_dict()) if image else None,
        audio=AudioContextResponse(**audio.to_dict()) if audio else None,
    )


@router.post("/mapdata/configure", response_model=ConfigureResponse)
async def configure_mapdata(
    request: ConfigureRequest,
    current_user: dict = Depends(get_current_active_user_async),
):
    """Configure branch and drive, re-initialize MapDataService."""
    service = get_mapdata_service()

    drive = request.drive.upper().strip()
    if not drive.isalpha():
        raise HTTPException(status_code=400, detail="Drive must be a single letter")

    branch = request.branch.strip()
    if not branch:
        raise HTTPException(status_code=400, detail="Branch name cannot be empty")

    logger.info(
        f"[MAPDATA] User {current_user['username']} configuring: "
        f"branch={branch}, drive={drive}"
    )

    success = service.initialize(branch=branch, drive=drive)

    return ConfigureResponse(
        success=success,
        branch=branch,
        drive=drive,
        message=f"MapData service configured: {drive}:/{branch}"
        if success
        else "Configuration failed - paths may not exist",
    )


@router.get("/mapdata/status", response_model=StatusResponse)
async def get_mapdata_status(
    current_user: dict = Depends(get_current_active_user_async),
):
    """Get MapData service status."""
    service = get_mapdata_service()
    status = service.get_status()
    return StatusResponse(
        **status,
        known_branches=KNOWN_BRANCHES,
    )
