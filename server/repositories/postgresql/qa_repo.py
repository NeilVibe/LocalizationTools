"""
PostgreSQL QAResultRepository Implementation.

Full persistence of QA results in PostgreSQL.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update, delete, and_
from loguru import logger

from server.repositories.interfaces.qa_repository import QAResultRepository
from server.database.models import LDMQAResult, LDMRow


class PostgreSQLQAResultRepository(QAResultRepository):
    """PostgreSQL implementation of QAResultRepository."""

    def __init__(self, db: AsyncSession):
        self.db = db

    def _result_to_dict(self, result: LDMQAResult, row: LDMRow = None) -> Dict[str, Any]:
        """Convert SQLAlchemy model to dict."""
        d = {
            "id": result.id,
            "row_id": result.row_id,
            "file_id": result.file_id,
            "check_type": result.check_type,
            "severity": result.severity,
            "message": result.message,
            "details": result.details,
            "created_at": result.created_at.isoformat() if result.created_at else None,
            "resolved_at": result.resolved_at.isoformat() if result.resolved_at else None,
            "resolved_by": result.resolved_by
        }
        # Include row info if provided
        if row:
            d["row_num"] = row.row_num
            d["source"] = row.source[:200] if row.source else None
            d["target"] = row.target[:200] if row.target else None
        return d

    # =========================================================================
    # Query Operations
    # =========================================================================

    async def get(self, result_id: int) -> Optional[Dict[str, Any]]:
        """Get QA result by ID."""
        logger.debug(f"[QA] get called: result_id={result_id}")

        result = await self.db.execute(
            select(LDMQAResult).where(LDMQAResult.id == result_id)
        )
        qa_result = result.scalar_one_or_none()

        if not qa_result:
            return None

        return self._result_to_dict(qa_result)

    async def get_for_row(
        self,
        row_id: int,
        include_resolved: bool = False
    ) -> List[Dict[str, Any]]:
        """Get QA results for a row."""
        logger.debug(f"[QA] get_for_row called: row_id={row_id}, include_resolved={include_resolved}")

        query = select(LDMQAResult).where(LDMQAResult.row_id == row_id)

        if not include_resolved:
            query = query.where(LDMQAResult.resolved_at.is_(None))

        query = query.order_by(LDMQAResult.created_at)

        result = await self.db.execute(query)
        qa_results = result.scalars().all()

        logger.debug(f"[QA] get_for_row result: row_id={row_id}, count={len(qa_results)}")
        return [self._result_to_dict(r) for r in qa_results]

    async def get_for_file(
        self,
        file_id: int,
        check_type: Optional[str] = None,
        include_resolved: bool = False
    ) -> List[Dict[str, Any]]:
        """Get QA results for a file with row info."""
        logger.debug(f"[QA] get_for_file called: file_id={file_id}, check_type={check_type}")

        query = (
            select(LDMQAResult, LDMRow)
            .join(LDMRow, LDMQAResult.row_id == LDMRow.id)
            .where(LDMQAResult.file_id == file_id)
        )

        if not include_resolved:
            query = query.where(LDMQAResult.resolved_at.is_(None))

        if check_type:
            query = query.where(LDMQAResult.check_type == check_type)

        query = query.order_by(LDMRow.row_num, LDMQAResult.created_at)

        result = await self.db.execute(query)
        rows = result.all()

        results = [self._result_to_dict(qa_result, row) for qa_result, row in rows]
        logger.debug(f"[QA] get_for_file result: file_id={file_id}, count={len(results)}")
        return results

    async def get_summary(self, file_id: int) -> Dict[str, Any]:
        """Get QA summary for a file."""
        logger.debug(f"[QA] get_summary called: file_id={file_id}")

        # Count issues by check type
        result = await self.db.execute(
            select(
                LDMQAResult.check_type,
                func.count(LDMQAResult.id).label("count")
            )
            .where(
                LDMQAResult.file_id == file_id,
                LDMQAResult.resolved_at.is_(None)
            )
            .group_by(LDMQAResult.check_type)
        )
        counts = {row.check_type: row.count for row in result.all()}

        # Get last checked time
        result = await self.db.execute(
            select(func.max(LDMRow.qa_checked_at))
            .where(LDMRow.file_id == file_id)
        )
        last_checked = result.scalar()

        total = sum(counts.values())

        summary = {
            "file_id": file_id,
            "line": counts.get("line", 0),
            "term": counts.get("term", 0),
            "pattern": counts.get("pattern", 0),
            "character": counts.get("character", 0),
            "grammar": counts.get("grammar", 0),
            "total": total,
            "last_checked": last_checked.isoformat() if last_checked else None
        }

        logger.debug(f"[QA] get_summary result: file_id={file_id}, total={total}")
        return summary

    # =========================================================================
    # Write Operations
    # =========================================================================

    async def create(
        self,
        row_id: int,
        file_id: int,
        check_type: str,
        severity: str,
        message: str,
        details: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Create a new QA result."""
        logger.debug(f"[QA] create called: row_id={row_id}, check_type={check_type}")

        qa_result = LDMQAResult(
            row_id=row_id,
            file_id=file_id,
            check_type=check_type,
            severity=severity,
            message=message,
            details=details,
            created_at=datetime.utcnow()
        )

        self.db.add(qa_result)
        await self.db.flush()

        logger.success(f"[QA] Created: id={qa_result.id}, row_id={row_id}, check_type={check_type}")
        return self._result_to_dict(qa_result)

    async def bulk_create(
        self,
        results: List[Dict[str, Any]]
    ) -> int:
        """Bulk create QA results."""
        logger.debug(f"[QA] bulk_create called: count={len(results)}")

        if not results:
            return 0

        created_at = datetime.utcnow()
        qa_results = []

        for r in results:
            qa_result = LDMQAResult(
                row_id=r["row_id"],
                file_id=r["file_id"],
                check_type=r["check_type"],
                severity=r["severity"],
                message=r["message"],
                details=r.get("details"),
                created_at=created_at
            )
            self.db.add(qa_result)
            qa_results.append(qa_result)

        await self.db.flush()

        logger.success(f"[QA] Bulk created: count={len(qa_results)}")
        return len(qa_results)

    async def resolve(
        self,
        result_id: int,
        resolved_by: int
    ) -> Optional[Dict[str, Any]]:
        """Mark a QA result as resolved."""
        logger.debug(f"[QA] resolve called: result_id={result_id}, resolved_by={resolved_by}")

        result = await self.db.execute(
            select(LDMQAResult).where(LDMQAResult.id == result_id)
        )
        qa_result = result.scalar_one_or_none()

        if not qa_result:
            logger.warning(f"[QA] Resolve target not found: result_id={result_id}")
            return None

        if qa_result.resolved_at:
            logger.debug(f"[QA] Already resolved: result_id={result_id}")
            return self._result_to_dict(qa_result)

        qa_result.resolved_at = datetime.utcnow()
        qa_result.resolved_by = resolved_by

        await self.db.flush()

        # Update row's QA count
        await self.update_row_qa_count(qa_result.row_id)

        await self.db.commit()

        logger.success(f"[QA] Resolved: result_id={result_id}")
        return self._result_to_dict(qa_result)

    async def delete_unresolved_for_row(self, row_id: int) -> int:
        """Delete all unresolved QA results for a row."""
        logger.debug(f"[QA] delete_unresolved_for_row called: row_id={row_id}")

        result = await self.db.execute(
            delete(LDMQAResult).where(
                and_(
                    LDMQAResult.row_id == row_id,
                    LDMQAResult.resolved_at.is_(None)
                )
            )
        )

        count = result.rowcount
        logger.debug(f"[QA] Deleted unresolved: row_id={row_id}, count={count}")
        return count

    async def delete_for_file(self, file_id: int) -> int:
        """Delete all QA results for a file."""
        logger.debug(f"[QA] delete_for_file called: file_id={file_id}")

        result = await self.db.execute(
            delete(LDMQAResult).where(LDMQAResult.file_id == file_id)
        )

        count = result.rowcount
        logger.success(f"[QA] Deleted for file: file_id={file_id}, count={count}")
        return count

    # =========================================================================
    # Utility Operations
    # =========================================================================

    async def count_unresolved_for_row(self, row_id: int) -> int:
        """Count unresolved QA issues for a row."""
        result = await self.db.execute(
            select(func.count(LDMQAResult.id))
            .where(
                LDMQAResult.row_id == row_id,
                LDMQAResult.resolved_at.is_(None)
            )
        )
        return result.scalar() or 0

    async def update_row_qa_count(self, row_id: int) -> None:
        """Update the row's qa_flag_count field."""
        count = await self.count_unresolved_for_row(row_id)

        await self.db.execute(
            update(LDMRow)
            .where(LDMRow.id == row_id)
            .values(qa_flag_count=count)
        )

        logger.debug(f"[QA] Updated row QA count: row_id={row_id}, count={count}")
