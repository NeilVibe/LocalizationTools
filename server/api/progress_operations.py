"""
Progress Operations API

Real-time operation progress tracking endpoints.
Manages ActiveOperation records for live progress monitoring in Task Manager.
"""

from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from server.database.models import ActiveOperation, User
from server.utils.dependencies import get_async_db, get_current_active_user_async
from server.utils.websocket import (
    emit_operation_start,
    emit_progress_update,
    emit_operation_complete,
    emit_operation_failed
)

router = APIRouter(prefix="/api/progress", tags=["Progress Operations"])


# ============================================================================
# Pydantic Models
# ============================================================================

class OperationCreate(BaseModel):
    """Request model for creating a new operation."""
    tool_name: str = Field(..., max_length=50, description="Tool name (e.g., 'XLSTransfer')")
    function_name: str = Field(..., max_length=100, description="Function name (e.g., 'transfer_to_excel')")
    operation_name: str = Field(..., max_length=200, description="Human-readable operation name")
    total_steps: Optional[int] = Field(None, description="Total number of steps if known")
    file_info: Optional[dict] = Field(None, description="File metadata being processed")
    parameters: Optional[dict] = Field(None, description="Operation parameters")


class OperationUpdate(BaseModel):
    """Request model for updating operation progress."""
    status: Optional[str] = Field(None, description="running, completed, failed, cancelled")
    progress_percentage: Optional[float] = Field(None, ge=0.0, le=100.0, description="0.0 to 100.0")
    current_step: Optional[str] = Field(None, max_length=200, description="Current step description")
    completed_steps: Optional[int] = Field(None, description="Number of completed steps")
    estimated_completion: Optional[datetime] = Field(None, description="Estimated completion time")
    error_message: Optional[str] = Field(None, description="Error message if failed")


class OperationResponse(BaseModel):
    """Response model for operation data."""
    operation_id: int
    user_id: int
    username: str
    session_id: Optional[str]

    tool_name: str
    function_name: str
    operation_name: str

    status: str
    progress_percentage: float
    current_step: Optional[str]
    total_steps: Optional[int]
    completed_steps: Optional[int]  # Changed from int to Optional[int]

    started_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]
    estimated_completion: Optional[datetime]

    file_info: Optional[dict]
    parameters: Optional[dict]
    error_message: Optional[str]

    # Result files
    output_dir: Optional[str]
    output_files: Optional[list]

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() + 'Z' if v else None
        }


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/operations", response_model=OperationResponse, status_code=status.HTTP_201_CREATED)
async def create_operation(
    operation: OperationCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Create a new active operation.

    Called when a long-running operation starts to create a tracking record.
    """
    logger.info(f"Creating operation: {operation.operation_name} for user {current_user['username']}")

    try:
        # Create new operation record
        new_operation = ActiveOperation(
            user_id=current_user["user_id"],
            username=current_user["username"],
            session_id=None,  # TODO: Get from session context if available
            tool_name=operation.tool_name,
            function_name=operation.function_name,
            operation_name=operation.operation_name,
            status="running",
            progress_percentage=0.0,
            total_steps=operation.total_steps,
            completed_steps=0,
            file_info=operation.file_info,
            parameters=operation.parameters,
            started_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        db.add(new_operation)
        await db.commit()
        await db.refresh(new_operation)

        logger.success(f"Operation created: ID={new_operation.operation_id}, Name={operation.operation_name}")

        # Emit WebSocket event for operation start
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

    except Exception as e:
        logger.error(f"Failed to create operation: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create operation: {str(e)}"
        )


@router.get("/operations", response_model=List[OperationResponse])
async def get_operations(
    status_filter: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Get all operations for current user.

    Optional status filter: running, completed, failed, cancelled
    """
    logger.info(f"Fetching operations for user {current_user['username']}, status={status_filter}")

    try:
        query = select(ActiveOperation).where(ActiveOperation.user_id == current_user["user_id"])

        if status_filter:
            query = query.where(ActiveOperation.status == status_filter)

        query = query.order_by(ActiveOperation.started_at.desc()).limit(limit)

        result = await db.execute(query)
        operations = result.scalars().all()

        logger.info(f"Found {len(operations)} operations for user {current_user['username']}")

        return operations

    except Exception as e:
        logger.error(f"Failed to fetch operations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch operations: {str(e)}"
        )


@router.get("/operations/{operation_id}", response_model=OperationResponse)
async def get_operation(
    operation_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """Get specific operation by ID."""
    logger.info(f"Fetching operation {operation_id} for user {current_user['username']}")

    try:
        query = select(ActiveOperation).where(
            ActiveOperation.operation_id == operation_id,
            ActiveOperation.user_id == current_user["user_id"]
        )
        result = await db.execute(query)
        operation = result.scalar_one_or_none()

        if not operation:
            logger.warning(f"Operation {operation_id} not found for user {current_user['username']}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Operation {operation_id} not found"
            )

        return operation

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch operation {operation_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch operation: {str(e)}"
        )


@router.put("/operations/{operation_id}", response_model=OperationResponse)
async def update_operation(
    operation_id: int,
    update_data: OperationUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Update operation progress.

    Called periodically during operation execution to update progress.
    """
    logger.info(f"Updating operation {operation_id}: progress={update_data.progress_percentage}, status={update_data.status}")

    try:
        # Fetch operation
        query = select(ActiveOperation).where(
            ActiveOperation.operation_id == operation_id,
            ActiveOperation.user_id == current_user["user_id"]
        )
        result = await db.execute(query)
        operation = result.scalar_one_or_none()

        if not operation:
            logger.warning(f"Operation {operation_id} not found for user {current_user['username']}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Operation {operation_id} not found"
            )

        # Update fields
        update_dict = update_data.model_dump(exclude_unset=True)

        for field, value in update_dict.items():
            setattr(operation, field, value)

        operation.updated_at = datetime.utcnow()

        # If status changed to completed/failed, set completed_at
        if update_data.status in ["completed", "failed", "cancelled"] and not operation.completed_at:
            operation.completed_at = datetime.utcnow()

        await db.commit()
        await db.refresh(operation)

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

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update operation {operation_id}: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update operation: {str(e)}"
        )


@router.delete("/operations/{operation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_operation(
    operation_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """Delete operation record."""
    logger.info(f"Deleting operation {operation_id} for user {current_user['username']}")

    try:
        query = delete(ActiveOperation).where(
            ActiveOperation.operation_id == operation_id,
            ActiveOperation.user_id == current_user["user_id"]
        )
        result = await db.execute(query)
        await db.commit()

        if result.rowcount == 0:
            logger.warning(f"Operation {operation_id} not found for user {current_user['username']}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Operation {operation_id} not found"
            )

        logger.success(f"Operation {operation_id} deleted")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete operation {operation_id}: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete operation: {str(e)}"
        )


@router.delete("/operations/cleanup/completed", status_code=status.HTTP_200_OK)
async def cleanup_completed_operations(
    days_old: int = 7,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Clean up old completed/failed operations.

    Removes operations completed more than `days_old` days ago.
    """
    logger.info(f"Cleaning up operations older than {days_old} days for user {current_user['username']}")

    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)

        query = delete(ActiveOperation).where(
            ActiveOperation.user_id == current_user["user_id"],
            ActiveOperation.status.in_(["completed", "failed", "cancelled"]),
            ActiveOperation.completed_at < cutoff_date
        )

        result = await db.execute(query)
        await db.commit()

        deleted_count = result.rowcount
        logger.success(f"Cleaned up {deleted_count} old operations for user {current_user['username']}")

        return {"deleted_count": deleted_count, "days_old": days_old}

    except Exception as e:
        logger.error(f"Failed to cleanup operations: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cleanup operations: {str(e)}"
        )


# Missing import for cleanup endpoint
from datetime import timedelta
