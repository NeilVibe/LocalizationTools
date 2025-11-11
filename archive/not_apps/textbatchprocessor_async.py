"""
TextBatchProcessor API - Batch text file processing endpoints

Simple tool for common text operations:
- Find and replace patterns
- Extract unique strings
- Combine multiple files
- Word count statistics
- Split files by delimiter

Inherits from BaseToolAPI for consistent patterns.
"""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from pathlib import Path
import tempfile
import shutil
import sys
import time

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from server.api.base_tool_api import BaseToolAPI
from server.utils.dependencies import get_async_db, get_current_active_user_async
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger


# ============================================
# Request/Response Models
# ============================================

class FindReplaceRequest(BaseModel):
    """Request model for find and replace operation"""
    find_pattern: str = Field(..., description="Pattern to find")
    replace_text: str = Field(..., description="Replacement text")
    use_regex: bool = Field(False, description="Use regex matching")


class SplitRequest(BaseModel):
    """Request model for split operation"""
    delimiter: str = Field("\\n\\n", description="Delimiter to split by")
    prefix: str = Field("part", description="Prefix for output files")


class CombineRequest(BaseModel):
    """Request model for combine operation"""
    separator: str = Field("\\n", description="Separator between files")


# ============================================
# API Router
# ============================================

class TextBatchProcessorAPI(BaseToolAPI):
    """
    TextBatchProcessor API endpoints using BaseToolAPI pattern.

    Demonstrates how quickly a new app can be added using the base class.
    """

    def __init__(self):
        super().__init__(
            tool_name="TextBatchProcessor",
            router_prefix="/api/v2/textbatchprocessor"
        )
        self.router = APIRouter(prefix="/api/v2/textbatchprocessor", tags=["TextBatchProcessor"])
        self._setup_routes()

    def _setup_routes(self):
        """Setup all API routes"""

        @self.router.post("/find-replace")
        async def find_replace(
            files: List[UploadFile] = File(...),
            find_pattern: str = Form(...),
            replace_text: str = Form(...),
            use_regex: bool = Form(False),
            current_user: dict = Depends(get_current_active_user_async),
            db: AsyncSession = Depends(get_async_db),
            background_tasks: BackgroundTasks = None
        ):
            """Find and replace text patterns in uploaded files"""
            return await self._handle_find_replace(
                files, find_pattern, replace_text, use_regex, current_user, db, background_tasks
            )

        @self.router.post("/extract-unique")
        async def extract_unique(
            files: List[UploadFile] = File(...),
            sort_alphabetically: bool = Form(True),
            current_user: dict = Depends(get_current_active_user_async),
            db: AsyncSession = Depends(get_async_db),
            background_tasks: BackgroundTasks = None
        ):
            """Extract all unique strings from uploaded files"""
            return await self._handle_extract_unique(
                files, sort_alphabetically, current_user, db, background_tasks
            )

        @self.router.post("/combine")
        async def combine(
            files: List[UploadFile] = File(...),
            separator: str = Form("\\n"),
            current_user: dict = Depends(get_current_active_user_async),
            db: AsyncSession = Depends(get_async_db),
            background_tasks: BackgroundTasks = None
        ):
            """Combine multiple files into one"""
            return await self._handle_combine(
                files, separator, current_user, db, background_tasks
            )

        @self.router.post("/word-count")
        async def word_count(
            files: List[UploadFile] = File(...),
            current_user: dict = Depends(get_current_active_user_async),
            db: AsyncSession = Depends(get_async_db)
        ):
            """Get word count statistics for uploaded files"""
            return await self._handle_word_count(files, current_user, db)

        @self.router.post("/split")
        async def split(
            file: UploadFile = File(...),
            delimiter: str = Form("\\n\\n"),
            prefix: str = Form("part"),
            current_user: dict = Depends(get_current_active_user_async),
            db: AsyncSession = Depends(get_async_db),
            background_tasks: BackgroundTasks = None
        ):
            """Split a file by delimiter into multiple files"""
            return await self._handle_split(
                file, delimiter, prefix, current_user, db, background_tasks
            )

    # ============================================
    # Endpoint Handlers
    # ============================================

    async def _handle_find_replace(
        self,
        files: List[UploadFile],
        find_pattern: str,
        replace_text: str,
        use_regex: bool,
        current_user: dict,
        db: AsyncSession,
        background_tasks: BackgroundTasks
    ):
        """Handle find and replace operation"""
        start_time = time.time()
        user_info = self.extract_user_info(current_user)

        try:
            # Save uploaded files
            saved_files = await self.save_uploaded_files(files, log_prefix="TextBatchProcessor")

            # Import here to avoid circular dependencies
            from client.tools.text_batch_processor import find_and_replace

            # Process files
            logger.info(f"[TextBatchProcessor] Find/replace: '{find_pattern}' → '{replace_text}'")
            results = find_and_replace(
                file_paths=saved_files,
                find_pattern=find_pattern,
                replace_text=replace_text,
                use_regex=use_regex
            )

            logger.info(f"[TextBatchProcessor] Processed {len(results)} files")

            return self.success_response(
                message=f"Find and replace completed for {len(results)} files",
                data={
                    "files_processed": len(results),
                    "results": results
                },
                elapsed_time=time.time() - start_time
            )

        except Exception as e:
            return await self.handle_endpoint_error(
                e, user_info, "textbatchprocessor",
                time.time() - start_time, db
            )

    async def _handle_extract_unique(
        self,
        files: List[UploadFile],
        sort_alphabetically: bool,
        current_user: dict,
        db: AsyncSession,
        background_tasks: BackgroundTasks
    ):
        """Handle extract unique strings operation"""
        start_time = time.time()
        user_info = self.extract_user_info(current_user)

        try:
            # Save uploaded files
            saved_files = await self.save_uploaded_files(files, log_prefix="TextBatchProcessor")

            # Import here
            from client.tools.text_batch_processor import extract_unique_strings

            # Extract unique strings
            logger.info(f"[TextBatchProcessor] Extracting unique strings from {len(saved_files)} files")
            unique_strings, output_path = extract_unique_strings(
                file_paths=saved_files,
                sort_alphabetically=sort_alphabetically
            )

            logger.info(f"[TextBatchProcessor] Extracted {len(unique_strings)} unique strings")

            return self.success_response(
                message=f"Extracted {len(unique_strings)} unique strings",
                data={
                    "unique_count": len(unique_strings),
                    "output_file": output_path,
                    "unique_strings": unique_strings[:100]  # Return first 100 for preview
                },
                elapsed_time=time.time() - start_time
            )

        except Exception as e:
            return await self.handle_endpoint_error(
                e, user_info, "textbatchprocessor",
                time.time() - start_time, db
            )

    async def _handle_combine(
        self,
        files: List[UploadFile],
        separator: str,
        current_user: dict,
        db: AsyncSession,
        background_tasks: BackgroundTasks
    ):
        """Handle combine files operation"""
        start_time = time.time()
        user_info = self.extract_user_info(current_user)

        try:
            # Save uploaded files
            saved_files = await self.save_uploaded_files(files, log_prefix="TextBatchProcessor")

            # Import here
            from client.tools.text_batch_processor import combine_files

            # Combine files
            logger.info(f"[TextBatchProcessor] Combining {len(saved_files)} files")
            output_path, total_lines = combine_files(
                file_paths=saved_files,
                separator=separator
            )

            logger.info(f"[TextBatchProcessor] Combined into {total_lines} lines")

            return self.success_response(
                message=f"Combined {len(saved_files)} files into {total_lines} lines",
                data={
                    "files_combined": len(saved_files),
                    "total_lines": total_lines,
                    "output_file": output_path
                },
                elapsed_time=time.time() - start_time
            )

        except Exception as e:
            return await self.handle_endpoint_error(
                e, user_info, "textbatchprocessor",
                time.time() - start_time, db
            )

    async def _handle_word_count(
        self,
        files: List[UploadFile],
        current_user: dict,
        db: AsyncSession
    ):
        """Handle word count statistics operation"""
        start_time = time.time()
        user_info = self.extract_user_info(current_user)

        try:
            # Save uploaded files
            saved_files = await self.save_uploaded_files(files, log_prefix="TextBatchProcessor")

            # Import here
            from client.tools.text_batch_processor import get_word_count_stats

            # Get statistics
            logger.info(f"[TextBatchProcessor] Analyzing {len(saved_files)} files")
            stats = get_word_count_stats(file_paths=saved_files)

            # Calculate totals
            total_words = sum(s['words'] for s in stats.values())
            total_characters = sum(s['characters'] for s in stats.values())
            total_lines = sum(s['lines'] for s in stats.values())

            logger.info(f"[TextBatchProcessor] Total: {total_words} words, {total_characters} chars")

            return self.success_response(
                message=f"Analyzed {len(stats)} files",
                data={
                    "files_analyzed": len(stats),
                    "totals": {
                        "words": total_words,
                        "characters": total_characters,
                        "lines": total_lines
                    },
                    "per_file": stats
                },
                elapsed_time=time.time() - start_time
            )

        except Exception as e:
            return await self.handle_endpoint_error(
                e, user_info, "textbatchprocessor",
                time.time() - start_time, db
            )

    async def _handle_split(
        self,
        file: UploadFile,
        delimiter: str,
        prefix: str,
        current_user: dict,
        db: AsyncSession,
        background_tasks: BackgroundTasks
    ):
        """Handle split file operation"""
        start_time = time.time()
        user_info = self.extract_user_info(current_user)

        try:
            # Save uploaded file
            saved_files = await self.save_uploaded_files([file], log_prefix="TextBatchProcessor")

            # Import here
            from client.tools.text_batch_processor import split_by_delimiter

            # Split file
            logger.info(f"[TextBatchProcessor] Splitting file by delimiter: {repr(delimiter)}")
            output_paths = split_by_delimiter(
                file_path=saved_files[0],
                delimiter=delimiter,
                prefix=prefix
            )

            logger.info(f"[TextBatchProcessor] Split into {len(output_paths)} parts")

            return self.success_response(
                message=f"Split into {len(output_paths)} parts",
                data={
                    "parts_count": len(output_paths),
                    "output_files": output_paths
                },
                elapsed_time=time.time() - start_time
            )

        except Exception as e:
            return await self.handle_endpoint_error(
                e, user_info, "textbatchprocessor",
                time.time() - start_time, db
            )


# ============================================
# Router Instance
# ============================================

# Create API instance
text_batch_processor_api = TextBatchProcessorAPI()
router = text_batch_processor_api.router
