"""
WordCountMaster API Endpoints (Using BaseToolAPI Pattern)

REST API for WordCountMaster translation word count tracking tool.
Migrated from wordcount_diff_master.py desktop app to web API.

Features:
- Process XML translation files from loc and export folders
- Compare TODAY's data against any past date
- Smart weekly/monthly categorization (7 days vs 30 days)
- Generate Excel reports with 4 sheets (2 active, 2 N/A)
- Track history in JSON file
"""

from fastapi import Depends, HTTPException, UploadFile, File, Form, BackgroundTasks, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import time
import json
import shutil
from pathlib import Path
from datetime import datetime, timedelta

from server.api.base_tool_api import BaseToolAPI
from server.utils.dependencies import get_async_db, get_current_active_user_async
from loguru import logger


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class ProcessFilesRequest(BaseModel):
    """Request model for processing wordcount files."""
    past_date: str  # Format: YYYY-MM-DD
    output_filename: Optional[str] = None


class HistoryEntry(BaseModel):
    """Model for history entry."""
    date: str
    total_words: int
    completed_words: int
    coverage: float


# ============================================================================
# WORDCOUNT CONSTANTS
# ============================================================================

# Language codes (excluding Korean)
SUPPORTED_LANGUAGES = ["ENG", "FRA", "GER", "ITA", "SPA", "POR", "RUS", "JPN", "CHS", "CHT", "THA", "POL"]

# Category names for detailed sheets
CATEGORIES = ["Faction", "Main", "Sequencer + Other", "System", "World", "UI", "Quest", "Item", "NPC", "Misc"]


# ============================================================================
# WORDCOUNT API CLASS
# ============================================================================

class WordCountMasterAPI(BaseToolAPI):
    """
    WordCountMaster REST API using BaseToolAPI pattern.

    Provides word count tracking and comparison for translation files.
    """

    def __init__(self):
        super().__init__(
            tool_name="WordCountMaster",
            router_prefix="/api/v2/wordcount",
            temp_dir="/tmp/wordcount_uploads",
            router_tags=["WordCountMaster"]
        )

        # History file path
        self.history_file = Path("/tmp/wordcount_history.json")

        # Output directory for generated reports
        self.output_dir = Path("/tmp/wordcount_reports")
        self.output_dir.mkdir(exist_ok=True, parents=True)

        # Register routes
        self._register_routes()

        logger.success("WordCountMaster API initialized")

    def _register_routes(self):
        """Register all endpoint routes."""
        self.router.get("/health")(self.health)
        self.router.post("/process")(self.process_files)
        self.router.get("/history")(self.get_history)
        self.router.get("/download/{report_id}")(self.download_report)
        self.router.delete("/history")(self.clear_history)

    # ========================================================================
    # ENDPOINTS
    # ========================================================================

    async def health(self):
        """Check if WordCountMaster is ready."""
        logger.info("WordCountMaster health check requested")

        history_exists = self.history_file.exists()
        history_entries = 0

        if history_exists:
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    history_entries = len(data.get('history', []))
            except Exception as e:
                logger.warning(f"Could not read history file: {e}")

        return {
            "status": "ok",
            "history_file_exists": history_exists,
            "history_entries": history_entries,
            "supported_languages": SUPPORTED_LANGUAGES,
            "temp_dir": str(self.temp_dir),
            "output_dir": str(self.output_dir)
        }

    async def process_files(
        self,
        background_tasks: BackgroundTasks,
        files: List[UploadFile] = File(...),
        past_date: str = Form(...),
        current_user: dict = Depends(get_current_active_user_async),
        db: AsyncSession = Depends(get_async_db)
    ):
        """
        Process XML translation files and generate word count comparison report.

        Args:
            files: List of XML files from loc and export folders
            past_date: Past date to compare against (YYYY-MM-DD format)

        Returns:
            Operation ID for tracking progress
        """
        start_time = time.time()
        user_info = self.extract_user_info(current_user)

        self.log_function_start("process_files", user_info,
                                files_count=len(files),
                                past_date=past_date)

        # Validate date format
        try:
            past_date_obj = datetime.strptime(past_date, "%Y-%m-%d")
            today = datetime.now()
            days_diff = (today - past_date_obj).days

            if days_diff < 0:
                raise HTTPException(status_code=400, detail="Past date cannot be in the future")
            if days_diff > 365:
                raise HTTPException(status_code=400, detail="Past date cannot be more than 1 year ago")

        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

        # Create ActiveOperation
        operation = await self.create_operation(
            db=db,
            user_info=user_info,
            function_name="process_files",
            operation_name=f"WordCount Report ({len(files)} files, {days_diff} days)",
            file_info={
                "files": [f.filename for f in files],
                "past_date": past_date,
                "days_diff": days_diff
            }
        )

        await self.emit_start_event(operation, user_info)

        try:
            # Save uploaded files
            file_paths = await self.save_uploaded_files(files, "XML file")

            # Queue background task
            background_tasks.add_task(
                self._run_process_files_background,
                operation_id=operation.operation_id,
                user_info=user_info,
                file_paths=file_paths,
                past_date=past_date
            )

            logger.success(f"WordCount processing queued as operation {operation.operation_id}")

            return self.operation_started_response(
                operation_id=operation.operation_id,
                operation_name=operation.operation_name,
                additional_info={
                    "files_count": len(files),
                    "past_date": past_date,
                    "days_diff": days_diff,
                    "category": "Weekly" if abs(days_diff - 7) < abs(days_diff - 30) else "Monthly"
                }
            )

        except Exception as e:
            await self.handle_endpoint_error(
                error=e,
                user_info=user_info,
                function_name="process_files",
                elapsed_time=time.time() - start_time,
                db=db,
                operation=operation
            )

    async def get_history(
        self,
        current_user: dict = Depends(get_current_active_user_async)
    ):
        """
        Get word count history.

        Returns list of all historical runs.
        """
        start_time = time.time()
        user_info = self.extract_user_info(current_user)

        self.log_function_start("get_history", user_info)

        try:
            if not self.history_file.exists():
                return self.success_response(
                    message="No history found",
                    data={"history": [], "total_runs": 0},
                    elapsed_time=time.time() - start_time
                )

            with open(self.history_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                history = data.get('history', [])

            elapsed_time = time.time() - start_time

            self.log_function_success("get_history", user_info, elapsed_time,
                                      runs_count=len(history))

            return self.success_response(
                message=f"Retrieved {len(history)} historical runs",
                data={
                    "history": history,
                    "total_runs": len(history)
                },
                elapsed_time=elapsed_time
            )

        except Exception as e:
            await self.handle_endpoint_error(
                error=e,
                user_info=user_info,
                function_name="get_history",
                elapsed_time=time.time() - start_time
            )

    async def download_report(
        self,
        report_id: str,
        current_user: dict = Depends(get_current_active_user_async)
    ):
        """
        Download generated word count report.

        Args:
            report_id: Report filename (without path)

        Returns:
            Excel file for download
        """
        user_info = self.extract_user_info(current_user)

        logger.info(f"Download report requested: {report_id}", {
            "user": user_info["username"],
            "report_id": report_id
        })

        # Validate filename (prevent directory traversal)
        if ".." in report_id or "/" in report_id or "\\" in report_id:
            raise HTTPException(status_code=400, detail="Invalid report ID")

        report_path = self.output_dir / report_id

        if not report_path.exists():
            logger.error(f"Report not found: {report_id}")
            raise HTTPException(status_code=404, detail="Report not found")

        logger.success(f"Serving report: {report_id}", {
            "user": user_info["username"],
            "report_id": report_id,
            "file_size": report_path.stat().st_size
        })

        return FileResponse(
            path=str(report_path),
            filename=report_id,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    async def clear_history(
        self,
        current_user: dict = Depends(get_current_active_user_async)
    ):
        """
        Clear word count history.

        Deletes the history JSON file.
        """
        start_time = time.time()
        user_info = self.extract_user_info(current_user)

        self.log_function_start("clear_history", user_info)

        try:
            if self.history_file.exists():
                self.history_file.unlink()
                logger.warning(f"History cleared by {user_info['username']}")

            elapsed_time = time.time() - start_time

            self.log_function_success("clear_history", user_info, elapsed_time)

            return self.success_response(
                message="History cleared successfully",
                elapsed_time=elapsed_time
            )

        except Exception as e:
            await self.handle_endpoint_error(
                error=e,
                user_info=user_info,
                function_name="clear_history",
                elapsed_time=time.time() - start_time
            )

    # ========================================================================
    # BACKGROUND TASKS
    # ========================================================================

    def _run_process_files_background(
        self,
        operation_id: int,
        user_info: dict,
        file_paths: List[str],
        past_date: str
    ):
        """Background task for processing word count files."""
        def task():
            logger.info(f"Processing {len(file_paths)} XML files for date {past_date}")

            # Import the actual wordcount processing logic
            # For now, this is a placeholder - we'll integrate the actual logic later
            from server.tools.wordcount.processor import WordCountProcessor

            processor = WordCountProcessor(
                history_file=str(self.history_file),
                output_dir=str(self.output_dir)
            )

            # Process files and generate report
            report_path, stats = processor.process_files(
                file_paths=file_paths,
                past_date=past_date
            )

            report_filename = Path(report_path).name

            logger.success(f"WordCount report generated: {report_filename}", {
                "report_path": report_path,
                "stats": stats
            })

            return {
                "report_id": report_filename,
                "report_path": report_path,
                "languages_processed": stats.get("languages_processed", 0),
                "total_words": stats.get("total_words", 0),
                "completed_words": stats.get("completed_words", 0),
                "coverage_percent": stats.get("coverage_percent", 0),
                "category": stats.get("category", "Unknown"),
                "days_diff": stats.get("days_diff", 0)
            }

        wrapped = self.create_background_task(
            task_func=task,
            operation_id=operation_id,
            user_info=user_info,
            function_name="process_files",
            operation_name="WordCount Report Generation"
        )
        wrapped()


# ============================================================================
# INITIALIZE AND EXPORT ROUTER
# ============================================================================

wordcount_api = WordCountMasterAPI()
router = wordcount_api.router
