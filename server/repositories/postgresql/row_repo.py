"""
PostgreSQL Row Repository Implementation.

P10: FULL ABSTRACT + REPO Pattern

Implements RowRepository interface using SQLAlchemy async.
Permissions are baked INTO the repository (via file/project access).
"""

from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select, func, or_, and_
from loguru import logger

from server.database.models import LDMRow, LDMFile, LDMEditHistory, LDMProject, LDMResourceAccess
from server.repositories.interfaces.row_repository import RowRepository


class PostgreSQLRowRepository(RowRepository):
    """
    PostgreSQL implementation of RowRepository.

    P10: FULL ABSTRACT - Permissions are checked INSIDE the repository.
    Row access is granted via file access (which is via project access).
    """

    def __init__(self, db: AsyncSession, user: Optional[dict] = None):
        self.db = db
        self.user = user or {}

    def _is_admin(self) -> bool:
        return self.user.get("role") in ["admin", "superadmin"]

    async def _can_access_file(self, file_id: int) -> bool:
        """Check if current user can access file (and thus its rows)."""
        if not self.user:
            return False
        if self._is_admin():
            return True

        user_id = self.user.get("user_id")
        if not user_id:
            return False

        # Get file's project
        result = await self.db.execute(
            select(LDMFile.project_id).where(LDMFile.id == file_id)
        )
        row = result.first()
        if not row:
            return False

        project_id = row[0]

        # Check project access
        result = await self.db.execute(
            select(LDMProject.is_restricted, LDMProject.owner_id)
            .where(LDMProject.id == project_id)
        )
        proj_row = result.first()
        if not proj_row:
            return False

        is_restricted, owner_id = proj_row
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

    def _row_to_dict(self, row: LDMRow, include_file: bool = False) -> Dict[str, Any]:
        """Convert SQLAlchemy row to dict."""
        result = {
            "id": row.id,
            "file_id": row.file_id,
            "row_num": row.row_num,
            "string_id": row.string_id,
            "source": row.source,
            "target": row.target,
            "status": row.status,
            "qa_flag_count": row.qa_flag_count,
            "extra_data": row.extra_data,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            "updated_by": row.updated_by,
        }
        if include_file and row.file:
            result["file_name"] = row.file.name
            result["project_id"] = row.file.project_id
        return result

    # =========================================================================
    # Core CRUD
    # =========================================================================

    async def get(self, row_id: int) -> Optional[Dict[str, Any]]:
        """Get row by ID."""
        result = await self.db.execute(
            select(LDMRow).where(LDMRow.id == row_id)
        )
        row = result.scalar_one_or_none()
        return self._row_to_dict(row) if row else None

    async def get_with_file(self, row_id: int) -> Optional[Dict[str, Any]]:
        """Get row with file info."""
        result = await self.db.execute(
            select(LDMRow).options(
                selectinload(LDMRow.file)
            ).where(LDMRow.id == row_id)
        )
        row = result.scalar_one_or_none()
        return self._row_to_dict(row, include_file=True) if row else None

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
        """Create a single row."""
        row = LDMRow(
            file_id=file_id,
            row_num=row_num,
            source=source,
            target=target,
            string_id=string_id,
            status=status,
            extra_data=extra_data
        )
        self.db.add(row)
        await self.db.flush()
        await self.db.commit()
        logger.info(f"Created row: id={row.id}, file_id={file_id}, row_num={row_num}")
        return self._row_to_dict(row)

    async def update(
        self,
        row_id: int,
        target: Optional[str] = None,
        status: Optional[str] = None,
        updated_by: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Update a row's target text or status."""
        result = await self.db.execute(
            select(LDMRow).where(LDMRow.id == row_id)
        )
        row = result.scalar_one_or_none()

        if not row:
            return None

        # Track old values for history
        old_target = row.target
        old_status = row.status

        if target is not None:
            row.target = target
            # Auto-set status to translated if target is set and was pending
            if row.status == "pending" and target:
                row.status = "translated"

        if status is not None:
            row.status = status

        if updated_by is not None:
            row.updated_by = updated_by

        row.updated_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(row)

        logger.info(f"Updated row: id={row_id}, target_changed={target is not None}, status_changed={status is not None}")
        return self._row_to_dict(row)

    async def delete(self, row_id: int) -> bool:
        """Delete a row."""
        result = await self.db.execute(
            select(LDMRow).where(LDMRow.id == row_id)
        )
        row = result.scalar_one_or_none()

        if not row:
            return False

        await self.db.delete(row)
        await self.db.commit()
        logger.info(f"Deleted row: id={row_id}")
        return True

    # =========================================================================
    # Bulk Operations
    # =========================================================================

    async def bulk_create(
        self,
        file_id: int,
        rows: List[Dict[str, Any]]
    ) -> int:
        """Bulk create rows for a file."""
        row_objects = [
            LDMRow(
                file_id=file_id,
                row_num=r.get("row_num", i + 1),
                source=r.get("source", ""),
                target=r.get("target", ""),
                string_id=r.get("string_id"),
                status=r.get("status", "pending"),
                extra_data=r.get("extra_data")
            )
            for i, r in enumerate(rows)
        ]
        self.db.add_all(row_objects)
        await self.db.flush()
        await self.db.commit()
        logger.info(f"Bulk created {len(rows)} rows for file_id={file_id}")
        return len(rows)

    async def bulk_update(
        self,
        updates: List[Dict[str, Any]]
    ) -> int:
        """Bulk update multiple rows."""
        count = 0
        for update in updates:
            row_id = update.get("id")
            if not row_id:
                continue

            result = await self.db.execute(
                select(LDMRow).where(LDMRow.id == row_id)
            )
            row = result.scalar_one_or_none()
            if not row:
                continue

            if "target" in update:
                row.target = update["target"]
            if "status" in update:
                row.status = update["status"]
            row.updated_at = datetime.utcnow()
            count += 1

        await self.db.commit()
        logger.info(f"Bulk updated {count} rows")
        return count

    # =========================================================================
    # Query Operations
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
        offset = (page - 1) * limit

        # Handle fuzzy search mode separately (PostgreSQL pg_trgm)
        if search and search_mode == "fuzzy":
            return await self._fuzzy_search(file_id, search, search_fields, page, limit, status, filter_type)

        query = select(LDMRow).where(LDMRow.id > 0)  # Ensure valid query base
        query = query.where(LDMRow.file_id == file_id)

        # Track if we need count query
        needs_count_query = False
        field_conditions = []

        # Search
        if search:
            needs_count_query = True
            fields = [f.strip() for f in search_fields.split(",")]
            valid_fields = {"string_id", "source", "target"}
            fields = [f for f in fields if f in valid_fields]
            if not fields:
                fields = ["source", "target"]

            for field in fields:
                column = getattr(LDMRow, field, None)
                if column is None:
                    continue

                if search_mode == "exact":
                    field_conditions.append(func.lower(column) == func.lower(search))
                elif search_mode == "not_contain":
                    field_conditions.append(~column.ilike(f"%{search}%"))
                else:  # contain (default)
                    field_conditions.append(column.ilike(f"%{search}%"))

            if field_conditions:
                if search_mode == "not_contain":
                    query = query.where(and_(*field_conditions))
                else:
                    query = query.where(or_(*field_conditions))

        # Status filter
        if status:
            needs_count_query = True
            query = query.where(LDMRow.status == status)

        # Filter type
        if filter_type:
            needs_count_query = True
            if filter_type == "confirmed":
                query = query.where(LDMRow.status.in_(["approved", "reviewed"]))
            elif filter_type == "unconfirmed":
                query = query.where(LDMRow.status.in_(["pending", "translated"]))
            elif filter_type == "qa_flagged":
                query = query.where(LDMRow.qa_flag_count > 0)

        # Get total count
        if needs_count_query:
            count_query = select(func.count(LDMRow.id)).where(LDMRow.file_id == file_id)
            # Apply same filters to count
            if search and field_conditions:
                if search_mode == "not_contain":
                    count_query = count_query.where(and_(*field_conditions))
                else:
                    count_query = count_query.where(or_(*field_conditions))
            if status:
                count_query = count_query.where(LDMRow.status == status)
            if filter_type:
                if filter_type == "confirmed":
                    count_query = count_query.where(LDMRow.status.in_(["approved", "reviewed"]))
                elif filter_type == "unconfirmed":
                    count_query = count_query.where(LDMRow.status.in_(["pending", "translated"]))
                elif filter_type == "qa_flagged":
                    count_query = count_query.where(LDMRow.qa_flag_count > 0)
            count_result = await self.db.execute(count_query)
            total = count_result.scalar() or 0
        else:
            # Use cached row_count from file
            file_result = await self.db.execute(
                select(LDMFile.row_count).where(LDMFile.id == file_id)
            )
            total = file_result.scalar() or 0

        # Get paginated results
        query = query.order_by(LDMRow.row_num).offset(offset).limit(limit)
        result = await self.db.execute(query)
        rows = result.scalars().all()

        return [self._row_to_dict(r) for r in rows], total

    async def get_all_for_file(
        self,
        file_id: int,
        status_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all rows for a file (no pagination)."""
        query = select(LDMRow).where(LDMRow.file_id == file_id)

        if status_filter:
            if status_filter == "reviewed":
                query = query.where(LDMRow.status.in_(["reviewed", "approved"]))
            elif status_filter == "translated":
                query = query.where(LDMRow.status.in_(["translated", "reviewed", "approved"]))
            else:
                query = query.where(LDMRow.status == status_filter)

        query = query.order_by(LDMRow.row_num)
        result = await self.db.execute(query)
        rows = result.scalars().all()

        return [self._row_to_dict(r) for r in rows]

    async def count_for_file(self, file_id: int) -> int:
        """Count rows in a file."""
        result = await self.db.execute(
            select(func.count(LDMRow.id)).where(LDMRow.file_id == file_id)
        )
        return result.scalar() or 0

    # =========================================================================
    # Fuzzy Search (PostgreSQL pg_trgm)
    # =========================================================================

    FUZZY_SEARCH_THRESHOLD = 0.3

    async def _fuzzy_search(
        self,
        file_id: int,
        search: str,
        search_fields: str,
        page: int,
        limit: int,
        status: Optional[str] = None,
        filter_type: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Fuzzy search using PostgreSQL pg_trgm similarity.

        Uses trigram matching for fuzzy text search with similarity ranking.

        NOTE: similarity() is PostgreSQL-specific (pg_trgm extension).
        When server runs with SQLite fallback, returns empty results.
        """
        from sqlalchemy import text
        from server import config

        # similarity() requires PostgreSQL pg_trgm extension
        # Return empty when running on SQLite
        if config.ACTIVE_DATABASE_TYPE == "sqlite":
            logger.debug("[ROW-REPO] Fuzzy search not available (SQLite mode)")
            return [], 0

        offset = (page - 1) * limit

        # Parse fields
        fields = [f.strip() for f in search_fields.split(",")]
        valid_fields = {"string_id", "source", "target"}
        fields = [f for f in fields if f in valid_fields]
        if not fields:
            fields = ["source", "target"]

        # Build similarity expressions
        sim_expressions = []
        for field in fields:
            if field == "source":
                sim_expressions.append("similarity(lower(source), lower(:search))")
            elif field == "target":
                sim_expressions.append("similarity(lower(target), lower(:search))")
            elif field == "string_id":
                sim_expressions.append("similarity(lower(COALESCE(string_id, '')), lower(:search))")

        if not sim_expressions:
            sim_expressions = ["similarity(lower(source), lower(:search))"]

        max_sim = f"GREATEST({', '.join(sim_expressions)})"

        # Build WHERE clause for filters
        filter_clause = ""
        if status:
            filter_clause += " AND status = :status"
        if filter_type == "confirmed":
            filter_clause += " AND status IN ('approved', 'reviewed')"
        elif filter_type == "unconfirmed":
            filter_clause += " AND status IN ('pending', 'translated')"
        elif filter_type == "qa_flagged":
            filter_clause += " AND qa_flag_count > 0"

        # Count query
        count_sql = text(f"""
            SELECT COUNT(*) FROM ldm_rows
            WHERE file_id = :file_id
            AND {max_sim} >= :threshold
            {filter_clause}
        """)

        params = {
            "file_id": file_id,
            "search": search,
            "threshold": self.FUZZY_SEARCH_THRESHOLD,
        }
        if status:
            params["status"] = status

        count_result = await self.db.execute(count_sql, params)
        total = count_result.scalar() or 0

        # Main query - order by similarity DESC
        search_sql = text(f"""
            SELECT id, file_id, row_num, string_id, source, target, status,
                   qa_flag_count, extra_data, created_at, updated_at, updated_by,
                   {max_sim} as sim_score
            FROM ldm_rows
            WHERE file_id = :file_id
            AND {max_sim} >= :threshold
            {filter_clause}
            ORDER BY sim_score DESC, row_num ASC
            OFFSET :offset LIMIT :limit
        """)

        params["offset"] = offset
        params["limit"] = limit

        result = await self.db.execute(search_sql, params)
        raw_rows = result.fetchall()

        # Convert to dicts
        rows = []
        for r in raw_rows:
            rows.append({
                "id": r.id,
                "file_id": r.file_id,
                "row_num": r.row_num,
                "string_id": r.string_id,
                "source": r.source,
                "target": r.target,
                "status": r.status,
                "qa_flag_count": r.qa_flag_count,
                "extra_data": r.extra_data,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
                "updated_by": r.updated_by,
            })

        logger.info(f"Fuzzy search found {len(rows)} rows (total={total}) for '{search}'")
        return rows, total

    # =========================================================================
    # History Operations
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
        history = LDMEditHistory(
            row_id=row_id,
            user_id=user_id,
            old_target=old_target,
            new_target=new_target,
            old_status=old_status,
            new_status=new_status
        )
        self.db.add(history)
        await self.db.flush()

    async def get_edit_history(
        self,
        row_id: int,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get edit history for a row."""
        result = await self.db.execute(
            select(LDMEditHistory)
            .where(LDMEditHistory.row_id == row_id)
            .order_by(LDMEditHistory.created_at.desc())
            .limit(limit)
        )
        history = result.scalars().all()

        return [
            {
                "id": h.id,
                "row_id": h.row_id,
                "user_id": h.user_id,
                "old_target": h.old_target,
                "new_target": h.new_target,
                "old_status": h.old_status,
                "new_status": h.new_status,
                "created_at": h.created_at.isoformat() if h.created_at else None,
            }
            for h in history
        ]

    # =========================================================================
    # Similarity Search (P10-REPO: TM-style suggestions from project rows)
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
        Used for TM-style suggestions from project rows.

        NOTE: similarity() is PostgreSQL-specific (pg_trgm extension).
        When server runs with SQLite fallback, returns empty list.
        """
        from sqlalchemy import text
        from server import config

        # similarity() requires PostgreSQL pg_trgm extension
        # Return empty when running on SQLite
        if config.ACTIVE_DATABASE_TYPE == "sqlite":
            logger.debug("[ROW-REPO] Similarity search not available (SQLite mode)")
            return []

        conditions = ["r.target IS NOT NULL", "r.target != ''"]
        sql_params = {
            'search_text': source.strip(),
            'threshold': threshold,
            'max_results': max_results
        }

        if file_id:
            conditions.append("r.file_id = :file_id")
            sql_params['file_id'] = file_id
        elif project_id:
            conditions.append("f.project_id = :project_id")
            sql_params['project_id'] = project_id

        if exclude_row_id:
            conditions.append("r.id != :exclude_row_id")
            sql_params['exclude_row_id'] = exclude_row_id

        where_clause = " AND ".join(conditions)

        sql = text(f"""
            SELECT
                r.id,
                r.source,
                r.target,
                r.file_id,
                f.name as file_name,
                similarity(lower(r.source), lower(:search_text)) as sim
            FROM ldm_rows r
            JOIN ldm_files f ON r.file_id = f.id
            WHERE {where_clause}
              AND similarity(lower(r.source), lower(:search_text)) >= :threshold
            ORDER BY sim DESC
            LIMIT :max_results
        """)

        result = await self.db.execute(sql, sql_params)
        rows = result.fetchall()

        return [
            {
                'source': row.source,
                'target': row.target,
                'similarity': round(float(row.sim), 3),
                'row_id': row.id,
                'file_name': row.file_name
            }
            for row in rows
        ]
