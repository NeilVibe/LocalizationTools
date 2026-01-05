"""
File endpoints - Upload, download, list, preview files.

Migrated from api.py lines 392-658, 2448-2779
"""

import asyncio
from io import BytesIO
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select
from loguru import logger

from server.utils.dependencies import get_async_db, get_current_active_user_async, get_db
from server.database.models import LDMProject, LDMFile, LDMFolder, LDMRow
from server.tools.ldm.schemas import FileResponse, FileToTMRequest
from server.tools.ldm.permissions import can_access_project, can_access_file

router = APIRouter(tags=["LDM"])


# =============================================================================
# File CRUD Endpoints
# =============================================================================

@router.get("/projects/{project_id}/files", response_model=List[FileResponse])
async def list_files(
    project_id: int,
    folder_id: Optional[int] = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """List files in a project, optionally filtered by folder."""
    # Verify project exists
    result = await db.execute(
        select(LDMProject).where(LDMProject.id == project_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")

    # Check access permission
    if not await can_access_project(db, project_id, current_user):
        raise HTTPException(status_code=404, detail="Resource not found")

    query = select(LDMFile).where(LDMFile.project_id == project_id)
    if folder_id is not None:
        query = query.where(LDMFile.folder_id == folder_id)

    result = await db.execute(query)
    files = result.scalars().all()

    return files


@router.get("/files", response_model=List[FileResponse])
async def list_all_files(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    UI-074 FIX: List all files across all accessible projects.
    Used by ReferenceSettingsModal to show available reference files.
    """
    from server.tools.ldm.permissions import get_accessible_projects

    # Get all accessible projects for user
    accessible_projects = await get_accessible_projects(db, current_user)
    project_ids = [p.id for p in accessible_projects]

    if not project_ids:
        return []

    # Get files from all accessible projects
    query = (
        select(LDMFile)
        .where(LDMFile.project_id.in_(project_ids))
        .order_by(LDMFile.updated_at.desc())
        .offset(offset)
        .limit(limit)
    )

    result = await db.execute(query)
    files = result.scalars().all()

    return files


@router.get("/files/{file_id}", response_model=FileResponse)
async def get_file(
    file_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """Get file metadata by ID. P9: Falls back to SQLite for local files."""
    result = await db.execute(
        select(LDMFile).where(LDMFile.id == file_id)
    )
    file = result.scalar_one_or_none()

    if not file:
        # P9: Fallback to SQLite for local files
        return await _get_local_file_metadata(file_id)

    if not await can_access_file(db, file_id, current_user):
        raise HTTPException(status_code=404, detail="Resource not found")

    return file


@router.post("/files/upload", response_model=FileResponse)
async def upload_file(
    project_id: Optional[int] = Form(None),  # Optional when storage=local
    folder_id: Optional[int] = Form(None),
    file: UploadFile = File(...),
    # P9: Storage destination - 'server' (PostgreSQL) or 'local' (SQLite Offline Storage)
    storage: Optional[str] = Form("server"),
    # Excel column mapping (optional, only used for Excel files)
    source_col: Optional[int] = Form(None),      # Column index for source (0=A, 1=B, etc.)
    target_col: Optional[int] = Form(None),      # Column index for target
    stringid_col: Optional[int] = Form(None),    # Column index for StringID (None = 2-column mode)
    has_header: Optional[bool] = Form(True),     # Whether first row is header
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Upload a localization file (TXT/XML/Excel), parse it, and store rows in database.

    P9: Unified endpoint for both online (PostgreSQL) and offline (SQLite) storage.
    - storage='server' (default): Saves to PostgreSQL, requires project_id
    - storage='local': Saves to SQLite Offline Storage, project_id optional

    Supported formats:
    - TXT/TSV: Tab-delimited, columns 0-4=StringID, 5=Source(KR), 6=Target, 7+=extra
    - XML: LocStr elements with StringId, StrOrigin(source), Str(target), other attrs=extra
    - Excel: User-defined columns via source_col, target_col, stringid_col parameters
      - 2-column mode: Source + Target (default: A, B)
      - 3-column mode: Source + Target + StringID (e.g., A, B, C)

    Full Structure Preservation:
    - File-level metadata stored in LDMFile.extra_data (encoding, root element, etc.)
    - Row-level extra data stored in LDMRow.extra_data (extra columns/attributes)
    - Enables FULL reconstruction of original file format
    """
    # P9: Route to local storage if requested
    storage_type = storage or "server"
    if storage_type == "local":
        return await _upload_to_local_storage(
            file=file,
            source_col=source_col,
            target_col=target_col,
            stringid_col=stringid_col,
            has_header=has_header
        )

    # Server storage requires project_id
    if not project_id:
        raise HTTPException(status_code=400, detail="project_id is required for server storage")

    # Verify project exists
    result = await db.execute(
        select(LDMProject).where(LDMProject.id == project_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")

    # Check access permission
    if not await can_access_project(db, project_id, current_user):
        raise HTTPException(status_code=404, detail="Resource not found")

    # Verify folder exists (if provided)
    if folder_id:
        result = await db.execute(
            select(LDMFolder).where(
                LDMFolder.id == folder_id,
                LDMFolder.project_id == project_id
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Folder not found")

    # DB-002: Per-parent unique names with auto-rename
    from server.tools.ldm.utils.naming import generate_unique_name
    filename = file.filename or "unknown"
    filename = await generate_unique_name(
        db, LDMFile, filename,
        project_id=project_id,
        folder_id=folder_id
    )

    # Determine file type and parse
    ext = filename.lower().split('.')[-1] if '.' in filename else ''

    file_metadata = None
    if ext in ('txt', 'tsv'):
        from server.tools.ldm.file_handlers.txt_handler import parse_txt_file, get_file_format, get_source_language, get_file_metadata
        file_content = await file.read()
        rows_data = parse_txt_file(file_content, filename)
        file_format = get_file_format()
        source_lang = get_source_language()
        file_metadata = get_file_metadata()
    elif ext == 'xml':
        from server.tools.ldm.file_handlers.xml_handler import parse_xml_file, get_file_format, get_source_language, get_file_metadata
        file_content = await file.read()
        rows_data = parse_xml_file(file_content, filename)
        file_format = get_file_format()
        source_lang = get_source_language()
        file_metadata = get_file_metadata()
    elif ext in ('xlsx', 'xls'):
        from server.tools.ldm.file_handlers.excel_handler import parse_excel_file, get_file_format, get_source_language, get_file_metadata
        file_content = await file.read()
        # Use provided column mappings or defaults (A=0, B=1)
        rows_data = parse_excel_file(
            file_content,
            filename,
            source_col=source_col if source_col is not None else 0,
            target_col=target_col if target_col is not None else 1,
            stringid_col=stringid_col,  # None means 2-column mode
            has_header=has_header if has_header is not None else True
        )
        file_format = get_file_format()
        source_lang = get_source_language()
        file_metadata = get_file_metadata()
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format: {ext}. Use TXT, TSV, XML, or Excel (XLSX/XLS)."
        )

    if not rows_data:
        raise HTTPException(
            status_code=400,
            detail="No valid rows found in file"
        )

    # TASK-001: Add TrackedOperation for progress tracking on large files
    # Run row insertion in thread with progress tracking
    user_id = current_user["user_id"]
    username = current_user.get("username", "unknown")
    total_rows = len(rows_data)

    def _insert_file_and_rows():
        from server.utils.progress_tracker import TrackedOperation

        sync_db = next(get_db())
        try:
            with TrackedOperation(
                operation_name=f"Upload: {filename}",
                user_id=user_id,
                username=username,
                tool_name="LDM",
                function_name="upload_file",
                parameters={"filename": filename, "row_count": total_rows}
            ) as tracker:
                # Create file record
                new_file = LDMFile(
                    project_id=project_id,
                    folder_id=folder_id,
                    name=filename,
                    original_filename=filename,
                    format=file_format,
                    row_count=total_rows,
                    source_language=source_lang,
                    target_language=None,
                    extra_data=file_metadata
                )
                sync_db.add(new_file)
                sync_db.flush()  # Get the file ID

                tracker.update(10, "File record created", 1, total_rows + 1)

                # Create row records with progress
                for i, row_data in enumerate(rows_data):
                    row = LDMRow(
                        file_id=new_file.id,
                        row_num=row_data["row_num"],
                        string_id=row_data["string_id"],
                        source=row_data["source"],
                        target=row_data["target"],
                        status=row_data["status"],
                        extra_data=row_data.get("extra_data")
                    )
                    sync_db.add(row)

                    # Update progress every 100 rows
                    if (i + 1) % 100 == 0 or i == total_rows - 1:
                        progress_pct = 10 + ((i + 1) / total_rows) * 90
                        tracker.update(progress_pct, f"Row {i + 1}/{total_rows}", i + 1, total_rows)

                sync_db.commit()
                sync_db.refresh(new_file)

                return {
                    "id": new_file.id,
                    "project_id": new_file.project_id,
                    "folder_id": new_file.folder_id,
                    "name": new_file.name,
                    "original_filename": new_file.original_filename,
                    "format": new_file.format,
                    "row_count": new_file.row_count,
                    "source_language": new_file.source_language,
                    "target_language": new_file.target_language,
                    "created_at": new_file.created_at,
                    "updated_at": new_file.updated_at
                }
        finally:
            sync_db.close()

    result = await asyncio.to_thread(_insert_file_and_rows)

    logger.success(f"File uploaded: id={result['id']}, name='{filename}', rows={total_rows}, has_metadata={file_metadata is not None}")

    # Return FileResponse-compatible dict
    return result


@router.patch("/files/{file_id}/move")
async def move_file_to_folder(
    file_id: int,
    folder_id: Optional[int] = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Move a file to a different folder (or root of project if folder_id is None).

    Used for drag-and-drop file organization in FileExplorer.
    """
    from pydantic import BaseModel

    # Get file
    result = await db.execute(
        select(LDMFile).where(LDMFile.id == file_id)
    )
    file = result.scalar_one_or_none()

    if not file:
        # P9: Check if it's a local file - move not supported for local files
        from server.database.offline import get_offline_db
        offline_db = get_offline_db()
        if offline_db.get_local_file(file_id):
            raise HTTPException(
                status_code=400,
                detail="Cannot move local files to folders. Upload to server first."
            )
        raise HTTPException(status_code=404, detail="File not found")

    # Check access permission
    if not await can_access_project(db, file.project_id, current_user):
        raise HTTPException(status_code=403, detail="Not authorized to modify this file")

    # If folder_id provided, verify folder exists and belongs to same project
    if folder_id is not None:
        result = await db.execute(
            select(LDMFolder).where(
                LDMFolder.id == folder_id,
                LDMFolder.project_id == file.project_id
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Target folder not found or invalid")

    # Update file's folder_id
    file.folder_id = folder_id
    await db.commit()

    logger.success(f"File moved: id={file_id}, new_folder={folder_id}")

    return {"success": True, "file_id": file_id, "folder_id": folder_id}


@router.patch("/files/{file_id}/move-cross-project")
async def move_file_cross_project(
    file_id: int,
    target_project_id: int,
    target_folder_id: Optional[int] = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    EXPLORER-005: Move a file to a different project.
    EXPLORER-009: Requires 'cross_project_move' capability.
    """
    # Get file
    result = await db.execute(
        select(LDMFile).where(LDMFile.id == file_id)
    )
    file = result.scalar_one_or_none()

    if not file:
        # P9: Check if it's a local file - cross-project move not supported
        from server.database.offline import get_offline_db
        offline_db = get_offline_db()
        if offline_db.get_local_file(file_id):
            raise HTTPException(
                status_code=400,
                detail="Cannot move local files between projects. Upload to server first."
            )
        raise HTTPException(status_code=404, detail="File not found")

    # Check access to source project
    if not await can_access_project(db, file.project_id, current_user):
        raise HTTPException(status_code=404, detail="File not found")

    # Check access to destination project
    if not await can_access_project(db, target_project_id, current_user):
        raise HTTPException(status_code=404, detail="Destination project not found")

    # EXPLORER-009: Check capability for cross-project move
    from ..permissions import require_capability
    await require_capability(db, current_user, "cross_project_move")

    # Validate target folder if specified
    if target_folder_id is not None:
        result = await db.execute(
            select(LDMFolder).where(
                LDMFolder.id == target_folder_id,
                LDMFolder.project_id == target_project_id
            )
        )
        target_folder = result.scalar_one_or_none()
        if not target_folder:
            raise HTTPException(status_code=404, detail="Target folder not found")

    source_project_id = file.project_id

    # DB-002: Check for naming conflicts and auto-rename if needed
    from server.tools.ldm.utils.naming import generate_unique_name
    new_name = await generate_unique_name(
        db, LDMFile, file.name,
        project_id=target_project_id,
        folder_id=target_folder_id
    )

    # Update file
    file.name = new_name
    file.project_id = target_project_id
    file.folder_id = target_folder_id
    await db.commit()

    logger.success(f"File moved cross-project: id={file_id}, from project {source_project_id} to {target_project_id}")
    return {
        "success": True,
        "file_id": file_id,
        "new_name": new_name,
        "target_project_id": target_project_id,
        "target_folder_id": target_folder_id
    }


@router.post("/files/{file_id}/copy")
async def copy_file(
    file_id: int,
    target_project_id: Optional[int] = None,
    target_folder_id: Optional[int] = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Copy a file to a different location.
    EXPLORER-001: Ctrl+C/V file operations.

    If target_project_id is None, copies to same project.
    If target_folder_id is None, copies to project root.
    Auto-renames if duplicate name exists.
    """
    # Get source file
    result = await db.execute(
        select(LDMFile).where(LDMFile.id == file_id)
    )
    source_file = result.scalar_one_or_none()

    if not source_file:
        # P9: Check if it's a local file - copy to project not supported
        from server.database.offline import get_offline_db
        offline_db = get_offline_db()
        if offline_db.get_local_file(file_id):
            raise HTTPException(
                status_code=400,
                detail="Cannot copy local files to projects. Upload to server first."
            )
        raise HTTPException(status_code=404, detail="File not found")

    # Check access permission for source
    if not await can_access_project(db, source_file.project_id, current_user):
        raise HTTPException(status_code=404, detail="File not found")

    # Determine target project
    dest_project_id = target_project_id or source_file.project_id

    # Check access permission for destination
    if target_project_id and target_project_id != source_file.project_id:
        if not await can_access_project(db, target_project_id, current_user):
            raise HTTPException(status_code=404, detail="Destination project not found")

    # Generate unique name for copy
    from server.tools.ldm.utils.naming import generate_unique_name
    new_name = await generate_unique_name(
        db, LDMFile, source_file.name,
        project_id=dest_project_id,
        folder_id=target_folder_id
    )

    # Create copy of file metadata
    new_file = LDMFile(
        name=new_name,
        original_filename=source_file.original_filename,
        format=source_file.format,
        source_language=source_file.source_language,
        target_language=source_file.target_language,
        row_count=source_file.row_count,
        project_id=dest_project_id,
        folder_id=target_folder_id,
        extra_data=source_file.extra_data
    )
    db.add(new_file)
    await db.flush()

    # Copy all rows
    from server.database.models import LDMRow
    result = await db.execute(
        select(LDMRow).where(LDMRow.file_id == file_id)
    )
    source_rows = result.scalars().all()

    for row in source_rows:
        new_row = LDMRow(
            file_id=new_file.id,
            row_num=row.row_num,
            string_id=row.string_id,
            source=row.source,
            target=row.target,
            memo=row.memo,
            status=row.status,
            extra_data=row.extra_data
        )
        db.add(new_row)

    await db.commit()
    await db.refresh(new_file)

    logger.success(f"File copied: {source_file.name} -> {new_file.name}, id={new_file.id}")
    return {
        "success": True,
        "new_file_id": new_file.id,
        "name": new_file.name,
        "row_count": len(source_rows)
    }


@router.patch("/files/{file_id}/rename")
async def rename_file(
    file_id: int,
    name: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """Rename a file. P9: Falls back to SQLite for local files."""
    # Get file
    result = await db.execute(
        select(LDMFile).where(LDMFile.id == file_id)
    )
    file = result.scalar_one_or_none()

    if not file:
        # P9: Fallback to SQLite for local files
        return await _rename_local_file(file_id, name)

    # Check access permission
    if not await can_access_project(db, file.project_id, current_user):
        raise HTTPException(status_code=403, detail="Not authorized to modify this file")

    # DB-002: Per-parent unique names
    from server.tools.ldm.utils.naming import check_name_exists
    if await check_name_exists(
        db, LDMFile, name,
        project_id=file.project_id,
        folder_id=file.folder_id,
        exclude_id=file_id
    ):
        raise HTTPException(status_code=400, detail=f"A file named '{name}' already exists in this folder. Please use a different name.")

    old_name = file.name
    file.name = name
    await db.commit()

    logger.success(f"File renamed: id={file_id}, '{old_name}' -> '{name}'")
    return {"success": True, "file_id": file_id, "name": name}


@router.delete("/files/{file_id}")
async def delete_file(
    file_id: int,
    permanent: bool = Query(False, description="If true, permanently delete instead of moving to trash"),
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Delete a file and all its rows.
    EXPLORER-008: By default, moves to trash (soft delete). Use permanent=true for hard delete.
    P9: Falls back to SQLite for local files.
    """
    # Get file
    result = await db.execute(
        select(LDMFile).where(LDMFile.id == file_id)
    )
    file = result.scalar_one_or_none()

    if not file:
        # P9: Fallback to SQLite for local files
        return await _delete_local_file(file_id)

    # Check access permission
    if not await can_access_project(db, file.project_id, current_user):
        raise HTTPException(status_code=403, detail="Not authorized to delete this file")

    file_name = file.name

    if not permanent:
        # EXPLORER-008: Soft delete - move to trash
        from .trash import move_to_trash, serialize_file_for_trash

        # Serialize file data for restore
        file_data = await serialize_file_for_trash(db, file)

        # Move to trash
        await move_to_trash(
            db,
            item_type="file",
            item_id=file.id,
            item_name=file.name,
            item_data=file_data,
            parent_project_id=file.project_id,
            parent_folder_id=file.folder_id,
            deleted_by=current_user["user_id"]
        )

    # Hard delete the original
    await db.delete(file)
    await db.commit()

    action = "permanently deleted" if permanent else "moved to trash"
    logger.info(f"File {action}: id={file_id}, name='{file_name}'")
    return {"message": f"File {action}", "file_id": file_id}


@router.post("/files/excel-preview")
async def excel_preview(
    file: UploadFile = File(...),
    max_rows: int = Query(5, ge=1, le=20),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Get a preview of an Excel file for column mapping UI.

    Returns:
        - sheet_name: Name of the active sheet
        - headers: Column headers (from first row)
        - sample_rows: First N rows of data
        - total_rows: Total row count

    Use this before uploading to let users select which columns
    are Source, Target, and StringID.
    """
    filename = file.filename or "unknown"
    ext = filename.lower().split('.')[-1] if '.' in filename else ''

    if ext not in ('xlsx', 'xls'):
        raise HTTPException(
            status_code=400,
            detail=f"Excel preview only supports XLSX/XLS files, got: {ext}"
        )

    try:
        from server.tools.ldm.file_handlers.excel_handler import get_excel_preview
        file_content = await file.read()
        preview = get_excel_preview(file_content, max_rows=max_rows)
        return preview
    except Exception as e:
        logger.error(f"Excel preview failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# File to TM Conversion
# =============================================================================

@router.post("/files/{file_id}/register-as-tm")
async def register_file_as_tm(
    file_id: int,
    request: FileToTMRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Convert an LDM file into a Translation Memory.

    Takes all source/target pairs from the file and creates a new TM.
    """
    # Get file info
    result = await db.execute(
        select(LDMFile).where(LDMFile.id == file_id)
    )
    file = result.scalar_one_or_none()

    # P9: Fallback to SQLite for local files
    if not file:
        return await _register_local_file_as_tm(file_id, request, current_user)

    # Check access permission
    if not await can_access_file(db, file_id, current_user):
        raise HTTPException(status_code=404, detail="Resource not found")

    logger.info(f"Converting file to TM: file_id={file_id}, name={request.name}")

    try:
        # Get all rows from the file
        result = await db.execute(
            select(LDMRow).where(
                LDMRow.file_id == file_id,
                LDMRow.source.isnot(None),
                LDMRow.source != "",
                LDMRow.target.isnot(None),
                LDMRow.target != ""
            ).order_by(LDMRow.row_num)
        )
        rows = result.scalars().all()

        if not rows:
            raise HTTPException(status_code=400, detail="File has no translatable rows")

        # Create TM entries data
        entries_data = [
            {"source": row.source, "target": row.target}
            for row in rows
        ]

        # Run sync TMManager in threadpool to avoid blocking event loop
        def _create_tm():
            sync_db = next(get_db())
            try:
                from server.tools.ldm.tm_manager import TMManager
                tm_manager = TMManager(sync_db)

                # Create TM
                tm = tm_manager.create_tm(
                    name=request.name,
                    owner_id=current_user["user_id"],
                    source_lang="ko",  # Default, can be extended
                    target_lang=request.language,
                    description=request.description or f"Created from file: {file.name}"
                )

                # Add entries in bulk
                import time
                start_time = time.time()
                entry_count = tm_manager.add_entries_bulk(tm.id, entries_data)
                elapsed = time.time() - start_time

                return {
                    "tm_id": tm.id,
                    "name": tm.name,
                    "entry_count": entry_count,
                    "status": tm.status,
                    "time_seconds": round(elapsed, 2),
                    "rate_per_second": int(entry_count / elapsed) if elapsed > 0 else 0,
                    "source_file": file.name
                }
            finally:
                sync_db.close()

        result = await asyncio.to_thread(_create_tm)

        logger.info(f"TM created from file: tm_id={result['tm_id']}, entries={result['entry_count']}")
        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid file format or data")
    except Exception as e:
        logger.error(f"File to TM conversion failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Conversion failed. Check server logs.")


# =============================================================================
# File Download/Export
# =============================================================================

@router.get("/files/{file_id}/download")
async def download_file(
    file_id: int,
    status_filter: Optional[str] = Query(None, description="Filter by status: reviewed, translated, all"),
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Download a file with current translations.

    Rebuilds the file from database rows in the original format.
    Uses extra_data for FULL structure preservation (extra columns, attributes, etc.)

    P9: Unified endpoint - works for both PostgreSQL files and SQLite local files.

    Query params:
    - status_filter: "reviewed" (confirmed only), "translated" (translated+reviewed), "all" (everything)
    """
    # Get file info from PostgreSQL
    result = await db.execute(
        select(LDMFile).where(LDMFile.id == file_id)
    )
    file = result.scalar_one_or_none()

    # P9: Fallback to SQLite for local files
    if not file:
        return await _download_local_file(file_id, status_filter)

    # Check access permission for PostgreSQL files
    if not await can_access_file(db, file_id, current_user):
        raise HTTPException(status_code=404, detail="Resource not found")

    # Get file-level metadata for reconstruction
    file_metadata = file.extra_data or {}

    # Get all rows for this file
    status_conditions = []
    if status_filter == "reviewed":
        # Only confirmed/reviewed strings
        status_conditions = ["reviewed", "approved"]
    elif status_filter == "translated":
        # Translated and reviewed
        status_conditions = ["translated", "reviewed", "approved"]
    # else: all rows

    query = select(LDMRow).where(LDMRow.file_id == file_id).order_by(LDMRow.row_num)

    if status_conditions:
        query = query.where(LDMRow.status.in_(status_conditions))

    result = await db.execute(query)
    rows = result.scalars().all()

    if not rows:
        raise HTTPException(status_code=404, detail="No rows found for this file")

    # Build file content based on format (case-insensitive)
    # Pass file_metadata for full structure preservation
    format_lower = file.format.lower() if file.format else ""
    if format_lower == "txt":
        content = _build_txt_file(rows, file_metadata)
        media_type = "text/plain"
        extension = ".txt"
    elif format_lower == "xml":
        content = _build_xml_file(rows, file_metadata)
        media_type = "application/xml"
        extension = ".xml"
    elif format_lower in ["xlsx", "excel"]:
        content = _build_excel_file(rows, file_metadata)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        extension = ".xlsx"
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {file.format}")

    # Create filename
    base_name = file.original_filename.rsplit('.', 1)[0] if '.' in file.original_filename else file.original_filename
    download_name = f"{base_name}_export{extension}"

    logger.info(f"LDM: Downloading file {file_id} ({len(rows)} rows) as {download_name}")

    return StreamingResponse(
        BytesIO(content),
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={download_name}"}
    )


# =============================================================================
# File Merge (P3: MERGE System)
# =============================================================================

@router.post("/files/{file_id}/merge")
async def merge_file(
    file_id: int,
    original_file: UploadFile = File(..., description="Original file to merge into"),
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Merge reviewed translations from LDM back into original file.

    Flow:
    1. User uploads original file (from LanguageData)
    2. System gets reviewed rows from LDM database
    3. Matches by StringID + Source
    4. EDIT: Updates target for matches
    5. ADD: Appends new rows not in original
    6. Returns merged file for download

    Supported formats: TXT, XML (Excel not supported - no StringID)
    """
    from server.tools.ldm.file_handlers.txt_handler import parse_txt_file
    from server.tools.ldm.file_handlers.xml_handler import parse_xml_file

    # Get LDM file info
    result = await db.execute(
        select(LDMFile).options(selectinload(LDMFile.project)).where(
            LDMFile.id == file_id
        )
    )
    file = result.scalar_one_or_none()

    # P9: Fallback to SQLite for local files
    if not file:
        return await _merge_local_file(file_id, original_file)

    if not await can_access_project(db, file.project_id, current_user):
        raise HTTPException(status_code=404, detail="Resource not found")

    # Check format compatibility
    format_lower = file.format.lower() if file.format else ""
    if format_lower not in ["txt", "xml"]:
        raise HTTPException(
            status_code=400,
            detail=f"Merge not supported for format: {file.format}. Only TXT and XML supported."
        )

    # Read original file content
    original_content = await original_file.read()
    original_filename = original_file.filename or "merged_file"

    # Determine format from original file extension
    original_ext = original_filename.rsplit('.', 1)[-1].lower() if '.' in original_filename else ""

    # Validate format match
    if original_ext == "txt" and format_lower != "txt":
        raise HTTPException(status_code=400, detail="Format mismatch: LDM file is XML, original is TXT")
    if original_ext == "xml" and format_lower != "xml":
        raise HTTPException(status_code=400, detail="Format mismatch: LDM file is TXT, original is XML")

    # Parse original file
    if format_lower == "txt":
        original_rows = parse_txt_file(original_content, original_filename)
    else:  # xml
        original_rows = parse_xml_file(original_content, original_filename)

    if not original_rows:
        raise HTTPException(status_code=400, detail="Could not parse original file or file is empty")

    # Get reviewed rows from LDM database
    result = await db.execute(
        select(LDMRow).where(
            LDMRow.file_id == file_id,
            LDMRow.status.in_(["reviewed", "approved"])
        ).order_by(LDMRow.row_num)
    )
    db_rows = result.scalars().all()

    if not db_rows:
        raise HTTPException(status_code=400, detail="No reviewed rows to merge")

    # Build lookup from DB rows: (string_id, source) -> row
    db_lookup = {}
    for row in db_rows:
        key = (row.string_id or "", row.source or "")
        db_lookup[key] = row

    # Track merge statistics
    edited_count = 0
    added_count = 0
    original_keys = set()

    # Merge: Update original rows with reviewed translations
    merged_rows = []
    for orig in original_rows:
        key = (orig.get("string_id") or "", orig.get("source") or "")
        original_keys.add(key)

        if key in db_lookup:
            # EDIT: Replace target with reviewed translation
            db_row = db_lookup[key]
            orig["target"] = db_row.target
            orig["extra_data"] = db_row.extra_data or orig.get("extra_data")
            edited_count += 1

        merged_rows.append(orig)

    # ADD: Append new rows from DB that don't exist in original
    for key, db_row in db_lookup.items():
        if key not in original_keys:
            merged_rows.append({
                "row_num": len(merged_rows) + 1,
                "string_id": db_row.string_id,
                "source": db_row.source,
                "target": db_row.target,
                "extra_data": db_row.extra_data
            })
            added_count += 1

    # Build merged file content
    if format_lower == "txt":
        content = _build_txt_file_from_dicts(merged_rows, file.extra_data or {})
        media_type = "text/plain"
        extension = ".txt"
    else:  # xml
        content = _build_xml_file_from_dicts(merged_rows, file.extra_data or {})
        media_type = "application/xml"
        extension = ".xml"

    # Create filename
    base_name = original_filename.rsplit('.', 1)[0] if '.' in original_filename else original_filename
    download_name = f"{base_name}_merged{extension}"

    logger.info(f"LDM MERGE: file_id={file_id}, edited={edited_count}, added={added_count}, total={len(merged_rows)}")

    return StreamingResponse(
        BytesIO(content),
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename={download_name}",
            "X-Merge-Edited": str(edited_count),
            "X-Merge-Added": str(added_count),
            "X-Merge-Total": str(len(merged_rows))
        }
    )


# =============================================================================
# File Format Conversion (P4)
# =============================================================================

@router.get("/files/{file_id}/convert")
async def convert_file(
    file_id: int,
    format: str = Query(..., regex="^(xlsx|xml|txt|tmx)$", description="Target format"),
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Convert a file to a different format.
    P9: Falls back to SQLite for local files.

    Supported conversions:
    - TXT → Excel, XML, TMX
    - XML → Excel, TMX
    - Excel → XML, TMX

    NOT supported (StringID loss):
    - XML → TXT
    - Excel → TXT
    """
    # Get file info
    result = await db.execute(
        select(LDMFile).options(selectinload(LDMFile.project)).where(
            LDMFile.id == file_id
        )
    )
    file = result.scalar_one_or_none()

    if not file:
        # P9: Fallback to SQLite for local files
        return await _convert_local_file(file_id, format)

    if not await can_access_project(db, file.project_id, current_user):
        raise HTTPException(status_code=404, detail="Resource not found")

    source_format = file.format.lower() if file.format else ""
    target_format = format.lower()

    # Validate conversion is allowed
    if target_format == "txt" and source_format in ["xml", "xlsx", "excel"]:
        raise HTTPException(
            status_code=400,
            detail="Cannot convert to TXT: StringID information would be lost"
        )

    if source_format == target_format:
        raise HTTPException(
            status_code=400,
            detail=f"File is already in {target_format.upper()} format. Use Download instead."
        )

    # Get all rows for this file
    result = await db.execute(
        select(LDMRow).where(LDMRow.file_id == file_id).order_by(LDMRow.row_num)
    )
    rows = result.scalars().all()

    if not rows:
        raise HTTPException(status_code=404, detail="No rows found for this file")

    # Get file metadata
    file_metadata = file.extra_data or {}

    # Build file in target format
    if target_format == "xlsx":
        content = _build_excel_file(rows, file_metadata)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        extension = ".xlsx"
    elif target_format == "xml":
        content = _build_xml_file(rows, file_metadata)
        media_type = "application/xml"
        extension = ".xml"
    elif target_format == "txt":
        content = _build_txt_file(rows, file_metadata)
        media_type = "text/plain"
        extension = ".txt"
    elif target_format == "tmx":
        content = _build_tmx_file(rows, file_metadata, file)
        media_type = "application/x-tmx+xml"
        extension = ".tmx"
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {format}")

    # Create filename
    base_name = file.original_filename.rsplit('.', 1)[0] if '.' in file.original_filename else file.original_filename
    download_name = f"{base_name}_converted{extension}"

    logger.info(f"LDM CONVERT: file_id={file_id}, {source_format} → {target_format}, {len(rows)} rows")

    return StreamingResponse(
        BytesIO(content),
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename={download_name}",
            "X-Source-Format": source_format,
            "X-Target-Format": target_format,
            "X-Row-Count": str(len(rows))
        }
    )


@router.get("/files/{file_id}/extract-glossary")
async def extract_glossary(
    file_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Extract glossary terms from a file and download as Excel.

    Filtering rules:
    - Length ≤ 21 characters
    - Minimum 2 occurrences
    - No punctuation endings (.?!)

    Returns Excel with Source/Target columns.
    """
    from collections import Counter

    # Get file info
    result = await db.execute(
        select(LDMFile).options(selectinload(LDMFile.project)).where(
            LDMFile.id == file_id
        )
    )
    file = result.scalar_one_or_none()

    # P9: Fallback to SQLite for local files
    if not file:
        return await _extract_local_glossary(file_id)

    if not await can_access_project(db, file.project_id, current_user):
        raise HTTPException(status_code=404, detail="Resource not found")

    # Get all rows for this file
    result = await db.execute(
        select(LDMRow).where(
            LDMRow.file_id == file_id,
            LDMRow.source.isnot(None),
            LDMRow.source != ""
        )
    )
    rows = result.scalars().all()

    if not rows:
        raise HTTPException(status_code=404, detail="No rows found in file")

    # Count occurrences of each source term
    source_counts = Counter(row.source.strip() for row in rows if row.source)

    # Build source → target mapping (first occurrence wins)
    source_to_target = {}
    for row in rows:
        source = row.source.strip() if row.source else ""
        if source and source not in source_to_target:
            source_to_target[source] = row.target.strip() if row.target else ""

    # Filter glossary terms
    glossary = []
    for source, count in source_counts.items():
        # Rule 1: Length ≤ 21 characters
        if len(source) > 21:
            continue
        # Rule 2: Minimum 2 occurrences
        if count < 2:
            continue
        # Rule 3: No punctuation endings
        if source.endswith(('.', '?', '!')):
            continue

        target = source_to_target.get(source, "")
        glossary.append((source, target, count))

    if not glossary:
        raise HTTPException(status_code=404, detail="No glossary terms found (check filtering rules)")

    # Sort by frequency (most common first)
    glossary.sort(key=lambda x: -x[2])

    # Build Excel file
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Glossary"

    # Header row
    ws.cell(row=1, column=1, value="Source")
    ws.cell(row=1, column=2, value="Target")

    # Data rows
    for idx, (source, target, _count) in enumerate(glossary, start=2):
        ws.cell(row=idx, column=1, value=source)
        ws.cell(row=idx, column=2, value=target)

    # Save to bytes
    output = BytesIO()
    wb.save(output)
    output.seek(0)

    # Create filename
    base_name = file.original_filename.rsplit('.', 1)[0] if '.' in file.original_filename else file.original_filename
    download_name = f"{base_name}_glossary.xlsx"

    logger.info(f"LDM: Extracted glossary from file {file_id}: {len(glossary)} terms")

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={download_name}"}
    )


# =============================================================================
# File Builder Helpers
# =============================================================================

def _build_txt_file(rows: List[LDMRow], file_metadata: dict = None) -> bytes:
    """
    Rebuild TXT file from rows with FULL structure preservation.

    TXT format: tab-separated columns
    Original format: idx0\tidx1\tidx2\tidx3\tidx4\tsource\ttarget\t[extra columns...]

    Uses:
    - file_metadata.encoding: Original file encoding
    - file_metadata.total_columns: Total column count
    - row.extra_data: Extra columns beyond 0-6
    """
    file_metadata = file_metadata or {}
    lines = []

    for row in rows:
        # Reconstruct string_id parts - stored with spaces, output with tabs
        # Upload stores as "0 100 0 0 1" (space-joined), we need "0\t100\t0\t0\t1"
        string_id_parts = row.string_id.split(' ') if row.string_id else [""] * 5

        # Ensure we have 5 parts for the index
        while len(string_id_parts) < 5:
            string_id_parts.append("")

        # Build base columns: idx0\tidx1\tidx2\tidx3\tidx4\tsource\ttarget
        source = row.source or ""
        target = row.target or ""

        # Replace newlines back to actual newlines in the file
        source = source.replace("↵", "\n")
        target = target.replace("↵", "\n")

        # Start with standard 7 columns
        parts = string_id_parts[:5] + [source, target]

        # Add extra columns from extra_data (col7, col8, etc.)
        if row.extra_data:
            # Get the total columns from file metadata, or calculate from extra_data
            total_cols = file_metadata.get("total_columns", 7)
            for i in range(7, total_cols):
                col_key = f"col{i}"
                parts.append(row.extra_data.get(col_key, ""))

        line = "\t".join(parts)
        lines.append(line)

    content = "\n".join(lines)

    # Use original encoding if available
    encoding = file_metadata.get("encoding", "utf-8")
    return content.encode(encoding)


def _build_xml_file(rows: List[LDMRow], file_metadata: dict = None) -> bytes:
    """
    Rebuild XML file from rows.

    XML format:
    <?xml version="1.0" encoding="UTF-8"?>
    <LangData>
        <String StrOrigin="source" Str="target" StringId="ID"/>
    </LangData>

    Output format (order matters):
    - StrOrigin: Source text
    - Str: Target/translated text
    - StringId: Concatenated without spaces
    """
    import xml.etree.ElementTree as ET
    from xml.dom import minidom

    file_metadata = file_metadata or {}

    # Use original root element or default to LangData
    root_tag = file_metadata.get("root_element", "LangData")
    root = ET.Element(root_tag)

    # Use original element tag or default to String
    element_tag = file_metadata.get("element_tag", "String")

    for row in rows:
        string_elem = ET.SubElement(root, element_tag)

        # Set attributes in order: StrOrigin, Str, StringId (PascalCase)
        # StringId should be concatenated without spaces
        string_id = (row.string_id or "").replace(" ", "")

        # Use ordered dict approach - XML attributes are ordered in Python 3.7+
        string_elem.set("StrOrigin", row.source or "")
        string_elem.set("Str", row.target or "")
        string_elem.set("StringId", string_id)

    # Pretty print with original encoding
    encoding = file_metadata.get("encoding", "UTF-8")
    xml_str = ET.tostring(root, encoding='unicode')
    dom = minidom.parseString(xml_str)
    pretty_xml = dom.toprettyxml(indent="  ", encoding=encoding)

    return pretty_xml


def _build_excel_file(rows: List[LDMRow], file_metadata: dict = None) -> bytes:
    """
    Rebuild Excel file from rows with FULL structure preservation.

    Excel format: Source in column A, Target in column B, extra columns in C+

    Uses:
    - file_metadata.headers: Original column headers
    - file_metadata.sheet_name: Original sheet name
    - row.extra_data: Extra columns beyond A-B
    """
    import openpyxl

    file_metadata = file_metadata or {}

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = file_metadata.get("sheet_name", "Translations")

    # Get headers from metadata or use defaults
    headers = file_metadata.get("headers", ["Source", "Target"])
    if len(headers) < 2:
        headers = ["Source", "Target"]

    # Header row
    for col_idx, header in enumerate(headers, start=1):
        ws.cell(row=1, column=col_idx, value=header)

    # Data rows
    for row_idx, row in enumerate(rows, start=2):
        ws.cell(row=row_idx, column=1, value=row.source or "")
        ws.cell(row=row_idx, column=2, value=row.target or "")

        # Add extra columns from extra_data (C, D, E, etc.)
        if row.extra_data:
            for col_letter, val in row.extra_data.items():
                # Convert column letter to index (C=3, D=4, etc.)
                if col_letter.isalpha() and len(col_letter) == 1:
                    col_num = ord(col_letter.upper()) - ord('A') + 1
                    if col_num > 2:  # Skip A and B (source/target)
                        ws.cell(row=row_idx, column=col_num, value=val or "")

    # Save to bytes
    output = BytesIO()
    wb.save(output)
    output.seek(0)

    return output.read()


# =============================================================================
# Dict-based File Builders (for Merge)
# =============================================================================

def _build_txt_file_from_dicts(rows: List[dict], file_metadata: dict = None) -> bytes:
    """
    Build TXT file from dict rows (used by merge).

    Same as _build_txt_file but works with dicts instead of LDMRow objects.
    """
    file_metadata = file_metadata or {}
    lines = []

    for row in rows:
        # Reconstruct string_id parts
        string_id = row.get("string_id") or ""
        string_id_parts = string_id.split(' ') if string_id else [""] * 5

        # Ensure we have 5 parts
        while len(string_id_parts) < 5:
            string_id_parts.append("")

        source = row.get("source") or ""
        target = row.get("target") or ""

        # Replace newline markers
        source = source.replace("↵", "\n")
        target = target.replace("↵", "\n")

        # Start with standard 7 columns
        parts = string_id_parts[:5] + [source, target]

        # Add extra columns
        extra_data = row.get("extra_data")
        if extra_data:
            total_cols = file_metadata.get("total_columns", 7)
            for i in range(7, total_cols):
                col_key = f"col{i}"
                parts.append(extra_data.get(col_key, ""))

        line = "\t".join(parts)
        lines.append(line)

    content = "\n".join(lines)
    encoding = file_metadata.get("encoding", "utf-8")
    return content.encode(encoding)


def _build_xml_file_from_dicts(rows: List[dict], file_metadata: dict = None) -> bytes:
    """
    Build XML file from dict rows (used by merge).

    Same as _build_xml_file but works with dicts instead of LDMRow objects.
    """
    import xml.etree.ElementTree as ET
    from xml.dom import minidom

    file_metadata = file_metadata or {}

    root_tag = file_metadata.get("root_element", "LangData")
    root = ET.Element(root_tag)

    root_attribs = file_metadata.get("root_attributes")
    if root_attribs:
        for key, val in root_attribs.items():
            root.set(key, val)

    element_tag = file_metadata.get("element_tag", "String")

    for row in rows:
        string_elem = ET.SubElement(root, element_tag)

        string_elem.set("stringid", row.get("string_id") or "")
        string_elem.set("strorigin", row.get("source") or "")
        string_elem.set("str", row.get("target") or "")

        extra_data = row.get("extra_data")
        if extra_data:
            for attr_name, attr_val in extra_data.items():
                string_elem.set(attr_name, attr_val or "")

    encoding = file_metadata.get("encoding", "UTF-8")
    xml_str = ET.tostring(root, encoding='unicode')
    dom = minidom.parseString(xml_str)
    pretty_xml = dom.toprettyxml(indent="  ", encoding=encoding)

    return pretty_xml


# =============================================================================
# TMX Builder (P4: File Conversions)
# =============================================================================

def _build_tmx_file(rows: List[LDMRow], file_metadata: dict = None, file: LDMFile = None) -> bytes:
    """
    Build TMX (Translation Memory eXchange) file from rows.

    TMX format:
    <?xml version="1.0" encoding="UTF-8"?>
    <tmx version="1.4">
      <header ... />
      <body>
        <tu>
          <prop type="x-string-id">StringID</prop>
          <tuv xml:lang="ko"><seg>Source</seg></tuv>
          <tuv xml:lang="en"><seg>Target</seg></tuv>
        </tu>
      </body>
    </tmx>
    """
    import xml.etree.ElementTree as ET
    from datetime import datetime

    file_metadata = file_metadata or {}

    # Determine languages
    source_lang = file.source_language if file else "ko"
    target_lang = file.target_language if file else "en"

    # Create root element
    root = ET.Element("tmx", version="1.4")

    # Header
    header = ET.SubElement(root, "header")
    header.set("creationtool", "LocaNext")
    header.set("creationtoolversion", "1.0")
    header.set("datatype", "plaintext")
    header.set("segtype", "sentence")
    header.set("adminlang", "en")
    header.set("srclang", source_lang or "ko")
    header.set("creationdate", datetime.utcnow().strftime("%Y%m%dT%H%M%SZ"))

    # Body
    body = ET.SubElement(root, "body")

    for row in rows:
        tu = ET.SubElement(body, "tu")

        # Add StringID as property if available
        string_id = row.string_id if hasattr(row, 'string_id') else row.get("string_id")
        if string_id:
            prop = ET.SubElement(tu, "prop", type="x-string-id")
            prop.text = string_id

        # Source segment
        tuv_src = ET.SubElement(tu, "tuv")
        tuv_src.set("{http://www.w3.org/XML/1998/namespace}lang", source_lang or "ko")
        seg_src = ET.SubElement(tuv_src, "seg")
        source = row.source if hasattr(row, 'source') else row.get("source")
        seg_src.text = source or ""

        # Target segment
        tuv_tgt = ET.SubElement(tu, "tuv")
        tuv_tgt.set("{http://www.w3.org/XML/1998/namespace}lang", target_lang or "en")
        seg_tgt = ET.SubElement(tuv_tgt, "seg")
        target = row.target if hasattr(row, 'target') else row.get("target")
        seg_tgt.text = target or ""

    # Convert to bytes with XML declaration
    tree = ET.ElementTree(root)
    output = BytesIO()
    tree.write(output, encoding="utf-8", xml_declaration=True)
    content = output.getvalue()
    output.close()

    return content


# =============================================================================
# P9: Local Storage Upload (Offline Storage)
# =============================================================================

async def _upload_to_local_storage(
    file: UploadFile,
    source_col: Optional[int] = None,
    target_col: Optional[int] = None,
    stringid_col: Optional[int] = None,
    has_header: Optional[bool] = True
) -> dict:
    """
    P9: Upload a file to SQLite Offline Storage with proper parsing.

    This uses the SAME file parsers as PostgreSQL upload, ensuring
    consistent parsing for both online and offline modes.

    Returns a FileResponse-compatible dict.
    """
    from server.database.offline import get_offline_db
    from datetime import datetime

    filename = file.filename or "unknown"
    ext = filename.lower().split('.')[-1] if '.' in filename else ''

    # Parse file using existing handlers (same as PostgreSQL upload)
    file_metadata = None
    if ext in ('txt', 'tsv'):
        from server.tools.ldm.file_handlers.txt_handler import parse_txt_file, get_file_format, get_source_language, get_file_metadata
        file_content = await file.read()
        rows_data = parse_txt_file(file_content, filename)
        file_format = get_file_format()
        source_lang = get_source_language()
        file_metadata = get_file_metadata()
    elif ext == 'xml':
        from server.tools.ldm.file_handlers.xml_handler import parse_xml_file, get_file_format, get_source_language, get_file_metadata
        file_content = await file.read()
        rows_data = parse_xml_file(file_content, filename)
        file_format = get_file_format()
        source_lang = get_source_language()
        file_metadata = get_file_metadata()
    elif ext in ('xlsx', 'xls'):
        from server.tools.ldm.file_handlers.excel_handler import parse_excel_file, get_file_format, get_source_language, get_file_metadata
        file_content = await file.read()
        rows_data = parse_excel_file(
            file_content,
            filename,
            source_col=source_col if source_col is not None else 0,
            target_col=target_col if target_col is not None else 1,
            stringid_col=stringid_col,
            has_header=has_header if has_header is not None else True
        )
        file_format = get_file_format()
        source_lang = get_source_language()
        file_metadata = get_file_metadata()
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format: {ext}. Use TXT, TSV, XML, or Excel (XLSX/XLS)."
        )

    if not rows_data:
        raise HTTPException(
            status_code=400,
            detail="No valid rows found in file"
        )

    try:
        offline_db = get_offline_db()

        # Create local file in Offline Storage (may auto-rename if duplicate)
        result = offline_db.create_local_file(
            name=filename,
            original_filename=filename,
            file_format=file_format,
            source_language=source_lang,
            target_language=None
        )
        file_id = result["id"]
        final_name = result["name"]  # May be different from filename if renamed

        # Add parsed rows to the local file
        offline_db.add_rows_to_local_file(file_id, rows_data)

        logger.success(f"P9: File uploaded to Offline Storage: id={file_id}, name='{final_name}', rows={len(rows_data)}")

        # Return FileResponse-compatible dict
        now = datetime.utcnow()
        return {
            "id": file_id,
            "project_id": None,  # Local files have no project
            "folder_id": None,
            "name": final_name,  # P9-FIX: Use actual name (may be auto-renamed)
            "original_filename": filename,
            "format": file_format,
            "row_count": len(rows_data),
            "source_language": source_lang,
            "target_language": None,
            "created_at": now,
            "updated_at": now
        }

    except Exception as e:
        logger.error(f"P9: Failed to upload to Offline Storage: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")


async def _download_local_file(file_id: int, status_filter: Optional[str] = None):
    """
    P9: Download a local file from SQLite Offline Storage.

    Same logic as download_file but reads from SQLite instead of PostgreSQL.
    """
    from server.database.offline import get_offline_db

    offline_db = get_offline_db()

    # Get file info from SQLite
    file_info = offline_db.get_local_file(file_id)
    if not file_info:
        raise HTTPException(status_code=404, detail="File not found")

    # Get rows from SQLite
    rows_data = offline_db.get_rows_for_file(file_id)
    if not rows_data:
        raise HTTPException(status_code=404, detail="No rows found for this file")

    # Filter by status if requested
    if status_filter:
        if status_filter == "reviewed":
            status_conditions = ["reviewed", "approved"]
        elif status_filter == "translated":
            status_conditions = ["translated", "reviewed", "approved"]
        else:
            status_conditions = None

        if status_conditions:
            rows_data = [r for r in rows_data if r.get("status") in status_conditions]

    if not rows_data:
        raise HTTPException(status_code=404, detail="No rows match the status filter")

    # Convert to row-like objects for the builder functions
    class RowLike:
        def __init__(self, data):
            self.row_num = data.get("row_num", 0)
            self.string_id = data.get("string_id", "")
            self.source = data.get("source", "")
            self.target = data.get("target", "")
            self.extra_data = data.get("extra_data")

    rows = [RowLike(r) for r in rows_data]

    # Build file content based on format
    file_format = (file_info.get("format") or "txt").lower()
    file_metadata = file_info.get("extra_data") or {}

    if file_format == "txt":
        content = _build_txt_file(rows, file_metadata)
        media_type = "text/plain"
        extension = ".txt"
    elif file_format == "xml":
        content = _build_xml_file(rows, file_metadata)
        media_type = "application/xml"
        extension = ".xml"
    elif file_format in ["xlsx", "excel"]:
        content = _build_excel_file(rows, file_metadata)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        extension = ".xlsx"
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {file_format}")

    # Create filename
    original_filename = file_info.get("original_filename") or file_info.get("name") or "file"
    base_name = original_filename.rsplit('.', 1)[0] if '.' in original_filename else original_filename
    download_name = f"{base_name}_export{extension}"

    logger.info(f"P9: Downloading local file {file_id} ({len(rows)} rows) as {download_name}")

    return StreamingResponse(
        BytesIO(content),
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={download_name}"}
    )


async def _get_local_file_metadata(file_id: int) -> dict:
    """
    P9: Get file metadata from SQLite Offline Storage.
    Returns FileResponse-compatible dict.
    """
    from server.database.offline import get_offline_db
    from datetime import datetime

    offline_db = get_offline_db()
    file_info = offline_db.get_local_file(file_id)

    if not file_info:
        raise HTTPException(status_code=404, detail="File not found")

    # Return FileResponse-compatible dict
    return {
        "id": file_info.get("id"),
        "project_id": None,
        "folder_id": None,
        "name": file_info.get("name"),
        "original_filename": file_info.get("original_filename"),
        "format": file_info.get("format"),
        "row_count": file_info.get("row_count", 0),
        "source_language": file_info.get("source_language"),
        "target_language": file_info.get("target_language"),
        "created_at": file_info.get("created_at") or datetime.utcnow(),
        "updated_at": file_info.get("updated_at") or datetime.utcnow()
    }


async def _delete_local_file(file_id: int) -> dict:
    """
    P9: Delete a file from SQLite Offline Storage.
    """
    from server.database.offline import get_offline_db

    offline_db = get_offline_db()
    file_info = offline_db.get_local_file(file_id)

    if not file_info:
        raise HTTPException(status_code=404, detail="File not found")

    file_name = file_info.get("name")

    # Delete from SQLite (offline.py method deletes rows + file)
    success = offline_db.delete_local_file(file_id)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete file")

    logger.info(f"P9: Local file deleted: id={file_id}, name='{file_name}'")
    return {"message": "File deleted", "file_id": file_id}


async def _convert_local_file(file_id: int, target_format: str):
    """
    P9: Convert a local file from SQLite Offline Storage.
    Same logic as convert_file but reads from SQLite.
    """
    from server.database.offline import get_offline_db

    offline_db = get_offline_db()
    file_info = offline_db.get_local_file(file_id)

    if not file_info:
        raise HTTPException(status_code=404, detail="File not found")

    source_format = (file_info.get("format") or "txt").lower()
    target_format = target_format.lower()

    # Validate conversion
    if target_format == "txt" and source_format in ["xml", "xlsx", "excel"]:
        raise HTTPException(
            status_code=400,
            detail="Cannot convert to TXT: StringID information would be lost"
        )

    if source_format == target_format:
        raise HTTPException(
            status_code=400,
            detail=f"File is already in {target_format.upper()} format. Use Download instead."
        )

    # Get rows from SQLite
    rows_data = offline_db.get_rows_for_file(file_id)
    if not rows_data:
        raise HTTPException(status_code=404, detail="No rows found for this file")

    # Convert to row-like objects for the builder functions
    class RowLike:
        def __init__(self, data):
            self.row_num = data.get("row_num", 0)
            self.string_id = data.get("string_id", "")
            self.source = data.get("source", "")
            self.target = data.get("target", "")
            # P9: extra_data from SQLite is JSON string, need to parse it
            extra = data.get("extra_data")
            if extra and isinstance(extra, str):
                import json
                try:
                    self.extra_data = json.loads(extra)
                except (json.JSONDecodeError, TypeError):
                    self.extra_data = None
            else:
                self.extra_data = extra

    rows = [RowLike(r) for r in rows_data]
    # P9: file metadata from SQLite is also JSON string
    raw_metadata = file_info.get("extra_data")
    if raw_metadata and isinstance(raw_metadata, str):
        import json
        try:
            file_metadata = json.loads(raw_metadata)
        except (json.JSONDecodeError, TypeError):
            file_metadata = {}
    else:
        file_metadata = raw_metadata or {}

    # Build file in target format
    if target_format == "xlsx":
        content = _build_excel_file(rows, file_metadata)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        extension = ".xlsx"
    elif target_format == "xml":
        content = _build_xml_file(rows, file_metadata)
        media_type = "application/xml"
        extension = ".xml"
    elif target_format == "txt":
        content = _build_txt_file(rows, file_metadata)
        media_type = "text/plain"
        extension = ".txt"
    elif target_format == "tmx":
        # Create a file-like object for TMX builder
        class FileLike:
            source_language = file_info.get("source_language")
            target_language = file_info.get("target_language")
        content = _build_tmx_file(rows, file_metadata, FileLike())
        media_type = "application/x-tmx+xml"
        extension = ".tmx"
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {target_format}")

    # Create filename
    original_filename = file_info.get("original_filename") or file_info.get("name") or "file"
    base_name = original_filename.rsplit('.', 1)[0] if '.' in original_filename else original_filename
    download_name = f"{base_name}_converted{extension}"

    logger.info(f"P9: Converting local file {file_id}: {source_format} → {target_format}, {len(rows)} rows")

    return StreamingResponse(
        BytesIO(content),
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename={download_name}",
            "X-Source-Format": source_format,
            "X-Target-Format": target_format,
            "X-Row-Count": str(len(rows))
        }
    )


async def _rename_local_file(file_id: int, new_name: str) -> dict:
    """
    P9: Rename a file in SQLite Offline Storage.
    """
    from server.database.offline import get_offline_db

    offline_db = get_offline_db()
    file_info = offline_db.get_local_file(file_id)

    if not file_info:
        raise HTTPException(status_code=404, detail="File not found")

    old_name = file_info.get("name")

    # Use existing rename method
    success = offline_db.rename_local_file(file_id, new_name)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to rename file")

    logger.success(f"P9: Local file renamed: id={file_id}, '{old_name}' -> '{new_name}'")
    return {"success": True, "file_id": file_id, "name": new_name}


async def _extract_local_glossary(file_id: int):
    """
    P9: Extract glossary from a local file in SQLite.
    Same logic as extract_glossary but with SQLite data.
    """
    from collections import Counter
    from server.database.offline import get_offline_db
    import openpyxl

    offline_db = get_offline_db()
    file_info = offline_db.get_local_file(file_id)

    if not file_info:
        raise HTTPException(status_code=404, detail="File not found")

    rows_data = offline_db.get_rows_for_file(file_id)

    if not rows_data:
        raise HTTPException(status_code=404, detail="No rows found in file")

    # Filter rows with source
    rows_with_source = [r for r in rows_data if r.get("source")]

    # Count occurrences
    source_counts = Counter(r.get("source", "").strip() for r in rows_with_source)

    # Build source → target mapping
    source_to_target = {}
    for row in rows_with_source:
        source = row.get("source", "").strip()
        if source and source not in source_to_target:
            source_to_target[source] = row.get("target", "").strip() if row.get("target") else ""

    # Filter glossary terms (same rules as PostgreSQL version)
    glossary = []
    for source, count in source_counts.items():
        if len(source) > 21:
            continue
        if count < 2:
            continue
        if source.endswith(('.', '?', '!')):
            continue
        target = source_to_target.get(source, "")
        glossary.append((source, target, count))

    if not glossary:
        raise HTTPException(status_code=404, detail="No glossary terms found")

    glossary.sort(key=lambda x: -x[2])

    # Build Excel
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Glossary"
    ws.cell(row=1, column=1, value="Source")
    ws.cell(row=1, column=2, value="Target")

    for idx, (source, target, _) in enumerate(glossary, start=2):
        ws.cell(row=idx, column=1, value=source)
        ws.cell(row=idx, column=2, value=target)

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    original_filename = file_info.get("original_filename") or file_info.get("name") or "file"
    base_name = original_filename.rsplit('.', 1)[0] if '.' in original_filename else original_filename
    download_name = f"{base_name}_glossary.xlsx"

    logger.info(f"P9: Extracted glossary from local file {file_id}: {len(glossary)} terms")

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={download_name}"}
    )


async def _merge_local_file(file_id: int, original_file: UploadFile):
    """
    P9: Merge reviewed rows from a local SQLite file into an uploaded original.
    Same logic as merge_file but reads from SQLite.
    """
    from server.database.offline import get_offline_db
    from server.tools.ldm.file_handlers.txt_handler import parse_txt_file
    from server.tools.ldm.file_handlers.xml_handler import parse_xml_file

    offline_db = get_offline_db()
    file_info = offline_db.get_local_file(file_id)

    if not file_info:
        raise HTTPException(status_code=404, detail="File not found")

    format_lower = (file_info.get("format") or "txt").lower()
    if format_lower not in ["txt", "xml"]:
        raise HTTPException(status_code=400, detail=f"Merge not supported for format: {format_lower}")

    # Read original file
    original_content = await original_file.read()
    original_filename = original_file.filename or "merged_file"
    original_ext = original_filename.rsplit('.', 1)[-1].lower() if '.' in original_filename else ""

    # Parse original
    if format_lower == "txt":
        original_rows = parse_txt_file(original_content, original_filename)
    else:
        original_rows = parse_xml_file(original_content, original_filename)

    if not original_rows:
        raise HTTPException(status_code=400, detail="Could not parse original file")

    # Get reviewed rows from SQLite
    rows_data = offline_db.get_rows_for_file(file_id)
    db_rows = [r for r in rows_data if r.get("status") in ["reviewed", "approved"]]

    if not db_rows:
        raise HTTPException(status_code=400, detail="No reviewed rows to merge")

    # Build lookup
    db_lookup = {}
    for row in db_rows:
        key = (row.get("string_id") or "", row.get("source") or "")
        db_lookup[key] = row

    # Merge
    edited_count = 0
    added_count = 0
    original_keys = set()
    merged_rows = []

    for orig in original_rows:
        key = (orig.get("string_id") or "", orig.get("source") or "")
        original_keys.add(key)
        if key in db_lookup:
            db_row = db_lookup[key]
            orig["target"] = db_row.get("target")
            edited_count += 1
        merged_rows.append(orig)

    for key, db_row in db_lookup.items():
        if key not in original_keys:
            merged_rows.append({
                "row_num": len(merged_rows) + 1,
                "string_id": db_row.get("string_id"),
                "source": db_row.get("source"),
                "target": db_row.get("target"),
                "extra_data": db_row.get("extra_data")
            })
            added_count += 1

    # Build merged content
    if format_lower == "txt":
        content = _build_txt_file_from_dicts(merged_rows, file_info.get("extra_data") or {})
        media_type = "text/plain"
        extension = ".txt"
    else:
        content = _build_xml_file_from_dicts(merged_rows, file_info.get("extra_data") or {})
        media_type = "application/xml"
        extension = ".xml"

    base_name = original_filename.rsplit('.', 1)[0] if '.' in original_filename else original_filename
    download_name = f"{base_name}_merged{extension}"

    logger.info(f"P9: Merged local file {file_id}: edited={edited_count}, added={added_count}")

    return StreamingResponse(
        BytesIO(content),
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename={download_name}",
            "X-Merge-Edited": str(edited_count),
            "X-Merge-Added": str(added_count),
            "X-Merge-Total": str(len(merged_rows))
        }
    )


async def _register_local_file_as_tm(file_id: int, request, current_user: dict):
    """
    P9: Convert a local SQLite file into a TM in PostgreSQL.
    Gets rows from SQLite, creates TM in PostgreSQL.
    """
    import time
    from server.database.offline import get_offline_db

    offline_db = get_offline_db()
    file_info = offline_db.get_local_file(file_id)

    if not file_info:
        raise HTTPException(status_code=404, detail="File not found")

    rows_data = offline_db.get_rows_for_file(file_id)

    # Filter valid rows
    valid_rows = [r for r in rows_data if r.get("source") and r.get("target")]

    if not valid_rows:
        raise HTTPException(status_code=400, detail="File has no translatable rows")

    entries_data = [{"source": r.get("source"), "target": r.get("target")} for r in valid_rows]

    # Create TM using sync session
    def _create_tm():
        sync_db = next(get_db())
        try:
            from server.tools.ldm.tm_manager import TMManager
            tm_manager = TMManager(sync_db)

            tm = tm_manager.create_tm(
                name=request.name,
                owner_id=current_user["user_id"],
                source_lang="ko",
                target_lang=request.language,
                description=request.description or f"Created from local file: {file_info.get('name')}"
            )

            start_time = time.time()
            entry_count = tm_manager.add_entries_bulk(tm.id, entries_data)
            elapsed = time.time() - start_time

            return {
                "tm_id": tm.id,
                "name": tm.name,
                "entry_count": entry_count,
                "status": tm.status,
                "time_seconds": round(elapsed, 2),
                "rate_per_second": int(entry_count / elapsed) if elapsed > 0 else 0,
                "source_file": file_info.get("name")
            }
        finally:
            sync_db.close()

    result = await asyncio.to_thread(_create_tm)

    logger.info(f"P9: TM created from local file: tm_id={result['tm_id']}, entries={result['entry_count']}")
    return result
