"""
SQLite Folder Repository.

Implements FolderRepository interface using SQLite (offline mode).

ARCH-001: Schema-aware - works with both OFFLINE (offline_folders) and SERVER (ldm_folders) modes.
ASYNC MIGRATION (2026-01-31): Uses aiosqlite for true async operations.
"""

import time
from datetime import datetime
from typing import List, Optional, Dict, Any
from loguru import logger

from server.repositories.interfaces.folder_repository import FolderRepository
from server.repositories.sqlite.base import SQLiteBaseRepository, SchemaMode


class SQLiteFolderRepository(SQLiteBaseRepository, FolderRepository):
    """
    SQLite implementation of FolderRepository.

    ARCH-001: Schema-aware - uses _table() for dynamic table names.
    """

    def __init__(self, schema_mode: SchemaMode = SchemaMode.OFFLINE):
        super().__init__(schema_mode)

    def _normalize_folder(self, folder: Optional[Dict]) -> Optional[Dict[str, Any]]:
        """Normalize folder dict to match PostgreSQL format."""
        if not folder:
            return None

        result = {
            "id": folder.get("id"),
            "name": folder.get("name"),
            "project_id": folder.get("project_id"),
            "parent_id": folder.get("parent_id"),
            "created_at": folder.get("created_at"),
            "updated_at": folder.get("updated_at"),
        }

        # Only include sync_status for OFFLINE mode
        if self._has_column("sync_status"):
            result["sync_status"] = folder.get("sync_status")

        return result

    # =========================================================================
    # Core CRUD
    # =========================================================================

    async def get(self, folder_id: int) -> Optional[Dict[str, Any]]:
        """Get folder by ID."""
        async with self.db._get_async_connection() as conn:
            cursor = await conn.execute(
                f"SELECT * FROM {self._table('folders')} WHERE id = ?",
                (folder_id,)
            )
            row = await cursor.fetchone()
            return self._normalize_folder(dict(row)) if row else None

    async def get_all(self, project_id: int) -> List[Dict[str, Any]]:
        """Get all folders in a project."""
        async with self.db._get_async_connection() as conn:
            cursor = await conn.execute(
                f"SELECT * FROM {self._table('folders')} WHERE project_id = ? ORDER BY name",
                (project_id,)
            )
            rows = await cursor.fetchall()
            return [self._normalize_folder(dict(row)) for row in rows]

    async def create(
        self,
        name: str,
        project_id: int,
        parent_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Create a new folder."""
        # Generate unique name
        unique_name = await self.generate_unique_name(name, project_id, parent_id)

        # Use negative IDs for local folders
        folder_id = -int(time.time() * 1000) % 1000000000
        now = datetime.now().isoformat()

        async with self.db._get_async_connection() as conn:
            if self.schema_mode == SchemaMode.OFFLINE:
                await conn.execute(
                    f"""INSERT INTO {self._table('folders')}
                       (id, server_id, name, project_id, server_project_id, parent_id,
                        server_parent_id, created_at, updated_at, downloaded_at, sync_status)
                       VALUES (?, 0, ?, ?, ?, ?, ?, ?, ?, datetime('now'), 'local')""",
                    (
                        folder_id,
                        unique_name,
                        project_id,
                        project_id,
                        parent_id,
                        parent_id,
                        now,
                        now,
                    )
                )
            else:
                await conn.execute(
                    f"""INSERT INTO {self._table('folders')}
                       (id, name, project_id, parent_id, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (folder_id, unique_name, project_id, parent_id, now, now)
                )
            await conn.commit()

        logger.info(f"Created local folder: id={folder_id}, name='{unique_name}'")
        return await self.get(folder_id)

    async def delete(self, folder_id: int) -> bool:
        """Delete a folder and all its contents."""
        folder = await self.get(folder_id)
        if not folder:
            return False

        # Recursively delete all subfolders first
        await self._delete_folder_recursive(folder_id)

        async with self.db._get_async_connection() as conn:
            # Delete files in this folder
            await conn.execute(
                f"DELETE FROM {self._table('rows')} WHERE file_id IN (SELECT id FROM {self._table('files')} WHERE folder_id = ?)",
                (folder_id,)
            )
            await conn.execute(f"DELETE FROM {self._table('files')} WHERE folder_id = ?", (folder_id,))

            # Delete the folder
            await conn.execute(f"DELETE FROM {self._table('folders')} WHERE id = ?", (folder_id,))
            await conn.commit()

        logger.info(f"Deleted folder: id={folder_id}")
        return True

    async def _delete_folder_recursive(self, folder_id: int) -> None:
        """Recursively delete all subfolders."""
        async with self.db._get_async_connection() as conn:
            # Get subfolders
            cursor = await conn.execute(
                f"SELECT id FROM {self._table('folders')} WHERE parent_id = ?",
                (folder_id,)
            )
            rows = await cursor.fetchall()

            for row in rows:
                await self._delete_folder_recursive(row["id"])

                # Delete files in subfolder
                await conn.execute(
                    f"DELETE FROM {self._table('rows')} WHERE file_id IN (SELECT id FROM {self._table('files')} WHERE folder_id = ?)",
                    (row["id"],)
                )
                await conn.execute(f"DELETE FROM {self._table('files')} WHERE folder_id = ?", (row["id"],))

                # Delete subfolder
                await conn.execute(f"DELETE FROM {self._table('folders')} WHERE id = ?", (row["id"],))

            await conn.commit()

    # =========================================================================
    # Folder-Specific Operations
    # =========================================================================

    async def get_with_contents(self, folder_id: int) -> Optional[Dict[str, Any]]:
        """Get folder with its subfolders and files."""
        folder = await self.get(folder_id)
        if not folder:
            return None

        async with self.db._get_async_connection() as conn:
            # Get subfolders
            cursor = await conn.execute(
                f"SELECT id, name, created_at FROM {self._table('folders')} WHERE parent_id = ?",
                (folder_id,)
            )
            subfolder_rows = await cursor.fetchall()

            # Get files
            cursor = await conn.execute(
                f"SELECT id, name, format, row_count, created_at FROM {self._table('files')} WHERE folder_id = ?",
                (folder_id,)
            )
            file_rows = await cursor.fetchall()

        return {
            "id": folder["id"],
            "name": folder["name"],
            "project_id": folder["project_id"],
            "parent_id": folder["parent_id"],
            "subfolders": [
                {
                    "id": f["id"],
                    "name": f["name"],
                    "created_at": f["created_at"]
                }
                for f in subfolder_rows
            ],
            "files": [
                {
                    "id": f["id"],
                    "name": f["name"],
                    "format": f["format"],
                    "row_count": f["row_count"],
                    "created_at": f["created_at"]
                }
                for f in file_rows
            ]
        }

    async def rename(self, folder_id: int, new_name: str) -> Optional[Dict[str, Any]]:
        """Rename a folder."""
        folder = await self.get(folder_id)
        if not folder:
            return None

        # Check if name exists
        if await self.check_name_exists(
            new_name, folder["project_id"], folder["parent_id"], exclude_id=folder_id
        ):
            raise ValueError(
                f"A folder named '{new_name}' already exists in this location. "
                "Please use a different name."
            )

        old_name = folder["name"]

        async with self.db._get_async_connection() as conn:
            await conn.execute(
                f"UPDATE {self._table('folders')} SET name = ?, updated_at = datetime('now') WHERE id = ?",
                (new_name, folder_id)
            )
            await conn.commit()

        logger.info(f"Renamed folder: id={folder_id}, '{old_name}' -> '{new_name}'")
        return await self.get(folder_id)

    async def move(
        self,
        folder_id: int,
        parent_folder_id: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Move a folder to a different parent folder within same project."""
        folder = await self.get(folder_id)
        if not folder:
            return None

        # Prevent moving folder into itself
        if parent_folder_id == folder_id:
            raise ValueError("Cannot move folder into itself")

        # Validate target folder if specified
        if parent_folder_id is not None:
            target = await self.get(parent_folder_id)
            if not target or target["project_id"] != folder["project_id"]:
                raise ValueError("Target folder not found or invalid")

            # Check for circular reference
            if await self.is_descendant(parent_folder_id, folder_id):
                raise ValueError("Cannot move folder into its own subfolder")

        async with self.db._get_async_connection() as conn:
            await conn.execute(
                f"UPDATE {self._table('folders')} SET parent_id = ?, updated_at = datetime('now') WHERE id = ?",
                (parent_folder_id, folder_id)
            )
            await conn.commit()

        logger.info(f"Moved folder: id={folder_id}, new_parent={parent_folder_id}")
        return await self.get(folder_id)

    async def move_cross_project(
        self,
        folder_id: int,
        target_project_id: int,
        target_parent_id: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Move a folder to a different project."""
        folder = await self.get(folder_id)
        if not folder:
            return None

        # Validate target parent if specified
        if target_parent_id is not None:
            target = await self.get(target_parent_id)
            if not target or target["project_id"] != target_project_id:
                raise ValueError("Target parent folder not found")

        source_project_id = folder["project_id"]

        # DB-002: Auto-rename if needed
        new_name = await self.generate_unique_name(
            folder["name"], target_project_id, target_parent_id
        )

        async with self.db._get_async_connection() as conn:
            # Update the folder
            await conn.execute(
                f"""UPDATE {self._table('folders')}
                   SET name = ?, project_id = ?, parent_id = ?, updated_at = datetime('now')
                   WHERE id = ?""",
                (new_name, target_project_id, target_parent_id, folder_id)
            )
            await conn.commit()

        # Recursively update all subfolders and files
        await self._update_folder_project_recursive(folder_id, target_project_id)

        logger.info(
            f"Moved folder cross-project: id={folder_id}, "
            f"from project {source_project_id} to {target_project_id}"
        )

        result = await self.get(folder_id)
        result["new_name"] = new_name
        return result

    async def _update_folder_project_recursive(
        self,
        folder_id: int,
        new_project_id: int
    ) -> None:
        """Recursively update all subfolders and files to the new project."""
        async with self.db._get_async_connection() as conn:
            # Update all files in this folder
            await conn.execute(
                f"UPDATE {self._table('files')} SET project_id = ? WHERE folder_id = ?",
                (new_project_id, folder_id)
            )

            # Get subfolders and recursively update
            cursor = await conn.execute(
                f"SELECT id FROM {self._table('folders')} WHERE parent_id = ?",
                (folder_id,)
            )
            rows = await cursor.fetchall()

            for row in rows:
                await conn.execute(
                    f"UPDATE {self._table('folders')} SET project_id = ? WHERE id = ?",
                    (new_project_id, row["id"])
                )
                await self._update_folder_project_recursive(row["id"], new_project_id)

            await conn.commit()

    async def copy(
        self,
        folder_id: int,
        target_project_id: Optional[int] = None,
        target_parent_id: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Copy a folder and all its contents to a different location."""
        source_folder = await self.get(folder_id)
        if not source_folder:
            return None

        # Determine target project
        dest_project_id = target_project_id or source_folder["project_id"]

        # Generate unique name
        new_name = await self.generate_unique_name(
            source_folder["name"], dest_project_id, target_parent_id
        )

        # Create copy of folder
        new_folder_id = -int(time.time() * 1000) % 1000000000
        now = datetime.now().isoformat()

        async with self.db._get_async_connection() as conn:
            if self.schema_mode == SchemaMode.OFFLINE:
                await conn.execute(
                    f"""INSERT INTO {self._table('folders')}
                       (id, server_id, name, project_id, server_project_id, parent_id,
                        server_parent_id, created_at, updated_at, downloaded_at, sync_status)
                       VALUES (?, 0, ?, ?, ?, ?, ?, ?, ?, datetime('now'), 'local')""",
                    (
                        new_folder_id,
                        new_name,
                        dest_project_id,
                        dest_project_id,
                        target_parent_id,
                        target_parent_id,
                        now,
                        now,
                    )
                )
            else:
                await conn.execute(
                    f"""INSERT INTO {self._table('folders')}
                       (id, name, project_id, parent_id, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (new_folder_id, new_name, dest_project_id, target_parent_id, now, now)
                )
            await conn.commit()

        # Copy contents recursively
        files_copied = await self._copy_folder_contents(
            folder_id, new_folder_id, dest_project_id
        )

        logger.info(
            f"Copied folder: {source_folder['name']} -> {new_name}, "
            f"id={new_folder_id}, files={files_copied}"
        )

        return {
            "new_folder_id": new_folder_id,
            "name": new_name,
            "files_copied": files_copied
        }

    async def _copy_folder_contents(
        self,
        source_folder_id: int,
        dest_folder_id: int,
        dest_project_id: int
    ) -> int:
        """Copy all files and subfolders from source to destination."""
        files_copied = 0
        now = datetime.now().isoformat()

        async with self.db._get_async_connection() as conn:
            # Copy files
            cursor = await conn.execute(
                f"SELECT * FROM {self._table('files')} WHERE folder_id = ?",
                (source_folder_id,)
            )
            file_rows = await cursor.fetchall()

            for file in file_rows:
                # Generate unique name for each file
                file_name = await self._generate_unique_file_name(
                    file["name"], dest_project_id, dest_folder_id
                )

                # Generate new file ID
                new_file_id = -int(time.time() * 1000 + files_copied) % 1000000000

                if self.schema_mode == SchemaMode.OFFLINE:
                    await conn.execute(
                        f"""INSERT INTO {self._table('files')}
                           (id, server_id, name, original_filename, format, source_language,
                            target_language, row_count, project_id, server_project_id,
                            folder_id, server_folder_id, extra_data, created_at, updated_at,
                            downloaded_at, sync_status)
                           VALUES (?, 0, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), 'local')""",
                        (
                            new_file_id,
                            file_name,
                            file["original_filename"],
                            file["format"],
                            file["source_language"],
                            file["target_language"],
                            file["row_count"],
                            dest_project_id,
                            dest_project_id,
                            dest_folder_id,
                            dest_folder_id,
                            file["extra_data"],
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
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            new_file_id,
                            file_name,
                            file["original_filename"],
                            file["format"],
                            file["source_language"],
                            file["target_language"],
                            file["row_count"],
                            dest_project_id,
                            dest_folder_id,
                            file["extra_data"],
                            now,
                            now,
                        )
                    )

                # Copy rows
                cursor = await conn.execute(
                    f"SELECT * FROM {self._table('rows')} WHERE file_id = ?",
                    (file["id"],)
                )
                row_rows = await cursor.fetchall()

                for row in row_rows:
                    new_row_id = -int(time.time() * 1000) % 1000000000
                    if self.schema_mode == SchemaMode.OFFLINE:
                        await conn.execute(
                            f"""INSERT INTO {self._table('rows')}
                               (id, server_id, file_id, server_file_id, row_num, string_id,
                                source, target, memo, status, extra_data, created_at,
                                updated_at, downloaded_at, sync_status)
                               VALUES (?, 0, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), 'local')""",
                            (
                                new_row_id,
                                new_file_id,
                                new_file_id,
                                row["row_num"],
                                row["string_id"],
                                row["source"],
                                row["target"],
                                row["memo"],
                                row["status"],
                                row["extra_data"],
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
                                new_row_id,
                                new_file_id,
                                row["row_num"],
                                row["string_id"],
                                row["source"],
                                row["target"],
                                row["memo"],
                                row["status"],
                                row["extra_data"],
                                now,
                                now,
                            )
                        )

                files_copied += 1

            await conn.commit()

            # Copy subfolders recursively
            cursor = await conn.execute(
                f"SELECT * FROM {self._table('folders')} WHERE parent_id = ?",
                (source_folder_id,)
            )
            subfolder_rows = await cursor.fetchall()

        for subfolder in subfolder_rows:
            # Generate unique name
            sub_name = await self.generate_unique_name(
                subfolder["name"], dest_project_id, dest_folder_id
            )

            # Create subfolder
            new_subfolder_id = -int(time.time() * 1000) % 1000000000

            async with self.db._get_async_connection() as conn:
                if self.schema_mode == SchemaMode.OFFLINE:
                    await conn.execute(
                        f"""INSERT INTO {self._table('folders')}
                           (id, server_id, name, project_id, server_project_id, parent_id,
                            server_parent_id, created_at, updated_at, downloaded_at, sync_status)
                           VALUES (?, 0, ?, ?, ?, ?, ?, ?, ?, datetime('now'), 'local')""",
                        (
                            new_subfolder_id,
                            sub_name,
                            dest_project_id,
                            dest_project_id,
                            dest_folder_id,
                            dest_folder_id,
                            now,
                            now,
                        )
                    )
                else:
                    await conn.execute(
                        f"""INSERT INTO {self._table('folders')}
                           (id, name, project_id, parent_id, created_at, updated_at)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (new_subfolder_id, sub_name, dest_project_id, dest_folder_id, now, now)
                    )
                await conn.commit()

            # Recursively copy contents
            files_copied += await self._copy_folder_contents(
                subfolder["id"], new_subfolder_id, dest_project_id
            )

        return files_copied

    async def _generate_unique_file_name(
        self,
        base_name: str,
        project_id: int,
        folder_id: Optional[int]
    ) -> str:
        """Generate a unique file name in the folder."""
        counter = 0
        async with self.db._get_async_connection() as conn:
            while True:
                name = base_name if counter == 0 else f"{base_name}_{counter}"

                if folder_id is not None:
                    cursor = await conn.execute(
                        f"SELECT COUNT(*) as cnt FROM {self._table('files')} WHERE LOWER(name) = LOWER(?) AND folder_id = ?",
                        (name, folder_id)
                    )
                else:
                    cursor = await conn.execute(
                        f"SELECT COUNT(*) as cnt FROM {self._table('files')} WHERE LOWER(name) = LOWER(?) AND project_id = ? AND folder_id IS NULL",
                        (name, project_id)
                    )

                result = await cursor.fetchone()
                if result["cnt"] == 0:
                    return name
                counter += 1

    # =========================================================================
    # Query Operations
    # =========================================================================

    async def check_name_exists(
        self,
        name: str,
        project_id: int,
        parent_id: Optional[int] = None,
        exclude_id: Optional[int] = None
    ) -> bool:
        """Check if folder name exists in parent."""
        async with self.db._get_async_connection() as conn:
            if parent_id is None:
                query = f"""
                    SELECT COUNT(*) as cnt FROM {self._table('folders')}
                    WHERE LOWER(name) = LOWER(?) AND project_id = ? AND parent_id IS NULL
                """
                params = [name, project_id]
            else:
                query = f"""
                    SELECT COUNT(*) as cnt FROM {self._table('folders')}
                    WHERE LOWER(name) = LOWER(?) AND project_id = ? AND parent_id = ?
                """
                params = [name, project_id, parent_id]

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
        parent_id: Optional[int] = None
    ) -> str:
        """Generate a unique folder name."""
        if not await self.check_name_exists(base_name, project_id, parent_id):
            return base_name

        counter = 1
        while True:
            new_name = f"{base_name}_{counter}"
            if not await self.check_name_exists(new_name, project_id, parent_id):
                logger.info(f"Auto-renamed duplicate folder: '{base_name}' -> '{new_name}'")
                return new_name
            counter += 1

    async def get_children(self, folder_id: int) -> List[Dict[str, Any]]:
        """Get direct subfolders of a folder."""
        async with self.db._get_async_connection() as conn:
            cursor = await conn.execute(
                f"SELECT * FROM {self._table('folders')} WHERE parent_id = ? ORDER BY name",
                (folder_id,)
            )
            rows = await cursor.fetchall()
            return [self._normalize_folder(dict(row)) for row in rows]

    async def is_descendant(self, folder_id: int, potential_ancestor_id: int) -> bool:
        """Check if folder_id is a descendant of potential_ancestor_id."""
        async with self.db._get_async_connection() as conn:
            cursor = await conn.execute(
                f"SELECT parent_id FROM {self._table('folders')} WHERE id = ?",
                (folder_id,)
            )
            result = await cursor.fetchone()

            current_parent = result["parent_id"] if result else None

            while current_parent is not None:
                if current_parent == potential_ancestor_id:
                    return True
                cursor = await conn.execute(
                    f"SELECT parent_id FROM {self._table('folders')} WHERE id = ?",
                    (current_parent,)
                )
                result = await cursor.fetchone()
                current_parent = result["parent_id"] if result else None

            return False

    async def search(self, query: str) -> List[Dict[str, Any]]:
        """
        Search folders by name (case-insensitive partial match).

        P10-SEARCH: Used by Explorer Search for unified search across entities.
        """
        search_term = f"%{query}%"
        async with self.db._get_async_connection() as conn:
            cursor = await conn.execute(
                f"SELECT * FROM {self._table('folders')} WHERE name LIKE ? COLLATE NOCASE",
                (search_term,)
            )
            rows = await cursor.fetchall()

            return [self._normalize_folder(dict(row)) for row in rows]
