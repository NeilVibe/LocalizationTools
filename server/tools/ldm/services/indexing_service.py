"""
EMB-001: Auto-build Indexing Service

Provides background index building for TMs after upload.
Automatically triggers:
1. Embedding creation (WHOLE + LINE) via EmbeddingEngine
2. FAISS index building via FAISSManager
3. Hash lookup creation

Usage:
    from server.tools.ldm.services.indexing_service import trigger_auto_indexing
    
    # In route after TM upload:
    background_tasks.add_task(
        trigger_auto_indexing,
        tm_id=result["tm_id"],
        user_id=current_user["user_id"],
        username=current_user.get("username", "system")
    )
"""

from loguru import logger

from server.utils.dependencies import get_db


def trigger_auto_indexing(
    tm_id: int,
    user_id: int,
    username: str = "system",
    silent: bool = True
) -> dict:
    """
    Trigger automatic index building for a TM.
    
    Designed to run as a BackgroundTask after TM upload.
    Uses TMIndexer.build_indexes() which creates:
    - Hash indexes (whole_lookup.pkl, line_lookup.pkl)
    - Embeddings (whole.npy, line.npy + mappings)
    - FAISS indexes (whole.index, line.index)
    
    Args:
        tm_id: Translation Memory ID to index
        user_id: User ID for tracking
        username: Username for tracking
        silent: If True, no toast notification (default True for auto-indexing)
    
    Returns:
        Dict with indexing results or error info
    """
    from server.utils.progress_tracker import TrackedOperation
    from server.tools.ldm.tm_indexer import TMIndexer
    
    logger.info(f"[EMB-001] Auto-indexing triggered for TM {tm_id}")
    
    sync_db = next(get_db())
    try:
        # Use TrackedOperation for progress tracking
        # silent=True means no toast notification (background auto-operation)
        with TrackedOperation(
            operation_name=f"Auto-Index TM (id={tm_id})",
            user_id=user_id,
            username=username,
            tool_name="LDM",
            function_name="auto_index_tm",
            total_steps=4,
            parameters={"tm_id": tm_id, "auto": True},
            silent=silent  # Silent by default for auto-operations
        ) as tracker:
            
            # Progress callback for detailed tracking
            def progress_callback(stage: str, current: int, total: int):
                progress_pct = (current / total) * 100 if total > 0 else 0
                tracker.update(progress_pct, stage, current, total)
            
            # Build all indexes
            indexer = TMIndexer(sync_db)
            result = indexer.build_indexes(tm_id, progress_callback=progress_callback)
            
            logger.success(
                f"[EMB-001] Auto-indexing complete for TM {tm_id}: "
                f"entries={result['entry_count']}, "
                f"whole_emb={result['whole_embeddings_count']}, "
                f"line_emb={result['line_embeddings_count']}, "
                f"time={result['time_seconds']}s"
            )
            
            return result
            
    except Exception as e:
        logger.error(f"[EMB-001] Auto-indexing failed for TM {tm_id}: {e}", exc_info=True)
        return {
            "tm_id": tm_id,
            "status": "error",
            "error": str(e)
        }
    finally:
        sync_db.close()


def check_indexing_needed(tm_id: int) -> bool:
    """
    Check if a TM needs indexing.
    
    Returns True if:
    - No indexes exist
    - Indexes are stale (TM updated after last index build)
    
    Args:
        tm_id: Translation Memory ID
        
    Returns:
        True if indexing is needed
    """
    from pathlib import Path
    import json
    from datetime import datetime
    
    # Check if index directory exists
    data_dir = Path(__file__).parent.parent.parent.parent / "data" / "ldm_tm" / str(tm_id)
    metadata_path = data_dir / "metadata.json"
    
    if not metadata_path.exists():
        logger.debug(f"[EMB-001] TM {tm_id} has no indexes - needs indexing")
        return True
    
    # Check if index is stale
    try:
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        
        created_at = metadata.get("created_at")
        if not created_at:
            return True
        
        # Get TM updated_at from DB
        sync_db = next(get_db())
        try:
            from server.database.models import LDMTranslationMemory
            tm = sync_db.query(LDMTranslationMemory).filter(
                LDMTranslationMemory.id == tm_id
            ).first()
            
            if not tm:
                return False  # TM doesn't exist
            
            if tm.updated_at:
                index_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                tm_time = tm.updated_at
                
                # Handle timezone-aware vs naive comparison
                if index_time.tzinfo is not None and tm_time.tzinfo is None:
                    index_time = index_time.replace(tzinfo=None)
                elif index_time.tzinfo is None and tm_time.tzinfo is not None:
                    tm_time = tm_time.replace(tzinfo=None)
                
                if tm_time > index_time:
                    logger.debug(f"[EMB-001] TM {tm_id} indexes are stale - needs re-indexing")
                    return True
        finally:
            sync_db.close()
            
    except Exception as e:
        logger.warning(f"[EMB-001] Error checking index status for TM {tm_id}: {e}")
        return True  # When in doubt, re-index
    
    logger.debug(f"[EMB-001] TM {tm_id} indexes are current")
    return False


async def trigger_auto_indexing_async(
    tm_id: int,
    user_id: int,
    username: str = "system",
    silent: bool = True
) -> dict:
    """
    Async wrapper for trigger_auto_indexing.
    
    For use with asyncio.create_task() or similar async patterns.
    """
    import asyncio
    return await asyncio.to_thread(
        trigger_auto_indexing,
        tm_id=tm_id,
        user_id=user_id,
        username=username,
        silent=silent
    )
