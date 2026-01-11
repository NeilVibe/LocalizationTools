"""
PostgreSQL TM Repository.

Implements TMRepository interface using SQLAlchemy async operations.
This is the online mode adapter.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, delete
from sqlalchemy.orm import selectinload
from loguru import logger

from server.repositories.interfaces.tm_repository import TMRepository, AssignmentTarget
from server.database.models import (
    LDMTranslationMemory, LDMTMAssignment, LDMTMEntry,
    LDMPlatform, LDMProject, LDMFolder, LDMFile
)


# Constants
OFFLINE_STORAGE_PLATFORM_NAME = "Offline Storage"
OFFLINE_STORAGE_PROJECT_NAME = "Offline Storage"


class PostgreSQLTMRepository(TMRepository):
    """
    PostgreSQL implementation of TMRepository.

    Uses SQLAlchemy async session for all operations.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _tm_to_dict(self, tm: LDMTranslationMemory, assignment: Optional[LDMTMAssignment] = None) -> Dict[str, Any]:
        """Convert TM model to dict."""
        result = {
            "id": tm.id,
            "name": tm.name,
            "description": tm.description,
            "source_lang": tm.source_lang,
            "target_lang": tm.target_lang,
            "entry_count": tm.entry_count or 0,
            "status": tm.status,
            "mode": tm.mode,
            "owner_id": tm.owner_id,
            "created_at": tm.created_at.isoformat() if tm.created_at else None,
            "updated_at": tm.updated_at.isoformat() if tm.updated_at else None,
        }

        if assignment:
            result.update({
                "assignment_id": assignment.id,
                "platform_id": assignment.platform_id,
                "project_id": assignment.project_id,
                "folder_id": assignment.folder_id,
                "is_active": assignment.is_active,
                "priority": assignment.priority,
            })

        return result

    def _entry_to_dict(self, entry: LDMTMEntry) -> Dict[str, Any]:
        """Convert TM entry model to dict."""
        return {
            "id": entry.id,
            "tm_id": entry.tm_id,
            "source_text": entry.source_text,
            "target_text": entry.target_text,
            "source_hash": entry.source_hash,
            "string_id": entry.string_id,
            "created_by": entry.created_by,
            "change_date": entry.change_date.isoformat() if entry.change_date else None,
            "is_confirmed": entry.is_confirmed,
        }

    async def _ensure_offline_storage_platform(self) -> LDMPlatform:
        """Ensure Offline Storage platform exists."""
        result = await self.db.execute(
            select(LDMPlatform).where(LDMPlatform.name == OFFLINE_STORAGE_PLATFORM_NAME)
        )
        platform = result.scalar_one_or_none()

        if not platform:
            platform = LDMPlatform(
                name=OFFLINE_STORAGE_PLATFORM_NAME,
                description="Local files stored offline for translation",
                owner_id=1,
                is_restricted=False
            )
            self.db.add(platform)
            await self.db.flush()
            logger.info(f"Created Offline Storage platform (id={platform.id})")

        return platform

    async def _ensure_offline_storage_project(self) -> LDMProject:
        """Ensure Offline Storage project exists."""
        platform = await self._ensure_offline_storage_platform()

        result = await self.db.execute(
            select(LDMProject).where(
                and_(
                    LDMProject.platform_id == platform.id,
                    LDMProject.name == OFFLINE_STORAGE_PROJECT_NAME
                )
            )
        )
        project = result.scalar_one_or_none()

        if not project:
            project = LDMProject(
                name=OFFLINE_STORAGE_PROJECT_NAME,
                description="Local files stored offline",
                platform_id=platform.id,
                owner_id=1,
                is_restricted=False
            )
            self.db.add(project)
            await self.db.flush()
            logger.info(f"Created Offline Storage project (id={project.id})")

        return project

    # =========================================================================
    # Core CRUD
    # =========================================================================

    async def get(self, tm_id: int) -> Optional[Dict[str, Any]]:
        result = await self.db.execute(
            select(LDMTranslationMemory).where(LDMTranslationMemory.id == tm_id)
        )
        tm = result.scalar_one_or_none()
        if not tm:
            return None

        # Get assignment
        result = await self.db.execute(
            select(LDMTMAssignment).where(LDMTMAssignment.tm_id == tm_id)
        )
        assignment = result.scalar_one_or_none()

        return self._tm_to_dict(tm, assignment)

    async def get_all(self) -> List[Dict[str, Any]]:
        result = await self.db.execute(
            select(LDMTranslationMemory).order_by(LDMTranslationMemory.name)
        )
        tms = result.scalars().all()

        # Get all assignments in one query
        tm_ids = [tm.id for tm in tms]
        if tm_ids:
            result = await self.db.execute(
                select(LDMTMAssignment).where(LDMTMAssignment.tm_id.in_(tm_ids))
            )
            assignments = {a.tm_id: a for a in result.scalars().all()}
        else:
            assignments = {}

        return [self._tm_to_dict(tm, assignments.get(tm.id)) for tm in tms]

    async def create(
        self,
        name: str,
        source_lang: str = "ko",
        target_lang: str = "en",
        owner_id: Optional[int] = None
    ) -> Dict[str, Any]:
        tm = LDMTranslationMemory(
            name=name,
            source_lang=source_lang,
            target_lang=target_lang,
            owner_id=owner_id,
            entry_count=0,
            status="ready",
            mode="standard"
        )
        self.db.add(tm)
        await self.db.flush()
        await self.db.commit()
        logger.info(f"Created TM: {name} (id={tm.id})")
        return self._tm_to_dict(tm)

    async def delete(self, tm_id: int) -> bool:
        result = await self.db.execute(
            select(LDMTranslationMemory).where(LDMTranslationMemory.id == tm_id)
        )
        tm = result.scalar_one_or_none()
        if not tm:
            return False

        # Delete entries first
        await self.db.execute(
            delete(LDMTMEntry).where(LDMTMEntry.tm_id == tm_id)
        )
        # Delete assignment
        await self.db.execute(
            delete(LDMTMAssignment).where(LDMTMAssignment.tm_id == tm_id)
        )
        # Delete TM
        await self.db.delete(tm)
        await self.db.commit()
        logger.info(f"Deleted TM: {tm.name} (id={tm_id})")
        return True

    # =========================================================================
    # Assignment Operations
    # =========================================================================

    async def assign(self, tm_id: int, target: AssignmentTarget) -> Dict[str, Any]:
        # Validate only one scope
        if target.scope_count() > 1:
            raise ValueError("Only one scope can be set (platform, project, or folder)")

        # Get TM
        tm = await self.get(tm_id)
        if not tm:
            raise ValueError(f"TM {tm_id} not found")

        # Get or create assignment
        result = await self.db.execute(
            select(LDMTMAssignment).where(LDMTMAssignment.tm_id == tm_id)
        )
        assignment = result.scalar_one_or_none()

        if assignment:
            # Update existing
            assignment.platform_id = target.platform_id
            assignment.project_id = target.project_id
            assignment.folder_id = target.folder_id
            assignment.assigned_at = datetime.utcnow()
        else:
            # Create new
            assignment = LDMTMAssignment(
                tm_id=tm_id,
                platform_id=target.platform_id,
                project_id=target.project_id,
                folder_id=target.folder_id,
                is_active=False,
                priority=0,
                assigned_at=datetime.utcnow()
            )
            self.db.add(assignment)

        await self.db.commit()

        scope = "unassigned"
        if target.folder_id:
            scope = "folder"
        elif target.project_id:
            scope = "project"
        elif target.platform_id:
            scope = "platform"

        logger.info(f"Assigned TM {tm_id} to {scope}")
        return await self.get(tm_id)

    async def unassign(self, tm_id: int) -> Dict[str, Any]:
        return await self.assign(tm_id, AssignmentTarget())

    async def activate(self, tm_id: int) -> Dict[str, Any]:
        result = await self.db.execute(
            select(LDMTMAssignment).where(LDMTMAssignment.tm_id == tm_id)
        )
        assignment = result.scalar_one_or_none()

        if not assignment:
            raise ValueError("TM must be assigned before activation")

        if assignment.platform_id is None and assignment.project_id is None and assignment.folder_id is None:
            raise ValueError("TM must be assigned to a scope before activation")

        assignment.is_active = True
        assignment.activated_at = datetime.utcnow()
        await self.db.commit()
        logger.info(f"Activated TM {tm_id}")
        return await self.get(tm_id)

    async def deactivate(self, tm_id: int) -> Dict[str, Any]:
        result = await self.db.execute(
            select(LDMTMAssignment).where(LDMTMAssignment.tm_id == tm_id)
        )
        assignment = result.scalar_one_or_none()

        if assignment:
            assignment.is_active = False
            await self.db.commit()
            logger.info(f"Deactivated TM {tm_id}")

        return await self.get(tm_id)

    async def get_assignment(self, tm_id: int) -> Optional[Dict[str, Any]]:
        result = await self.db.execute(
            select(LDMTMAssignment).where(LDMTMAssignment.tm_id == tm_id)
        )
        assignment = result.scalar_one_or_none()

        if not assignment:
            return None

        return {
            "id": assignment.id,
            "tm_id": assignment.tm_id,
            "platform_id": assignment.platform_id,
            "project_id": assignment.project_id,
            "folder_id": assignment.folder_id,
            "is_active": assignment.is_active,
            "priority": assignment.priority,
        }

    # =========================================================================
    # Scope Queries
    # =========================================================================

    async def get_for_scope(
        self,
        platform_id: Optional[int] = None,
        project_id: Optional[int] = None,
        folder_id: Optional[int] = None,
        include_inactive: bool = False
    ) -> List[Dict[str, Any]]:
        query = select(LDMTMAssignment, LDMTranslationMemory).join(
            LDMTranslationMemory, LDMTMAssignment.tm_id == LDMTranslationMemory.id
        )

        if folder_id:
            query = query.where(LDMTMAssignment.folder_id == folder_id)
        elif project_id:
            query = query.where(LDMTMAssignment.project_id == project_id)
        elif platform_id:
            query = query.where(LDMTMAssignment.platform_id == platform_id)
        else:
            # Unassigned
            query = query.where(
                and_(
                    LDMTMAssignment.platform_id.is_(None),
                    LDMTMAssignment.project_id.is_(None),
                    LDMTMAssignment.folder_id.is_(None)
                )
            )

        if not include_inactive:
            query = query.where(LDMTMAssignment.is_active == True)

        result = await self.db.execute(query)
        rows = result.all()

        return [self._tm_to_dict(tm, assignment) for assignment, tm in rows]

    async def get_active_for_file(self, file_id: int) -> List[Dict[str, Any]]:
        # Get file's folder/project/platform chain
        result = await self.db.execute(
            select(LDMFile).where(LDMFile.id == file_id)
        )
        file = result.scalar_one_or_none()
        if not file:
            return []

        # Build scope chain
        scope_filters = []

        # Folder scope
        if file.folder_id:
            scope_filters.append(LDMTMAssignment.folder_id == file.folder_id)

        # Project scope
        if file.project_id:
            scope_filters.append(LDMTMAssignment.project_id == file.project_id)

            # Platform scope (need to get platform from project)
            result = await self.db.execute(
                select(LDMProject).where(LDMProject.id == file.project_id)
            )
            project = result.scalar_one_or_none()
            if project and project.platform_id:
                scope_filters.append(LDMTMAssignment.platform_id == project.platform_id)

        if not scope_filters:
            return []

        query = select(LDMTMAssignment, LDMTranslationMemory).join(
            LDMTranslationMemory, LDMTMAssignment.tm_id == LDMTranslationMemory.id
        ).where(
            and_(
                LDMTMAssignment.is_active == True,
                or_(*scope_filters)
            )
        ).order_by(LDMTMAssignment.priority.desc())

        result = await self.db.execute(query)
        rows = result.all()

        return [self._tm_to_dict(tm, assignment) for assignment, tm in rows]

    # =========================================================================
    # TM Entries
    # =========================================================================

    async def add_entry(
        self,
        tm_id: int,
        source: str,
        target: str,
        string_id: Optional[str] = None,
        created_by: Optional[str] = None
    ) -> Dict[str, Any]:
        import hashlib

        source_hash = hashlib.sha256(source.encode()).hexdigest()

        entry = LDMTMEntry(
            tm_id=tm_id,
            source_text=source,
            target_text=target,
            source_hash=source_hash,
            string_id=string_id,
            created_by=created_by,
            change_date=datetime.utcnow()
        )
        self.db.add(entry)

        # Update entry count
        result = await self.db.execute(
            select(LDMTranslationMemory).where(LDMTranslationMemory.id == tm_id)
        )
        tm = result.scalar_one_or_none()
        if tm:
            tm.entry_count = (tm.entry_count or 0) + 1

        await self.db.commit()
        return self._entry_to_dict(entry)

    async def get_entries(
        self,
        tm_id: int,
        offset: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        result = await self.db.execute(
            select(LDMTMEntry)
            .where(LDMTMEntry.tm_id == tm_id)
            .offset(offset)
            .limit(limit)
        )
        entries = result.scalars().all()
        return [self._entry_to_dict(e) for e in entries]

    async def search_entries(
        self,
        tm_id: int,
        query: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        # Simple LIKE search for now
        result = await self.db.execute(
            select(LDMTMEntry)
            .where(
                and_(
                    LDMTMEntry.tm_id == tm_id,
                    LDMTMEntry.source_text.ilike(f"%{query}%")
                )
            )
            .limit(limit)
        )
        entries = result.scalars().all()

        results = []
        for e in entries:
            d = self._entry_to_dict(e)
            d["match_score"] = 100 if query.lower() in e.source_text.lower() else 80
            results.append(d)

        return results

    async def delete_entry(self, entry_id: int) -> bool:
        result = await self.db.execute(
            select(LDMTMEntry).where(LDMTMEntry.id == entry_id)
        )
        entry = result.scalar_one_or_none()
        if not entry:
            return False

        tm_id = entry.tm_id
        await self.db.delete(entry)

        # Update entry count
        result = await self.db.execute(
            select(LDMTranslationMemory).where(LDMTranslationMemory.id == tm_id)
        )
        tm = result.scalar_one_or_none()
        if tm and tm.entry_count:
            tm.entry_count = max(0, tm.entry_count - 1)

        await self.db.commit()
        return True

    # =========================================================================
    # Tree Structure
    # =========================================================================

    async def get_tree(self) -> Dict[str, Any]:
        """Get full TM tree for UI."""
        # Ensure Offline Storage exists
        await self._ensure_offline_storage_project()

        # Get all platforms with projects
        result = await self.db.execute(
            select(LDMPlatform).options(selectinload(LDMPlatform.projects))
        )
        platforms = result.scalars().all()

        # Get all TMs with assignments
        all_tms = await self.get_all()

        # Group TMs by assignment
        unassigned = []
        by_platform = {}
        by_project = {}
        by_folder = {}

        for tm in all_tms:
            if tm.get("folder_id"):
                by_folder.setdefault(tm["folder_id"], []).append(tm)
            elif tm.get("project_id"):
                by_project.setdefault(tm["project_id"], []).append(tm)
            elif tm.get("platform_id"):
                by_platform.setdefault(tm["platform_id"], []).append(tm)
            else:
                unassigned.append(tm)

        # Build tree
        tree_platforms = []
        for p in platforms:
            platform_dict = {
                "id": p.id,
                "name": p.name,
                "tms": by_platform.get(p.id, []),
                "projects": []
            }

            for proj in p.projects:
                project_dict = {
                    "id": proj.id,
                    "name": proj.name,
                    "tms": by_project.get(proj.id, []),
                    "folders": []  # TODO: Add folder support
                }
                platform_dict["projects"].append(project_dict)

            tree_platforms.append(platform_dict)

        return {
            "unassigned": unassigned,
            "platforms": tree_platforms
        }
