"""
Sync endpoints - Online/Offline synchronization.

P10: FULL ABSTRACT + REPO Pattern
- Uses SyncService factory for all sync operations
- Permission checks via repositories (permissions baked in)
- No direct DB access in routes

Includes:
- sync-to-central: Push local SQLite changes to PostgreSQL
- download-for-offline: Pull file from PostgreSQL to local SQLite

Migrated from api.py lines 2786-3042

P10-REPO: Migrated to Repository Pattern (2026-01-13)
- Uses FileRepository, FolderRepository, TMRepository for entity lookups
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
from pydantic import BaseModel, Field
from typing import Optional, List

# P10: get_async_db only needed for SyncService factory
from server.utils.dependencies import get_async_db, get_current_active_user_async
from server.repositories import (
    FileRepository, get_file_repository,
    FolderRepository, get_folder_repository,
    TMRepository, get_tm_repository,
    ProjectRepository, get_project_repository
)
from server.tools.ldm.schemas import (
    SyncFileToCentralRequest, SyncFileToCentralResponse,
    SyncTMToCentralRequest, SyncTMToCentralResponse
)
from server.database.offline import get_offline_db
from server.services import SyncService


# =============================================================================
# P10: SyncService Factory (injects db internally)
# =============================================================================

def get_sync_service(
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
) -> SyncService:
    """
    Factory function for SyncService.

    P10: DB is injected here, not in routes. Routes only use SyncService.
    """
    offline_db = get_offline_db()
    return SyncService(db, offline_db)

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
        logger.error(f"[SYNC] Failed to get offline status: {e}")
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
        logger.error(f"[SYNC] Failed to list offline files: {e}")
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
    Automatically cleans up stale subscriptions for deleted files.
    """
    try:
        offline_db = get_offline_db()
        subs = offline_db.get_subscriptions()

        # Validate subscriptions - clean up stale ones for deleted files
        valid_subscriptions = []
        stale_subscription_ids = []

        for s in subs:
            is_valid = True

            if s["entity_type"] == "file":
                # Check if file exists (either in local SQLite or PostgreSQL)
                file_exists = offline_db.get_local_file(s["entity_id"]) is not None
                if not file_exists:
                    # File was deleted, mark subscription as stale
                    stale_subscription_ids.append((s["entity_type"], s["entity_id"]))
                    is_valid = False
                    logger.debug(f"Stale subscription found: file {s['entity_id']} no longer exists")

            if is_valid:
                valid_subscriptions.append(s)

        # Clean up stale subscriptions in the background
        for entity_type, entity_id in stale_subscription_ids:
            try:
                offline_db.remove_subscription(entity_type, entity_id)
                logger.info(f"Cleaned up stale subscription: {entity_type}={entity_id}")
            except Exception as cleanup_error:
                logger.warning(f"[SYNC] Failed to clean up stale subscription: {cleanup_error}")

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
            for s in valid_subscriptions
        ]

        return SubscriptionsResponse(
            subscriptions=subscriptions,
            total_count=len(subscriptions)
        )
    except Exception as e:
        logger.error(f"[SYNC] Failed to list subscriptions: {e}")
        return SubscriptionsResponse(subscriptions=[], total_count=0)


@router.post("/offline/subscribe", response_model=SubscribeResponse)
async def subscribe_for_offline(
    request: SubscribeRequest,
    current_user: dict = Depends(get_current_active_user_async),
    sync_service: SyncService = Depends(get_sync_service)
):
    """
    Enable offline sync for a platform, project, or file.

    P10: FULL ABSTRACT - Uses SyncService factory (db injected internally).
    This creates a subscription and triggers initial download.
    Subsequent syncs happen automatically.
    """
    from server.config import ACTIVE_DATABASE_TYPE

    logger.info(f"[SYNC] subscribe_for_offline: {request.entity_type}={request.entity_id}")

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

        # P10: Trigger initial sync using SyncService
        if request.entity_type == "file":
            await sync_service.sync_file_to_offline(request.entity_id)
        elif request.entity_type == "folder":
            await sync_service.sync_folder_to_offline(request.entity_id)
        elif request.entity_type == "project":
            await sync_service.sync_project_to_offline(request.entity_id)
        elif request.entity_type == "platform":
            await sync_service.sync_platform_to_offline(request.entity_id)
        elif request.entity_type == "tm":
            await sync_service.sync_tm_to_offline(request.entity_id)

        # Mark subscription as synced
        offline_db.update_subscription_status(
            request.entity_type, request.entity_id, "synced"
        )

        logger.info(f"[SYNC] subscribe_for_offline complete: {request.entity_type}={request.entity_id}")

        return SubscribeResponse(
            success=True,
            subscription_id=sub_id,
            message=f"Enabled offline sync for {request.entity_type}: {request.entity_name}"
        )

    except Exception as e:
        logger.error(f"[SYNC] [SYNC] Subscribe failed: {e}", exc_info=True)
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
        logger.error(f"[SYNC] Unsubscribe failed: {e}")
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
        logger.error(f"[SYNC] Push preview failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/offline/push-changes", response_model=PushChangesResponse)
async def push_changes_to_server(
    request: PushChangesRequest,
    current_user: dict = Depends(get_current_active_user_async),
    sync_service: SyncService = Depends(get_sync_service)
):
    """
    Push local changes for a file to the server (P3 Phase 3).

    P10: FULL ABSTRACT - Uses SyncService factory (db injected internally).
    This endpoint:
    1. Gets modified rows from local SQLite
    2. Pushes them to PostgreSQL
    3. Marks local rows as synced

    Use this when user clicks "Sync to Server" on a file with pending changes.
    """
    from server.config import ACTIVE_DATABASE_TYPE

    logger.info(f"[SYNC] push_changes_to_server: file_id={request.file_id}")

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

        # P10: Push changes using SyncService
        pushed_count = await sync_service.push_file_changes_to_server(request.file_id)

        # Update last sync time
        offline_db.set_last_sync()

        logger.success(f"[SYNC] [SYNC] Pushed {pushed_count} changes for file {request.file_id}")

        return PushChangesResponse(
            success=True,
            file_id=request.file_id,
            rows_pushed=pushed_count,
            message=f"Successfully pushed {pushed_count} changes to server"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[SYNC] [SYNC] Push changes failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/offline/sync-subscription", response_model=SyncSubscriptionResponse)
async def sync_subscription(
    request: SyncSubscriptionRequest,
    file_repo: FileRepository = Depends(get_file_repository),
    project_repo: ProjectRepository = Depends(get_project_repository),
    tm_repo: TMRepository = Depends(get_tm_repository),
    current_user: dict = Depends(get_current_active_user_async),
    sync_service: SyncService = Depends(get_sync_service)
):
    """
    Sync a single subscription (refresh from server).

    P10: FULL ABSTRACT - Uses SyncService factory (db injected internally).
    P10-REPO: Uses repositories for entity counts.

    This endpoint is called periodically by the continuous sync mechanism
    to keep offline data fresh with server changes.
    """
    from server.config import ACTIVE_DATABASE_TYPE

    logger.debug(f"[SYNC] sync_subscription: {request.entity_type}={request.entity_id}")

    if ACTIVE_DATABASE_TYPE != "postgresql":
        raise HTTPException(status_code=400, detail="Already in offline mode")

    try:
        offline_db = get_offline_db()

        # Check if subscription exists
        if not offline_db.is_subscribed(request.entity_type, request.entity_id):
            raise HTTPException(status_code=404, detail="Subscription not found")

        updated_count = 0

        # P10: Re-sync based on entity type using SyncService
        if request.entity_type == "file":
            await sync_service.sync_file_to_offline(request.entity_id)
            updated_count = 1
        elif request.entity_type == "project":
            # Count files in project via repository
            files = await file_repo.get_all(project_id=request.entity_id, limit=10000)
            updated_count = len(files) if files else 0
            await sync_service.sync_project_to_offline(request.entity_id)
        elif request.entity_type == "platform":
            # Count projects in platform via repository
            projects = await project_repo.get_all(platform_id=request.entity_id)
            updated_count = len(projects) if projects else 0
            await sync_service.sync_platform_to_offline(request.entity_id)
        elif request.entity_type == "tm":
            # SYNC-008: Sync TM with entries via repository
            updated_count = await tm_repo.count_entries(request.entity_id)
            await sync_service.sync_tm_to_offline(request.entity_id)

        # Update subscription status
        offline_db.update_subscription_status(
            request.entity_type, request.entity_id, "synced"
        )

        logger.debug(f"[SYNC] sync_subscription complete: {request.entity_type}={request.entity_id}")

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
        logger.error(f"[SYNC] [SYNC] Sync subscription failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


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
        logger.error(f"[SYNC] Failed to list local files: {e}")
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
        logger.error(f"[SYNC] Failed to get local file count: {e}")
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
        logger.error(f"[SYNC] Failed to delete file from Offline Storage: {e}", exc_info=True)
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
        logger.error(f"[SYNC] Failed to rename file in Offline Storage: {e}", exc_info=True)
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
        logger.error(f"[SYNC] Failed to add rows to offline file: {e}", exc_info=True)
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
        logger.error(f"[SYNC] Failed to create folder in Offline Storage: {e}", exc_info=True)
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
        logger.error(f"[SYNC] Failed to delete folder from Offline Storage: {e}", exc_info=True)
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
        logger.error(f"[SYNC] Failed to rename folder in Offline Storage: {e}", exc_info=True)
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
        logger.error(f"[SYNC] Failed to move file in Offline Storage: {e}", exc_info=True)
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
        logger.error(f"[SYNC] Failed to move folder in Offline Storage: {e}", exc_info=True)
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
        logger.error(f"[SYNC] Failed to list local trash: {e}", exc_info=True)
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
        logger.error(f"[SYNC] Failed to restore from local trash: {e}", exc_info=True)
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
        logger.error(f"[SYNC] Failed to permanently delete from local trash: {e}", exc_info=True)
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
    logger.info("[SYNC] Emptying local trash")

    try:
        offline_db = get_offline_db()
        count = offline_db.empty_local_trash()

        return EmptyLocalTrashResponse(
            success=True,
            deleted_count=count
        )

    except Exception as e:
        logger.error(f"[SYNC] Failed to empty local trash: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to empty trash: {str(e)}")


# =============================================================================
# Download for Offline
# =============================================================================

@router.post("/files/{file_id}/download-for-offline", response_model=DownloadForOfflineResponse)
async def download_file_for_offline(
    file_id: int,
    file_repo: FileRepository = Depends(get_file_repository),
    current_user: dict = Depends(get_current_active_user_async),
    sync_service: SyncService = Depends(get_sync_service)
):
    """
    Download/sync a file from PostgreSQL to local SQLite for offline use.

    P10: FULL ABSTRACT - Uses SyncService factory (db injected internally).
    P10-REPO: Uses FileRepository for file lookup (permissions baked in).

    Uses merge logic (last-write-wins):
    - Server rows are merged with local (doesn't overwrite local changes)
    - Local changes are pushed to server if newer
    - Deleted rows on server are removed locally
    """
    from server.config import ACTIVE_DATABASE_TYPE

    logger.info(f"[SYNC] download_file_for_offline: file_id={file_id}")

    # Verify we're online (connected to PostgreSQL)
    if ACTIVE_DATABASE_TYPE != "postgresql":
        raise HTTPException(
            status_code=400,
            detail="Already in offline mode. File should already be available locally."
        )

    # P10: Get file via repository (permissions checked inside - returns None if no access)
    file = await file_repo.get(file_id)
    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    try:
        # Get offline database instance
        offline_db = get_offline_db()

        # P10: Use SyncService for merge-aware sync (handles hierarchy)
        await sync_service.sync_file_to_offline(file_id)

        # Update sync metadata
        offline_db.set_last_sync()

        logger.success(f"[SYNC] [SYNC] Downloaded for offline: file={file.get('name')}")

        return DownloadForOfflineResponse(
            success=True,
            file_id=file.get("id"),
            file_name=file.get("name"),
            row_count=file.get("row_count", 0),
            message=f"Synced {file.get('name')} for offline use (merge applied)"
        )

    except Exception as e:
        logger.error(f"[SYNC] [SYNC] Download for offline failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to save for offline: {str(e)}")


@router.post("/sync-to-central", response_model=SyncFileToCentralResponse)
async def sync_file_to_central(
    request: SyncFileToCentralRequest,
    folder_repo: FolderRepository = Depends(get_folder_repository),
    project_repo: ProjectRepository = Depends(get_project_repository),
    current_user: dict = Depends(get_current_active_user_async),
    sync_service: SyncService = Depends(get_sync_service)
):
    """
    Sync a file from Offline Storage (SQLite) to central PostgreSQL.

    P10: FULL ABSTRACT - Uses SyncService factory (db injected internally).
    P10-REPO: Uses repositories for validation (permissions baked in).

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

    logger.info(f"[SYNC] sync_file_to_central: file_id={request.file_id}, "
                f"dest_project={request.destination_project_id}, dest_folder={request.destination_folder_id}")

    # Verify we're online (connected to PostgreSQL)
    if ACTIVE_DATABASE_TYPE != "postgresql":
        raise HTTPException(
            status_code=400,
            detail="Cannot sync to central server while in offline mode. Connect to server first."
        )

    # P10: Verify destination project access via repository (permissions baked in)
    dest_project = await project_repo.get(request.destination_project_id)
    if not dest_project:
        raise HTTPException(status_code=404, detail="Destination project not found")

    # P10: Verify destination folder if specified via repository (permissions baked in)
    if request.destination_folder_id:
        folder = await folder_repo.get(request.destination_folder_id)
        if not folder or folder.get("project_id") != request.destination_project_id:
            raise HTTPException(status_code=404, detail="Destination folder not found")

    try:
        # P10: Use SyncService for sync-to-central
        offline_db = get_offline_db()

        result = await sync_service.sync_file_to_central(
            local_file_id=request.file_id,
            destination_project_id=request.destination_project_id,
            destination_folder_id=request.destination_folder_id,
            user_id=current_user["user_id"]
        )

        logger.success(f"[SYNC] [SYNC] sync_file_to_central complete: file_id={request.file_id}")

        return SyncFileToCentralResponse(
            success=True,
            new_file_id=result["new_file_id"],
            rows_synced=result["rows_synced"],
            message=f"Successfully synced {result['rows_synced']} rows to central server"
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[SYNC] [SYNC] Sync to central failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Sync failed. Check server logs.")


@router.post("/tm/sync-to-central", response_model=SyncTMToCentralResponse)
async def sync_tm_to_central(
    request: SyncTMToCentralRequest,
    current_user: dict = Depends(get_current_active_user_async),
    sync_service: SyncService = Depends(get_sync_service)
):
    """
    Sync a Translation Memory from local SQLite to central PostgreSQL.

    P10: FULL ABSTRACT - Uses SyncService factory (db injected internally).
    This endpoint:
    1. Reads TM metadata + all entries from local SQLite
    2. Creates new TM record in PostgreSQL
    3. Bulk inserts all entries to PostgreSQL
    4. Returns the new tm_id in central DB
    """
    from server.config import ACTIVE_DATABASE_TYPE

    logger.info(f"[SYNC] sync_tm_to_central: tm_id={request.tm_id}")

    # Verify we're online (connected to PostgreSQL)
    if ACTIVE_DATABASE_TYPE != "postgresql":
        raise HTTPException(
            status_code=400,
            detail="Cannot sync to central server while in offline mode. Connect to server first."
        )

    try:
        # P10: Use SyncService for sync-to-central
        offline_db = get_offline_db()

        result = await sync_service.sync_tm_to_central(
            local_tm_id=request.tm_id,
            user_id=current_user["user_id"]
        )

        logger.success(f"[SYNC] [SYNC] sync_tm_to_central complete: tm_id={request.tm_id}")

        return SyncTMToCentralResponse(
            success=True,
            new_tm_id=result["new_tm_id"],
            entries_synced=result["entries_synced"],
            message=f"Successfully synced {result['entries_synced']} TM entries to central server. Run 'Build Indexes' on the server to enable semantic search."
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[SYNC] [SYNC] TM sync to central failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="TM sync failed. Check server logs.")
