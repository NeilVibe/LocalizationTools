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
from pydantic import BaseModel, Field
from typing import Optional, List

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
    entity_type: str  # platform, project, folder, file
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
            # Download single file (includes path hierarchy)
            await _sync_file_to_offline(db, request.entity_id, offline_db)
        elif request.entity_type == "folder":
            # Download folder and all files in it (includes path hierarchy)
            await _sync_folder_to_offline(db, request.entity_id, offline_db)
        elif request.entity_type == "project":
            # Download all folders and files in project (includes platform)
            await _sync_project_to_offline(db, request.entity_id, offline_db)
        elif request.entity_type == "platform":
            # Download all projects, folders, and files in platform
            await _sync_platform_to_offline(db, request.entity_id, offline_db)
        elif request.entity_type == "tm":
            # SYNC-008: Download TM and all entries (with last-write-wins merge)
            await _sync_tm_to_offline(db, request.entity_id, offline_db)

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


# =============================================================================
# Push Local Changes to Server (P3 Phase 3)
# =============================================================================

class PushChangesRequest(BaseModel):
    file_id: int


class PushChangesPreview(BaseModel):
    file_id: int
    file_name: str
    modified_rows: int
    new_rows: int
    total_changes: int


class PushChangesResponse(BaseModel):
    success: bool
    file_id: int
    rows_pushed: int
    message: str


@router.get("/offline/push-preview/{file_id}", response_model=PushChangesPreview)
async def get_push_preview(
    file_id: int,
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Preview what changes will be pushed for a file.

    Returns count of modified and new rows that will be synced.
    Call this before push-changes to show user what will happen.
    """
    try:
        offline_db = get_offline_db()

        # Get file info
        file_info = offline_db.get_file(file_id)
        if not file_info:
            raise HTTPException(status_code=404, detail="File not found in offline storage")

        # Count changes
        modified_rows = offline_db.get_modified_rows(file_id)
        new_rows = offline_db.get_new_rows(file_id)

        return PushChangesPreview(
            file_id=file_id,
            file_name=file_info.get("name", "Unknown"),
            modified_rows=len(modified_rows),
            new_rows=len(new_rows),
            total_changes=len(modified_rows) + len(new_rows)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Push preview failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/offline/push-changes", response_model=PushChangesResponse)
async def push_changes_to_server(
    request: PushChangesRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Push local changes for a file to the server (P3 Phase 3).

    This endpoint:
    1. Gets modified rows from local SQLite
    2. Pushes them to PostgreSQL
    3. Marks local rows as synced

    Use this when user clicks "Sync to Server" on a file with pending changes.
    """
    from server.config import ACTIVE_DATABASE_TYPE

    logger.info(f"Push changes to server: file_id={request.file_id}")

    # Verify we're online
    if ACTIVE_DATABASE_TYPE != "postgresql":
        raise HTTPException(
            status_code=400,
            detail="Cannot push to server while in offline mode. Connect to server first."
        )

    try:
        offline_db = get_offline_db()

        # Get file info
        file_info = offline_db.get_file(request.file_id)
        if not file_info:
            raise HTTPException(status_code=404, detail="File not found in offline storage")

        # Push changes
        pushed_count = await _push_local_changes_for_file(db, request.file_id, offline_db)

        # Update last sync time
        offline_db.set_last_sync()

        logger.success(f"Pushed {pushed_count} changes for file {request.file_id}")

        return PushChangesResponse(
            success=True,
            file_id=request.file_id,
            rows_pushed=pushed_count,
            message=f"Successfully pushed {pushed_count} changes to server"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Push changes failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


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
        elif request.entity_type == "tm":
            # SYNC-008: Sync TM with entries
            entries_result = await db.execute(
                select(LDMTMEntry).where(LDMTMEntry.tm_id == request.entity_id)
            )
            entries = entries_result.scalars().all()
            updated_count = len(entries)
            await _sync_tm_to_offline(db, request.entity_id, offline_db)

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

def _platform_to_dict(platform) -> dict:
    """Convert a platform ORM object to a dict for offline storage."""
    return {
        "id": platform.id,
        "name": platform.name,
        "description": platform.description,
        "owner_id": platform.owner_id,
        "is_restricted": platform.is_restricted,
        "created_at": platform.created_at.isoformat() if platform.created_at else None,
        "updated_at": platform.updated_at.isoformat() if platform.updated_at else None
    }


def _project_to_dict(project) -> dict:
    """Convert a project ORM object to a dict for offline storage."""
    return {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "platform_id": project.platform_id,
        "owner_id": project.owner_id,
        "is_restricted": project.is_restricted,
        "created_at": project.created_at.isoformat() if project.created_at else None,
        "updated_at": project.updated_at.isoformat() if project.updated_at else None
    }


def _folder_to_dict(folder) -> dict:
    """Convert a folder ORM object to a dict for offline storage."""
    return {
        "id": folder.id,
        "name": folder.name,
        "project_id": folder.project_id,
        "parent_id": folder.parent_id,
        "created_at": folder.created_at.isoformat() if folder.created_at else None
    }


async def _sync_folder_hierarchy(db: AsyncSession, folder, offline_db):
    """
    Sync a folder and its parent folders recursively.
    Ensures the full path exists in offline storage.
    """
    from server.database.models import LDMFolder

    # If folder has a parent, sync parent first (recursive)
    if folder.parent_id:
        parent_result = await db.execute(select(LDMFolder).where(LDMFolder.id == folder.parent_id))
        parent = parent_result.scalar_one_or_none()
        if parent:
            await _sync_folder_hierarchy(db, parent, offline_db)

    # Now save this folder
    offline_db.save_folder(_folder_to_dict(folder))
    logger.debug(f"Synced folder: {folder.name}")


async def _sync_folder_to_offline(db: AsyncSession, folder_id: int, offline_db):
    """
    Sync a folder and all its files to offline storage.
    Also syncs parent hierarchy (platform/project/parent folders).
    """
    from server.database.models import LDMPlatform, LDMFolder

    # Get folder
    result = await db.execute(select(LDMFolder).where(LDMFolder.id == folder_id))
    folder = result.scalar_one_or_none()
    if not folder:
        raise HTTPException(status_code=404, detail=f"Folder {folder_id} not found")

    # Get and sync project
    project_result = await db.execute(select(LDMProject).where(LDMProject.id == folder.project_id))
    project = project_result.scalar_one_or_none()
    if project:
        # Get and sync platform
        platform_result = await db.execute(select(LDMPlatform).where(LDMPlatform.id == project.platform_id))
        platform = platform_result.scalar_one_or_none()
        if platform:
            offline_db.save_platform(_platform_to_dict(platform))

        # Save project
        offline_db.save_project(_project_to_dict(project))

    # Sync folder hierarchy (including this folder and parents)
    await _sync_folder_hierarchy(db, folder, offline_db)

    # Sync all files in this folder
    files_result = await db.execute(
        select(LDMFile).where(LDMFile.folder_id == folder_id)
    )
    files = files_result.scalars().all()

    for file in files:
        await _sync_file_to_offline(db, file.id, offline_db)

    # Sync subfolders recursively
    subfolders_result = await db.execute(
        select(LDMFolder).where(LDMFolder.parent_id == folder_id)
    )
    subfolders = subfolders_result.scalars().all()

    for subfolder in subfolders:
        await _sync_folder_to_offline(db, subfolder.id, offline_db)

    logger.info(f"Synced folder {folder.name} with {len(files)} files and {len(subfolders)} subfolders")


async def _sync_file_to_offline(db: AsyncSession, file_id: int, offline_db):
    """
    Sync a single file to offline storage with merge logic.

    IMPORTANT: Server is source of truth for PATH (platform/project/folder).
    This function syncs the full path hierarchy before syncing file content.

    Merge Rules (last-write-wins):
    - Local synced + server newer → take server
    - Local modified + server newer → server wins, discard local
    - Local modified + local newer → keep local, push later
    - Server has row we don't → insert
    - We have row server deleted → delete local
    """
    from server.database.models import LDMPlatform, LDMFolder

    result = await db.execute(select(LDMFile).where(LDMFile.id == file_id))
    file = result.scalar_one_or_none()
    if not file:
        raise HTTPException(status_code=404, detail=f"File {file_id} not found")

    # =========================================================================
    # SYNC PATH HIERARCHY FIRST (Server = Source of Truth for structure)
    # Order: Platform → Project → Folder → File
    # =========================================================================

    # 1. Get and sync Project (required)
    project_result = await db.execute(select(LDMProject).where(LDMProject.id == file.project_id))
    project = project_result.scalar_one_or_none()
    if project:
        # 2. Get and sync Platform (required for project)
        platform_result = await db.execute(select(LDMPlatform).where(LDMPlatform.id == project.platform_id))
        platform = platform_result.scalar_one_or_none()
        if platform:
            offline_db.save_platform(_platform_to_dict(platform))
            logger.debug(f"Synced platform: {platform.name}")

        # Save project
        offline_db.save_project(_project_to_dict(project))
        logger.debug(f"Synced project: {project.name}")

    # 3. Get and sync Folder (optional - file may be at project root)
    if file.folder_id:
        folder_result = await db.execute(select(LDMFolder).where(LDMFolder.id == file.folder_id))
        folder = folder_result.scalar_one_or_none()
        if folder:
            # Sync parent folders recursively if nested
            await _sync_folder_hierarchy(db, folder, offline_db)

    # =========================================================================
    # SYNC FILE CONTENT
    # =========================================================================

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
    """
    Sync all folders and files in a project to offline storage.
    Also syncs the parent platform.
    """
    from server.database.models import LDMPlatform, LDMFolder

    # Get project
    result = await db.execute(select(LDMProject).where(LDMProject.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

    # Sync platform first
    platform_result = await db.execute(select(LDMPlatform).where(LDMPlatform.id == project.platform_id))
    platform = platform_result.scalar_one_or_none()
    if platform:
        offline_db.save_platform(_platform_to_dict(platform))

    # Save project
    offline_db.save_project(_project_to_dict(project))

    # Sync all root folders in project (which recursively sync subfolders and files)
    folders_result = await db.execute(
        select(LDMFolder).where(LDMFolder.project_id == project_id, LDMFolder.parent_id == None)
    )
    root_folders = folders_result.scalars().all()

    for folder in root_folders:
        await _sync_folder_to_offline(db, folder.id, offline_db)

    # Sync files at project root (no folder)
    files_result = await db.execute(
        select(LDMFile).where(LDMFile.project_id == project_id, LDMFile.folder_id == None)
    )
    root_files = files_result.scalars().all()

    for file in root_files:
        await _sync_file_to_offline(db, file.id, offline_db)

    # Count total files synced
    all_files_result = await db.execute(
        select(LDMFile).where(LDMFile.project_id == project_id)
    )
    all_files = all_files_result.scalars().all()

    logger.info(f"Synced project {project.name} with {len(root_folders)} folders and {len(all_files)} files")


async def _sync_platform_to_offline(db: AsyncSession, platform_id: int, offline_db):
    """Sync all projects in a platform to offline storage."""
    from server.database.models import LDMPlatform

    # Get platform
    result = await db.execute(select(LDMPlatform).where(LDMPlatform.id == platform_id))
    platform = result.scalar_one_or_none()
    if not platform:
        raise HTTPException(status_code=404, detail=f"Platform {platform_id} not found")

    # Save platform
    offline_db.save_platform(_platform_to_dict(platform))

    # Get all projects in platform
    projects_result = await db.execute(
        select(LDMProject).where(LDMProject.platform_id == platform_id)
    )
    projects = projects_result.scalars().all()

    for project in projects:
        await _sync_project_to_offline(db, project.id, offline_db)

    logger.info(f"Synced platform {platform.name} with {len(projects)} projects")


async def _sync_tm_to_offline(db: AsyncSession, tm_id: int, offline_db):
    """
    Sync a Translation Memory to offline storage with merge logic.

    SYNC-008: TM offline sync support with last-write-wins merge.

    Merge Rules (same as file rows):
    - Local synced + server newer → take server
    - Local modified + server newer → server wins
    - Local modified + local newer → keep local
    - Server has entry we don't → insert
    - We have entry server deleted → delete local
    """
    # Get TM from PostgreSQL
    result = await db.execute(
        select(LDMTranslationMemory).where(LDMTranslationMemory.id == tm_id)
    )
    tm = result.scalar_one_or_none()
    if not tm:
        raise HTTPException(status_code=404, detail=f"Translation Memory {tm_id} not found")

    # Get all entries for this TM
    entries_result = await db.execute(
        select(LDMTMEntry).where(LDMTMEntry.tm_id == tm_id)
    )
    server_entries = entries_result.scalars().all()

    # Save TM metadata to offline storage
    local_tm_id = offline_db.save_tm({
        "id": tm.id,
        "name": tm.name,
        "description": tm.description,
        "source_lang": tm.source_lang,
        "target_lang": tm.target_lang,
        "entry_count": tm.entry_count,
        "status": tm.status,
        "mode": tm.mode if hasattr(tm, 'mode') else 'standard',
        "owner_id": tm.owner_id,
        "created_at": tm.created_at.isoformat() if tm.created_at else None,
        "updated_at": tm.updated_at.isoformat() if tm.updated_at else None,
        "indexed_at": tm.indexed_at.isoformat() if tm.indexed_at else None
    })

    # Track merge stats
    stats = {"inserted": 0, "updated": 0, "skipped": 0, "deleted": 0}
    server_entry_ids = set()

    # Merge each server entry using last-write-wins
    for entry in server_entries:
        server_entry_ids.add(entry.id)
        entry_data = {
            "id": entry.id,
            "source_text": entry.source_text,
            "target_text": entry.target_text,
            "source_hash": entry.source_hash,
            "string_id": entry.string_id if hasattr(entry, 'string_id') else None,
            "created_by": entry.created_by,
            "change_date": entry.change_date.isoformat() if entry.change_date else None,
            "updated_at": entry.updated_at.isoformat() if entry.updated_at else None,
            "updated_by": entry.updated_by if hasattr(entry, 'updated_by') else None,
            "is_confirmed": entry.is_confirmed if hasattr(entry, 'is_confirmed') else False,
            "confirmed_by": entry.confirmed_by if hasattr(entry, 'confirmed_by') else None,
            "confirmed_at": entry.confirmed_at.isoformat() if hasattr(entry, 'confirmed_at') and entry.confirmed_at else None
        }
        result = offline_db.merge_tm_entry(entry_data, local_tm_id)
        stats[result] += 1

    # Delete local entries that no longer exist on server
    local_entry_ids = offline_db.get_local_tm_entry_server_ids(local_tm_id)
    deleted_ids = local_entry_ids - server_entry_ids
    for deleted_id in deleted_ids:
        offline_db.delete_tm_entry(deleted_id)
        stats["deleted"] += 1

    # Push local TM entry changes to server
    pushed = await _push_tm_changes_to_server(db, local_tm_id, tm_id, offline_db)

    logger.info(f"Synced TM {tm.name}: inserted={stats['inserted']}, updated={stats['updated']}, "
                f"skipped={stats['skipped']}, deleted={stats['deleted']}, pushed={pushed}")


async def _push_tm_changes_to_server(db: AsyncSession, local_tm_id: int, server_tm_id: int, offline_db) -> int:
    """
    Push local TM entry changes to the server.

    Returns: number of entries pushed
    """
    pushed_count = 0

    # Get modified entries
    modified_entries = offline_db.get_modified_tm_entries(local_tm_id)
    for local_entry in modified_entries:
        server_id = local_entry.get("server_id")
        if server_id:
            # Update existing entry on server
            await db.execute(
                LDMTMEntry.__table__.update()
                .where(LDMTMEntry.id == server_id)
                .values(
                    target_text=local_entry.get("target_text"),
                    is_confirmed=local_entry.get("is_confirmed", False),
                    confirmed_by=local_entry.get("confirmed_by"),
                )
            )
            offline_db.mark_tm_entry_synced(local_entry["id"])
            pushed_count += 1

    # Get new entries (created offline)
    new_entries = offline_db.get_new_tm_entries(local_tm_id)
    for local_entry in new_entries:
        # Create new entry on server
        import hashlib
        source_hash = hashlib.sha256(local_entry.get("source_text", "").encode()).hexdigest()
        new_entry = LDMTMEntry(
            tm_id=server_tm_id,
            source_text=local_entry.get("source_text"),
            target_text=local_entry.get("target_text"),
            source_hash=source_hash,
            created_by=local_entry.get("created_by"),
        )
        db.add(new_entry)
        await db.flush()

        offline_db.mark_tm_entry_synced(local_entry["id"])
        pushed_count += 1

    if pushed_count > 0:
        await db.commit()

    return pushed_count


# =============================================================================
# Orphaned Files (P3-PHASE5: Offline Storage Fallback)
# =============================================================================

class OrphanedFileInfo(BaseModel):
    id: int
    name: str
    format: str
    row_count: int
    error_message: Optional[str]
    updated_at: Optional[str]


class LocalFolderInfo(BaseModel):
    id: int
    name: str
    parent_id: Optional[int]
    created_at: Optional[str]


class OrphanedFilesResponse(BaseModel):
    files: list[OrphanedFileInfo]
    folders: list[LocalFolderInfo] = []  # P9: Added folders support
    total_count: int


@router.get("/offline/local-files", response_model=OrphanedFilesResponse)
async def list_local_files(
    parent_id: Optional[int] = None,
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    List local files and folders in Offline Storage.

    P9: Now supports folders! Pass parent_id to get contents of a subfolder.

    These items are displayed in the "Offline Storage" virtual folder.
    User can move them to proper locations via Ctrl+X/V when online.
    """
    try:
        offline_db = get_offline_db()

        # Get local folders (at root or in specified parent)
        local_folders = offline_db.get_local_folders(parent_id)
        folders = [
            LocalFolderInfo(
                id=f["id"],
                name=f["name"],
                parent_id=f.get("parent_id"),
                created_at=f.get("created_at")
            )
            for f in local_folders
        ]

        # Get local files (at root or in specified parent)
        if parent_id is None:
            # Root level: get files with no folder
            local_files = [f for f in offline_db.get_local_files() if f.get("folder_id") is None]
        else:
            # Inside a folder: get files in that folder
            local_files = [f for f in offline_db.get_local_files() if f.get("folder_id") == parent_id]

        files = [
            OrphanedFileInfo(
                id=f["id"],
                name=f["name"],
                format=f.get("format", "txt"),
                row_count=f.get("row_count", 0),
                error_message=f.get("error_message"),
                updated_at=f.get("updated_at")
            )
            for f in local_files
        ]

        return OrphanedFilesResponse(
            files=files,
            folders=folders,
            total_count=len(files) + len(folders)
        )
    except Exception as e:
        logger.error(f"Failed to list local files: {e}")
        return OrphanedFilesResponse(files=[], folders=[], total_count=0)


@router.get("/offline/local-file-count")
async def get_local_file_count(
    current_user: dict = Depends(get_current_active_user_async)
):
    """Get count of local files in Offline Storage (for UI indicator)."""
    try:
        offline_db = get_offline_db()
        count = offline_db.get_local_file_count()
        return {"count": count}
    except Exception as e:
        logger.error(f"Failed to get local file count: {e}")
        return {"count": 0}


# =============================================================================
# P9: Offline Storage Operations
# Note: File CREATION uses unified /api/ldm/files/upload?storage=local
# These endpoints handle DELETE, RENAME, and ADD ROWS for offline files
# =============================================================================

class DeleteOfflineFileResponse(BaseModel):
    success: bool
    message: str


class RenameOfflineFileRequest(BaseModel):
    new_name: str = Field(..., min_length=1, description="New filename (cannot be empty)")


class RenameOfflineFileResponse(BaseModel):
    success: bool
    message: str


# NOTE: File CREATION endpoint was removed - use unified /api/ldm/files/upload?storage=local
# This ensures proper parsing via backend file handlers (txt_handler, xml_handler, excel_handler)


@router.delete("/offline/storage/files/{file_id}", response_model=DeleteOfflineFileResponse)
async def delete_offline_storage_file(
    file_id: int,
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    P9: Delete a file from Offline Storage.

    Only works for local files (files in Offline Storage).
    Downloaded files from the server cannot be deleted this way.
    """
    logger.info(f"Deleting file from Offline Storage: {file_id}")

    try:
        offline_db = get_offline_db()
        success = offline_db.delete_local_file(file_id)

        if success:
            return DeleteOfflineFileResponse(
                success=True,
                message="File deleted from Offline Storage"
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete: file not found or not in Offline Storage"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete file from Offline Storage: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")


@router.put("/offline/storage/files/{file_id}/rename", response_model=RenameOfflineFileResponse)
async def rename_offline_storage_file(
    file_id: int,
    request: RenameOfflineFileRequest,
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    P9: Rename a file in Offline Storage.

    Only works for local files (files in Offline Storage).
    Downloaded files from the server cannot be renamed this way.
    """
    logger.info(f"Renaming file in Offline Storage: {file_id} -> {request.new_name}")

    try:
        offline_db = get_offline_db()
        success = offline_db.rename_local_file(file_id, request.new_name)

        if success:
            return RenameOfflineFileResponse(
                success=True,
                message=f"File renamed to '{request.new_name}'"
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="Cannot rename: file not found or not in Offline Storage"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to rename file in Offline Storage: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to rename file: {str(e)}")


@router.post("/offline/storage/files/{file_id}/rows")
async def add_rows_to_offline_file(
    file_id: int,
    rows: list,
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    P9: Add rows to a file in Offline Storage.

    Only works for local files (files in Offline Storage).
    """
    logger.info(f"Adding {len(rows)} rows to offline file {file_id}")

    try:
        offline_db = get_offline_db()

        # Verify file exists and is local (in Offline Storage)
        file_info = offline_db.get_file(file_id)
        if not file_info:
            raise HTTPException(status_code=404, detail="File not found")
        if file_info.get("sync_status") != "local":
            raise HTTPException(
                status_code=400,
                detail="Cannot add rows: file is not in Offline Storage"
            )

        offline_db.add_rows_to_local_file(file_id, rows)

        return {
            "success": True,
            "rows_added": len(rows),
            "message": f"Added {len(rows)} rows to file"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add rows to offline file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to add rows: {str(e)}")


# =============================================================================
# Offline Storage Folder Operations (P9)
# =============================================================================

class CreateOfflineFolderRequest(BaseModel):
    name: str = Field(..., min_length=1, description="Folder name (cannot be empty)")
    parent_id: Optional[int] = Field(None, description="Parent folder ID (null for root)")


class CreateOfflineFolderResponse(BaseModel):
    success: bool
    id: int
    name: str
    message: str


class DeleteOfflineFolderResponse(BaseModel):
    success: bool
    message: str


class RenameOfflineFolderRequest(BaseModel):
    new_name: str = Field(..., min_length=1, description="New folder name (cannot be empty)")


class RenameOfflineFolderResponse(BaseModel):
    success: bool
    message: str


@router.post("/offline/storage/folders", response_model=CreateOfflineFolderResponse)
async def create_offline_storage_folder(
    request: CreateOfflineFolderRequest,
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    P9: Create a folder in Offline Storage.

    Creates a local folder that exists only in SQLite Offline Storage.
    These folders can later be moved to a real project when going online.
    """
    logger.info(f"Creating folder in Offline Storage: name='{request.name}', parent={request.parent_id}")

    try:
        offline_db = get_offline_db()
        folder_id, final_name = offline_db.create_local_folder(request.name, request.parent_id)

        return CreateOfflineFolderResponse(
            success=True,
            id=folder_id,
            name=final_name,
            message=f"Folder '{final_name}' created in Offline Storage"
        )

    except Exception as e:
        logger.error(f"Failed to create folder in Offline Storage: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create folder: {str(e)}")


@router.delete("/offline/storage/folders/{folder_id}", response_model=DeleteOfflineFolderResponse)
async def delete_offline_storage_folder(
    folder_id: int,
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    P9: Delete a folder from Offline Storage.

    Only works for local folders (folders in Offline Storage).
    Also deletes all files and subfolders inside.
    """
    logger.info(f"Deleting folder from Offline Storage: {folder_id}")

    try:
        offline_db = get_offline_db()
        success = offline_db.delete_local_folder(folder_id)

        if success:
            return DeleteOfflineFolderResponse(
                success=True,
                message="Folder deleted from Offline Storage"
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete: folder not found or not in Offline Storage"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete folder from Offline Storage: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete folder: {str(e)}")


@router.put("/offline/storage/folders/{folder_id}/rename", response_model=RenameOfflineFolderResponse)
async def rename_offline_storage_folder(
    folder_id: int,
    request: RenameOfflineFolderRequest,
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    P9: Rename a folder in Offline Storage.

    Only works for local folders (folders in Offline Storage).
    """
    logger.info(f"Renaming folder in Offline Storage: {folder_id} -> {request.new_name}")

    try:
        offline_db = get_offline_db()
        success = offline_db.rename_local_folder(folder_id, request.new_name)

        if success:
            return RenameOfflineFolderResponse(
                success=True,
                message=f"Folder renamed to '{request.new_name}'"
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="Cannot rename: folder not found or not in Offline Storage"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to rename folder in Offline Storage: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to rename folder: {str(e)}")


# =============================================================================
# P9: Move Operations for Offline Storage
# =============================================================================

class MoveOfflineFileRequest(BaseModel):
    target_folder_id: Optional[int] = Field(None, description="Target folder ID (null for root)")


class MoveOfflineFileResponse(BaseModel):
    success: bool
    message: str


class MoveOfflineFolderRequest(BaseModel):
    target_parent_id: Optional[int] = Field(None, description="Target parent folder ID (null for root)")


class MoveOfflineFolderResponse(BaseModel):
    success: bool
    message: str


@router.patch("/offline/storage/files/{file_id}/move", response_model=MoveOfflineFileResponse)
async def move_offline_storage_file(
    file_id: int,
    target_folder_id: Optional[int] = None,
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    P9: Move a file within Offline Storage.

    Only works for local files (files in Offline Storage).
    target_folder_id can be:
    - null/omitted: Move to root of Offline Storage
    - int: Move into the specified local folder
    """
    target_desc = f"folder {target_folder_id}" if target_folder_id else "root"
    logger.info(f"Moving file in Offline Storage: {file_id} -> {target_desc}")

    try:
        offline_db = get_offline_db()
        success = offline_db.move_local_file(file_id, target_folder_id)

        if success:
            return MoveOfflineFileResponse(
                success=True,
                message=f"File moved to {target_desc}"
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="Cannot move: file not found, not in Offline Storage, or target folder invalid"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to move file in Offline Storage: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to move file: {str(e)}")


@router.patch("/offline/storage/folders/{folder_id}/move", response_model=MoveOfflineFolderResponse)
async def move_offline_storage_folder(
    folder_id: int,
    target_parent_id: Optional[int] = None,
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    P9: Move a folder within Offline Storage.

    Only works for local folders (folders in Offline Storage).
    target_parent_id can be:
    - null/omitted: Move to root of Offline Storage
    - int: Move into the specified local folder

    Cannot move a folder into itself or its descendants.
    """
    target_desc = f"folder {target_parent_id}" if target_parent_id else "root"
    logger.info(f"Moving folder in Offline Storage: {folder_id} -> {target_desc}")

    try:
        offline_db = get_offline_db()
        success = offline_db.move_local_folder(folder_id, target_parent_id)

        if success:
            return MoveOfflineFolderResponse(
                success=True,
                message=f"Folder moved to {target_desc}"
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="Cannot move: folder not found, not in Offline Storage, or target invalid (cannot move into self/descendants)"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to move folder in Offline Storage: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to move folder: {str(e)}")


# =============================================================================
# P9-BIN-001: Local Trash (Recycle Bin for Offline Storage)
# =============================================================================

class LocalTrashItem(BaseModel):
    id: int
    item_type: str  # 'local-file' or 'local-folder'
    item_id: int
    item_name: str
    parent_folder_id: Optional[int]
    deleted_at: str
    expires_at: str
    status: str


class ListLocalTrashResponse(BaseModel):
    items: List[LocalTrashItem]
    count: int


class RestoreLocalTrashResponse(BaseModel):
    success: bool
    message: str
    item_type: Optional[str] = None
    item_id: Optional[int] = None


class EmptyLocalTrashResponse(BaseModel):
    success: bool
    deleted_count: int


@router.get("/offline/trash", response_model=ListLocalTrashResponse)
async def list_local_trash(
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    P9-BIN-001: List items in local Recycle Bin (Offline Storage trash).

    Returns all trashed local files and folders with their metadata.
    """
    try:
        offline_db = get_offline_db()
        items = offline_db.list_local_trash()

        return ListLocalTrashResponse(
            items=[LocalTrashItem(**item) for item in items],
            count=len(items)
        )

    except Exception as e:
        logger.error(f"Failed to list local trash: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list local trash: {str(e)}")


@router.post("/offline/trash/{trash_id}/restore", response_model=RestoreLocalTrashResponse)
async def restore_from_local_trash(
    trash_id: int,
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    P9-BIN-001: Restore an item from local Recycle Bin.

    Restores the file/folder and all its contents back to Offline Storage.
    """
    logger.info(f"Restoring from local trash: trash_id={trash_id}")

    try:
        offline_db = get_offline_db()
        result = offline_db.restore_from_local_trash(trash_id)

        if result:
            return RestoreLocalTrashResponse(
                success=True,
                message="Item restored successfully",
                item_type=result.get("item_type"),
                item_id=result.get("item_id")
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="Cannot restore: item not found or already restored"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to restore from local trash: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to restore: {str(e)}")


@router.delete("/offline/trash/{trash_id}")
async def permanent_delete_from_local_trash(
    trash_id: int,
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    P9-BIN-001: Permanently delete an item from local Recycle Bin.

    This action cannot be undone.
    """
    logger.info(f"Permanently deleting from local trash: trash_id={trash_id}")

    try:
        offline_db = get_offline_db()
        success = offline_db.permanent_delete_from_local_trash(trash_id)

        if success:
            return {"success": True, "message": "Item permanently deleted"}
        else:
            raise HTTPException(
                status_code=404,
                detail="Trash item not found"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to permanently delete from local trash: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete: {str(e)}")


@router.delete("/offline/trash", response_model=EmptyLocalTrashResponse)
async def empty_local_trash(
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    P9-BIN-001: Empty the entire local Recycle Bin.

    Permanently deletes all trashed local files and folders.
    This action cannot be undone.
    """
    logger.info("Emptying local trash")

    try:
        offline_db = get_offline_db()
        count = offline_db.empty_local_trash()

        return EmptyLocalTrashResponse(
            success=True,
            deleted_count=count
        )

    except Exception as e:
        logger.error(f"Failed to empty local trash: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to empty trash: {str(e)}")


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
            offline_db.save_project(_project_to_dict(project))

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
    Sync a file from Offline Storage (SQLite) to central PostgreSQL.

    This endpoint:
    1. Reads file metadata + all rows from Offline Storage (SQLite)
    2. Creates new file record in PostgreSQL (destination project/folder)
    3. Bulk inserts all rows to PostgreSQL
    4. Returns the new file_id in central DB

    Use this when:
    - User imported a file to Offline Storage
    - User wants to upload local work to a server project
    """
    from server.config import ACTIVE_DATABASE_TYPE
    from server.database.offline import get_offline_db

    logger.info(f"Sync to central: file_id={request.file_id}, dest_project={request.destination_project_id}, dest_folder={request.destination_folder_id}")

    # Verify we're online (connected to PostgreSQL)
    if ACTIVE_DATABASE_TYPE != "postgresql":
        raise HTTPException(
            status_code=400,
            detail="Cannot sync to central server while in offline mode. Connect to server first."
        )

    # Verify destination project access (DESIGN-001: Public by default)
    if not await can_access_project(db, request.destination_project_id, current_user):
        raise HTTPException(status_code=404, detail="Destination project not found")

    # Verify destination folder if specified
    if request.destination_folder_id:
        folder_result = await db.execute(
            select(LDMFolder).where(
                LDMFolder.id == request.destination_folder_id,
                LDMFolder.project_id == request.destination_project_id
            )
        )
        if not folder_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Destination folder not found")

    try:
        # Read from Offline Storage using offline.py
        offline_db = get_offline_db()
        local_file = offline_db.get_local_file(request.file_id)

        if not local_file:
            raise HTTPException(status_code=404, detail="File not found in Offline Storage")

        local_rows = offline_db.get_rows_for_file(request.file_id)
        logger.info(f"Read {len(local_rows)} rows from Offline Storage for file {request.file_id}")

        # Parse extra_data if it's a JSON string
        import json
        extra_data = local_file.get("extra_data")
        if extra_data and isinstance(extra_data, str):
            try:
                extra_data = json.loads(extra_data)
            except (json.JSONDecodeError, TypeError):
                extra_data = None

        # Create new file in PostgreSQL
        new_file = LDMFile(
            project_id=request.destination_project_id,
            folder_id=request.destination_folder_id,  # Can be None for project root
            name=local_file.get("name", "unknown"),
            original_filename=local_file.get("original_filename") or local_file.get("name"),
            format=local_file.get("format", "txt"),
            row_count=len(local_rows),
            source_language=local_file.get("source_language"),
            target_language=local_file.get("target_language"),
            extra_data=extra_data,
            created_by=current_user["user_id"]
        )
        db.add(new_file)
        await db.flush()

        # Create rows in PostgreSQL
        for local_row in local_rows:
            # Parse extra_data for rows too
            row_extra = local_row.get("extra_data")
            if row_extra and isinstance(row_extra, str):
                try:
                    row_extra = json.loads(row_extra)
                except (json.JSONDecodeError, TypeError):
                    row_extra = None

            new_row = LDMRow(
                file_id=new_file.id,
                row_num=local_row.get("row_num", 0),
                string_id=local_row.get("string_id"),
                source=local_row.get("source"),
                target=local_row.get("target"),
                status=local_row.get("status", "pending"),
                extra_data=row_extra
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
