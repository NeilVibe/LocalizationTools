"""
Repository Factory.

Provides dependency injection functions for FastAPI routes.
Automatically selects PostgreSQL or SQLite based on user's mode.

P9-ARCH: The repository pattern abstracts database access so that:
- Online mode uses PostgreSQL (multi-user, real-time sync)
- Offline mode uses SQLite (single-user, local storage)
"""

from typing import Optional
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from server.utils.dependencies import get_async_db
from server.repositories.interfaces.tm_repository import TMRepository
from server.repositories.interfaces.file_repository import FileRepository
from server.repositories.interfaces.row_repository import RowRepository
from server.repositories.interfaces.project_repository import ProjectRepository
from server.repositories.interfaces.folder_repository import FolderRepository
from server.repositories.interfaces.platform_repository import PlatformRepository
from server.repositories.interfaces.qa_repository import QAResultRepository
from server.repositories.interfaces.trash_repository import TrashRepository
from server.repositories.interfaces.capability_repository import CapabilityRepository


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
    db: AsyncSession = Depends(get_async_db)
) -> TMRepository:
    """
    Factory function - returns correct TM repository based on mode.

    Used as FastAPI dependency:
        @router.get("/tms")
        async def get_tms(repo: TMRepository = Depends(get_tm_repository)):
            return await repo.get_all()

    Logic:
    - If Authorization header token starts with "OFFLINE_MODE_" → SQLite
    - Otherwise → PostgreSQL
    """
    # Import here to avoid circular imports
    from server.repositories.postgresql.tm_repo import PostgreSQLTMRepository
    from server.repositories.sqlite.tm_repo import SQLiteTMRepository

    # Check if offline mode from Authorization header
    auth_header = request.headers.get("Authorization", "")
    is_offline = auth_header.startswith("Bearer OFFLINE_MODE_")

    if is_offline:
        return SQLiteTMRepository()
    else:
        return PostgreSQLTMRepository(db)


def is_offline_mode(current_user: Optional[dict]) -> bool:
    """Check if current user is in offline mode."""
    if not current_user:
        return False
    token = current_user.get("token", "")
    return isinstance(token, str) and token.startswith("OFFLINE_MODE_")


def get_file_repository(
    request: Request,
    db: AsyncSession = Depends(get_async_db)
) -> FileRepository:
    """
    Factory function - returns correct File repository based on mode.

    Used as FastAPI dependency:
        @router.get("/files/{file_id}")
        async def get_file(
            file_id: int,
            repo: FileRepository = Depends(get_file_repository)
        ):
            return await repo.get(file_id)

    Logic:
    - If Authorization header token starts with "OFFLINE_MODE_" → SQLite
    - Otherwise → PostgreSQL
    """
    # Import here to avoid circular imports
    from server.repositories.postgresql.file_repo import PostgreSQLFileRepository
    from server.repositories.sqlite.file_repo import SQLiteFileRepository

    # Check if offline mode from Authorization header
    auth_header = request.headers.get("Authorization", "")
    is_offline = auth_header.startswith("Bearer OFFLINE_MODE_")

    if is_offline:
        return SQLiteFileRepository()
    else:
        return PostgreSQLFileRepository(db)


def get_row_repository(
    request: Request,
    db: AsyncSession = Depends(get_async_db)
) -> RowRepository:
    """
    Factory function - returns correct Row repository based on mode.

    Used as FastAPI dependency:
        @router.get("/files/{file_id}/rows")
        async def get_rows(
            file_id: int,
            repo: RowRepository = Depends(get_row_repository)
        ):
            return await repo.get_for_file(file_id)

    Logic:
    - If Authorization header token starts with "OFFLINE_MODE_" → SQLite
    - Otherwise → PostgreSQL
    """
    # Import here to avoid circular imports
    from server.repositories.postgresql.row_repo import PostgreSQLRowRepository
    from server.repositories.sqlite.row_repo import SQLiteRowRepository

    # Check if offline mode from Authorization header
    auth_header = request.headers.get("Authorization", "")
    is_offline = auth_header.startswith("Bearer OFFLINE_MODE_")

    if is_offline:
        return SQLiteRowRepository()
    else:
        return PostgreSQLRowRepository(db)


def get_project_repository(
    request: Request,
    db: AsyncSession = Depends(get_async_db)
) -> ProjectRepository:
    """
    Factory function - returns correct Project repository based on mode.

    Used as FastAPI dependency:
        @router.get("/projects/{project_id}")
        async def get_project(
            project_id: int,
            repo: ProjectRepository = Depends(get_project_repository)
        ):
            return await repo.get(project_id)

    Logic:
    - If Authorization header token starts with "OFFLINE_MODE_" → SQLite
    - Otherwise → PostgreSQL
    """
    # Import here to avoid circular imports
    from server.repositories.postgresql.project_repo import PostgreSQLProjectRepository
    from server.repositories.sqlite.project_repo import SQLiteProjectRepository

    # Check if offline mode from Authorization header
    auth_header = request.headers.get("Authorization", "")
    is_offline = auth_header.startswith("Bearer OFFLINE_MODE_")

    if is_offline:
        return SQLiteProjectRepository()
    else:
        return PostgreSQLProjectRepository(db)


def get_folder_repository(
    request: Request,
    db: AsyncSession = Depends(get_async_db)
) -> FolderRepository:
    """
    Factory function - returns correct Folder repository based on mode.

    Used as FastAPI dependency:
        @router.get("/folders/{folder_id}")
        async def get_folder(
            folder_id: int,
            repo: FolderRepository = Depends(get_folder_repository)
        ):
            return await repo.get(folder_id)

    Logic:
    - If Authorization header token starts with "OFFLINE_MODE_" → SQLite
    - Otherwise → PostgreSQL
    """
    # Import here to avoid circular imports
    from server.repositories.postgresql.folder_repo import PostgreSQLFolderRepository
    from server.repositories.sqlite.folder_repo import SQLiteFolderRepository

    # Check if offline mode from Authorization header
    auth_header = request.headers.get("Authorization", "")
    is_offline = auth_header.startswith("Bearer OFFLINE_MODE_")

    if is_offline:
        return SQLiteFolderRepository()
    else:
        return PostgreSQLFolderRepository(db)


def get_platform_repository(
    request: Request,
    db: AsyncSession = Depends(get_async_db)
) -> PlatformRepository:
    """
    Factory function - returns correct Platform repository based on mode.

    Used as FastAPI dependency:
        @router.get("/platforms/{platform_id}")
        async def get_platform(
            platform_id: int,
            repo: PlatformRepository = Depends(get_platform_repository)
        ):
            return await repo.get(platform_id)

    Logic:
    - If Authorization header token starts with "OFFLINE_MODE_" → SQLite
    - Otherwise → PostgreSQL
    """
    # Import here to avoid circular imports
    from server.repositories.postgresql.platform_repo import PostgreSQLPlatformRepository
    from server.repositories.sqlite.platform_repo import SQLitePlatformRepository

    # Check if offline mode from Authorization header
    auth_header = request.headers.get("Authorization", "")
    is_offline = auth_header.startswith("Bearer OFFLINE_MODE_")

    if is_offline:
        return SQLitePlatformRepository()
    else:
        return PostgreSQLPlatformRepository(db)


def get_qa_repository(
    request: Request,
    db: AsyncSession = Depends(get_async_db)
) -> QAResultRepository:
    """
    Factory function - returns correct QA repository based on mode.

    Used as FastAPI dependency:
        @router.get("/files/{file_id}/qa")
        async def get_qa_results(
            file_id: int,
            repo: QAResultRepository = Depends(get_qa_repository)
        ):
            return await repo.get_for_file(file_id)

    Logic:
    - If Authorization header token starts with "OFFLINE_MODE_" → SQLite
    - Otherwise → PostgreSQL

    P10: FULL PARITY - Both databases persist QA results identically.
    """
    # Import here to avoid circular imports
    from server.repositories.postgresql.qa_repo import PostgreSQLQAResultRepository
    from server.repositories.sqlite.qa_repo import SQLiteQAResultRepository

    # Check if offline mode from Authorization header
    auth_header = request.headers.get("Authorization", "")
    is_offline = auth_header.startswith("Bearer OFFLINE_MODE_")

    if is_offline:
        return SQLiteQAResultRepository()
    else:
        return PostgreSQLQAResultRepository(db)


def get_trash_repository(
    request: Request,
    db: AsyncSession = Depends(get_async_db)
) -> TrashRepository:
    """
    Factory function - returns correct Trash repository based on mode.

    Used as FastAPI dependency:
        @router.get("/trash")
        async def list_trash(
            repo: TrashRepository = Depends(get_trash_repository)
        ):
            return await repo.get_for_user(user_id)

    Logic:
    - If Authorization header token starts with "OFFLINE_MODE_" → SQLite
    - Otherwise → PostgreSQL

    P10: FULL PARITY - Both databases persist trash identically.
    """
    # Import here to avoid circular imports
    from server.repositories.postgresql.trash_repo import PostgreSQLTrashRepository
    from server.repositories.sqlite.trash_repo import SQLiteTrashRepository

    # Check if offline mode from Authorization header
    auth_header = request.headers.get("Authorization", "")
    is_offline = auth_header.startswith("Bearer OFFLINE_MODE_")

    if is_offline:
        return SQLiteTrashRepository()
    else:
        return PostgreSQLTrashRepository(db)


def get_capability_repository(
    request: Request,
    db: AsyncSession = Depends(get_async_db)
) -> CapabilityRepository:
    """
    Factory function - returns correct Capability repository based on mode.

    Used as FastAPI dependency:
        @router.post("/capabilities")
        async def grant_capability(
            repo: CapabilityRepository = Depends(get_capability_repository)
        ):
            return await repo.grant_capability(...)

    Logic:
    - If Authorization header token starts with "OFFLINE_MODE_" → SQLite (stub)
    - Otherwise → PostgreSQL

    Note: Capabilities are admin-only and primarily online functionality.
    SQLite adapter returns empty results gracefully for offline mode.
    """
    # Import here to avoid circular imports
    from server.repositories.postgresql.capability_repo import PostgreSQLCapabilityRepository
    from server.repositories.sqlite.capability_repo import SQLiteCapabilityRepository

    # Check if offline mode from Authorization header
    auth_header = request.headers.get("Authorization", "")
    is_offline = auth_header.startswith("Bearer OFFLINE_MODE_")

    if is_offline:
        return SQLiteCapabilityRepository()
    else:
        return PostgreSQLCapabilityRepository(db)
