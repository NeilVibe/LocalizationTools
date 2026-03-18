"""
MapData Context endpoints - image/audio context by string_id.

Provides REST API for looking up image and audio context associated
with translation grid rows, and configuring branch/drive settings.

Phase 5: Visual Polish and Integration (Plan 01)
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field
from loguru import logger

from server.utils.dependencies import get_current_active_user_async
from server.tools.ldm.services.mapdata_service import (
    get_mapdata_service,
    convert_to_wsl_path,
    KNOWN_BRANCHES,
)
from server.tools.ldm.services.media_converter import get_media_converter

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

@router.get("/mapdata/thumbnail/{texture_name}")
async def get_thumbnail(
    texture_name: str,
):
    """Serve a PNG thumbnail for a DDS texture by name.

    Looks up the texture in the DDS index (case-insensitive), converts
    DDS -> PNG via MediaConverter, and returns PNG bytes with cache headers.
    """
    service = get_mapdata_service()
    dds_path = service._dds_index.get(texture_name.lower())

    # Fallback: check mock_gamedata textures directory
    if not dds_path:
        mock_textures = Path(__file__).resolve().parents[4] / "tests" / "fixtures" / "mock_gamedata" / "textures"
        if mock_textures.is_dir():
            for ext in ['.png', '.dds', '.jpg']:
                candidate = mock_textures / f"{texture_name}{ext}"
                if candidate.exists():
                    dds_path = str(candidate)
                    break
            # Also try subdirectories and case-insensitive match
            if not dds_path:
                for f in mock_textures.rglob("*"):
                    if f.is_file() and f.stem.lower() == texture_name.lower():
                        dds_path = str(f)
                        break

    if dds_path is None:
        raise HTTPException(status_code=404, detail=f"Texture '{texture_name}' not found")

    # Serve PNG/JPG files directly without DDS conversion
    if dds_path.lower().endswith(('.png', '.jpg', '.jpeg')):
        media = "image/png" if dds_path.lower().endswith('.png') else "image/jpeg"
        # Use file mtime as ETag for cache-busting when images are regenerated
        import hashlib
        mtime = str(Path(dds_path).stat().st_mtime)
        etag = hashlib.md5(f"{dds_path}:{mtime}".encode()).hexdigest()[:16]
        return FileResponse(dds_path, media_type=media, headers={
            "Cache-Control": "no-cache, must-revalidate",
            "ETag": f'"{etag}"',
        })

    wsl_path = convert_to_wsl_path(str(dds_path))
    converter = get_media_converter()

    png_bytes = await asyncio.to_thread(
        converter.convert_dds_to_png, Path(wsl_path)
    )
    if png_bytes is None:
        raise HTTPException(status_code=500, detail=f"Failed to convert '{texture_name}'")

    return Response(
        content=png_bytes,
        media_type="image/png",
        headers={"Cache-Control": "no-cache, must-revalidate"},
    )


@router.get("/mapdata/audio/stream/{string_id}")
async def stream_audio(
    string_id: str,
):
    """Stream WAV audio for a string_id.

    Looks up audio context, converts WEM -> WAV via MediaConverter,
    and returns the WAV file.
    """
    service = get_mapdata_service()
    audio_ctx = service.get_audio_context(string_id)
    if audio_ctx is None:
        raise HTTPException(status_code=404, detail=f"No audio for '{string_id}'")

    wsl_path = convert_to_wsl_path(audio_ctx.wem_path)
    converter = get_media_converter()

    wav_path = await asyncio.to_thread(
        converter.convert_wem_to_wav, Path(wsl_path)
    )
    if wav_path is None:
        raise HTTPException(status_code=500, detail="Audio conversion failed")

    return FileResponse(str(wav_path), media_type="audio/wav")


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

    if branch not in KNOWN_BRANCHES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown branch '{branch}'. Must be one of: {KNOWN_BRANCHES}",
        )

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
