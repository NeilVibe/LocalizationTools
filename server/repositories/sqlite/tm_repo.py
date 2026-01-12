"""
SQLite TM Repository.

Implements TMRepository interface using SQLite (offline.py).
This is the offline mode adapter.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import hashlib
from loguru import logger

from server.repositories.interfaces.tm_repository import TMRepository, AssignmentTarget
from server.database.offline import get_offline_db


class SQLiteTMRepository(TMRepository):
    """
    SQLite implementation of TMRepository.

    Uses OfflineDatabase from offline.py for all operations.
    Enables full offline TM support - same operations work without server.
    """

    def __init__(self):
        self.db = get_offline_db()

    # =========================================================================
    # Core CRUD
    # =========================================================================

    async def get(self, tm_id: int) -> Optional[Dict[str, Any]]:
        """Get TM by ID from SQLite."""
        # Try to get from offline_tms table
        tms = self.db.get_tms()
        for tm in tms:
            if tm.get("id") == tm_id:
                # Add assignment info
                assignment = self.db.get_local_tm_assignment(tm_id)
                if assignment:
                    tm.update({
                        "assignment_id": assignment.get("id"),
                        "platform_id": assignment.get("platform_id"),
                        "project_id": assignment.get("project_id"),
                        "folder_id": assignment.get("folder_id"),
                        "is_active": assignment.get("is_active", False),
                    })
                return tm
        return None

    async def get_all(self) -> List[Dict[str, Any]]:
        """Get all TMs from SQLite."""
        return self.db.get_all_local_tms()

    async def create(
        self,
        name: str,
        source_lang: str = "ko",
        target_lang: str = "en",
        owner_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Create new TM in SQLite."""
        return self.db.create_local_tm(name, source_lang, target_lang)

    async def delete(self, tm_id: int) -> bool:
        """Delete TM from SQLite."""
        conn = self.db._get_connection()
        try:
            # Delete entries
            conn.execute("DELETE FROM offline_tm_entries WHERE tm_id = ?", (tm_id,))
            # Delete assignments
            conn.execute("DELETE FROM offline_tm_assignments WHERE tm_id = ?", (tm_id,))
            # Delete TM
            result = conn.execute("DELETE FROM offline_tms WHERE id = ?", (tm_id,))
            conn.commit()
            deleted = result.rowcount > 0
            if deleted:
                logger.info(f"Deleted local TM {tm_id}")
            return deleted
        finally:
            conn.close()

    # =========================================================================
    # Assignment Operations
    # =========================================================================

    async def assign(self, tm_id: int, target: AssignmentTarget) -> Dict[str, Any]:
        """Assign TM to scope in SQLite."""
        if target.scope_count() > 1:
            raise ValueError("Only one scope can be set (platform, project, or folder)")

        result = self.db.assign_local_tm(
            tm_id=tm_id,
            platform_id=target.platform_id,
            project_id=target.project_id,
            folder_id=target.folder_id
        )

        scope = "unassigned"
        if target.folder_id:
            scope = "folder"
        elif target.project_id:
            scope = "project"
        elif target.platform_id:
            scope = "platform"

        logger.info(f"Assigned local TM {tm_id} to {scope}")
        return await self.get(tm_id)

    async def unassign(self, tm_id: int) -> Dict[str, Any]:
        """Unassign TM in SQLite."""
        self.db.unassign_local_tm(tm_id)
        return await self.get(tm_id)

    async def activate(self, tm_id: int) -> Dict[str, Any]:
        """Activate TM in SQLite."""
        assignment = self.db.get_local_tm_assignment(tm_id)

        if not assignment:
            raise ValueError("TM must be assigned before activation")

        if (assignment.get("platform_id") is None and
            assignment.get("project_id") is None and
            assignment.get("folder_id") is None):
            raise ValueError("TM must be assigned to a scope before activation")

        conn = self.db._get_connection()
        try:
            conn.execute(
                """UPDATE offline_tm_assignments
                   SET is_active = 1, activated_at = datetime('now')
                   WHERE tm_id = ?""",
                (tm_id,)
            )
            conn.commit()
            logger.info(f"Activated local TM {tm_id}")
        finally:
            conn.close()

        return await self.get(tm_id)

    async def deactivate(self, tm_id: int) -> Dict[str, Any]:
        """Deactivate TM in SQLite."""
        conn = self.db._get_connection()
        try:
            conn.execute(
                "UPDATE offline_tm_assignments SET is_active = 0 WHERE tm_id = ?",
                (tm_id,)
            )
            conn.commit()
            logger.info(f"Deactivated local TM {tm_id}")
        finally:
            conn.close()

        return await self.get(tm_id)

    async def get_assignment(self, tm_id: int) -> Optional[Dict[str, Any]]:
        """Get TM assignment from SQLite."""
        return self.db.get_local_tm_assignment(tm_id)

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
        """Get TMs for scope from SQLite."""
        return self.db.get_local_tm_assignments_for_scope(
            platform_id=platform_id,
            project_id=project_id,
            folder_id=folder_id
        )

    async def get_active_for_file(self, file_id: int) -> List[Dict[str, Any]]:
        """Get active TMs for file scope chain."""
        # Get file info
        conn = self.db._get_connection()
        try:
            row = conn.execute(
                "SELECT folder_id, project_id FROM offline_files WHERE id = ?",
                (file_id,)
            ).fetchone()

            if not row:
                return []

            folder_id = row["folder_id"]
            project_id = row["project_id"]

            # Get all active TMs in scope chain
            results = []

            # Folder-level TMs
            if folder_id:
                folder_tms = await self.get_for_scope(folder_id=folder_id)
                for tm in folder_tms:
                    if tm.get("is_active"):
                        tm["scope"] = "folder"
                        results.append(tm)

            # Project-level TMs
            if project_id:
                project_tms = await self.get_for_scope(project_id=project_id)
                for tm in project_tms:
                    if tm.get("is_active"):
                        tm["scope"] = "project"
                        results.append(tm)

            return results
        finally:
            conn.close()

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
        """Add entry to TM in SQLite."""
        entry = {
            "source_text": source,
            "target_text": target,
            "source_hash": hashlib.sha256(source.encode()).hexdigest(),
            "string_id": string_id,
            "created_by": created_by,
            "change_date": datetime.now().isoformat(),
            "is_confirmed": False,
        }
        entry_id = self.db.save_tm_entry(entry, tm_id)
        entry["id"] = entry_id
        entry["tm_id"] = tm_id
        return entry

    async def add_entries_bulk(
        self,
        tm_id: int,
        entries: List[Dict[str, Any]]
    ) -> int:
        """
        Bulk add entries to TM in SQLite using executemany.

        Equivalent to PostgreSQL's COPY TEXT for performance.
        Uses single transaction with executemany = instant for 1000s of entries.
        """
        if not entries:
            return 0

        conn = self.db._get_connection()
        try:
            now = datetime.now().isoformat()

            # Prepare data for executemany
            data = []
            for e in entries:
                source = e.get("source") or e.get("source_text", "")
                target = e.get("target") or e.get("target_text", "")
                data.append((
                    tm_id,
                    source,
                    target,
                    hashlib.sha256(source.encode()).hexdigest(),
                    e.get("string_id"),
                    now,
                    False  # is_confirmed
                ))

            # Bulk insert with executemany (single transaction = fast!)
            conn.executemany(
                """INSERT INTO offline_tm_entries
                   (tm_id, source_text, target_text, source_hash, string_id, change_date, is_confirmed)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                data
            )

            # Update entry count on TM
            conn.execute(
                "UPDATE offline_tms SET entry_count = entry_count + ? WHERE id = ?",
                (len(data), tm_id)
            )

            conn.commit()
            logger.info(f"Bulk added {len(data)} entries to SQLite TM {tm_id}")
            return len(data)
        finally:
            conn.close()

    async def get_entries(
        self,
        tm_id: int,
        offset: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get TM entries from SQLite."""
        entries = self.db.get_tm_entries(tm_id)
        return entries[offset:offset + limit]

    async def search_entries(
        self,
        tm_id: int,
        query: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search TM entries in SQLite."""
        entries = self.db.get_tm_entries(tm_id)

        results = []
        query_lower = query.lower()
        for e in entries:
            source = e.get("source_text", "")
            if query_lower in source.lower():
                e["match_score"] = 100 if query_lower == source.lower() else 80
                results.append(e)
                if len(results) >= limit:
                    break

        return results

    async def delete_entry(self, entry_id: int) -> bool:
        """Delete TM entry from SQLite."""
        conn = self.db._get_connection()
        try:
            # Get tm_id first
            row = conn.execute(
                "SELECT tm_id FROM offline_tm_entries WHERE id = ?",
                (entry_id,)
            ).fetchone()

            if not row:
                return False

            tm_id = row["tm_id"]

            # Delete entry
            conn.execute("DELETE FROM offline_tm_entries WHERE id = ?", (entry_id,))

            # Update entry count
            conn.execute(
                """UPDATE offline_tms
                   SET entry_count = CASE
                       WHEN entry_count > 0 THEN entry_count - 1
                       ELSE 0
                   END
                   WHERE id = ?""",
                (tm_id,)
            )
            conn.commit()
            return True
        finally:
            conn.close()

    # =========================================================================
    # Tree Structure
    # =========================================================================

    async def get_tree(self) -> Dict[str, Any]:
        """Get TM tree structure for UI with folder hierarchy."""
        all_tms = await self.get_all()

        # Group by assignment
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

        def build_folder_tree(folders: list, parent_id) -> list:
            """Build hierarchical folder structure."""
            result = []
            for folder in folders:
                if folder["parent_id"] == parent_id:
                    folder_dict = {
                        "id": folder["id"],
                        "name": folder["name"],
                        "tms": by_folder.get(folder["id"], []),
                        "folders": build_folder_tree(folders, folder["id"])
                    }
                    result.append(folder_dict)
            return result

        # Get platforms from SQLite
        conn = self.db._get_connection()
        try:
            platforms = conn.execute(
                "SELECT * FROM offline_platforms ORDER BY name"
            ).fetchall()

            tree_platforms = []
            for p in platforms:
                # P9-FIX: Skip duplicate "Offline Storage" platforms synced from PostgreSQL
                # The real Offline Storage has id=-1 (well-known SQLite ID)
                # Any other "Offline Storage" with positive ID was synced from PostgreSQL
                if p["name"] == "Offline Storage" and p["id"] != -1:
                    logger.debug(f"[TM-REPO] Skipping synced Offline Storage platform (id={p['id']})")
                    continue
                platform_dict = {
                    "id": p["id"],
                    "name": p["name"],
                    "tms": by_platform.get(p["id"], []),
                    "projects": []
                }

                # Get projects for this platform
                projects = conn.execute(
                    "SELECT * FROM offline_projects WHERE platform_id = ?",
                    (p["id"],)
                ).fetchall()

                for proj in projects:
                    # Get all folders for this project
                    folders = conn.execute(
                        "SELECT * FROM offline_folders WHERE project_id = ?",
                        (proj["id"],)
                    ).fetchall()

                    # Build folder tree (root folders have parent_id=None)
                    folder_tree = build_folder_tree(
                        [dict(f) for f in folders],
                        None
                    )

                    project_dict = {
                        "id": proj["id"],
                        "name": proj["name"],
                        "tms": by_project.get(proj["id"], []),
                        "folders": folder_tree
                    }
                    platform_dict["projects"].append(project_dict)

                tree_platforms.append(platform_dict)

            return {
                "unassigned": unassigned,
                "platforms": tree_platforms
            }
        finally:
            conn.close()
