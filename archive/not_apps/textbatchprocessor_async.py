"""
TextBatchProcessor API - Batch text file processing tool

Provides endpoints for:
- Find and replace across multiple files
- Extract unique strings
- Combine multiple files
- Word count statistics
- Split files by delimiter
"""

from fastapi import APIRouter, Depends, UploadFile, File, BackgroundTasks, Form
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from pathlib import Path
import asyncio
from loguru import logger

from server.api.base_tool_api import BaseToolAPI
from server.utils.dependencies import get_async_db, get_current_active_user_async
from client.tools.text_batch_processor import core as tbp_core


class TextBatchProcessorAPI(BaseToolAPI):
    """TextBatchProcessor API using BaseToolAPI pattern"""

    def __init__(self):
        super().__init__(
            tool_name="TextBatchProcessor",
            router_prefix="/api/v2/textbatchprocessor",
            temp_dir="/tmp/textbatchprocessor_test"
        )
        self._setup_routes()

    def _setup_routes(self):
        """Setup all TextBatchProcessor API routes"""

        # Health check
        @self.router.get("/health")
        async def health_check():
            """Health check for TextBatchProcessor"""
            return {
                "status": "ok",
                "tool": "TextBatchProcessor",
                "functions": [
                    "find_and_replace",
                    "extract_unique_strings",
                    "combine_files",
                    "word_count_stats",
                    "split_by_delimiter"
                ]
            }

        # Find and Replace
        @self.router.post("/test/find-and-replace")
        async def find_and_replace(
            files: List[UploadFile] = File(...),
            find_pattern: str = Form(...),
            replace_text: str = Form(...),
            use_regex: bool = Form(False),
            background_tasks: BackgroundTasks = BackgroundTasks(),
            db: AsyncSession = Depends(get_async_db),
            current_user: dict = Depends(get_current_active_user_async)
        ):
            """
            Find and replace text patterns in multiple files.

            Supports both simple text replacement and regex patterns.
            """
            try:
                # Extract user info
                user_info = self.extract_user_info(current_user)

                # Save uploaded files
                file_paths = await self.save_uploaded_files(files)

                # Create operation
                operation = await self.create_operation(
                    db=db,
                    user_info=user_info,
                    function_name="find_and_replace",
                    operation_name=f"Find & Replace in {len(files)} files",
                    file_info={
                        "files": [f.filename for f in files],
                        "pattern": find_pattern,
                        "use_regex": use_regex
                    }
                )

                # Execute in background
                background_tasks.add_task(
                    self._execute_find_and_replace,
                    operation["operation_id"],
                    file_paths,
                    find_pattern,
                    replace_text,
                    use_regex,
                    user_info
                )

                return JSONResponse({
                    "status": "processing",
                    "operation_id": operation["operation_id"],
                    "message": f"Processing {len(files)} files..."
                })

            except Exception as e:
                logger.error(f"Find and replace error: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        # Extract Unique Strings
        @self.router.post("/test/extract-unique")
        async def extract_unique(
            files: List[UploadFile] = File(...),
            background_tasks: BackgroundTasks = BackgroundTasks(),
            db: AsyncSession = Depends(get_async_db),
            current_user: dict = Depends(get_current_active_user_async)
        ):
            """Extract unique strings from multiple files"""
            try:
                user_info = self.extract_user_info(current_user)
                file_paths = await self.save_uploaded_files(files)

                operation = await self.create_operation(
                    db=db,
                    user_info=user_info,
                    function_name="extract_unique_strings",
                    operation_name=f"Extract Unique from {len(files)} files",
                    file_info={"files": [f.filename for f in files]}
                )

                background_tasks.add_task(
                    self._execute_extract_unique,
                    operation["operation_id"],
                    file_paths,
                    user_info
                )

                return JSONResponse({
                    "status": "processing",
                    "operation_id": operation["operation_id"]
                })

            except Exception as e:
                logger.error(f"Extract unique error: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        # Combine Files
        @self.router.post("/test/combine")
        async def combine_files(
            files: List[UploadFile] = File(...),
            output_filename: str = Form("combined.txt"),
            background_tasks: BackgroundTasks = BackgroundTasks(),
            db: AsyncSession = Depends(get_async_db),
            current_user: dict = Depends(get_current_active_user_async)
        ):
            """Combine multiple files into one"""
            try:
                user_info = self.extract_user_info(current_user)
                file_paths = await self.save_uploaded_files(files)

                operation = await self.create_operation(
                    db=db,
                    user_info=user_info,
                    function_name="combine_files",
                    operation_name=f"Combine {len(files)} files",
                    file_info={
                        "files": [f.filename for f in files],
                        "output": output_filename
                    }
                )

                background_tasks.add_task(
                    self._execute_combine,
                    operation["operation_id"],
                    file_paths,
                    output_filename,
                    user_info
                )

                return JSONResponse({
                    "status": "processing",
                    "operation_id": operation["operation_id"]
                })

            except Exception as e:
                logger.error(f"Combine files error: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        # Word Count Stats
        @self.router.post("/test/word-count")
        async def word_count_stats(
            files: List[UploadFile] = File(...),
            background_tasks: BackgroundTasks = BackgroundTasks(),
            db: AsyncSession = Depends(get_async_db),
            current_user: dict = Depends(get_current_active_user_async)
        ):
            """Get word count statistics for files"""
            try:
                user_info = self.extract_user_info(current_user)
                file_paths = await self.save_uploaded_files(files)

                operation = await self.create_operation(
                    db=db,
                    user_info=user_info,
                    function_name="word_count_stats",
                    operation_name=f"Word Count for {len(files)} files",
                    file_info={"files": [f.filename for f in files]}
                )

                background_tasks.add_task(
                    self._execute_word_count,
                    operation["operation_id"],
                    file_paths,
                    user_info
                )

                return JSONResponse({
                    "status": "processing",
                    "operation_id": operation["operation_id"]
                })

            except Exception as e:
                logger.error(f"Word count error: {e}")
                raise HTTPException(status_code=500, detail=str(e))

    # Background task implementations

    async def _execute_find_and_replace(
        self,
        operation_id: int,
        file_paths: List[str],
        find_pattern: str,
        replace_text: str,
        use_regex: bool,
        user_info: dict
    ):
        """Execute find and replace in background"""
        try:
            # Emit start event
            emit_operation_start(operation_id, user_info["user_id"], user_info["username"])

            # Execute
            results = tbp_core.find_and_replace(
                file_paths=file_paths,
                find_pattern=find_pattern,
                replace_text=replace_text,
                use_regex=use_regex
            )

            # Complete operation
            await self.complete_operation(
                operation_id=operation_id,
                user_info=user_info,
                result_data={"results": results, "files_processed": len(results)}
            )

        except Exception as e:
            logger.error(f"Find and replace execution error: {e}")
            await self.fail_operation(operation_id, user_info, str(e))

    async def _execute_extract_unique(
        self,
        operation_id: int,
        file_paths: List[str],
        user_info: dict
    ):
        """Execute extract unique strings in background"""
        try:
            emit_operation_start(operation_id, user_info["user_id"], user_info["username"])

            results = tbp_core.extract_unique_strings(file_paths)

            await self.complete_operation(
                operation_id=operation_id,
                user_info=user_info,
                result_data={"unique_strings": len(results), "output_file": results}
            )

        except Exception as e:
            logger.error(f"Extract unique execution error: {e}")
            await self.fail_operation(operation_id, user_info, str(e))

    async def _execute_combine(
        self,
        operation_id: int,
        file_paths: List[str],
        output_filename: str,
        user_info: dict
    ):
        """Execute combine files in background"""
        try:
            emit_operation_start(operation_id, user_info["user_id"], user_info["username"])

            output_path = tbp_core.combine_files(file_paths, output_filename)

            await self.complete_operation(
                operation_id=operation_id,
                user_info=user_info,
                result_data={"output_file": output_path, "files_combined": len(file_paths)}
            )

        except Exception as e:
            logger.error(f"Combine files execution error: {e}")
            await self.fail_operation(operation_id, user_info, str(e))

    async def _execute_word_count(
        self,
        operation_id: int,
        file_paths: List[str],
        user_info: dict
    ):
        """Execute word count stats in background"""
        try:
            emit_operation_start(operation_id, user_info["user_id"], user_info["username"])

            stats = tbp_core.get_word_count_stats(file_paths)

            await self.complete_operation(
                operation_id=operation_id,
                user_info=user_info,
                result_data={"stats": stats}
            )

        except Exception as e:
            logger.error(f"Word count execution error: {e}")
            await self.fail_operation(operation_id, user_info, str(e))


# Create API instance and router
tbp_api = TextBatchProcessorAPI()
router = tbp_api.router
