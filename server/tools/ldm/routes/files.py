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
        raise HTTPException(status_code=403, detail="Access denied")

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
    """Get file metadata by ID."""
    result = await db.execute(
        select(LDMFile).where(LDMFile.id == file_id)
    )
    file = result.scalar_one_or_none()

    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    if not await can_access_file(db, file_id, current_user):
        raise HTTPException(status_code=403, detail="Access denied")

    return file


@router.post("/files/upload", response_model=FileResponse)
async def upload_file(
    project_id: int = Form(...),
    folder_id: Optional[int] = Form(None),
    file: UploadFile = File(...),
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
    # Verify project exists
    result = await db.execute(
        select(LDMProject).where(LDMProject.id == project_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")

    # Check access permission
    if not await can_access_project(db, project_id, current_user):
        raise HTTPException(status_code=403, detail="Access denied")

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

    # DESIGN-001: Check for globally unique file name (no duplicates anywhere)
    filename = file.filename or "unknown"
    duplicate_query = select(LDMFile).where(LDMFile.name == filename)
    result = await db.execute(duplicate_query)
    existing_file = result.scalar_one_or_none()
    if existing_file:
        raise HTTPException(
            status_code=409,  # 409 Conflict - proper status for duplicate resource
            detail=f"A file named '{filename}' already exists. Please use a different name."
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


@router.patch("/files/{file_id}/rename")
async def rename_file(
    file_id: int,
    name: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """Rename a file."""
    # Get file
    result = await db.execute(
        select(LDMFile).where(LDMFile.id == file_id)
    )
    file = result.scalar_one_or_none()

    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    # Check access permission
    if not await can_access_project(db, file.project_id, current_user):
        raise HTTPException(status_code=403, detail="Not authorized to modify this file")

    # Check for duplicate name in same folder
    # DESIGN-001: Check for globally unique file name (no duplicates anywhere)
    duplicate_query = select(LDMFile).where(
        LDMFile.name == name,
        LDMFile.id != file_id
    )
    result = await db.execute(duplicate_query)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"A file named '{name}' already exists. Please use a different name.")

    old_name = file.name
    file.name = name
    await db.commit()

    logger.success(f"File renamed: id={file_id}, '{old_name}' -> '{name}'")
    return {"success": True, "file_id": file_id, "name": name}


@router.delete("/files/{file_id}")
async def delete_file(
    file_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """Delete a file and all its rows."""
    # Get file
    result = await db.execute(
        select(LDMFile).where(LDMFile.id == file_id)
    )
    file = result.scalar_one_or_none()

    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    # Check access permission
    if not await can_access_project(db, file.project_id, current_user):
        raise HTTPException(status_code=403, detail="Not authorized to delete this file")

    file_name = file.name
    await db.delete(file)
    await db.commit()

    logger.info(f"File deleted: id={file_id}, name='{file_name}'")
    return {"message": "File deleted", "file_id": file_id}


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

    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    # Check access permission
    if not await can_access_file(db, file_id, current_user):
        raise HTTPException(status_code=403, detail="Access denied")

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

    Query params:
    - status_filter: "reviewed" (confirmed only), "translated" (translated+reviewed), "all" (everything)
    """
    # Get file info
    result = await db.execute(
        select(LDMFile).where(LDMFile.id == file_id)
    )
    file = result.scalar_one_or_none()

    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    # Check access permission
    if not await can_access_file(db, file_id, current_user):
        raise HTTPException(status_code=403, detail="Access denied")

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

    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    if not await can_access_project(db, file.project_id, current_user):
        raise HTTPException(status_code=403, detail="Access denied")

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
        raise HTTPException(status_code=404, detail="File not found")

    if not await can_access_project(db, file.project_id, current_user):
        raise HTTPException(status_code=403, detail="Access denied")

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

    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    if not await can_access_project(db, file.project_id, current_user):
        raise HTTPException(status_code=403, detail="Access denied")

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
