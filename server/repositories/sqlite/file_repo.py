"""
SQLite File Repository.

Implements FileRepository interface using SQLite (offline mode).
Delegates to existing OfflineDatabase methods.
"""

from typing import List, Optional, Dict, Any

from server.repositories.interfaces.file_repository import FileRepository
from server.database.offline import get_offline_db


class SQLiteFileRepository(FileRepository):
    """
    SQLite implementation of FileRepository.

    Uses OfflineDatabase for all operations.
    This is the offline mode adapter.
    """

    def __init__(self):
        self.db = get_offline_db()

    # =========================================================================
    # Core CRUD
    # =========================================================================

    async def get(self, file_id: int) -> Optional[Dict[str, Any]]:
        # Use existing offline.py method
        file = self.db.get_local_file(file_id)
        if file:
            return self._normalize_file(file)
        # Also try get_file for synced files
        file = self.db.get_file(file_id)
        return self._normalize_file(file) if file else None

    async def get_all(
        self,
        project_id: Optional[int] = None,
        folder_id: Optional[int] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        if project_id is not None:
            files = self.db.get_files(project_id, folder_id)
        else:
            # Get all local files
            files = self.db.get_local_files()

        # Apply pagination
        files = files[offset:offset + limit]
        return [self._normalize_file(f) for f in files]

    async def create(
        self,
        name: str,
        original_filename: str,
        format: str,
        project_id: int,
        folder_id: Optional[int] = None,
        source_language: str = "ko",
        target_language: str = "en",
        extra_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        # Use existing create_local_file which handles:
        # - Negative ID generation
        # - Auto-rename for duplicates
        # - sync_status='local'
        result = self.db.create_local_file(
            name=name,
            original_filename=original_filename,
            file_format=format,
            source_language=source_language,
            target_language=target_language,
            extra_data=extra_data,
            folder_id=folder_id
        )

        # create_local_file returns {"id": ..., "name": ..., "folder_id": ...}
        file_id = result["id"] if isinstance(result, dict) else result

        # Return full file dict
        file = self.db.get_local_file(file_id)
        return self._normalize_file(file)

    async def delete(self, file_id: int, permanent: bool = False) -> bool:
        # Uses P9-BIN-001 soft delete pattern
        return self.db.delete_local_file(file_id, permanent=permanent)

    # =========================================================================
    # File Operations
    # =========================================================================

    async def rename(self, file_id: int, new_name: str) -> Dict[str, Any]:
        success = self.db.rename_local_file(file_id, new_name)
        if not success:
            raise ValueError(f"Could not rename file {file_id}")

        file = self.db.get_local_file(file_id)
        return self._normalize_file(file)

    async def move(
        self,
        file_id: int,
        target_folder_id: Optional[int] = None
    ) -> Dict[str, Any]:
        success = self.db.move_local_file(file_id, target_folder_id)
        if not success:
            raise ValueError(f"Could not move file {file_id}")

        file = self.db.get_local_file(file_id)
        return self._normalize_file(file)

    async def move_cross_project(
        self,
        file_id: int,
        target_project_id: int,
        target_folder_id: Optional[int] = None
    ) -> Dict[str, Any]:
        # For offline mode, cross-project move is typically not supported
        # Local files belong to Offline Storage project
        raise ValueError("Cross-project move not supported in offline mode")

    async def copy(
        self,
        file_id: int,
        target_project_id: Optional[int] = None,
        target_folder_id: Optional[int] = None
    ) -> Dict[str, Any]:
        # Get source file
        source = await self.get(file_id)
        if not source:
            raise ValueError(f"File {file_id} not found")

        # Create copy
        result = await self.create(
            name=source["name"],
            original_filename=source.get("original_filename", source["name"]),
            format=source.get("format", "txt"),
            project_id=target_project_id or source["project_id"],
            folder_id=target_folder_id,
            source_language=source.get("source_language", "ko"),
            target_language=source.get("target_language"),
            extra_data=source.get("extra_data")
        )

        # Copy rows
        rows = await self.get_rows_for_export(file_id)
        if rows:
            await self.add_rows(result["id"], rows)

        return result

    async def update_row_count(self, file_id: int, count: int) -> None:
        # Update row count in SQLite
        with self.db._get_connection() as conn:
            conn.execute(
                "UPDATE offline_files SET row_count = ? WHERE id = ?",
                (count, file_id)
            )
            conn.commit()

    # =========================================================================
    # Row Operations (File-scoped)
    # =========================================================================

    async def get_rows(
        self,
        file_id: int,
        offset: int = 0,
        limit: int = 100,
        status_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        rows = self.db.get_rows_for_file(file_id)

        # Apply status filter
        if status_filter:
            rows = [r for r in rows if r.get("status") == status_filter]

        # Apply pagination
        rows = rows[offset:offset + limit]

        return [self._normalize_row(r) for r in rows]

    async def add_rows(
        self,
        file_id: int,
        rows: List[Dict[str, Any]]
    ) -> int:
        # Use existing method
        self.db.add_rows_to_local_file(file_id, rows)
        return len(rows)

    async def get_rows_for_export(
        self,
        file_id: int,
        status_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        rows = self.db.get_rows_for_file(file_id)

        # Apply status filter
        if status_filter:
            rows = [r for r in rows if r.get("status") == status_filter]

        return [self._normalize_row(r) for r in rows]

    # =========================================================================
    # Query Operations
    # =========================================================================

    async def check_name_exists(
        self,
        name: str,
        project_id: int,
        folder_id: Optional[int] = None,
        exclude_id: Optional[int] = None
    ) -> bool:
        with self.db._get_connection() as conn:
            if folder_id is None:
                query = """
                    SELECT COUNT(*) as cnt FROM offline_files
                    WHERE project_id = ? AND folder_id IS NULL AND name = ?
                """
                params = [project_id, name]
            else:
                query = """
                    SELECT COUNT(*) as cnt FROM offline_files
                    WHERE project_id = ? AND folder_id = ? AND name = ?
                """
                params = [project_id, folder_id, name]

            if exclude_id is not None:
                query += " AND id != ?"
                params.append(exclude_id)

            result = conn.execute(query, params).fetchone()
            return result["cnt"] > 0

    async def generate_unique_name(
        self,
        base_name: str,
        project_id: int,
        folder_id: Optional[int] = None
    ) -> str:
        if not await self.check_name_exists(base_name, project_id, folder_id):
            return base_name

        # Split extension
        if '.' in base_name and not base_name.startswith('.'):
            name_part, ext = base_name.rsplit('.', 1)
            ext = f".{ext}"
        else:
            name_part = base_name
            ext = ""

        counter = 1
        while True:
            new_name = f"{name_part}_{counter}{ext}"
            if not await self.check_name_exists(new_name, project_id, folder_id):
                return new_name
            counter += 1

    async def get_with_project(self, file_id: int) -> Optional[Dict[str, Any]]:
        file = await self.get(file_id)
        if not file:
            return None

        # Get project info
        project_id = file.get("project_id")
        if project_id:
            with self.db._get_connection() as conn:
                project = conn.execute(
                    "SELECT name FROM offline_projects WHERE id = ?",
                    (project_id,)
                ).fetchone()
                if project:
                    file["project_name"] = project["name"]

        return file

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _normalize_file(self, file: Optional[Dict]) -> Optional[Dict[str, Any]]:
        """Normalize file dict to match PostgreSQL format."""
        if not file:
            return None

        return {
            "id": file.get("id"),
            "name": file.get("name"),
            "original_filename": file.get("original_filename"),
            "format": file.get("format"),
            "row_count": file.get("row_count", 0),
            "source_language": file.get("source_language"),
            "target_language": file.get("target_language"),
            "project_id": file.get("project_id"),
            "folder_id": file.get("folder_id"),
            "extra_data": file.get("extra_data"),
            "created_at": file.get("created_at"),
            "updated_at": file.get("updated_at"),
            # SQLite-specific fields
            "sync_status": file.get("sync_status"),
        }

    def _normalize_row(self, row: Optional[Dict]) -> Optional[Dict[str, Any]]:
        """Normalize row dict to match PostgreSQL format."""
        if not row:
            return None

        return {
            "id": row.get("id"),
            "file_id": row.get("file_id"),
            "row_num": row.get("row_num", 0),
            "string_id": row.get("string_id"),
            "source": row.get("source"),
            "target": row.get("target"),
            "memo": row.get("memo"),
            "status": row.get("status"),
            "extra_data": row.get("extra_data"),
            "created_at": row.get("created_at"),
            "updated_at": row.get("updated_at"),
            # SQLite-specific fields
            "sync_status": row.get("sync_status"),
        }

    async def search(self, query: str) -> List[Dict[str, Any]]:
        """
        Search files by name (case-insensitive partial match).

        P10-SEARCH: Used by Explorer Search for unified search across entities.
        """
        search_term = f"%{query}%"
        with self.db._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM offline_files WHERE name LIKE ? COLLATE NOCASE",
                (search_term,)
            ).fetchall()

            return [self._normalize_file(dict(row)) for row in rows]
