"""Health check endpoint."""

from fastapi import APIRouter
from loguru import logger

router = APIRouter(tags=["LDM"])


@router.get("/health")
async def health():
    """Health check endpoint for LDM module."""
    logger.info("[HEALTH] LDM health check requested")
    return {
        "status": "ok",
        "module": "LDM (LanguageData Manager)",
        "version": "1.0.0",
        "features": {
            "projects": True,
            "folders": True,
            "files": True,
            "tm": True,
            "pretranslation": True,
            "websocket": True
        }
    }
