"""Health check endpoint."""

import os
import sys

from fastapi import APIRouter, Depends
from loguru import logger
from server.utils.dependencies import get_current_active_user_async

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


@router.get("/system-status")
async def system_status(_user=Depends(get_current_active_user_async)):
    """Return comprehensive system status for the Status page."""
    status = {
        "server": {
            "mode": os.environ.get("DATABASE_MODE", "postgresql"),
            "platform": sys.platform,
            "python_version": sys.version.split()[0],
        },
        "model2vec": {"status": "unknown"},
        "mega_index": {"status": "unknown", "entries": 0},
        "websocket": {"status": "connected"},
    }

    # Model2Vec status
    try:
        from server.tools.shared.embedding_engine import get_embedding_engine
        engine = get_embedding_engine("model2vec")
        if engine._model is not None:
            status["model2vec"] = {"status": "loaded", "dimension": engine.dimension, "name": engine.name}
        else:
            # Try to find the path
            path = engine._find_local_model_path()
            if path:
                status["model2vec"] = {"status": "found_not_loaded", "path": str(path)}
            else:
                status["model2vec"] = {"status": "not_found", "hint": "Place Model2Vec/ folder next to LocaNext.exe"}
    except Exception as e:
        status["model2vec"] = {"status": "error", "error": str(e)}

    # MegaIndex status
    try:
        from server.tools.ldm.services.mega_index import get_mega_index
        mi = get_mega_index()
        total = len(mi.stringid_to_translations) if mi._built else 0
        mi_status = {"status": "built" if mi._built else "not_built", "entries": total}
        if mi._built:
            ec = mi.entity_counts()
            mi_status["counts"] = {
                "knowledge": ec.get("knowledge", 0),
                "characters": ec.get("character", 0),
                "items": ec.get("item", 0),
                "regions": ec.get("region", 0),
                "factions": ec.get("faction", 0),
                "skills": ec.get("skill", 0),
                "gimmicks": ec.get("gimmick", 0),
                "dds": len(mi.dds_by_stem),
                "wem": len(mi.wem_by_event),
                "strorigins": len(mi.stringid_to_strorigin),
            }
            mi_status["build_time"] = round(mi._build_time, 2)
        status["mega_index"] = mi_status
    except Exception as e:
        status["mega_index"] = {"status": "error", "error": str(e)}

    # Qwen status
    try:
        from server.tools.shared.embedding_engine import is_light_mode
        status["qwen"] = {"status": "unavailable" if is_light_mode() else "available"}
    except Exception:
        status["qwen"] = {"status": "unknown"}

    # ahocorasick
    try:
        import ahocorasick  # noqa: F401
        status["ahocorasick"] = {"status": "installed"}
    except ImportError:
        status["ahocorasick"] = {"status": "fallback"}

    return status
