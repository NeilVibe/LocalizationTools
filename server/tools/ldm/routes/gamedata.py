"""
GameData API endpoints -- folder browsing, column detection, and attribute editing.

Phase 18: Game Dev Grid -- provides REST endpoints for the Game Dev Grid
file explorer to browse gamedata folders, detect XML entity columns, and
save inline edits back to XML files.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger

from server.utils.dependencies import get_current_active_user_async
from server.tools.ldm.schemas.gamedata import (
    BrowseRequest,
    FileColumnsRequest,
    FileColumnsResponse,
    FolderTreeResponse,
    GameDevSaveRequest,
    GameDevSaveResponse,
)
from server.tools.ldm.services.gamedata_browse_service import GameDataBrowseService
from server.tools.ldm.services.gamedata_edit_service import GameDataEditService


router = APIRouter(tags=["GameData"])

# Default base directory for gamedata -- can be overridden via settings
# Uses the mock_gamedata from Phase 15 when available, falls back to project root
_DEFAULT_BASE_DIR = Path(__file__).resolve().parents[4]  # project root


def _get_base_dir() -> Path:
    """Get the base directory for gamedata operations.

    Checks for mock_gamedata first (Phase 15), then falls back to project root.
    """
    mock_dir = _DEFAULT_BASE_DIR / "tests" / "mock_gamedata"
    if mock_dir.is_dir():
        return mock_dir
    return _DEFAULT_BASE_DIR


# =============================================================================
# Endpoints
# =============================================================================


@router.post("/gamedata/browse", response_model=FolderTreeResponse)
async def browse_gamedata(
    request: BrowseRequest,
    current_user: dict = Depends(get_current_active_user_async),
):
    """Browse a gamedata folder and return tree structure with XML metadata.

    Args:
        request: Contains path to browse and optional max_depth.

    Returns:
        FolderTreeResponse with recursive folder tree and XML file metadata.
    """
    base_dir = _get_base_dir()

    try:
        svc = GameDataBrowseService(base_dir=base_dir)
        root_node = svc.scan_folder(request.path, max_depth=request.max_depth)
    except ValueError as e:
        logger.warning(f"[GameData API] Path traversal attempt: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Path not found: {request.path}")

    if not Path(request.path).is_dir():
        raise HTTPException(status_code=404, detail=f"Directory not found: {request.path}")

    return FolderTreeResponse(root=root_node, base_path=str(base_dir))


@router.post("/gamedata/columns", response_model=FileColumnsResponse)
async def detect_columns(
    request: FileColumnsRequest,
    current_user: dict = Depends(get_current_active_user_async),
):
    """Detect dynamic columns for an XML file's entities.

    Used by the frontend to configure grid columns before loading entity data.

    Args:
        request: Contains xml_path to analyze.

    Returns:
        FileColumnsResponse with column hints and editable attribute list.
    """
    base_dir = _get_base_dir()

    if not Path(request.xml_path).is_file():
        raise HTTPException(status_code=404, detail=f"File not found: {request.xml_path}")

    try:
        svc = GameDataBrowseService(base_dir=base_dir)
        result = svc.detect_columns(request.xml_path)
    except ValueError as e:
        logger.warning(f"[GameData API] Path traversal attempt: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    return result


@router.put("/gamedata/save", response_model=GameDevSaveResponse)
async def save_gamedata(
    request: GameDevSaveRequest,
    current_user: dict = Depends(get_current_active_user_async),
):
    """Save an inline edit to a specific XML entity attribute.

    Preserves br-tags correctly through lxml round-trip.

    Args:
        request: Contains xml_path, entity_index, attr_name, and new_value.

    Returns:
        GameDevSaveResponse with success status and message.
    """
    base_dir = _get_base_dir()

    if not Path(request.xml_path).is_file():
        raise HTTPException(status_code=404, detail=f"File not found: {request.xml_path}")

    try:
        svc = GameDataEditService(base_dir=base_dir)
        success = svc.update_entity_attribute(
            xml_path=request.xml_path,
            entity_index=request.entity_index,
            attr_name=request.attr_name,
            new_value=request.new_value,
        )
    except ValueError as e:
        logger.warning(f"[GameData API] Path traversal attempt: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    if not success:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid entity index {request.entity_index}",
        )

    return GameDevSaveResponse(
        success=True,
        message=f"Updated {request.attr_name} on entity {request.entity_index}",
    )
