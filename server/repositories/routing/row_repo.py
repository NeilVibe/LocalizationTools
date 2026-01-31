"""
Routing Row Repository.

Transparently routes row operations based on entity IDs:
- Negative IDs → SQLite OFFLINE mode (local Electron data)
- Positive IDs → Primary repository (PostgreSQL or SQLite SERVER mode)

This eliminates factory pattern violations where routes directly imported
SQLiteRowRepository for negative IDs.
"""

from typing import List, Optional, Dict, Any, Tuple
from loguru import logger

from server.repositories.interfaces.row_repository import RowRepository
from server.repositories.sqlite.row_repo import SQLiteRowRepository
from server.repositories.sqlite.base import SchemaMode


class RoutingRowRepository(RowRepository):
    """
    Routes row operations based on entity IDs.
    
    Negative IDs are local Electron data (SQLite OFFLINE mode).
    Positive IDs go to the primary repository (PostgreSQL or SQLite SERVER).
    
    This wraps any RowRepository and adds transparent routing for negative IDs.
    """
    
    def __init__(self, primary_repo: RowRepository):
        """
        Initialize with the primary repository.
        
        Args:
            primary_repo: The repository for positive IDs (PostgreSQL or SQLite SERVER)
        """
        self._primary = primary_repo
        self._offline = SQLiteRowRepository(schema_mode=SchemaMode.OFFLINE)
    
    def _get_repo_for_id(self, entity_id: int) -> RowRepository:
        """Get appropriate repository based on ID sign."""
        if entity_id < 0:
            return self._offline
        return self._primary
    
    # =========================================================================
    # Core CRUD - Routes based on row_id
    # =========================================================================
    
    async def get(self, row_id: int) -> Optional[Dict[str, Any]]:
        """Get row by ID."""
        repo = self._get_repo_for_id(row_id)
        return await repo.get(row_id)
    
    async def get_with_file(self, row_id: int) -> Optional[Dict[str, Any]]:
        """Get row with file info."""
        repo = self._get_repo_for_id(row_id)
        return await repo.get_with_file(row_id)
    
    async def create(
        self,
        file_id: int,
        row_num: int,
        source: str,
        target: str = "",
        string_id: Optional[str] = None,
        status: str = "pending",
        extra_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a single row - routes based on file_id."""
        repo = self._get_repo_for_id(file_id)
        return await repo.create(
            file_id=file_id,
            row_num=row_num,
            source=source,
            target=target,
            string_id=string_id,
            status=status,
            extra_data=extra_data
        )
    
    async def update(
        self,
        row_id: int,
        target: Optional[str] = None,
        status: Optional[str] = None,
        updated_by: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Update a row's target text or status."""
        repo = self._get_repo_for_id(row_id)
        return await repo.update(
            row_id=row_id,
            target=target,
            status=status,
            updated_by=updated_by
        )
    
    async def delete(self, row_id: int) -> bool:
        """Delete a row."""
        repo = self._get_repo_for_id(row_id)
        return await repo.delete(row_id)
    
    # =========================================================================
    # Bulk Operations - Routes based on file_id or first update's ID
    # =========================================================================
    
    async def bulk_create(
        self,
        file_id: int,
        rows: List[Dict[str, Any]]
    ) -> int:
        """Bulk create rows for a file."""
        repo = self._get_repo_for_id(file_id)
        return await repo.bulk_create(file_id=file_id, rows=rows)
    
    async def bulk_update(
        self,
        updates: List[Dict[str, Any]]
    ) -> int:
        """Bulk update multiple rows."""
        if not updates:
            return 0
        
        # Split updates by ID sign
        positive_updates = [u for u in updates if u.get("id", 0) >= 0]
        negative_updates = [u for u in updates if u.get("id", 0) < 0]
        
        count = 0
        if positive_updates:
            count += await self._primary.bulk_update(positive_updates)
        if negative_updates:
            count += await self._offline.bulk_update(negative_updates)
        
        return count
    
    # =========================================================================
    # Query Operations - Routes based on file_id
    # =========================================================================
    
    async def get_for_file(
        self,
        file_id: int,
        page: int = 1,
        limit: int = 50,
        search: Optional[str] = None,
        search_mode: str = "contain",
        search_fields: str = "source,target",
        status: Optional[str] = None,
        filter_type: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Get paginated rows for a file with search/filter."""
        repo = self._get_repo_for_id(file_id)
        return await repo.get_for_file(
            file_id=file_id,
            page=page,
            limit=limit,
            search=search,
            search_mode=search_mode,
            search_fields=search_fields,
            status=status,
            filter_type=filter_type
        )
    
    async def get_all_for_file(
        self,
        file_id: int,
        status_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all rows for a file (no pagination, for export)."""
        repo = self._get_repo_for_id(file_id)
        return await repo.get_all_for_file(file_id=file_id, status_filter=status_filter)
    
    async def count_for_file(self, file_id: int) -> int:
        """Count rows in a file."""
        repo = self._get_repo_for_id(file_id)
        return await repo.count_for_file(file_id)
    
    # =========================================================================
    # History Operations - Routes based on row_id
    # =========================================================================
    
    async def add_edit_history(
        self,
        row_id: int,
        user_id: int,
        old_target: Optional[str],
        new_target: Optional[str],
        old_status: Optional[str],
        new_status: Optional[str]
    ) -> None:
        """Record edit history for a row."""
        repo = self._get_repo_for_id(row_id)
        await repo.add_edit_history(
            row_id=row_id,
            user_id=user_id,
            old_target=old_target,
            new_target=new_target,
            old_status=old_status,
            new_status=new_status
        )
    
    async def get_edit_history(
        self,
        row_id: int,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get edit history for a row."""
        repo = self._get_repo_for_id(row_id)
        return await repo.get_edit_history(row_id=row_id, limit=limit)
    
    # =========================================================================
    # Similarity Search - Uses primary repo (PostgreSQL feature)
    # =========================================================================
    
    async def suggest_similar(
        self,
        source: str,
        file_id: Optional[int] = None,
        project_id: Optional[int] = None,
        exclude_row_id: Optional[int] = None,
        threshold: float = 0.5,
        max_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for similar rows using pg_trgm similarity.
        
        Routes based on file_id if provided, otherwise uses primary repo.
        Note: SQLite returns empty list (similarity not available offline).
        """
        if file_id is not None and file_id < 0:
            return await self._offline.suggest_similar(
                source=source,
                file_id=file_id,
                project_id=project_id,
                exclude_row_id=exclude_row_id,
                threshold=threshold,
                max_results=max_results
            )
        return await self._primary.suggest_similar(
            source=source,
            file_id=file_id,
            project_id=project_id,
            exclude_row_id=exclude_row_id,
            threshold=threshold,
            max_results=max_results
        )
