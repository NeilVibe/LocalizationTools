"""
Phase 45: AI Capabilities API - Runtime AI engine status endpoint.

Exposes AI engine availability to the frontend so UI can
gracefully degrade when engines are missing (Pitfall #2 prevention).

Endpoints:
- GET /ai-capabilities       -> cached capabilities
- POST /ai-capabilities/refresh -> force re-probe
"""
from __future__ import annotations

from fastapi import APIRouter

from loguru import logger

from ..services.ai_capability_service import get_ai_capability_service

router = APIRouter(prefix="/ai-capabilities", tags=["ai-capabilities"])


@router.get("")
async def get_ai_capabilities():
    """
    Get current AI engine availability status.

    Returns cached probe results. First call triggers automatic probe.
    """
    svc = get_ai_capability_service()
    status = svc.get_status()
    return {
        "capabilities": status["capabilities"],
        "light_mode": status["light_mode"],
        "last_check": status["last_check"],
    }


@router.post("/refresh")
async def refresh_ai_capabilities():
    """
    Force re-probe of all AI engines.

    Useful after installing/starting an engine at runtime.
    """
    logger.info("[AI-CAPS] Manual refresh triggered")
    svc = get_ai_capability_service()
    svc.check_all()
    status = svc.get_status()
    return {
        "capabilities": status["capabilities"],
        "light_mode": status["light_mode"],
        "last_check": status["last_check"],
    }
