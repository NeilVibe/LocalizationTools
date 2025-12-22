"""
Settings endpoints - Embedding engine configuration.

Migrated from api.py lines 3049-3144
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from loguru import logger

from server.utils.dependencies import get_current_active_user_async
from server.tools.ldm.schemas import (
    EmbeddingEngineInfo, EmbeddingEngineResponse, SetEngineRequest
)

router = APIRouter(tags=["LDM"])


@router.get("/settings/embedding-engines", response_model=List[EmbeddingEngineInfo])
async def list_embedding_engines(
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    List available embedding engines.

    Returns info about each engine for UI display.
    """
    from server.tools.shared import get_available_engines
    return get_available_engines()


@router.get("/settings/embedding-engine", response_model=EmbeddingEngineResponse)
async def get_current_embedding_engine(
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Get the currently selected embedding engine.
    """
    from server.tools.shared import get_current_engine_name, get_embedding_engine

    engine_name = get_current_engine_name()
    engine = get_embedding_engine(engine_name)

    return EmbeddingEngineResponse(
        current_engine=engine_name,
        engine_name=engine.name
    )


@router.post("/settings/embedding-engine", response_model=EmbeddingEngineResponse)
async def set_embedding_engine(
    request: SetEngineRequest,
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Change the embedding engine.

    Options:
    - "model2vec": Fast (79x), lightweight, good for real-time (DEFAULT)
    - "qwen": Deep semantic, heavy, good for batch/quality work

    Note: Changing engine requires re-indexing TMs for best results.
    Existing indexes will still work but may have dimension mismatches.

    TASK-002: Returns warning when switching to Qwen (slower engine).
    """
    from server.tools.shared import set_current_engine, get_embedding_engine, get_current_engine_name

    try:
        previous_engine = get_current_engine_name()
        set_current_engine(request.engine)
        engine = get_embedding_engine(request.engine)

        logger.info(f"User {current_user['username']} switched embedding engine: {previous_engine} → {request.engine}")

        # TASK-002: Add warning when switching to Qwen (slower engine)
        warning = None
        if request.engine.lower() == "qwen":
            warning = (
                "Qwen engine is ~30x slower than Model2Vec. "
                "Syncing large TMs may take significantly longer. "
                "Recommended for batch processing or when quality is critical."
            )
            logger.warning(f"User {current_user['username']} switched to Qwen engine (slower)")

        return EmbeddingEngineResponse(
            current_engine=get_current_engine_name(),
            engine_name=engine.name,
            warning=warning
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
