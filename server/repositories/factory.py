"""
Repository Factory.

P10: FULL ABSTRACT + REPO + FACTORY Pattern
ARCH-001: 3-Mode Detection for TRUE Layer Abstraction

Provides dependency injection functions for FastAPI routes.
Automatically selects the correct repository based on mode:

3-MODE DETECTION:
├─ Offline mode (header)      → SQLiteRepo(schema_mode=OFFLINE)  → offline_* tables
├─ Server local (SQLite)      → SQLiteRepo(schema_mode=SERVER)   → ldm_* tables
└─ PostgreSQL available       → PostgreSQLRepo(db, user)         → ldm_* tables

Routes ONLY use repositories. No direct DB access. Ever.
Permissions are baked INTO PostgreSQL repositories.
"""

from typing import Tuple
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
    Detect if request is in offline mode (Electron app's local storage).

    Offline mode is indicated by Authorization header starting with "OFFLINE_MODE_".

    This uses the OFFLINE schema (offline_projects, offline_files, etc.)
    which is separate from the server schema (ldm_projects, ldm_files, etc.).
    """
    auth_header = request.headers.get("Authorization", "")
    return auth_header.startswith("Bearer OFFLINE_MODE_")


def _is_server_local() -> bool:
    """
    ARCH-001: Detect if server is running in server-local SQLite mode.

    When PostgreSQL is unavailable, the server uses SQLite with the ldm_* schema
    (same table structure as PostgreSQL). This is different from offline mode
    which uses the offline_* schema.

    Returns:
        True if server is using server-local SQLite (ACTIVE_DATABASE_TYPE == "sqlite")
    """
    from server import config
    return config.ACTIVE_DATABASE_TYPE == "sqlite"


def get_tm_repository(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
) -> TMRepository:
    """
    Factory function - returns correct TM repository based on mode.

    ARCH-001: 3-Mode Detection
    - Offline mode (header) → SQLiteRepo(OFFLINE) → offline_tms
    - Server local (SQLite) → SQLiteRepo(SERVER)  → ldm_translation_memories
    - PostgreSQL available  → PostgreSQLRepo      → ldm_translation_memories
    """
    from server.repositories.sqlite.tm_repo import SQLiteTMRepository
    from server.repositories.sqlite.base import SchemaMode

    if _is_offline_mode(request):
        return SQLiteTMRepository(schema_mode=SchemaMode.OFFLINE)
    elif _is_server_local():
        return SQLiteTMRepository(schema_mode=SchemaMode.SERVER)
    else:
        from server.repositories.postgresql.tm_repo import PostgreSQLTMRepository
        return PostgreSQLTMRepository(db, current_user)


def get_file_repository(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
) -> FileRepository:
    """
    Factory function - returns correct File repository based on mode.

    ARCH-001: 3-Mode Detection
    - Offline mode (header) → SQLiteRepo(OFFLINE) → offline_files
    - Server local (SQLite) → SQLiteRepo(SERVER)  → ldm_files
    - PostgreSQL available  → PostgreSQLRepo      → ldm_files
    """
    from server.repositories.sqlite.file_repo import SQLiteFileRepository
    from server.repositories.sqlite.base import SchemaMode

    if _is_offline_mode(request):
        return SQLiteFileRepository(schema_mode=SchemaMode.OFFLINE)
    elif _is_server_local():
        return SQLiteFileRepository(schema_mode=SchemaMode.SERVER)
    else:
        from server.repositories.postgresql.file_repo import PostgreSQLFileRepository
        return PostgreSQLFileRepository(db, current_user)


def get_row_repository(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
) -> RowRepository:
    """
    Factory function - returns correct Row repository based on mode.

    ARCH-001: 3-Mode Detection + Negative ID Routing
    - Offline mode (header) → SQLiteRepo(OFFLINE) → offline_rows
    - Server local (SQLite) → SQLiteRepo(SERVER)  → ldm_rows
    - PostgreSQL available  → RoutingRepo wrapping PostgreSQL
    
    RoutingRowRepository handles negative IDs (local Electron data) transparently.
    Routes never need to know about negative ID handling.
    """
    from server.repositories.sqlite.row_repo import SQLiteRowRepository
    from server.repositories.sqlite.base import SchemaMode
    from server.repositories.routing.row_repo import RoutingRowRepository

    if _is_offline_mode(request):
        return SQLiteRowRepository(schema_mode=SchemaMode.OFFLINE)
    elif _is_server_local():
        primary = SQLiteRowRepository(schema_mode=SchemaMode.SERVER)
        return RoutingRowRepository(primary)
    else:
        from server.repositories.postgresql.row_repo import PostgreSQLRowRepository
        primary = PostgreSQLRowRepository(db, current_user)
        return RoutingRowRepository(primary)


def get_project_repository(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
) -> ProjectRepository:
    """
    Factory function - returns correct Project repository based on mode.

    ARCH-001: 3-Mode Detection
    - Offline mode (header) → SQLiteRepo(OFFLINE) → offline_projects
    - Server local (SQLite) → SQLiteRepo(SERVER)  → ldm_projects
    - PostgreSQL available  → PostgreSQLRepo      → ldm_projects
    """
    from server.repositories.sqlite.project_repo import SQLiteProjectRepository
    from server.repositories.sqlite.base import SchemaMode

    if _is_offline_mode(request):
        return SQLiteProjectRepository(schema_mode=SchemaMode.OFFLINE)
    elif _is_server_local():
        return SQLiteProjectRepository(schema_mode=SchemaMode.SERVER)
    else:
        from server.repositories.postgresql.project_repo import PostgreSQLProjectRepository
        return PostgreSQLProjectRepository(db, current_user)


def get_folder_repository(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
) -> FolderRepository:
    """
    Factory function - returns correct Folder repository based on mode.

    ARCH-001: 3-Mode Detection
    - Offline mode (header) → SQLiteRepo(OFFLINE) → offline_folders
    - Server local (SQLite) → SQLiteRepo(SERVER)  → ldm_folders
    - PostgreSQL available  → PostgreSQLRepo      → ldm_folders
    """
    from server.repositories.sqlite.folder_repo import SQLiteFolderRepository
    from server.repositories.sqlite.base import SchemaMode

    if _is_offline_mode(request):
        return SQLiteFolderRepository(schema_mode=SchemaMode.OFFLINE)
    elif _is_server_local():
        return SQLiteFolderRepository(schema_mode=SchemaMode.SERVER)
    else:
        from server.repositories.postgresql.folder_repo import PostgreSQLFolderRepository
        return PostgreSQLFolderRepository(db, current_user)


def get_platform_repository(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
) -> PlatformRepository:
    """
    Factory function - returns correct Platform repository based on mode.

    ARCH-001: 3-Mode Detection
    - Offline mode (header) → SQLiteRepo(OFFLINE) → offline_platforms
    - Server local (SQLite) → SQLiteRepo(SERVER)  → ldm_platforms
    - PostgreSQL available  → PostgreSQLRepo      → ldm_platforms
    """
    from server.repositories.sqlite.platform_repo import SQLitePlatformRepository
    from server.repositories.sqlite.base import SchemaMode

    if _is_offline_mode(request):
        return SQLitePlatformRepository(schema_mode=SchemaMode.OFFLINE)
    elif _is_server_local():
        return SQLitePlatformRepository(schema_mode=SchemaMode.SERVER)
    else:
        from server.repositories.postgresql.platform_repo import PostgreSQLPlatformRepository
        return PostgreSQLPlatformRepository(db, current_user)


def get_qa_repository(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
) -> QAResultRepository:
    """
    Factory function - returns correct QA repository based on mode.

    ARCH-001: 3-Mode Detection
    - Offline mode (header) → SQLiteRepo(OFFLINE) → offline_qa_results
    - Server local (SQLite) → SQLiteRepo(SERVER)  → ldm_qa_results
    - PostgreSQL available  → PostgreSQLRepo      → ldm_qa_results
    """
    from server.repositories.sqlite.qa_repo import SQLiteQAResultRepository
    from server.repositories.sqlite.base import SchemaMode

    if _is_offline_mode(request):
        return SQLiteQAResultRepository(schema_mode=SchemaMode.OFFLINE)
    elif _is_server_local():
        return SQLiteQAResultRepository(schema_mode=SchemaMode.SERVER)
    else:
        from server.repositories.postgresql.qa_repo import PostgreSQLQAResultRepository
        return PostgreSQLQAResultRepository(db, current_user)


def get_trash_repository(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
) -> TrashRepository:
    """
    Factory function - returns correct Trash repository based on mode.

    ARCH-001: 3-Mode Detection
    - Offline mode (header) → SQLiteRepo(OFFLINE) → offline_trash
    - Server local (SQLite) → SQLiteRepo(SERVER)  → ldm_trash
    - PostgreSQL available  → PostgreSQLRepo      → ldm_trash
    """
    from server.repositories.sqlite.trash_repo import SQLiteTrashRepository
    from server.repositories.sqlite.base import SchemaMode

    if _is_offline_mode(request):
        return SQLiteTrashRepository(schema_mode=SchemaMode.OFFLINE)
    elif _is_server_local():
        return SQLiteTrashRepository(schema_mode=SchemaMode.SERVER)
    else:
        from server.repositories.postgresql.trash_repo import PostgreSQLTrashRepository
        return PostgreSQLTrashRepository(db, current_user)


def get_capability_repository(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
) -> CapabilityRepository:
    """
    Factory function - returns correct Capability repository based on mode.

    ARCH-001: 3-Mode Detection
    - Offline mode (header) → SQLiteRepo(OFFLINE) (stub - single user)
    - Server local (SQLite) → SQLiteRepo(SERVER) (stub - no multi-user)
    - PostgreSQL available  → PostgreSQLRepo (admin-only)

    Note: Capability management is admin-only and not available in SQLite modes.
    """
    from server.repositories.sqlite.capability_repo import SQLiteCapabilityRepository

    if _is_offline_mode(request):
        return SQLiteCapabilityRepository()
    elif _is_server_local():
        return SQLiteCapabilityRepository()
    else:
        from server.repositories.postgresql.capability_repo import PostgreSQLCapabilityRepository
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
    from server.repositories.sqlite.base import SchemaMode

    server_repo = PostgreSQLFileRepository(db, current_user)
    local_repo = SQLiteFileRepository(schema_mode=SchemaMode.OFFLINE)

    return (server_repo, local_repo)
