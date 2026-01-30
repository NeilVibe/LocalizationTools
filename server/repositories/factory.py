"""
Repository Factory.

P10: FULL ABSTRACT + REPO + FACTORY Pattern

Provides dependency injection functions for FastAPI routes.
Automatically selects PostgreSQL or SQLite based on user's mode.

Architecture:
- Online mode → PostgreSQL repos (with user context for permissions)
- Offline mode → SQLite repos (no permissions, single user)

Routes ONLY use repositories. No direct DB access. Ever.
Permissions are baked INTO PostgreSQL repositories.
"""

from typing import Optional, Tuple
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from server.utils.dependencies import get_async_db, get_current_active_user_async
from server.repositories.interfaces.tm_repository import TMRepository
from server.repositories.interfaces.file_repository import FileRepository
from server.repositories.interfaces.row_repository import RowRepository
from server.repositories.interfaces.project_repository import ProjectRepository
from server.repositories.interfaces.folder_repository import FolderRepository
from server.repositories.interfaces.platform_repository import PlatformRepository
from server.repositories.interfaces.qa_repository import QAResultRepository
from server.repositories.interfaces.trash_repository import TrashRepository
from server.repositories.interfaces.capability_repository import CapabilityRepository


# =============================================================================
# Mode Detection
# =============================================================================

def _is_offline_mode(request: Request) -> bool:
    """
    Detect if request is in offline mode.

    Offline mode is indicated by Authorization header starting with "OFFLINE_MODE_".

    NOTE: This is NOT about whether the server uses SQLite vs PostgreSQL.
    The SQLite repos use a separate OFFLINE schema (offline_projects, etc.)
    which is different from the standard server schema (ldm_projects, etc.).

    Even when the server falls back to SQLite, it still uses PostgreSQL repos
    because they work with the standard schema that's created during server init.
    """
    auth_header = request.headers.get("Authorization", "")
    return auth_header.startswith("Bearer OFFLINE_MODE_")


async def get_current_user_optional(request: Request) -> Optional[dict]:
    """
    Get current user from request state if available, otherwise None.

    This is used by the repository factory to detect offline mode.
    Unlike get_current_active_user_async, this doesn't raise on missing auth.
    """
    # Check if user was set by auth middleware
    if hasattr(request.state, "user"):
        return request.state.user

    # Try to get from Authorization header for mode detection
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        # Just return token info for mode detection
        return {"token": token}

    return None


def get_tm_repository(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
) -> TMRepository:
    """
    Factory function - returns correct TM repository based on mode.

    P10: FULL ABSTRACT - Passes user context to PostgreSQL repos for permission checks.

    Used as FastAPI dependency:
        @router.get("/tms")
        async def get_tms(repo: TMRepository = Depends(get_tm_repository)):
            return await repo.get_all()  # Permissions checked inside!

    Logic:
    - Offline mode → SQLite repo (no permissions, single user)
    - Online mode → PostgreSQL repo (with user context for permissions)
    """
    # Import here to avoid circular imports
    from server.repositories.postgresql.tm_repo import PostgreSQLTMRepository
    from server.repositories.sqlite.tm_repo import SQLiteTMRepository

    if _is_offline_mode(request):
        return SQLiteTMRepository()
    else:
        return PostgreSQLTMRepository(db, current_user)


def is_offline_mode(current_user: Optional[dict]) -> bool:
    """Check if current user is in offline mode."""
    if not current_user:
        return False
    token = current_user.get("token", "")
    return isinstance(token, str) and token.startswith("OFFLINE_MODE_")


def get_file_repository(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
) -> FileRepository:
    """
    Factory function - returns correct File repository based on mode.

    P10: FULL ABSTRACT - Passes user context to PostgreSQL repos for permission checks.

    Used as FastAPI dependency:
        @router.get("/files/{file_id}")
        async def get_file(
            file_id: int,
            repo: FileRepository = Depends(get_file_repository)
        ):
            return await repo.get(file_id)  # Permissions checked inside!

    Logic:
    - Offline mode → SQLite repo (no permissions, single user)
    - Online mode → PostgreSQL repo (with user context for permissions)
    """
    # Import here to avoid circular imports
    from server.repositories.postgresql.file_repo import PostgreSQLFileRepository
    from server.repositories.sqlite.file_repo import SQLiteFileRepository

    if _is_offline_mode(request):
        return SQLiteFileRepository()
    else:
        return PostgreSQLFileRepository(db, current_user)


def get_row_repository(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
) -> RowRepository:
    """
    Factory function - returns correct Row repository based on mode.

    P10: FULL ABSTRACT - Passes user context to PostgreSQL repos for permission checks.

    Used as FastAPI dependency:
        @router.get("/files/{file_id}/rows")
        async def get_rows(
            file_id: int,
            repo: RowRepository = Depends(get_row_repository)
        ):
            return await repo.get_for_file(file_id)  # Permissions checked inside!

    Logic:
    - Offline mode → SQLite repo (no permissions, single user)
    - Online mode → PostgreSQL repo (with user context for permissions)
    """
    # Import here to avoid circular imports
    from server.repositories.postgresql.row_repo import PostgreSQLRowRepository
    from server.repositories.sqlite.row_repo import SQLiteRowRepository

    if _is_offline_mode(request):
        return SQLiteRowRepository()
    else:
        return PostgreSQLRowRepository(db, current_user)


def get_project_repository(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
) -> ProjectRepository:
    """
    Factory function - returns correct Project repository based on mode.

    P10: FULL ABSTRACT - Passes user context to PostgreSQL repos for permission checks.

    Used as FastAPI dependency:
        @router.get("/projects/{project_id}")
        async def get_project(
            project_id: int,
            repo: ProjectRepository = Depends(get_project_repository)
        ):
            return await repo.get(project_id)  # Permissions checked inside!

    Logic:
    - Offline mode → SQLite repo (no permissions, single user)
    - Online mode → PostgreSQL repo (with user context for permissions)
    """
    # Import here to avoid circular imports
    from server.repositories.postgresql.project_repo import PostgreSQLProjectRepository
    from server.repositories.sqlite.project_repo import SQLiteProjectRepository

    if _is_offline_mode(request):
        return SQLiteProjectRepository()
    else:
        return PostgreSQLProjectRepository(db, current_user)


def get_folder_repository(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
) -> FolderRepository:
    """
    Factory function - returns correct Folder repository based on mode.

    P10: FULL ABSTRACT - Passes user context to PostgreSQL repos for permission checks.

    Used as FastAPI dependency:
        @router.get("/folders/{folder_id}")
        async def get_folder(
            folder_id: int,
            repo: FolderRepository = Depends(get_folder_repository)
        ):
            return await repo.get(folder_id)  # Permissions checked inside!

    Logic:
    - Offline mode → SQLite repo (no permissions, single user)
    - Online mode → PostgreSQL repo (with user context for permissions)
    """
    # Import here to avoid circular imports
    from server.repositories.postgresql.folder_repo import PostgreSQLFolderRepository
    from server.repositories.sqlite.folder_repo import SQLiteFolderRepository

    if _is_offline_mode(request):
        return SQLiteFolderRepository()
    else:
        return PostgreSQLFolderRepository(db, current_user)


def get_platform_repository(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
) -> PlatformRepository:
    """
    Factory function - returns correct Platform repository based on mode.

    P10: FULL ABSTRACT - Passes user context to PostgreSQL repos for permission checks.

    Used as FastAPI dependency:
        @router.get("/platforms/{platform_id}")
        async def get_platform(
            platform_id: int,
            repo: PlatformRepository = Depends(get_platform_repository)
        ):
            return await repo.get(platform_id)  # Permissions checked inside!

    Logic:
    - Offline mode → SQLite repo (no permissions, single user)
    - Online mode → PostgreSQL repo (with user context for permissions)
    """
    # Import here to avoid circular imports
    from server.repositories.postgresql.platform_repo import PostgreSQLPlatformRepository
    from server.repositories.sqlite.platform_repo import SQLitePlatformRepository

    if _is_offline_mode(request):
        return SQLitePlatformRepository()
    else:
        return PostgreSQLPlatformRepository(db, current_user)


def get_qa_repository(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
) -> QAResultRepository:
    """
    Factory function - returns correct QA repository based on mode.

    P10: FULL ABSTRACT - Passes user context to PostgreSQL repos for permission checks.

    Used as FastAPI dependency:
        @router.get("/files/{file_id}/qa")
        async def get_qa_results(
            file_id: int,
            repo: QAResultRepository = Depends(get_qa_repository)
        ):
            return await repo.get_for_file(file_id)  # Permissions checked inside!

    Logic:
    - Offline mode → SQLite repo (no permissions, single user)
    - Online mode → PostgreSQL repo (with user context for permissions)
    """
    # Import here to avoid circular imports
    from server.repositories.postgresql.qa_repo import PostgreSQLQAResultRepository
    from server.repositories.sqlite.qa_repo import SQLiteQAResultRepository

    if _is_offline_mode(request):
        return SQLiteQAResultRepository()
    else:
        return PostgreSQLQAResultRepository(db, current_user)


def get_trash_repository(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
) -> TrashRepository:
    """
    Factory function - returns correct Trash repository based on mode.

    P10: FULL ABSTRACT - Passes user context to PostgreSQL repos for permission checks.

    Used as FastAPI dependency:
        @router.get("/trash")
        async def list_trash(
            repo: TrashRepository = Depends(get_trash_repository)
        ):
            return await repo.get_for_user()  # User context already in repo!

    Logic:
    - Offline mode → SQLite repo (no permissions, single user)
    - Online mode → PostgreSQL repo (with user context for permissions)
    """
    # Import here to avoid circular imports
    from server.repositories.postgresql.trash_repo import PostgreSQLTrashRepository
    from server.repositories.sqlite.trash_repo import SQLiteTrashRepository

    if _is_offline_mode(request):
        return SQLiteTrashRepository()
    else:
        return PostgreSQLTrashRepository(db, current_user)


def get_capability_repository(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
) -> CapabilityRepository:
    """
    Factory function - returns correct Capability repository based on mode.

    P10: FULL ABSTRACT - Passes user context to PostgreSQL repos for permission checks.

    Used as FastAPI dependency:
        @router.post("/capabilities")
        async def grant_capability(
            repo: CapabilityRepository = Depends(get_capability_repository)
        ):
            return await repo.grant_capability(...)  # Admin check inside!

    Logic:
    - Offline mode → SQLite repo (stub, returns empty - offline = single user)
    - Online mode → PostgreSQL repo (admin-only, checks user role)
    """
    # Import here to avoid circular imports
    from server.repositories.postgresql.capability_repo import PostgreSQLCapabilityRepository
    from server.repositories.sqlite.capability_repo import SQLiteCapabilityRepository

    if _is_offline_mode(request):
        return SQLiteCapabilityRepository()
    else:
        return PostgreSQLCapabilityRepository(db, current_user)


# =============================================================================
# Sync Repositories - For dual-repo operations
# =============================================================================

def get_sync_repositories(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
) -> Tuple[FileRepository, FileRepository]:
    """
    Get BOTH PostgreSQL and SQLite file repositories for sync operations.

    P10: FULL ABSTRACT - Used when online user needs to sync local ↔ server.

    Returns:
        Tuple of (server_repo, local_repo) for sync operations.

    Usage:
        @router.post("/sync/push")
        async def push_local_to_server(
            repos: Tuple[FileRepository, FileRepository] = Depends(get_sync_repositories)
        ):
            server_repo, local_repo = repos
            local_files = await local_repo.get_all()
            for file in local_files:
                await server_repo.create(**file)
    """
    from server.repositories.postgresql.file_repo import PostgreSQLFileRepository
    from server.repositories.sqlite.file_repo import SQLiteFileRepository

    server_repo = PostgreSQLFileRepository(db, current_user)
    local_repo = SQLiteFileRepository()

    return (server_repo, local_repo)
