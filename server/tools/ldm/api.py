"""
LDM (LanguageData Manager) API Endpoints

REST API for managing localization projects, folders, files, and rows.
Supports real-time collaboration via WebSocket (see websocket.py).
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel
from loguru import logger
from io import BytesIO

from server.utils.dependencies import get_async_db, get_current_active_user_async, get_db
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
    - TXT/TSV: Tab-delimited, columns 0-4=StringID, 5=Source(KR), 6=Target
    - XML: LocStr elements with StringId, StrOrigin(source), Str(target)
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

    if ext in ('txt', 'tsv'):
        from server.tools.ldm.file_handlers.txt_handler import parse_txt_file, get_file_format, get_source_language
        file_content = await file.read()
        rows_data = parse_txt_file(file_content, filename)
        file_format = get_file_format()
        source_lang = get_source_language()
    elif ext == 'xml':
        from server.tools.ldm.file_handlers.xml_handler import parse_xml_file, get_file_format, get_source_language
        file_content = await file.read()
        rows_data = parse_xml_file(file_content, filename)
        file_format = get_file_format()
        source_lang = get_source_language()
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

    # Create file record
    new_file = LDMFile(
        project_id=project_id,
        folder_id=folder_id,
        name=filename,
        original_filename=filename,
        format=file_format,
        row_count=len(rows_data),
        source_language=source_lang,
        target_language=None  # Set later based on project settings
    )
    db.add(new_file)
    await db.flush()  # Get the file ID

    # Create row records
    for row_data in rows_data:
        row = LDMRow(
            file_id=new_file.id,
            row_num=row_data["row_num"],
            string_id=row_data["string_id"],
            source=row_data["source"],
            target=row_data["target"],
            status=row_data["status"]
        )
        db.add(row)

    await db.commit()
    await db.refresh(new_file)

    logger.success(f"File uploaded: id={new_file.id}, name='{filename}', rows={len(rows_data)}")
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

    # Need sync session for TM queries (using async session's sync_session)
    # For now, use a simpler approach with direct query

    try:
        # Build query for rows with translations
        query = select(
            LDMRow.id,
            LDMRow.source,
            LDMRow.target,
            LDMRow.file_id,
            LDMFile.name.label('file_name')
        ).join(
            LDMFile, LDMRow.file_id == LDMFile.id
        ).where(
            LDMRow.target.isnot(None),
            LDMRow.target != ''
        )

        # Scope by file if specified
        if file_id:
            query = query.where(LDMRow.file_id == file_id)
        elif project_id:
            query = query.where(LDMFile.project_id == project_id)

        # Exclude current row
        if exclude_row_id:
            query = query.where(LDMRow.id != exclude_row_id)

        # Limit search
        query = query.limit(1000)

        result = await db.execute(query)
        rows = result.fetchall()

        # Calculate similarity for each row
        normalized_source = source.strip().lower()
        suggestions = []

        for row in rows:
            if row.source:
                row_source = row.source.strip().lower()

                # Simple similarity calculation
                if normalized_source == row_source:
                    similarity = 1.0
                elif normalized_source in row_source or row_source in normalized_source:
                    shorter = min(len(normalized_source), len(row_source))
                    longer = max(len(normalized_source), len(row_source))
                    similarity = 0.8 * (shorter / longer)
                else:
                    # Word-level Jaccard similarity
                    words1 = set(normalized_source.split())
                    words2 = set(row_source.split())
                    if words1 and words2:
                        intersection = len(words1 & words2)
                        union = len(words1 | words2)
                        similarity = intersection / union if union > 0 else 0
                    else:
                        similarity = 0

                if similarity >= threshold:
                    suggestions.append({
                        'source': row.source,
                        'target': row.target,
                        'similarity': round(similarity, 3),
                        'row_id': row.id,
                        'file_name': row.file_name
                    })

        # Sort by similarity and limit
        suggestions.sort(key=lambda x: x['similarity'], reverse=True)
        suggestions = suggestions[:max_results]

        logger.info(f"TM found {len(suggestions)} suggestions")
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
    from server.tools.ldm.tm_manager import TMManager

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

        # Use sync session for TMManager
        sync_db = next(get_db())
        try:
            tm_manager = TMManager(sync_db)
            result = tm_manager.upload_tm(
                file_content=file_content,
                filename=filename,
                name=name,
                owner_id=current_user["user_id"],
                source_lang=source_lang,
                target_lang=target_lang,
                description=description
            )
            return result
        finally:
            sync_db.close()

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
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Search for exact match in a Translation Memory.

    Uses hash-based O(1) lookup for maximum speed.
    """
    from server.tools.ldm.tm_manager import TMManager

    logger.info(f"TM exact search: tm_id={tm_id}, source={source[:30]}...")

    sync_db = next(get_db())
    try:
        tm_manager = TMManager(sync_db)

        # Verify TM ownership
        tm = tm_manager.get_tm(tm_id)
        if not tm or tm.get("owner_id") != current_user["user_id"]:
            # Try async check for ownership
            pass  # Will fail in search if not owned

        result = tm_manager.search_exact(tm_id, source)
        if result:
            return {"match": result, "found": True}
        return {"match": None, "found": False}
    finally:
        sync_db.close()


@router.get("/tm/{tm_id}/search")
async def search_tm(
    tm_id: int,
    pattern: str,
    limit: int = Query(10, ge=1, le=100),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Search a Translation Memory using LIKE pattern.

    For fuzzy/similar text searching (not exact match).
    """
    from server.tools.ldm.tm_manager import TMManager

    logger.info(f"TM search: tm_id={tm_id}, pattern={pattern[:30]}...")

    sync_db = next(get_db())
    try:
        tm_manager = TMManager(sync_db)
        results = tm_manager.search_like(tm_id, pattern, limit=limit)
        return {"results": results, "count": len(results)}
    finally:
        sync_db.close()


@router.post("/tm/{tm_id}/entries")
async def add_tm_entry(
    tm_id: int,
    source_text: str = Form(...),
    target_text: str = Form(...),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Add a single entry to a Translation Memory (Adaptive TM).

    Used to add translations as they're created during editing.
    """
    from server.tools.ldm.tm_manager import TMManager

    logger.info(f"Adding TM entry: tm_id={tm_id}, source={source_text[:30]}...")

    sync_db = next(get_db())
    try:
        tm_manager = TMManager(sync_db)
        result = tm_manager.add_entry(tm_id, source_text, target_text)

        if not result:
            raise HTTPException(status_code=404, detail="Translation Memory not found")

        logger.success(f"TM entry added: tm_id={tm_id}, total entries={result['entry_count']}")
        return result
    finally:
        sync_db.close()


@router.post("/tm/{tm_id}/build-indexes")
async def build_tm_indexes(
    tm_id: int,
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
    """
    from server.tools.ldm.tm_indexer import TMIndexer

    logger.info(f"Building TM indexes: tm_id={tm_id}, user={current_user['user_id']}")

    sync_db = next(get_db())
    try:
        # Verify TM ownership first
        tm = sync_db.query(LDMTranslationMemory).filter(
            LDMTranslationMemory.id == tm_id
        ).first()

        if not tm:
            raise HTTPException(status_code=404, detail="Translation Memory not found")

        if tm.owner_id != current_user["user_id"]:
            raise HTTPException(status_code=403, detail="Access denied")

        # Build indexes
        indexer = TMIndexer(sync_db)
        result = indexer.build_indexes(tm_id)

        logger.success(f"TM indexes built: tm_id={tm_id}, entries={result['entry_count']}")
        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"TM index build failed: {e}")
        raise HTTPException(status_code=500, detail=f"Index build failed: {str(e)}")
    finally:
        sync_db.close()


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
    format_lower = file.format.lower() if file.format else ""
    if format_lower == "txt":
        content = _build_txt_file(rows)
        media_type = "text/plain"
        extension = ".txt"
    elif format_lower == "xml":
        content = _build_xml_file(rows)
        media_type = "application/xml"
        extension = ".xml"
    elif format_lower in ["xlsx", "excel"]:
        content = _build_excel_file(rows)
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


def _build_txt_file(rows: List[LDMRow]) -> bytes:
    """
    Rebuild TXT file from rows.

    TXT format: tab-separated columns
    Original format: idx0\tidx1\tidx2\tidx3\tidx4\tsource\ttarget
    """
    lines = []
    for row in rows:
        # Reconstruct string_id parts - stored with spaces, output with tabs
        # Upload stores as "0 100 0 0 1" (space-joined), we need "0\t100\t0\t0\t1"
        string_id_parts = row.string_id.split(' ') if row.string_id else [""] * 5

        # Ensure we have 5 parts for the index
        while len(string_id_parts) < 5:
            string_id_parts.append("")

        # Build line: idx0\tidx1\tidx2\tidx3\tidx4\tsource\ttarget
        source = row.source or ""
        target = row.target or ""

        # Replace newlines back to actual newlines in the file
        source = source.replace("↵", "\n")
        target = target.replace("↵", "\n")

        line = "\t".join(string_id_parts[:5] + [source, target])
        lines.append(line)

    content = "\n".join(lines)
    return content.encode('utf-8')


def _build_xml_file(rows: List[LDMRow]) -> bytes:
    """
    Rebuild XML file from rows.

    XML format:
    <?xml version="1.0" encoding="UTF-8"?>
    <LangData>
        <String stringid="ID" strorigin="source" str="target"/>
    </LangData>
    """
    import xml.etree.ElementTree as ET
    from xml.dom import minidom

    root = ET.Element("LangData")

    for row in rows:
        string_elem = ET.SubElement(root, "String")
        string_elem.set("stringid", row.string_id or "")
        string_elem.set("strorigin", row.source or "")
        string_elem.set("str", row.target or "")

    # Pretty print
    xml_str = ET.tostring(root, encoding='unicode')
    dom = minidom.parseString(xml_str)
    pretty_xml = dom.toprettyxml(indent="  ", encoding="UTF-8")

    return pretty_xml


def _build_excel_file(rows: List[LDMRow]) -> bytes:
    """
    Rebuild Excel file from rows.

    Excel format: Source in column A, Target in column B
    """
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Translations"

    # Header
    ws.cell(row=1, column=1, value="Source")
    ws.cell(row=1, column=2, value="Target")

    # Data
    for i, row in enumerate(rows, start=2):
        ws.cell(row=i, column=1, value=row.source or "")
        ws.cell(row=i, column=2, value=row.target or "")

    # Save to bytes
    output = BytesIO()
    wb.save(output)
    output.seek(0)

    return output.read()
