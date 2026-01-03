"""
Sync endpoints - Online/Offline synchronization.

Includes:
- sync-to-central: Push local SQLite changes to PostgreSQL
- download-for-offline: Pull file from PostgreSQL to local SQLite

Migrated from api.py lines 2786-3042
"""

import os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, create_engine
from sqlalchemy.orm import Session
from loguru import logger
from pydantic import BaseModel
from typing import Optional

from server.utils.dependencies import get_async_db, get_current_active_user_async
from server.database.models import (
    LDMProject, LDMFile, LDMRow,
    LDMTranslationMemory, LDMTMEntry
)
from server.tools.ldm.schemas import (
    SyncFileToCentralRequest, SyncFileToCentralResponse,
    SyncTMToCentralRequest, SyncTMToCentralResponse
)
from server.tools.ldm.permissions import can_access_project, can_access_file, get_accessible_projects
from server.database.offline import get_offline_db

router = APIRouter(tags=["LDM"])


# =============================================================================
# Response Models
# =============================================================================

class DownloadForOfflineResponse(BaseModel):
    success: bool
    file_id: int
    file_name: str
    row_count: int
    message: str


class OfflineStatusResponse(BaseModel):
    mode: str  # "online" or "offline"
    offline_available: bool
    file_count: int
    row_count: int
    pending_changes: int
    last_sync: Optional[str]


class OfflineFileInfo(BaseModel):
    id: int
    name: str
    format: str
    row_count: int
    sync_status: str
    downloaded_at: Optional[str]


class OfflineFilesResponse(BaseModel):
    files: list[OfflineFileInfo]
    total_count: int


# =============================================================================
# Offline Status & Files
# =============================================================================

@router.get("/offline/status", response_model=OfflineStatusResponse)
async def get_offline_status(
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Get current offline status and statistics.

    Returns:
    - mode: "online" (PostgreSQL) or "offline" (SQLite)
    - offline_available: Whether any files are downloaded for offline
    - file_count: Number of files available offline
    - row_count: Total rows available offline
    - pending_changes: Changes waiting to sync
    - last_sync: Last sync timestamp
    """
    from server.config import ACTIVE_DATABASE_TYPE

    try:
        offline_db = get_offline_db()
        stats = offline_db.get_stats()
        last_sync = offline_db.get_last_sync()

        return OfflineStatusResponse(
            mode="offline" if ACTIVE_DATABASE_TYPE == "sqlite" else "online",
            offline_available=stats.get("files", 0) > 0,
            file_count=stats.get("files", 0),
            row_count=stats.get("rows", 0),
            pending_changes=stats.get("pending_changes", 0),
            last_sync=last_sync
        )
    except Exception as e:
        logger.error(f"Failed to get offline status: {e}")
        return OfflineStatusResponse(
            mode="online",
            offline_available=False,
            file_count=0,
            row_count=0,
            pending_changes=0,
            last_sync=None
        )


@router.get("/offline/files", response_model=OfflineFilesResponse)
async def list_offline_files(
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    List all files available for offline use.

    Returns list of downloaded files with their sync status.
    """
    try:
        offline_db = get_offline_db()

        # Get all projects first (to get all files)
        all_files = []
        projects = offline_db.get_projects()

        for project in projects:
            files = offline_db.get_files(project["id"])
            for f in files:
                all_files.append(OfflineFileInfo(
                    id=f["id"],
                    name=f["name"],
                    format=f.get("format", "txt"),
                    row_count=f.get("row_count", 0),
                    sync_status=f.get("sync_status", "synced"),
                    downloaded_at=f.get("downloaded_at")
                ))

        return OfflineFilesResponse(
            files=all_files,
            total_count=len(all_files)
        )
    except Exception as e:
        logger.error(f"Failed to list offline files: {e}")
        return OfflineFilesResponse(files=[], total_count=0)


# =============================================================================
# Download for Offline
# =============================================================================

@router.post("/files/{file_id}/download-for-offline", response_model=DownloadForOfflineResponse)
async def download_file_for_offline(
    file_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Download a file from PostgreSQL to local SQLite for offline use.

    This endpoint:
    1. Reads file metadata + all rows from PostgreSQL (central server)
    2. Stores them in local SQLite database
    3. Returns success with row count

    Use this when:
    - User wants to work on a file while offline
    - User is about to go offline and wants to prepare files
    """
    from server.config import ACTIVE_DATABASE_TYPE

    logger.info(f"Download for offline: file_id={file_id}")

    # Verify we're online (connected to PostgreSQL)
    if ACTIVE_DATABASE_TYPE != "postgresql":
        raise HTTPException(
            status_code=400,
            detail="Already in offline mode. File should already be available locally."
        )

    # Verify file access (DESIGN-001: Public by default)
    if not await can_access_file(db, file_id, current_user):
        raise HTTPException(status_code=403, detail="Access denied")

    # Get file from PostgreSQL
    result = await db.execute(select(LDMFile).where(LDMFile.id == file_id))
    file = result.scalar_one_or_none()

    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    # Get all rows for this file
    rows_result = await db.execute(
        select(LDMRow)
        .where(LDMRow.file_id == file_id)
        .order_by(LDMRow.row_num)
    )
    rows = rows_result.scalars().all()

    # Get the project info
    project_result = await db.execute(select(LDMProject).where(LDMProject.id == file.project_id))
    project = project_result.scalar_one_or_none()

    try:
        # Get offline database instance
        offline_db = get_offline_db()

        # Save project (needed for foreign key)
        if project:
            offline_db.save_project({
                "id": project.id,
                "name": project.name,
                "description": project.description,
                "platform_id": project.platform_id,
                "owner_id": project.owner_id,
                "is_restricted": project.is_restricted,
                "created_at": project.created_at.isoformat() if project.created_at else None,
                "updated_at": project.updated_at.isoformat() if project.updated_at else None
            })

        # Save file
        offline_db.save_file({
            "id": file.id,
            "name": file.name,
            "original_filename": file.original_filename,
            "format": file.format,
            "row_count": file.row_count,
            "source_language": file.source_language,
            "target_language": file.target_language,
            "project_id": file.project_id,
            "folder_id": file.folder_id,
            "extra_data": file.extra_data,
            "created_at": file.created_at.isoformat() if file.created_at else None,
            "updated_at": file.updated_at.isoformat() if file.updated_at else None
        })

        # Save all rows
        row_data = []
        for row in rows:
            row_data.append({
                "id": row.id,
                "row_num": row.row_num,
                "string_id": row.string_id,
                "source": row.source,
                "target": row.target,
                "memo": row.memo if hasattr(row, 'memo') else None,
                "status": row.status,
                "extra_data": row.extra_data,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "updated_at": row.updated_at.isoformat() if row.updated_at else None
            })

        offline_db.save_rows(file.id, row_data)

        # Update sync metadata
        offline_db.set_last_sync()

        logger.success(f"Downloaded for offline: file={file.name}, rows={len(rows)}")

        return DownloadForOfflineResponse(
            success=True,
            file_id=file.id,
            file_name=file.name,
            row_count=len(rows),
            message=f"Downloaded {file.name} with {len(rows)} rows for offline use"
        )

    except Exception as e:
        logger.error(f"Download for offline failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to save for offline: {str(e)}")


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

    logger.info(f"Sync to central: file_id={request.file_id}, dest_project={request.destination_project_id}")

    # Verify we're online (connected to PostgreSQL)
    if ACTIVE_DATABASE_TYPE != "postgresql":
        raise HTTPException(
            status_code=400,
            detail="Cannot sync to central server while in offline mode. Connect to server first."
        )

    # Verify destination project access (DESIGN-001: Public by default)
    if not await can_access_project(db, request.destination_project_id, current_user):
        raise HTTPException(status_code=403, detail="Access denied to destination project")

    # Read from local SQLite database
    # The SQLite file is at server/data/locanext.db
    sqlite_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
        "data", "locanext.db"
    )

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
        logger.error(f"Sync to central failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Sync failed. Check server logs.")


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

    logger.info(f"Sync TM to central: tm_id={request.tm_id}")

    # Verify we're online (connected to PostgreSQL)
    if ACTIVE_DATABASE_TYPE != "postgresql":
        raise HTTPException(
            status_code=400,
            detail="Cannot sync to central server while in offline mode. Connect to server first."
        )

    # Read from local SQLite database
    sqlite_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
        "data", "locanext.db"
    )

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
        logger.error(f"TM sync to central failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="TM sync failed. Check server logs.")
