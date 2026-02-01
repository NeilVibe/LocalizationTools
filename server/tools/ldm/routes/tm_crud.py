"""
TM CRUD endpoints - Translation Memory list, get, delete, upload, export.

P10: FULL ABSTRACT + REPO Pattern
- All endpoints use Repository Pattern with permissions baked in
- No direct DB access in routes

P9-ARCH: Uses Repository Pattern for database abstraction.
- Online mode: PostgreSQLTMRepository
- Offline mode: SQLiteTMRepository

EMB-001: Auto-build embeddings+index on TM upload
- After upload, automatically triggers background indexing
- User uploads TM -> automatically ready for semantic search

Note: Upload and Export operations use TMManager directly (complex file parsing).
The Repository pattern handles simpler CRUD operations.

Migrated from api.py lines 1195-1365, 1871-1936
"""

import asyncio
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, BackgroundTasks, Request
from fastapi.responses import Response
from loguru import logger

from server.utils.dependencies import get_current_active_user_async, get_db
from server.tools.ldm.schemas import TMResponse, TMUploadResponse, DeleteResponse

# Repository Pattern imports
from server.repositories import TMRepository, get_tm_repository

# EMB-001: Auto-indexing service
from server.tools.ldm.services import trigger_auto_indexing

router = APIRouter(tags=["LDM"])


@router.post("/tm/upload", response_model=TMUploadResponse)
async def upload_tm(
    request: Request,
    background_tasks: BackgroundTasks,
    name: str = Form(...),
    source_lang: str = Form("ko"),
    target_lang: str = Form("en"),
    description: Optional[str] = Form(None),
    file: UploadFile = File(...),
    # TM mode: "standard" (duplicates merged) or "stringid" (all variations kept)
    mode: str = Form("standard"),
    # Excel column mapping (only used for Excel files)
    source_col: Optional[int] = Form(None),      # Column index for source (0=A)
    target_col: Optional[int] = Form(None),      # Column index for target (1=B)
    stringid_col: Optional[int] = Form(None),    # Column index for StringID (2=C)
    has_header: Optional[bool] = Form(True),     # Whether first row is header
    # EMB-001: Auto-indexing option (default True)
    auto_index: Optional[bool] = Form(True),     # Whether to auto-build indexes after upload
    # ARCH-002: Repository pattern for name uniqueness check
    repo: TMRepository = Depends(get_tm_repository),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Upload a Translation Memory file.

    Supported formats:
    - TXT/TSV: Column 5 = Source, Column 6 = Target
    - XML: StrOrigin = Source, Str = Target
    - XLSX: User-defined columns via source_col, target_col, stringid_col

    Modes:
    - standard: Duplicates merged (most frequent target wins)
    - stringid: All variations kept (same source, different StringIDs)

    EMB-001: Auto-indexing
    - By default, automatically builds embeddings and FAISS indexes after upload
    - Set auto_index=false to skip (manual indexing required later)

    Performance: ~20,000+ entries/second bulk insert
    """
    filename = file.filename or "unknown"
    ext = filename.lower().split('.')[-1] if '.' in filename else ''

    # UI-077 FIX + ARCH-002: Check for duplicate TM name via repository (factory pattern)
    if await repo.check_name_exists(name):
        raise HTTPException(
            status_code=400,
            detail=f"A Translation Memory named '{name}' already exists. Please use a different name."
        )

    if ext not in ('txt', 'tsv', 'xml', 'xlsx', 'xls'):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported TM format: {ext}. Use TXT, TSV, XML, or XLSX."
        )

    logger.info(f"[TM] TM upload started: name={name}, file={filename}, user={current_user['user_id']}, auto_index={auto_index}")

    # TASK-001: Add TrackedOperation for progress tracking
    user_id = current_user["user_id"]
    username = current_user.get("username", "unknown")

    try:
        file_content = await file.read()

        # Run sync TMManager in threadpool to avoid blocking event loop
        def _upload_tm():
            from server.utils.progress_tracker import TrackedOperation

            sync_db = next(get_db())
            try:
                with TrackedOperation(
                    operation_name=f"Upload TM: {name}",
                    user_id=user_id,
                    username=username,
                    tool_name="LDM",
                    function_name="upload_tm",
                    parameters={"name": name, "filename": filename, "mode": mode}
                ) as tracker:
                    tracker.update(10, "Parsing file...")

                    from server.tools.ldm.tm_manager import TMManager
                    tm_manager = TMManager(sync_db)

                    tracker.update(30, "Inserting entries...")

                    result = tm_manager.upload_tm(
                        file_content=file_content,
                        filename=filename,
                        name=name,
                        owner_id=user_id,
                        source_lang=source_lang,
                        target_lang=target_lang,
                        description=description,
                        mode=mode,
                        source_col=source_col if source_col is not None else 0,
                        target_col=target_col if target_col is not None else 1,
                        stringid_col=stringid_col,
                        has_header=has_header if has_header is not None else True
                    )

                    tracker.update(100, f"Complete: {result['entry_count']} entries")
                    return result
            finally:
                sync_db.close()

        result = await asyncio.to_thread(_upload_tm)
        
        # EMB-001: Trigger auto-indexing in background
        if auto_index and result.get("tm_id"):
            tm_id = result["tm_id"]
            logger.info(f"[EMB-001] Scheduling auto-indexing for TM {tm_id}")
            
            # Add to FastAPI background tasks
            # This runs AFTER the response is sent to the client
            background_tasks.add_task(
                trigger_auto_indexing,
                tm_id=tm_id,
                user_id=user_id,
                username=username,
                silent=True  # No toast for auto-operations
            )
            
            # Update response to indicate indexing is scheduled
            result["indexing_status"] = "scheduled"
            logger.info(f"[EMB-001] Auto-indexing scheduled for TM {tm_id}")
        
        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid TM data provided")
    except Exception as e:
        logger.error(f"[TM] TM upload failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="TM upload failed. Check server logs.")


@router.get("/tm", response_model=List[TMResponse])
async def list_tms(
    repo: TMRepository = Depends(get_tm_repository),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    List all Translation Memories accessible to current user.

    P9-ARCH: Uses Repository Pattern - automatically returns TMs from
    PostgreSQL (online) or SQLite (offline) based on user's mode.
    DESIGN-001: Public by default.
    """
    # Repository returns all accessible TMs for the appropriate database
    tms = await repo.get_all()

    # Create TM-like objects for response model compatibility
    class TMLike:
        def __init__(self, data):
            self.id = data.get("id")
            self.name = data.get("name")
            self.description = data.get("description")
            self.source_lang = data.get("source_lang", "ko")
            self.target_lang = data.get("target_lang", "en")
            self.entry_count = data.get("entry_count", 0)
            self.status = data.get("status", "ready")
            self.mode = data.get("mode", "standard")
            self.owner_id = data.get("owner_id") or current_user["user_id"]
            self.created_at = data.get("created_at")
            self.updated_at = data.get("updated_at")
            self.indexed_at = data.get("indexed_at")

    result = [TMLike(tm) if isinstance(tm, dict) else tm for tm in tms]
    logger.info(f"[TM] Listed {len(result)} TMs for user {current_user['user_id']}")
    return result


@router.get("/tm/{tm_id}", response_model=TMResponse)
async def get_tm(
    tm_id: int,
    repo: TMRepository = Depends(get_tm_repository),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Get a Translation Memory by ID.

    P9-ARCH: Uses Repository Pattern - fetches from PostgreSQL (online)
    or SQLite (offline) based on user's mode.
    DESIGN-001: Public by default.
    """
    tm = await repo.get(tm_id)
    if not tm:
        raise HTTPException(status_code=404, detail="Translation Memory not found")

    # Create TM-like object for response model compatibility
    class TMLike:
        def __init__(self, data):
            self.id = data.get("id")
            self.name = data.get("name")
            self.description = data.get("description")
            self.source_lang = data.get("source_lang", "ko")
            self.target_lang = data.get("target_lang", "en")
            self.entry_count = data.get("entry_count", 0)
            self.status = data.get("status", "ready")
            self.mode = data.get("mode", "standard")
            self.owner_id = data.get("owner_id") or current_user["user_id"]
            self.created_at = data.get("created_at")
            self.updated_at = data.get("updated_at")
            self.indexed_at = data.get("indexed_at")

    return TMLike(tm) if isinstance(tm, dict) else tm


@router.delete("/tm/{tm_id}", response_model=DeleteResponse)
async def delete_tm(
    tm_id: int,
    repo: TMRepository = Depends(get_tm_repository),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Delete a Translation Memory and all its entries.

    P9-ARCH: Uses Repository Pattern - deletes from PostgreSQL (online)
    or SQLite (offline) based on user's mode.
    DESIGN-001: Public by default.
    """
    # Get TM first to get entry count
    tm = await repo.get(tm_id)
    if not tm:
        raise HTTPException(status_code=404, detail="Translation Memory not found")

    entry_count = tm.get("entry_count", 0) if isinstance(tm, dict) else getattr(tm, "entry_count", 0)

    # Delete using repository
    deleted = await repo.delete(tm_id)
    if not deleted:
        raise HTTPException(status_code=500, detail="Failed to delete Translation Memory")

    logger.info(f"[TM] Deleted TM: id={tm_id}, entries={entry_count}")
    return {"message": "Translation Memory deleted", "entries_deleted": entry_count}


@router.get("/tm/{tm_id}/export")
async def export_tm(
    tm_id: int,
    format: str = Query("text", regex="^(text|excel|tmx)$"),
    columns: Optional[str] = Query(None, description="Comma-separated list of columns: source_text,target_text,string_id,created_at"),
    current_user: dict = Depends(get_current_active_user_async),
    tm_repo: TMRepository = Depends(get_tm_repository)
):
    """
    Export a Translation Memory in specified format (DESIGN-001: Public by default).

    Formats:
    - text: Tab-separated values (TSV)
    - excel: Excel spreadsheet (.xlsx)
    - tmx: Translation Memory eXchange format

    Columns (optional, comma-separated):
    - source_text (required, always included)
    - target_text (required, always included)
    - string_id
    - created_at

    P10: FULL ABSTRACT - Permission check is INSIDE repository.
    Returns file download.
    """
    logger.info(f"[TM] Exporting TM: tm_id={tm_id}, format={format}, columns={columns}")

    # P10: Get TM via repository (permissions checked inside - returns None if no access)
    tm = await tm_repo.get(tm_id)
    if not tm:
        raise HTTPException(status_code=404, detail="Translation Memory not found")

    # Parse columns if provided
    column_list = None
    if columns:
        column_list = [c.strip() for c in columns.split(",") if c.strip()]

    # Run export in threadpool (uses sync ORM)
    def _export_tm():
        sync_db = next(get_db())
        try:
            from server.tools.ldm.tm_manager import TMManager
            tm_manager = TMManager(sync_db)
            return tm_manager.export_tm(tm_id, format=format, columns=column_list)
        finally:
            sync_db.close()

    result = await asyncio.to_thread(_export_tm)

    logger.success(f"[TM] TM exported: tm_id={tm_id}, entries={result['entry_count']}, format={format}")

    return Response(
        content=result["content"],
        media_type=result["mime_type"],
        headers={
            "Content-Disposition": f'attachment; filename="{result["filename"]}"'
        }
    )
