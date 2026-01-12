"""
PostgreSQL File Repository.

Implements FileRepository interface using SQLAlchemy async operations.
This is the online mode adapter.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from loguru import logger

from server.repositories.interfaces.file_repository import FileRepository
from server.database.models import LDMFile, LDMRow, LDMProject, LDMFolder


class PostgreSQLFileRepository(FileRepository):
    """
    PostgreSQL implementation of FileRepository.

    Uses SQLAlchemy async session for all operations.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _file_to_dict(self, file: LDMFile, project: Optional[LDMProject] = None) -> Dict[str, Any]:
        """Convert LDMFile model to dict."""
        result = {
            "id": file.id,
            "name": file.name,
            "original_filename": file.original_filename,
            "format": file.format,
            "row_count": file.row_count or 0,
            "source_language": file.source_language,
            "target_language": file.target_language,
            "project_id": file.project_id,
            "folder_id": file.folder_id,
            "extra_data": file.extra_data,
            "created_at": file.created_at.isoformat() if file.created_at else None,
            "updated_at": file.updated_at.isoformat() if file.updated_at else None,
        }

        if project:
            result["project_name"] = project.name

        return result

    def _row_to_dict(self, row: LDMRow) -> Dict[str, Any]:
        """Convert LDMRow model to dict."""
        return {
            "id": row.id,
            "file_id": row.file_id,
            "row_num": row.row_num,
            "string_id": row.string_id,
            "source": row.source,
            "target": row.target,
            "status": row.status,
            "extra_data": row.extra_data,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }

    # =========================================================================
    # Core CRUD
    # =========================================================================

    async def get(self, file_id: int) -> Optional[Dict[str, Any]]:
        result = await self.db.execute(
            select(LDMFile).where(LDMFile.id == file_id)
        )
        file = result.scalar_one_or_none()
        return self._file_to_dict(file) if file else None

    async def get_all(
        self,
        project_id: Optional[int] = None,
        folder_id: Optional[int] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        query = select(LDMFile)

        if project_id is not None:
            query = query.where(LDMFile.project_id == project_id)
        if folder_id is not None:
            query = query.where(LDMFile.folder_id == folder_id)

        query = query.order_by(LDMFile.name).offset(offset).limit(limit)

        result = await self.db.execute(query)
        files = result.scalars().all()

        return [self._file_to_dict(f) for f in files]

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
        file = LDMFile(
            name=name,
            original_filename=original_filename,
            format=format,
            project_id=project_id,
            folder_id=folder_id,
            source_language=source_language,
            target_language=target_language,
            extra_data=extra_data,
            row_count=0
        )
        self.db.add(file)
        await self.db.flush()
        await self.db.commit()
        logger.info(f"Created file: {name} (id={file.id})")
        return self._file_to_dict(file)

    async def delete(self, file_id: int, permanent: bool = False) -> bool:
        result = await self.db.execute(
            select(LDMFile).where(LDMFile.id == file_id)
        )
        file = result.scalar_one_or_none()
        if not file:
            return False

        if permanent:
            # Delete rows first
            await self.db.execute(
                LDMRow.__table__.delete().where(LDMRow.file_id == file_id)
            )
            # Delete file
            await self.db.delete(file)
            logger.info(f"Permanently deleted file: {file.name} (id={file_id})")
        else:
            # Soft delete - move to trash (handled by trash repository)
            # For now, mark as deleted or use trash service
            await self.db.delete(file)
            logger.info(f"Deleted file: {file.name} (id={file_id})")

        await self.db.commit()
        return True

    # =========================================================================
    # File Operations
    # =========================================================================

    async def rename(self, file_id: int, new_name: str) -> Dict[str, Any]:
        result = await self.db.execute(
            select(LDMFile).where(LDMFile.id == file_id)
        )
        file = result.scalar_one_or_none()
        if not file:
            raise ValueError(f"File {file_id} not found")

        # Check uniqueness
        if await self.check_name_exists(new_name, file.project_id, file.folder_id, exclude_id=file_id):
            raise ValueError(f"Name '{new_name}' already exists in this folder")

        file.name = new_name
        file.updated_at = datetime.utcnow()
        await self.db.commit()
        logger.info(f"Renamed file {file_id} to '{new_name}'")
        return self._file_to_dict(file)

    async def move(
        self,
        file_id: int,
        target_folder_id: Optional[int] = None
    ) -> Dict[str, Any]:
        result = await self.db.execute(
            select(LDMFile).where(LDMFile.id == file_id)
        )
        file = result.scalar_one_or_none()
        if not file:
            raise ValueError(f"File {file_id} not found")

        # Validate target folder exists and is in same project
        if target_folder_id is not None:
            result = await self.db.execute(
                select(LDMFolder).where(
                    and_(
                        LDMFolder.id == target_folder_id,
                        LDMFolder.project_id == file.project_id
                    )
                )
            )
            if not result.scalar_one_or_none():
                raise ValueError("Target folder not found or not in same project")

        # Check for name conflicts
        if await self.check_name_exists(file.name, file.project_id, target_folder_id, exclude_id=file_id):
            raise ValueError(f"Name '{file.name}' already exists in target folder")

        file.folder_id = target_folder_id
        file.updated_at = datetime.utcnow()
        await self.db.commit()
        logger.info(f"Moved file {file_id} to folder {target_folder_id}")
        return self._file_to_dict(file)

    async def move_cross_project(
        self,
        file_id: int,
        target_project_id: int,
        target_folder_id: Optional[int] = None
    ) -> Dict[str, Any]:
        result = await self.db.execute(
            select(LDMFile).where(LDMFile.id == file_id)
        )
        file = result.scalar_one_or_none()
        if not file:
            raise ValueError(f"File {file_id} not found")

        # Validate target project
        result = await self.db.execute(
            select(LDMProject).where(LDMProject.id == target_project_id)
        )
        if not result.scalar_one_or_none():
            raise ValueError("Target project not found")

        # Validate target folder if specified
        if target_folder_id is not None:
            result = await self.db.execute(
                select(LDMFolder).where(
                    and_(
                        LDMFolder.id == target_folder_id,
                        LDMFolder.project_id == target_project_id
                    )
                )
            )
            if not result.scalar_one_or_none():
                raise ValueError("Target folder not found or not in target project")

        # Auto-rename if name conflict
        new_name = await self.generate_unique_name(file.name, target_project_id, target_folder_id)

        file.name = new_name
        file.project_id = target_project_id
        file.folder_id = target_folder_id
        file.updated_at = datetime.utcnow()
        await self.db.commit()
        logger.info(f"Moved file {file_id} to project {target_project_id}, folder {target_folder_id}")
        return self._file_to_dict(file)

    async def copy(
        self,
        file_id: int,
        target_project_id: Optional[int] = None,
        target_folder_id: Optional[int] = None
    ) -> Dict[str, Any]:
        # Get source file
        result = await self.db.execute(
            select(LDMFile).where(LDMFile.id == file_id)
        )
        source_file = result.scalar_one_or_none()
        if not source_file:
            raise ValueError(f"File {file_id} not found")

        # Determine target location
        dest_project_id = target_project_id or source_file.project_id
        dest_folder_id = target_folder_id

        # Generate unique name
        new_name = await self.generate_unique_name(source_file.name, dest_project_id, dest_folder_id)

        # Create new file
        new_file = LDMFile(
            name=new_name,
            original_filename=source_file.original_filename,
            format=source_file.format,
            project_id=dest_project_id,
            folder_id=dest_folder_id,
            source_language=source_file.source_language,
            target_language=source_file.target_language,
            extra_data=source_file.extra_data,
            row_count=source_file.row_count
        )
        self.db.add(new_file)
        await self.db.flush()

        # Copy all rows
        result = await self.db.execute(
            select(LDMRow).where(LDMRow.file_id == file_id).order_by(LDMRow.row_num)
        )
        source_rows = result.scalars().all()

        for row in source_rows:
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

        await self.db.commit()
        logger.info(f"Copied file {file_id} to new file {new_file.id}")
        return self._file_to_dict(new_file)

    async def update_row_count(self, file_id: int, count: int) -> None:
        result = await self.db.execute(
            select(LDMFile).where(LDMFile.id == file_id)
        )
        file = result.scalar_one_or_none()
        if file:
            file.row_count = count
            file.updated_at = datetime.utcnow()
            await self.db.commit()

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
        query = select(LDMRow).where(LDMRow.file_id == file_id)

        if status_filter:
            query = query.where(LDMRow.status == status_filter)

        query = query.order_by(LDMRow.row_num).offset(offset).limit(limit)

        result = await self.db.execute(query)
        rows = result.scalars().all()

        return [self._row_to_dict(r) for r in rows]

    async def add_rows(
        self,
        file_id: int,
        rows: List[Dict[str, Any]]
    ) -> int:
        for row_data in rows:
            row = LDMRow(
                file_id=file_id,
                row_num=row_data.get("row_num", 0),
                string_id=row_data.get("string_id"),
                source=row_data.get("source", ""),
                target=row_data.get("target", ""),
                status=row_data.get("status", "normal"),
                extra_data=row_data.get("extra_data")
            )
            self.db.add(row)

        await self.db.flush()
        await self.update_row_count(file_id, len(rows))
        await self.db.commit()
        logger.info(f"Added {len(rows)} rows to file {file_id}")
        return len(rows)

    async def get_rows_for_export(
        self,
        file_id: int,
        status_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        query = select(LDMRow).where(LDMRow.file_id == file_id)

        if status_filter:
            query = query.where(LDMRow.status == status_filter)

        query = query.order_by(LDMRow.row_num)

        result = await self.db.execute(query)
        rows = result.scalars().all()

        return [self._row_to_dict(r) for r in rows]

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
        query = select(func.count()).select_from(LDMFile).where(
            and_(
                LDMFile.name == name,
                LDMFile.project_id == project_id
            )
        )

        if folder_id is not None:
            query = query.where(LDMFile.folder_id == folder_id)
        else:
            query = query.where(LDMFile.folder_id.is_(None))

        if exclude_id is not None:
            query = query.where(LDMFile.id != exclude_id)

        result = await self.db.execute(query)
        count = result.scalar()
        return count > 0

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
        result = await self.db.execute(
            select(LDMFile, LDMProject).join(
                LDMProject, LDMFile.project_id == LDMProject.id
            ).where(LDMFile.id == file_id)
        )
        row = result.first()
        if not row:
            return None

        file, project = row
        return self._file_to_dict(file, project)

    async def search(self, query: str) -> List[Dict[str, Any]]:
        """
        Search files by name (case-insensitive partial match).

        P10-SEARCH: Used by Explorer Search for unified search across entities.
        """
        search_term = f"%{query.lower()}%"
        result = await self.db.execute(
            select(LDMFile).where(LDMFile.name.ilike(search_term))
        )
        files = result.scalars().all()

        return [self._file_to_dict(f) for f in files]
