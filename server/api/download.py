"""
File Download API
Allows downloading result files from completed operations
"""

import os
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from server.database.models import ActiveOperation
from server.utils.dependencies import get_async_db, get_current_active_user_async

router = APIRouter(prefix="/api/download", tags=["File Download"])


@router.get("/operation/{operation_id}")
async def download_operation_result(
    operation_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Download result file(s) from a completed operation.

    Returns the first output file from the operation's output directory.
    """
    logger.info(f"Download request for operation {operation_id} from user {current_user['username']}")

    try:
        # Get operation from database
        result = await db.execute(
            select(ActiveOperation).where(ActiveOperation.operation_id == operation_id)
        )
        operation = result.scalar_one_or_none()

        if not operation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Operation {operation_id} not found"
            )

        # Check user owns this operation
        if operation.user_id != current_user['user_id']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to download this operation's results"
            )

        # Check operation is completed
        if operation.status != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Operation is not completed yet (status: {operation.status})"
            )

        # Check output_dir exists
        if not operation.output_dir:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No output files available for this operation"
            )

        # Get first file from output directory
        output_dir = operation.output_dir
        if not os.path.exists(output_dir):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Output directory not found: {output_dir}"
            )

        # List files in directory
        files = [f for f in os.listdir(output_dir) if os.path.isfile(os.path.join(output_dir, f))]
        if not files:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No output files found in directory"
            )

        # Return first file (usually only one for XLSTransfer)
        file_path = os.path.join(output_dir, files[0])

        logger.success(f"Serving file {files[0]} for operation {operation_id}")

        return FileResponse(
            path=file_path,
            filename=files[0],
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Download failed for operation {operation_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to download file: {str(e)}"
        )
