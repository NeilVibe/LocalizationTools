"""
LDM (LanguageData Manager) API Endpoints

REST API for managing localization projects, folders, files, and rows.
Supports real-time collaboration via WebSocket (see websocket.py).
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel
from loguru import logger

from server.utils.dependencies import get_async_db, get_current_active_user_async
from server.database.models import (
    User, LDMProject, LDMFolder, LDMFile, LDMRow, LDMEditHistory, LDMActiveSession
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
