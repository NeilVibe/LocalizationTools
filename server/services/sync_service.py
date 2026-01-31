"""
Sync Service - Handles bidirectional sync between PostgreSQL and SQLite.

P10: This service bridges BOTH databases simultaneously for sync operations.
Unlike routes that use one repository (selected by factory), this service
explicitly works with both PostgreSQL (server) and SQLite (offline) data.

Usage:
    from server.services import SyncService

    sync_service = SyncService(pg_session, offline_db)
    await sync_service.sync_file_to_offline(file_id)
"""

from typing import Dict, List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from server.database.models import (
    LDMPlatform, LDMProject, LDMFolder, LDMFile, LDMRow,
    LDMTranslationMemory, LDMTMEntry
)


class SyncService:
    """
    Bidirectional sync service between PostgreSQL and SQLite.

    This service handles:
    - Downloading data from PostgreSQL to SQLite (sync to offline)
    - Uploading changes from SQLite to PostgreSQL (push to server)
    - Merge logic with last-write-wins conflict resolution
    """

    def __init__(self, pg_session: AsyncSession, offline_db):
        """
        Initialize SyncService with both database connections.

        Args:
            pg_session: SQLAlchemy async session for PostgreSQL
            offline_db: OfflineDatabase instance for SQLite
        """
        self.pg = pg_session
        self.sqlite = offline_db

    # =========================================================================
    # Model to Dict Converters
    # =========================================================================

    @staticmethod
    def _platform_to_dict(platform: LDMPlatform) -> Dict[str, Any]:
        """Convert SQLAlchemy Platform model to dict for SQLite storage."""
        return {
            "id": platform.id,
            "name": platform.name,
            "description": platform.description,
            "is_restricted": platform.is_restricted,
            "created_at": platform.created_at.isoformat() if platform.created_at else None,
            "updated_at": platform.updated_at.isoformat() if platform.updated_at else None
        }

    @staticmethod
    def _project_to_dict(project: LDMProject) -> Dict[str, Any]:
        """Convert SQLAlchemy Project model to dict for SQLite storage."""
        return {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "platform_id": project.platform_id,
            "is_restricted": project.is_restricted,
            "created_at": project.created_at.isoformat() if project.created_at else None,
            "updated_at": project.updated_at.isoformat() if project.updated_at else None
        }

    @staticmethod
    def _folder_to_dict(folder: LDMFolder) -> Dict[str, Any]:
        """Convert SQLAlchemy Folder model to dict for SQLite storage."""
        # Note: LDMFolder model has no updated_at column
        return {
            "id": folder.id,
            "name": folder.name,
            "project_id": folder.project_id,
            "parent_id": folder.parent_id,
            "created_at": folder.created_at.isoformat() if folder.created_at else None,
        }

    @staticmethod
    def _file_to_dict(file: LDMFile) -> Dict[str, Any]:
        """Convert SQLAlchemy File model to dict for SQLite storage."""
        return {
            "id": file.id,
            "name": file.name,
            "original_filename": file.original_filename,
            "format": file.format,
            "row_count": file.row_count,
            "source_language": file.source_language,
            "target_language": file.target_language,
            "project_id": file.project_id,
            "folder_id": file.folder_id,
            "extra_data": file.extra_data,
            "created_at": file.created_at.isoformat() if file.created_at else None,
            "updated_at": file.updated_at.isoformat() if file.updated_at else None
        }

    @staticmethod
    def _row_to_dict(row: LDMRow) -> Dict[str, Any]:
        """Convert SQLAlchemy Row model to dict for SQLite storage."""
        return {
            "id": row.id,
            "row_num": row.row_num,
            "string_id": row.string_id,
            "source": row.source,
            "target": row.target,
            "memo": row.memo if hasattr(row, 'memo') else None,
            "status": row.status,
            "extra_data": row.extra_data,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None
        }

    # =========================================================================
    # Sync to Offline (PostgreSQL → SQLite)
    # =========================================================================

    async def sync_folder_hierarchy(self, folder: LDMFolder) -> None:
        """
        Recursively sync folder hierarchy to offline storage.
        Syncs parent folders first, then the folder itself.
        """
        # If folder has a parent, sync parent first
        if folder.parent_id:
            parent_result = await self.pg.execute(
                select(LDMFolder).where(LDMFolder.id == folder.parent_id)
            )
            parent = parent_result.scalar_one_or_none()
            if parent:
                await self.sync_folder_hierarchy(parent)

        # Sync this folder
        await self.sqlite.save_folder(self._folder_to_dict(folder))
        logger.debug(f"[SYNC] Synced folder: {folder.name}")

    async def sync_file_to_offline(self, file_id: int) -> Dict[str, int]:
        """
        Sync a single file from PostgreSQL to SQLite.

        IMPORTANT: Server is source of truth for PATH (platform/project/folder).
        This function syncs the full path hierarchy before syncing file content.

        Merge Rules (last-write-wins):
        - Local synced + server newer → take server
        - Local modified + server newer → server wins, discard local
        - Local modified + local newer → keep local, push later
        - Server has row we don't → insert
        - We have row server deleted → delete local

        Returns:
            Dict with stats: inserted, updated, skipped, deleted, pushed
        """
        logger.info(f"[SYNC] sync_file_to_offline: file_id={file_id}")

        # Get file from PostgreSQL
        result = await self.pg.execute(select(LDMFile).where(LDMFile.id == file_id))
        file = result.scalar_one_or_none()
        if not file:
            raise ValueError(f"File {file_id} not found")

        # =====================================================================
        # SYNC PATH HIERARCHY (Server = Source of Truth for structure)
        # Order: Platform → Project → Folder → File
        # =====================================================================

        # 1. Get and sync Project (required)
        project_result = await self.pg.execute(
            select(LDMProject).where(LDMProject.id == file.project_id)
        )
        project = project_result.scalar_one_or_none()
        if project:
            # 2. Get and sync Platform (required for project)
            platform_result = await self.pg.execute(
                select(LDMPlatform).where(LDMPlatform.id == project.platform_id)
            )
            platform = platform_result.scalar_one_or_none()
            if platform:
                await self.sqlite.save_platform(self._platform_to_dict(platform))
                logger.debug(f"[SYNC] Synced platform: {platform.name}")

            # Save project
            await self.sqlite.save_project(self._project_to_dict(project))
            logger.debug(f"[SYNC] Synced project: {project.name}")

        # 3. Sync Folder hierarchy (if file is in a folder)
        if file.folder_id:
            folder_result = await self.pg.execute(
                select(LDMFolder).where(LDMFolder.id == file.folder_id)
            )
            folder = folder_result.scalar_one_or_none()
            if folder:
                await self.sync_folder_hierarchy(folder)

        # =====================================================================
        # SYNC FILE CONTENT
        # =====================================================================

        # Get server rows
        rows_result = await self.pg.execute(
            select(LDMRow).where(LDMRow.file_id == file_id).order_by(LDMRow.row_num)
        )
        server_rows = rows_result.scalars().all()

        # Save/update file metadata
        await self.sqlite.save_file(self._file_to_dict(file))

        # Convert server rows to dicts for batch processing
        server_row_data = [self._row_to_dict(row) for row in server_rows]
        server_row_ids = {row.id for row in server_rows}

        # Use BATCH merge - 100x faster than per-row merge
        stats = await self.sqlite.merge_rows_batch(server_row_data, file.id)
        stats["deleted"] = 0

        # Delete local rows that no longer exist on server
        local_row_ids = await self.sqlite.get_local_row_server_ids(file.id)
        deleted_ids = local_row_ids - server_row_ids
        for deleted_id in deleted_ids:
            await self.sqlite.delete_row(deleted_id)
            stats["deleted"] += 1

        # Push local changes to server
        pushed = await self.push_file_changes_to_server(file_id)
        stats["pushed"] = pushed

        logger.info(f"[SYNC] sync_file_to_offline complete: file={file.name}, "
                    f"inserted={stats['inserted']}, updated={stats['updated']}, "
                    f"skipped={stats['skipped']}, deleted={stats['deleted']}, pushed={pushed}")

        return stats

    async def sync_folder_to_offline(self, folder_id: int) -> Dict[str, Any]:
        """
        Sync a folder and all its contents to offline storage.

        Returns:
            Dict with stats: files_synced, total_rows
        """
        logger.info(f"[SYNC] sync_folder_to_offline: folder_id={folder_id}")

        # Get folder
        result = await self.pg.execute(select(LDMFolder).where(LDMFolder.id == folder_id))
        folder = result.scalar_one_or_none()
        if not folder:
            raise ValueError(f"Folder {folder_id} not found")

        # Sync project and platform (path hierarchy)
        project_result = await self.pg.execute(
            select(LDMProject).where(LDMProject.id == folder.project_id)
        )
        project = project_result.scalar_one_or_none()
        if project:
            platform_result = await self.pg.execute(
                select(LDMPlatform).where(LDMPlatform.id == project.platform_id)
            )
            platform = platform_result.scalar_one_or_none()
            if platform:
                await self.sqlite.save_platform(self._platform_to_dict(platform))
            await self.sqlite.save_project(self._project_to_dict(project))

        # Sync folder hierarchy
        await self.sync_folder_hierarchy(folder)

        # Sync all files in folder
        files_result = await self.pg.execute(
            select(LDMFile).where(LDMFile.folder_id == folder_id)
        )
        files = files_result.scalars().all()

        total_stats = {"files_synced": 0, "total_rows": 0}
        for file in files:
            stats = await self.sync_file_to_offline(file.id)
            total_stats["files_synced"] += 1
            total_stats["total_rows"] += stats.get("inserted", 0) + stats.get("updated", 0)

        # Sync subfolders recursively
        subfolders_result = await self.pg.execute(
            select(LDMFolder).where(LDMFolder.parent_id == folder_id)
        )
        subfolders = subfolders_result.scalars().all()
        for subfolder in subfolders:
            sub_stats = await self.sync_folder_to_offline(subfolder.id)
            total_stats["files_synced"] += sub_stats["files_synced"]
            total_stats["total_rows"] += sub_stats["total_rows"]

        logger.info(f"[SYNC] sync_folder_to_offline complete: folder={folder.name}, "
                    f"files={total_stats['files_synced']}, rows={total_stats['total_rows']}")

        return total_stats

    async def sync_project_to_offline(self, project_id: int) -> Dict[str, Any]:
        """
        Sync a project and all its contents to offline storage.

        Returns:
            Dict with stats: folders_synced, files_synced, total_rows
        """
        logger.info(f"[SYNC] sync_project_to_offline: project_id={project_id}")

        # Get project
        result = await self.pg.execute(select(LDMProject).where(LDMProject.id == project_id))
        project = result.scalar_one_or_none()
        if not project:
            raise ValueError(f"Project {project_id} not found")

        # Sync platform
        platform_result = await self.pg.execute(
            select(LDMPlatform).where(LDMPlatform.id == project.platform_id)
        )
        platform = platform_result.scalar_one_or_none()
        if platform:
            await self.sqlite.save_platform(self._platform_to_dict(platform))

        # Sync project
        await self.sqlite.save_project(self._project_to_dict(project))

        total_stats = {"folders_synced": 0, "files_synced": 0, "total_rows": 0}

        # Sync root folders (folders with no parent)
        folders_result = await self.pg.execute(
            select(LDMFolder).where(
                LDMFolder.project_id == project_id,
                LDMFolder.parent_id == None
            )
        )
        root_folders = folders_result.scalars().all()

        for folder in root_folders:
            stats = await self.sync_folder_to_offline(folder.id)
            total_stats["folders_synced"] += 1
            total_stats["files_synced"] += stats["files_synced"]
            total_stats["total_rows"] += stats["total_rows"]

        # Sync root files (files with no folder)
        files_result = await self.pg.execute(
            select(LDMFile).where(
                LDMFile.project_id == project_id,
                LDMFile.folder_id == None
            )
        )
        root_files = files_result.scalars().all()

        for file in root_files:
            stats = await self.sync_file_to_offline(file.id)
            total_stats["files_synced"] += 1
            total_stats["total_rows"] += stats.get("inserted", 0) + stats.get("updated", 0)

        logger.info(f"[SYNC] sync_project_to_offline complete: project={project.name}, "
                    f"folders={total_stats['folders_synced']}, files={total_stats['files_synced']}, "
                    f"rows={total_stats['total_rows']}")

        return total_stats

    async def sync_platform_to_offline(self, platform_id: int) -> Dict[str, Any]:
        """
        Sync a platform and all its projects to offline storage.

        Returns:
            Dict with stats: projects_synced, folders_synced, files_synced, total_rows
        """
        logger.info(f"[SYNC] sync_platform_to_offline: platform_id={platform_id}")

        # Get platform
        result = await self.pg.execute(select(LDMPlatform).where(LDMPlatform.id == platform_id))
        platform = result.scalar_one_or_none()
        if not platform:
            raise ValueError(f"Platform {platform_id} not found")

        # Sync platform
        await self.sqlite.save_platform(self._platform_to_dict(platform))

        total_stats = {"projects_synced": 0, "folders_synced": 0, "files_synced": 0, "total_rows": 0}

        # Sync all projects in platform
        projects_result = await self.pg.execute(
            select(LDMProject).where(LDMProject.platform_id == platform_id)
        )
        projects = projects_result.scalars().all()

        for project in projects:
            stats = await self.sync_project_to_offline(project.id)
            total_stats["projects_synced"] += 1
            total_stats["folders_synced"] += stats["folders_synced"]
            total_stats["files_synced"] += stats["files_synced"]
            total_stats["total_rows"] += stats["total_rows"]

        logger.info(f"[SYNC] sync_platform_to_offline complete: platform={platform.name}, "
                    f"projects={total_stats['projects_synced']}, files={total_stats['files_synced']}")

        return total_stats

    # =========================================================================
    # Push to Server (SQLite → PostgreSQL)
    # =========================================================================

    async def push_file_changes_to_server(self, file_id: int) -> int:
        """
        Push local changes for a file to the server.

        Returns:
            Number of rows pushed
        """
        pushed_count = 0

        # Get modified rows from SQLite
        modified_rows = await self.sqlite.get_modified_rows(file_id)

        for local_row in modified_rows:
            server_id = local_row.get("server_id")
            if not server_id:
                continue  # Skip rows without server mapping

            # Update server row
            result = await self.pg.execute(
                select(LDMRow).where(LDMRow.id == server_id)
            )
            server_row = result.scalar_one_or_none()

            if server_row:
                server_row.target = local_row.get("target")
                server_row.status = local_row.get("status")
                if hasattr(server_row, 'memo'):
                    server_row.memo = local_row.get("memo")

                pushed_count += 1

                # Mark local row as synced
                await self.sqlite.mark_row_synced(local_row["id"])

        if pushed_count > 0:
            await self.pg.commit()
            logger.info(f"[SYNC] Pushed {pushed_count} changes to server for file {file_id}")

        return pushed_count

    # =========================================================================
    # TM Sync Operations
    # =========================================================================

    async def sync_tm_to_offline(self, tm_id: int) -> Dict[str, int]:
        """
        Sync a Translation Memory from PostgreSQL to SQLite.

        Uses last-write-wins merge for entries.

        Returns:
            Dict with stats: inserted, updated, skipped
        """
        logger.info(f"[SYNC] sync_tm_to_offline: tm_id={tm_id}")

        # Get TM from PostgreSQL
        result = await self.pg.execute(
            select(LDMTranslationMemory).where(LDMTranslationMemory.id == tm_id)
        )
        tm = result.scalar_one_or_none()
        if not tm:
            raise ValueError(f"TM {tm_id} not found")

        # Save TM metadata to SQLite
        await self.sqlite.save_tm({
            "id": tm.id,
            "name": tm.name,
            "source_language": tm.source_lang,  # Model uses source_lang
            "target_language": tm.target_lang,  # Model uses target_lang
            "owner_id": tm.owner_id,
            "entry_count": tm.entry_count,
            "created_at": tm.created_at.isoformat() if tm.created_at else None,
            "updated_at": tm.updated_at.isoformat() if tm.updated_at else None
        })

        # Get all TM entries
        entries_result = await self.pg.execute(
            select(LDMTMEntry).where(LDMTMEntry.tm_id == tm_id)
        )
        entries = entries_result.scalars().all()

        # Merge entries using individual merge calls (last-write-wins)
        stats = {"inserted": 0, "updated": 0, "skipped": 0}
        for entry in entries:
            entry_data = {
                "id": entry.id,
                "tm_id": entry.tm_id,
                "source_text": entry.source_text if hasattr(entry, 'source_text') else entry.source,
                "target_text": entry.target_text if hasattr(entry, 'target_text') else entry.target,
                "source_hash": entry.source_hash if hasattr(entry, 'source_hash') else None,
                "created_at": entry.created_at.isoformat() if entry.created_at else None,
                "updated_at": entry.updated_at.isoformat() if entry.updated_at else None,
                "created_by": entry.created_by if hasattr(entry, 'created_by') else None,
            }
            result = await self.sqlite.merge_tm_entry(entry_data, tm.id)
            stats[result] += 1

        logger.info(f"[SYNC] sync_tm_to_offline complete: tm={tm.name}, "
                    f"inserted={stats['inserted']}, updated={stats['updated']}, skipped={stats['skipped']}")

        return stats

    async def push_tm_changes_to_server(self, local_tm_id: int, server_tm_id: int) -> int:
        """
        Push local TM changes to server.

        Args:
            local_tm_id: ID of TM in SQLite (may be negative for new TMs)
            server_tm_id: ID of TM in PostgreSQL

        Returns:
            Number of entries pushed
        """
        logger.info(f"[SYNC] push_tm_changes_to_server: local={local_tm_id}, server={server_tm_id}")

        # Get modified entries from SQLite
        modified_entries = await self.sqlite.get_modified_tm_entries(local_tm_id)
        pushed_count = 0

        for local_entry in modified_entries:
            server_id = local_entry.get("server_id")

            if server_id:
                # Update existing entry
                result = await self.pg.execute(
                    select(LDMTMEntry).where(LDMTMEntry.id == server_id)
                )
                server_entry = result.scalar_one_or_none()

                if server_entry:
                    server_entry.source = local_entry.get("source")
                    server_entry.target = local_entry.get("target")
                    pushed_count += 1
            else:
                # Create new entry
                new_entry = LDMTMEntry(
                    tm_id=server_tm_id,
                    source=local_entry.get("source"),
                    target=local_entry.get("target")
                )
                self.pg.add(new_entry)
                pushed_count += 1

            # Mark local entry as synced
            await self.sqlite.mark_tm_entry_synced(local_entry["id"])

        if pushed_count > 0:
            await self.pg.commit()

            # Update TM entry count
            result = await self.pg.execute(
                select(LDMTranslationMemory).where(LDMTranslationMemory.id == server_tm_id)
            )
            tm = result.scalar_one_or_none()
            if tm:
                entries_result = await self.pg.execute(
                    select(LDMTMEntry).where(LDMTMEntry.tm_id == server_tm_id)
                )
                tm.entry_count = len(entries_result.scalars().all())
                await self.pg.commit()

        logger.info(f"[SYNC] push_tm_changes_to_server complete: pushed={pushed_count}")

        return pushed_count

    # =========================================================================
    # Sync to Central (SQLite → PostgreSQL)
    # =========================================================================

    async def sync_file_to_central(
        self,
        local_file_id: int,
        destination_project_id: int,
        destination_folder_id: Optional[int],
        user_id: int
    ) -> Dict[str, Any]:
        """
        Sync a file from SQLite (Offline Storage) to PostgreSQL (central server).

        This creates a NEW file in PostgreSQL at the specified destination.
        Use this when:
        - User imported a file to Offline Storage
        - User wants to upload local work to a server project

        Args:
            local_file_id: ID of file in SQLite (negative for local-only files)
            destination_project_id: Target project ID in PostgreSQL
            destination_folder_id: Target folder ID in PostgreSQL (or None for project root)
            user_id: ID of user performing the sync

        Returns:
            Dict with new_file_id and rows_synced
        """
        import json
        logger.info(f"[SYNC] sync_file_to_central: local_file_id={local_file_id}, "
                    f"dest_project={destination_project_id}, dest_folder={destination_folder_id}")

        # Get local file from SQLite
        local_file = await self.sqlite.get_local_file(local_file_id)
        if not local_file:
            raise ValueError(f"File {local_file_id} not found in Offline Storage")

        # Get all rows for this file
        local_rows = await self.sqlite.get_rows_for_file(local_file_id)
        logger.info(f"[SYNC] Read {len(local_rows)} rows from Offline Storage")

        # Parse extra_data if it's a JSON string
        extra_data = local_file.get("extra_data")
        if extra_data and isinstance(extra_data, str):
            try:
                extra_data = json.loads(extra_data)
            except (json.JSONDecodeError, TypeError):
                extra_data = None

        # Create new file in PostgreSQL
        new_file = LDMFile(
            project_id=destination_project_id,
            folder_id=destination_folder_id,
            name=local_file.get("name", "unknown"),
            original_filename=local_file.get("original_filename") or local_file.get("name"),
            format=local_file.get("format", "txt"),
            row_count=len(local_rows),
            source_language=local_file.get("source_language"),
            target_language=local_file.get("target_language"),
            extra_data=extra_data,
            created_by=user_id
        )
        self.pg.add(new_file)
        await self.pg.flush()

        # Create rows in PostgreSQL
        for local_row in local_rows:
            # Parse extra_data for rows too
            row_extra = local_row.get("extra_data")
            if row_extra and isinstance(row_extra, str):
                try:
                    row_extra = json.loads(row_extra)
                except (json.JSONDecodeError, TypeError):
                    row_extra = None

            new_row = LDMRow(
                file_id=new_file.id,
                row_num=local_row.get("row_num", 0),
                string_id=local_row.get("string_id"),
                source=local_row.get("source"),
                target=local_row.get("target"),
                status=local_row.get("status", "pending"),
                extra_data=row_extra
            )
            self.pg.add(new_row)

        await self.pg.commit()

        logger.success(f"[SYNC] sync_file_to_central complete: local_id={local_file_id} → "
                      f"central_id={new_file.id}, rows={len(local_rows)}")

        return {
            "new_file_id": new_file.id,
            "rows_synced": len(local_rows)
        }

    async def sync_tm_to_central(self, local_tm_id: int, user_id: int) -> Dict[str, Any]:
        """
        Sync a Translation Memory from SQLite to PostgreSQL.

        This creates a NEW TM in PostgreSQL with all entries.
        The TM will need re-indexing on the server for semantic search.

        Args:
            local_tm_id: ID of TM in SQLite
            user_id: ID of user performing the sync

        Returns:
            Dict with new_tm_id and entries_synced
        """
        logger.info(f"[SYNC] sync_tm_to_central: local_tm_id={local_tm_id}")

        # Get local TM from SQLite
        local_tm = await self.sqlite.get_tm(local_tm_id)
        if not local_tm:
            raise ValueError(f"Translation Memory {local_tm_id} not found in local storage")

        # Get all entries for this TM
        local_entries = await self.sqlite.get_tm_entries(local_tm_id)
        logger.info(f"[SYNC] Read {len(local_entries)} entries from local SQLite")

        # Create new TM in PostgreSQL
        new_tm = LDMTranslationMemory(
            name=local_tm.get("name"),
            description=local_tm.get("description"),
            owner_id=user_id,
            source_lang=local_tm.get("source_lang"),
            target_lang=local_tm.get("target_lang"),
            entry_count=len(local_entries),
            status="pending"  # Will need re-indexing on server
        )
        self.pg.add(new_tm)
        await self.pg.flush()

        # Bulk insert entries to PostgreSQL
        for local_entry in local_entries:
            import hashlib
            source_text = local_entry.get("source_text", "")
            source_hash = hashlib.sha256(source_text.encode()).hexdigest()

            new_entry = LDMTMEntry(
                tm_id=new_tm.id,
                source_text=source_text,
                target_text=local_entry.get("target_text"),
                source_hash=source_hash,
                created_by=local_entry.get("created_by") or user_id,
                change_date=local_entry.get("change_date")
            )
            self.pg.add(new_entry)

        await self.pg.commit()

        logger.success(f"[SYNC] sync_tm_to_central complete: local_id={local_tm_id} → "
                      f"central_id={new_tm.id}, entries={len(local_entries)}")

        return {
            "new_tm_id": new_tm.id,
            "entries_synced": len(local_entries)
        }
