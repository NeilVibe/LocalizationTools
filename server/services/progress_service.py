"""
Progress Service - Operation progress tracking and lifecycle management.

Extracts business logic from progress_operations routes.
Uses AsyncSession for database operations.

Usage:
    from server.services.progress_service import ProgressService

    service = ProgressService(db)
    operation = await service.create_operation(user, tool_name="XLSTransfer", ...)
    operations = await service.get_operations(user_id=1)
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from server.database.models import ActiveOperation
from server.utils.websocket import (
    emit_operation_start,
    emit_progress_update,
    emit_operation_complete,
    emit_operation_failed
)


class ProgressService:
    """Service layer for operation progress tracking."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_operation(
        self,
        user: dict,
        tool_name: str,
        function_name: str,
        operation_name: str,
        total_steps: Optional[int] = None,
        file_info: Optional[dict] = None,
        parameters: Optional[dict] = None
    ) -> ActiveOperation:
        """
        Create a new active operation record and emit WebSocket start event.

        Args:
            user: Current user dict with user_id, username
            tool_name: Tool name (e.g., 'XLSTransfer')
            function_name: Function name (e.g., 'transfer_to_excel')
            operation_name: Human-readable operation name
            total_steps: Total number of steps if known
            file_info: File metadata being processed
            parameters: Operation parameters

        Returns:
            The created ActiveOperation model instance.

        Raises:
            Exception: On database or WebSocket errors (caller wraps with HTTPException).
        """
        logger.info(f"Creating operation: {operation_name} for user {user['username']}")

        new_operation = ActiveOperation(
            user_id=user["user_id"],
            username=user["username"],
            session_id=None,
            tool_name=tool_name,
            function_name=function_name,
            operation_name=operation_name,
            status="running",
            progress_percentage=0.0,
            total_steps=total_steps,
            completed_steps=0,
            file_info=file_info,
            parameters=parameters,
            started_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        self.db.add(new_operation)
        await self.db.commit()
        await self.db.refresh(new_operation)

        logger.success(f"Operation created: ID={new_operation.operation_id}, Name={operation_name}")

        await emit_operation_start({
            'operation_id': new_operation.operation_id,
            'user_id': new_operation.user_id,
            'username': new_operation.username,
            'tool_name': new_operation.tool_name,
            'function_name': new_operation.function_name,
            'operation_name': new_operation.operation_name,
            'status': new_operation.status,
            'progress_percentage': new_operation.progress_percentage,
            'started_at': new_operation.started_at.isoformat(),
            'file_info': new_operation.file_info,
            'parameters': new_operation.parameters
        })

        return new_operation

    async def get_operations(
        self,
        user_id: int,
        status_filter: Optional[str] = None,
        limit: int = 50
    ) -> List[ActiveOperation]:
        """
        Get all operations for a user.

        Args:
            user_id: User ID to filter by
            status_filter: Optional status filter (running, completed, failed, cancelled)
            limit: Maximum number of results

        Returns:
            List of ActiveOperation model instances.
        """
        query = select(ActiveOperation).where(ActiveOperation.user_id == user_id)

        if status_filter:
            query = query.where(ActiveOperation.status == status_filter)

        query = query.order_by(ActiveOperation.started_at.desc()).limit(limit)

        result = await self.db.execute(query)
        operations = result.scalars().all()

        logger.info(f"Found {len(operations)} operations for user_id={user_id}")
        return operations

    async def get_operation(self, operation_id: int, user_id: int) -> Optional[ActiveOperation]:
        """
        Get a single operation by ID, scoped to user.

        Returns:
            ActiveOperation if found, None otherwise.
        """
        query = select(ActiveOperation).where(
            ActiveOperation.operation_id == operation_id,
            ActiveOperation.user_id == user_id
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def update_operation(
        self,
        operation_id: int,
        user_id: int,
        update_data: Dict[str, Any]
    ) -> Optional[ActiveOperation]:
        """
        Update operation progress and emit appropriate WebSocket events.

        Args:
            operation_id: Operation ID
            user_id: User ID (for ownership check)
            update_data: Dict of fields to update (from model_dump(exclude_unset=True))

        Returns:
            Updated ActiveOperation if found, None otherwise.

        Raises:
            Exception: On database or WebSocket errors (caller wraps with HTTPException).
        """
        logger.info(f"Updating operation {operation_id}: {update_data}")

        query = select(ActiveOperation).where(
            ActiveOperation.operation_id == operation_id,
            ActiveOperation.user_id == user_id
        )
        result = await self.db.execute(query)
        operation = result.scalar_one_or_none()

        if not operation:
            return None

        # Update fields
        for field, value in update_data.items():
            setattr(operation, field, value)

        operation.updated_at = datetime.utcnow()

        # If status changed to completed/failed, set completed_at
        new_status = update_data.get("status")
        if new_status in ["completed", "failed", "cancelled"] and not operation.completed_at:
            operation.completed_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(operation)

        logger.success(f"Operation {operation_id} updated: {operation.progress_percentage}% complete")

        # Emit WebSocket event based on status
        operation_data = {
            'operation_id': operation.operation_id,
            'user_id': operation.user_id,
            'username': operation.username,
            'tool_name': operation.tool_name,
            'function_name': operation.function_name,
            'operation_name': operation.operation_name,
            'status': operation.status,
            'progress_percentage': operation.progress_percentage,
            'current_step': operation.current_step,
            'total_steps': operation.total_steps,
            'completed_steps': operation.completed_steps,
            'started_at': operation.started_at.isoformat(),
            'updated_at': operation.updated_at.isoformat(),
            'completed_at': operation.completed_at.isoformat() if operation.completed_at else None,
            'estimated_completion': operation.estimated_completion.isoformat() if operation.estimated_completion else None,
            'error_message': operation.error_message,
            'file_info': operation.file_info,
            'parameters': operation.parameters
        }

        if operation.status == "completed":
            await emit_operation_complete(operation_data)
        elif operation.status == "failed":
            await emit_operation_failed(operation_data)
        else:
            await emit_progress_update(operation_data)

        return operation

    async def delete_operation(self, operation_id: int, user_id: int) -> bool:
        """
        Delete an operation record.

        Returns:
            True if deleted, False if not found.
        """
        query = delete(ActiveOperation).where(
            ActiveOperation.operation_id == operation_id,
            ActiveOperation.user_id == user_id
        )
        result = await self.db.execute(query)
        await self.db.commit()

        if result.rowcount == 0:
            return False

        logger.success(f"Operation {operation_id} deleted")
        return True

    async def cleanup_completed(self, user_id: int, days_old: int = 7) -> int:
        """
        Clean up old completed/failed/cancelled operations.

        Args:
            user_id: User ID
            days_old: Remove operations completed more than this many days ago

        Returns:
            Number of deleted operations.
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)

        query = delete(ActiveOperation).where(
            ActiveOperation.user_id == user_id,
            ActiveOperation.status.in_(["completed", "failed", "cancelled"]),
            ActiveOperation.completed_at < cutoff_date
        )

        result = await self.db.execute(query)
        await self.db.commit()

        deleted_count = result.rowcount
        logger.success(f"Cleaned up {deleted_count} old operations for user_id={user_id}")
        return deleted_count

    async def cleanup_stale(self, user_id: int, minutes_old: int = 60) -> int:
        """
        Mark stale running operations as failed.

        Operations that have been "running" for longer than minutes_old
        are likely stuck and get marked as failed.

        Args:
            user_id: User ID
            minutes_old: Threshold in minutes

        Returns:
            Number of operations marked as failed.
        """
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes_old)

        update_query = (
            update(ActiveOperation)
            .where(
                ActiveOperation.user_id == user_id,
                ActiveOperation.status == "running",
                ActiveOperation.started_at < cutoff_time
            )
            .values(
                status="failed",
                error_message=f"Automatically marked as failed (stale after {minutes_old} minutes)",
                completed_at=datetime.utcnow()
            )
        )

        result = await self.db.execute(update_query)
        await self.db.commit()

        marked_count = result.rowcount
        logger.success(f"Marked {marked_count} stale operations as failed for user_id={user_id}")
        return marked_count
