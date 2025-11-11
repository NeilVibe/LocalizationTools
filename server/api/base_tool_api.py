"""
Base Tool API - Common patterns for all tool endpoints

This base class extracts common patterns from tool APIs (like XLSTransfer)
to reduce code duplication and enable rapid addition of new apps.

Goal: Reduce per-app API code from ~1000+ lines to ~150 lines (85% reduction)

Usage:
    class MyToolAPI(BaseToolAPI):
        def __init__(self):
            super().__init__(
                tool_name="MyTool",
                router_prefix="/api/v2/mytool",
                temp_dir="/tmp/mytool_test"
            )
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any, Callable
from pathlib import Path
from datetime import datetime
import asyncio
import time
import os
import sys

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from server.utils.dependencies import get_async_db, get_current_active_user_async
from server.database.models import User, ActiveOperation
from server.utils.websocket import (
    emit_operation_start,
    emit_progress_update,
    emit_operation_complete,
    emit_operation_failed
)
from loguru import logger
import server.config as config


class BaseToolAPI:
    """
    Base class for all tool APIs providing common functionality.

    Reduces boilerplate code by 85% through shared patterns:
    - User authentication extraction
    - ActiveOperation management
    - WebSocket event emission
    - File upload handling
    - Error handling and logging
    - Background task execution
    - Response formatting
    """

    def __init__(
        self,
        tool_name: str,
        router_prefix: str,
        temp_dir: str = "/tmp/tool_test",
        router_tags: Optional[List[str]] = None
    ):
        """
        Initialize base tool API.

        Args:
            tool_name: Display name for the tool (e.g., "XLSTransfer")
            router_prefix: API route prefix (e.g., "/api/v2/xlstransfer")
            temp_dir: Temporary directory for file uploads
            router_tags: Tags for OpenAPI documentation
        """
        self.tool_name = tool_name
        self.router_prefix = router_prefix
        self.temp_dir = Path(temp_dir)
        self.router = APIRouter(
            prefix=router_prefix,
            tags=router_tags or [tool_name]
        )

        logger.info(f"Initialized {tool_name} API", {
            "tool": tool_name,
            "prefix": router_prefix,
            "temp_dir": str(temp_dir)
        })

    # ========================================================================
    # USER AUTHENTICATION HELPERS
    # ========================================================================

    def extract_user_info(self, current_user: Any) -> Dict[str, Any]:
        """
        Extract username and user_id from current_user (works with dict or object).

        Args:
            current_user: User object from Depends(get_current_active_user_async)

        Returns:
            Dict with 'username' and 'user_id' keys
        """
        if isinstance(current_user, dict):
            username = current_user.get("username", "unknown")
            user_id = current_user.get("user_id")
        else:
            username = getattr(current_user, "username", "unknown")
            user_id = getattr(current_user, "user_id", None)

        return {"username": username, "user_id": user_id}

    # ========================================================================
    # ACTIVE OPERATION MANAGEMENT
    # ========================================================================

    async def create_operation(
        self,
        db: AsyncSession,
        user_info: Dict[str, Any],
        function_name: str,
        operation_name: str,
        file_info: Optional[Dict[str, Any]] = None
    ) -> ActiveOperation:
        """
        Create ActiveOperation record for progress tracking.

        Args:
            db: Database session
            user_info: Dict with 'username' and 'user_id'
            function_name: Function being executed (e.g., "create_dictionary")
            operation_name: Human-readable name (e.g., "Create Dictionary (2 files)")
            file_info: Optional metadata about files being processed

        Returns:
            Created ActiveOperation object
        """
        operation = ActiveOperation(
            user_id=user_info["user_id"],
            username=user_info["username"],
            tool_name=self.tool_name,
            function_name=function_name,
            operation_name=operation_name,
            status="running",
            progress_percentage=0.0,
            completed_steps=0,
            file_info=file_info or {},
            started_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        db.add(operation)
        await db.commit()
        await db.refresh(operation)

        logger.success(f"Created ActiveOperation: ID={operation.operation_id}", {
            "operation_id": operation.operation_id,
            "tool": self.tool_name,
            "function": function_name,
            "user": user_info["username"]
        })

        return operation

    async def emit_start_event(
        self,
        operation: ActiveOperation,
        user_info: Dict[str, Any]
    ):
        """
        Emit WebSocket event for operation start.

        Args:
            operation: ActiveOperation record
            user_info: Dict with 'username' and 'user_id'
        """
        await emit_operation_start({
            'operation_id': operation.operation_id,
            'user_id': user_info["user_id"],
            'username': user_info["username"],
            'tool_name': self.tool_name,
            'function_name': operation.function_name,
            'operation_name': operation.operation_name,
            'status': 'running',
            'progress_percentage': 0.0,
            'started_at': operation.started_at.isoformat() + 'Z'
        })

    async def mark_operation_failed(
        self,
        db: AsyncSession,
        operation: ActiveOperation,
        user_info: Dict[str, Any],
        error: Exception
    ):
        """
        Mark operation as failed and emit WebSocket event.

        Args:
            db: Database session
            operation: ActiveOperation record
            user_info: Dict with 'username' and 'user_id'
            error: Exception that caused the failure
        """
        operation.status = "failed"
        operation.error_message = str(error)
        operation.completed_at = datetime.utcnow()
        operation.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(operation)

        # Emit WebSocket event for operation failure
        await emit_operation_failed({
            'operation_id': operation.operation_id,
            'user_id': user_info["user_id"],
            'username': user_info["username"],
            'tool_name': self.tool_name,
            'function_name': operation.function_name,
            'operation_name': operation.operation_name,
            'status': 'failed',
            'error_message': str(error),
            'started_at': operation.started_at.isoformat() + 'Z',
            'completed_at': operation.completed_at.isoformat() + 'Z'
        })

        logger.error(f"Operation {operation.operation_id} failed: {str(error)}", {
            "operation_id": operation.operation_id,
            "tool": self.tool_name,
            "function": operation.function_name,
            "error": str(error),
            "error_type": type(error).__name__
        })

    def mark_operation_complete_sync(
        self,
        operation_id: int,
        user_info: Dict[str, Any],
        function_name: str,
        operation_name: str,
        result_data: Optional[Dict[str, Any]] = None
    ):
        """
        Mark operation as completed (synchronous, for background tasks).

        Args:
            operation_id: ID of the operation
            user_info: Dict with 'username' and 'user_id'
            function_name: Function name
            operation_name: Operation name
            result_data: Optional result data to include in event
        """
        try:
            # Create synchronous database session
            engine = create_engine(
                config.DATABASE_URL,
                connect_args={"check_same_thread": False} if "sqlite" in config.DATABASE_URL else {}
            )
            db_session = Session(engine)

            try:
                operation = db_session.query(ActiveOperation).filter(
                    ActiveOperation.operation_id == operation_id
                ).first()

                if operation:
                    operation.status = "completed"
                    operation.progress_percentage = 100.0
                    operation.completed_at = datetime.utcnow()
                    operation.updated_at = datetime.utcnow()
                    db_session.commit()

                    # Emit WebSocket completion event
                    event_data = {
                        'operation_id': operation_id,
                        'user_id': user_info["user_id"],
                        'username': user_info["username"],
                        'tool_name': self.tool_name,
                        'function_name': function_name,
                        'operation_name': operation_name,
                        'status': 'completed',
                        'progress_percentage': 100.0,
                        'started_at': operation.started_at.isoformat() + 'Z',
                        'completed_at': operation.completed_at.isoformat() + 'Z'
                    }

                    if result_data:
                        event_data.update(result_data)

                    asyncio.run(emit_operation_complete(event_data))

                    logger.success(f"Operation {operation_id} completed", {
                        "operation_id": operation_id,
                        "tool": self.tool_name,
                        "function": function_name
                    })
            finally:
                db_session.close()

        except Exception as e:
            logger.error(f"Failed to mark operation {operation_id} as complete: {e}")

    def mark_operation_failed_sync(
        self,
        operation_id: int,
        user_info: Dict[str, Any],
        function_name: str,
        operation_name: str,
        error: Exception
    ):
        """
        Mark operation as failed (synchronous, for background tasks).

        Args:
            operation_id: ID of the operation
            user_info: Dict with 'username' and 'user_id'
            function_name: Function name
            operation_name: Operation name
            error: Exception that caused the failure
        """
        try:
            engine = create_engine(
                config.DATABASE_URL,
                connect_args={"check_same_thread": False} if "sqlite" in config.DATABASE_URL else {}
            )
            db_session = Session(engine)

            try:
                operation = db_session.query(ActiveOperation).filter(
                    ActiveOperation.operation_id == operation_id
                ).first()

                if operation:
                    operation.status = "failed"
                    operation.error_message = str(error)
                    operation.completed_at = datetime.utcnow()
                    operation.updated_at = datetime.utcnow()
                    db_session.commit()

                    # Emit WebSocket failure event
                    asyncio.run(emit_operation_failed({
                        'operation_id': operation_id,
                        'user_id': user_info["user_id"],
                        'username': user_info["username"],
                        'tool_name': self.tool_name,
                        'function_name': function_name,
                        'operation_name': operation_name,
                        'status': 'failed',
                        'error_message': str(error),
                        'started_at': operation.started_at.isoformat() + 'Z' if operation.started_at else None,
                        'completed_at': operation.completed_at.isoformat() + 'Z' if operation.completed_at else None
                    }))

                    logger.error(f"Operation {operation_id} failed: {str(error)}", {
                        "operation_id": operation_id,
                        "tool": self.tool_name,
                        "function": function_name,
                        "error": str(error),
                        "error_type": type(error).__name__
                    })
            finally:
                db_session.close()

        except Exception as db_error:
            logger.error(f"Failed to update operation {operation_id} status: {db_error}")

    # ========================================================================
    # FILE UPLOAD HANDLING
    # ========================================================================

    async def save_uploaded_files(
        self,
        files: List[UploadFile],
        log_prefix: str = "Uploaded file"
    ) -> List[str]:
        """
        Save uploaded files to temp directory and return paths.

        Args:
            files: List of UploadFile objects from FastAPI
            log_prefix: Prefix for log messages

        Returns:
            List of saved file paths
        """
        self.temp_dir.mkdir(exist_ok=True, parents=True)

        logger.info(f"Saving {len(files)} files to temp directory", {
            "file_count": len(files),
            "temp_dir": str(self.temp_dir)
        })

        file_paths = []
        for i, file in enumerate(files, 1):
            file_path = self.temp_dir / file.filename

            with open(file_path, "wb") as f:
                content = await file.read()
                file_size = len(content)
                f.write(content)

            file_paths.append(str(file_path))

            logger.info(f"{log_prefix} {i}/{len(files)}: {file.filename}", {
                "filename": file.filename,
                "size_bytes": file_size,
                "path": str(file_path)
            })

        return file_paths

    # ========================================================================
    # RESPONSE FORMATTING
    # ========================================================================

    def success_response(
        self,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        elapsed_time: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Create standardized success response.

        Args:
            message: Success message
            data: Optional data to include
            elapsed_time: Optional elapsed time in seconds

        Returns:
            Standardized response dictionary
        """
        response = {
            "success": True,
            "message": message
        }

        if data:
            response.update(data)

        if elapsed_time is not None:
            response["elapsed_time"] = elapsed_time

        return response

    def operation_started_response(
        self,
        operation_id: int,
        operation_name: str,
        additional_info: Optional[Dict[str, Any]] = None
    ) -> JSONResponse:
        """
        Create standardized response for started background operation.

        Args:
            operation_id: ID of the created operation
            operation_name: Name of the operation
            additional_info: Optional additional info to include

        Returns:
            JSONResponse with 202 Accepted status
        """
        content = {
            "success": True,
            "message": f"{operation_name} started",
            "operation_id": operation_id,
            "operation_name": operation_name,
            "status": "running",
            "note": f"Check /api/progress/operations/{operation_id} for real-time progress"
        }

        if additional_info:
            content.update(additional_info)

        return JSONResponse(status_code=202, content=content)

    # ========================================================================
    # ERROR HANDLING
    # ========================================================================

    async def handle_endpoint_error(
        self,
        error: Exception,
        user_info: Dict[str, Any],
        function_name: str,
        elapsed_time: float,
        db: Optional[AsyncSession] = None,
        operation: Optional[ActiveOperation] = None
    ):
        """
        Handle errors in endpoints with proper logging and database updates.

        Args:
            error: The exception that occurred
            user_info: User information dict
            function_name: Name of the function that failed
            elapsed_time: Time elapsed before error
            db: Optional database session
            operation: Optional ActiveOperation to mark as failed
        """
        logger.error(
            f"{self.tool_name}.{function_name} failed after {elapsed_time:.2f}s: {str(error)}",
            {
                "tool": self.tool_name,
                "function": function_name,
                "user": user_info["username"],
                "error": str(error),
                "error_type": type(error).__name__,
                "elapsed_time": elapsed_time
            }
        )

        # Mark operation as failed if provided
        if operation and db:
            try:
                await self.mark_operation_failed(db, operation, user_info, error)
            except Exception as db_error:
                logger.error(f"Failed to update operation status: {db_error}")

        # Raise HTTP exception
        raise HTTPException(
            status_code=500,
            detail=f"{function_name.replace('_', ' ').title()} failed: {str(error)}"
        )

    # ========================================================================
    # BACKGROUND TASK WRAPPER
    # ========================================================================

    def create_background_task(
        self,
        task_func: Callable,
        operation_id: int,
        user_info: Dict[str, Any],
        function_name: str,
        operation_name: str,
        **task_kwargs
    ) -> Callable:
        """
        Create a background task wrapper with error handling and operation tracking.

        Args:
            task_func: The actual task function to execute
            operation_id: ID of the operation
            user_info: User information dict
            function_name: Name of the function
            operation_name: Name of the operation
            **task_kwargs: Additional kwargs to pass to task_func

        Returns:
            Wrapped task function
        """
        def wrapped_task():
            try:
                # Change to project root
                original_cwd = os.getcwd()
                os.chdir(project_root)

                # Redirect stderr to avoid broken pipe errors in background thread
                old_stderr = sys.stderr
                sys.stderr = open(os.devnull, 'w')

                try:
                    # Execute the actual task
                    result = task_func(**task_kwargs)
                finally:
                    # Restore stderr and directory
                    sys.stderr = old_stderr
                    os.chdir(original_cwd)

                # Mark operation as complete
                result_data = result if isinstance(result, dict) else None
                self.mark_operation_complete_sync(
                    operation_id=operation_id,
                    user_info=user_info,
                    function_name=function_name,
                    operation_name=operation_name,
                    result_data=result_data
                )

            except Exception as e:
                # Mark operation as failed
                self.mark_operation_failed_sync(
                    operation_id=operation_id,
                    user_info=user_info,
                    function_name=function_name,
                    operation_name=operation_name,
                    error=e
                )

        return wrapped_task

    # ========================================================================
    # UTILITY METHODS
    # ========================================================================

    def log_function_start(
        self,
        function_name: str,
        user_info: Dict[str, Any],
        **kwargs
    ):
        """
        Log function start with parameters.

        Args:
            function_name: Name of the function
            user_info: User information dict
            **kwargs: Additional parameters to log
        """
        log_data = {
            "tool": self.tool_name,
            "function": function_name,
            "user": user_info["username"]
        }
        log_data.update(kwargs)

        logger.info(
            f"{self.tool_name}.{function_name} started by {user_info['username']}",
            log_data
        )

    def log_function_success(
        self,
        function_name: str,
        user_info: Dict[str, Any],
        elapsed_time: float,
        **kwargs
    ):
        """
        Log function success with metrics.

        Args:
            function_name: Name of the function
            user_info: User information dict
            elapsed_time: Time elapsed in seconds
            **kwargs: Additional metrics to log
        """
        log_data = {
            "tool": self.tool_name,
            "function": function_name,
            "user": user_info["username"],
            "elapsed_time": elapsed_time
        }
        log_data.update(kwargs)

        logger.success(
            f"{self.tool_name}.{function_name} completed in {elapsed_time:.2f}s",
            log_data
        )
