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
"""

from server.repositories.interfaces.tm_repository import TMRepository, AssignmentTarget
from server.repositories.factory import get_tm_repository

__all__ = [
    "TMRepository",
    "AssignmentTarget",
    "get_tm_repository",
]
