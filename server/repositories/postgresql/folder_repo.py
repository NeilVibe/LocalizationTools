"""
PostgreSQL Folder Repository Implementation.

P10: FULL ABSTRACT + REPO Pattern

Implements FolderRepository interface using SQLAlchemy async.
Permissions are baked INTO the repository.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from loguru import logger

from server.database.models import LDMFolder, LDMFile, LDMRow, LDMProject, LDMResourceAccess
from server.repositories.interfaces.folder_repository import FolderRepository


class PostgreSQLFolderRepository(FolderRepository):
    """
    PostgreSQL implementation of FolderRepository.

    P10: FULL ABSTRACT - Permissions are checked INSIDE the repository.
    """

    def __init__(self, db: AsyncSession, user: Optional[dict] = None):
        self.db = db
        self.user = user or {}

    def _is_admin(self) -> bool:
        return self.user.get("role") in ["admin", "superadmin"]

    async def _can_access_project(self, project_id: int) -> bool:
        """Check if current user can access project (folder's parent)."""
        if not self.user:
            return False
        if self._is_admin():
            return True

        user_id = self.user.get("user_id")
        if not user_id:
            return False

        result = await self.db.execute(
            select(LDMProject.is_restricted, LDMProject.owner_id)
            .where(LDMProject.id == project_id)
        )
        row = result.first()
        if not row:
            return False

        is_restricted, owner_id = row
        if owner_id == user_id:
            return True
        if not is_restricted:
            return True

        result = await self.db.execute(
            select(LDMResourceAccess.id)
            .where(
                LDMResourceAccess.project_id == project_id,
                LDMResourceAccess.user_id == user_id
            )
        )
        return result.first() is not None

    def _folder_to_dict(self, folder: LDMFolder) -> Dict[str, Any]:
        """Convert SQLAlchemy folder to dict."""
        return {
            "id": folder.id,
            "name": folder.name,
            "project_id": folder.project_id,
            "parent_id": folder.parent_id,
            "created_at": folder.created_at.isoformat() if folder.created_at else None,
        }

    # =========================================================================
    # Core CRUD
    # =========================================================================

    async def get(self, folder_id: int) -> Optional[Dict[str, Any]]:
        """
        Get folder by ID with permission check.

        P10: FULL ABSTRACT - Permission check baked in. Returns None if user lacks access.
        """
        result = await self.db.execute(
            select(LDMFolder).where(LDMFolder.id == folder_id)
        )
        folder = result.scalar_one_or_none()
        if not folder:
            return None

        # P10: Check permission via project access
        if not await self._can_access_project(folder.project_id):
            logger.debug(f"[FOLDER_REPO] Access denied: user {self.user.get('user_id')} cannot access folder {folder_id}")
            return None

        return self._folder_to_dict(folder)

    async def get_all(self, project_id: int) -> List[Dict[str, Any]]:
        """
        Get all folders in a project with permission check.

        P10: FULL ABSTRACT - Permission check baked in. Returns empty list if no access.
        """
        # P10: Check project access first
        if not await self._can_access_project(project_id):
            logger.debug(f"[FOLDER_REPO] Access denied: user {self.user.get('user_id')} cannot access project {project_id}")
            return []

        result = await self.db.execute(
            select(LDMFolder)
            .where(LDMFolder.project_id == project_id)
            .order_by(LDMFolder.name)
        )
        folders = result.scalars().all()
        return [self._folder_to_dict(f) for f in folders]

    async def create(
        self,
        name: str,
        project_id: int,
        parent_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Create a new folder."""
        # DB-002: Generate unique name
        unique_name = await self.generate_unique_name(name, project_id, parent_id)

        folder = LDMFolder(
            name=unique_name,
            project_id=project_id,
            parent_id=parent_id
        )
        self.db.add(folder)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(folder)

        logger.info(f"Created folder: id={folder.id}, name='{unique_name}'")
        return self._folder_to_dict(folder)

    async def delete(self, folder_id: int) -> bool:
        """Delete a folder and all its contents."""
        result = await self.db.execute(
            select(LDMFolder).where(LDMFolder.id == folder_id)
        )
        folder = result.scalar_one_or_none()

        if not folder:
            return False

        # SQLAlchemy cascade should handle subfolders and files
        await self.db.delete(folder)
        await self.db.commit()

        logger.info(f"Deleted folder: id={folder_id}")
        return True

    # =========================================================================
    # Folder-Specific Operations
    # =========================================================================

    async def get_with_contents(self, folder_id: int) -> Optional[Dict[str, Any]]:
        """
        Get folder with its subfolders and files.

        P10: FULL ABSTRACT - Permission check baked in. Returns None if user lacks access.
        """
        # Get folder
        result = await self.db.execute(
            select(LDMFolder).where(LDMFolder.id == folder_id)
        )
        folder = result.scalar_one_or_none()

        if not folder:
            return None

        # P10: Check permission via project access
        if not await self._can_access_project(folder.project_id):
            logger.debug(f"[FOLDER_REPO] Access denied for get_with_contents: folder_id={folder_id}")
            return None

        # Get subfolders
        result = await self.db.execute(
            select(LDMFolder).where(LDMFolder.parent_id == folder_id)
        )
        subfolders = result.scalars().all()

        # Get files
        result = await self.db.execute(
            select(LDMFile).where(LDMFile.folder_id == folder_id)
        )
        files = result.scalars().all()

        return {
            "id": folder.id,
            "name": folder.name,
            "project_id": folder.project_id,
            "parent_id": folder.parent_id,
            "subfolders": [
                {
                    "id": f.id,
                    "name": f.name,
                    "created_at": f.created_at.isoformat() if f.created_at else None
                }
                for f in subfolders
            ],
            "files": [
                {
                    "id": f.id,
                    "name": f.name,
                    "format": f.format,
                    "row_count": f.row_count,
                    "created_at": f.created_at.isoformat() if f.created_at else None
                }
                for f in files
            ]
        }

    async def rename(self, folder_id: int, new_name: str) -> Optional[Dict[str, Any]]:
        """Rename a folder."""
        result = await self.db.execute(
            select(LDMFolder).where(LDMFolder.id == folder_id)
        )
        folder = result.scalar_one_or_none()

        if not folder:
            return None

        # Check if name exists
        if await self.check_name_exists(
            new_name, folder.project_id, folder.parent_id, exclude_id=folder_id
        ):
            raise ValueError(
                f"A folder named '{new_name}' already exists in this location. "
                "Please use a different name."
            )

        old_name = folder.name
        folder.name = new_name

        await self.db.commit()
        await self.db.refresh(folder)

        logger.info(f"Renamed folder: id={folder_id}, '{old_name}' -> '{new_name}'")
        return self._folder_to_dict(folder)

    async def move(
        self,
        folder_id: int,
        parent_folder_id: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Move a folder to a different parent folder within same project."""
        result = await self.db.execute(
            select(LDMFolder).where(LDMFolder.id == folder_id)
        )
        folder = result.scalar_one_or_none()

        if not folder:
            return None

        # Prevent moving folder into itself
        if parent_folder_id == folder_id:
            raise ValueError("Cannot move folder into itself")

        # Validate target folder if specified
        if parent_folder_id is not None:
            result = await self.db.execute(
                select(LDMFolder).where(
                    LDMFolder.id == parent_folder_id,
                    LDMFolder.project_id == folder.project_id
                )
            )
            target_folder = result.scalar_one_or_none()
            if not target_folder:
                raise ValueError("Target folder not found or invalid")

            # Check for circular reference
            if await self.is_descendant(parent_folder_id, folder_id):
                raise ValueError("Cannot move folder into its own subfolder")

        folder.parent_id = parent_folder_id

        await self.db.commit()
        await self.db.refresh(folder)

        logger.info(f"Moved folder: id={folder_id}, new_parent={parent_folder_id}")
        return self._folder_to_dict(folder)

    async def move_cross_project(
        self,
        folder_id: int,
        target_project_id: int,
        target_parent_id: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Move a folder to a different project.

        P10: Permission checks baked in - checks access to source folder AND target project.
        Note: Capability check (cross_project_move) is done at route level.
        """
        result = await self.db.execute(
            select(LDMFolder).where(LDMFolder.id == folder_id)
        )
        folder = result.scalar_one_or_none()

        if not folder:
            return None

        # P10: Check access to source folder's project
        if not await self._can_access_project(folder.project_id):
            raise PermissionError(f"Cannot access source folder {folder_id}")

        # P10: Check access to target project
        if not await self._can_access_project(target_project_id):
            raise PermissionError(f"Cannot access target project {target_project_id}")

        # Validate target parent if specified
        if target_parent_id is not None:
            result = await self.db.execute(
                select(LDMFolder).where(
                    LDMFolder.id == target_parent_id,
                    LDMFolder.project_id == target_project_id
                )
            )
            if not result.scalar_one_or_none():
                raise ValueError("Target parent folder not found")

        source_project_id = folder.project_id

        # DB-002: Auto-rename if needed
        new_name = await self.generate_unique_name(
            folder.name, target_project_id, target_parent_id
        )

        # Update the folder
        folder.name = new_name
        folder.project_id = target_project_id
        folder.parent_id = target_parent_id

        # Recursively update all subfolders and files
        await self._update_folder_project_recursive(folder_id, target_project_id)

        await self.db.commit()
        await self.db.refresh(folder)

        logger.info(
            f"Moved folder cross-project: id={folder_id}, "
            f"from project {source_project_id} to {target_project_id}"
        )
        return {
            **self._folder_to_dict(folder),
            "new_name": new_name
        }

    async def _update_folder_project_recursive(
        self,
        folder_id: int,
        new_project_id: int
    ) -> None:
        """Recursively update all subfolders and files to the new project."""
        # Update all files in this folder
        result = await self.db.execute(
            select(LDMFile).where(LDMFile.folder_id == folder_id)
        )
        files = result.scalars().all()
        for file in files:
            file.project_id = new_project_id

        # Get subfolders and recursively update
        result = await self.db.execute(
            select(LDMFolder).where(LDMFolder.parent_id == folder_id)
        )
        subfolders = result.scalars().all()
        for subfolder in subfolders:
            subfolder.project_id = new_project_id
            await self._update_folder_project_recursive(subfolder.id, new_project_id)

    async def copy(
        self,
        folder_id: int,
        target_project_id: Optional[int] = None,
        target_parent_id: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Copy a folder and all its contents to a different location."""
        result = await self.db.execute(
            select(LDMFolder).where(LDMFolder.id == folder_id)
        )
        source_folder = result.scalar_one_or_none()

        if not source_folder:
            return None

        # Determine target project
        dest_project_id = target_project_id or source_folder.project_id

        # Generate unique name
        new_name = await self.generate_unique_name(
            source_folder.name, dest_project_id, target_parent_id
        )

        # Create copy of folder
        new_folder = LDMFolder(
            name=new_name,
            project_id=dest_project_id,
            parent_id=target_parent_id
        )
        self.db.add(new_folder)
        await self.db.flush()

        # Copy contents recursively
        files_copied = await self._copy_folder_contents(
            folder_id, new_folder.id, dest_project_id
        )

        await self.db.commit()
        await self.db.refresh(new_folder)

        logger.info(
            f"Copied folder: {source_folder.name} -> {new_name}, "
            f"id={new_folder.id}, files={files_copied}"
        )
        return {
            "new_folder_id": new_folder.id,
            "name": new_folder.name,
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

        # Copy files
        result = await self.db.execute(
            select(LDMFile).where(LDMFile.folder_id == source_folder_id)
        )
        files = result.scalars().all()

        for file in files:
            # Generate unique name for each file
            from server.tools.ldm.utils.naming import generate_unique_name
            file_name = await generate_unique_name(
                self.db, LDMFile, file.name,
                project_id=dest_project_id,
                folder_id=dest_folder_id
            )

            new_file = LDMFile(
                name=file_name,
                original_filename=file.original_filename,
                format=file.format,
                source_language=file.source_language,
                target_language=file.target_language,
                row_count=file.row_count,
                project_id=dest_project_id,
                folder_id=dest_folder_id,
                extra_data=file.extra_data
            )
            self.db.add(new_file)
            await self.db.flush()

            # Copy rows
            result = await self.db.execute(
                select(LDMRow).where(LDMRow.file_id == file.id)
            )
            rows = result.scalars().all()
            for row in rows:
                new_row = LDMRow(
                    file_id=new_file.id,
                    row_num=row.row_num,
                    string_id=row.string_id,
                    source=row.source,
                    target=row.target,
                    status=row.status,
                    extra_data=row.extra_data
                )
                self.db.add(new_row)

            files_copied += 1

        # Copy subfolders recursively
        result = await self.db.execute(
            select(LDMFolder).where(LDMFolder.parent_id == source_folder_id)
        )
        subfolders = result.scalars().all()

        for subfolder in subfolders:
            # Generate unique name
            sub_name = await self.generate_unique_name(
                subfolder.name, dest_project_id, dest_folder_id
            )

            new_subfolder = LDMFolder(
                name=sub_name,
                project_id=dest_project_id,
                parent_id=dest_folder_id
            )
            self.db.add(new_subfolder)
            await self.db.flush()

            # Recursively copy contents
            files_copied += await self._copy_folder_contents(
                subfolder.id, new_subfolder.id, dest_project_id
            )

        return files_copied

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
        query = select(func.count(LDMFolder.id)).where(
            func.lower(LDMFolder.name) == func.lower(name),
            LDMFolder.project_id == project_id
        )

        if parent_id is not None:
            query = query.where(LDMFolder.parent_id == parent_id)
        else:
            query = query.where(LDMFolder.parent_id.is_(None))

        if exclude_id is not None:
            query = query.where(LDMFolder.id != exclude_id)

        result = await self.db.execute(query)
        count = result.scalar() or 0
        return count > 0

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
        result = await self.db.execute(
            select(LDMFolder)
            .where(LDMFolder.parent_id == folder_id)
            .order_by(LDMFolder.name)
        )
        folders = result.scalars().all()
        return [self._folder_to_dict(f) for f in folders]

    async def is_descendant(self, folder_id: int, potential_ancestor_id: int) -> bool:
        """Check if folder_id is a descendant of potential_ancestor_id."""
        result = await self.db.execute(
            select(LDMFolder.parent_id).where(LDMFolder.id == folder_id)
        )
        current_parent = result.scalar_one_or_none()

        while current_parent is not None:
            if current_parent == potential_ancestor_id:
                return True
            result = await self.db.execute(
                select(LDMFolder.parent_id).where(LDMFolder.id == current_parent)
            )
            current_parent = result.scalar_one_or_none()

        return False

    async def search(self, query: str) -> List[Dict[str, Any]]:
        """
        Search folders by name (case-insensitive partial match).

        P10-SEARCH: Used by Explorer Search for unified search across entities.
        """
        search_term = f"%{query.lower()}%"
        result = await self.db.execute(
            select(LDMFolder).where(LDMFolder.name.ilike(search_term))
        )
        folders = result.scalars().all()

        return [self._folder_to_dict(f) for f in folders]
