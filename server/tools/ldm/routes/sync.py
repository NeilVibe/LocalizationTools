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


class SyncSubscription(BaseModel):
    id: int
    entity_type: str
    entity_id: int
    entity_name: str
    auto_subscribed: bool
    sync_status: str
    last_sync_at: Optional[str]
    created_at: Optional[str]


class SubscriptionsResponse(BaseModel):
    subscriptions: list[SyncSubscription]
    total_count: int


class SubscribeRequest(BaseModel):
    entity_type: str  # platform, project, file
    entity_id: int
    entity_name: str
    auto_subscribed: bool = False  # True if auto-synced on file open


class SubscribeResponse(BaseModel):
    success: bool
    subscription_id: int
    message: str


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
# Sync Subscriptions
# =============================================================================

@router.get("/offline/subscriptions", response_model=SubscriptionsResponse)
async def list_subscriptions(
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    List all active sync subscriptions.

    Shows what platforms/projects/files are enabled for offline sync.
    """
    try:
        offline_db = get_offline_db()
        subs = offline_db.get_subscriptions()

        subscriptions = [
            SyncSubscription(
                id=s["id"],
                entity_type=s["entity_type"],
                entity_id=s["entity_id"],
                entity_name=s["entity_name"],
                auto_subscribed=bool(s.get("auto_subscribed", 0)),
                sync_status=s.get("sync_status", "pending"),
                last_sync_at=s.get("last_sync_at"),
                created_at=s.get("created_at")
            )
            for s in subs
        ]

        return SubscriptionsResponse(
            subscriptions=subscriptions,
            total_count=len(subscriptions)
        )
    except Exception as e:
        logger.error(f"Failed to list subscriptions: {e}")
        return SubscriptionsResponse(subscriptions=[], total_count=0)


@router.post("/offline/subscribe", response_model=SubscribeResponse)
async def subscribe_for_offline(
    request: SubscribeRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Enable offline sync for a platform, project, or file.

    This creates a subscription and triggers initial download.
    Subsequent syncs happen automatically.
    """
    from server.config import ACTIVE_DATABASE_TYPE

    logger.info(f"Subscribe for offline: {request.entity_type}={request.entity_id}")

    if ACTIVE_DATABASE_TYPE != "postgresql":
        raise HTTPException(status_code=400, detail="Already in offline mode")

    try:
        offline_db = get_offline_db()

        # Create subscription
        sub_id = offline_db.add_subscription(
            entity_type=request.entity_type,
            entity_id=request.entity_id,
            entity_name=request.entity_name,
            auto_subscribed=request.auto_subscribed
        )

        # Trigger initial sync based on entity type
        if request.entity_type == "file":
            # Download single file
            await _sync_file_to_offline(db, request.entity_id, offline_db)
        elif request.entity_type == "project":
            # Download all files in project
            await _sync_project_to_offline(db, request.entity_id, offline_db)
        elif request.entity_type == "platform":
            # Download all projects in platform
            await _sync_platform_to_offline(db, request.entity_id, offline_db)

        # Mark subscription as synced
        offline_db.update_subscription_status(
            request.entity_type, request.entity_id, "synced"
        )

        return SubscribeResponse(
            success=True,
            subscription_id=sub_id,
            message=f"Enabled offline sync for {request.entity_type}: {request.entity_name}"
        )

    except Exception as e:
        logger.error(f"Subscribe failed: {e}", exc_info=True)
        # Mark as error
        try:
            offline_db.update_subscription_status(
                request.entity_type, request.entity_id, "error", str(e)
            )
        except:
            pass
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/offline/subscribe/{entity_type}/{entity_id}")
async def unsubscribe_from_offline(
    entity_type: str,
    entity_id: int,
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Disable offline sync for an entity.

    Removes the subscription. Local data is NOT deleted (user may want to keep it).
    """
    try:
        offline_db = get_offline_db()
        offline_db.remove_subscription(entity_type, entity_id)

        return {"success": True, "message": f"Disabled offline sync for {entity_type} {entity_id}"}
    except Exception as e:
        logger.error(f"Unsubscribe failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class SyncSubscriptionRequest(BaseModel):
    entity_type: str
    entity_id: int


class SyncSubscriptionResponse(BaseModel):
    success: bool
    entity_type: str
    entity_id: int
    updated_count: int
    message: str


@router.post("/offline/sync-subscription", response_model=SyncSubscriptionResponse)
async def sync_subscription(
    request: SyncSubscriptionRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Sync a single subscription (refresh from server).

    This endpoint is called periodically by the continuous sync mechanism
    to keep offline data fresh with server changes.
    """
    from server.config import ACTIVE_DATABASE_TYPE

    logger.debug(f"Sync subscription: {request.entity_type}={request.entity_id}")

    if ACTIVE_DATABASE_TYPE != "postgresql":
        raise HTTPException(status_code=400, detail="Already in offline mode")

    try:
        offline_db = get_offline_db()

        # Check if subscription exists
        if not offline_db.is_subscribed(request.entity_type, request.entity_id):
            raise HTTPException(status_code=404, detail="Subscription not found")

        updated_count = 0

        # Re-sync based on entity type
        if request.entity_type == "file":
            await _sync_file_to_offline(db, request.entity_id, offline_db)
            updated_count = 1
        elif request.entity_type == "project":
            # Count files in project
            files_result = await db.execute(
                select(LDMFile).where(LDMFile.project_id == request.entity_id)
            )
            files = files_result.scalars().all()
            updated_count = len(files)
            await _sync_project_to_offline(db, request.entity_id, offline_db)
        elif request.entity_type == "platform":
            # Count projects in platform
            projects_result = await db.execute(
                select(LDMProject).where(LDMProject.platform_id == request.entity_id)
            )
            projects = projects_result.scalars().all()
            updated_count = len(projects)
            await _sync_platform_to_offline(db, request.entity_id, offline_db)

        # Update subscription status
        offline_db.update_subscription_status(
            request.entity_type, request.entity_id, "synced"
        )

        return SyncSubscriptionResponse(
            success=True,
            entity_type=request.entity_type,
            entity_id=request.entity_id,
            updated_count=updated_count,
            message=f"Synced {request.entity_type} {request.entity_id}"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Sync subscription failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Internal Sync Helpers
# =============================================================================

async def _sync_file_to_offline(db: AsyncSession, file_id: int, offline_db):
    """
    Sync a single file to offline storage with merge logic.

    Merge Rules (last-write-wins):
    - Local synced + server newer → take server
    - Local modified + server newer → server wins, discard local
    - Local modified + local newer → keep local, push later
    - Server has row we don't → insert
    - We have row server deleted → delete local
    """
    result = await db.execute(select(LDMFile).where(LDMFile.id == file_id))
    file = result.scalar_one_or_none()
    if not file:
        raise HTTPException(status_code=404, detail=f"File {file_id} not found")

    # Get server rows
    rows_result = await db.execute(
        select(LDMRow).where(LDMRow.file_id == file_id).order_by(LDMRow.row_num)
    )
    server_rows = rows_result.scalars().all()

    # Save/update file metadata
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

    # Track merge stats
    stats = {"inserted": 0, "updated": 0, "skipped": 0, "deleted": 0}
    server_row_ids = set()

    # Merge each server row
    for row in server_rows:
        server_row_ids.add(row.id)
        row_data = {
            "id": row.id,
            "row_num": row.row_num,
            "string_id": row.string_id,
            "source": row.source,
            "target": row.target,
            "memo": row.memo if hasattr(row, 'memo') else None,
            "status": row.status,
            "extra_data": row.extra_data,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None
        }
        result = offline_db.merge_row(row_data, file.id)
        stats[result] += 1

    # Delete local rows that no longer exist on server
    local_row_ids = offline_db.get_local_row_server_ids(file.id)
    deleted_ids = local_row_ids - server_row_ids
    for deleted_id in deleted_ids:
        offline_db.delete_row(deleted_id)
        stats["deleted"] += 1

    # Push local changes to server
    pushed = await _push_local_changes_for_file(db, file_id, offline_db)

    logger.info(f"Synced file {file.name}: inserted={stats['inserted']}, updated={stats['updated']}, "
                f"skipped={stats['skipped']}, deleted={stats['deleted']}, pushed={pushed}")


async def _push_local_changes_for_file(db: AsyncSession, file_id: int, offline_db) -> int:
    """
    Push local changes for a file to the server.

    Returns: number of rows pushed
    """
    pushed_count = 0

    # Get modified rows
    modified_rows = offline_db.get_modified_rows(file_id)
    for local_row in modified_rows:
        server_id = local_row.get("server_id")
        if server_id:
            # Update existing row on server
            await db.execute(
                LDMRow.__table__.update()
                .where(LDMRow.id == server_id)
                .values(
                    target=local_row.get("target"),
                    memo=local_row.get("memo"),
                    status=local_row.get("status"),
                )
            )
            offline_db.mark_row_synced(local_row["id"])
            pushed_count += 1

    # Get new rows (created offline)
    new_rows = offline_db.get_new_rows(file_id)
    for local_row in new_rows:
        # Create new row on server
        new_row = LDMRow(
            file_id=file_id,
            row_num=local_row.get("row_num", 0),
            string_id=local_row.get("string_id"),
            source=local_row.get("source"),
            target=local_row.get("target"),
            status=local_row.get("status", "normal"),
            extra_data=local_row.get("extra_data"),
        )
        db.add(new_row)
        await db.flush()

        # Update local row with new server ID
        offline_db.mark_row_synced(local_row["id"])
        pushed_count += 1

    if pushed_count > 0:
        await db.commit()
        # Mark changes as synced
        for change in offline_db.get_pending_changes():
            if change.get("entity_type") == "row":
                offline_db.mark_change_synced(change["id"])

    return pushed_count


async def _sync_project_to_offline(db: AsyncSession, project_id: int, offline_db):
    """Sync all files in a project to offline storage."""
    # Get project
    result = await db.execute(select(LDMProject).where(LDMProject.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

    # Save project
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

    # Get all files in project
    files_result = await db.execute(
        select(LDMFile).where(LDMFile.project_id == project_id)
    )
    files = files_result.scalars().all()

    for file in files:
        await _sync_file_to_offline(db, file.id, offline_db)

    logger.info(f"Synced project {project.name} with {len(files)} files")


async def _sync_platform_to_offline(db: AsyncSession, platform_id: int, offline_db):
    """Sync all projects in a platform to offline storage."""
    from server.database.models import LDMPlatform

    # Get platform
    result = await db.execute(select(LDMPlatform).where(LDMPlatform.id == platform_id))
    platform = result.scalar_one_or_none()
    if not platform:
        raise HTTPException(status_code=404, detail=f"Platform {platform_id} not found")

    # Save platform
    offline_db.save_platform({
        "id": platform.id,
        "name": platform.name,
        "description": platform.description,
        "owner_id": platform.owner_id,
        "is_restricted": platform.is_restricted,
        "created_at": platform.created_at.isoformat() if platform.created_at else None,
        "updated_at": platform.updated_at.isoformat() if platform.updated_at else None
    })

    # Get all projects in platform
    projects_result = await db.execute(
        select(LDMProject).where(LDMProject.platform_id == platform_id)
    )
    projects = projects_result.scalars().all()

    for project in projects:
        await _sync_project_to_offline(db, project.id, offline_db)

    logger.info(f"Synced platform {platform.name} with {len(projects)} projects")


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
    Download/sync a file from PostgreSQL to local SQLite for offline use.

    Uses merge logic (last-write-wins):
    - Server rows are merged with local (doesn't overwrite local changes)
    - Local changes are pushed to server if newer
    - Deleted rows on server are removed locally
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
        raise HTTPException(status_code=404, detail="Resource not found")

    # Get file from PostgreSQL
    result = await db.execute(select(LDMFile).where(LDMFile.id == file_id))
    file = result.scalar_one_or_none()

    if not file:
        raise HTTPException(status_code=404, detail="File not found")

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

        # Use merge-aware sync
        await _sync_file_to_offline(db, file_id, offline_db)

        # Update sync metadata
        offline_db.set_last_sync()

        logger.success(f"Downloaded for offline: file={file.name}")

        return DownloadForOfflineResponse(
            success=True,
            file_id=file.id,
            file_name=file.name,
            row_count=file.row_count,
            message=f"Synced {file.name} for offline use (merge applied)"
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
        raise HTTPException(status_code=404, detail="Destination project not found")

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
