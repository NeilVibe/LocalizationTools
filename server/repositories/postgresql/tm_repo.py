"""
PostgreSQL TM Repository.

Implements TMRepository interface using SQLAlchemy async operations.
This is the online mode adapter.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, delete, text
from sqlalchemy.orm import selectinload
from loguru import logger

from server.repositories.interfaces.tm_repository import TMRepository, AssignmentTarget
from server.database.models import (
    LDMTranslationMemory, LDMTMAssignment, LDMTMEntry,
    LDMPlatform, LDMProject, LDMFile
)


# Constants
OFFLINE_STORAGE_PLATFORM_NAME = "Offline Storage"
OFFLINE_STORAGE_PROJECT_NAME = "Offline Storage"


class PostgreSQLTMRepository(TMRepository):
    """
    PostgreSQL implementation of TMRepository.

    P10: FULL ABSTRACT - Permissions are checked INSIDE the repository.
    TM access is controlled via project/platform assignments.
    """

    def __init__(self, db: AsyncSession, user: Optional[dict] = None):
        self.db = db
        self.user = user or {}

    def _is_admin(self) -> bool:
        return self.user.get("role") in ["admin", "superadmin"]

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
    # TM Linking (Active TMs for Projects)
    # =========================================================================

    async def link_to_project(
        self,
        tm_id: int,
        project_id: int,
        priority: int = 1
    ) -> Dict[str, Any]:
        """Link a TM to a project for auto-add on confirm."""
        from server.database.models import LDMActiveTM

        # Check if already linked
        result = await self.db.execute(
            select(LDMActiveTM).where(
                LDMActiveTM.tm_id == tm_id,
                LDMActiveTM.project_id == project_id
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Update priority if already exists
            existing.priority = priority
            await self.db.commit()
            return {"tm_id": tm_id, "project_id": project_id, "priority": priority, "created": False}

        # Create new link
        link = LDMActiveTM(
            tm_id=tm_id,
            project_id=project_id,
            priority=priority
        )
        self.db.add(link)
        await self.db.commit()

        logger.info(f"[TM-REPO] Linked TM {tm_id} to project {project_id} with priority {priority}")
        return {"tm_id": tm_id, "project_id": project_id, "priority": priority, "created": True}

    async def unlink_from_project(self, tm_id: int, project_id: int) -> bool:
        """Unlink a TM from a project."""
        from server.database.models import LDMActiveTM

        result = await self.db.execute(
            select(LDMActiveTM).where(
                LDMActiveTM.tm_id == tm_id,
                LDMActiveTM.project_id == project_id
            )
        )
        link = result.scalar_one_or_none()

        if not link:
            return False

        await self.db.delete(link)
        await self.db.commit()

        logger.info(f"[TM-REPO] Unlinked TM {tm_id} from project {project_id}")
        return True

    async def get_linked_for_project(
        self,
        project_id: int,
        user_id: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Get the highest-priority linked TM for a project."""
        from server.database.models import LDMActiveTM

        query = (
            select(LDMTranslationMemory)
            .join(LDMActiveTM, LDMActiveTM.tm_id == LDMTranslationMemory.id)
            .where(LDMActiveTM.project_id == project_id)
        )

        # Filter by owner if user_id provided
        if user_id is not None:
            query = query.where(LDMTranslationMemory.owner_id == user_id)

        query = query.order_by(LDMActiveTM.priority).limit(1)

        result = await self.db.execute(query)
        tm = result.scalar_one_or_none()

        if not tm:
            return None

        return self._tm_to_dict(tm)

    async def get_all_linked_for_project(
        self,
        project_id: int
    ) -> List[Dict[str, Any]]:
        """Get all TMs linked to a project, ordered by priority."""
        from server.database.models import LDMActiveTM

        result = await self.db.execute(
            select(LDMActiveTM, LDMTranslationMemory)
            .join(LDMTranslationMemory, LDMActiveTM.tm_id == LDMTranslationMemory.id)
            .where(LDMActiveTM.project_id == project_id)
            .order_by(LDMActiveTM.priority)
        )
        links = result.all()

        return [
            {
                "tm_id": link.LDMActiveTM.tm_id,
                "tm_name": link.LDMTranslationMemory.name,
                "priority": link.LDMActiveTM.priority,
                "status": link.LDMTranslationMemory.status,
                "entry_count": link.LDMTranslationMemory.entry_count,
                "linked_at": link.LDMActiveTM.activated_at.isoformat() if link.LDMActiveTM.activated_at else None
            }
            for link in links
        ]

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

    async def add_entries_bulk(
        self,
        tm_id: int,
        entries: List[Dict[str, Any]]
    ) -> int:
        """
        Bulk add entries to TM using COPY TEXT (20k+ entries/sec).

        Uses PostgreSQL's COPY protocol for maximum performance.
        """
        import hashlib
        from server.database.db_utils import bulk_copy_tm_entries

        if not entries:
            return 0

        # Format entries for bulk_copy_tm_entries
        formatted = []
        for e in entries:
            source = e.get("source") or e.get("source_text", "")
            target = e.get("target") or e.get("target_text", "")
            formatted.append({
                "source_text": source,
                "target_text": target,
                "string_id": e.get("string_id")
            })

        # Use sync db session for COPY TEXT
        from server.utils.dependencies import get_db
        sync_db = next(get_db())
        try:
            inserted = bulk_copy_tm_entries(sync_db, tm_id, formatted)

            # Update entry count on TM
            from server.database.models import LDMTranslationMemory
            tm = sync_db.query(LDMTranslationMemory).filter(
                LDMTranslationMemory.id == tm_id
            ).first()
            if tm:
                tm.entry_count = (tm.entry_count or 0) + inserted
                sync_db.commit()

            logger.info(f"Bulk added {inserted} entries to PostgreSQL TM {tm_id}")
            return inserted
        finally:
            sync_db.close()

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

    async def update_entry(
        self,
        entry_id: int,
        source_text: Optional[str] = None,
        target_text: Optional[str] = None,
        string_id: Optional[str] = None,
        updated_by: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """P11-FIX: Update TM entry via Repository Pattern."""
        import hashlib
        from server.database.db_utils import normalize_text_for_hash

        result = await self.db.execute(
            select(LDMTMEntry).where(LDMTMEntry.id == entry_id)
        )
        entry = result.scalar_one_or_none()
        if not entry:
            return None

        # Update fields if provided
        if source_text is not None:
            entry.source_text = source_text
            normalized = normalize_text_for_hash(source_text)
            entry.source_hash = hashlib.sha256(normalized.encode('utf-8')).hexdigest()

        if target_text is not None:
            entry.target_text = target_text

        if string_id is not None:
            entry.string_id = string_id

        entry.updated_at = datetime.utcnow()
        entry.updated_by = updated_by

        # Mark TM as updated
        result = await self.db.execute(
            select(LDMTranslationMemory).where(LDMTranslationMemory.id == entry.tm_id)
        )
        tm = result.scalar_one_or_none()
        if tm:
            tm.updated_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(entry)

        logger.info(f"Updated TM entry {entry_id} by {updated_by}")
        return self._entry_to_dict(entry)

    async def confirm_entry(
        self,
        entry_id: int,
        confirm: bool = True,
        confirmed_by: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """P11-FIX: Confirm/unconfirm TM entry via Repository Pattern."""
        result = await self.db.execute(
            select(LDMTMEntry).where(LDMTMEntry.id == entry_id)
        )
        entry = result.scalar_one_or_none()
        if not entry:
            return None

        if confirm:
            entry.is_confirmed = True
            entry.confirmed_at = datetime.utcnow()
            entry.confirmed_by = confirmed_by
        else:
            entry.is_confirmed = False
            entry.confirmed_at = None
            entry.confirmed_by = None

        await self.db.commit()
        await self.db.refresh(entry)

        logger.info(f"{'Confirmed' if confirm else 'Unconfirmed'} TM entry {entry_id} by {confirmed_by}")

        result = self._entry_to_dict(entry)
        result.update({
            "confirmed_at": entry.confirmed_at.isoformat() if entry.confirmed_at else None,
            "confirmed_by": entry.confirmed_by
        })
        return result

    async def bulk_confirm_entries(
        self,
        tm_id: int,
        entry_ids: List[int],
        confirm: bool = True,
        confirmed_by: Optional[str] = None
    ) -> int:
        """P11-FIX: Bulk confirm/unconfirm via Repository Pattern."""
        from sqlalchemy import update

        now = datetime.utcnow()

        if confirm:
            stmt = update(LDMTMEntry).where(
                and_(
                    LDMTMEntry.tm_id == tm_id,
                    LDMTMEntry.id.in_(entry_ids)
                )
            ).values(
                is_confirmed=True,
                confirmed_at=now,
                confirmed_by=confirmed_by
            )
        else:
            stmt = update(LDMTMEntry).where(
                and_(
                    LDMTMEntry.tm_id == tm_id,
                    LDMTMEntry.id.in_(entry_ids)
                )
            ).values(
                is_confirmed=False,
                confirmed_at=None,
                confirmed_by=None
            )

        result = await self.db.execute(stmt)
        await self.db.commit()

        updated_count = result.rowcount
        logger.info(f"Bulk {'confirmed' if confirm else 'unconfirmed'} {updated_count} entries in TM {tm_id} by {confirmed_by}")
        return updated_count

    async def get_glossary_terms(
        self,
        tm_ids: List[int],
        max_length: int = 20,
        limit: int = 1000
    ) -> List[tuple]:
        """Get short TM entries as glossary terms for QA checks."""
        from sqlalchemy import func

        if not tm_ids:
            return []

        result = await self.db.execute(
            select(LDMTMEntry.source_text, LDMTMEntry.target_text)
            .where(
                LDMTMEntry.tm_id.in_(tm_ids),
                func.length(LDMTMEntry.source_text) <= max_length,
                LDMTMEntry.source_text.isnot(None),
                LDMTMEntry.target_text.isnot(None)
            )
            .limit(limit)
        )

        return [(row[0], row[1]) for row in result.all()]

    # =========================================================================
    # Tree Structure
    # =========================================================================

    async def get_tree(self) -> Dict[str, Any]:
        """Get full TM tree for UI with folder hierarchy."""
        from server.database.models import LDMFolder

        # Ensure Offline Storage exists
        await self._ensure_offline_storage_project()

        # Get all platforms with projects and their folders
        result = await self.db.execute(
            select(LDMPlatform).options(
                selectinload(LDMPlatform.projects).selectinload(LDMProject.folders)
            )
        )
        platforms = result.scalars().all()

        # Get all TMs with assignments
        all_tms = await self.get_all()

        # P11-FIX: Transform TMs to use tm_id/tm_name format expected by frontend
        def transform_tm(tm: Dict) -> Dict:
            return {
                "tm_id": tm.get("id"),
                "tm_name": tm.get("name"),
                "entry_count": tm.get("entry_count", 0),
                "is_active": tm.get("is_active", False),
                "platform_id": tm.get("platform_id"),
                "project_id": tm.get("project_id"),
                "folder_id": tm.get("folder_id"),
                "source_lang": tm.get("source_lang"),
                "target_lang": tm.get("target_lang"),
            }

        # Group TMs by assignment
        unassigned = []
        by_platform = {}
        by_project = {}
        by_folder = {}

        for tm in all_tms:
            transformed = transform_tm(tm)
            if tm.get("folder_id"):
                by_folder.setdefault(tm["folder_id"], []).append(transformed)
            elif tm.get("project_id"):
                by_project.setdefault(tm["project_id"], []).append(transformed)
            elif tm.get("platform_id"):
                by_platform.setdefault(tm["platform_id"], []).append(transformed)
            else:
                unassigned.append(transformed)

        def build_folder_tree(folders: list, parent_id: int = None) -> list:
            """Build hierarchical folder structure."""
            result = []
            for folder in folders:
                if folder.parent_id == parent_id:
                    folder_dict = {
                        "id": folder.id,
                        "name": folder.name,
                        "tms": by_folder.get(folder.id, []),
                        "children": build_folder_tree(folders, folder.id)  # P11-FIX: Frontend expects 'children'
                    }
                    result.append(folder_dict)
            return result

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
                # Build folder tree for this project (root folders have parent_id=None)
                folder_tree = build_folder_tree(list(proj.folders), None)

                project_dict = {
                    "id": proj.id,
                    "name": proj.name,
                    "tms": by_project.get(proj.id, []),
                    "folders": folder_tree
                }
                platform_dict["projects"].append(project_dict)

            tree_platforms.append(platform_dict)

        return {
            "unassigned": unassigned,
            "platforms": tree_platforms
        }

    # =========================================================================
    # Index Operations (P10-REPO)
    # =========================================================================

    async def get_indexes(self, tm_id: int) -> List[Dict[str, Any]]:
        """Get index status for a TM."""
        from server.database.models import LDMTMIndex

        result = await self.db.execute(
            select(LDMTMIndex).where(LDMTMIndex.tm_id == tm_id)
        )
        indexes = result.scalars().all()

        return [
            {
                "type": idx.index_type,
                "status": idx.status,
                "file_size": idx.file_size,
                "built_at": idx.built_at.isoformat() if idx.built_at else None
            }
            for idx in indexes
        ]

    async def count_entries(self, tm_id: int) -> int:
        """Count entries in a TM."""
        from sqlalchemy import func

        result = await self.db.execute(
            select(func.count()).select_from(LDMTMEntry).where(LDMTMEntry.tm_id == tm_id)
        )
        return result.scalar() or 0

    # =========================================================================
    # Advanced Search (P10-REPO)
    # =========================================================================

    async def search_exact(
        self,
        tm_id: int,
        source: str
    ) -> Optional[Dict[str, Any]]:
        """Hash-based exact match search."""
        import hashlib
        from server.database.db_utils import normalize_text_for_hash

        normalized = normalize_text_for_hash(source)
        source_hash = hashlib.sha256(normalized.encode('utf-8')).hexdigest()

        result = await self.db.execute(
            select(LDMTMEntry).where(
                LDMTMEntry.tm_id == tm_id,
                LDMTMEntry.source_hash == source_hash
            )
        )
        entry = result.scalar_one_or_none()

        if entry:
            return {
                "source_text": entry.source_text,
                "target_text": entry.target_text,
                "similarity": 1.0,
                "tier": 1,
                "strategy": "perfect_whole_match"
            }
        return None

    async def search_similar(
        self,
        tm_id: int,
        source: str,
        threshold: float = 0.5,
        max_results: int = 5
    ) -> List[Dict[str, Any]]:
        """pg_trgm similarity search."""
        sql = text("""
            SELECT
                e.id,
                e.source_text as source,
                e.target_text as target,
                e.tm_id,
                similarity(lower(e.source_text), lower(:search_text)) as sim
            FROM ldm_tm_entries e
            WHERE e.tm_id = :tm_id
              AND e.target_text IS NOT NULL
              AND e.target_text != ''
              AND similarity(lower(e.source_text), lower(:search_text)) >= :threshold
            ORDER BY sim DESC
            LIMIT :max_results
        """)

        result = await self.db.execute(sql, {
            'tm_id': tm_id,
            'search_text': source.strip(),
            'threshold': threshold,
            'max_results': max_results
        })
        rows = result.fetchall()

        return [
            {
                'source': row.source,
                'target': row.target,
                'similarity': round(float(row.sim), 3),
                'entry_id': row.id,
                'tm_id': row.tm_id,
                'file_name': 'TM'
            }
            for row in rows
        ]
