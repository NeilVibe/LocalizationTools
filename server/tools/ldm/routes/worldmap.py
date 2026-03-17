"""WorldMap API endpoints -- map nodes, routes, and coordinate data.

Phase 20: Interactive World Map -- provides REST endpoint for the interactive
world map visualization with node positions and route connections.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends
from loguru import logger

from server.utils.dependencies import get_current_active_user_async
from server.tools.ldm.schemas.worldmap import WorldMapData
from server.tools.ldm.services.worldmap_service import WorldMapService


router = APIRouter(prefix="/worldmap", tags=["WorldMap"])

# Module-level singleton (lazy-initialized on first request)
_worldmap_service: Optional[WorldMapService] = None

# Default base directory for mock_gamedata
_DEFAULT_BASE_DIR = Path(__file__).resolve().parents[4]  # project root


def _get_worldmap_service() -> WorldMapService:
    """Get or create the WorldMapService singleton."""
    global _worldmap_service
    if _worldmap_service is None:
        # Use mock_gamedata if available (Phase 15)
        mock_dir = _DEFAULT_BASE_DIR / "tests" / "fixtures" / "mock_gamedata"
        if mock_dir.is_dir():
            base_dir = mock_dir
        else:
            base_dir = _DEFAULT_BASE_DIR

        logger.info(f"[WorldMap API] Initializing WorldMapService from {base_dir}")
        _worldmap_service = WorldMapService(base_dir=base_dir)

    return _worldmap_service


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/data", response_model=WorldMapData)
async def get_worldmap_data(
    current_user: dict = Depends(get_current_active_user_async),
):
    """Get complete world map dataset with nodes, routes, and bounds.

    Returns all FactionNode positions, NodeWaypointInfo routes,
    and computed coordinate bounds for the map viewport.
    """
    svc = _get_worldmap_service()

    try:
        return svc.get_map_data()
    except Exception as e:
        logger.error(f"[WorldMap API] get_map_data failed: {e}")
        return WorldMapData(nodes=[], routes=[], bounds={})


@router.post("/reload")
async def reload_worldmap(
    current_user: dict = Depends(get_current_active_user_async),
):
    """Force re-initialization of the WorldMapService singleton."""
    global _worldmap_service
    _worldmap_service = None
    svc = _get_worldmap_service()
    data = svc.get_map_data()
    return {
        "status": "reloaded",
        "nodes": len(data.nodes),
        "routes": len(data.routes),
    }
