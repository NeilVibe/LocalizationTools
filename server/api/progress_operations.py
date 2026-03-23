"""
Progress Operations API

Thin route handlers delegating to ProgressService.
Real-time operation progress tracking endpoints.
Manages ActiveOperation records for live progress monitoring in Task Manager.
"""

from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from server.utils.dependencies import get_async_db, get_current_active_user_async
from server.services.progress_service import ProgressService

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
    completed_steps: Optional[int]

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
    try:
        service = ProgressService(db)
        return await service.create_operation(
            user=current_user,
            tool_name=operation.tool_name,
            function_name=operation.function_name,
            operation_name=operation.operation_name,
            total_steps=operation.total_steps,
            file_info=operation.file_info,
            parameters=operation.parameters
        )
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
    try:
        service = ProgressService(db)
        return await service.get_operations(
            user_id=current_user["user_id"],
            status_filter=status_filter,
            limit=limit
        )
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
    try:
        service = ProgressService(db)
        operation = await service.get_operation(operation_id, current_user["user_id"])

        if not operation:
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
    try:
        service = ProgressService(db)
        operation = await service.update_operation(
            operation_id=operation_id,
            user_id=current_user["user_id"],
            update_data=update_data.model_dump(exclude_unset=True)
        )

        if not operation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Operation {operation_id} not found"
            )

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
    try:
        service = ProgressService(db)
        deleted = await service.delete_operation(operation_id, current_user["user_id"])

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Operation {operation_id} not found"
            )

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
    try:
        service = ProgressService(db)
        deleted_count = await service.cleanup_completed(
            user_id=current_user["user_id"],
            days_old=days_old
        )
        return {"deleted_count": deleted_count, "days_old": days_old}

    except Exception as e:
        logger.error(f"Failed to cleanup operations: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cleanup operations: {str(e)}"
        )


@router.delete("/operations/cleanup/stale", status_code=status.HTTP_200_OK)
async def cleanup_stale_running_operations(
    minutes_old: int = 60,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Cleanup stale running operations.

    Operations that have been "running" for longer than minutes_old
    are likely stuck and should be marked as failed.

    Default: 60 minutes
    """
    try:
        service = ProgressService(db)
        marked_count = await service.cleanup_stale(
            user_id=current_user["user_id"],
            minutes_old=minutes_old
        )
        return {"marked_failed_count": marked_count, "minutes_old": minutes_old}

    except Exception as e:
        logger.error(f"Failed to cleanup stale operations: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cleanup stale operations: {str(e)}"
        )
