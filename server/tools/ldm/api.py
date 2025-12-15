"""
LDM (LanguageData Manager) API Endpoints

REST API for managing localization projects, folders, files, and rows.
Supports real-time collaboration via WebSocket (see websocket.py).
"""

import asyncio
import hashlib
from functools import partial
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from sqlalchemy.orm import selectinload
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel
from loguru import logger
from io import BytesIO

from server.utils.dependencies import get_async_db, get_current_active_user_async, get_db
from server.database.db_utils import normalize_text_for_hash
from server.database.models import (
    User, LDMProject, LDMFolder, LDMFile, LDMRow, LDMEditHistory, LDMActiveSession,
    LDMTranslationMemory, LDMTMEntry
)


# ============================================================================
# Pydantic Schemas
# ============================================================================

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None

class ProjectResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    owner_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class FolderCreate(BaseModel):
    project_id: int
    parent_id: Optional[int] = None
    name: str

class FolderResponse(BaseModel):
    id: int
    project_id: int
    parent_id: Optional[int]
    name: str
    created_at: datetime

    class Config:
        from_attributes = True

class FileResponse(BaseModel):
    id: int
    project_id: int
    folder_id: Optional[int]
    name: str
    original_filename: str
    format: str
    row_count: int
    source_language: str
    target_language: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class RowResponse(BaseModel):
    id: int
    file_id: int
    row_num: int
    string_id: Optional[str]
    source: Optional[str]
    target: Optional[str]
    status: str
    updated_at: datetime

    class Config:
        from_attributes = True

class RowUpdate(BaseModel):
    target: Optional[str] = None
    status: Optional[str] = None

class PaginatedRows(BaseModel):
    rows: List[RowResponse]
    total: int
    page: int
    limit: int
    total_pages: int


class TMResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    source_lang: str
    target_lang: str
    entry_count: int
    status: str
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


class TMUploadResponse(BaseModel):
    tm_id: int
    name: str
    entry_count: int
    status: str
    time_seconds: float
    rate_per_second: int


class TMSearchResult(BaseModel):
    source_text: str
    target_text: str
    similarity: float
    tier: int
    strategy: str


# ============================================================================
# Router
# ============================================================================

router = APIRouter(prefix="/api/ldm", tags=["LDM"])


# ============================================================================
# Health Check
# ============================================================================

@router.get("/health")
async def health():
    """Health check endpoint for LDM module."""
    logger.info("LDM health check requested")
    return {
        "status": "ok",
        "module": "LDM (LanguageData Manager)",
        "version": "1.0.0",
        "features": {
            "projects": True,
            "folders": True,
            "files": True,
            "rows": True,
            "websocket": True,  # Phase 3: Real-time sync enabled
            "row_locking": True,
            "presence": True
        }
    }


# ============================================================================
# Projects
# ============================================================================

@router.get("/projects", response_model=List[ProjectResponse])
async def list_projects(
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """List all projects for current user."""
    user_id = current_user["user_id"]
    logger.info(f"Listing projects for user {user_id}")

    result = await db.execute(
        select(LDMProject).where(LDMProject.owner_id == current_user["user_id"])
    )
    projects = result.scalars().all()

    return projects


@router.post("/projects", response_model=ProjectResponse)
async def create_project(
    project: ProjectCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """Create a new project."""
    user_id = current_user["user_id"]
    logger.info(f"Creating project '{project.name}' for user {user_id}")

    new_project = LDMProject(
        name=project.name,
        description=project.description,
        owner_id=current_user["user_id"]
    )

    db.add(new_project)
    await db.commit()
    await db.refresh(new_project)

    logger.success(f"Project created: id={new_project.id}, name='{new_project.name}'")
    return new_project


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """Get a project by ID."""
    result = await db.execute(
        select(LDMProject).where(
            LDMProject.id == project_id,
            LDMProject.owner_id == current_user["user_id"]
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return project


@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """Delete a project and all its contents."""
    result = await db.execute(
        select(LDMProject).where(
            LDMProject.id == project_id,
            LDMProject.owner_id == current_user["user_id"]
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    await db.delete(project)
    await db.commit()

    logger.info(f"Project deleted: id={project_id}")
    return {"message": "Project deleted"}


# ============================================================================
# Folders
# ============================================================================

@router.get("/projects/{project_id}/folders", response_model=List[FolderResponse])
async def list_folders(
    project_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """List all folders in a project."""
    # Verify project ownership
    result = await db.execute(
        select(LDMProject).where(
            LDMProject.id == project_id,
            LDMProject.owner_id == current_user["user_id"]
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")

    result = await db.execute(
        select(LDMFolder).where(LDMFolder.project_id == project_id)
    )
    folders = result.scalars().all()

    return folders


@router.post("/folders", response_model=FolderResponse)
async def create_folder(
    folder: FolderCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """Create a new folder in a project."""
    # Verify project ownership
    result = await db.execute(
        select(LDMProject).where(
            LDMProject.id == folder.project_id,
            LDMProject.owner_id == current_user["user_id"]
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")

    new_folder = LDMFolder(
        project_id=folder.project_id,
        parent_id=folder.parent_id,
        name=folder.name
    )

    db.add(new_folder)
    await db.commit()
    await db.refresh(new_folder)

    logger.info(f"Folder created: id={new_folder.id}, name='{new_folder.name}'")
    return new_folder


@router.delete("/folders/{folder_id}")
async def delete_folder(
    folder_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """Delete a folder and all its contents."""
    result = await db.execute(
        select(LDMFolder).options(selectinload(LDMFolder.project)).where(
            LDMFolder.id == folder_id
        )
    )
    folder = result.scalar_one_or_none()

    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    if folder.project.owner_id != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    await db.delete(folder)
    await db.commit()

    logger.info(f"Folder deleted: id={folder_id}")
    return {"message": "Folder deleted"}


# ============================================================================
# Files
# ============================================================================

@router.get("/projects/{project_id}/files", response_model=List[FileResponse])
async def list_files(
    project_id: int,
    folder_id: Optional[int] = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """List files in a project, optionally filtered by folder."""
    # Verify project ownership
    result = await db.execute(
        select(LDMProject).where(
            LDMProject.id == project_id,
            LDMProject.owner_id == current_user["user_id"]
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")

    query = select(LDMFile).where(LDMFile.project_id == project_id)
    if folder_id is not None:
        query = query.where(LDMFile.folder_id == folder_id)

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
        select(LDMFile).options(selectinload(LDMFile.project)).where(
            LDMFile.id == file_id
        )
    )
    file = result.scalar_one_or_none()

    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    if file.project.owner_id != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    return file


@router.post("/files/upload", response_model=FileResponse)
async def upload_file(
    project_id: int = Form(...),
    folder_id: Optional[int] = Form(None),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Upload a localization file (TXT/XML), parse it, and store rows in database.

    Supported formats:
    - TXT/TSV: Tab-delimited, columns 0-4=StringID, 5=Source(KR), 6=Target, 7+=extra
    - XML: LocStr elements with StringId, StrOrigin(source), Str(target), other attrs=extra

    Full Structure Preservation:
    - File-level metadata stored in LDMFile.extra_data (encoding, root element, etc.)
    - Row-level extra data stored in LDMRow.extra_data (extra columns/attributes)
    - Enables FULL reconstruction of original file format
    """
    # Verify project ownership
    result = await db.execute(
        select(LDMProject).where(
            LDMProject.id == project_id,
            LDMProject.owner_id == current_user["user_id"]
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")

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

    # Determine file type and parse
    filename = file.filename or "unknown"
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
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format: {ext}. Use TXT, TSV, or XML."
        )

    if not rows_data:
        raise HTTPException(
            status_code=400,
            detail="No valid rows found in file"
        )

    # Create file record (with file-level metadata for reconstruction)
    new_file = LDMFile(
        project_id=project_id,
        folder_id=folder_id,
        name=filename,
        original_filename=filename,
        format=file_format,
        row_count=len(rows_data),
        source_language=source_lang,
        target_language=None,  # Set later based on project settings
        extra_data=file_metadata  # File-level metadata for full reconstruction
    )
    db.add(new_file)
    await db.flush()  # Get the file ID

    # Create row records (with row-level extra data for reconstruction)
    for row_data in rows_data:
        row = LDMRow(
            file_id=new_file.id,
            row_num=row_data["row_num"],
            string_id=row_data["string_id"],
            source=row_data["source"],
            target=row_data["target"],
            status=row_data["status"],
            extra_data=row_data.get("extra_data")  # Extra columns/attributes
        )
        db.add(row)

    await db.commit()
    await db.refresh(new_file)

    logger.success(f"File uploaded: id={new_file.id}, name='{filename}', rows={len(rows_data)}, has_metadata={file_metadata is not None}")
    return new_file


# ============================================================================
# Rows (Pagination)
# ============================================================================

@router.get("/files/{file_id}/rows", response_model=PaginatedRows)
async def list_rows(
    file_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    search: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """Get paginated rows for a file."""
    # Verify file access
    result = await db.execute(
        select(LDMFile).options(selectinload(LDMFile.project)).where(
            LDMFile.id == file_id
        )
    )
    file = result.scalar_one_or_none()

    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    if file.project.owner_id != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    # Build query
    query = select(LDMRow).where(LDMRow.file_id == file_id)
    count_query = select(func.count(LDMRow.id)).where(LDMRow.file_id == file_id)

    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            (LDMRow.source.ilike(search_pattern)) |
            (LDMRow.target.ilike(search_pattern)) |
            (LDMRow.string_id.ilike(search_pattern))
        )
        count_query = count_query.where(
            (LDMRow.source.ilike(search_pattern)) |
            (LDMRow.target.ilike(search_pattern)) |
            (LDMRow.string_id.ilike(search_pattern))
        )

    if status:
        query = query.where(LDMRow.status == status)
        count_query = count_query.where(LDMRow.status == status)

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Get paginated rows
    offset = (page - 1) * limit
    query = query.order_by(LDMRow.row_num).offset(offset).limit(limit)

    result = await db.execute(query)
    rows = result.scalars().all()

    total_pages = (total + limit - 1) // limit

    return PaginatedRows(
        rows=rows,
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages
    )


@router.put("/rows/{row_id}", response_model=RowResponse)
async def update_row(
    row_id: int,
    update: RowUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """Update a row's target text or status (source is READ-ONLY)."""
    # Get row with file and project
    result = await db.execute(
        select(LDMRow).options(
            selectinload(LDMRow.file).selectinload(LDMFile.project)
        ).where(LDMRow.id == row_id)
    )
    row = result.scalar_one_or_none()

    if not row:
        raise HTTPException(status_code=404, detail="Row not found")

    if row.file.project.owner_id != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    # Save history before update
    old_target = row.target
    old_status = row.status

    # Update row
    if update.target is not None:
        row.target = update.target
        # Auto-set status to translated if target is set and was pending
        if row.status == "pending" and update.target:
            row.status = "translated"

    if update.status is not None:
        row.status = update.status

    row.updated_by = current_user["user_id"]
    row.updated_at = datetime.utcnow()

    # Create edit history
    history = LDMEditHistory(
        row_id=row_id,
        user_id=current_user["user_id"],
        old_target=old_target,
        new_target=row.target,
        old_status=old_status,
        new_status=row.status
    )
    db.add(history)

    await db.commit()
    await db.refresh(row)

    # Broadcast cell update to all viewers (real-time sync)
    try:
        from server.tools.ldm.websocket import broadcast_cell_update
        await broadcast_cell_update(
            file_id=row.file_id,
            row_id=row.id,
            row_num=row.row_num,
            target=row.target,
            status=row.status,
            updated_by=current_user["user_id"],
            updated_by_username=current_user["username"]
        )
    except Exception as e:
        # WebSocket broadcast failure shouldn't fail the API call
        logger.warning(f"Failed to broadcast cell update: {e}")

    user_id = current_user["user_id"]
    logger.info(f"Row updated: id={row_id}, user={user_id}")
    return row


# ============================================================================
# Project Tree (Full structure for File Explorer)
# ============================================================================

@router.get("/projects/{project_id}/tree")
async def get_project_tree(
    project_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """Get full project tree structure (folders + files) for File Explorer."""
    # Verify project ownership
    result = await db.execute(
        select(LDMProject).where(
            LDMProject.id == project_id,
            LDMProject.owner_id == current_user["user_id"]
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get all folders
    result = await db.execute(
        select(LDMFolder).where(LDMFolder.project_id == project_id)
    )
    folders = result.scalars().all()

    # Get all files
    result = await db.execute(
        select(LDMFile).where(LDMFile.project_id == project_id)
    )
    files = result.scalars().all()

    # Build tree structure
    def build_tree(parent_id=None):
        tree = []

        # Add folders at this level
        for folder in folders:
            if folder.parent_id == parent_id:
                tree.append({
                    "type": "folder",
                    "id": folder.id,
                    "name": folder.name,
                    "children": build_tree(folder.id)
                })

        # Add files at this level
        for file in files:
            if file.folder_id == parent_id:
                tree.append({
                    "type": "file",
                    "id": file.id,
                    "name": file.name,
                    "format": file.format,
                    "row_count": file.row_count
                })

        return tree

    return {
        "project": {
            "id": project.id,
            "name": project.name,
            "description": project.description
        },
        "tree": build_tree(None)
    }


# ============================================================================
# Translation Memory (TM) API
# ============================================================================

@router.get("/tm/suggest")
async def get_tm_suggestions(
    source: str,
    file_id: Optional[int] = None,
    project_id: Optional[int] = None,
    exclude_row_id: Optional[int] = None,
    threshold: float = 0.70,
    max_results: int = 5,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Get Translation Memory suggestions for a source text.

    Finds similar source texts in the database and returns their translations.

    Args:
        source: Korean source text to find matches for
        file_id: Optional - limit search to same file
        project_id: Optional - limit search to same project
        exclude_row_id: Optional - exclude this row from results
        threshold: Minimum similarity (0.0-1.0, default 0.70)
        max_results: Maximum suggestions (default 5)

    Returns:
        List of TM suggestions with source, target, similarity, etc.
    """
    from server.tools.ldm.tm import TranslationMemory

    logger.info(f"TM suggest: source={source[:30]}..., file={file_id}, project={project_id}")

    try:
        # Use PostgreSQL pg_trgm similarity() for efficient fuzzy matching
        # This is O(log n) with GIN index vs O(n) Python loop
        from sqlalchemy import text, literal_column

        # Build SQL with pg_trgm similarity
        # Note: Requires pg_trgm extension and GIN index on source column
        sql_params = {
            'search_text': source.strip(),
            'threshold': threshold,
            'max_results': max_results
        }

        # Base conditions - use parameterized queries (NO f-strings for SQL!)
        conditions = ["r.target IS NOT NULL", "r.target != ''"]
        if file_id:
            conditions.append("r.file_id = :file_id")
            sql_params['file_id'] = file_id
        elif project_id:
            conditions.append("f.project_id = :project_id")
            sql_params['project_id'] = project_id
        if exclude_row_id:
            conditions.append("r.id != :exclude_row_id")
            sql_params['exclude_row_id'] = exclude_row_id

        where_clause = " AND ".join(conditions)

        # Use pg_trgm similarity() for fuzzy matching
        # Falls back to exact match if pg_trgm not available
        sql = text(f"""
            SELECT
                r.id,
                r.source,
                r.target,
                r.file_id,
                f.name as file_name,
                similarity(lower(r.source), lower(:search_text)) as sim
            FROM ldm_rows r
            JOIN ldm_files f ON r.file_id = f.id
            WHERE {where_clause}
              AND similarity(lower(r.source), lower(:search_text)) >= :threshold
            ORDER BY sim DESC
            LIMIT :max_results
        """)

        result = await db.execute(sql, sql_params)
        rows = result.fetchall()

        suggestions = [
            {
                'source': row.source,
                'target': row.target,
                'similarity': round(float(row.sim), 3),
                'row_id': row.id,
                'file_name': row.file_name
            }
            for row in rows
        ]

        logger.info(f"TM found {len(suggestions)} suggestions (pg_trgm)")
        return {"suggestions": suggestions, "count": len(suggestions)}

    except Exception as e:
        logger.error(f"TM suggest failed: {e}")
        raise HTTPException(status_code=500, detail=f"TM search failed: {str(e)}")


# ============================================================================
# Translation Memory CRUD (TMManager-based)
# ============================================================================

@router.post("/tm/upload", response_model=TMUploadResponse)
async def upload_tm(
    name: str = Form(...),
    source_lang: str = Form("ko"),
    target_lang: str = Form("en"),
    description: Optional[str] = Form(None),
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Upload a Translation Memory file.

    Supported formats:
    - TXT/TSV: Column 5 = Source, Column 6 = Target
    - XML: StrOrigin = Source, Str = Target
    - XLSX: Column A = Source, Column B = Target

    Performance: ~20,000+ entries/second bulk insert
    """
    filename = file.filename or "unknown"
    ext = filename.lower().split('.')[-1] if '.' in filename else ''

    if ext not in ('txt', 'tsv', 'xml', 'xlsx', 'xls'):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported TM format: {ext}. Use TXT, TSV, XML, or XLSX."
        )

    logger.info(f"TM upload started: name={name}, file={filename}, user={current_user['user_id']}")

    try:
        file_content = await file.read()

        # Run sync TMManager in threadpool to avoid blocking event loop
        def _upload_tm():
            sync_db = next(get_db())
            try:
                from server.tools.ldm.tm_manager import TMManager
                tm_manager = TMManager(sync_db)
                return tm_manager.upload_tm(
                    file_content=file_content,
                    filename=filename,
                    name=name,
                    owner_id=current_user["user_id"],
                    source_lang=source_lang,
                    target_lang=target_lang,
                    description=description
                )
            finally:
                sync_db.close()

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _upload_tm)
        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"TM upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"TM upload failed: {str(e)}")


@router.get("/tm", response_model=List[TMResponse])
async def list_tms(
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """List all Translation Memories for current user."""
    result = await db.execute(
        select(LDMTranslationMemory).where(
            LDMTranslationMemory.owner_id == current_user["user_id"]
        ).order_by(LDMTranslationMemory.created_at.desc())
    )
    tms = result.scalars().all()

    logger.info(f"Listed {len(tms)} TMs for user {current_user['user_id']}")
    return tms


@router.get("/tm/{tm_id}", response_model=TMResponse)
async def get_tm(
    tm_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """Get a Translation Memory by ID."""
    result = await db.execute(
        select(LDMTranslationMemory).where(
            LDMTranslationMemory.id == tm_id,
            LDMTranslationMemory.owner_id == current_user["user_id"]
        )
    )
    tm = result.scalar_one_or_none()

    if not tm:
        raise HTTPException(status_code=404, detail="Translation Memory not found")

    return tm


@router.delete("/tm/{tm_id}")
async def delete_tm(
    tm_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """Delete a Translation Memory and all its entries."""
    result = await db.execute(
        select(LDMTranslationMemory).where(
            LDMTranslationMemory.id == tm_id,
            LDMTranslationMemory.owner_id == current_user["user_id"]
        )
    )
    tm = result.scalar_one_or_none()

    if not tm:
        raise HTTPException(status_code=404, detail="Translation Memory not found")

    entry_count = tm.entry_count
    await db.delete(tm)
    await db.commit()

    logger.info(f"Deleted TM: id={tm_id}, entries={entry_count}")
    return {"message": "Translation Memory deleted", "entries_deleted": entry_count}


@router.get("/tm/{tm_id}/search/exact")
async def search_tm_exact(
    tm_id: int,
    source: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Search for exact match in a Translation Memory.

    Uses hash-based O(1) lookup for maximum speed.
    """
    logger.info(f"TM exact search: tm_id={tm_id}, source={source[:30]}...")

    # Verify TM ownership (async)
    tm_result = await db.execute(
        select(LDMTranslationMemory).where(
            LDMTranslationMemory.id == tm_id,
            LDMTranslationMemory.owner_id == current_user["user_id"]
        )
    )
    if not tm_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Translation Memory not found")

    # Generate hash for O(1) lookup (async query)
    normalized = normalize_text_for_hash(source)
    source_hash = hashlib.sha256(normalized.encode('utf-8')).hexdigest()

    entry_result = await db.execute(
        select(LDMTMEntry).where(
            LDMTMEntry.tm_id == tm_id,
            LDMTMEntry.source_hash == source_hash
        )
    )
    entry = entry_result.scalar_one_or_none()

    if entry:
        return {
            "match": {
                "source_text": entry.source_text,
                "target_text": entry.target_text,
                "similarity": 1.0,
                "tier": 1,
                "strategy": "perfect_whole_match"
            },
            "found": True
        }
    return {"match": None, "found": False}


@router.get("/tm/{tm_id}/search")
async def search_tm(
    tm_id: int,
    pattern: str,
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Search a Translation Memory using LIKE pattern.

    For fuzzy/similar text searching (not exact match).
    """
    logger.info(f"TM search: tm_id={tm_id}, pattern={pattern[:30]}...")

    # Verify TM ownership (async)
    tm_result = await db.execute(
        select(LDMTranslationMemory).where(
            LDMTranslationMemory.id == tm_id,
            LDMTranslationMemory.owner_id == current_user["user_id"]
        )
    )
    if not tm_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Translation Memory not found")

    # Async LIKE search
    entries_result = await db.execute(
        select(LDMTMEntry).where(
            LDMTMEntry.tm_id == tm_id,
            LDMTMEntry.source_text.ilike(f"%{pattern}%")
        ).limit(limit)
    )
    entries = entries_result.scalars().all()

    results = [
        {
            "source_text": e.source_text,
            "target_text": e.target_text,
            "similarity": 0.0,  # LIKE doesn't provide similarity
            "tier": 0,
            "strategy": "like_search"
        }
        for e in entries
    ]
    return {"results": results, "count": len(results)}


@router.post("/tm/{tm_id}/entries")
async def add_tm_entry(
    tm_id: int,
    source_text: str = Form(...),
    target_text: str = Form(...),
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Add a single entry to a Translation Memory (Adaptive TM).

    Used to add translations as they're created during editing.
    """
    logger.info(f"Adding TM entry: tm_id={tm_id}, source={source_text[:30]}...")

    # Verify TM ownership (async)
    tm_result = await db.execute(
        select(LDMTranslationMemory).where(
            LDMTranslationMemory.id == tm_id,
            LDMTranslationMemory.owner_id == current_user["user_id"]
        )
    )
    if not tm_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Translation Memory not found")

    # Run sync bulk_copy in threadpool to avoid blocking event loop
    def _add_entry():
        sync_db = next(get_db())
        try:
            from server.tools.ldm.tm_manager import TMManager
            tm_manager = TMManager(sync_db)
            return tm_manager.add_entry(tm_id, source_text, target_text)
        finally:
            sync_db.close()

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, _add_entry)

    if not result:
        raise HTTPException(status_code=404, detail="Translation Memory not found")

    logger.success(f"TM entry added: tm_id={tm_id}, total entries={result['entry_count']}")
    return result


@router.post("/tm/{tm_id}/build-indexes")
async def build_tm_indexes(
    tm_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Build FAISS indexes for a Translation Memory.

    Creates:
    - whole_text_lookup (hash index for Tier 1 exact match)
    - line_lookup (hash index for Tier 3 line match)
    - whole.index (FAISS HNSW for Tier 2 semantic search)
    - line.index (FAISS HNSW for Tier 4 line-by-line search)

    This is required before using the 5-Tier Cascade TM search.
    Building indexes can take several minutes for large TMs (50k+ entries).

    Returns operation_id for progress tracking via WebSocket/TaskManager.
    """
    from server.tools.ldm.tm_indexer import TMIndexer
    from server.utils.progress_tracker import TrackedOperation

    logger.info(f"Building TM indexes: tm_id={tm_id}, user={current_user['user_id']}")

    # Verify TM ownership (async)
    tm_result = await db.execute(
        select(LDMTranslationMemory).where(
            LDMTranslationMemory.id == tm_id
        )
    )
    tm = tm_result.scalar_one_or_none()

    if not tm:
        raise HTTPException(status_code=404, detail="Translation Memory not found")

    if tm.owner_id != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    tm_name = tm.name  # Capture for use in executor

    # Run indexing in threadpool to avoid blocking event loop
    def _build_indexes():
        sync_db = next(get_db())
        try:
            # Create operation for progress tracking
            with TrackedOperation(
                operation_name=f"Build TM Indexes: {tm_name}",
                user_id=current_user["user_id"],
                username=current_user.get("username", "unknown"),
                tool_name="LDM",
                function_name="build_tm_indexes",
                total_steps=4,
                parameters={"tm_id": tm_id}
            ) as tracker:
                # Build indexes with progress callback
                def progress_callback(stage: str, current: int, total: int):
                    progress_pct = (current / total) * 100 if total > 0 else 0
                    tracker.update(progress_pct, stage, current, total)

                indexer = TMIndexer(sync_db)
                result = indexer.build_indexes(tm_id, progress_callback=progress_callback)

                logger.success(f"TM indexes built: tm_id={tm_id}, entries={result['entry_count']}")
                return result
        finally:
            sync_db.close()

    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _build_indexes)
        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"TM index build failed: {e}")
        raise HTTPException(status_code=500, detail=f"Index build failed: {str(e)}")


@router.get("/tm/{tm_id}/indexes")
async def get_tm_index_status(
    tm_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Get index status for a Translation Memory.

    Returns list of indexes and their status.
    """
    from server.database.models import LDMTMIndex

    # Verify TM ownership
    result = await db.execute(
        select(LDMTranslationMemory).where(
            LDMTranslationMemory.id == tm_id,
            LDMTranslationMemory.owner_id == current_user["user_id"]
        )
    )
    tm = result.scalar_one_or_none()

    if not tm:
        raise HTTPException(status_code=404, detail="Translation Memory not found")

    # Get indexes
    result = await db.execute(
        select(LDMTMIndex).where(LDMTMIndex.tm_id == tm_id)
    )
    indexes = result.scalars().all()

    return {
        "tm_id": tm_id,
        "tm_status": tm.status,
        "indexes": [
            {
                "type": idx.index_type,
                "status": idx.status,
                "file_size": idx.file_size,
                "built_at": idx.built_at.isoformat() if idx.built_at else None
            }
            for idx in indexes
        ]
    }


# ============================================================================
# File to TM Conversion Endpoint
# ============================================================================

class FileToTMRequest(BaseModel):
    name: str
    project_id: Optional[int] = None
    language: str = "en"
    description: Optional[str] = None


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

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _create_tm)

        logger.info(f"TM created from file: tm_id={result['tm_id']}, entries={result['entry_count']}")
        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"File to TM conversion failed: {e}")
        raise HTTPException(status_code=500, detail=f"Conversion failed: {str(e)}")


# ============================================================================
# File Download/Export Endpoints
# ============================================================================

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
    Rebuild XML file from rows with FULL structure preservation.

    XML format:
    <?xml version="1.0" encoding="UTF-8"?>
    <RootElement rootAttr="...">
        <ElementTag stringid="ID" strorigin="source" str="target" otherAttr="..."/>
    </RootElement>

    Uses:
    - file_metadata.root_element: Original root element tag name
    - file_metadata.root_attributes: Original root element attributes
    - file_metadata.element_tag: Original localization element tag name
    - row.extra_data: Extra attributes beyond stringid/strorigin/str
    """
    import xml.etree.ElementTree as ET
    from xml.dom import minidom

    file_metadata = file_metadata or {}

    # Use original root element or default to LangData
    root_tag = file_metadata.get("root_element", "LangData")
    root = ET.Element(root_tag)

    # Add original root attributes if preserved
    root_attribs = file_metadata.get("root_attributes")
    if root_attribs:
        for key, val in root_attribs.items():
            root.set(key, val)

    # Use original element tag or default to String
    element_tag = file_metadata.get("element_tag", "String")

    for row in rows:
        string_elem = ET.SubElement(root, element_tag)

        # Set core attributes
        string_elem.set("stringid", row.string_id or "")
        string_elem.set("strorigin", row.source or "")
        string_elem.set("str", row.target or "")

        # Add extra attributes from extra_data
        if row.extra_data:
            for attr_name, attr_val in row.extra_data.items():
                string_elem.set(attr_name, attr_val or "")

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


# ============================================================================
# Sync to Central Server (Offline → Online)
# ============================================================================

class SyncFileToCentralRequest(BaseModel):
    """Request body for syncing a local file to central PostgreSQL."""
    file_id: int  # File ID in local SQLite
    destination_project_id: int  # Project ID in central PostgreSQL


class SyncFileToCentralResponse(BaseModel):
    """Response for sync operation."""
    success: bool
    new_file_id: Optional[int] = None
    rows_synced: int = 0
    message: str


class SyncTMToCentralRequest(BaseModel):
    """Request body for syncing a local TM to central PostgreSQL."""
    tm_id: int  # TM ID in local SQLite


class SyncTMToCentralResponse(BaseModel):
    """Response for TM sync operation."""
    success: bool
    new_tm_id: Optional[int] = None
    entries_synced: int = 0
    message: str


@router.post("/sync-to-central", response_model=SyncFileToCentralResponse)
async def sync_file_to_central(
    request: SyncFileToCentralRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Sync a file from local SQLite to central PostgreSQL.

    This endpoint:
    1. Reads file metadata + all rows from local SQLite
    2. Creates new file record in PostgreSQL (destination project)
    3. Bulk inserts all rows to PostgreSQL
    4. Returns the new file_id in central DB

    Use this when:
    - User worked offline (SQLite mode)
    - User reconnected (went online)
    - User wants to upload local work to central server

    The file data is passed as JSON (not re-read from disk).
    """
    from server.config import ACTIVE_DATABASE_TYPE
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    import os

    logger.info(f"Sync to central: file_id={request.file_id}, dest_project={request.destination_project_id}")

    # Verify we're online (connected to PostgreSQL)
    if ACTIVE_DATABASE_TYPE != "postgresql":
        raise HTTPException(
            status_code=400,
            detail="Cannot sync to central server while in offline mode. Connect to server first."
        )

    # Verify destination project exists and user has access
    project_result = await db.execute(
        select(LDMProject).where(
            LDMProject.id == request.destination_project_id,
            LDMProject.owner_id == current_user["user_id"]
        )
    )
    if not project_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Destination project not found or access denied")

    # Read from local SQLite database
    # The SQLite file is at server/data/locanext.db
    sqlite_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "locanext.db")

    if not os.path.exists(sqlite_path):
        raise HTTPException(
            status_code=400,
            detail="No local database found. You may not have worked offline."
        )

    try:
        # Create SQLite engine and session
        sqlite_engine = create_engine(f"sqlite:///{sqlite_path}")
        sqlite_session = Session(sqlite_engine)

        try:
            # Read the file from SQLite
            local_file = sqlite_session.query(LDMFile).filter(LDMFile.id == request.file_id).first()

            if not local_file:
                raise HTTPException(status_code=404, detail="File not found in local database")

            # Read all rows for this file from SQLite
            local_rows = sqlite_session.query(LDMRow).filter(
                LDMRow.file_id == request.file_id
            ).order_by(LDMRow.row_num).all()

            logger.info(f"Read {len(local_rows)} rows from local SQLite for file {request.file_id}")

            # Create new file in PostgreSQL
            new_file = LDMFile(
                project_id=request.destination_project_id,
                folder_id=None,  # Goes to project root
                name=local_file.name,
                original_filename=local_file.original_filename,
                format=local_file.format,
                row_count=len(local_rows),
                source_language=local_file.source_language,
                target_language=local_file.target_language,
                extra_data=local_file.extra_data,
                created_by=current_user["user_id"]
            )
            db.add(new_file)
            await db.flush()

            # Create rows in PostgreSQL
            for local_row in local_rows:
                new_row = LDMRow(
                    file_id=new_file.id,
                    row_num=local_row.row_num,
                    string_id=local_row.string_id,
                    source=local_row.source,
                    target=local_row.target,
                    status=local_row.status,
                    extra_data=local_row.extra_data
                )
                db.add(new_row)

            await db.commit()

            logger.success(f"Synced file to central: local_id={request.file_id} → central_id={new_file.id}, rows={len(local_rows)}")

            return SyncFileToCentralResponse(
                success=True,
                new_file_id=new_file.id,
                rows_synced=len(local_rows),
                message=f"Successfully synced {len(local_rows)} rows to central server"
            )

        finally:
            sqlite_session.close()
            sqlite_engine.dispose()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Sync to central failed: {e}")
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@router.post("/tm/sync-to-central", response_model=SyncTMToCentralResponse)
async def sync_tm_to_central(
    request: SyncTMToCentralRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Sync a Translation Memory from local SQLite to central PostgreSQL.

    This endpoint:
    1. Reads TM metadata + all entries from local SQLite
    2. Creates new TM record in PostgreSQL
    3. Bulk inserts all entries to PostgreSQL
    4. Returns the new tm_id in central DB
    """
    from server.config import ACTIVE_DATABASE_TYPE
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    import os

    logger.info(f"Sync TM to central: tm_id={request.tm_id}")

    # Verify we're online (connected to PostgreSQL)
    if ACTIVE_DATABASE_TYPE != "postgresql":
        raise HTTPException(
            status_code=400,
            detail="Cannot sync to central server while in offline mode. Connect to server first."
        )

    # Read from local SQLite database
    sqlite_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "locanext.db")

    if not os.path.exists(sqlite_path):
        raise HTTPException(
            status_code=400,
            detail="No local database found. You may not have worked offline."
        )

    try:
        # Create SQLite engine and session
        sqlite_engine = create_engine(f"sqlite:///{sqlite_path}")
        sqlite_session = Session(sqlite_engine)

        try:
            # Read the TM from SQLite
            local_tm = sqlite_session.query(LDMTranslationMemory).filter(
                LDMTranslationMemory.id == request.tm_id
            ).first()

            if not local_tm:
                raise HTTPException(status_code=404, detail="Translation Memory not found in local database")

            # Read all entries for this TM from SQLite
            local_entries = sqlite_session.query(LDMTMEntry).filter(
                LDMTMEntry.tm_id == request.tm_id
            ).all()

            logger.info(f"Read {len(local_entries)} entries from local SQLite for TM {request.tm_id}")

            # Create new TM in PostgreSQL
            new_tm = LDMTranslationMemory(
                name=local_tm.name,
                description=local_tm.description,
                owner_id=current_user["user_id"],
                source_lang=local_tm.source_lang,
                target_lang=local_tm.target_lang,
                entry_count=len(local_entries),
                status="pending"  # Will need re-indexing on server
            )
            db.add(new_tm)
            await db.flush()

            # Bulk insert entries to PostgreSQL
            for local_entry in local_entries:
                new_entry = LDMTMEntry(
                    tm_id=new_tm.id,
                    source_text=local_entry.source_text,
                    target_text=local_entry.target_text,
                    source_hash=local_entry.source_hash,
                    created_by=local_entry.created_by,
                    change_date=local_entry.change_date
                )
                db.add(new_entry)

            await db.commit()

            logger.success(f"Synced TM to central: local_id={request.tm_id} → central_id={new_tm.id}, entries={len(local_entries)}")

            return SyncTMToCentralResponse(
                success=True,
                new_tm_id=new_tm.id,
                entries_synced=len(local_entries),
                message=f"Successfully synced {len(local_entries)} TM entries to central server. Run 'Build Indexes' on the server to enable semantic search."
            )

        finally:
            sqlite_session.close()
            sqlite_engine.dispose()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"TM sync to central failed: {e}")
        raise HTTPException(status_code=500, detail=f"TM sync failed: {str(e)}")
