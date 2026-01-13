"""
Repository Pattern Implementation for LocaNext.

This module provides the abstraction layer between routes and databases.
Same interface works for both PostgreSQL (online) and SQLite (offline).

Usage in routes:
    from server.repositories import get_tm_repository, TMRepository

    @router.patch("/tm/{tm_id}/assign")
    async def assign_tm(
        tm_id: int,
        repo: TMRepository = Depends(get_tm_repository)
    ):
        return await repo.assign(tm_id, target)

    from server.repositories import get_file_repository, FileRepository

    @router.get("/files/{file_id}")
    async def get_file(
        file_id: int,
        repo: FileRepository = Depends(get_file_repository)
    ):
        return await repo.get(file_id)
"""

from server.repositories.interfaces.tm_repository import TMRepository, AssignmentTarget
from server.repositories.interfaces.file_repository import FileRepository
from server.repositories.interfaces.row_repository import RowRepository
from server.repositories.interfaces.project_repository import ProjectRepository
from server.repositories.interfaces.folder_repository import FolderRepository
from server.repositories.interfaces.platform_repository import PlatformRepository
from server.repositories.interfaces.qa_repository import QAResultRepository
from server.repositories.interfaces.trash_repository import TrashRepository
from server.repositories.interfaces.capability_repository import CapabilityRepository
from server.repositories.factory import (
    get_tm_repository, get_file_repository, get_row_repository,
    get_project_repository, get_folder_repository, get_platform_repository,
    get_qa_repository, get_trash_repository, get_capability_repository
)

__all__ = [
    # TM Repository
    "TMRepository",
    "AssignmentTarget",
    "get_tm_repository",
    # File Repository
    "FileRepository",
    "get_file_repository",
    # Row Repository
    "RowRepository",
    "get_row_repository",
    # Project Repository
    "ProjectRepository",
    "get_project_repository",
    # Folder Repository
    "FolderRepository",
    "get_folder_repository",
    # Platform Repository
    "PlatformRepository",
    "get_platform_repository",
    # QA Repository
    "QAResultRepository",
    "get_qa_repository",
    # Trash Repository
    "TrashRepository",
    "get_trash_repository",
    # Capability Repository
    "CapabilityRepository",
    "get_capability_repository",
]
