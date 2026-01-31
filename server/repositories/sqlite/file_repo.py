"""
SQLite File Repository.

Implements FileRepository interface using SQLite (offline mode).

ARCH-001: Schema-aware - works with both OFFLINE (offline_files) and SERVER (ldm_files) modes.
ASYNC MIGRATION (2026-01-31): Uses aiosqlite for true async operations.
"""

import time
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from loguru import logger

from server.repositories.interfaces.file_repository import FileRepository
from server.repositories.sqlite.base import SQLiteBaseRepository, SchemaMode


class SQLiteFileRepository(SQLiteBaseRepository, FileRepository):
    """
    SQLite implementation of FileRepository.

    ARCH-001: Schema-aware - uses _table() for dynamic table names.
    """

    def __init__(self, schema_mode: SchemaMode = SchemaMode.OFFLINE):
        super().__init__(schema_mode)

    # =========================================================================
    # Core CRUD
    # =========================================================================

    async def get(self, file_id: int) -> Optional[Dict[str, Any]]:
        async with self.db._get_async_connection() as conn:
            cursor = await conn.execute(
                f"SELECT * FROM {self._table('files')} WHERE id = ?",
                (file_id,)
            )
            row = await cursor.fetchone()
            return self._normalize_file(dict(row)) if row else None

    async def get_all(
        self,
        project_id: Optional[int] = None,
        folder_id: Optional[int] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        async with self.db._get_async_connection() as conn:
            if project_id is not None:
                if folder_id is not None:
                    cursor = await conn.execute(
                        f"SELECT * FROM {self._table('files')} WHERE project_id = ? AND folder_id = ? ORDER BY name LIMIT ? OFFSET ?",
                        (project_id, folder_id, limit, offset)
                    )
                else:
                    cursor = await conn.execute(
                        f"SELECT * FROM {self._table('files')} WHERE project_id = ? ORDER BY name LIMIT ? OFFSET ?",
                        (project_id, limit, offset)
                    )
            else:
                cursor = await conn.execute(
                    f"SELECT * FROM {self._table('files')} ORDER BY name LIMIT ? OFFSET ?",
                    (limit, offset)
                )

            rows = await cursor.fetchall()
            return [self._normalize_file(dict(row)) for row in rows]

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
        # Generate unique name
        unique_name = await self.generate_unique_name(name, project_id, folder_id)

        # Use negative IDs for local files
        file_id = -int(time.time() * 1000) % 1000000000
        now = datetime.now().isoformat()
        extra_data_json = json.dumps(extra_data) if extra_data else None

        async with self.db._get_async_connection() as conn:
            if self.schema_mode == SchemaMode.OFFLINE:
                await conn.execute(
                    f"""INSERT INTO {self._table('files')}
                       (id, server_id, name, original_filename, format, source_language,
                        target_language, row_count, project_id, server_project_id,
                        folder_id, server_folder_id, extra_data, created_at, updated_at,
                        downloaded_at, sync_status)
                       VALUES (?, 0, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?, ?, datetime('now'), 'local')""",
                    (
                        file_id,
                        unique_name,
                        original_filename,
                        format,
                        source_language,
                        target_language,
                        project_id,
                        project_id,
                        folder_id,
                        folder_id,
                        extra_data_json,
                        now,
                        now,
                    )
                )
            else:
                await conn.execute(
                    f"""INSERT INTO {self._table('files')}
                       (id, name, original_filename, format, source_language,
                        target_language, row_count, project_id, folder_id, extra_data,
                        created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?)""",
                    (
                        file_id,
                        unique_name,
                        original_filename,
                        format,
                        source_language,
                        target_language,
                        project_id,
                        folder_id,
                        extra_data_json,
                        now,
                        now,
                    )
                )
            await conn.commit()

        logger.info(f"Created local file: id={file_id}, name='{unique_name}'")
        return await self.get(file_id)

    async def delete(self, file_id: int, permanent: bool = False) -> bool:
        file = await self.get(file_id)
        if not file:
            return False

        async with self.db._get_async_connection() as conn:
            # Delete rows first
            await conn.execute(
                f"DELETE FROM {self._table('rows')} WHERE file_id = ?",
                (file_id,)
            )

            # Delete QA results if table exists
            try:
                await conn.execute(
                    f"DELETE FROM {self._table('qa_results')} WHERE file_id = ?",
                    (file_id,)
                )
            except Exception:
                pass  # Table might not exist

            # Delete file
            await conn.execute(
                f"DELETE FROM {self._table('files')} WHERE id = ?",
                (file_id,)
            )
            await conn.commit()

        logger.info(f"Deleted file: id={file_id}")
        return True

    # =========================================================================
    # File Operations
    # =========================================================================

    async def rename(self, file_id: int, new_name: str) -> Dict[str, Any]:
        file = await self.get(file_id)
        if not file:
            raise ValueError(f"File {file_id} not found")

        # Check if name exists
        if await self.check_name_exists(new_name, file["project_id"], file.get("folder_id"), exclude_id=file_id):
            raise ValueError(f"A file named '{new_name}' already exists")

        async with self.db._get_async_connection() as conn:
            await conn.execute(
                f"UPDATE {self._table('files')} SET name = ?, updated_at = datetime('now') WHERE id = ?",
                (new_name, file_id)
            )
            await conn.commit()

        logger.info(f"Renamed file: id={file_id}, '{file['name']}' -> '{new_name}'")
        return await self.get(file_id)

    async def move(
        self,
        file_id: int,
        target_folder_id: Optional[int] = None
    ) -> Dict[str, Any]:
        file = await self.get(file_id)
        if not file:
            raise ValueError(f"File {file_id} not found")

        async with self.db._get_async_connection() as conn:
            await conn.execute(
                f"UPDATE {self._table('files')} SET folder_id = ?, updated_at = datetime('now') WHERE id = ?",
                (target_folder_id, file_id)
            )
            await conn.commit()

        logger.info(f"Moved file: id={file_id}, folder={target_folder_id}")
        return await self.get(file_id)

    async def move_cross_project(
        self,
        file_id: int,
        target_project_id: int,
        target_folder_id: Optional[int] = None
    ) -> Dict[str, Any]:
        file = await self.get(file_id)
        if not file:
            raise ValueError(f"File {file_id} not found")

        # Generate unique name in target location
        new_name = await self.generate_unique_name(file["name"], target_project_id, target_folder_id)

        async with self.db._get_async_connection() as conn:
            await conn.execute(
                f"UPDATE {self._table('files')} SET name = ?, project_id = ?, folder_id = ?, updated_at = datetime('now') WHERE id = ?",
                (new_name, target_project_id, target_folder_id, file_id)
            )
            await conn.commit()

        logger.info(f"Moved file cross-project: id={file_id}, project={target_project_id}")
        return await self.get(file_id)

    async def copy(
        self,
        file_id: int,
        target_project_id: Optional[int] = None,
        target_folder_id: Optional[int] = None
    ) -> Dict[str, Any]:
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
        async with self.db._get_async_connection() as conn:
            await conn.execute(
                f"UPDATE {self._table('files')} SET row_count = ? WHERE id = ?",
                (count, file_id)
            )
            await conn.commit()

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
        async with self.db._get_async_connection() as conn:
            if status_filter:
                cursor = await conn.execute(
                    f"SELECT * FROM {self._table('rows')} WHERE file_id = ? AND status = ? ORDER BY row_num LIMIT ? OFFSET ?",
                    (file_id, status_filter, limit, offset)
                )
            else:
                cursor = await conn.execute(
                    f"SELECT * FROM {self._table('rows')} WHERE file_id = ? ORDER BY row_num LIMIT ? OFFSET ?",
                    (file_id, limit, offset)
                )
            rows = await cursor.fetchall()
            return [self._normalize_row(dict(row)) for row in rows]

    async def add_rows(
        self,
        file_id: int,
        rows: List[Dict[str, Any]]
    ) -> int:
        if not rows:
            return 0

        now = datetime.now().isoformat()
        async with self.db._get_async_connection() as conn:
            for row_data in rows:
                row_id = -int(time.time() * 1000) % 1000000000
                extra_data_json = json.dumps(row_data.get("extra_data")) if row_data.get("extra_data") else None

                if self.schema_mode == SchemaMode.OFFLINE:
                    await conn.execute(
                        f"""INSERT INTO {self._table('rows')}
                           (id, server_id, file_id, server_file_id, row_num, string_id,
                            source, target, memo, status, extra_data, created_at,
                            updated_at, downloaded_at, sync_status)
                           VALUES (?, 0, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), 'local')""",
                        (
                            row_id,
                            file_id,
                            file_id,
                            row_data.get("row_num", 0),
                            row_data.get("string_id"),
                            row_data.get("source"),
                            row_data.get("target"),
                            row_data.get("memo"),
                            row_data.get("status", "normal"),
                            extra_data_json,
                            now,
                            now,
                        )
                    )
                else:
                    await conn.execute(
                        f"""INSERT INTO {self._table('rows')}
                           (id, file_id, row_num, string_id, source, target, memo,
                            status, extra_data, created_at, updated_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            row_id,
                            file_id,
                            row_data.get("row_num", 0),
                            row_data.get("string_id"),
                            row_data.get("source"),
                            row_data.get("target"),
                            row_data.get("memo"),
                            row_data.get("status", "normal"),
                            extra_data_json,
                            now,
                            now,
                        )
                    )
            await conn.commit()

        # Update file row count
        await self.update_row_count(file_id, len(rows))
        return len(rows)

    async def get_rows_for_export(
        self,
        file_id: int,
        status_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        async with self.db._get_async_connection() as conn:
            if status_filter:
                cursor = await conn.execute(
                    f"SELECT * FROM {self._table('rows')} WHERE file_id = ? AND status = ? ORDER BY row_num",
                    (file_id, status_filter)
                )
            else:
                cursor = await conn.execute(
                    f"SELECT * FROM {self._table('rows')} WHERE file_id = ? ORDER BY row_num",
                    (file_id,)
                )
            rows = await cursor.fetchall()
            return [self._normalize_row(dict(row)) for row in rows]

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
        async with self.db._get_async_connection() as conn:
            if folder_id is None:
                query = f"""
                    SELECT COUNT(*) as cnt FROM {self._table('files')}
                    WHERE project_id = ? AND folder_id IS NULL AND LOWER(name) = LOWER(?)
                """
                params = [project_id, name]
            else:
                query = f"""
                    SELECT COUNT(*) as cnt FROM {self._table('files')}
                    WHERE project_id = ? AND folder_id = ? AND LOWER(name) = LOWER(?)
                """
                params = [project_id, folder_id, name]

            if exclude_id is not None:
                query += " AND id != ?"
                params.append(exclude_id)

            cursor = await conn.execute(query, params)
            result = await cursor.fetchone()
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
            async with self.db._get_async_connection() as conn:
                cursor = await conn.execute(
                    f"SELECT name FROM {self._table('projects')} WHERE id = ?",
                    (project_id,)
                )
                project = await cursor.fetchone()
                if project:
                    file["project_name"] = project["name"]

        return file

    async def search(self, query: str) -> List[Dict[str, Any]]:
        """
        Search files by name (case-insensitive partial match).

        P10-SEARCH: Used by Explorer Search for unified search across entities.
        """
        search_term = f"%{query}%"
        async with self.db._get_async_connection() as conn:
            cursor = await conn.execute(
                f"SELECT * FROM {self._table('files')} WHERE name LIKE ? COLLATE NOCASE",
                (search_term,)
            )
            rows = await cursor.fetchall()

            return [self._normalize_file(dict(row)) for row in rows]

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _normalize_file(self, file: Optional[Dict]) -> Optional[Dict[str, Any]]:
        """Normalize file dict to match PostgreSQL format."""
        if not file:
            return None

        result = {
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
        }

        # Only include sync_status for OFFLINE mode
        if self._has_column("sync_status"):
            result["sync_status"] = file.get("sync_status")

        return result

    def _normalize_row(self, row: Optional[Dict]) -> Optional[Dict[str, Any]]:
        """Normalize row dict to match PostgreSQL format."""
        if not row:
            return None

        result = {
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
        }

        # Only include sync_status for OFFLINE mode
        if self._has_column("sync_status"):
            result["sync_status"] = row.get("sync_status")

        return result
